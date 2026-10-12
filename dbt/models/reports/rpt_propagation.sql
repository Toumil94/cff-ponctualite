-- Propagation : retard moyen selon le rang de l'arrêt dans la course.
-- Montre comment un retard s'accumule (ou se résorbe) au fil du trajet.
select
    category,
    least(stop_seq, 20)             as stop_seq,
    count(*)                        as n_measured,
    avg(delay_s)                    as avg_delay_s,
    avg(is_punctual::int)           as punctuality
from {{ ref('fct_arrivals') }}
where is_measured and category in (
    select category from {{ ref('rpt_category') }} order by n_measured desc limit 5
)
group by all
having count(*) >= 200
order by category, stop_seq
