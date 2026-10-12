-- La ponctualité est un taux : elle doit rester entre 0 et 1 partout.
select 'kpis' as model, punctuality from {{ ref('rpt_kpis') }} where punctuality not between 0 and 1
union all
select 'daily', punctuality from {{ ref('rpt_daily') }} where punctuality not between 0 and 1
union all
select 'station', punctuality from {{ ref('rpt_station') }} where punctuality not between 0 and 1
