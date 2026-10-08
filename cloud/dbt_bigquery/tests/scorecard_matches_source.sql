-- Reconciliation: the scorecard must carry every fund and every vote it was built from.
with s as (select count(*) as funds, sum(votes) as votes from {{ ref('rpt_fund_scorecard') }}),
     d as (select count(*) as funds from {{ source('published', 'dim_funds') }}),
     v as (select sum(votes) as votes
           from {{ source('published', 'fct_fund_year_topic') }}
           where fund_id in (select fund_id from {{ source('published', 'dim_funds') }}))
select s.funds, d.funds, s.votes, v.votes
from s, d, v
where s.funds <> d.funds or coalesce(s.votes, 0) <> coalesce(v.votes, 0)
