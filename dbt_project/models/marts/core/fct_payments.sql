{{ config(materialized='table') }}

-- ============================================================
-- fct_payments
-- Payment-grain fact. Used for all revenue KPIs. Restricts to
-- successful payments only via is_recognized_revenue flag, but
-- keeps refunds/failures available for finance reporting.
-- Grain: one row per payment_id
-- ============================================================

with payments as (
    select * from {{ ref('stg_payments') }}
),

customers as (
    select customer_id, customer_sk, segment, country_code
    from {{ ref('dim_customers') }}
),

final as (
    select
        p.payment_id,
        c.customer_sk,
        p.customer_id,
        cast(p.paid_at as date)            as payment_date,
        p.paid_at,
        p.amount_local,
        p.currency,
        p.amount_usd,
        p.status,
        p.plan,
        c.segment                          as customer_segment,
        c.country_code,
        case when p.status = 'succeeded' then true else false end
                                           as is_recognized_revenue,
        case
            when p.status = 'succeeded' then p.amount_usd
            else 0
        end                                as recognized_amount_usd
    from payments p
    left join customers c using (customer_id)
)

select * from final
