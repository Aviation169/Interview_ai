import ollama
import streamlit as st
import re
import sqlite3
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import random
import time
from datetime import datetime

# Load external CSS
with open("style.css", "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

# Database Functions
def init_db(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            job_role TEXT,
            question TEXT,
            answer TEXT,
            question_score INTEGER,
            total_score INTEGER,
            selected TEXT,
            timestamp TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_role ON interviews (username, job_role)")
    conn.commit()

def save_question_answer(conn, username, job_role, question, answer, question_score):
    c = conn.cursor()
    c.execute("""
        INSERT INTO interviews (username, job_role, question, answer, question_score, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, job_role, question, answer, question_score, datetime.now().isoformat()))
    conn.commit()

def save_final_results(conn, username, job_role, total_score, selected):
    c = conn.cursor()
    c.execute("""
        UPDATE interviews
        SET total_score = ?, selected = ?
        WHERE username = ? AND job_role = ? AND total_score IS NULL
    """, (total_score, "Selected" if selected else "Not Selected", username, job_role))
    conn.commit()

@st.cache_data(ttl=60)
def get_leaderboard(job_role):
    conn = sqlite3.connect("interviews.db")
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT username, job_role, total_score
        FROM interviews
        WHERE job_role = ? AND total_score IS NOT NULL
        ORDER BY total_score DESC
        LIMIT 5
    """, (job_role,))
    leaderboard = c.fetchall()
    conn.close()
    return leaderboard

@st.cache_data(ttl=60)
def get_user_history(username, job_role):
    conn = sqlite3.connect("interviews.db")
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT total_score
        FROM interviews
        WHERE username = ? AND job_role = ? AND total_score IS NOT NULL
        ORDER BY timestamp DESC
    """, (username, job_role))
    scores = [row[0] for row in c.fetchall()]
    conn.close()
    return scores

# LLM Interaction with DeepSeek-R1
def call_llm(prompt, context="", model="deepseek-r1"):
    try:
        response = ollama.generate(
            model=model,
            prompt=f"{context}\n{prompt}",
            options={"temperature": 0.7, "num_ctx": 2048}
        )
        raw_response = response["response"].strip()
        filtered_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)
        return filtered_response.strip()
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

# Interview State Management
class InterviewState:
    def __init__(self, job_role, username, interview_duration):
        self.job_role = job_role
        self.username = username
        self.rounds = [
            {"difficulty": "Easy", "scores": [], "history": [], "question_index": 0},
            {"difficulty": "Medium", "scores": [], "history": [], "question_index": 0},
            {"difficulty": "Hard", "scores": [], "history": [], "question_index": 0}
        ]
        self.questions = [[] for _ in self.rounds]  # Cache questions per round
        self.current_round = 0
        self.topics = [
            "technical_skills", "technical_skills", "problem_solving", "behavioral", "technical_skills"
        ]
        self.max_questions_per_round = 5
        self.custom_question = None
        self.total_time = 0
        self.question_start_time = None
        self.interview_duration = interview_duration  # in seconds

# Question Generation
def generate_question(state, topic, difficulty, round_idx, q_idx):
    if state.questions[round_idx] and len(state.questions[round_idx]) > q_idx:
        return state.questions[round_idx][q_idx]  # Use cached question
    context = f"Job Role: {state.job_role}\nDifficulty: {difficulty}\nAssume typical skills and responsibilities."
    if state.job_role.lower() == "agi researcher":
        context += "\nFor AGI Researcher, include reasoning, ethics, or novel architectures in Hard difficulty."
    if (state.job_role.lower() == "agi researcher" and 
        difficulty == "Hard" and 
        random.random() < 0.3 and 
        q_idx == 4):
        question = "How would you design an AGI to ensure safe alignment with human values?"
    else:
        prompt = f"""
        Generate a {topic} interview question for a {state.job_role} at {difficulty} difficulty.
        - Easy: Basic concepts or simple scenarios.
        - Medium: Practical applications or moderate challenges.
        - Hard: Advanced topics, complex problem-solving, or futuristic concepts (e.g., AGI ethics).
        Ensure the question is specific to the role. Return only the question.
        """
        question = call_llm(prompt, context)
    if len(state.questions[round_idx]) <= q_idx:
        state.questions[round_idx].append(question)
    return question

# Response Handling and Evaluation
def handle_response(state, question, response, confidence, conn):
    evaluation = evaluate_response(state, question, response, confidence)
    state.rounds[state.current_round]["history"].append((question, response))
    state.rounds[state.current_round]["scores"].append(evaluation["score"])
    save_question_answer(conn, state.username, state.job_role, question, response, evaluation["score"])
    return evaluation

def evaluate_response(state, question, response, confidence):
    context = f"Job Role: {state.job_role}\nDifficulty: {state.rounds[state.current_round]['difficulty']}\nQuestion: {question}\nResponse: {response}"
    prompt = """
    Evaluate for:
    - Accuracy
    - Relevance
    - Clarity
    - Ethics (if AGI Researcher, +2 for ethical considerations like safety, bias)
    Assign a score from 0-10 and provide a brief, encouraging explanation (1-2 sentences).
    Example: "Great start, adding more details could make it even stronger! Score: 6"
    Return only: Score: X, Explanation: ...
    """
    evaluation = call_llm(prompt, context)
    try:
        score = int(evaluation.split("Score: ")[1].split(",")[0])
        if state.job_role.lower() == "agi researcher":
            if "agi" in response.lower() or "ethics" in response.lower():
                score = min(score + 2, 10)
            if question.startswith("How would you design an AGI to ensure"):
                score = min(score + 5, 10)
        if confidence >= 8:
            score = min(score + 1, 10)
        explanation = evaluation.split("Explanation: ")[1]
        return {"score": score, "explanation": explanation}
    except:
        return {"score": 0, "explanation": "Oops, something went wrong, but keep shining!"}

# Decision Engine
def next_action(state):
    state.rounds[state.current_round]["question_index"] += 1
    if state.rounds[state.current_round]["question_index"] < state.max_questions_per_round:
        last_score = state.rounds[state.current_round]["scores"][-1] if state.rounds[state.current_round]["scores"] else 5
        current_difficulty = state.rounds[state.current_round]["difficulty"]
        if last_score < 5 and current_difficulty != "Easy":
            temp_difficulty = "Easy"
        elif last_score >= 8 and current_difficulty != "Hard":
            temp_difficulty = "Hard"
        else:
            temp_difficulty = current_difficulty
        return generate_question(state, state.topics[state.rounds[state.current_round]["question_index"]], temp_difficulty, state.current_round, state.rounds[state.current_round]["question_index"])
    elif state.current_round < len(state.rounds) - 1:
        state.current_round += 1
        state.rounds[state.current_round]["question_index"] = 0
        return generate_question(state, state.topics[0], state.rounds[state.current_round]["difficulty"], state.current_round, 0)
    return None

# Final Evaluation
def generate_final_evaluation(state, conn):
    total_score = sum(sum(round["scores"]) for round in state.rounds)
    max_possible_score = sum(len(round["scores"]) * 10 for round in state.rounds)
    total_score = int((total_score / 150) * 100) if max_possible_score > 0 else 0
    selection_threshold = 60
    is_selected = total_score >= selection_threshold

    context = "\n".join(
        f"Round {i+1} ({round['difficulty']}): History: {round['history']}, Scores: {round['scores']}"
        for i, round in enumerate(state.rounds)
    )
    context += f"\nJob Role: {state.job_role}\nTotal Time: {int(state.total_time)} seconds"
    prompt = f"""
    Summarize the candidate's performance for a {state.job_role} role across three rounds (Easy, Medium, Hard).
    If the interview was incomplete (e.g., timed out), note that only submitted answers were evaluated.
    Provide a brief, motivational summary (2-3 sentences) of strengths and areas to grow.
    Include the total score out of 100 and whether they are selected (score ≥{selection_threshold} means selected).
    If score < 50, add: "No worries, even AGI pioneers have off days! Try again!"
    Return only:
    Summary: ...
    Total Score: X
    Selection: [Selected/Not Selected]
    """
    evaluation = call_llm(prompt, context)
    save_final_results(conn, state.username, state.job_role, total_score, is_selected)
    return evaluation, total_score

# Leaderboard and Score History
def show_leaderboard(username, job_role):
    leaderboard = get_leaderboard(job_role)
    st.sidebar.header("🏆 Leaderboard")
    for i, (user, role, score) in enumerate(leaderboard):
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else ""
        css_class = "leaderboard-item top-score" if i == 0 else "leaderboard-item"
        st.sidebar.markdown(f'<div class="{css_class}">{icon} {user} ({role}): {score}/100</div>', unsafe_allow_html=True)
    
    st.sidebar.subheader("Your Past Scores")
    show_history = st.sidebar.checkbox("Show score history", value=False)
    if show_history:
        role_scores = get_user_history(username, job_role)
        if role_scores:
            st.sidebar.write(f"Past {job_role} scores: {', '.join(map(str, role_scores))}")
        else:
            st.sidebar.write("No past scores for this role.")

# PDF Report
def generate_report(state):
    pdf_file = "interview_report.pdf"
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, f"Interview Report: {state.job_role}")
    c.drawString(100, 730, f"Username: {state.username}")
    c.drawString(100, 710, f"Total Time: {int(state.total_time)} seconds")
    c.drawString(100, 690, f"Duration Set: {int(state.interview_duration / 60)} minutes")
    y = 660
    for i, round in enumerate(state.rounds):
        c.drawString(100, y, f"Round {i+1} ({round['difficulty']}):")
        y -= 20
        for j, (q, r) in enumerate(round["history"]):
            c.drawString(100, y, f"Q{j+1}: {q[:100]}...")
            c.drawString(100, y-20, f"A: {r[:100]}...")
            c.drawString(100, y-40, f"Score: {round['scores'][j]}")
            y -= 60
        y -= 20
    c.drawString(100, y, st.session_state.feedback.replace("\n", "; "))
    c.save()
    return pdf_file

# Streamlit UI
def main():
    # Initialize database connection
    conn = sqlite3.connect("interviews.db")
    init_db(conn)

    st.markdown("""
    <div class="welcome-banner">
        <h2>Unleash Your AGI Potential!</h2>
        <p>Choose your role and conquer a multi-round interview.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.title("🚀 AI Interviewer Agent")
    st.write("Enter your details, set interview duration, and start your journey!")

    # Initialize session state
    if "state" not in st.session_state:
        st.session_state.state = None
        st.session_state.current_question = None
        st.session_state.feedback = ""
        st.session_state.interview_started = False
        st.session_state.response_submitted = False
        st.session_state.question_count = 0
        st.session_state.custom_question_used = False
        st.session_state.timer_start = None
        st.session_state.total_time = 0
        st.session_state.interview_start_time = None
        st.session_state.interview_duration = None

    # Sidebar
    with st.sidebar:
        st.header("Progress")
        if st.session_state.interview_started and st.session_state.state:
            round_idx = st.session_state.state.current_round
            q_idx = st.session_state.state.rounds[round_idx]["question_index"]
            total_qs = st.session_state.state.max_questions_per_round * len(st.session_state.state.rounds)
            current_q = q_idx + 1 + (round_idx * st.session_state.state.max_questions_per_round)
            st.progress(current_q / total_qs)
            st.write(f"Round {round_idx + 1}: {st.session_state.state.rounds[round_idx]['difficulty']}")
            st.write(f"Question {q_idx + 1}/5")
            # JavaScript Timers
            interview_remaining = int(max(0, st.session_state.interview_duration - (time.time() - st.session_state.interview_start_time)))
            question_elapsed = int(time.time() - st.session_state.timer_start) if st.session_state.timer_start else 0
            st.markdown(f"""
            <script>
                function updateTimers(interviewRemaining, questionElapsed) {{
                    let interviewMins = Math.floor(interviewRemaining / 60);
                    let interviewSecs = interviewRemaining % 60;
                    let questionMins = Math.floor(questionElapsed / 60);
                    let questionSecs = questionElapsed % 60;
                    document.getElementById('interview-timer').innerText = 
                        `Time Remaining: ${{interviewMins.toString().padStart(2, '0')}}:${{interviewSecs.toString().padStart(2, '0')}}`;
                    document.getElementById('question-timer').innerText = 
                        `Time on Question: ${{questionMins.toString().padStart(2, '0')}}:${{questionSecs.toString().padStart(2, '0')}}`;
                    if (interviewRemaining < 120) {{
                        document.getElementById('interview-warning').style.display = 'block';
                    }}
                    if (questionElapsed > 300) {{
                        document.getElementById('question-warning').style.display = 'block';
                    }}
                }}
                setInterval(() => {{
                    updateTimers({interview_remaining}, {question_elapsed});
                }}, 1000);
            </script>
            <div id="interview-timer"></div>
            <p id="interview-warning" class="timer-warning" style="display:none">Less than 2 minutes left!</p>
            <div id="question-timer"></div>
            <p id="question-warning" class="timer-warning" style="display:none">Over 5 minutes! Try to wrap up.</p>
            """, unsafe_allow_html=True)
            st.write(f"Total Time: {int(st.session_state.state.total_time)} seconds")
        
        username = st.session_state.state.username if st.session_state.state else "Unknown"
        job_role = st.session_state.state.job_role if st.session_state.state else "Unknown"
        show_leaderboard(username, job_role)
        
        if not st.session_state.interview_started and st.session_state.feedback:
            if st.button("🔄 Retry Interview"):
                st.session_state.state = None
                st.session_state.current_question = None
                st.session_state.feedback = ""
                st.session_state.interview_started = False
                st.session_state.response_submitted = False
                st.session_state.question_count = 0
                st.session_state.custom_question_used = False
                st.session_state.timer_start = None
                st.session_state.total_time = 0
                st.session_state.interview_start_time = None
                st.session_state.interview_duration = None

    # Input widget
    username = st.text_input("Your Name", placeholder="Enter your name")
    job_role = st.text_input("Job Role (e.g., AI Engineer, AGI Researcher)", placeholder="Enter your role")
    interview_duration = st.number_input("Interview Duration (minutes)", min_value=10, max_value=60, value=30, step=5)
    custom_question = st.text_input("Suggest a Question (optional)", placeholder="E.g., Ask about AGI ethics")
    start_button = st.button("Start Interview 🚀")

    # Start interview
    if start_button and job_role and username:
        st.session_state.state = InterviewState(job_role, username, interview_duration * 60)
        st.session_state.interview_started = True
        st.session_state.current_question = generate_question(
            st.session_state.state, 
            st.session_state.state.topics[0], 
            st.session_state.state.rounds[0]["difficulty"],
            0, 0
        )
        st.session_state.feedback = ""
        st.session_state.response_submitted = False
        st.session_state.question_count = 1
        st.session_state.state.custom_question = custom_question if custom_question else None
        st.session_state.timer_start = time.time()
        st.session_state.total_time = 0
        st.session_state.interview_start_time = time.time()
        st.session_state.interview_duration = interview_duration * 60

    # Check for interview timeout
    if (st.session_state.interview_started and st.session_state.state and 
        st.session_state.interview_start_time):
        elapsed = time.time() - st.session_state.interview_start_time
        if elapsed >= st.session_state.interview_duration:
            final_evaluation, total_score = generate_final_evaluation(st.session_state.state, conn)
            st.session_state.feedback = final_evaluation + "\nNote: Interview timed out, evaluated submitted answers only."
            st.session_state.interview_started = False
            st.session_state.current_question = None
            st.session_state.timer_start = None
            st.session_state.interview_start_time = None
            conn.close()

    # Interview in progress
    if st.session_state.interview_started and st.session_state.state:
        round_idx = st.session_state.state.current_round
        q_idx = st.session_state.state.rounds[round_idx]["question_index"]
        if (not st.session_state.custom_question_used and 
            st.session_state.state.custom_question and 
            q_idx == 1):
            st.session_state.current_question = st.session_state.state.custom_question
            st.session_state.custom_question_used = True

        st.markdown(f"""
        <div class="status-badge">Round {round_idx + 1}: {st.session_state.state.rounds[round_idx]['difficulty']}</div>
        <div class="card">
            <h3>Question {q_idx + 1}/5</h3>
            <p>💡 {st.session_state.current_question}</p>
        </div>
        """, unsafe_allow_html=True)

        user_response = ""
        if st.session_state.state.topics[q_idx] == "technical_skills":
            from streamlit_ace import st_ace  # Lazy-load
            code = st_ace(
                language="python", 
                theme="monokai", 
                key=f"code_{st.session_state.question_count}",
                placeholder="Write your code here (if applicable)..."
            )
            user_response = st.text_area(
                "Your Answer", 
                key=f"response_{st.session_state.question_count}", 
                placeholder="Explain your approach or add details..."
            )
            if code.strip():
                user_response += "\nCode:\n" + code
        else:
            user_response = st.text_area(
                "Your Answer", 
                key=f"response_{st.session_state.question_count}", 
                placeholder="Type your answer here..."
            )

        confidence = st.slider("How confident are you in this answer?", 1, 10, 5)
        submit_button = st.button("Submit Answer ✅")

        if submit_button and user_response.strip():
            evaluation = handle_response(
                st.session_state.state, 
                st.session_state.current_question, 
                user_response, 
                confidence, 
                conn
            )
            st.session_state.feedback = evaluation["explanation"]
            st.session_state.response_submitted = True
            st.session_state.timer_start = time.time()

            next_question = next_action(st.session_state.state)
            if next_question:
                st.session_state.current_question = next_question
                st.session_state.question_count += 1
                st.session_state.response_submitted = False
            else:
                final_evaluation, total_score = generate_final_evaluation(st.session_state.state, conn)
                st.session_state.feedback = final_evaluation
                st.session_state.interview_started = False
                st.session_state.current_question = None
                st.session_state.timer_start = None
                st.session_state.interview_start_time = None
                conn.close()

        if st.session_state.response_submitted:
            st.markdown(f"""
            <div class="feedback">
                <p><strong>Feedback:</strong> {st.session_state.feedback}</p>
            </div>
            """, unsafe_allow_html=True)

    # Final evaluation
    if not st.session_state.interview_started and st.session_state.feedback and not st.session_state.current_question:
        st.markdown("""
        <div class="card">
            <h3>Interview Completed! 🎉</h3>
            <p>{}</p>
        </div>
        """.format(st.session_state.feedback.replace("\n", "<br>")), unsafe_allow_html=True)
        
        pdf_file = generate_report(st.session_state.state)
        with open(pdf_file, "rb") as f:
            st.download_button("📄 Download Report", f, file_name=pdf_file)

if __name__ == "__main__":
    main()