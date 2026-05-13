# Executive KPI Dashboard — End-to-End Data Pipeline

A production-grade analytics stack that turns three messy source systems into a single source of truth executives actually trust.

**Stack:** dbt · Airflow · DuckDB (local) / Snowflake (prod) · Streamlit / Power BI

## What it does

Ingests synthetic CRM, app-event, and payment data → cleans it in a staging layer → builds a star-schema core (dim_customers, dim_date, fct_events, fct_payments) → materializes curated KPI marts → serves them to a dashboard. The whole thing is orchestrated by an Airflow DAG with source-freshness gates, automated dbt tests, and Slack alerts.

## Quickstart

```bash
pip install -r requirements.txt
./run_pipeline.sh
streamlit run dashboard/app.py
```

## KPIs delivered

- Daily / Weekly / Monthly Active Users + DAU/MAU stickiness
- Monthly revenue by segment with MoM growth and ARPU
- Signup → completion → activation → upgrade funnel by cohort

## Project structure

```
data_generation/   synthetic source data generators
dbt_project/       staging + core + KPI marts
airflow/dags/      daily orchestration DAG
dashboard/         Streamlit executive view
verify_pipeline.py one-command full demo
```

See `NOTION_PAGE.md` for the full project showcase with code walkthroughs and live results.
