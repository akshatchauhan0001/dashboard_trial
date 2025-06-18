import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import altair as alt
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

# === GOOGLE SHEETS SETUP ===
@st.cache_data(ttl=3600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # creds = ServiceAccountCredentials.from_json_keyfile_name("dashboard1-463207-1a30e1730fbc.json", scope)
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("meta_data_fetching").worksheet("May-June Dashboard")
    data = pd.DataFrame(sheet.get_all_records())

    # Clean numeric columns
    numeric_cols = [
    'Cost (USD)',
    'Return on ad spend (ROAS)',
    'CPM (cost per 1000 impressions)',
    'Cost per action (CPA)',
    'Website purchases conversion value',
    'CTR (link click-through rate)',
    'Impressions',
    'Link clicks'  # ✅ Add this line
]
    for col in numeric_cols:
        data[col] = (
            data[col].astype(str)
            .str.replace('%', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.extract(r'(\d+\.?\d*)')[0]
            .astype(float)
        )

    data['Date'] = pd.to_datetime(data['Date'])
    return data

# === LOAD DATA ===
st.title("📊 Meta Ads Performance Dashboard")
data = load_data()

# === FILTERS ===
campaigns = st.multiselect("Select Campaign(s):", options=data["Campaign name"].unique(), default=data["Campaign name"].unique())
filtered_data = data[data["Campaign name"].isin(campaigns)]

# === KPIs ===
st.subheader("🔹 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Spend", f"${filtered_data['Cost (USD)'].sum():,.2f}")
col2.metric("Total Impressions", f"{filtered_data['Impressions'].sum():,.0f}")
col3.metric("Average ROAS", f"{filtered_data['Return on ad spend (ROAS)'].mean():.2f}")

col4, col5, col6 = st.columns(3)
ctr_avg = filtered_data['CTR (link click-through rate)'].mean()
col4.metric("Average CTR (%)", f"{ctr_avg:.2f}")

cpa_avg = filtered_data['Cost per action (CPA)'].mean()
col5.metric("Avg CPA", f"${cpa_avg:.2f}")

revenue = filtered_data['Website purchases conversion value'].sum()
col6.metric("Total Revenue", f"${revenue:,.2f}")

# # === 📈 Spend vs Sales Over Time ===
# st.subheader("📈 Spend and Sales Over Time")
# time_series = filtered_data.groupby("Date")[['Cost (USD)', 'Website purchases conversion value']].sum().reset_index()
# fig1 = px.bar(time_series, x='Date', y='Cost (USD)', labels={'Cost (USD)': 'Spend'}, opacity=0.6)
# fig1.add_scatter(x=time_series['Date'], y=time_series['Website purchases conversion value'], mode='lines+markers', name='Sales', yaxis='y2')
# st.plotly_chart(fig1, use_container_width=True)

# === 📈 Spend Over Time ===
st.subheader("📈 Spend Over Time")
time_series = filtered_data.groupby("Date")[['Cost (USD)']].sum().reset_index()

fig1 = px.bar(
    time_series,
    x='Date',
    y='Cost (USD)',
    labels={'Cost (USD)': 'Spend'},
    opacity=0.85,
    title='Daily Ad Spend',
    color_discrete_sequence=['#1f77b4']  # Optional: custom bar color
)

fig1.update_layout(
    xaxis_title='Date',
    yaxis_title='Spend (USD)',
    bargap=0.2,
    height=400
)

st.plotly_chart(fig1, use_container_width=True)


# === 📊 ROAS by Campaign ===
st.subheader("📊 ROAS by Campaign")
campaign_roas = filtered_data.groupby('Campaign name')['Return on ad spend (ROAS)'].mean().reset_index()
campaign_roas['Color'] = campaign_roas['Return on ad spend (ROAS)'].apply(lambda x: 'green' if x > 3 else 'orange' if x >= 1 else 'red')
fig2 = px.bar(campaign_roas, x='Campaign name', y='Return on ad spend (ROAS)', color='Color', color_discrete_map='identity')
st.plotly_chart(fig2, use_container_width=True)

# === 📊 Revenue Share by Campaign ===
st.subheader("📊 Revenue Share by Campaign")
revenue_share = filtered_data.groupby('Campaign name')['Website purchases conversion value'].sum().reset_index()
fig3 = px.pie(revenue_share, values='Website purchases conversion value', names='Campaign name')
st.plotly_chart(fig3, use_container_width=True)

# === 📊 Budget Utilization: Spend & ROAS by Campaign ===
st.subheader("📊 Budget Utilization by Campaign")

# Prepare summary data
util_data = (
    filtered_data.groupby("Campaign name")
    .agg({
        "Cost (USD)": "sum",
        "Return on ad spend (ROAS)": "mean"
    })
    .reset_index()
)

# Melt data for grouped bar chart
util_melted = util_data.melt(id_vars="Campaign name", var_name="Metric", value_name="Value")

# Bar chart
util_chart = alt.Chart(util_melted).mark_bar().encode(
    x=alt.X('Campaign name:N', title="Campaign", sort='-y'),
    y=alt.Y('Value:Q', title="Value"),
    color=alt.Color('Metric:N', scale=alt.Scale(scheme='category10')),
    tooltip=['Campaign name', 'Metric', 'Value']
).properties(
    height=400
).configure_axisX(
    labelAngle=-40
)

st.altair_chart(util_chart, use_container_width=True)


# === 📊 Campaign Performance: CTR, CPA, ROAS ===
st.subheader("📊 Campaign Performance Metrics")

# Prepare summary data
perf_data = (
    filtered_data.groupby("Campaign name")
    .agg({
        "CTR (link click-through rate)": "mean",
        "Cost per action (CPA)": "mean",
        "Return on ad spend (ROAS)": "mean"
    })
    .reset_index()
)

# Melt data for grouped bar chart
perf_melted = perf_data.melt(id_vars="Campaign name", var_name="Metric", value_name="Value")

# Grouped bar chart
perf_chart = alt.Chart(perf_melted).mark_bar().encode(
    x=alt.X('Campaign name:N', title="Campaign", sort='-y'),
    y=alt.Y('Value:Q'),
    color=alt.Color('Metric:N', scale=alt.Scale(scheme='tableau20')),
    tooltip=['Campaign name', 'Metric', 'Value']
).properties(
    height=400
).configure_axisX(
    labelAngle=-40
)

st.altair_chart(perf_chart, use_container_width=True)


# === 📅 Day-wise ROAS ===
st.subheader("📅 Day-wise ROAS")
filtered_data['Weekday'] = filtered_data['Date'].dt.day_name()
weekday_roas = filtered_data.groupby('Weekday')['Return on ad spend (ROAS)'].mean().reindex([
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
]).reset_index()
fig6 = px.bar(weekday_roas, x='Weekday', y='Return on ad spend (ROAS)')
st.plotly_chart(fig6, use_container_width=True)

# === 💡 Simple Conversion Funnel ===
st.subheader("💡 Conversion Funnel")

# Safe numeric conversion (if needed)
total_impressions = filtered_data['Impressions'].sum()
total_clicks = filtered_data['Link clicks'].sum()
total_conversions = filtered_data['Website purchases conversion value'].count()

# Conversion rates
ctr = (total_clicks / total_impressions) * 100 if total_impressions else 0
cvr = (total_conversions / total_clicks) * 100 if total_clicks else 0

# Show KPIs
col1, col2, col3 = st.columns(3)
col1.metric("👀 Impressions", f"{total_impressions:,.0f}")
col2.metric("🖱️ Clicks", f"{total_clicks:,.0f}", f"{ctr:.2f}% CTR")
col3.metric("🛒 Conversions", f"{total_conversions:,}", f"{cvr:.2f}% CVR")

# Optional: Visual bar to show the step-down
funnel_df = pd.DataFrame({
    'Stage': ['Impressions', 'Clicks', 'Conversions'],
    'Count': [total_impressions, total_clicks, total_conversions]
})

funnel_chart = alt.Chart(funnel_df).mark_bar(size=40).encode(
    x=alt.X('Count:Q', title='Volume'),
    y=alt.Y('Stage:N', sort=['Impressions', 'Clicks', 'Conversions']),
    color=alt.Color('Stage:N', scale=alt.Scale(scheme='tealblues'))
).properties(height=200)

st.altair_chart(funnel_chart, use_container_width=True)



# === 🚦 Performance Heatmap ===
st.subheader("🚦 Performance Heatmap")
heatmap_data = filtered_data.groupby('Campaign name')[['Return on ad spend (ROAS)', 'CTR (link click-through rate)', 'Cost per action (CPA)']].mean()
fig8, ax = plt.subplots()
sns.heatmap(heatmap_data, cmap="YlGnBu", annot=True, fmt=".2f", ax=ax)
st.pyplot(fig8)

# === RAW DATA ===
with st.expander("🧾 Show Raw Data"):
    st.dataframe(filtered_data)
