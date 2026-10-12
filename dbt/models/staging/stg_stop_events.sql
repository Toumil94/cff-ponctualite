-- Un arrêt d'un train dans une gare, tel que publié dans les Ist-Daten.
-- Rôle : typer les colonnes (tout arrive en texte), normaliser les formats de date
-- qui ont varié selon les versions du fichier, et calculer les retards en secondes.

with src as (
    select * from read_parquet('{{ var("raw_glob") }}', union_by_name = true)
),

typed as (
    select
        coalesce(
            try_strptime(trim(BETRIEBSTAG), '%d.%m.%Y'),
            try_strptime(trim(BETRIEBSTAG), '%Y-%m-%d')
        )::date                                         as service_date,
        trim(FAHRT_BEZEICHNER)                          as trip_id,
        trim(BETREIBER_ABK)                             as operator,
        nullif(trim(LINIEN_TEXT), '')                   as line,
        upper(nullif(trim(VERKEHRSMITTEL_TEXT), ''))    as category,
        trim(BPUIC)                                     as station_id,
        trim(HALTESTELLEN_NAME)                         as station_name,
        {{ parse_ts('ANKUNFTSZEIT') }}                  as arr_planned,
        {{ parse_ts('AN_PROGNOSE') }}                   as arr_actual,
        upper(nullif(trim(AN_PROGNOSE_STATUS), ''))     as arr_status,
        {{ parse_ts('ABFAHRTSZEIT') }}                  as dep_planned,
        {{ parse_ts('AB_PROGNOSE') }}                   as dep_actual,
        upper(nullif(trim(AB_PROGNOSE_STATUS), ''))     as dep_status,
        lower(trim(FAELLT_AUS_TF)) = 'true'             as is_cancelled,
        coalesce(lower(trim(DURCHFAHRT_TF)) = 'true', false) as is_pass_through
    from src
)

select
    *,
    date_diff('second', arr_planned, arr_actual)  as arr_delay_s,
    date_diff('second', dep_planned, dep_actual)  as dep_delay_s
from typed
where service_date is not null
  and trip_id is not null
  and not is_pass_through
