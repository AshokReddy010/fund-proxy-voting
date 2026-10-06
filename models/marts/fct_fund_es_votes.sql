-- Fund votes on shareholder proposals about environmental or social topics:
-- one row per fund, per proposal, per reporting year.
--
-- Three things are settled here:
--   1. If a filer sent a corrected filing for the same fund and year, only the latest one counts.
--   2. If a fund split its shares between answers, the answer with the most shares counts.
--   3. A proposal is identified by company, meeting date and its wording within one filing.
with filings as (

    select filing_id, filer_cik, filer_name, report_year, filed_date
    from {{ ref('stg_filings') }}
    where filer_kind = 'fund' and report_year is not null

),

votes as (

    select
        v.filing_id,
        v.fund_id,
        f.filer_cik,
        f.filer_name,
        f.report_year,
        f.filed_date,
        v.issuer_name,
        v.cusip,
        v.meeting_date,
        v.proposal_text,
        coalesce(v.cusip, upper(v.issuer_name)) || '|' || coalesce(cast(v.meeting_date as varchar), '') || '|'
            || md5(regexp_replace(lower(v.proposal_text), '[^a-z0-9]', '', 'g'))   as proposal_key,
        v.is_environment,
        v.is_social,
        v.vote,
        v.voted_with_management,
        coalesce(v.shares_voted, 0)                                                 as shares_voted
    from {{ ref('fct_votes') }} as v
    inner join filings as f using (filing_id)
    where v.fund_id is not null
      and v.proposed_by = 'shareholder'
      and (v.is_environment or v.is_social)
      and v.vote in ('FOR', 'AGAINST', 'ABSTAIN', 'WITHHOLD')

),

latest_filing as (

    select filer_cik, report_year, fund_id, arg_max(filing_id, filed_date) as filing_id
    from votes
    group by all

),

one_answer as (

    select
        v.filing_id,
        v.fund_id,
        v.proposal_key,
        any_value(v.filer_cik)                      as filer_cik,
        any_value(v.filer_name)                     as filer_name,
        any_value(v.report_year)                    as report_year,
        any_value(v.issuer_name)                    as issuer_name,
        any_value(v.cusip)                          as cusip,
        any_value(v.meeting_date)                   as meeting_date,
        any_value(v.proposal_text)                  as proposal_text,
        bool_or(v.is_environment)                   as is_environment,
        bool_or(v.is_social)                        as is_social,
        arg_max(v.vote, v.shares_voted)             as vote,
        bool_or(v.voted_with_management)            as voted_with_management
    from votes as v
    inner join latest_filing as l using (filer_cik, report_year, fund_id, filing_id)
    group by v.filing_id, v.fund_id, v.proposal_key

)

select
    a.*,
    a.vote = 'FOR'                              as supported,
    coalesce(d.is_esg_named, false)             as is_esg_named,
    d.fund_name,
    -- Specialist ESG fund houses. Their votes are the yardstick for which way a proposal points,
    -- so they are kept apart from the funds being measured.
    regexp_matches(
        lower(coalesce(d.fund_name, '') || ' ' || a.filer_name),
        'calvert|green century|domini|trillium|boston common|parnassus|impax|praxis|nia impact|adasina'
    )                                           as is_reference_house,
    l.proposal_id                               as matched_proposal_id,
    coalesce(l.direction, 'unclear')            as direction,
    coalesce(l.basis, 'not labelled')           as direction_basis
from one_answer as a
left join {{ ref('dim_funds') }} as d using (fund_id)
left join {{ ref('proposal_labels') }} as l
    on  l.cusip is not distinct from a.cusip
    and l.meeting_date is not distinct from a.meeting_date
    and l.report_year = a.report_year
    and l.wording_key = regexp_replace(lower(a.proposal_text), '[^a-z0-9 ]', '', 'g')
