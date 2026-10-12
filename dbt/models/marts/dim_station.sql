-- Dimension gare : un identifiant UIC, le nom le plus fréquent et le volume observé.
select
    station_id,
    mode(station_name)          as station_name,
    count(*)                    as n_arrivals_total
from {{ ref('fct_arrivals') }}
group by station_id
