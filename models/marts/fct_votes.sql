-- The cleaned votes saved as a table, joined to their filing, so later models are fast.
-- Notice-only filings carry no votes, so only voting and combination reports appear here.
select
    v.*,
    f.filer_kind,
    f.filer_name,
    f.report_year,
    f.is_amendment
from {{ ref('stg_votes') }} as v
inner join {{ ref('stg_filings') }} as f using (filing_id)
