-- One row per vote record, cleaned.
-- Filers write the same answer in dozens of ways and dates in a dozen formats,
-- so everything is standardised here and the original text is kept alongside.
with source as (

    select * from {{ source('raw', 'raw_votes') }}
    -- A few filers left the column headings inside their data.
    where upper(coalesce(vote_source, '')) not in ('VOTE SOURCE', 'PROPOSAL SOURCE')
      and upper(coalesce(management_recommendation, '')) not in ('MANAGEMENT RECOMMENDATION', 'VOTE.VOTERECORD.MANAGEMENTRECOMMENDATION')

),

tidied as (

    select
        accession                                           as filing_id,
        trim(issuer_name)                                   as issuer_name,
        case when length(trim(cusip)) = 9 then upper(trim(cusip)) end as cusip,
        case when length(trim(isin)) = 12 then upper(trim(isin)) end  as isin,
        trim(meeting_date)                                  as meeting_date_text,
        trim(vote_description)                              as proposal_text,
        upper(coalesce(categories, ''))                     as categories,
        upper(trim(coalesce(vote_source, '')))              as source_text,
        upper(trim(regexp_replace(coalesce(how_voted, ''), '[\s-]+', ' ', 'g')))                 as vote_text,
        upper(trim(regexp_replace(coalesce(management_recommendation, ''), '[\s-]+', ' ', 'g'))) as rec_text,
        try_cast(shares_voted as double)                    as shares_voted,
        try_cast(shares_on_loan as double)                  as shares_on_loan,
        nullif(upper(trim(series_id)), '')                  as fund_id
    from source

),

standardised as (

    select
        *,
        coalesce(
            try_strptime(meeting_date_text, '%m/%d/%Y'),
            try_strptime(meeting_date_text, '%m/%d/%y'),
            try_strptime(meeting_date_text, '%d-%b-%Y'),
            try_strptime(meeting_date_text, '%d-%b-%y'),
            try_strptime(meeting_date_text, '%Y%m%d')
        )::date as meeting_date_parsed,

        case
            when vote_text in ('FOR', 'F', 'YES', 'FOR ALL') then 'FOR'
            when vote_text in ('AGAINST', 'A', 'NO') then 'AGAINST'
            when vote_text in ('WITHHOLD', 'WITHHELD', 'W', 'WITHOLD', 'WITHHOLD ALL') then 'WITHHOLD'
            when vote_text = 'ABSTAIN' then 'ABSTAIN'
            when vote_text in ('ONE YEAR', '1 YEAR', '1', '1 YEARS', 'ONE', '1YR', '1.0') then '1 YEAR'
            when vote_text in ('TWO YEARS', '2 YEARS', '2 YEAR', 'TWO YEAR', '2', '2.0') then '2 YEARS'
            when vote_text in ('THREE YEARS', '3 YEARS', '3 YEAR', 'THREE YEAR', '3', '3.0') then '3 YEARS'
            when vote_text in ('TAKE NO ACTION', 'TAKENOACTION', 'DO NOT VOTE', 'NO VOTE', 'DID NOT VOTE', 'NOT VOTED',
                               'NONVOTING ITEM', 'NONE', 'N/A', 'NOT APPLICABLE', 'UNVOTED', 'NO ACTION', 'NOT VOTING', 'DID NOTE VOTE',
                               'NON VOTING', 'NO ACTION TAKEN', 'NO VOTES', 'TNA', 'NO SHARES VOTED', 'NULL') then 'NOT VOTED'
            when vote_text = '' then 'UNKNOWN'
            else 'OTHER'
        end as vote,

        -- This column is easy to misread. The SEC form does not record what management
        -- recommended; it records whether the vote was cast FOR or AGAINST that recommendation.
        case
            when rec_text in ('FOR', 'F', 'YES') then 'WITH'
            when rec_text in ('AGAINST', 'A', 'NO') then 'AGAINST'
            else 'NONE'
        end as versus_management,

        case
            when source_text in ('ISSUER', 'MGMT', 'MANAGEMENT') then 'company'
            when source_text = 'SECURITY HOLDER' then 'shareholder'
            else 'unknown'
        end as proposed_by

    from tidied

)

select
    filing_id,
    fund_id,
    issuer_name,
    cusip,
    isin,
    -- Dates outside the period these filings can cover are treated as typing errors.
    case when meeting_date_parsed between date '2023-07-01' and date '2026-12-31' then meeting_date_parsed end as meeting_date,
    proposal_text,
    categories,
    categories like '%ENVIRONMENT OR CLIMATE%'                      as is_environment,
    categories like '%OTHER SOCIAL ISSUES%'
        or categories like '%HUMAN RIGHTS%'
        or categories like '%DIVERSITY%'                            as is_social,
    categories like '%DIRECTOR ELECTIONS%'                          as is_director_election,
    categories like '%SAY-ON-PAY%'                                  as is_say_on_pay,
    categories like '%CORPORATE GOVERNANCE%'
        or categories like '%SHAREHOLDER RIGHTS%'                   as is_governance,
    proposed_by,
    vote,
    versus_management,
    case versus_management when 'WITH' then true when 'AGAINST' then false end as voted_with_management,
    shares_voted,
    shares_on_loan,
    vote_text                                                       as vote_as_filed
from standardised
