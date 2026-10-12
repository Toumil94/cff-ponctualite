-- Évolution jour par jour.
select
    f.service_date,
    d.weekday,
    d.is_weekend,
    count(*)                                as n_arrivals,
    avg(f.is_punctual::int)                 as punctuality,
    avg(f.delay_s)                          as avg_delay_s,
    avg(f.is_cancelled::int)                as cancel_rate
from {{ ref('fct_arrivals') }} f
join {{ ref('dim_date') }} d using (service_date)
group by all
order by f.service_date
