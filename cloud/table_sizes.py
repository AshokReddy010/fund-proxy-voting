"""Measure the tables in the local warehouse, to decide what fits in BigQuery's free tier.

Run from the project folder:  python cloud\\table_sizes.py
It only reads the database. It writes small temporary Parquet files to measure
their size, then deletes them.
"""
import os
import tempfile

import duckdb

DB = "fund_voting.duckdb"


def main():
    con = duckdb.connect(DB, read_only=True)
    con.execute("SET memory_limit = '2GB'")
    tables = con.execute("""
        select table_name, table_type
        from information_schema.tables
        where table_schema = 'main'
        order by table_name
    """).fetchall()

    print(f"{'table':<32}{'type':<12}{'rows':>14}{'columns':>9}{'parquet MB':>12}")
    with tempfile.TemporaryDirectory() as tmp:
        for name, kind in tables:
            rows = con.execute(f'select count(*) from "{name}"').fetchone()[0]
            cols = len(con.execute(f'select * from "{name}" limit 0').description)
            size = ""
            if kind == "BASE TABLE" and rows < 20_000_000:
                path = os.path.join(tmp, f"{name}.parquet")
                con.execute(f"copy \"{name}\" to '{path}' (format parquet)")
                size = f"{os.path.getsize(path) / 1e6:,.1f}"
                os.remove(path)
            print(f"{name:<32}{kind:<12}{rows:>14,}{cols:>9}{size:>12}")


if __name__ == "__main__":
    main()
