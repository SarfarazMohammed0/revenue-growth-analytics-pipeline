{{ config(materialized='view') }}

-- ============================================================
-- stg_app_events
-- Cleans raw event logs and assigns a funnel_step ordinal so
-- downstream funnel models can rank user progression.
-- Grain: one row per event_id
-- ============================================================

with source as (
    select * from {{ source('raw', 'raw_app_events') }}
),

renamed as (
    select
        cast(event_id as varchar)                  as event_id,
        cast(customer_id as varchar)               as customer_id,
        cast(event_timestamp as timestamp)         as event_at,
        lower(trim(event_type))                    as event_type,
        lower(trim(platform))                      as platform,
        cast(session_id as varchar)                as session_id,
        case lower(trim(event_type))
            when 'page_view'         then 1
            when 'sign_up_started'   then 2
            when 'sign_up_completed' then 3
            when 'activated'         then 4
            when 'upgraded'          then 5
            else null
        end                                        as funnel_step,
        current_timestamp                          as _loaded_at
    from source
)

select * from renamed
