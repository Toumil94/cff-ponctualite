-- Ponctualité par gare. Seules les gares avec assez d'arrivées mesurées sont gardées
-- pour éviter les classements trompeurs sur de petits volumes.
with s as (
    select
        f.station_id,
        s.station_name,
        count(*) filter (where f.is_measured)   as n_measured,
        avg(f.is_punctual::int)                 as punctuality,
        avg(f.delay_s)                          as avg_delay_s,
        quantile_cont(f.delay_s, 0.9)           as p90_delay_s,
        avg(f.is_cancelled::int)                as cancel_rate,
        count(distinct f.line)                  as n_lines
    from {{ ref('fct_arrivals') }} f
    join {{ ref('dim_station') }} s using (station_id)
    group by all
)
select
    *,
    rank() over (order by punctuality desc) as rank_punctuality
from s
where n_measured >= (select greatest(100, quantile_cont(n_measured, 0.5)) from s)
