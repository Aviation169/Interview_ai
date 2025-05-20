# AI Interviewer Agent 🚀

Welcome to the **AI Interviewer Agent**, an AI-powered interview simulator designed to prepare you for roles like AGI Researcher! This Streamlit app, backed by DeepSeek-R1 (via Ollama), delivers a multi-round interview with personalized questions, real-time timers, a code editor, and a SQLite database to store your progress. Aim for a score of ≥60/100 to get "Selected" and unleash your AGI potential! 😎

This project includes tools to check stored data and optimize performance, addressing slowness and ensuring your answers are saved.

## 📋 Project Structure
- `interview_agent.py`: Main app with Streamlit UI, question generation, and evaluation.
- `check_interviews_db.py`: Script to verify data in `interviews.db`.
- `style.css`: Custom CSS for the app’s sleek UI (gradient banner, cards, Inter font).
- `requirements.txt`: Python dependencies.
- `interviews.db`: SQLite database (created on first run) storing questions, answers, scores, and more.

## ✨ Features
- **Multi-Round Interview**: 3 rounds (Easy, Medium, Hard), 5 questions each, tailored to your job role (e.g., AGI Researcher).
- **Dynamic UI**: Streamlit interface with gradient banner, progress bar, status badges, and animated buttons.
- **Timers**: Global (e.g., 30 minutes) and per-question (5-minute warning) timers, updated via JavaScript for smoothness.
- **Code Editor**: `streamlit-ace` for technical questions (Python).
- **SQLite Database**: Stores username, job role, questions, answers, scores, and selection status (`interviews.db`).
- **Enhancements**:
  - Personalized questions based on job role.
  - AGI bonus (+5 for specific questions), ethics bonus (+2), confidence slider (+1 for ≥8).
  - Custom question input.
  - Ethical feedback for AGI Researcher role.
  - PDF report with performance summary.
- **Leaderboard & History**: See top 5 scores and your past scores in the sidebar.
- **Database Checker**: `check_interviews_db.py` displays stored data in a table.

## 🛠️ Setup
### Prerequisites
- **Python**: 3.8+ (verify with `python --version`).
- **Ollama**: For DeepSeek-R1 LLM (GPU recommended for speed).
- **OS**: Windows (tested on `C:\Users\<>\Desktop\RAG`).

### Installation
1. **Clone or Set Up Project**:
   - Place all files (`interview_agent.py`, `check_interviews_db.py`, `style.css`, `requirements.txt`) in `C:\Users\Ajay sivakumar\Desktop\RAG`.

2. **Create Virtual Environment** (recommended):
   ```bash
   cd C:\Users\<>\Desktop\RAG
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   - Installs `ollama==0.3.3`, `streamlit==1.39.0`, `streamlit-ace==0.1.1`, `reportlab==4.2.2`, `tabulate==0.9.0`.
   - `sqlite3` is built-in.

4. **Set Up Ollama**:
   ```bash
   ollama pull deepseek-r1
   ollama run deepseek-r1
   ```
   - Verify: `ollama list`.
   - For speed, enable GPU (CUDA): Set `OLLAMA_CUDA_ENABLED=1`.

## 🚀 Usage
### Running the Interviewer Agent
1. **Start Ollama**:
   ```bash
   ollama run deepseek-r1
   ```

2. **Run the App**:
   ```bash
   cd C:\Users\<>\Desktop\RAG
   streamlit run interview_agent.py
   ```
   - Open `http://localhost:8501` in your browser.

3. **Use the UI**:
   - **Input**: Enter username (e.g., “Ajay Sivakumar”), job role (e.g., “AGI Researcher”), interview duration (e.g., 30 minutes), and optional custom question (e.g., “Ask about AGI safety”).
   - **Start**: Click “Start Interview 🚀” (requires username, job role).
   - **Sidebar**: Track progress (e.g., 7/15), round (e.g., “Round 1: Easy”), question (e.g., “Question 2/5”), timers (“Time Remaining: 28:45”, “Time on Question: 02:30”), leaderboard, and past scores.
   - **Answer**: Respond to 15 questions (3 rounds) via text or code editor (technical questions). Rate confidence (1-10).
   - **Finish**: Complete all questions or timeout. View feedback, score (0-100), selection status (≥60 = “Selected”), and download PDF report.
   - **Retry**: Click “🔄 Retry Interview” if score <60 (aim for 80+!).

### Checking the Database
1. **Run the Checker**:
   ```bash
   python check_interviews_db.py
   ```
   - Outputs a table of all records in `interviews.db` (username, job role, question, answer, scores, etc.).
   - Summary: Total records, unique users, job roles, completed interviews.

