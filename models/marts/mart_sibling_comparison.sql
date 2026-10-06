-- A fairer test: ESG-named funds against ordinary funds run by the SAME company,
-- voting on the SAME proposal. If an ESG label changes how a fund votes,
-- it should show up as a gap between a fund and its own siblings.
with per_proposal as (

    select
        filing_id,
        proposal_key,
        any_value(filer_name)                                           as filer_name,
        any_value(report_year)                                          as report_year,
        any_value(direction)                                            as direction,
        any_value(direction_basis)                                      as direction_basis,
        count(*) filter (where is_esg_named)                            as esg_funds,
        count(*) filter (where not is_esg_named)                        as other_funds,
        avg(supported::int) filter (where is_esg_named)                 as esg_support,
        avg(supported::int) filter (where not is_esg_named)             as other_support
    from {{ ref('fct_fund_es_votes') }}
    -- Specialist houses are the yardstick, so they are not compared with themselves.
    where not is_reference_house
    group by filing_id, proposal_key

)

select
    filing_id,
    proposal_key,
    filer_name,
    report_year,
    direction,
    direction_basis,
    esg_funds,
    other_funds,
    esg_support,
    other_support,
    esg_support - other_support                                         as support_gap,
    case
        when round(esg_support) = round(other_support) then 'same as siblings'
        when esg_support > other_support then 'ESG fund more supportive'
        else 'ESG fund less supportive'
    end                                                                 as outcome
from per_proposal
where esg_funds > 0 and other_funds > 0
