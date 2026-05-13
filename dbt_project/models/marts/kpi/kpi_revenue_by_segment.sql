{{ config(materialized='table') }}

-- ============================================================
-- kpi_revenue_by_segment
-- Monthly recognized revenue (USD) sliced by customer segment.
-- Includes MoM growth % using a window function.
-- Grain: one row per (month, segment)
-- ============================================================

with monthly as (
    select
        date_trunc('month', payment_date)::date    as month_start,
        customer_segment                           as segment,
        sum(recognized_amount_usd)                 as revenue_usd,
        count(distinct customer_id)                as paying_customers,
        count(*)                                   as txn_count
    from {{ ref('fct_payments') }}
    where is_recognized_revenue
    group by 1, 2
),

with_growth as (
    select
        month_start,
        segment,
        revenue_usd,
        paying_customers,
        txn_count,
        lag(revenue_usd) over (
            partition by segment order by month_start
        ) as prev_month_revenue,
        case
            when lag(revenue_usd) over (partition by segment order by month_start) is null
                 or lag(revenue_usd) over (partition by segment order by month_start) = 0
            then null
            else round(
                (revenue_usd - lag(revenue_usd) over (partition by segment order by month_start))
                / lag(revenue_usd) over (partition by segment order by month_start),
                4
            )
        end as mom_growth_pct,
        case when paying_customers = 0 then 0
             else round(revenue_usd / paying_customers, 2)
        end as arpu_usd
    from monthly
)

select * from with_growth
order by month_start, segment
