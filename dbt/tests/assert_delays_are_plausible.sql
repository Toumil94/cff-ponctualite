-- Un retard mesuré de plus de 6 heures ou une avance de plus d'une heure trahit
-- une erreur de saisie ou de parsing. On tolère quelques cas isolés (moins de 0,1 %).
with bad as (
    select count(*) filter (where delay_s > 6 * 3600 or delay_s < -3600) as n_bad,
           count(*) as n
    from {{ ref('fct_arrivals') }}
    where is_measured
)
select * from bad where n_bad > 0.001 * n
