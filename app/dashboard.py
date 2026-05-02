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

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_transactions() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            t.id,
            t.date,
            t.description,
            t.amount,
            t.type,
            t.transaction_type,
            a.name        AS account_name,
            a.account_type,
            c.name        AS category,
            c.color       AS category_color
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN categories c ON t.category_id = c.id
        WHERE
            c.name NOT IN ('Transfer', 'Excluded')
            AND (
                (a.account_type = 'credit' AND t.amount > 0)
                OR (a.account_type = 'checking' AND t.amount < 0)
                OR (a.account_type = 'checking' AND t.amount > 0 AND c.name IN ('Venmo, Zelle, & Paypal', 'Income'))
                OR (a.account_type = 'venmo')
            )
    """, conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["year"] = df["date"].dt.year
    # For venmo, preserve sign so incoming payments offset spending
    df["spend"] = df.apply(
        lambda row: row["amount"] if row["account_type"] == "venmo" else abs(row["amount"]),
        axis=1
    )

    return df


# ── Sidebar filters ───────────────────────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    st.sidebar.title("Filters")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    all_categories = sorted(df["category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=all_categories,
        default=all_categories,
    )

    all_accounts = sorted(df["account_name"].unique().tolist())
    selected_accounts = st.sidebar.multiselect(
        "Accounts",
        options=all_accounts,
        default=all_accounts,
    )

    return (
        pd.Timestamp(start_date),
        pd.Timestamp(end_date),
        selected_categories,
        selected_accounts,
    )


# ── Summary metrics ───────────────────────────────────────────────────────────
def render_summary_metrics(df: pd.DataFrame):
    total_spend = df["spend"].sum()
    avg_monthly = df.groupby("month")["spend"].sum().mean()
    top_category = df.groupby("category")["spend"].sum().idxmax()
    total_transactions = len(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total spend",        f"${total_spend:,.2f}")
    col2.metric("Avg monthly spend",  f"${avg_monthly:,.2f}")
    col3.metric("Top category",       top_category)
    col4.metric("Transactions",       f"{total_transactions:,}")


# ── Spending trend ────────────────────────────────────────────────────────────
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


# ── Monthly breakdown ─────────────────────────────────────────────────────────
def render_monthly_breakdown(df: pd.DataFrame, colors: dict):
    st.subheader("Monthly spending by category")

    available_months = sorted(
        df["month"].dt.strftime("%B %Y").unique().tolist(), reverse=True
    )
    selected_month_str = st.selectbox("Select month", available_months)
    selected_month = pd.to_datetime(selected_month_str, format="%B %Y")

    month_df = df[df["month"] == selected_month]

    col1, col2 = st.columns([1, 1])

    with col1:
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
        fig = px.bar(
            category_totals,
            x="spend",
            y="category",
            orientation="h",
            color="category",
            color_discrete_map=colors,
            labels={"spend": "Amount ($)", "category": ""},
            text=category_totals["spend"].apply(lambda x: f"${x:,.2f}"),
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=20, r=80),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)


# ── Transaction table ─────────────────────────────────────────────────────────
def render_transaction_table(df: pd.DataFrame, all_categories: list):
    st.subheader("Transactions")

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search = st.text_input("Search descriptions", placeholder="e.g. amazon, uber, starbucks...")
    with col2:
        amount_filter = st.selectbox("Amount", ["All", "Spending (positive)", "Offsets (negative)"])
    with col3:
        category_options = ["All"] + sorted(df["category"].unique().tolist())
        selected_category = st.selectbox("Category", category_options)
    with col4:
        account_options = ["All"] + sorted(df["account_name"].unique().tolist())
        selected_account = st.selectbox("Account", account_options)

    # ── Apply filters ─────────────────────────────────────────────────────────
    table_df = df.copy()

    if search:
        table_df = table_df[
            table_df["description"].str.contains(search, case=False, na=False)
        ]
    if selected_account != "All":
        table_df = table_df[table_df["account_name"] == selected_account]
    if selected_category != "All":
        table_df = table_df[table_df["category"] == selected_category]
    if amount_filter == "Spending (positive)":
        table_df = table_df[table_df["spend"] > 0]
    elif amount_filter == "Offsets (negative)":
        table_df = table_df[table_df["spend"] < 0]

    # ── Sort and format ───────────────────────────────────────────────────────
    table_df = table_df.sort_values("date", ascending=False)
    table_df["date"] = table_df["date"].dt.strftime("%Y-%m-%d")
    table_df["Amount"] = table_df["spend"].apply(
        lambda x: f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"
    )

    display_df = table_df[["id", "date", "description", "Amount", "category", "account_name"]].rename(columns={
        "date":         "Date",
        "description":  "Description",
        "category":     "Category",
        "account_name": "Account",
    })

    # ── Editable table ────────────────────────────────────────────────────────
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        height=400,
        hide_index=True,
        disabled=["id", "Date", "Description", "Amount", "Account"],
        column_config={
            "id": None,
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=all_categories,
                required=True,
            ),
        },
        key="transaction_table",
    )

    # ── Save changes ──────────────────────────────────────────────────────────
    changes = edited_df[edited_df["Category"] != display_df["Category"]]
    if not changes.empty:
        conn = get_connection()
        cursor = conn.cursor()
        saved = 0
        for _, row in changes.iterrows():
            cursor.execute("SELECT id FROM categories WHERE name = ?", (row["Category"],))
            cat_row = cursor.fetchone()
            if cat_row:
                cursor.execute("""
                    UPDATE transactions
                    SET category_id = ?, manually_categorized = 1
                    WHERE id = ?
                """, (cat_row["id"], row["id"]))
                saved += 1
        conn.commit()
        conn.close()

        if saved:
            st.success(f"{saved} transaction(s) updated.")
            st.cache_data.clear()
            st.rerun()

    st.caption(f"{len(table_df):,} transactions")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.title("💰 Personal Finance Dashboard")

    df = load_transactions()
    colors = get_category_colors()

    start_date, end_date, selected_categories, selected_accounts = render_sidebar(df)

    filtered_df = df[
        (df["date"] >= start_date) &
        (df["date"] <= end_date) &
        (df["category"].isin(selected_categories)) &
        (df["account_name"].isin(selected_accounts))
    ]

    render_summary_metrics(filtered_df)
    st.divider()
    render_spending_trend(filtered_df, colors)
    st.divider()
    render_monthly_breakdown(filtered_df, colors)
    st.divider()
    all_categories = sorted(df["category"].unique().tolist())
    render_transaction_table(filtered_df, all_categories)


if __name__ == "__main__":
    main()