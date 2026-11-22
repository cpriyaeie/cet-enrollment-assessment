# CET Course Enrollment Ingestion Pipeline

This repository contains the data ingestion pipeline for loading Continuous Education and Training (CET) course registration CSV submissions into a SQLite database (`courses.db`).

---

## Repository Structure

```text
├── data/
│   └── enrolments.csv                # Raw CET course enrollment submission CSV
├──docs/
   └──section2_schema_design.md       # Database schema & Medallion architecture design
   └──section4_ml_scaling.md          # ML inference bottleneck analysis & optimization
├── sql/
    └── reports
        /prerequisite_report.sql      # SQLite report identifying prerequisite violations
│   └── tables/                       # DDL scripts defining courses & enrolments tables
├── courses.db                        # SQLite database populated by ingest.py
├── ingest.py                         # Python ETL script to validate and load CSV data into SQLite
└── README.md                         # Setup and pipeline documentation
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


## Section 2: Database Schema Design Considerations
See [docs/section2_schema_design.md](docs/section2_schema_design.md) for the full design covering Medallion layers (Bronze, Silver, Gold), many-to-many relationships, data quality checks, and Gold layer analytical modeling.



## Section 3: Prerequisite Compliance Report

Execute sql/reports/prerequisite_report.sql against courses.db:
bash
sqlite3 -header -column courses.db < sql/reports/prerequisite_report.sql

### Overview
Unpacks each course's JSON `prerequisites` array using SQLite's `json_each()` and identifies participants who registered for a course without completing all required prerequisite courses prior to their `course_date.

## Section 4: Scaling ML Inference for 200M Courses
See [docs/section4_ml_scaling.md](docs/section4_ml_scaling.md) for the bottleneck analysis and how to optimize both SageMaker serving and the calling script.

