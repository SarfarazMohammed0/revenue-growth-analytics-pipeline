{{ config(materialized='view') }}

-- ============================================================
-- stg_payments
-- Cleans payment records and converts amounts to USD using a
-- simple static FX table. In production this would join an
-- exchange_rates dimension on payment_date.
-- Grain: one row per payment_id
-- ============================================================

with source as (
    select * from {{ source('raw', 'raw_payments') }}
),

fx as (
    select 'USD' as currency, 1.00 as usd_rate union all
    select 'EUR', 1.08 union all
    select 'GBP', 1.27 union all
    select 'INR', 0.012 union all
    select 'JPY', 0.0067
),

renamed as (
    select
        cast(p.payment_id as varchar)              as payment_id,
        cast(p.customer_id as varchar)             as customer_id,
        cast(p.payment_timestamp as timestamp)     as paid_at,
        cast(p.amount as decimal(12,2))            as amount_local,
        upper(trim(p.currency))                    as currency,
        cast(p.amount as decimal(12,2)) * fx.usd_rate
                                                   as amount_usd,
        lower(trim(p.status))                      as status,
        upper(substr(p.plan,1,1)) || lower(substr(p.plan,2)) as plan,
        current_timestamp                          as _loaded_at
    from source p
    left join fx on upper(trim(p.currency)) = fx.currency
)

select * from renamed
