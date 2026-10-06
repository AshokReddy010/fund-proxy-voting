"""Print the ESG results after proposals have been sorted by direction.

    python show_esg.py > esg_results.txt
"""
import duckdb
import pandas as pd

pd.set_option("display.width", 220)
con = duckdb.connect("fund_voting.duckdb", read_only=True)


def show(title, sql):
    print("\n" + "=" * 90 + "\n" + title + "\n" + "=" * 90)
    print(con.execute(sql).fetch_df().to_string(index=False))


show("How many fund votes got a label",
     "select direction, direction_basis, count(*) as fund_votes, count(distinct matched_proposal_id) as proposals, "
     "round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_votes from fct_fund_es_votes group by all order by fund_votes desc")
show("Headline: support by proposal direction and fund group (labels decided by reference votes)",
     "select report_year, direction, fund_group, funds, votes, pct_for_all_votes, pct_for_average_fund "
     "from mart_support_by_direction where direction_basis = 'reference votes' order by direction, report_year, fund_group")
show("Same, for proposals labelled by wording only (less certain)",
     "select report_year, direction, fund_group, funds, votes, pct_for_all_votes "
     "from mart_support_by_direction where direction_basis = 'wording only' order by direction, report_year, fund_group")
show("Same company, same proposal: ESG-named funds against their siblings, by direction",
     "select direction, report_year, count(*) as proposals_compared, "
     "round(100 * avg(esg_support), 2) as esg_pct_for, round(100 * avg(other_support), 2) as siblings_pct_for, "
     "round(100.0 * count(*) filter (where outcome = 'same as siblings') / count(*), 2) as pct_same, "
     "round(100.0 * count(*) filter (where outcome = 'ESG fund more supportive') / count(*), 2) as pct_esg_more, "
     "round(100.0 * count(*) filter (where outcome = 'ESG fund less supportive') / count(*), 2) as pct_esg_less "
     "from mart_sibling_comparison where direction_basis = 'reference votes' group by all order by 1, 2")
show("Fund houses on proposals the specialists backed: ESG-named funds against siblings (30+ proposals)",
     "select filer_name, count(*) as proposals_compared, round(100 * avg(esg_support), 1) as esg_pct_for, "
     "round(100 * avg(other_support), 1) as siblings_pct_for, "
     "round(100.0 * count(*) filter (where outcome = 'same as siblings') / count(*), 1) as pct_same "
     "from mart_sibling_comparison where direction = 'supports ESG' and direction_basis = 'reference votes' "
     "group by all having count(*) >= 30 order by proposals_compared desc limit 40")
show("ESG-named funds (not specialist houses) on proposals the specialists backed: lowest support (40+ votes)",
     "select fund_name, filer_name, count(*) as votes, round(100 * avg(supported::int), 1) as pct_for from fct_fund_es_votes "
     "where is_esg_named and not is_reference_house and direction = 'supports ESG' and direction_basis = 'reference votes' "
     "group by all having count(*) >= 40 order by pct_for, votes desc limit 25")
show("Same: highest support (40+ votes)",
     "select fund_name, filer_name, count(*) as votes, round(100 * avg(supported::int), 1) as pct_for from fct_fund_es_votes "
     "where is_esg_named and not is_reference_house and direction = 'supports ESG' and direction_basis = 'reference votes' "
     "group by all having count(*) >= 40 order by pct_for desc, votes desc limit 25")
show("Distribution: how many ESG-named funds fall in each support band on backed proposals (20+ votes)",
     "with f as (select fund_id, avg(supported::int) as s from fct_fund_es_votes where is_esg_named and not is_reference_house "
     "and direction = 'supports ESG' and direction_basis = 'reference votes' group by all having count(*) >= 20) "
     "select case when s < 0.1 then 'a) under 10%' when s < 0.25 then 'b) 10 to 25%' when s < 0.5 then 'c) 25 to 50%' "
     "when s < 0.75 then 'd) 50 to 75%' else 'e) 75% and over' end as support_band, count(*) as funds from f group by all order by 1")
