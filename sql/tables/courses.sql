CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    prerequisites TEXT -- JSON string representation of array<int> e.g., [1,2,3]
);