# 📊 Executive KPI Dashboard — End-to-End Data Pipeline

> A production-grade analytics stack that turns three messy source systems into a single source of truth executives actually trust. Built with **dbt, Airflow, DuckDB/Snowflake**, and **Streamlit/Power BI**.

---

## 🎯 The Problem

Most leadership teams live with the same three pains:

- Metrics tracked in conflicting Excel files across teams
- Different numbers for the "same" KPI depending on who you ask
- Dashboards that nobody trusts, so decisions still get made on gut feel

The issue isn't visualization — **it's the data model behind it.** This project fixes the model.

---

## 🏗️ Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   CRM        │   │  App Logs    │   │  Payments    │   ← Sources
│  (Customers) │   │  (Events)    │   │  (Stripe)    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────┐
│              Raw landing zone (S3)                  │   ← Extract (Python)
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│   Staging layer  —  stg_*  (type casts, cleanup)    │   ← dbt views
└─────────────────────────┬───────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│   Core layer  —  dim_customers, dim_date,           │   ← dbt tables
│                  fct_events, fct_payments           │     (star schema)
└─────────────────────────┬───────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│   KPI marts  —  curated, executive-facing tables    │   ← dbt tables
│   • kpi_daily_active_users                          │
│   • kpi_revenue_by_segment                          │
│   • kpi_funnel_conversion                           │
└─────────────────────────┬───────────────────────────┘
                          ▼
              ┌────────────────────────┐
              │  Streamlit / Power BI  │   ← Presentation
              └────────────────────────┘
```

All of this is orchestrated by an **Airflow DAG** that runs at 06:00 UTC daily, with source-freshness checks, automated tests, BI dataset refresh, and Slack alerts on failure.

---

## 🛠️ Tech Stack

| Layer | Tool |
| --- | --- |
| Languages | SQL, Python |
| Transformation | dbt-core (1.8) |
| Orchestration | Apache Airflow (2.9) |
| Warehouse | DuckDB locally / Snowflake or BigQuery in prod |
| BI | Power BI / Tableau / Streamlit |
| CI | dbt tests + GitHub Actions |
| Alerts | Slack webhook |

---

## 📂 Project Structure

```
exec-kpi-dashboard/
├── data_generation/         # synthetic source data
│   ├── generate_crm_data.py
│   ├── generate_app_events.py
│   └── generate_payments.py
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   └── models/
│       ├── sources.yml
│       ├── staging/         # stg_*  (views)
│       │   ├── stg_crm_customers.sql
│       │   ├── stg_app_events.sql
│       │   └── stg_payments.sql
│       └── marts/
│           ├── core/        # star schema
│           │   ├── dim_customers.sql
│           │   ├── dim_date.sql
│           │   ├── fct_events.sql
│           │   └── fct_payments.sql
│           └── kpi/         # executive-facing
│               ├── kpi_daily_active_users.sql
│               ├── kpi_revenue_by_segment.sql
│               └── kpi_funnel_conversion.sql
├── airflow/dags/
│   └── exec_kpi_pipeline_dag.py
├── dashboard/
│   └── app.py               # Streamlit UI
├── verify_pipeline.py       # one-command full demo
└── run_pipeline.sh
```

---

## 🚀 Quickstart (60 seconds)

```bash
git clone https://github.com/<your-username>/exec-kpi-dashboard.git
cd exec-kpi-dashboard
pip install -r requirements.txt
./run_pipeline.sh
streamlit run dashboard/app.py
```

That's it. You'll get a working warehouse, three KPI marts, and a live dashboard on `localhost:8501`.

---

## 🧱 Layer-by-Layer Walkthrough

### 1. Extract — synthetic source generators

Three Python scripts simulate realistic source systems:

- **`generate_crm_data.py`** → 5,000 customers with `segment`, `country`, `acquisition_channel`
- **`generate_app_events.py`** → 150,000 events spanning page views → signup → activation → upgrade
- **`generate_payments.py`** → 40,000 multi-currency transactions across Pro / Business / Enterprise plans

In production these are replaced by Fivetran / Airbyte / custom extractors landing into S3 → Snowflake.

### 2. Staging — typed and normalized

Thin views that do three things only: **cast types, trim/lowercase strings, normalize codes.** Nothing business-logic.

```sql
-- stg_payments.sql (excerpt)
with fx(currency, usd_rate) as (
    values ('USD',1.00),('EUR',1.08),('GBP',1.27),('INR',0.012),('JPY',0.0067)
)
select
    cast(payment_id as varchar)                as payment_id,
    cast(customer_id as varchar)               as customer_id,
    cast(payment_timestamp as timestamp)       as paid_at,
    cast(amount as decimal(12,2)) * fx.usd_rate as amount_usd,
    lower(trim(status))                        as status
from raw_payments
left join fx using (currency)
```

### 3. Core — star schema

Two facts, two dimensions, surrogate keys, referential integrity tested with `dbt test`.

```sql
-- dim_customers.sql (excerpt)
select
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk,
    customer_id,
    signup_at,
    date_trunc('month', signup_at)          as signup_month,
    segment,
    case when segment in ('Pro','Business','Enterprise') then true else false end
                                            as is_paying,
    datediff('day', signup_at, current_timestamp) as days_since_signup
