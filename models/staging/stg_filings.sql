-- One row per filing, with typed columns and plain-language filer and report kinds.
select
    accession                                   as filing_id,
    form_type,
    form_type = 'N-PX/A'                        as is_amendment,
    cik                                         as filer_cik,
    trim(company)                               as filer_name,
    try_cast(date_filed as date)                as filed_date,
    case registrant_type
        when 'RMIC' then 'fund'
        when 'IM' then 'manager'
        else 'unknown'
    end                                         as filer_kind,
    case
        when report_type ilike '%notice%' then 'notice'
        when report_type ilike '%combination%' then 'combination'
        when report_type ilike '%voting%' then 'voting'
        else 'unknown'
    end                                         as report_kind,
    try_cast(report_year as integer)            as report_year,
    try_strptime(period_of_report, '%m/%d/%Y')::date as period_end_date,
    try_cast(series_count as integer)           as series_count,
    status                                      as download_status
from {{ source('raw', 'raw_filings') }}
