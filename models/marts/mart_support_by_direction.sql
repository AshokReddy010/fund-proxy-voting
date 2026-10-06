-- The corrected headline. Proposals are split by which way they point, and funds into three groups:
-- specialist ESG houses (the yardstick), ESG-named funds at other houses, and all other funds.
with votes as (

    select
        *,
        case
            when is_reference_house then '1 Specialist ESG houses'
            when is_esg_named then '2 ESG-named funds elsewhere'
            else '3 Other funds'
        end as fund_group
    from {{ ref('fct_fund_es_votes') }}

),

per_fund as (

    select report_year, direction, direction_basis, fund_group, fund_id,
           count(*) as votes, avg(supported::int) as support_rate
    from votes
    group by all

)

select
    report_year,
    direction,
    direction_basis,
    fund_group,
    count(*)                                                as funds,
    sum(votes)                                              as votes,
    round(100 * sum(votes * support_rate) / sum(votes), 2)  as pct_for_all_votes,
    round(100 * avg(support_rate), 2)                       as pct_for_average_fund
from per_fund
group by all
order by direction_basis, direction, report_year, fund_group
