"""
Home page — this replaces your existing dashboard.py.
The only change is a new render_home() function added above main(),
and a page selector added to the sidebar so users can switch between
the home page and the dashboard.

Everything else (load_transactions, inject_theme, render_sidebar,
render_summary_metrics, render_spending_trend, render_monthly_breakdown,
render_transaction_table) is unchanged.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
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
            a.name          AS account_name,
            a.account_type,
            s.name          AS subcategory,
            s.color         AS subcategory_color,
            c.name          AS category
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN subcategories s ON t.subcategory_id = s.id
        JOIN categories c ON s.category_id = c.id
        WHERE
            c.name != 'Excluded'
            AND s.name != 'Excluded'
        AND (
            a.account_type = 'credit'
            OR a.account_type = 'checking'
            OR a.account_type = 'venmo'
        )
    """, conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    df["month_str"] = df["date"].dt.strftime("%Y-%m")
    df["year"] = df["date"].dt.year
    df["spend"] = df.apply(
        lambda row: row["amount"] if row["account_type"] == "venmo"
        else abs(row["amount"]) if (
            (row["account_type"] == "credit" and row["amount"] > 0) or
            (row["account_type"] == "checking" and row["amount"] < 0)
        ) else -abs(row["amount"]),
        axis=1
    )

    return df

