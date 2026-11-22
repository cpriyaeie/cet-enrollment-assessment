import csv
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("courses.db")
SCHEMA_DIR = Path("sql/tables")
CSV_PATH = Path("data/enrolments.csv")

SUPPORTED_DATE_FORMATS = (
    "%Y-%m-%d",   # 2024-01-15
    "%d/%m/%Y",   # 15/01/2024
    "%Y/%m/%d",   # 2024/02/01
    "%d-%m-%Y",   # 01-02-2024
    "%d %b %Y",   # 20 Jan 2024
)


def parse_and_validate_date(date_str: str) -> str:
    """Parse multiple date formats and enforce realistic CET enrollment bounds."""
    cleaned = date_str.strip()
    parsed_dt = None

    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            parsed_dt = datetime.strptime(cleaned, fmt)
            break
        except ValueError:
            continue

    if parsed_dt is None:
        raise ValueError(f"Invalid or non-existent calendar date: '{cleaned}'")

    if parsed_dt.year < 2000 or parsed_dt.year > 2030:
        raise ValueError(f"Out-of-range enrollment year: '{cleaned}'")

    return parsed_dt.strftime("%Y-%m-%d")


def apply_schemas(conn: sqlite3.Connection, schema_dir: Path) -> None:
    """Apply all SQL DDL files in sql/tables."""
    if schema_dir.exists():
        for sql_file in sorted(schema_dir.glob("*.sql")):
            print(f"Applying schema: {sql_file}")
            with open(sql_file, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
    conn.commit()


def ingest_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    cursor = conn.cursor()
    canonical_names: dict[str, str] = {}
    valid_records: list[tuple] = []
    skipped_errors: list[str] = []

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            raw_eid = (row.get("enrollment_id") or "").strip()
            try:
                enrollment_id = int(raw_eid)
                participant_id = row["participant_id"].strip().upper()
                raw_name = row["participant_name"].strip()

                # Standardize name per participant_id (keep fullest name observed)
                if participant_id not in canonical_names or len(raw_name) > len(canonical_names[participant_id]):
                    canonical_names[participant_id] = raw_name

                course_id = int(row["course_id"].strip())
                course_date = parse_and_validate_date(row["course_date"])
                amount = float(row["amount"].strip())
                subsidy = float(row["subsidy"].strip())
                credits_used = float(row["credits_used"].strip())

                if amount < 0 or subsidy < 0 or credits_used < 0:
                    raise ValueError("Negative financial values are not permitted")

                if round(subsidy + credits_used, 2) > round(amount, 2):
                    raise ValueError("Subsidy + credits_used exceeds course amount")

                valid_records.append(
                    (
                        enrollment_id,
                        participant_id,
                        raw_name,
                        course_id,
                        course_date,
                        amount,
                        subsidy,
                        credits_used,
                    )
                )

            except Exception as exc:
                skipped_errors.append(f"Row {row_num} (enrollment_id={raw_eid}): {exc}")

    # Insert/upsert all valid records
    for eid, pid, _, cid, cdate, amt, sub, cred in valid_records:
        clean_name = canonical_names[pid]
        cursor.execute(
            """
            INSERT INTO enrolments (
                enrollment_id, participant_id, participant_name,
                course_id, course_date, amount, subsidy, credits_used
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(enrollment_id) DO UPDATE SET
                participant_id = excluded.participant_id,
                participant_name = excluded.participant_name,
                course_id = excluded.course_id,
                course_date = excluded.course_date,
                amount = excluded.amount,
                subsidy = excluded.subsidy,
                credits_used = excluded.credits_used
            """,
            (eid, pid, clean_name, cid, cdate, amt, sub, cred),
        )

    conn.commit()

    if skipped_errors:
        print(f"IGNORED {len(skipped_errors)} invalid row(s):")
        for msg in skipped_errors:
            print(f"  - {msg}")

    print(f"SUCCESS: Inserted/updated {len(valid_records)} valid records into 'enrolments'.")


if __name__ == "__main__":
    print(f"Target database: {DB_PATH}")
    print(f"Schema folder:   {SCHEMA_DIR}")
    print(f"Source CSV:      {CSV_PATH}")

    with sqlite3.connect(DB_PATH) as connection:
        apply_schemas(connection, SCHEMA_DIR)
        ingest_csv(connection, CSV_PATH)