"""Load the downloaded voting records into one database file and write a summary.

Run from the project folder:
    pip install duckdb
    python load_raw.py

It creates fund_voting.duckdb (the database) and profile.txt (a summary to send).
The first part reads about 73 million rows, so allow 15 to 40 minutes on an older laptop.
"""
import time
from pathlib import Path

import duckdb

DATA = Path("npx_data")
DB = "fund_voting.duckdb"

started = time.time()
con = duckdb.connect(DB)
con.execute("set memory_limit = '2GB'")
con.execute("set threads = 2")
con.execute("set preserve_insertion_order = false")
con.execute(f"set temp_directory = '{(DATA / 'duck_tmp').as_posix()}'")

print("Loading filings and fund names...")
for table, file in [("raw_filings", "filings.csv"), ("raw_series", "series.csv")]:
    con.execute(
        f"create or replace table {table} as select * from read_csv('{(DATA / file).as_posix()}', "
        "header = true, all_varchar = true, quote = '\"', escape = '\"')"
    )

print("Loading votes (the long part)...")
con.execute(
    "create or replace table raw_votes as select * from read_csv("
    f"'{(DATA / 'votes').as_posix()}/*.csv.gz', header = true, all_varchar = true, "
    "quote = '\"', escape = '\"', union_by_name = true, parallel = false)"
)
print(f"Loaded in {(time.time() - started) / 60:.1f} minutes. Writing the summary...")

SECTIONS = [
    ("Row counts", """
        select 'filings' as item, count(*) as n from raw_filings
        union all select 'fund names', count(*) from raw_series
        union all select 'votes', count(*) from raw_votes
        union all select 'filings that have votes', count(distinct accession) from raw_votes"""),
    ("Filings by form, filer type and report type", """
        select form_type, registrant_type, report_type, count(*) as filings
        from raw_filings group by all order by filings desc"""),
    ("Filings by download status", "select status, count(*) as filings from raw_filings group by all order by filings desc"),
    ("Filings by reporting year", "select report_year, count(*) as filings from raw_filings group by all order by filings desc limit 12"),
    ("Votes by filer type", """
        select f.registrant_type, count(*) as votes, count(distinct v.accession) as filings
        from raw_votes v left join raw_filings f using (accession) group by all order by votes desc"""),
    ("Votes by topic category (as labelled in the filings)", "select categories, count(*) as votes from raw_votes group by all order by votes desc limit 40"),
    ("How voted: the different spellings", "select how_voted, count(*) as votes from raw_votes group by all order by votes desc limit 40"),
    ("Management recommendation: the different spellings", "select management_recommendation, count(*) as votes from raw_votes group by all order by votes desc limit 30"),
    ("Who proposed it", "select vote_source, count(*) as votes from raw_votes group by all order by votes desc limit 10"),
    ("Share of rows with a blank in each column", """
        select round(100.0 * count(*) filter (where coalesce(issuer_name, '') = '') / count(*), 2) as issuer_name,
               round(100.0 * count(*) filter (where coalesce(cusip, '') in ('', '-', 'N/A')) / count(*), 2) as cusip,
               round(100.0 * count(*) filter (where coalesce(isin, '') in ('', '-', 'N/A')) / count(*), 2) as isin,
               round(100.0 * count(*) filter (where coalesce(meeting_date, '') = '') / count(*), 2) as meeting_date,
               round(100.0 * count(*) filter (where coalesce(vote_description, '') = '') / count(*), 2) as description,
               round(100.0 * count(*) filter (where coalesce(categories, '') = '') / count(*), 2) as categories,
               round(100.0 * count(*) filter (where coalesce(how_voted, '') = '') / count(*), 2) as how_voted,
               round(100.0 * count(*) filter (where coalesce(management_recommendation, '') = '') / count(*), 2) as mgmt_rec,
               round(100.0 * count(*) filter (where coalesce(series_id, '') = '') / count(*), 2) as series_id
        from raw_votes"""),
    ("Meeting date formats", """
        select regexp_replace(regexp_replace(meeting_date, '[0-9]', '9', 'g'), '[A-Za-z]', 'a', 'g') as pattern, count(*) as votes
        from raw_votes group by all order by votes desc limit 12"""),
    ("Largest filings by votes", """
        select f.company, f.registrant_type, f.report_year, count(*) as votes
        from raw_votes v left join raw_filings f using (accession) group by all order by votes desc limit 25"""),
    ("Fund names: how many look ESG-labelled", """
        select count(*) as fund_rows, count(distinct series_id) as distinct_funds,
               count(distinct series_id) filter (where regexp_matches(lower(series_name),
                   'esg|sustainab|climate|social|responsib|impact|green|carbon|environment|clean energy|low.carbon|fossil|paris')) as esg_named_funds
        from raw_series"""),
    ("Examples of ESG-labelled fund names", """
        select distinct series_name from raw_series
        where regexp_matches(lower(series_name), 'esg|sustainab|climate|social|responsib|impact|green|carbon|environment|clean energy|fossil|paris')
        order by series_name limit 40"""),
    ("Fund votes that carry a fund ID, and whether the ID has a name", """
        select count(*) as fund_votes,
               count(*) filter (where coalesce(v.series_id, '') <> '') as with_series_id,
               count(*) filter (where s.series_id is not null) as with_matching_name
        from raw_votes v
        join raw_filings f on f.accession = v.accession and f.registrant_type = 'RMIC'
        left join (select distinct accession, series_id from raw_series) s
               on s.accession = v.accession and s.series_id = v.series_id"""),
    ("Environment and social proposals: 15 random examples", """
        select issuer_name, vote_source, how_voted, management_recommendation, left(vote_description, 150) as description
        from raw_votes where categories ilike '%ENVIRONMENT%' or categories ilike '%SOCIAL%'
        using sample 15 rows"""),
    ("Random rows", """
        select issuer_name, cusip, meeting_date, left(vote_description, 90) as description, categories, how_voted,
               management_recommendation, series_id
        from raw_votes using sample 12 rows"""),
]

lines = []
for title, sql in SECTIONS:
    lines += ["", "=" * 100, title, "=" * 100]
    try:
        frame = con.execute(sql).fetch_df()
        lines.append(frame.to_string(index=False, max_colwidth=160))
    except Exception as error:
        lines.append(f"(could not run: {error})")

log = DATA / "log.txt"
if log.exists():
    problems = log.read_text(encoding="utf-8", errors="replace").splitlines()
    lines += ["", "=" * 100, f"Download problems logged: {len(problems)}", "=" * 100] + problems[:40]

Path("profile.txt").write_text("\n".join(lines), encoding="utf-8")
con.close()
size = Path(DB).stat().st_size / 1e9
print(f"Done in {(time.time() - started) / 60:.1f} minutes. Database size {size:.2f} GB.")
print("Send the file profile.txt")
