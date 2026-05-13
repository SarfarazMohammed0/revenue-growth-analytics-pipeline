{{ config(materialized='view') }}

-- ============================================================
-- stg_crm_customers
-- Cleans raw CRM exports: trims whitespace, casts types,
-- normalizes country codes, and flags PII fields.
-- Grain: one row per customer_id
-- ============================================================

with source as (
    select * from {{ source('raw', 'raw_crm_customers') }}
),

renamed as (
    select
        cast(customer_id as varchar)                          as customer_id,
        trim(first_name)                                      as first_name,
        trim(last_name)                                       as last_name,
        lower(trim(email))                                    as email,
        cast(signup_date as timestamp)                        as signup_at,
        upper(trim(country))                                  as country_code,
        lower(trim(acquisition_channel))                      as acquisition_channel,
        initcap(segment)                                      as segment,
        case
            when lower(cast(is_active as varchar)) in ('true', '1', 't') then true
            else false
        end                                                   as is_active,
        current_timestamp                                     as _loaded_at
    from source
)

select * from renamed
