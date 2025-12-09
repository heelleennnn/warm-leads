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

# ----- Date range filter with presets -----
min_date = df["Lead_Date"].min().date()
max_date = df["Lead_Date"].max().date()

date_mode = st.sidebar.radio(
    "Date range",
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

# ----- State filter (using STATE) -----
states = sorted(df["STATE"].dropna().unique())
select_all_states = st.sidebar.checkbox("Select All States", value=True)

if select_all_states:
    selected_states = states        # we will NOT filter by state later
else:
    selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)

# This temp df is only to generate the list of locations based on selected states
if select_all_states:
    df_for_locations = df
else:
    df_for_locations = df[df["STATE"].isin(selected_states)]

# ----- Location filter (using Location_clean) -----
# NOTE: multiselect has built-in search, so we don't need a separate text_input.
all_locations = sorted(df_for_locations["Location_clean"].dropna().unique())

select_all_locations = st.sidebar.checkbox(
    "Select All Locations (after state filter)", value=True
)

if select_all_locations:
    selected_locations = all_locations  # we will NOT filter by location later
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

# Filter by Lead_Date using selected/preset range
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date)

filtered = filtered[
    (filtered["Lead_Date"] >= start_ts) &
    (filtered["Lead_Date"] <= end_ts)
]

# Only filter by STATE if user actually narrowed states
if not select_all_states:
    if selected_states:
        filtered = filtered[filtered["STATE"].isin(selected_states)]
    else:
        filtered = filtered.iloc[0:0]

# Only filter by Location_clean if user actually narrowed locations
if not select_all_locations:
    if selected_locations:
        filtered = filtered[filtered["Location_clean"].isin(selected_locations)]
    else:
        filtered = filtered.iloc[0:0]

st.caption(f"Rows after filters: {len(filtered)}")

# --------------------------------
# KPI ROW
# --------------------------------
if not filtered.empty:
    total_leads = len(filtered)
    # number of days in selected range that actually exist in filtered data
    date_span_days = (
        filtered["Lead_Date"].max().date() - filtered["Lead_Date"].min().date()
    ).days + 1
    avg_leads_per_day = total_leads / date_span_days if date_span_days > 0 else 0
    num_dealers = filtered["Dealer"].nunique()
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
if not filtered.empty:
    # ---------- 1. Leads Over Time (Weekly) ----------
    weekly_counts = (
        filtered
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
    # Navy blue
    fig_week.update_traces(line_color="#003f5c", marker_color="#003f5c")
    fig_week.update_layout(margin=dict(l=40, r=40, t=60, b=40))

    st.plotly_chart(fig_week, use_container_width=True)

    # ---------- 2. Individual Dealer (top 15 dealers) ----------
    dealer_counts = (
        filtered
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
    # Light blue
    fig_dealer.update_traces(marker_color="#7ab8ff")
    fig_dealer.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )

    st.plotly_chart(fig_dealer, use_container_width=True)

    # ---------- 3. Specific Locations (by Location_clean) ----------
    location_counts = (
        filtered
        .groupby("Location_clean")
        .size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_location = px.bar(
        location_counts.head(25),  # show top 25 locations for readability
        x="Location_clean",
        y="Leads",
        title="Specific Locations",
        height=CHART_HEIGHT
    )
    # Medium blue
    fig_location.update_traces(marker_color="#2f76c6")
    fig_location.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )

    st.plotly_chart(fig_location, use_container_width=True)

    # ---------- 4. Leads by State (STATE) ----------
    state_counts = (
        filtered
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
    # Sky blue
    fig_state.update_traces(marker_color="#76c7ff")
    fig_state.update_layout(margin=dict(l=40, r=40, t=60, b=40))

    st.plotly_chart(fig_state, use_container_width=True)
else:
    st.info("No data available for the selected filters.")
