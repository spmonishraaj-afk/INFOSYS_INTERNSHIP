import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

# --- 1. Database Connection ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False) 
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- 2. Password Hashing Functions ---
def hash_password(password):
    return generate_password_hash(password)

def verify_password(plain_password, hashed_password):
    try:
        return check_password_hash(hashed_password, plain_password)
    except Exception:
        return False

# --- 3. Database Table Creation (MODIFIED) ---
def create_tables():
    """Creates all necessary tables if they don't exist."""
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
        ''')
        
        conn.execute('''
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_1 TEXT NOT NULL,
            skill_2 TEXT NOT NULL,
            education TEXT NOT NULL,
            prediction_1 TEXT NOT NULL,
            prediction_2 TEXT NOT NULL,
            prediction_3 TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        ''')
        
        # --- MODIFIED: Feedback Table ---
        conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prediction_id INTEGER, -- NEW: This links to the prediction
            rating INTEGER,
            comment TEXT,
            is_accurate TEXT,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (prediction_id) REFERENCES prediction_history (id) ON DELETE CASCADE
        );
        ''')
        
        try:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin123"), "admin")
            )
            conn.commit()
            print("Default admin user created (admin / admin123).")
        except sqlite3.IntegrityError:
            print("Admin user already exists.")
        
    except Exception as e:
        print(f"An error occurred creating tables: {e}")
    finally:
        conn.close()

# --- 4. User Account Functions ---
def add_user(username, password, role='user'):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  
    finally:
        conn.close()

def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user 

def get_all_users():
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, role FROM users ORDER BY username").fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()

# --- 5. Prediction History Functions (MODIFIED) ---
def save_prediction(user_id, skill_1, skill_2, education, p1, p2, p3):
    """Saves a user's prediction and returns the new prediction's ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO prediction_history 
            (user_id, skill_1, skill_2, education, prediction_1, prediction_2, prediction_3, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, skill_1, skill_2, education, p1, p2, p3, datetime.datetime.now())
        )
        conn.commit()
        return cursor.lastrowid # NEW: Return the ID of the row we just inserted
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return None
    finally:
        conn.close()

def get_prediction_history(user_id):
    conn = get_db_connection()
    history = conn.execute(
        "SELECT id, skill_1, skill_2, education, prediction_1, prediction_2, prediction_3, timestamp FROM prediction_history WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return history

def get_similar_users(skill_1, skill_2, education, user_id):
    conn = get_db_connection()
    sql_query = """
        SELECT 
            u.username, 
            ph.skill_1, 
            ph.skill_2, 
            ph.education
        FROM prediction_history ph
        JOIN users u ON ph.user_id = u.id
        WHERE 
            ph.user_id != ? AND
            ph.education = ? AND
            (
                ph.skill_1 = ? OR 
                ph.skill_1 = ? OR
                ph.skill_2 = ? OR
                ph.skill_2 = ?
            )
        GROUP BY u.username
        LIMIT 10 
        """
    params = (user_id, education, skill_1, skill_2, skill_1, skill_2)
    similar_users = conn.execute(sql_query, params).fetchall()
    conn.close()
    return similar_users

# --- 7. Admin Panel Functions ---
def get_total_user_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]
    conn.close()
    return count

def get_total_prediction_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM prediction_history").fetchone()[0]
    conn.close()
    return count

def get_average_feedback_rating():
    conn = get_db_connection()
    rating = conn.execute("SELECT IFNULL(AVG(rating), 0) FROM feedback").fetchone()[0]
    conn.close()
    return round(rating, 2) 

def get_all_predictions_with_username():
    conn = get_db_connection()
    all_history = conn.execute(
        """
        SELECT u.username, ph.skill_1, ph.skill_2, ph.education, ph.prediction_1, ph.timestamp
        FROM prediction_history ph
        JOIN users u ON ph.user_id = u.id
        ORDER BY ph.timestamp DESC
        """
    ).fetchall()
    conn.close()
    return all_history

def get_top_predicted_jobs():
    conn = get_db_connection()
    top_jobs = conn.execute(
        """
        SELECT prediction_1, COUNT(*) as count
        FROM prediction_history
        GROUP BY prediction_1
        ORDER BY count DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()
    return top_jobs

def get_top_searched_skills():
    conn = get_db_connection()
    top_skills = conn.execute(
        """
        SELECT Skill, SUM(count) AS total_count
        FROM (
            SELECT skill_1 AS Skill, COUNT(*) as count FROM prediction_history GROUP BY skill_1
            UNION ALL
            SELECT skill_2 AS Skill, COUNT(*) as count FROM prediction_history GROUP BY skill_2
        )
        GROUP BY Skill
        ORDER BY total_count DESC
        LIMIT 5;
        """
    ).fetchall()
    conn.close()
    return top_skills

def get_top_searched_education():
    conn = get_db_connection()
    top_edu = conn.execute(
        """
        SELECT education, COUNT(*) as count
        FROM prediction_history
        GROUP BY education
        ORDER BY count DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()
    return top_edu

# --- 8. Feedback Functions (MODIFIED) ---
def save_feedback(user_id, prediction_id, rating, comment, is_accurate):
    """Saves a user's feedback, linking it to a prediction."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO feedback (user_id, prediction_id, rating, comment, is_accurate, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, prediction_id, rating, comment, is_accurate, datetime.datetime.now())
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False
    finally:
        conn.close()

def get_all_feedback():
    """Fetches all feedback, joining with predictions to get context."""
    conn = get_db_connection()
    feedback = conn.execute(
        """
        SELECT 
            u.username, 
            f.rating, 
            f.is_accurate, 
            f.comment, 
            f.timestamp,
            ph.skill_1,
            ph.skill_2,
            ph.education,
            ph.prediction_1
        FROM feedback f
        JOIN users u ON f.user_id = u.id
        LEFT JOIN prediction_history ph ON f.prediction_id = ph.id
        ORDER BY f.timestamp DESC
        """
    ).fetchall()
    conn.close()
    return feedback

# --- 9. Initialization Block ---
if __name__ == "__main__":
    create_tables()
    print("Database tables initialized successfully.")