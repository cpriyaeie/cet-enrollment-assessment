# Section 2: Database Schema Design Considerations

## 1. Bronze, Silver, and Gold Layers

* **Bronze Layer (Raw Data)**
  * **Design:** Stores the exact raw CSV rows as `TEXT` along with ingestion metadata (`filename`, `ingested_at`, `row_hash`).
  * **Transformations:** None. Keeps an untouched audit trail in case a CET centre disputes a payout.

* **Silver Layer (Cleaned & Normalized Data)**
  * **Design:** Enforces proper data types (`INTEGER`, `REAL`, `DATE`) and splits data into clean relational tables (`courses`, `enrollments`, `participants`, `course_prerequisites`).
  * **Transformations:** Standardizes date formats to `YYYY-MM-DD`, deduplicates `enrollment_id`s, fixes inconsistent participant names, and unpacks the JSON `prerequisites` array.

* **Gold Layer (Analytics & Reporting)**
  * **Design:** Uses a **Star Schema** (`fact_enrollments`, `dim_courses`, `dim_participants`, `dim_date`) plus pre-aggregated monthly summary tables.
  * **Transformations:** Calculates `net_cash_payable` (`amount - subsidy - credits_used`), adds a `has_prerequisites_met` flag, and rolls up credit usage by course and month.

---

## 2. Handling Many-to-Many (M:N) Relationships

* **Participants ↔ Courses (via `enrollments`):**
  * One learner can take many courses, and one course has many learners. The `enrollments` table acts as a bridge table connecting `participants` (`1:N`) and `courses` (`1:N`).
  * Keeping `participants` in a separate dimension table prevents name-update issues across multiple enrollments.

* **Courses ↔ Prerequisite Courses (Self-Referencing M:N):**
  * Storing prerequisites as a JSON array (e.g., ``) works for raw ingestion, but is slow to query and cannot enforce foreign keys.
  * In the Silver layer, we unpack the JSON array into a dedicated junction table (`course_prerequisites`) with `(course_id, prerequisite_course_id)` as a composite primary key, foreign keys back to `courses(course_id)`, and a check preventing a course from requiring itself.

---

## 3. Data Quality Checks Between Layers

| Transition | Check | Action on Failure |
| :--- | :--- | :--- |
| **Bronze → Silver** | **Valid Dates:** Ensure `course_date` is a real calendar date within valid operational years. | Reject the file and return a row-by-row error report to the CET centre. |
| **Bronze → Silver** | **Financial Rules:** Ensure amounts are non-negative and `subsidy + credits_used <= amount`. | Reject invalid claims to prevent credit over-disbursement. |
| **Bronze → Silver** | **No Duplicate Claims:** Check uniqueness on `enrollment_id` and `(participant_id, course_id, course_date)`. | Block duplicate submissions for the same learner and course date. |
| **Silver → Gold** | **Prerequisite Check:** Verify required prerequisite courses were completed prior to `course_date`. | Flag non-compliant registrations (`has_prerequisites_met = 0`) for audit. |

---

## 4. Designing the Gold Layer for Fast Queries

* **Star Schema:**
  * `fact_enrollments` stores transaction metrics (`amount`, `subsidy`, `credits_used`, `net_cash_payable`) linked to `dim_courses`, `dim_participants`, and `dim_date`.
  * `dim_courses` tracks historical changes to course fees or prerequisites over time (SCD Type 2) so past enrollments are evaluated against the rules active at that time.
  * `dim_date` pre-computes year, quarter, month, and Singapore fiscal year (`Apr–Mar`) attributes for fast filtering.
* **Query Speed Optimizations:**
  * Add composite indexes on common filter columns such as `(date_key, course_key)`.
  * Maintain pre-aggregated monthly summary tables for dashboards so reports do not need to scan every raw enrollment row.
