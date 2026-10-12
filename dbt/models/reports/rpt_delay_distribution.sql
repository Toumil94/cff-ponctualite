-- Répartition des retards à l'arrivée, par tranches.
with b as (
    select
        case
            when delay_s < 0    then '0_avance'
            when delay_s < 60   then '1_moins_1min'
            when delay_s < 180  then '2_1_a_3min'
            when delay_s < 300  then '3_3_a_5min'
            when delay_s < 600  then '4_5_a_10min'
            when delay_s < 900  then '5_10_a_15min'
            else                     '6_plus_15min'
        end as bucket
    from {{ ref('fct_arrivals') }}
    where is_measured
)
select bucket, count(*) as n, count(*)::double / sum(count(*)) over () as share
from b
group by bucket
order by bucket
