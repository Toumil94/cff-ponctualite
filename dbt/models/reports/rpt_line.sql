-- Ponctualité par ligne.
select
    f.line,
    l.category,
    count(*) filter (where f.is_measured)   as n_measured,
    count(distinct (f.service_date, f.trip_id))               as n_trips,
    avg(f.is_punctual::int)                 as punctuality,
    avg(f.delay_s)                          as avg_delay_s,
    avg(f.is_cancelled::int)                as cancel_rate
from {{ ref('fct_arrivals') }} f
join {{ ref('dim_line') }} l using (line)
group by all
having count(*) filter (where f.is_measured) >= 300
order by n_measured desc
