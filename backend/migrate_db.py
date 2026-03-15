import sqlite3
import os

db_paths = [
    r"face_detection.db",
    r"missing_persons.db",
    r"data/face_detection.db",
    r"data/missing_persons.db"
]

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"Checking {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_images'")
            if cursor.fetchone():
                print(f"Table 'person_images' found in {db_path}")
                for col in ["blur_score", "yaw_angle", "pitch_angle", "quality_score"]:
                    try:
                        cursor.execute(f"ALTER TABLE person_images ADD COLUMN {col} FLOAT;")
                        print(f"Added '{col}'.")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            print(f"Column '{col}' already exists.")
                        else:
                            print(f"Error adding '{col}': {e}")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error connecting: {e}")
