-- Indicateurs clés sur toute la période couverte.
select
    min(service_date)                                   as date_from,
    max(service_date)                                   as date_to,
    count(distinct service_date)                        as n_days,
    count(*)                                            as n_arrivals,
    count(*) filter (where is_measured)                 as n_measured,
    count(distinct trip_id)                             as n_trips,
    count(distinct station_id)                          as n_stations,
    avg(is_punctual::int)                               as punctuality,
    avg(delay_s)                                        as avg_delay_s,
    quantile_cont(delay_s, 0.9)                         as p90_delay_s,
    avg(is_cancelled::int)                              as cancel_rate,
    count(*) filter (where is_measured)::double / count(*) as coverage
from {{ ref('fct_arrivals') }}
