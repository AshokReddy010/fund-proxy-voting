"""Save the wording of every environmental and social shareholder proposal, with how funds voted on it.

    python scripts/export_proposals.py

Creates proposals.csv: one row per company, meeting and wording. It includes how a
reference group of specialist ESG fund houses voted, which helps tell which way a proposal points.
"""
import duckdb

REFERENCE = "calvert|green century|domini|trillium|boston common|parnassus|impax|praxis|nia impact|adasina"

con = duckdb.connect("fund_voting.duckdb", read_only=True)
con.execute(f"""
    copy (
        with votes as (
            select *,
                   regexp_matches(lower(coalesce(fund_name, '') || ' ' || filer_name), '{REFERENCE}') as is_reference
            from fct_fund_es_votes
        )
        select
            any_value(issuer_name)                              as company,
            cusip,
            meeting_date,
            report_year,
            regexp_replace(lower(proposal_text), '[^a-z0-9 ]', '', 'g') as wording_key,
            any_value(proposal_text)                            as proposal_text,
            bool_or(is_environment)                             as is_environment,
            bool_or(is_social)                                  as is_social,
            count(*)                                            as fund_votes,
            count(*) filter (where supported)                   as fund_votes_for,
            count(distinct filer_cik)                           as filers,
            count(*) filter (where voted_with_management)       as votes_with_management,
            count(*) filter (where is_esg_named)                as esg_votes,
            count(*) filter (where is_esg_named and supported)  as esg_votes_for,
            count(*) filter (where is_reference)                as reference_votes,
            count(*) filter (where is_reference and supported)  as reference_votes_for
        from votes
        group by cusip, meeting_date, report_year, wording_key
        order by fund_votes desc
    ) to 'proposals.csv' (header, delimiter ',')
""")
rows, ref = con.execute(
    "select count(*), sum(reference_votes) from read_csv('proposals.csv')"
).fetchone()
print(f"Saved {rows:,} proposal rows to proposals.csv ({int(ref):,} votes from the reference group).")
print("Send proposals.csv")
