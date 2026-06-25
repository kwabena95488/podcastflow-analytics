{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {%- if target.name == 'prod' -%}
            {%- if custom_schema_name == 'bronze' -%}
                bronze
            {%- elif custom_schema_name == 'silver' -%}
                silver  
            {%- elif custom_schema_name == 'gold' -%}
                gold
            {%- elif custom_schema_name == 'dbt_artifacts' -%}
                dbt_artifacts
            {%- elif custom_schema_name == 'streaming' -%}
                streaming
            {%- elif custom_schema_name == 'external' -%}
                external
            {%- else -%}
                {{ custom_schema_name }}
            {%- endif -%}
        {%- else -%}
            {%- if custom_schema_name == 'bronze' -%}
                bronze
            {%- elif custom_schema_name == 'silver' -%}
                silver
            {%- elif custom_schema_name == 'gold' -%}
                gold
            {%- elif custom_schema_name == 'dbt_artifacts' -%}
                dbt_artifacts
            {%- elif custom_schema_name == 'streaming' -%}
                streaming
            {%- elif custom_schema_name == 'external' -%}
                external
            {%- else -%}
                {{ default_schema }}_{{ custom_schema_name }}
            {%- endif -%}
        {%- endif -%}
    {%- endif -%}

{%- endmacro %} 