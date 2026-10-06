-- One row of headline quality numbers, so cleaning results can be read without scanning the big table.
select
    count(*)                                                                as votes,
    count(distinct filing_id)                                               as filings_with_votes,
    count(*) filter (where filer_kind = 'fund')                             as fund_votes,
    count(*) filter (where filer_kind = 'manager')                          as manager_votes,
    round(100.0 * count(*) filter (where meeting_date is null) / count(*), 3)   as pct_no_usable_date,
    round(100.0 * count(*) filter (where cusip is null) / count(*), 2)          as pct_no_cusip,
    round(100.0 * count(*) filter (where vote = 'OTHER') / count(*), 3)         as pct_vote_unrecognised,
    round(100.0 * count(*) filter (where vote = 'UNKNOWN') / count(*), 2)       as pct_vote_blank,
    round(100.0 * count(*) filter (where vote = 'NOT VOTED') / count(*), 2)     as pct_not_voted,
    round(100.0 * count(*) filter (where voted_with_management is not null) / count(*), 2) as pct_comparable_to_management,
    round(100.0 * count(*) filter (where voted_with_management) / nullif(count(*) filter (where voted_with_management is not null), 0), 2) as pct_with_management,
    count(*) filter (where is_environment)                                  as environment_votes,
    count(*) filter (where is_social)                                       as social_votes,
    count(*) filter (where proposed_by = 'shareholder')                     as shareholder_proposal_votes
from {{ ref('fct_votes') }}
