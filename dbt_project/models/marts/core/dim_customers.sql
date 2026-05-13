{{ config(materialized='table') }}

-- ============================================================
-- dim_customers
-- Customer dimension. SCD Type 1 (overwrites on change).
-- Adds a surrogate key for join performance and derived
-- attributes used heavily by KPI marts.
-- Grain: one row per customer
-- ============================================================

with customers as (
    select * from {{ ref('stg_crm_customers') }}
),

enriched as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk,
        customer_id,
        first_name,
        last_name,
        email,
        signup_at,
        date_trunc('day', signup_at)            as signup_date,
        date_trunc('month', signup_at)          as signup_month,
        country_code,
        acquisition_channel,
        segment,
        case
            when segment in ('Pro', 'Business', 'Enterprise') then true
            else false
        end                                     as is_paying,
        is_active,
        datediff('day', signup_at, current_timestamp) as days_since_signup
    from customers
)

select * from enriched
