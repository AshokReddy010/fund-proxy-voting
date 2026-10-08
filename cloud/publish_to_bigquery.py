"""Publish the curated tables from the local DuckDB warehouse to BigQuery.

The 73.8 million raw votes stay on this laptop. Only the finished tables, and
one summary built from the full vote table, go to the cloud. Every published
table is checked afterwards: its row count in BigQuery must equal the local count.

Run from the project folder:
    python cloud\\publish_to_bigquery.py --dry-run    show what would be sent
    python cloud\\publish_to_bigquery.py              send it

Why not everything: the free BigQuery sandbox allows 10 GB of storage for the
project's whole life, deletes tables after 60 days, and has no INSERT or MERGE.
So the curated layer is re-sent whole on each refresh, which also resets the
60-day clock.
"""
import argparse
import csv
import os
import tempfile
from datetime import datetime, timezone

import duckdb

PROJECT = "fund-voting-warehouse"
DATASET = "fund_voting"
LOCAL_DB = "fund_voting.duckdb"
LOG = os.path.join("cloud", "publish_log.csv")

# Tables copied as they are.
TABLES = [
    "dim_funds",
    "fct_fund_es_votes",
    "mart_support_by_direction",
    "mart_sibling_comparison",
    "data_quality_summary",
    "proposal_labels",
]

# One extra table, built here from all 73.8 million votes.
SUMMARY_NAME = "fct_fund_year_topic"
SUMMARY_SQL = """
select
    fund_id,
    report_year,
    case
        when is_environment then 'Environment'
        when is_social then 'Social'
        when is_say_on_pay then 'Executive pay'
        when is_director_election then 'Director elections'
        when is_governance then 'Governance'
        else 'Other'
    end                                                        as topic,
    proposed_by,
    count(*)                                                   as votes,
    count(*) filter (where vote = 'FOR')                       as votes_for,
    count(*) filter (where vote = 'AGAINST')                   as votes_against,
    count(*) filter (where vote = 'ABSTAIN')                   as votes_abstain,
    count(*) filter (where versus_management = 'WITH')         as with_management,
    count(*) filter (where versus_management = 'AGAINST')      as against_management,
    sum(shares_voted)                                          as shares_voted
from fct_votes
where filer_kind = 'fund' and fund_id is not null and report_year is not null
group by all
"""


def local_tables(con, folder):
    """Write each table to Parquet. Returns (name, path, local row count)."""
    out = []
    for name in TABLES:
        path = os.path.join(folder, f"{name}.parquet")
        con.execute(f"copy (select * from {name}) to '{path}' (format parquet)")
        rows = con.execute(f"select count(*) from {name}").fetchone()[0]
        out.append((name, path, rows))
    path = os.path.join(folder, f"{SUMMARY_NAME}.parquet")
    con.execute(f"copy ({SUMMARY_SQL}) to '{path}' (format parquet)")
    rows = con.execute(f"select count(*) from read_parquet('{path}')").fetchone()[0]
    out.append((SUMMARY_NAME, path, rows))
    return out


def publish(files):
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT)
    dataset = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)

    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    audit = []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name, path, local_rows in files:
        table_id = f"{PROJECT}.{DATASET}.{name}"
        with open(path, "rb") as handle:
            client.load_table_from_file(handle, table_id, job_config=config).result()
        table = client.get_table(table_id)
        status = "ok" if table.num_rows == local_rows else "MISMATCH"
        audit.append({
            "published_at": stamp, "table_name": name, "local_rows": local_rows,
            "cloud_rows": table.num_rows, "cloud_mb": round(table.num_bytes / 1e6, 1),
            "status": status,
        })
        print(f"  {name:<28}{local_rows:>12,} rows  {table.num_bytes / 1e6:>8.1f} MB  {status}")

    # Keep the check results in the warehouse too, by loading them as a file
    # (the sandbox allows load jobs but not INSERT statements).
    audit_path = os.path.join(os.path.dirname(files[0][1]), "load_audit.csv")
    with open(audit_path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    audit_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1, autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    with open(audit_path, "rb") as handle:
        client.load_table_from_file(handle, f"{PROJECT}.{DATASET}.load_audit",
                                    job_config=audit_config).result()
    return audit


def append_log(audit):
    new_file = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        if new_file:
            writer.writeheader()
        writer.writerows(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="build the files and report sizes, send nothing")
    args = parser.parse_args()

    con = duckdb.connect(LOCAL_DB, read_only=True)
    con.execute("SET memory_limit = '2GB'")
    with tempfile.TemporaryDirectory() as folder:
        files = local_tables(con, folder)
        total = sum(os.path.getsize(p) for _, p, _ in files) / 1e6
        print(f"{len(files)} tables, {sum(r for *_, r in files):,} rows, {total:,.1f} MB as Parquet")
        for name, path, rows in files:
            print(f"  {name:<28}{rows:>12,} rows  {os.path.getsize(path) / 1e6:>8.1f} MB")
        if args.dry_run:
            print("Dry run: nothing was sent.")
            return
        print(f"Publishing to {PROJECT}.{DATASET} ...")
        audit = publish(files)
    append_log(audit)
    sent = sum(row["cloud_mb"] for row in audit)
    bad = [row["table_name"] for row in audit if row["status"] != "ok"]
    print(f"Done: {sent:,.1f} MB in BigQuery. Row counts {'match' if not bad else 'DIFFER for ' + ', '.join(bad)}.")
    print(f"Every publish is logged in {LOG}, to keep track of the 10 GB lifetime allowance.")


if __name__ == "__main__":
    main()
