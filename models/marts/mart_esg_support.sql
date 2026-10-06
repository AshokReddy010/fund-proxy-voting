-- The headline comparison: how often ESG-named funds and other funds vote FOR
-- shareholder proposals on environmental and social topics, by year.
-- Two views of the same question: every vote counted once, and every fund counted once.
with tagged as (

    select *, 'Environment' as topic from {{ ref('fct_fund_es_votes') }} where is_environment
    union all
    select *, 'Social' as topic from {{ ref('fct_fund_es_votes') }} where is_social

),

per_fund as (

    select
        report_year,
        topic,
        is_esg_named,
        fund_id,
        count(*)                                as votes,
        avg(supported::int)                     as support_rate
    from tagged
    group by all

)

select
    report_year,
    topic,
    case when is_esg_named then 'ESG-named funds' else 'Other funds' end as fund_group,
    count(*)                                                    as funds,
    sum(votes)                                                  as votes,
    round(100 * sum(votes * support_rate) / sum(votes), 2)      as pct_for_all_votes,
    round(100 * avg(support_rate), 2)                           as pct_for_average_fund,
    round(100 * median(support_rate), 2)                        as pct_for_median_fund
from per_fund
group by all
order by report_year, topic, fund_group
