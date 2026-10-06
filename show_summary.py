"""Print the headline data quality numbers after `dbt build`.

    python show_summary.py
"""
import duckdb

con = duckdb.connect("fund_voting.duckdb", read_only=True)
row = con.execute("select * from data_quality_summary").fetch_df().iloc[0]
for name, value in row.items():
    print(f"{name:<32} {value:>16,}" if isinstance(value, (int, float)) else f"{name:<32} {value}")
print()
print(con.execute(
    "select vote, count(*) as votes from fct_votes group by all order by votes desc"
).fetch_df().to_string(index=False))
print()
print(con.execute(
    "select vote_as_filed, count(*) as votes from fct_votes where vote = 'OTHER' group by all order by votes desc limit 25"
).fetch_df().to_string(index=False))
print()
print(con.execute(
    "select report_year, filer_kind, count(*) as votes from fct_votes group by all order by 1, 2"
).fetch_df().to_string(index=False))
