-- Si moins de la moitié des arrivées ont une mesure réelle, le format a sans doute
-- changé : mieux vaut échouer que publier des chiffres faux.
select coverage from {{ ref('rpt_kpis') }} where coverage < 0.5
