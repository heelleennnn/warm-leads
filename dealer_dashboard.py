import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------
# PAGE SETUP
# --------------------------------
st.set_page_config(
    page_title="Digital Dealer Leads Dashboard",
    layout="wide"
)

# --------------------------------
# GLOBAL CHART SETTINGS
# --------------------------------
CHART_HEIGHT = 450  # all charts same height

# --------------------------------
# LOAD DATA
# --------------------------------
def load_data():
    df = pd.read_csv(
        "cleaned_digital_dealer_full.csv",
        parse_dates=["Lead_Date", "Week_Start"]
    )
    df = df.rename(columns={"Dealer/Website": "Dealer"})
    return df

df = load_data()

# Clean up Location text
if "Location" in df.columns:
    df["Location_clean"] = (
        df["Location"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.title()
    )
else:
    df["Location_clean"] = ""

# Required columns
required_cols = ["Lead_Date", "Week_Start", "Dealer", "STATE", "Location_clean"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

st.caption(f"Total rows in CSV: {len(df)}")

# --------------------------------
# TITLE
# --------------------------------
st.title("📊 Digital Dealer Leads Dashboard")

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

# ----- Date range filter -----
min_date = df["Lead_Date"].min().date()
max_date = df["Lead_Date"].max().date()

date_mode = st.sidebar.radio(
    "Date range",
    ["Custom range", "Last 7 days", "Last 30 days", "Last 90 days"],
    index=0
)

if date_mode == "Custom range":
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date, max_date)
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range
        end_date = date_range
else:
    days_lookup = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
    days = days_lookup[date_mode]
    start_date = max_date - pd.Timedelta(days=days - 1)
    if start_date < min_date:
        start_date = min_date
    end_date = max_date
    st.sidebar.info(f"{start_date} → {end_date}")

# ----- State filter -----
states = sorted(df["STATE"].dropna().unique())
select_all_states = st.sidebar.checkbox("Select All States", value=True)

if select_all_states:
    selected_states = states
else:
    selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)

# ----- Location filter -----
df_for_locations = df if select_all_states else df[df["STATE"].isin(selected_states)]
all_locations = sorted(df_for_locations["Location_clean"].dropna().unique())

select_all_locations = st.sidebar.checkbox(
    "Select All Locations (after state filter)", value=True
)

if select_all_locations:
    selected_locations = all_locations
else:
    selected_locations = st.sidebar.multiselect(
        "Select Location(s)",
        all_locations,
        default=all_locations,
        key="location_multiselect"
    )

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered = df.copy()

start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date)

filtered = filtered[
    (filtered["Lead_Date"] >= start_ts) &
    (filtered["Lead_Date"] <= end_ts)
]

if not select_all_states:
    filtered = filtered[filtered["STATE"].isin(selected_states)]

if not select_all_locations:
    filtered = filtered[filtered["Location_clean"].isin(selected_locations)]

st.caption(f"Rows after filters: {len(filtered)}")

# --------------------------------
# KPI ROW
# --------------------------------
if not filtered.empty:
    total_leads = len(filtered)
    date_span_days = (
        filtered["Lead_Date"].max().date()
        - filtered["Lead_Date"].min().date()
    ).days + 1
    avg_leads_per_day = total_leads / date_span_days if date_span_days > 0 else 0
    num_dealers = filtered["Dealer"].nunique()
else:
    total_leads = avg_leads_per_day = num_dealers = 0

kpi1, kpi2, kpi3 = st.columns(3)

kpi1.metric("Total Leads", f"{total_leads:,}")
kpi2.metric("Avg Leads per Day", f"{avg_leads_per_day:.1f}")
kpi3.metric("Number of Dealers", f"{num_dealers:,}")

st.markdown("---")

# --------------------------------
# MAIN CONTENT
# --------------------------------
if not filtered.empty:

    # ---------- 1. Weekly Leads Line Chart ----------
    weekly_counts = (
        filtered
        .groupby("Week_Start").size()
        .reset_index(name="Leads")
        .sort_values("Week_Start")
    )

    fig_week = px.line(
        weekly_counts,
        x="Week_Start",
        y="Leads",
        markers=True,
        title="Leads Over Time (Weekly)",
        height=CHART_HEIGHT
    )
    fig_week.update_traces(line_color="#324AB2", marker_color="#324AB2")
    fig_week.update_layout(
        xaxis_title="State",
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )
    st.plotly_chart(fig_week, use_container_width=True)

    # ---------- 2. Individual Dealer ----------
    dealer_counts = (
        filtered
        .groupby("Dealer").size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_dealer = px.bar(
        dealer_counts.head(15),
        x="Dealer",
        y="Leads",
        title="Leads by Website",
        height=CHART_HEIGHT
    )
    fig_dealer.update_traces(marker_color="#0073CF")
    fig_dealer.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )
    st.plotly_chart(fig_dealer, use_container_width=True)

    # ---------- 3. Specific Locations ----------
    location_counts = (
        filtered
        .groupby("Location_clean").size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_location = px.bar(
        location_counts.head(25),
        x="Location_clean",
        y="Leads",
        title="Leads by Individual Dealer",
        height=CHART_HEIGHT
    )
    fig_location.update_traces(marker_color="#3E8EDE")
    fig_location.update_layout(
        xaxis_title="Specific Dealers",
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )
    st.plotly_chart(fig_location, use_container_width=True)

    # ---------- 4. Leads by State ----------
    state_counts = (
        filtered
        .groupby("STATE").size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_state = px.bar(
        state_counts,
        x="STATE",
        y="Leads",
        title="Leads by State",
        height=CHART_HEIGHT
    )
    fig_state.update_traces(marker_color="#76c7ff")
    fig_state.update_layout(
        xaxis_title="State",
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )
    st.plotly_chart(fig_state, use_container_width=True)

else:
    st.info("No data available for selected filters.")
