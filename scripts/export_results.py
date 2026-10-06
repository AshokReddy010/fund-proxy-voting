"""Save the result tables as small CSV files, so the findings can be read and charted without the full database.

    python scripts/export_results.py
"""
from pathlib import Path

import duckdb

OUT = Path("reports/tables")
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("fund_voting.duckdb", read_only=True)

TABLES = {
    "data_quality_summary": "select * from data_quality_summary",
    "votes_by_year_and_filer_kind": "select report_year, filer_kind, count(*) as votes from fct_votes group by all order by 1, 2",
    "vote_values": "select vote, count(*) as votes from fct_votes group by all order by votes desc",
    "label_coverage": """
        select direction, direction_basis, count(*) as fund_votes, count(distinct matched_proposal_id) as proposals
        from fct_fund_es_votes group by all order by fund_votes desc""",
    "support_by_direction": "select * from mart_support_by_direction",
    "sibling_comparison_by_year": """
        select direction, direction_basis, report_year, count(*) as proposals_compared,
               round(100 * avg(esg_support), 2) as esg_pct_for,
               round(100 * avg(other_support), 2) as siblings_pct_for,
               round(100.0 * count(*) filter (where outcome = 'same as siblings') / count(*), 2) as pct_same,
               round(100.0 * count(*) filter (where outcome = 'ESG fund more supportive') / count(*), 2) as pct_esg_more,
               round(100.0 * count(*) filter (where outcome = 'ESG fund less supportive') / count(*), 2) as pct_esg_less
        from mart_sibling_comparison group by all order by 1, 2, 3""",
    "sibling_comparison_by_house": """
        select filer_name, count(*) as proposals_compared,
               round(100 * avg(esg_support), 1) as esg_pct_for,
               round(100 * avg(other_support), 1) as siblings_pct_for,
               round(100.0 * count(*) filter (where outcome = 'same as siblings') / count(*), 1) as pct_same
        from mart_sibling_comparison
        where direction = 'supports ESG' and direction_basis = 'reference votes'
        group by all having count(*) >= 30 order by proposals_compared desc""",
    "esg_named_fund_support": """
        select fund_id, fund_name, filer_name, count(*) as votes, round(100 * avg(supported::int), 1) as pct_for
        from fct_fund_es_votes
        where is_esg_named and not is_reference_house
          and direction = 'supports ESG' and direction_basis = 'reference votes'
        group by all having count(*) >= 20 order by pct_for, votes desc""",
}

for name, sql in TABLES.items():
    frame = con.execute(sql).fetch_df()
    frame.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:<32} {len(frame):>6,} rows")
print(f"Saved to {OUT}")
