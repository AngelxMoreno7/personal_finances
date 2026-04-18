import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from finance.db import get_connection
from finance.categorizer import get_category_colors

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Personal Finance",
    page_icon="💰",
    layout="wide"
)

# ── Constants ─────────────────────────────────────────────────────────────────
EXCLUDE_CATEGORIES = {"Transfer"}
EXCLUDE_TRANSACTION_TYPES = {"Payment"}  # credit card payments

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_transactions() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            t.date,
            t.description,
            t.amount,
            t.type,
            t.transaction_type,
            t.account_id,
            a.name        AS account_name,
            a.account_type,
            c.name        AS category,
            c.color       AS category_color
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN categories c ON t.category_id = c.id
        WHERE
            -- Exclude savings transfers
            c.name NOT IN ('Transfer')
            -- Exclude credit card payment rows (checking side of the payment)
            AND NOT (a.account_type = 'checking' AND t.amount < -200
                     AND t.type IN ('ACH_DEBIT', 'ACCT_XFER'))
            -- Exclude credit card payment rows (credit card side)
            AND NOT (a.account_type = 'credit' AND t.transaction_type = 'Payment')
            -- Only count spending (positive amounts on credit = purchase, negative on checking = spend)
            AND (
                (a.account_type = 'credit'   AND t.amount > 0)
                OR
                (a.account_type = 'checking' AND t.amount < 0)
            )
    """, conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["year"] = df["date"].dt.year
    df["spend"] = df["amount"].abs()

    return df


# ── Sidebar filters ───────────────────────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    st.sidebar.title("Filters")

    # Date range
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Categories
    all_categories = sorted(df["category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=all_categories,
        default=all_categories,
    )

    return pd.Timestamp(start_date), pd.Timestamp(end_date), selected_categories


# ── Charts ────────────────────────────────────────────────────────────────────
def render_spending_trend(df: pd.DataFrame, colors: dict):
    st.subheader("Spending trend over time")

    monthly = (
        df.groupby(["month", "category"])["spend"]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        monthly,
        x="month",
        y="spend",
        color="category",
        color_discrete_map=colors,
        labels={"month": "", "spend": "Amount ($)", "category": "Category"},
        barmode="stack",
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=60, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_breakdown(df: pd.DataFrame, colors: dict):
    st.subheader("Monthly spending by category")

    # Month selector
    available_months = sorted(df["month"].dt.strftime("%B %Y").unique().tolist(), reverse=True)
    selected_month_str = st.selectbox("Select month", available_months)
    selected_month = pd.to_datetime(selected_month_str, format="%B %Y")

    month_df = df[df["month"] == selected_month]

    col1, col2 = st.columns([1, 1])

    with col1:
        # Pie chart
        category_totals = (
            month_df.groupby("category")["spend"]
            .sum()
            .reset_index()
            .sort_values("spend", ascending=False)
        )
        fig = px.pie(
            category_totals,
            values="spend",
            names="category",
            color="category",
            color_discrete_map=colors,
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Bar chart sorted by spend
        fig = px.bar(
            category_totals,
            x="spend",
            y="category",
            orientation="h",
            color="category",
            color_discrete_map=colors,
            labels={"spend": "Amount ($)", "category": ""},
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_summary_metrics(df: pd.DataFrame, start_date, end_date):
    filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    total_spend = filtered["spend"].sum()
    avg_monthly = filtered.groupby("month")["spend"].sum().mean()
    top_category = filtered.groupby("category")["spend"].sum().idxmax()
    total_transactions = len(filtered)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total spend", f"${total_spend:,.2f}")
    col2.metric("Avg monthly spend", f"${avg_monthly:,.2f}")
    col3.metric("Top category", top_category)
    col4.metric("Transactions", f"{total_transactions:,}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.title("💰 Personal Finance Dashboard")

    df = load_transactions()
    colors = get_category_colors()

    start_date, end_date, selected_categories = render_sidebar(df)

    # Apply filters
    filtered_df = df[
        (df["date"] >= start_date) &
        (df["date"] <= end_date) &
        (df["category"].isin(selected_categories))
    ]

    render_summary_metrics(filtered_df, start_date, end_date)
    st.divider()
    render_spending_trend(filtered_df, colors)
    st.divider()
    render_monthly_breakdown(filtered_df, colors)


if __name__ == "__main__":
    main()