def inject_theme(theme: str):
    themes = {
        "Linear/Notion Dark": {
            "bg":          "#0F0F0F",
            "card":        "#1A1A1A",
            "accent":      "#7C5CFC",
            "accent2":     "#A78BFA",
            "text":        "#FFFFFF",
            "subtext":     "#A0A0A0",
            "border":      "#2A2A2A",
            "pill_bg":     "#2A2A2A",
            "pill_text":   "#A78BFA",
        },
        "Arctic": {
            "bg":          "#F7F9FC",
            "card":        "#FFFFFF",
            "accent":      "#2563EB",
            "accent2":     "#60A5FA",
            "text":        "#1E293B",
            "subtext":     "#64748B",
            "border":      "#E2E8F0",
            "pill_bg":     "#DBEAFE",
            "pill_text":   "#1D4ED8",
        },
        "Dracula": {
            "bg":          "#282A36",
            "card":        "#44475A",
            "accent":      "#FF79C6",
            "accent2":     "#50FA7B",
            "text":        "#F8F8F2",
            "subtext":     "#6272A4",
            "border":      "#6272A4",
            "pill_bg":     "#44475A",
            "pill_text":   "#FF79C6",
        },
    }

    t = themes[theme]

    st.markdown(f"""
    <style>
    /* ── Hide deploy button ── */
    [data-testid="stToolbar"] {{
        display: none !important;
    }}
                
    /* ── Header / top bar ── */
    [data-testid="stHeader"] {{
        background-color: {t['bg']} !important;
    }}

    /* ── Top toolbar buttons (Deploy, 3 dots) ── */
    [data-testid="stHeader"] button {{
        color: {t['text']} !important;
    }}
    [data-testid="stHeader"] a {{
        color: {t['text']} !important;
    }}

    /* ── Main block container top padding area ── */
    [data-testid="stAppViewContainer"] {{
        background-color: {t['bg']} !important;
    }}

    /* ── The decorative top color strip Streamlit adds ── */
    [data-testid="stDecoration"] {{
        background-color: {t['bg']} !important;
        background-image: none !important;
    }}
    
    /* ── App background ── */
    .stApp {{
        background-color: {t['bg']};
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background-color: {t['card']};
        border-right: 1px solid {t['border']};
    }}
    [data-testid="stSidebar"] * {{
        color: {t['text']} !important;
    }}

    /* ── Main text ── */
    .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp label {{
        color: {t['text']} !important;
    }}

    /* ── Metric cards ── */
    [data-testid="metric-container"] {{
        background-color: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 16px;
    }}
    [data-testid="metric-container"] * {{
        color: {t['text']} !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {t['accent']} !important;
        font-size: 1.4rem !important;
    }}

    /* ── Multiselect pills ── */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
        background-color: {t['pill_bg']} !important;
        border: 1px solid {t['accent']} !important;
        border-radius: 6px !important;
        padding: 2px 4px !important;
    }}
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] span {{
        color: {t['pill_text']} !important;
        font-size: 0.75rem !important;
    }}

    /* ── Select/input boxes ── */
    [data-baseweb="select"] > div:last-child {{
        background-color: {t['card']} !important;
        border-color: {t['border']} !important;
        color: {t['text']} !important;
    }}
    [data-baseweb="input"] {{
        background-color: {t['card']} !important;
        border-color: {t['border']} !important;
        color: {t['text']} !important;
    }}

    /* ── Buttons ── */
    .stButton button {{
        background-color: {t['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }}

    /* ── Dividers ── */
    hr {{
        border-color: {t['border']} !important;
    }}

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {t['border']};
        border-radius: 8px;
    }}

    /* ── Radio buttons ── */
    [data-testid="stRadio"] label {{
        color: {t['text']} !important;
    }}

    /* ── Subtext / captions ── */
    .stApp .stCaption {{
        color: {t['subtext']} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    st.sidebar.title("💰 Personal Spending")
    
    theme = st.sidebar.selectbox(
        "Theme",
        ["Linear/Notion Dark", "Arctic", "Dracula"],
        index=1
    )
    
    inject_theme(theme)
    
    st.sidebar.divider()
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

    # View toggle
    view_by = st.sidebar.radio("View by", ["Category", "Subcategory"], horizontal=True)

    # Category filter
    all_categories = sorted(df["category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=all_categories,
        default=[c for c in all_categories if c not in ("Income", "Uncategorized")],
    )

    # Subcategory filter — only show subcategories within selected categories
    filtered_subcats = sorted(
        df[df["category"].isin(selected_categories)]["subcategory"].unique().tolist()
    )
    all_subcategories = sorted(df["subcategory"].unique().tolist())
    selected_subcategories = st.sidebar.multiselect(
        "Subcategories",
        options=filtered_subcats,
        default=filtered_subcats,
    )

    # Account filter
    all_accounts = sorted(df["account_name"].unique().tolist())
    selected_accounts = st.sidebar.multiselect(
        "Accounts",
        options=all_accounts,
        default=all_accounts,
    )

    return (
        pd.Timestamp(start_date),
        pd.Timestamp(end_date),
        view_by,
        selected_categories,
        selected_subcategories,
        selected_accounts,
        all_subcategories,
    )


# ── Summary metrics ───────────────────────────────────────────────────────────
def render_summary_metrics(df: pd.DataFrame):
    total_spend = df["spend"].sum()
    avg_monthly = df.groupby("month_str")["spend"].sum().mean()
    top_category = df.groupby("category")["spend"].sum().idxmax()
    top_subcategory = df.groupby("subcategory")["spend"].sum().idxmax()
    total_transactions = len(df)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total spend",       f"${total_spend:,.2f}")
    col2.metric("Avg monthly spend", f"${avg_monthly:,.2f}")
    col3.metric("Top category",      top_category)
    col4.metric("Top subcategory",   top_subcategory)
    col5.metric("Transactions",      f"{total_transactions:,}")


# ── Spending trend ────────────────────────────────────────────────────────────
def render_spending_trend(df: pd.DataFrame, view_by: str, colors: dict):
    st.subheader("Spending trend over time")

    group_col = "subcategory" if view_by == "Subcategory" else "category"

    monthly = (
        df.groupby(["month_str", group_col])["spend"]
        .sum()
        .reset_index()
        .sort_values("month_str")
    )

    fig = px.bar(
        monthly,
        x="month_str",
        y="spend",
        color=group_col,
        color_discrete_map=colors if view_by == "Subcategory" else None,
        labels={"month_str": "", "spend": "Amount ($)", group_col: view_by},
        barmode="stack",
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=60, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, type="category"),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Monthly breakdown ─────────────────────────────────────────────────────────
def render_monthly_breakdown(df: pd.DataFrame, view_by: str, colors: dict):
    st.subheader("Monthly spending by category")

    available_months = sorted(df["month_str"].unique().tolist(), reverse=True)
    display_months = {m: pd.to_datetime(m).strftime("%B %Y") for m in available_months}
    selected_display = st.selectbox("Select month", list(display_months.values()))
    selected_month_str = [k for k, v in display_months.items() if v == selected_display][0]

    month_df = df[df["month_str"] == selected_month_str]
    group_col = "subcategory" if view_by == "Subcategory" else "category"

    category_totals = (
        month_df.groupby(group_col)["spend"]
        .sum()
        .reset_index()
        .sort_values("spend", ascending=False)
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        fig = px.pie(
            category_totals,
            values="spend",
            names=group_col,
            color=group_col,
            color_discrete_map=colors if view_by == "Subcategory" else None,
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
            y=group_col,
            orientation="h",
            color=group_col,
            color_discrete_map=colors if view_by == "Subcategory" else None,
            labels={"spend": "Amount ($)", group_col: ""},
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
def render_transaction_table(df: pd.DataFrame, all_subcategories: list):
    st.subheader("Transactions")

    with st.expander("How does manual categorization work? →", expanded=False):
        st.markdown("""
        **Changing a subcategory**  
        The Subcategory column is editable. Click any cell in that column to open a dropdown
        and assign a different subcategory. The change saves to the database instantly — no
        save button needed.

        **What "manually categorized" means**  
        Once you change a subcategory here, that transaction is flagged as manually categorized.
        This protects your override — if you ever run **Save & Recategorize** from the Categories
        page, the app will re-scan all transactions against your keywords but will skip any
        transaction you've manually set here. Your manual assignments are never overwritten.

        **Excluding a transaction**  
        If a transaction shouldn't appear in your spending at all (e.g. a credit card payment,
        a transfer, an investment), assign it to **Excluded** from the dropdown. It will
        disappear from all charts and metrics on the next reload.

        **Searching and filtering first**  
        Use the search and filter controls above the table to narrow down to the transactions
        you want to fix before editing. This is especially useful for bulk cleanup — filter
        by subcategory "Uncategorized", then work through the list.
        """)

    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])

    with col1:
        search = st.text_input("Search descriptions", placeholder="e.g. amazon, uber, starbucks...")
    with col2:
        account_options = ["All"] + sorted(df["account_name"].unique().tolist())
        selected_account = st.selectbox("Account", account_options)
    with col3:
        category_options = ["All"] + sorted(df["category"].unique().tolist())
        selected_category = st.selectbox("Category", category_options)
    with col4:
        if selected_category != "All":
            subcat_pool = sorted(df[df["category"] == selected_category]["subcategory"].unique().tolist())
        else:
            subcat_pool = sorted(df["subcategory"].unique().tolist())
        subcategory_options = ["All"] + subcat_pool
        selected_subcategory = st.selectbox("Subcategory", subcategory_options)
    with col5:
        min_amount = st.number_input("Min amount", value=None, placeholder="e.g. -50", step=1.0)
    with col6:
        max_amount = st.number_input("Max amount", value=None, placeholder="e.g. 200", step=1.0)

    table_df = df.copy()

    if search:
        table_df = table_df[
            table_df["description"].str.contains(search, case=False, na=False)
        ]
    if selected_account != "All":
        table_df = table_df[table_df["account_name"] == selected_account]
    if selected_category != "All":
        table_df = table_df[table_df["category"] == selected_category]
    if selected_subcategory != "All":
        table_df = table_df[table_df["subcategory"] == selected_subcategory]
    if min_amount is not None:
        table_df = table_df[table_df["spend"] >= min_amount]
    if max_amount is not None:
        table_df = table_df[table_df["spend"] <= max_amount]

    table_df = table_df.sort_values("date", ascending=False)
    table_df["date"] = table_df["date"].dt.strftime("%Y-%m-%d")
    table_df["Amount"] = table_df["spend"].apply(
        lambda x: f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"
    )

    subcat_options = all_subcategories.copy()
    if "Excluded" not in subcat_options:
        subcat_options = sorted(subcat_options + ["Excluded"])

    display_df = table_df[["id", "date", "description", "Amount", "subcategory", "category", "account_name"]].rename(columns={
        "date":         "Date",
        "description":  "Description",
        "subcategory":  "Subcategory",
        "category":     "Category",
        "account_name": "Account",
    })

    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        height=400,
        hide_index=True,
        disabled=["id", "Date", "Description", "Amount", "Category", "Account"],
        column_config={
            "id": None,
            "Subcategory": st.column_config.SelectboxColumn(
                "Subcategory",
                options=subcat_options,
                required=True,
            ),
        },
        key="transaction_table",
    )

    changes = edited_df[edited_df["Subcategory"] != display_df["Subcategory"]]
    if not changes.empty:
        conn = get_connection()
        cursor = conn.cursor()
        saved = 0
        for _, row in changes.iterrows():
            cursor.execute("SELECT id, category_id FROM subcategories WHERE name = ?", (row["Subcategory"],))
            subcat_row = cursor.fetchone()
            if subcat_row:
                cursor.execute("""
                    UPDATE transactions
                    SET subcategory_id = ?, manually_categorized = 1
                    WHERE id = ?
                """, (subcat_row["id"], row["id"]))
                saved += 1
        conn.commit()
        conn.close()

        if saved:
            st.success(f"{saved} transaction(s) updated.")
            st.cache_data.clear()
            st.rerun()

    st.caption(f"{len(table_df):,} transactions")


# ── Home page ─────────────────────────────────────────────────────────────────
def render_home():
    st.title("👋 Welcome to your Personal Spending Dashboard")
    st.markdown(
        "This app brings all your bank and credit card transactions into one place, "
        "automatically sorts them into spending categories, and helps you see exactly "
        "where your money is going — month by month."
    )

    st.divider()

    st.subheader("🚀 Getting started")
    st.markdown("""
    Here's the recommended flow to get up and running:

    **1. Set up your categories** *(Categories page)*  
    Head to the Categories page and make the spending categories your own. The app comes
    with a set of defaults, but you'll want to add keywords that match the way your
    specific banks and merchants describe transactions.

    **2. Import your transactions** *(Import page)*  
    Download a CSV export from your bank or card provider and upload it on the Import page.
    Select the right source for each file and the app takes care of the rest — parsing,
    categorizing, and skipping any duplicates automatically.

    **3. Review and clean up** *(Dashboard → Transactions table)*  
    After importing, check the Transactions table for anything labeled **Uncategorized**
    and assign it a subcategory directly in the table. Those overrides are saved permanently
    and won't be touched if you recategorize later.

    **4. Explore your spending** *(Dashboard)*  
    Filter by date, category, or account from the sidebar. The charts update live so you
    can zero in on exactly what you want to see.
    """)

    st.divider()

    st.subheader("🔁 Monthly routine")
    st.markdown(
        "Once you're set up, keeping the app current takes just a few minutes each month:"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.info("**① Download**\nExport CSVs from Chase, Amex, and Venmo for the month")
    col2.info("**② Import**\nUpload each file on the Import page — duplicates are skipped automatically")
    col3.info("**③ Review**\nCheck for new Uncategorized transactions and assign them")
    col4.info("**④ Explore**\nOpen the Dashboard and see how the month looked")

    st.caption(
        "💡 Venmo only allows monthly CSV exports — download one file per month "
        "and import each separately."
    )

    st.divider()

    st.subheader("📄 Supported sources")
    st.markdown("""
    | Source | Where to download |
    |---|---|
    | Chase Checking | chase.com → Accounts → Download |
    | Chase Credit | chase.com → Accounts → Download |
    | American Express | americanexpress.com → Statements → Download CSV |
    | Venmo | venmo.com → Statements → Download CSV |
    """)

    st.divider()

    st.subheader("🗂️ What's in the app")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📊 Dashboard**")
        st.caption(
            "Your main spending view — summary metrics, a monthly trend chart, "
            "a category breakdown, and a searchable transaction table with inline editing."
        )
    with col2:
        st.markdown("**📥 Import**")
        st.caption(
            "Upload CSVs from your bank or card provider. "
            "The app handles parsing, deduplication, and categorization automatically."
        )
    with col3:
        st.markdown("**🗂️ Categories**")
        st.caption(
            "Customize the categories and keywords used to sort your transactions. "
            "Changes take effect on future imports, or across all existing transactions "
            "if you choose Save & Recategorize."
        )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    df = load_transactions()
    colors = get_category_colors()

    # Determine which page to show via sidebar nav
    st.sidebar.title("💰 Personal Spending")

    theme = st.sidebar.selectbox(
        "Theme",
        ["Linear/Notion Dark", "Arctic", "Dracula"],
        index=1
    )
    inject_theme(theme)

    st.sidebar.divider()
    page = st.sidebar.radio("Navigate", ["🏠 Home", "📊 Dashboard"], label_visibility="collapsed")

    if page == "🏠 Home":
        render_home()
        return

    # ── Dashboard ─────────────────────────────────────────────────────────────
    st.title("💰 Personal Spending Dashboard")

    st.sidebar.title("Filters")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    view_by = st.sidebar.radio("View by", ["Category", "Subcategory"], horizontal=True)

    all_categories = sorted(df["category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=all_categories,
        default=[c for c in all_categories if c not in ("Income", "Uncategorized")],
    )

    filtered_subcats = sorted(
        df[df["category"].isin(selected_categories)]["subcategory"].unique().tolist()
    )
    all_subcategories = sorted(df["subcategory"].unique().tolist())
    selected_subcategories = st.sidebar.multiselect(
        "Subcategories",
        options=filtered_subcats,
        default=filtered_subcats,
    )

    all_accounts = sorted(df["account_name"].unique().tolist())
    selected_accounts = st.sidebar.multiselect(
        "Accounts",
        options=all_accounts,
        default=all_accounts,
    )

    filtered_df = df[
        (df["date"] >= pd.Timestamp(start_date)) &
        (df["date"] <= pd.Timestamp(end_date)) &
        (df["category"].isin(selected_categories)) &
        (df["subcategory"].isin(selected_subcategories)) &
        (df["account_name"].isin(selected_accounts))
    ]

    render_summary_metrics(filtered_df)
    st.divider()
    render_spending_trend(filtered_df, view_by, colors)
    st.divider()
    render_monthly_breakdown(filtered_df, view_by, colors)
    st.divider()
    render_transaction_table(filtered_df, all_subcategories)


if __name__ == "__main__":
    main()
