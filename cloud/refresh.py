"""Monthly refresh: fetch only new SEC filings, add them, rebuild, and re-publish.

Run from the project folder, with the virtual environment active:
    python cloud\\refresh.py                    the full refresh
    python cloud\\refresh.py --skip-download    rebuild and re-publish without contacting the SEC

Steps
  1. download_votes.py fetches filings it has not seen before (it skips finished ones).
  2. New vote files are appended to raw_votes. Nothing already loaded is read again.
  3. dbt rebuilds the local models and runs their tests.
  4. Result tables and charts are regenerated.
  5. The curated tables are re-published to BigQuery with a row-count audit,
     which also resets the sandbox's 60-day expiry.
  6. dbt rebuilds and tests the BigQuery reporting models.
Each run adds one line to cloud/refresh_log.csv.

Proposals first seen in new filings are labelled "unclear" until the labelling
step (scripts/export_proposals.py, then scripts/label_proposals.py) is re-run.
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

DATA = Path("npx_data")
VOTES = DATA / "votes"
DB = "fund_voting.duckdb"
LOG = Path("cloud") / "refresh_log.csv"
CSV_OPTIONS = "header = true, all_varchar = true, quote = '\"', escape = '\"'"


def step(title):
    print(f"\n=== {title} ===", flush=True)


def run(command, cwd=None):
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def count_filings():
    path = DATA / "filings.csv"
    if not path.exists():
        return 0
    with open(path, newline="", encoding="utf-8") as handle:
        return sum(1 for _ in handle) - 1


def load_new_votes():
    """Append vote files that are not yet in raw_votes. Returns (files, rows) added."""
    con = duckdb.connect(DB)
    con.execute("set memory_limit = '2GB'")
    con.execute(f"set temp_directory = '{(DATA / 'duck_tmp').as_posix()}'")

    # The filing and fund-name lists are small, so they are simply reloaded.
    for table, file in [("raw_filings", "filings.csv"), ("raw_series", "series.csv")]:
        con.execute(f"create or replace table {table} as select * from "
                    f"read_csv('{(DATA / file).as_posix()}', {CSV_OPTIONS})")

    loaded = {row[0] for row in con.execute("select distinct accession from raw_votes").fetchall()}
    new_files = [p for p in sorted(VOTES.glob("*.csv.gz")) if p.name[:-len(".csv.gz")] not in loaded]
    rows = 0
    if new_files:
        before = con.execute("select count(*) from raw_votes").fetchone()[0]
        paths = ", ".join(f"'{p.as_posix()}'" for p in new_files)
        con.execute(f"insert into raw_votes by name select * from read_csv([{paths}], "
                    f"{CSV_OPTIONS}, union_by_name = true)")
        rows = con.execute("select count(*) from raw_votes").fetchone()[0] - before
    total = con.execute("select count(*) from raw_votes").fetchone()[0]
    con.close()
    return len(new_files), rows, total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()
    started = time.time()
    python = sys.executable
    record = {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "new_filings": 0,
              "new_vote_files": 0, "new_votes": 0, "total_votes": 0, "status": "failed"}
    try:
        filings_before = count_filings()
        if not args.skip_download:
            step("1. Fetch new SEC filings")
            run([python, "download_votes.py"])
        record["new_filings"] = count_filings() - filings_before

        step("2. Add new votes to the local warehouse")
        files, rows, total = load_new_votes()
        record.update(new_vote_files=files, new_votes=rows, total_votes=total)
        print(f"{files:,} new vote files, {rows:,} new votes, {total:,} in total")

        step("3. Rebuild and test the local models")
        run(["dbt", "build", "--profiles-dir", "."])

        step("4. Regenerate result tables and charts")
        run([python, os.path.join("scripts", "export_results.py")])
        run([python, os.path.join("scripts", "make_charts.py")])

        step("5. Re-publish curated tables to BigQuery")
        run([python, os.path.join("cloud", "publish_to_bigquery.py")])

        step("6. Rebuild and test the BigQuery reporting models")
        run(["dbt", "build", "--profiles-dir", "."], cwd=os.path.join("cloud", "dbt_bigquery"))
        record["status"] = "ok"
    finally:
        new_file = not LOG.exists()
        with open(LOG, "a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record))
            if new_file:
                writer.writeheader()
            writer.writerow(record)
        minutes = (time.time() - started) / 60
        print(f"\nRefresh {record['status']} in {minutes:.0f} minutes. Logged in {LOG}.")


if __name__ == "__main__":
    main()
