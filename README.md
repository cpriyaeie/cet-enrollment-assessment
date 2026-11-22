# CET Course Enrollment Ingestion Pipeline

This repository contains the data ingestion pipeline for loading Continuous Education and Training (CET) course registration CSV submissions into a SQLite database (`courses.db`).

---

## Repository Structure

```text
├── data/
│   └── enrolments.csv      # Raw CET course enrollment submission CSV
├── sql/
│   └── tables/             # DDL scripts defining courses & enrolments tables
├── courses.db              # SQLite database populated by ingest.py
├── ingest.py               # Python ETL script to validate and load CSV data into SQLite
└── README.md               # Setup and pipeline documentation
```

---
## Section 1: Data Ingestion Pipeline
## Setup & Execution

1. Ensure **Python 3.8+** is installed (uses standard library modules only: `csv`, `sqlite3`, `datetime`, `pathlib`).
2. Verify that `courses.db`, `sql/tables/*.sql`, and `data/enrolments.csv` are in place.
3. Run the ingestion script from the repository root:
   ```bash
   python ingest.py
   ```

---

## Data Quality Handling & Pipeline Behavior

`ingest.py` applies the DDL schemas in `sql/tables/`, detects the active table spelling (`enrolments` or `enrollments`), validates incoming records, and inserts all clean rows:

* **Multi-Format Date Standardization:** Parses and normalizes heterogeneous date formats (`YYYY-MM-DD`, `DD/MM/YYYY`, `YYYY/MM/DD`, `DD-MM-YYYY`, and `DD Mon YYYY`) into ISO-8601 (`YYYY-MM-DD`).
* **Invalid & Outlier Date Filtering:**
  * Row 22 (`enrollment_id = 21`) contains `2023-02-29` (non-existent calendar date; 2023 was not a leap year).
  * Row 27 (`enrollment_id = 26`) contains `1900-06-10` (out-of-range placeholder year).
  * Invalid rows are logged and skipped so the remaining **32 valid records** load cleanly without corrupting downstream reporting.
* **Participant Name Standardization:** Resolves inconsistent naming variations per `participant_id` (e.g., `"Fiona W"` -> `"Fiona Wong"`, `"Charles Ng"` -> `"Charlie Ng"`) by keeping the fullest name observed.
* **Financial & Idempotency Checks:** Enforces non-negative financial values, validates that `subsidy + credits_used <= amount`, and uses `ON CONFLICT(enrollment_id) DO UPDATE` so re-running the pipeline safely upserts records without creating duplicates.

## Section 3: Prerequisite Compliance Report

### How to Run
Execute `prerequisite_report.sql` against `courses.db`:
```bash
sqlite3 -header -column courses.db < prerequisite_report.sql
```

### Overview
Unpacks each course's JSON `prerequisites` array using SQLite's `json_each()` and identifies participants who registered for a course without completing all required prerequisite courses prior to their `course_date.


