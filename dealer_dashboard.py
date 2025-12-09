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
# LOAD DATA
# --------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(
        "cleaned_digital_dealer_full.csv",
        parse_dates=["ParsedDate", "Week_Start"]  # ParsedDate is the real date column
    )

    # Use ParsedDate as the main Lead_Date field for consistency
    df["Lead_Date"] = df["ParsedDate"]

    # Clean up junk / legacy columns if present
    df = df.drop(columns=["Unnamed: 29", "State"], errors="ignore")

    return df


df = load_data()

st.title("📊 Digital Dealer Leads Dashboard")

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

# ----- Week filter -----
if "Week_Label" in df.columns:
    weeks = df["Week_Label"].dropna().unique().tolist()

    # Sort by the actual date embedded in the label, e.g. "Week of 01/12/2024"
    try:
        weeks = sorted(
            weeks,
            key=lambda w: pd.to_datetime(
                str(w).replace("Week of ", ""),
                dayfirst=True,
                errors="coerce"
            )
        )
    except Exception:
        weeks = sorted(weeks)

    select_all_weeks = st.sidebar.checkbox("Select All Weeks", value=True)
    if select_all_weeks:
        selected_weeks = weeks
    else:
        selected_weeks = st.sidebar.multiselect("Select Week(s)", weeks, default=weeks)
else:
    selected_weeks = None

# ----- State filter (STATE column) -----
if "STATE" in df.columns:
    states = sorted(df["STATE"].dropna().unique())
    select_all_states = st.sidebar.checkbox("Select All States", value=True)
    if select_all_states:
        selected_states = states
    else:
        selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)
else:
    selected_states = None

# ----- Dealer filter -----
if "Dealer" in df.columns:
    dealers = sorted(df["Dealer"].dropna().unique())
    select_all_dealers = st.sidebar.checkbox("Select All Dealers", value=True)
    if select_all_dealers:
        selected_dealers = dealers
    else:
        selected_dealers = st.sidebar.multiselect("Select Dealer(s)", dealers, default=dealers)
else:
    selected_dealers = None

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered = df.copy()

if selected_weeks is not None and len(selected_weeks) > 0:
    filtered = filtered[filtered["Week_Label"].isin(selected_weeks)]

if selected_states is not None and len(selected_states) > 0:
    filtered = filtered[filtered["STATE"].isin(selected_states)]

if selected_dealers is not None and len(selected_dealers) > 0:
    filtered = filtered[filtered["Dealer"].isin(selected_dealers)]

# --------------------------------
# KPIs
# --------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Leads", len(filtered))
col2.metric("Active Dealers", filtered["Dealer"].nunique() if "Dealer" in filtered.columns else 0)
col3.metric("States", filtered["STATE"].nunique() if "STATE" in filtered.columns else 0)

st.markdown("---")

# --------------------------------
# CHARTS
# --------------------------------
if not filtered.empty:
    # Leads over time (weekly)
    if "Week_Start" in filtered.columns:
        weekly = (
            filtered.groupby("Week_Start")
            .size()
            .reset_index(name="Leads")
            .sort_values("Week_Start")
        )

        if not weekly.empty:
            fig_week = px.line(
                weekly,
                x="Week_Start",
                y="Leads",
                markers=True,
                title="Leads Over Time (Weekly)"
            )
            st.plotly_chart(fig_week, use_container_width=True)

    # Leads by Dealer
    if "Dealer" in filtered.columns:
        dealer_counts = (
            filtered.groupby("Dealer")
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
        )

        if not dealer_counts.empty:
            fig_dealer = px.bar(
                dealer_counts,
                x="Dealer",
                y="Leads",
                title="Leads by Dealer"
            )
            st.plotly_chart(fig_dealer, use_container_width=True)

    # Leads by State
    if "STATE" in filtered.columns:
        state_counts = (
            filtered.groupby("STATE")
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
        )

        if not state_counts.empty:
            fig_state = px.bar(
                state_counts,
                x="STATE",
                y="Leads",
                title="Leads by State"
            )
            st.plotly_chart(fig_state, use_container_width=True)
else:
    st.warning("No data for the selected filters.")

# --------------------------------
# DETAIL TABLE
# --------------------------------
st.subheader("Filtered Lead Records")
if not filtered.empty:
    # Sort most recent first using Lead_Date (which is ParsedDate)
    if "Lead_Date" in filtered.columns:
        filtered_display = filtered.sort_values("Lead_Date", ascending=False)
    else:
        filtered_display = filtered

    st.dataframe(
        filtered_display,
        use_container_width=True
    )
else:
    st.write("No rows match the current filters.")
