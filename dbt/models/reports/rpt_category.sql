-- Ponctualité par catégorie de train (IC, IR, RE, S...).
select
    category,
    count(*) filter (where is_measured)     as n_measured,
    count(distinct trip_id)                 as n_trips,
    avg(is_punctual::int)                   as punctuality,
    avg(delay_s)                            as avg_delay_s,
    quantile_cont(delay_s, 0.9)             as p90_delay_s,
    avg(is_cancelled::int)                  as cancel_rate
from {{ ref('fct_arrivals') }}
group by category
having count(*) filter (where is_measured) >= 500
order by n_measured desc
