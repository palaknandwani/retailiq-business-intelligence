
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3
from pathlib import Path

st.set_page_config(
    page_title="RetailIQ | Business Intelligence",
    page_icon="🛍️",
    layout="wide"
)

# ==========================================
# PREMIUM DESIGN
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #0B1120;
    color: #F1F5F9;
}

section[data-testid="stSidebar"] {
    background: #111B2E;
    border-right: 1px solid #263449;
}

section[data-testid="stSidebar"] h1 {
    color: #60A5FA;
    font-weight: 800;
}

h1, h2, h3 {
    color: #F8FAFC;
    font-weight: 800;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #17243B, #1E3150);
    border: 1px solid #334968;
    padding: 20px;
    border-radius: 16px;
}

div[data-testid="stMetricLabel"] {
    color: #94A3B8;
}

div[data-testid="stMetricValue"] {
    color: #60A5FA;
    font-weight: 800;
}

.stButton button, .stDownloadButton button {
    background: #2563EB;
    color: white;
    border-radius: 9px;
    font-weight: 600;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 12px;
}

hr {
    border-color: #334155;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# GENERATE RETAIL DATA
# ==========================================

@st.cache_data
def generate_data():

    np.random.seed(42)

    n = 1500

    dates = pd.to_datetime(
        np.random.choice(
            pd.date_range("2025-01-01", "2025-12-31"),
            n
        )
    )

    categories = [
        "Electronics", "Fashion", "Home", "Beauty", "Sports"
    ]

    regions = ["North", "South", "East", "West", "Central"]

    products = {
        "Electronics": ["Headphones", "Laptop", "Smartphone"],
        "Fashion": ["Shoes", "Jacket", "T-Shirt"],
        "Home": ["Furniture", "Lamp", "Kitchen Set"],
        "Beauty": ["Skincare", "Perfume", "Makeup"],
        "Sports": ["Yoga Mat", "Dumbbells", "Sports Shoes"]
    }

    rows = []

    for i in range(n):

        category = np.random.choice(categories)
        product = np.random.choice(products[category])

        quantity = np.random.randint(1, 6)
        price = np.random.randint(300, 15000)
        discount = np.random.choice([0, 5, 10, 15, 20])

        revenue = quantity * price * (1 - discount / 100)
        cost = revenue * np.random.uniform(0.45, 0.75)

        rows.append({
            "Order_ID": f"ORD{i+1001}",
            "Date": dates[i],
            "Customer_ID": f"CUST{np.random.randint(1, 401)}",
            "Region": np.random.choice(regions),
            "Category": category,
            "Product": product,
            "Quantity": quantity,
            "Unit_Price": price,
            "Discount": discount,
            "Revenue": round(revenue, 2),
            "Profit": round(revenue - cost, 2)
        })

    return pd.DataFrame(rows)


df = generate_data()

# ==========================================
# SQLITE DATABASE
# ==========================================

db_path = Path(__file__).parent / "retailiq.db"

with sqlite3.connect(db_path) as conn:

    df.to_sql("sales", conn, if_exists="replace", index=False)

    sql_summary = pd.read_sql_query("""
        SELECT
            Category,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Revenue,
            ROUND(SUM(Profit), 2) AS Profit
        FROM sales
        GROUP BY Category
        ORDER BY Revenue DESC
    """, conn)

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("🛍️ RetailIQ")
st.sidebar.caption("BUSINESS INTELLIGENCE PLATFORM")
st.sidebar.divider()

page = st.sidebar.radio(
    "EXPLORE DASHBOARD",
    [
        "Executive Overview",
        "Sales Analytics",
        "Product Analytics",
        "Customer Analytics",
        "Regional Analytics",
        "Business Insights"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("Data Filters")

regions = st.sidebar.multiselect(
    "Select Regions",
    sorted(df["Region"].unique()),
    default=sorted(df["Region"].unique())
)

categories = st.sidebar.multiselect(
    "Select Categories",
    sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique())
)

st.sidebar.subheader("Date Range")

min_date = df["Date"].min()
max_date = df["Date"].max()

default_start = max(
    min_date,
    max_date - pd.Timedelta(days=89)
)

selected_dates = st.sidebar.date_input(
    "Choose Analysis Period",
    value=(default_start.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)

# ==========================================
# FILTER DATA
# ==========================================

if len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = default_start.date()
    end_date = max_date.date()

if start_date > end_date:
    st.error("Please select a valid date range.")
    st.stop()

filtered = df[
    df["Region"].isin(regions) &
    df["Category"].isin(categories) &
    df["Date"].dt.date.between(start_date, end_date)
].copy()

period_days = (end_date - start_date).days + 1

previous_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
previous_start = previous_end - pd.Timedelta(days=period_days - 1)

previous_df = df[
    df["Region"].isin(regions) &
    df["Category"].isin(categories) &
    df["Date"].between(
        previous_start,
        previous_end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    )
].copy()

# ==========================================
# KPI CALCULATIONS
# ==========================================

revenue = filtered["Revenue"].sum()
profit = filtered["Profit"].sum()
orders = len(filtered)
customers = filtered["Customer_ID"].nunique()

avg_order = revenue / orders if orders else 0
margin = profit / revenue * 100 if revenue else 0

previous_revenue = previous_df["Revenue"].sum()
previous_profit = previous_df["Profit"].sum()
previous_orders = len(previous_df)
previous_customers = previous_df["Customer_ID"].nunique()

def calculate_growth(current, previous):

    if previous == 0:
        return None

    growth = (current - previous) / previous * 100

    return f"{growth:+.1f}% vs previous period"

revenue_growth = calculate_growth(revenue, previous_revenue)
profit_growth = calculate_growth(profit, previous_profit)
orders_growth = calculate_growth(orders, previous_orders)
customers_growth = calculate_growth(customers, previous_customers)

st.sidebar.divider()
st.sidebar.caption("2025 | SYNTHETIC DEMO DATA")
st.sidebar.caption("Developed by Palak Nandwani")

# ==========================================
# HEADER
# ==========================================

st.markdown(
    "<h1>RetailIQ <span style='color:#60A5FA'>.</span></h1>",
    unsafe_allow_html=True
)

st.caption("RETAIL PERFORMANCE & BUSINESS INTELLIGENCE")

st.caption(f"Analysis period: {start_date} to {end_date}")

st.divider()

chart_template = "plotly_dark"

# ==========================================
# COMMON MONTHLY DATA
# ==========================================

if not filtered.empty:

    monthly = (
        filtered.assign(
            Month=filtered["Date"].dt.to_period("M").astype(str)
        )
        .groupby("Month")
        .agg(
            Revenue=("Revenue", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order_ID", "count")
        )
        .reset_index()
    )

# ==========================================
# 1. EXECUTIVE OVERVIEW
# ==========================================

if page == "Executive Overview":

    st.subheader("Executive Overview")
    st.write("Your business performance at a glance.")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Revenue", f"₹{revenue:,.0f}", delta=revenue_growth)
    c2.metric("Total Profit", f"₹{profit:,.0f}", delta=profit_growth)
    c3.metric("Total Orders", f"{orders:,}", delta=orders_growth)
    c4.metric("Customers", f"{customers:,}", delta=customers_growth)

    st.divider()

    if not filtered.empty:

        left, right = st.columns(2)

        with left:

            fig = px.line(
                monthly,
                x="Month",
                y="Revenue",
                markers=True,
                title="Monthly Revenue Trend",
                template=chart_template
            )

            fig.update_traces(line_color="#60A5FA")
            st.plotly_chart(fig, width="stretch")

        with right:

            category_data = (
                filtered.groupby("Category")["Revenue"]
                .sum().reset_index()
            )

            fig = px.pie(
                category_data,
                names="Category",
                values="Revenue",
                hole=0.55,
                title="Revenue by Category",
                template=chart_template
            )

            st.plotly_chart(fig, width="stretch")

        st.subheader("Monthly Performance")

        st.dataframe(monthly, width="stretch", hide_index=True)

    else:
        st.warning("No data available for these filters.")

# ==========================================
# 2. SALES ANALYTICS
# ==========================================

elif page == "Sales Analytics":

    st.subheader("Sales Intelligence")

    c1, c2, c3 = st.columns(3)

    c1.metric("Revenue", f"₹{revenue:,.0f}", delta=revenue_growth)
    c2.metric("Profit", f"₹{profit:,.0f}", delta=profit_growth)
    c3.metric("Average Order Value", f"₹{avg_order:,.0f}")

    st.metric("Profit Margin", f"{margin:.2f}%")

    if not filtered.empty:

        fig = px.bar(
            monthly,
            x="Month",
            y=["Revenue", "Profit"],
            barmode="group",
            title="Revenue vs Profit",
            template=chart_template
        )

        st.plotly_chart(fig, width="stretch")

        fig = px.line(
            monthly,
            x="Month",
            y="Orders",
            markers=True,
            title="Monthly Order Volume",
            template=chart_template
        )

        st.plotly_chart(fig, width="stretch")

# ==========================================
# 3. PRODUCT ANALYTICS
# ==========================================

elif page == "Product Analytics":

    st.subheader("Product Performance")

    if not filtered.empty:

        product_data = (
            filtered.groupby("Product")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum"),
                Units_Sold=("Quantity", "sum")
            )
            .reset_index()
            .sort_values("Revenue", ascending=False)
        )

        left, right = st.columns(2)

        with left:

            fig = px.bar(
                product_data.head(10),
                x="Revenue",
                y="Product",
                orientation="h",
                title="Top Products by Revenue",
                template=chart_template
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            st.plotly_chart(fig, width="stretch")

        with right:

            fig = px.bar(
                product_data,
                x="Product",
                y="Profit",
                title="Product Profitability",
                template=chart_template
            )

            st.plotly_chart(fig, width="stretch")

        st.subheader("Product Performance Table")

        st.dataframe(product_data, width="stretch", hide_index=True)

    else:
        st.warning("No data available.")

# ==========================================
# 4. CUSTOMER ANALYTICS
# ==========================================

elif page == "Customer Analytics":

    st.subheader("Customer Intelligence")

    if not filtered.empty:

        customer_data = (
            filtered.groupby("Customer_ID")
            .agg(
                Orders=("Order_ID", "count"),
                Spending=("Revenue", "sum"),
                Profit=("Profit", "sum")
            )
            .reset_index()
        )

        customer_data["Segment"] = pd.cut(
            customer_data["Spending"],
            bins=[-1, 10000, 30000, float("inf")],
            labels=["Low Value", "Medium Value", "High Value"]
        )

        repeat_customers = (customer_data["Orders"] > 1).sum()
        repeat_rate = repeat_customers / len(customer_data) * 100

        c1, c2, c3 = st.columns(3)

        c1.metric("Unique Customers", len(customer_data))
        c2.metric("Repeat Purchase Rate", f"{repeat_rate:.1f}%")
        c3.metric(
            "Average Spending",
            f"₹{customer_data['Spending'].mean():,.0f}"
        )

        segment_data = (
            customer_data["Segment"]
            .value_counts()
            .reset_index()
        )

        segment_data.columns = ["Segment", "Customers"]

        fig = px.pie(
            segment_data,
            names="Segment",
            values="Customers",
            hole=0.5,
            title="Customer Segmentation",
            template=chart_template
        )

        st.plotly_chart(fig, width="stretch")

        st.subheader("Top Customers")

        st.dataframe(
            customer_data.sort_values(
                "Spending", ascending=False
            ).head(20),
            width="stretch",
            hide_index=True
        )

        st.caption(
            "Repeat purchase rate measures customers with multiple "
            "orders in the selected period; it is not a cohort retention metric."
        )

    else:
        st.warning("No data available.")

# ==========================================
# 5. REGIONAL ANALYTICS
# ==========================================

elif page == "Regional Analytics":

    st.subheader("Regional Performance")

    if not filtered.empty:

        regional = (
            filtered.groupby("Region")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum"),
                Orders=("Order_ID", "count")
            )
            .reset_index()
        )

        best_region = regional.loc[
            regional["Revenue"].idxmax(), "Region"
        ]

        weakest_region = regional.loc[
            regional["Revenue"].idxmin(), "Region"
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric("Regions", len(regional))
        c2.metric("Top Region", best_region)
        c3.metric("Lowest Revenue Region", weakest_region)

        left, right = st.columns(2)

        with left:

            fig = px.bar(
                regional,
                x="Region",
                y="Revenue",
                color="Region",
                title="Revenue by Region",
                template=chart_template
            )

            st.plotly_chart(fig, width="stretch")

        with right:

            fig = px.bar(
                regional,
                x="Region",
                y="Profit",
                color="Region",
                title="Profit by Region",
                template=chart_template
            )

            st.plotly_chart(fig, width="stretch")

        st.dataframe(regional, width="stretch", hide_index=True)

    else:
        st.warning("No data available.")

# ==========================================
# 6. BUSINESS INTELLIGENCE INSIGHTS
# ==========================================

elif page == "Business Insights":

    st.subheader("Business Intelligence Center")

    st.write(
        "Discover opportunities, understand risks and "
        "identify areas for business improvement."
    )

    if not filtered.empty:

        category_data = (
            filtered.groupby("Category")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum")
            )
            .reset_index()
        )

        product_data = (
            filtered.groupby("Product")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum")
            )
            .reset_index()
        )

        region_data = (
            filtered.groupby("Region")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum")
            )
            .reset_index()
        )

        best_category = category_data.loc[
            category_data["Revenue"].idxmax()
        ]

        best_profit_category = category_data.loc[
            category_data["Profit"].idxmax()
        ]

        best_product = product_data.loc[
            product_data["Revenue"].idxmax()
        ]

        best_region = region_data.loc[
            region_data["Revenue"].idxmax()
        ]

        weakest_region = region_data.loc[
            region_data["Revenue"].idxmin()
        ]

        lowest_margin_category = category_data.assign(
            Margin=category_data["Profit"] /
            category_data["Revenue"].replace(0, np.nan) * 100
        ).dropna().sort_values("Margin").head(1)

        repeat_rate = 0

        if customers > 0:
            repeat_rate = (
                (filtered.groupby("Customer_ID")["Order_ID"].count() > 1)
                .sum() / customers * 100
            )

        # Insight cards
        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Highest Revenue Category",
                best_category["Category"],
                f"₹{best_category['Revenue']:,.0f}"
            )

            st.metric(
                "Most Profitable Category",
                best_profit_category["Category"],
                f"₹{best_profit_category['Profit']:,.0f}"
            )

        with c2:

            st.metric(
                "Top Revenue Product",
                best_product["Product"],
                f"₹{best_product['Revenue']:,.0f}"
            )

            st.metric(
                "Best Performing Region",
                best_region["Region"],
                f"₹{best_region['Revenue']:,.0f}"
            )

        st.divider()

        st.subheader("Business Recommendations")

        st.success(
            f"**Growth opportunity:** {best_category['Category']} "
            f"leads revenue generation. Review its successful "
            f"products and consider expanding this category."
        )

        st.info(
            f"**Regional opportunity:** {weakest_region['Region']} "
            f"has the lowest revenue among the selected regions. "
            f"Investigate product demand, customer reach and pricing."
        )

        if not lowest_margin_category.empty:

            low_category = lowest_margin_category.iloc[0]

            st.warning(
                f"**Profitability watch:** {low_category['Category']} "
                f"has the lowest observed category profit margin "
                f"({low_category['Margin']:.1f}%). Review discounts "
                f"and costs before increasing sales."
            )

        if repeat_rate < 30:

            st.info(
                f"**Customer opportunity:** Repeat purchase rate "
                f"is {repeat_rate:.1f}%. Test loyalty offers and "
                f"post-purchase engagement."
            )

        else:

            st.success(
                f"**Customer opportunity:** Repeat purchase rate "
                f"is {repeat_rate:.1f}%. Analyse what encourages "
                f"customers to purchase again."
            )

        st.divider()

        st.subheader("Category Profitability Matrix")

        category_data["Profit Margin"] = (
            category_data["Profit"] /
            category_data["Revenue"].replace(0, np.nan) * 100
        )

        fig = px.scatter(
            category_data,
            x="Revenue",
            y="Profit Margin",
            size="Profit",
            color="Category",
            hover_name="Category",
            title="Revenue vs Profit Margin",
            template=chart_template
        )

        st.plotly_chart(fig, width="stretch")

        st.caption(
            "Recommendations are descriptive, rule-based insights "
            "generated from synthetic demonstration data. "
            "They are not causal findings or predictive forecasts."
        )

    else:

        st.warning("No data available for generating insights.")

# ==========================================
# SQL ANALYSIS
# ==========================================

with st.expander("🗄️ Explore SQL Business Analysis"):

    st.write("Category-level analysis using SQLite.")

    st.dataframe(
        sql_summary,
        width="stretch",
        hide_index=True
    )

    st.code("""
SELECT
    Category,
    COUNT(*) AS Orders,
    ROUND(SUM(Revenue), 2) AS Revenue,
    ROUND(SUM(Profit), 2) AS Profit
FROM sales
GROUP BY Category
ORDER BY Revenue DESC;
    """, language="sql")

# ==========================================
# DOWNLOAD REPORT
# ==========================================

st.divider()

st.subheader("Export Business Report")

csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇ Download Sales Report (CSV)",
    data=csv_data,
    file_name="retailiq_sales_report.csv",
    mime="text/csv"
)

st.caption(
    "RetailIQ | Python • Pandas • SQLite • Plotly • Streamlit"
)

st.caption(
    "Portfolio project by Palak Nandwani | "
    "All transaction data is synthetic demonstration data."
)
