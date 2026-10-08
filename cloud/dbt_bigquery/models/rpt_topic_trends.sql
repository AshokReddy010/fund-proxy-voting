-- How funds vote on each topic, per year, built from all 73.8 million votes.
select
    report_year,
    topic,
    proposed_by,
    count(distinct fund_id)                                          as funds,
    sum(votes)                                                       as votes,
    round(100 * safe_divide(sum(votes_for), sum(votes)), 2)          as pct_for,
    round(100 * safe_divide(sum(with_management),
                            sum(with_management) + sum(against_management)), 2) as pct_with_management
from {{ source('published', 'fct_fund_year_topic') }}
group by report_year, topic, proposed_by
