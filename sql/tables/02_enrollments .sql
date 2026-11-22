CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY,
    participant_id TEXT NOT NULL,
    participant_name TEXT NOT NULL,
    course_id INTEGER NOT NULL,
    course_date DATE NOT NULL,
    amount REAL NOT NULL,
    subsidy REAL NOT NULL,
    credits_used REAL NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses (course_id)
);