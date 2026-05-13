"""
Executive KPI Dashboard – Streamlit front-end.

Reads from the curated KPI marts in DuckDB (or any warehouse if you swap
the connection string) and renders a clean executive view.

Run with:
    streamlit run dashboard/app.py
"""
import duckdb
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"

st.set_page_config(
    page_title="Executive KPI Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(sql).fetchdf()


st.title("📊 Executive KPI Dashboard")
st.caption("Powered by dbt + DuckDB. Data refreshed daily at 06:00 UTC by Airflow.")

# ---------------- Headline KPI tiles ----------------
dau = q("""
    select date_day, dau, wau, mau, dau_mau_ratio
    from kpi.kpi_daily_active_users
    order by date_day desc
    limit 30
""")
rev = q("""
    select month_start, sum(revenue_usd) as revenue
    from kpi.kpi_revenue_by_segment
    group by 1 order by 1
""")
funnel = q("select * from kpi.kpi_funnel_conversion order by cohort_month")

col1, col2, col3, col4 = st.columns(4)
col1.metric("DAU (latest)",        f"{int(dau['dau'].iloc[0]):,}")
col2.metric("MAU (latest)",        f"{int(dau['mau'].iloc[0]):,}")
col3.metric("DAU/MAU stickiness",  f"{dau['dau_mau_ratio'].iloc[0]:.1%}")
col4.metric("Revenue (last 30d)",  f"${rev['revenue'].tail(1).iloc[0]:,.0f}")

st.divider()

# ---------------- DAU trend ----------------
st.subheader("Daily Active Users (last 30 days)")
chart = alt.Chart(dau).mark_line(point=True).encode(
    x="date_day:T",
    y=alt.Y("dau:Q", title="DAU"),
    tooltip=["date_day", "dau", "wau", "mau"],
).properties(height=320)
st.altair_chart(chart, use_container_width=True)

# ---------------- Revenue by segment ----------------
st.subheader("Monthly Revenue by Segment")
seg = q("select * from kpi.kpi_revenue_by_segment order by month_start")
bar = alt.Chart(seg).mark_bar().encode(
    x="month_start:T",
    y="revenue_usd:Q",
    color="segment:N",
    tooltip=["month_start", "segment", "revenue_usd", "arpu_usd", "mom_growth_pct"],
).properties(height=320)
st.altair_chart(bar, use_container_width=True)

# ---------------- Funnel ----------------
st.subheader("Signup → Activation → Upgrade Funnel")
latest = funnel.iloc[-1]
fcol1, fcol2, fcol3, fcol4 = st.columns(4)
fcol1.metric("Cohort size",  f"{int(latest['cohort_size']):,}")
fcol2.metric("% Completed",  f"{latest['pct_completed']:.1%}")
fcol3.metric("% Activated",  f"{latest['pct_activated']:.1%}")
fcol4.metric("% Upgraded",   f"{latest['pct_upgraded']:.1%}")

st.dataframe(funnel, use_container_width=True)
