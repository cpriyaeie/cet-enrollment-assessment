WITH course_prerequisites AS (
    -- Step 1: Unpack the JSON prerequisites array (e.g., [1, 2]) into one row per required course
    SELECT 
        c.course_id,
        c.name AS course_name,
        CAST(prereq.value AS INTEGER) AS required_course_id
    FROM courses c
    JOIN json_each(c.prerequisites) prereq
)
-- Step 2: Identify enrollments where a participant has not taken the required prerequisite beforehand
SELECT 
    e.enrollment_id,
    e.participant_id,
    e.participant_name,
    e.course_id,
    cp.course_name,
    e.course_date,
    cp.required_course_id AS missing_prerequisite_course_id
FROM enrollments e
JOIN course_prerequisites cp 
    ON e.course_id = cp.course_id
WHERE NOT EXISTS (
    -- Check if the participant completed the prerequisite course strictly before this course_date
    SELECT 1
    FROM enrollments prior
    WHERE prior.participant_id = e.participant_id
      AND prior.course_id = cp.required_course_id
      AND prior.course_date < e.course_date
)
ORDER BY 
    e.course_date, 
    e.enrollment_id;