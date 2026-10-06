-- Fails if more than 1% of votes could not be matched to a standard value,
-- which would mean a new spelling has appeared that the cleaning rules do not cover.
select pct_vote_unrecognised
from {{ ref('data_quality_summary') }}
where pct_vote_unrecognised > 1
