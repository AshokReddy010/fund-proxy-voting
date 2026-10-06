{# Passes when no two rows share the same values in the listed columns. #}
{% test dbt_utils_free_unique_combination(model, columns) %}
select {{ columns }}, count(*) as copies
from {{ model }}
group by {{ columns }}
having count(*) > 1
{% endtest %}
