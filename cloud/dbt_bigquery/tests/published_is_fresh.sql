-- Fails when the curated tables were last published more than 45 days ago,
-- well before the sandbox's 60-day expiry would delete them.
select max(published_at) as last_publish
from {{ source('published', 'load_audit') }}
having timestamp_diff(current_timestamp(), timestamp(max(published_at)), day) > 45
