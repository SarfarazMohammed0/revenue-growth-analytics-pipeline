{{ config(materialized='table') }}

-- ============================================================
-- fct_events
-- Event-grain fact. One row per app event. Foreign keys to
-- dim_customers and dim_date for star-schema joins.
-- Grain: one row per event_id
-- ============================================================

with events as (
    select * from {{ ref('stg_app_events') }}
),

customers as (
    select customer_id, customer_sk from {{ ref('dim_customers') }}
),

final as (
    select
        e.event_id,
        c.customer_sk,
        e.customer_id,
        cast(e.event_at as date)         as event_date,
        e.event_at                       as event_at,
        e.event_type,
        e.platform,
        e.session_id,
        e.funnel_step,
        case when e.event_type = 'page_view'         then 1 else 0 end as is_page_view,
        case when e.event_type = 'sign_up_completed' then 1 else 0 end as is_signup,
        case when e.event_type = 'activated'         then 1 else 0 end as is_activation,
        case when e.event_type = 'upgraded'          then 1 else 0 end as is_upgrade
    from events e
    left join customers c using (customer_id)
)

select * from final