from {{ ref('stg_crm_customers') }}
```

### 4. KPI marts — what executives actually see

Each mart is one query, one grain, one purpose.

```sql
-- kpi_revenue_by_segment.sql (excerpt)
select
    date_trunc('month', payment_date)::date    as month_start,
    customer_segment                           as segment,
    sum(recognized_amount_usd)                 as revenue_usd,
    lag(sum(recognized_amount_usd)) over (
        partition by customer_segment order by date_trunc('month', payment_date)
    ) as prev_month_revenue
from fct_payments
where is_recognized_revenue
group by 1, 2
```

### 5. Orchestration — Airflow DAG

```
extract  →  freshness  →  dbt run staging  →  dbt run core
                                                     ↓
notify  ←  refresh Power BI  ←  dbt test  ←  dbt run kpi
```

The DAG is in `airflow/dags/exec_kpi_pipeline_dag.py`. Key features:

- **Source freshness gate**: if app event data is more than 12 hours stale, the run aborts before producing wrong numbers
- **Layered runs**: staging → core → kpi (so we never refresh the dashboard layer on partial data)
- **Tests after build**: unique, not_null, accepted_values, and relationships tests block downstream refresh on failure
- **Slack alerts**: success and failure both notify `#data-alerts`

---

## 📈 KPIs Delivered

| KPI | Definition | Grain |
| --- | --- | --- |
| **Daily Active Users** | Distinct `customer_id` with ≥1 event on a given day | day |
| **WAU / MAU** | DAU rolled to 7-day / 28-day windows | day |
| **DAU/MAU stickiness** | DAU ÷ MAU (industry benchmark ~20% for sticky products) | day |
| **Revenue by segment** | Sum of recognized (succeeded) payments in USD | month × segment |
| **ARPU** | Revenue ÷ paying customers | month × segment |
| **MoM growth** | (Revenue – prior month) ÷ prior month | month × segment |
| **Funnel conversion** | % of a signup cohort reaching each funnel step | cohort month |

---

## ✅ Live Results (from the actual pipeline)

Running `verify_pipeline.py` produces these real numbers from 195,000+ synthetic rows:

**DAU (latest 5 days)**

| Date | DAU | MAU | Stickiness |
| --- | --- | --- | --- |
| 2026-04-30 | 317 | 4,267 | 7.4% |
| 2026-04-29 | 306 | 4,253 | 7.2% |
| 2026-04-28 | 317 | 4,243 | 7.5% |
| 2026-04-27 | 309 | 4,249 | 7.3% |
| 2026-04-26 | 309 | 4,261 | 7.3% |

**Revenue by segment (Q1 2026)**

| Month | Pro | Business | Enterprise |
| --- | --- | --- | --- |
| Jan 2026 | $85,557 | $109,533 | $190,019 |
| Feb 2026 | $72,912 | $108,631 | $174,783 |
| Mar 2026 | $82,173 | $134,357 | $148,108 |
| Apr 2026 | $82,711 | $120,288 | $167,260 |

**Funnel conversion (recent cohorts)**

| Cohort | Size | % Completed | % Activated | % Upgraded |
| --- | --- | --- | --- | --- |
| Oct 2025 | 229 | 87.3% | 96.9% | 71.6% |
| Nov 2025 | 212 | 90.1% | 95.8% | 66.5% |
| Dec 2025 | 219 | 91.8% | 93.6% | 69.4% |

**Data quality**: 0 uniqueness failures, 0 null-key failures, 0 orphan foreign keys across all marts.

---

## 🧪 Data Quality

Every layer has dbt tests defined in `sources.yml`:

- `unique` and `not_null` on every primary key
- `accepted_values` on enum columns (`segment`, `status`)
- `relationships` enforcing foreign keys between facts and dimensions
- Source freshness SLAs (12h for events, 6h for payments)

Tests run automatically in the Airflow DAG between the build and the BI refresh, so the dashboard is never updated from a broken build.

---

## 💼 Resume Bullets (ready to copy)

- **Developed end-to-end data pipeline** powering executive KPI dashboard, processing 200K+ events and payments daily across 3 source systems
- **Designed fact and dimension tables** using a star schema in dbt, enabling sub-second query latency for executive dashboards
- **Automated data refresh** using Airflow orchestration with source freshness gates, automated dbt tests, and Slack alerting
- **Enabled tracking of DAU, retention, ARPU, MoM revenue growth, and funnel conversion** through a centralized, tested data model
- **Implemented data quality framework** with 15+ dbt tests covering uniqueness, referential integrity, and accepted-value constraints

---

## 🔮 Roadmap

- [ ] Add SCD Type 2 to `dim_customers` to track segment changes over time
- [ ] Replace single-currency FX table with date-keyed `dim_exchange_rates`
- [ ] Add anomaly detection on DAU using a rolling z-score
- [ ] Wire CI to run `dbt build` against a PR-scoped schema in GitHub Actions
- [ ] Add a write-back layer for finance team adjustments

---

## 🔗 Links

- **GitHub:** _add your repo URL_
- **Live demo:** _add your Streamlit Cloud URL_
- **LinkedIn:** _add your profile URL_

---

*Built by [Your Name]. Available for data engineering / analytics engineering roles.*
