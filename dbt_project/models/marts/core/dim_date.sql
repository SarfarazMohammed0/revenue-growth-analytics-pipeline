{{ config(materialized='table') }}

-- ============================================================
-- dim_date
-- Standard date dimension. Spans 2023-01-01 to 2027-12-31 so
-- KPI marts can left-join on date and show gaps as zero.
-- Grain: one row per calendar day
-- ============================================================

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2023-01-01' as date)",
        end_date="cast('2028-01-01' as date)"
    ) }}
),

enriched as (
    select
        cast(date_day as date)                              as date_day,
        extract(year from date_day)                         as year,
        extract(quarter from date_day)                      as quarter,
        extract(month from date_day)                        as month,
        extract(day from date_day)                          as day_of_month,
        extract(dayofweek from date_day)                    as day_of_week,
        strftime(date_day, '%A')                            as day_name,
        strftime(date_day, '%B')                            as month_name,
        date_trunc('month', date_day)                       as month_start,
        date_trunc('quarter', date_day)                     as quarter_start,
        date_trunc('year', date_day)                        as year_start,
        case
            when extract(dayofweek from date_day) in (0, 6) then true
            else false
        end                                                 as is_weekend
    from date_spine
)

select * from enriched
