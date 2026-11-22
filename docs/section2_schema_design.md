# Section 2: Database Schema Design Considerations

## 1. Modeling Across Bronze, Silver, and Gold Layers

* **Bronze Layer (Raw Landing & Audit Trail)**
  * **Modeling:** Stores raw CSV submissions as `TEXT` alongside ingestion metadata (`_ingestion_id`, `_source_filename`, `_ingested_at`, `_row_hash`).
  * **Transformations:** None to business values. Preserves an immutable audit trail if a CET centre disputes subsidy or credit calculations.
* **Silver Layer (Cleansed, Conformed & Normalized)**
  * **Modeling:** Enforces the relational schema (`courses`, `enrollments`, `participants`, and `course_prerequisites`) with strict data types (`INTEGER`, `REAL`, `DATE`).
  * **Transformations:**
    * Standardizes heterogeneous date formats into ISO `YYYY-MM-DD`.
    * Deduplicates records on `enrollment_id` using latest-timestamp `UPSERT` logic.
    * Resolves canonical `participant_name` values per `participant_id`.
    * Explodes JSON `prerequisites` arrays into normalized relational rows.
* **Gold Layer (Curated Analytical Models)**
  * **Modeling:** Implements a **Star Schema** (`fact_enrollments`, `dim_courses`, `dim_participants`, `dim_date`) plus pre-aggregated summary tables.
  * **Transformations:** Computes derived financial metrics (`net_cash_payable = amount - subsidy - credits_used`), attaches compliance flags (`is_prerequisite_met`), and aggregates monthly/quarterly credit utilization by CET provider.

---

## 2. Handling Many-to-Many (M:N) Relationships

* **Learners ↔ Courses (via `enrollments`):**
  * A learner can register for multiple courses, and each course has many learners. The `enrollments` table resolves this M:N relationship as an associative transaction table linking `participants` (`1:N`) and `courses` (`1:N`).
  * Separating `participants` into its own entity in Silver avoids update anomalies when a learner's name changes across submissions.
* **Courses ↔ Prerequisite Courses (Self-Referencing M:N):**
  * While the raw `courses` table stores prerequisites as a JSON array (e.g., ``), querying JSON arrays at scale prevents foreign key enforcement and slows down dependency checks.
  * In the Silver layer, the JSON array is normalized into a self-referencing bridge table (`course_prerequisites`) with composite primary key `(course_id, prerequisite_course_id)`, foreign keys referencing `courses(course_id)`, and a `CHECK (course_id <> prerequisite_course_id)` constraint to prevent self-loops.

---

## 3. Data Quality Checks Between Layers

| Layer Transition | Validation / Rule | Action on Failure |
| :--- | :--- | :--- |
| **Bronze → Silver** | **Type & Calendar Validity:** Ensure `course_date` is a valid calendar date within realistic operational bounds (`2000–2030`). | Reject file atomically and return row-level error report to the CET centre. |
| **Bronze → Silver** | **Financial Reconciliation:** Enforce `amount >= 0`, `subsidy >= 0`, `credits_used >= 0`, and `subsidy + credits_used <= amount`. | Block over-disbursement claims and reject invalid submissions. |
| **Bronze → Silver** | **Duplicate Claim Prevention:** Enforce uniqueness on `enrollment_id` and composite `(participant_id, course_id, course_date)`. | Reject duplicate subsidy/credit claims for the same learner-course-date. |
| **Bronze → Silver** | **Referential Integrity:** Verify `course_id` exists in `courses`. | Enforce foreign key constraints; reject orphan course references. |
| **Silver → Gold** | **Prerequisite Eligibility:** Verify all `prerequisite_course_id`s were completed prior to `course_date`. | Populate `is_prerequisite_met = 0` in `fact_enrollments` for compliance reporting. |

---

## 4. Designing the Gold Layer for Efficient Analytical Queries

* **Star Schema Design:**
  * `fact_enrollments`: Grain of one row per valid enrollment, storing foreign keys (`course_key`, `participant_key`, `date_key`) and additive measures (`amount`, `subsidy`, `credits_used`, `net_cash_payable`, `is_prerequisite_met`).
  * `dim_courses` (SCD Type 2): Tracks changes to course fees or prerequisite rules over time (`effective_from`, `effective_to`, `is_current`) so historical compliance audits evaluate rules active on the enrollment date.
  * `dim_participants`: Stores unique learner profiles, total lifetime credits utilized, and enrollment counts.
  * `dim_date`: Pre-populated calendar dimension supporting Singapore fiscal year (`Apr–Mar`), quarter, and month roll-ups without runtime date parsing.
* **Performance Optimizations:**
  * **Composite Covering Indexes:** Index high-selectivity filter and join columns (e.g., `(date_key, course_key)` and `(participant_key, course_key, date_key)`).
  * **Pre-Aggregated Summary Tables:** Maintain `gold_monthly_disbursement_summary` grouped by fiscal period and course to power executive dashboards in milliseconds without scanning raw fact rows.