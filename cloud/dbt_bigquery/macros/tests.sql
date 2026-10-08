{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as copies
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

{% test between(model, column_name, low, high) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ low }} or {{ column_name }} > {{ high }}
{% endtest %}
