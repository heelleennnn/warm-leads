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
# @st.cache_data   # comment this out while debugging
def load_data():
    df = pd.read_csv(
        "cleaned_digital_dealer_full.csv",
        parse_dates=["Lead_Date", "Week_Start"]
    )
    df = df.rename(columns={"Dealer/Website": "Dealer"})
    return df

df = load_data()

# Clean up Location text (strip spaces, normalise case, etc.)
if "Location" in df.columns:
    df["Location_clean"] = (
        df["Location"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)  # collapse multiple spaces
        .str.title()                            # "sydney cbd" -> "Sydney Cbd"
    )
else:
    df["Location_clean"] = ""

# --- Ensure required columns exist ---
required_cols = ["Lead_Date", "Week_Start", "Dealer", "STATE", "Location_clean"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(
        f"The following required columns are missing from the data: {missing}\n\n"
        f"Available columns are: {list(df.columns)}\n\n"
        "Please adjust the CSV headers or this script so they line up."
    )
    st.stop()

# Sanity check – should show expected row count if full dataset
st.caption(f"Total rows in CSV: {len(df)}")

# --------------------------------
# TITLE
# --------------------------------
st.title("📊 Digital Dealer Leads Dashboard")

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

# ----- Date range filter with presets (GLOBAL) -----
min_date = df["Lead_Date"].min().date()
max_date = df["Lead_Date"].max().date()

date_mode = st.sidebar.radio(
    "Date range (applies to all charts)",
    ["Custom range", "Last 7 days", "Last 30 days", "Last 90 days"],
    index=0
)

if date_mode == "Custom range":
    # Show calendar input
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date, max_date)
    )

    # Ensure we always have a start & end date
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range
        end_date = date_range
else:
    # Preset modes use max_date as the "end"
    if date_mode == "Last 7 days":
        days = 7
    elif date_mode == "Last 30 days":
        days = 30
    else:  # "Last 90 days"
        days = 90

    # Calculate start date but don't go earlier than min_date
    start_date = max_date - pd.Timedelta(days=days - 1)
    if start_date < min_date:
        start_date = min_date

    end_date = max_date

    # Show the resolved range for clarity
    st.sidebar.info(f"Showing {date_mode.lower()}:\n{start_date} → {end_date}")

# ----- State filter (ONLY affects State graph) -----
states = sorted(df["STATE"].dropna().unique())
select_all_states = st.sidebar.checkbox("Select All States (State graph only)", value=True)

if select_all_states:
    selected_states = states
else:
    selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)

# ----- Location filter (ONLY affects Location graph) -----
# We'll base location options on the date-filtered data later, but
# we can still build from full df here and then intersect later if needed.
all_locations_full = sorted(df["Location_clean"].dropna().unique())

location_search = st.sidebar.text_input("Search location (Location graph only)")

if location_search:
    location_options = [
        loc for loc in all_locations_full
        if location_search.lower() in loc.lower()
    ]
else:
    location_options = all_locations_full

select_all_locations = st.sidebar.checkbox(
    "Select All Locations (Location graph only)", value=True
)

if select_all_locations:
    selected_locations = location_options
else:
    selected_locations = st.sidebar.multiselect(
        "Select Location(s)",
        location_options,
        default=location_options
    )

# --------------------------------
# APPLY GLOBAL FILTERS (DATE ONLY)
# --------------------------------
date_start_ts = pd.to_datetime(start_date)
date_end_ts = pd.to_datetime(end_date)

date_filtered = df[
    (df["Lead_Date"] >= date_start_ts) &
    (df["Lead_Date"] <= date_end_ts)
].copy()

st.caption(f"Rows after date filter: {len(date_filtered)}")

# --------------------------------
# KPI ROW (based on date filter only)
# --------------------------------
if not date_filtered.empty:
    total_leads = len(date_filtered)
    date_span_days = (
        date_filtered["Lead_Date"].max().date() - date_filtered["Lead_Date"].min().date()
    ).days + 1
    avg_leads_per_day = total_leads / date_span_days if date_span_days > 0 else 0
    num_dealers = date_filtered["Dealer"].nunique()
else:
    total_leads = 0
    avg_leads_per_day = 0
    num_dealers = 0

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

with kpi_col1:
    st.metric("Total Leads", f"{total_leads:,}")

with kpi_col2:
    st.metric("Avg Leads per Day", f"{avg_leads_per_day:.1f}")

with kpi_col3:
    st.metric("Number of Dealers", f"{num_dealers:,}")

st.markdown("---")

# --------------------------------
# MAIN CONTENT
# --------------------------------
if not date_filtered.empty:
    # ---------- 1. Leads Over Time (Weekly) ----------
    weekly_counts = (
        date_filtered
        .groupby("Week_Start")
        .size()
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
    fig_week.update_layout(margin=dict(l=40, r=40, t=60, b=40))

    st.plotly_chart(fig_week, use_container_width=True)

    # ---------- 2. Individual Dealer (top 15, date filter only) ----------
    dealer_counts = (
        date_filtered
        .groupby("Dealer")
        .size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_dealer = px.bar(
        dealer_counts.head(15),  # top 15 dealers
        x="Dealer",
        y="Leads",
        title="Individual Dealer",
        height=CHART_HEIGHT
    )
    # Lighter shade of blue for bars
    fig_dealer.update_traces(marker_color="#8EC6FF")
    fig_dealer.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )

    st.plotly_chart(fig_dealer, use_container_width=True)

    # ---------- 3. Specific Locations (Location graph, location filter only) ----------
    # Base on date-filtered data
    loc_df = date_filtered.copy()

    # Apply location filter ONLY to this graph
    if selected_locations:
        loc_df = loc_df[loc_df["Location_clean"].isin(selected_locations)]
    else:
        loc_df = loc_df.iloc[0:0]

    if not loc_df.empty:
        location_counts = (
            loc_df
            .groupby("Location_clean")
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
        )

        fig_location = px.bar(
            location_counts.head(25),  # top 25 locations for readability
            x="Location_clean",
            y="Leads",
            title="Specific Locations",
            height=CHART_HEIGHT
        )
        # Lighter shade of blue for bars
        fig_location.update_traces(marker_color="#8EC6FF")
        fig_location.update_layout(
            xaxis_tickangle=-45,
            margin=dict(l=40, r=40, t=60, b=80)
        )

        st.plotly_chart(fig_location, use_container_width=True)
    else:
        st.info("No data available for the selected locations and date range.")

    # ---------- 4. Leads by State (State graph, state filter only) ----------
    state_df = date_filtered.copy()

    # Apply state filter ONLY to this graph
    if not select_all_states:
        if selected_states:
            state_df = state_df[state_df["STATE"].isin(selected_states)]
        else:
            state_df = state_df.iloc[0:0]

    if not state_df.empty:
        state_counts = (
            state_df
            .groupby("STATE")
            .size()
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
        fig_state.update_layout(margin=dict(l=40, r=40, t=60, b=40))

        st.plotly_chart(fig_state, use_container_width=True)
    else:
        st.info("No data available for the selected states and date range.")
else:
    st.info("No data available for the selected date range.")
