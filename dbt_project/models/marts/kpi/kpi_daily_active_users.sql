{{ config(materialized='table') }}

-- ============================================================
-- kpi_daily_active_users
-- Daily, weekly, and monthly active user counts. Joined to
-- dim_date so calendar gaps render as zero on the dashboard.
-- Grain: one row per calendar day
-- ============================================================

with daily as (
    select
        event_date,
        count(distinct customer_id) as dau
    from {{ ref('fct_events') }}
    group by 1
),

wau as (
    select
        event_date,
        count(distinct customer_id) as wau
    from {{ ref('fct_events') }} e1
    join (
        select distinct event_date as anchor_date
        from {{ ref('fct_events') }}
    ) a on e1.event_date between a.anchor_date - interval 6 day and a.anchor_date
    group by 1
),

mau as (
    select
        event_date,
        count(distinct customer_id) as mau
    from {{ ref('fct_events') }} e1
    join (
        select distinct event_date as anchor_date
        from {{ ref('fct_events') }}
    ) a on e1.event_date between a.anchor_date - interval 29 day and a.anchor_date
    group by 1
),

final as (
    select
        d.date_day,
        coalesce(daily.dau, 0)                                as dau,
        coalesce(wau.wau, 0)                                  as wau,
        coalesce(mau.mau, 0)                                  as mau,
        case
            when coalesce(mau.mau, 0) = 0 then 0
            else round(coalesce(daily.dau, 0) * 1.0 / mau.mau, 4)
        end                                                   as dau_mau_ratio
    from {{ ref('dim_date') }} d
    left join daily on d.date_day = daily.event_date
    left join wau   on d.date_day = wau.event_date
    left join mau   on d.date_day = mau.event_date
    where d.date_day between date '2025-01-01' and current_date
)

select * from final
order by date_day
