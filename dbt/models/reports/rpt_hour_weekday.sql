-- Carte de chaleur : ponctualité par jour de la semaine et heure d'arrivée prévue.
select
    weekday,
    hour,
    count(*) filter (where is_measured)     as n_measured,
    avg(is_punctual::int)                   as punctuality,
    avg(delay_s)                            as avg_delay_s
from {{ ref('fct_arrivals') }}
where hour between 5 and 23
group by all
order by weekday, hour
