{# Use the schema names exactly as written in dbt_project.yml (staging, core, reporting)
   instead of dbt's default "<your_dev_schema>_staging". #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}