2. **Filter Data** (optional):
   - Edit `check_interviews_db.py` to uncomment lines in `if __name__ == "__main__":`.
   - Example: Filter by username “Ajay Sivakumar” or job role “AGI Researcher”:
     ```python
     filter_by_user_or_role(DB_PATH, username="Ajay Sivakumar", job_role="AGI Researcher")
     ```

## 🎯 Scoring Tips
To hit 80+/100:
- **Pace**: ~2 minutes/question (use timers).
- **Early Questions**: Nail Easy round (first 5) for a buffer.
- **Bonuses**:
  - Mention “AGI” or “ethics” (+2 for AGI Researcher).
  - Confidence ≥8 (+1).
  - Answer the AGI alignment question well (+5).
- **Code**: Write clear Python in the code editor (e.g., AGI pseudocode).
- **Custom Question**: Choose a strength (e.g., AGI safety).
- **Track**: Monitor progress bar and leaderboard.

## ⚡ Performance Optimization
The app is optimized to address slowness:
- **Cached Questions**: Stored in memory to reduce LLM calls (2-10 seconds each).
- **Persistent SQLite**: Single connection minimizes database overhead.
- **JavaScript Timers**: Smooth updates without Streamlit reruns.
- **Cached Queries**: Leaderboard and history use `@st.cache_data`.
- **Indexed Database**: Fast queries with `idx_user_role`.
- **External CSS**: `style.css` reduces UI rendering time.

**Expected Performance**:
- Startup: ~5-10 seconds.
- Question loading: ~0.1-2 seconds (cached) or ~2-10 seconds (LLM).
- Answer submission: ~3-10 seconds.
- Sidebar: Smooth timers.
- Database queries: ~0.1 seconds.

## 🐛 Troubleshooting
### General
- **Slow Performance**:
  - **Ollama**: Test `ollama generate deepseek-r1 "Test prompt"`. If >5 seconds, enable CUDA or use `llama3`.
  - **Streamlit**: Clear cache (`streamlit cache clear`) or try `--server.port 8502`.
  - **Hardware**: Ensure ≥8GB RAM, 4+ cores, SSD. Close heavy apps.
- **Dependencies**:
  - Update pip: `pip install --upgrade pip`.
  - Reinstall: `pip install -r requirements.txt`.
- **Ollama**: Verify `deepseek-r1` is running (`ollama list`).

### Database Issues
- **No Data in `interviews.db`**:
  - Check permissions in `C:\Users\<>\Desktop\RAG`.
  - Run `interview_agent.py`, answer a question, then `check_interviews_db.py`.
  - Delete `interviews.db` to recreate.
- **Slow Writes**:
  - Use SSD.
  - Disable antivirus for the folder.

### Errors
- **ValueError in `interview_agent.py`** (e.g., `unsupported format character ';'`):
  - Ensure you’re using the latest `interview_agent.py` with f-strings for JavaScript timers.
- **Other**:
  - Share error messages, slow parts (startup, questions, submission), or system specs (CPU, GPU, RAM).

## 📝 Example Usage
**Username**: Ajay Sivakumar  
**Job Role**: AGI Researcher  
**Duration**: 30 minutes  
**Custom Question**: “What are the risks of AGI misalignment?”

1. Run `streamlit run interview_agent.py`.
2. Enter details, start interview.
3. Answer questions (e.g., “Risks include value misalignment...”, confidence 9).
4. Sidebar shows progress, timers, leaderboard.
5. Timeout or complete: Get score (e.g., 88/100, “Selected”), download PDF.
6. Run `python check_interviews_db.py` to see stored data:
   ```
   +----+---------------+-------------+-------------------------+-------------------------+----------+--------------+-----------+---------------------+
   | ID | Username      | Job Role    | Question                | Answer                  | Q Score  | Total Score  | Selected  | Timestamp           |
   +----+---------------+-------------+-------------------------+-------------------------+----------+--------------+-----------+---------------------+
   | 7  | Ajay Sivakumar| AGI Researcher | What are the risks of...| Risks include value... |      8   |         35   | Not Selected | 2025-05-20T13:30:00 |
   | ...                                                                                                                    |
   +----+---------------+-------------+-------------------------+-------------------------+----------+--------------+-----------+---------------------+
   ```

## 🌟 Contributing
Want to add features (e.g., past Q&A display, hints)?:
1. Fork or edit locally.
2. Test changes with `interview_agent.py` and `check_interviews_db.py`.
3. Share ideas or issues via email or GitHub (if hosted).

## 📜 License
MIT License. Use, modify, and share freely!

---

Built with 💪 by Ajay Sivakumar to conquer AGI interviews! Let’s hit 80+/100, ra! 😄
