import sqlite3
from tabulate import tabulate
from pathlib import Path

def check_database(db_path="interviews.db"):
    """
    Check the contents of the interviews database and display all records in a table.
    
    Args:
        db_path (str): Path to the SQLite database file.
    """
    try:
        # Check if database file exists
        if not Path(db_path).exists():
            print(f"Error: Database file '{db_path}' does not exist.")
            return

        # Connect to the database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Verify table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interviews'")
        if not c.fetchone():
            print("Error: 'interviews' table does not exist in the database.")
            conn.close()
            return

        # Query all records from interviews table
        c.execute("""
            SELECT id, username, job_role, question, answer, question_score, 
                   total_score, selected, timestamp 
            FROM interviews
            ORDER BY timestamp DESC
        """)
        rows = c.fetchall()

        # Check if there are any records
        if not rows:
            print("No records found in the 'interviews' table.")
            conn.close()
            return

        # Define table headers
        headers = [
            "ID", "Username", "Job Role", "Question", "Answer", 
            "Q Score", "Total Score", "Selected", "Timestamp"
        ]

        # Truncate long strings for display (e.g., question, answer)
        display_rows = []
        for row in rows:
            # Truncate question and answer to 50 characters for readability
            question = (row[3][:47] + "...") if row[3] and len(row[3]) > 50 else row[3]
            answer = (row[4][:47] + "...") if row[4] and len(row[4]) > 50 else row[4]
            display_rows.append([
                row[0], row[1], row[2], question, answer, 
                row[5], row[6], row[7], row[8]
            ])

        # Print table using tabulate
        print("\nInterview Records:")
        print(tabulate(display_rows, headers=headers, tablefmt="grid"))

        # Summary statistics
        print("\nSummary:")
        print(f"Total Records: {len(rows)}")
        usernames = len(set(row[1] for row in rows))
        print(f"Unique Users: {usernames}")
        job_roles = len(set(row[2] for row in rows))
        print(f"Unique Job Roles: {job_roles}")
        completed = sum(1 for row in rows if row[6] is not None)
        print(f"Completed Interviews: {completed}")

        # Close connection
        conn.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def filter_by_user_or_role(db_path="interviews.db", username=None, job_role=None):
    """
    Query records filtered by username or job role.
    
    Args:
        db_path (str): Path to the SQLite database file.
        username (str, optional): Filter by username.
        job_role (str, optional): Filter by job role.
    """
    try:
        if not Path(db_path).exists():
            print(f"Error: Database file '{db_path}' does not exist.")
            return

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        query = """
            SELECT id, username, job_role, question, answer, question_score, 
                   total_score, selected, timestamp 
            FROM interviews
            WHERE 1=1
        """
        params = []
        if username:
            query += " AND username = ?"
            params.append(username)
        if job_role:
            query += " AND job_role = ?"
            params.append(job_role)
        query += " ORDER BY timestamp DESC"

        c.execute(query, params)
        rows = c.fetchall()

        if not rows:
            print(f"No records found for username='{username}' and/or job_role='{job_role}'.")
            conn.close()
            return

        headers = [
            "ID", "Username", "Job Role", "Question", "Answer", 
            "Q Score", "Total Score", "Selected", "Timestamp"
        ]
        display_rows = [
            [
                row[0], row[1], row[2], 
                (row[3][:47] + "...") if row[3] and len(row[3]) > 50 else row[3],
                (row[4][:47] + "...") if row[4] and len(row[4]) > 50 else row[4],
                row[5], row[6], row[7], row[8]
            ]
            for row in rows
        ]

        print(f"\nFiltered Records (username='{username}', job_role='{job_role}'):")
        print(tabulate(display_rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal Filtered Records: {len(rows)}")

        conn.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Path to the database
    DB_PATH = r"C:\Users\Ajay sivakumar\Desktop\RAG\interviews.db"

    # Check all records
    print("Checking all records in the database...")
    check_database(DB_PATH)

    # Example: Filter by username or job role (uncomment to use)
    # print("\nChecking records for specific user...")
    # filter_by_user_or_role(DB_PATH, username="Ajay Sivakumar")
    # print("\nChecking records for specific job role...")
    # filter_by_user_or_role(DB_PATH, job_role="AGI Researcher")
    # print("\nChecking records for user and job role...")
    # filter_by_user_or_role(DB_PATH, username="Ajay Sivakumar", job_role="AGI Researcher")