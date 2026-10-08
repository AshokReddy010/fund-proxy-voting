-- Per fund house and year: do its ESG-named funds back pro-ESG proposals more than
-- its other funds do? Only houses with both kinds of fund voting are kept.
with votes as (
    select filer_name as fund_house, report_year, is_esg_named, supported
    from {{ source('published', 'fct_fund_es_votes') }}
    where direction = 'supports ESG'
      and direction_basis = 'reference votes'
      and not is_reference_house
),

by_group as (
    select
        fund_house,
        report_year,
        countif(is_esg_named)                                        as esg_named_votes,
        countif(not is_esg_named)                                    as other_votes,
        round(100 * safe_divide(countif(is_esg_named and supported), countif(is_esg_named)), 2)         as pct_esg_named_for,
        round(100 * safe_divide(countif(not is_esg_named and supported), countif(not is_esg_named)), 2) as pct_other_for
    from votes
    group by fund_house, report_year
)

select
    *,
    round(pct_esg_named_for - pct_other_for, 2) as gap_points
from by_group
where esg_named_votes >= 20 and other_votes >= 20
