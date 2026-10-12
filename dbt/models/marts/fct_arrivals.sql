-- Table de faits : une ligne par arrivée d'un train dans une gare.
-- Grain : (service_date, trip_id, station_id). La gare de départ n'a pas d'arrivée et est exclue.
-- Ponctualité selon la définition des CFF : moins de 3 minutes de retard à l'arrivée.

with events as (
    select
        *,
        row_number() over (
            partition by service_date, trip_id
            order by coalesce(arr_planned, dep_planned)
        ) as stop_seq
    from {{ ref('stg_stop_events') }}
),

dedup as (
    -- Les fichiers contiennent parfois un même arrêt en double : on garde le plus complet.
    select *
    from events
    qualify row_number() over (
        partition by service_date, trip_id, station_id, arr_planned
        order by (arr_status = 'REAL') desc, arr_actual desc nulls last
    ) = 1
)

select
    service_date,
    trip_id,
    operator,
    coalesce(line, category)                                as line,
    coalesce(category, 'AUTRE')                             as category,
    station_id,
    station_name,
    stop_seq,
    arr_planned,
    arr_actual,
    arr_status,
    is_cancelled,
    -- Un retard n'est mesuré que si le passage a été réellement enregistré (statut REAL).
    arr_status = 'REAL' and not is_cancelled                as is_measured,
    case when arr_status = 'REAL' and not is_cancelled then arr_delay_s end as delay_s,
    case when arr_status = 'REAL' and not is_cancelled
         then arr_delay_s < {{ var('punctual_threshold_s') }} end         as is_punctual,
    extract(hour from arr_planned)::int                     as hour,
    isodow(service_date)                                    as weekday
from dedup
where arr_planned is not null
