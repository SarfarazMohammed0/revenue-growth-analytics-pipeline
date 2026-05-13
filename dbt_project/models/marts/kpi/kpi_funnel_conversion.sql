{{ config(materialized='table') }}

-- ============================================================
-- kpi_funnel_conversion
-- Cohort funnel: for users who signed up in a given month,
-- what percentage progressed through each step of the funnel?
-- Steps: signup_started -> signup_completed -> activated -> upgraded
-- Grain: one row per signup_month
-- ============================================================

with signup_cohorts as (
    select
        customer_id,
        date_trunc('month', signup_at)::date as signup_month
    from {{ ref('dim_customers') }}
),

user_milestones as (
    select
        c.customer_id,
        c.signup_month,
        max(case when e.event_type = 'sign_up_started'   then 1 else 0 end) as did_start,
        max(case when e.event_type = 'sign_up_completed' then 1 else 0 end) as did_complete,
        max(case when e.event_type = 'activated'         then 1 else 0 end) as did_activate,
        max(case when e.event_type = 'upgraded'          then 1 else 0 end) as did_upgrade
    from signup_cohorts c
    left join {{ ref('fct_events') }} e using (customer_id)
    group by c.customer_id, c.signup_month
),

cohort_rollup as (
    select
        signup_month                                    as cohort_month,
        count(*)                                        as cohort_size,
        sum(did_start)                                  as started,
        sum(did_complete)                               as completed,
        sum(did_activate)                               as activated,
        sum(did_upgrade)                                as upgraded
    from user_milestones
    group by 1
),

final as (
    select
        cohort_month,
        cohort_size,
        started,
        completed,
        activated,
        upgraded,
        round(started   * 1.0 / nullif(cohort_size, 0), 4) as pct_started,
        round(completed * 1.0 / nullif(cohort_size, 0), 4) as pct_completed,
        round(activated * 1.0 / nullif(cohort_size, 0), 4) as pct_activated,
        round(upgraded  * 1.0 / nullif(cohort_size, 0), 4) as pct_upgraded,
        round(activated * 1.0 / nullif(completed, 0), 4)   as completion_to_activation,
        round(upgraded  * 1.0 / nullif(activated, 0), 4)   as activation_to_upgrade
    from cohort_rollup
)

select * from final
order by cohort_month
