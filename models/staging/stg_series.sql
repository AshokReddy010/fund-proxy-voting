-- One row per fund named on a filing.
select
    accession                                   as filing_id,
    upper(trim(series_id))                      as fund_id,
    trim(regexp_replace(series_name, '\s+', ' ', 'g')) as fund_name
from {{ source('raw', 'raw_series') }}
where coalesce(trim(series_id), '') <> ''
