-- Dimension ligne : catégorie (IC, IR, RE, S...) et opérateur principal.
select
    line,
    mode(category)              as category,
    mode(operator)              as operator,
    count(distinct (service_date, trip_id)) as n_trips_total
from {{ ref('fct_arrivals') }}
group by line
