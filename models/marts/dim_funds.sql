-- One row per fund, with its most recent name and a label for funds marketed on ESG themes.
-- The label is read from the fund's name. That is an approximation: a fund can follow
-- ESG rules without saying so in its name, and this label will miss it.
with named as (

    select
        s.fund_id,
        s.fund_name,
        f.filer_cik,
        f.filer_name,
        f.report_year,
        f.filed_date
    from {{ ref('stg_series') }} as s
    inner join {{ ref('stg_filings') }} as f using (filing_id)

),

latest as (

    select
        fund_id,
        arg_max(fund_name, filed_date)      as fund_name,
        arg_max(filer_name, filed_date)     as filer_name,
        arg_max(filer_cik, filed_date)      as filer_cik,
        count(distinct fund_name)           as names_used,
        min(report_year)                    as first_report_year,
        max(report_year)                    as last_report_year
    from named
    group by fund_id

)

select
    *,
    regexp_matches(
        lower(fund_name),
        '\b(esg|sustainab\w*|climate|socially|social justice|social choice|responsib\w*|responsive|impact|green|carbon|environmental\w*|clean energy|fossil|paris)\b'
    ) as is_esg_named
from latest
