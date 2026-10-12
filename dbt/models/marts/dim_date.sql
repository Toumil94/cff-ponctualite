-- Dimension calendrier sur la période couverte.
select
    service_date,
    isodow(service_date)                        as weekday,
    isodow(service_date) >= 6                   as is_weekend,
    strftime(service_date, '%Y-%m')             as month
from (select distinct service_date from {{ ref('fct_arrivals') }})
