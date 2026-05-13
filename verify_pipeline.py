"""
Verifies the dbt SQL logic runs end-to-end by executing the same
transformations directly in DuckDB. Used to prove the pipeline works
without needing the full dbt installation.
"""
import duckdb
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
con = duckdb.connect(str(DATA / "warehouse.duckdb"))

# --- Load raw ---
for name in ["raw_crm_customers", "raw_app_events", "raw_payments"]:
    con.execute(f"create or replace table {name} as "
                f"select * from read_csv_auto('{DATA}/{name}.csv')")
    n = con.execute(f"select count(*) from {name}").fetchone()[0]
    print(f"  loaded {name:25s} {n:>10,} rows")

# --- Staging ---
con.execute("""
create or replace view stg_crm_customers as
select
    cast(customer_id as varchar) as customer_id,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    lower(trim(email)) as email,
    cast(signup_date as timestamp) as signup_at,
    upper(trim(country)) as country_code,
    lower(trim(acquisition_channel)) as acquisition_channel,
    case when segment ilike 'free'       then 'Free'
         when segment ilike 'pro'        then 'Pro'
         when segment ilike 'business'   then 'Business'
         when segment ilike 'enterprise' then 'Enterprise'
    end as segment,
    case when lower(cast(is_active as varchar)) in ('true','1','t') then true else false end as is_active
from raw_crm_customers
""")

con.execute("""
create or replace view stg_app_events as
select
    cast(event_id as varchar) as event_id,
    cast(customer_id as varchar) as customer_id,
    cast(event_timestamp as timestamp) as event_at,
    lower(trim(event_type)) as event_type,
    lower(trim(platform)) as platform,
    cast(session_id as varchar) as session_id,
    case lower(trim(event_type))
        when 'page_view' then 1 when 'sign_up_started' then 2
        when 'sign_up_completed' then 3 when 'activated' then 4
        when 'upgraded' then 5 else null end as funnel_step
from raw_app_events
""")

con.execute("""
create or replace view stg_payments as
with fx(currency, usd_rate) as (values
    ('USD',1.00),('EUR',1.08),('GBP',1.27),('INR',0.012),('JPY',0.0067)
)
select
    cast(payment_id as varchar) as payment_id,
    cast(customer_id as varchar) as customer_id,
    cast(payment_timestamp as timestamp) as paid_at,
    cast(amount as decimal(12,2)) as amount_local,
    upper(trim(currency)) as currency,
    cast(amount as decimal(12,2)) * fx.usd_rate as amount_usd,
    lower(trim(status)) as status,
    upper(substr(plan,1,1)) || lower(substr(plan,2)) as plan
from raw_payments p
left join fx using (currency)
""")

# --- Core ---
con.execute("""
create or replace table dim_customers as
select
    md5(customer_id) as customer_sk,
    customer_id, first_name, last_name, email, signup_at,
    date_trunc('day', signup_at) as signup_date,
    date_trunc('month', signup_at) as signup_month,
    country_code, acquisition_channel, segment,
    case when segment in ('Pro','Business','Enterprise') then true else false end as is_paying,
    is_active,
    datediff('day', signup_at, current_timestamp) as days_since_signup
from stg_crm_customers
""")

con.execute("""
create or replace table fct_events as
select
    e.event_id, c.customer_sk, e.customer_id,
    cast(e.event_at as date) as event_date, e.event_at,
    e.event_type, e.platform, e.session_id, e.funnel_step,
    (e.event_type='page_view')::int as is_page_view,
    (e.event_type='sign_up_completed')::int as is_signup,
    (e.event_type='activated')::int as is_activation,
    (e.event_type='upgraded')::int as is_upgrade
from stg_app_events e left join dim_customers c using (customer_id)
""")

con.execute("""
create or replace table fct_payments as
select
    p.payment_id, c.customer_sk, p.customer_id,
    cast(p.paid_at as date) as payment_date, p.paid_at,
    p.amount_local, p.currency, p.amount_usd, p.status, p.plan,
    c.segment as customer_segment, c.country_code,
    (p.status='succeeded') as is_recognized_revenue,
    case when p.status='succeeded' then p.amount_usd else 0 end as recognized_amount_usd
from stg_payments p left join dim_customers c using (customer_id)
""")

# --- KPI marts ---
con.execute("""
create or replace table kpi_daily_active_users as
with daily as (
    select event_date, count(distinct customer_id) as dau
    from fct_events group by 1
),
mau as (
    select e.event_date, count(distinct e2.customer_id) as mau
    from (select distinct event_date from fct_events) e
    join fct_events e2 on e2.event_date between e.event_date - interval 29 day and e.event_date
    group by 1
)
select d.event_date as date_day, d.dau, m.mau,
       case when m.mau=0 then 0 else round(d.dau::double / m.mau, 4) end as dau_mau_ratio
from daily d join mau m using (event_date)
order by 1
""")

con.execute("""
create or replace table kpi_revenue_by_segment as
select
    date_trunc('month', payment_date)::date as month_start,
    customer_segment as segment,
    sum(recognized_amount_usd) as revenue_usd,
    count(distinct customer_id) as paying_customers,
    count(*) as txn_count,
    case when count(distinct customer_id)=0 then 0
         else round(sum(recognized_amount_usd)/count(distinct customer_id),2) end as arpu_usd
from fct_payments where is_recognized_revenue
group by 1,2 order by 1,2
""")

con.execute("""
create or replace table kpi_funnel_conversion as
with milestones as (
    select c.customer_id,
           date_trunc('month', c.signup_at)::date as cohort_month,
           max((e.event_type='sign_up_started')::int)   as did_start,
           max((e.event_type='sign_up_completed')::int) as did_complete,
           max((e.event_type='activated')::int)         as did_activate,
           max((e.event_type='upgraded')::int)          as did_upgrade
    from dim_customers c
    left join fct_events e using (customer_id)
    group by 1,2
)
select cohort_month,
       count(*) as cohort_size,
       sum(did_start) as started,
       sum(did_complete) as completed,
       sum(did_activate) as activated,
       sum(did_upgrade) as upgraded,
       round(sum(did_complete)::double / count(*), 4) as pct_completed,
       round(sum(did_activate)::double / count(*), 4) as pct_activated,
       round(sum(did_upgrade)::double  / count(*), 4) as pct_upgraded
from milestones group by 1 order by 1
""")

print("\n--- KPI snapshots ---\n")

print("DAU (last 5 days):")
print(con.execute("select * from kpi_daily_active_users order by date_day desc limit 5").fetchdf().to_string(index=False))

print("\nRevenue by segment (recent months):")
print(con.execute("""
    select * from kpi_revenue_by_segment
    where month_start >= date '2026-01-01'
    order by month_start, segment
""").fetchdf().to_string(index=False))

print("\nFunnel conversion (recent cohorts):")
print(con.execute("""
    select cohort_month, cohort_size, pct_completed, pct_activated, pct_upgraded
    from kpi_funnel_conversion
    where cohort_month >= date '2025-10-01'
    order by cohort_month
""").fetchdf().to_string(index=False))

print("\nData quality checks:")
checks = con.execute("""
    select 'unique customer_id'   as test, count(*) - count(distinct customer_id) as failures from dim_customers
    union all
    select 'unique payment_id',         count(*) - count(distinct payment_id) from fct_payments
    union all
    select 'no orphan event customer_sk', sum(case when customer_sk is null then 1 else 0 end) from fct_events
""").fetchdf()
print(checks.to_string(index=False))

con.close()
print("\n✓ End-to-end pipeline verified.")
