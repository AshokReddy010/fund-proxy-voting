-- The latest publish, one row per table, for a status panel on the dashboard.
select *
from {{ source('published', 'load_audit') }}
where true
qualify published_at = max(published_at) over ()
