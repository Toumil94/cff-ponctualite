-- Essaie successivement les formats de date vus dans les différentes versions des Ist-Daten.
{% macro parse_ts(col) %}
{% set ts_formats = ['%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'] %}

    coalesce(
        {%- for f in ts_formats %}
        try_strptime(nullif(trim({{ col }}), ''), '{{ f }}'){{ "," if not loop.last }}
        {%- endfor %}
    )
{%- endmacro %}
