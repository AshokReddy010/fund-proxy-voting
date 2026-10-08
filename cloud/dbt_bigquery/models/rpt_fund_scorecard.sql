-- One row per fund: how often it sided with management overall, and how often it
-- backed environmental and social proposals that specialist ESG houses supported.
with overall as (
    select
        fund_id,
        sum(votes)                                                   as votes,
        round(100 * safe_divide(sum(with_management),
                                sum(with_management) + sum(against_management)), 2) as pct_with_management
    from {{ source('published', 'fct_fund_year_topic') }}
    group by fund_id
),

es as (
    select
        fund_id,
        count(*)                                                     as es_votes_on_pro_esg,
        round(100 * avg(if(supported, 1, 0)), 2)                     as pct_backing_pro_esg
    from {{ source('published', 'fct_fund_es_votes') }}
    where direction = 'supports ESG'
      and direction_basis = 'reference votes'
      and not is_reference_house
    group by fund_id
)

select
    f.fund_id,
    f.fund_name,
    f.filer_name                    as fund_house,
    f.is_esg_named,
    o.votes,
    o.pct_with_management,
    e.es_votes_on_pro_esg,
    -- Below 20 votes the rate is too noisy to compare funds on.
    if(e.es_votes_on_pro_esg >= 20, e.pct_backing_pro_esg, null) as pct_backing_pro_esg
from {{ source('published', 'dim_funds') }} as f
left join overall as o using (fund_id)
left join es as e using (fund_id)
