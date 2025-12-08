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
        "/Users/randuan/Downloads/cleaned_digital_dealer_prepped.csv",
        parse_dates=["Lead_Date", "Week_Start"]
    )
    return df

df = load_data()

st.title("📊 Digital Dealer Leads Dashboard")

# --------------------------------
# SIDEBAR FILTERS (with Select All + auto-hide)
# --------------------------------
st.sidebar.header("Filters")

# ----- Week filter -----
weeks = sorted(
    df["Week_Label"].dropna().unique(),
    key=lambda w: pd.to_datetime(w.replace("Week of ", ""), dayfirst=True)
)

select_all_weeks = st.sidebar.checkbox("Select All Weeks", value=True)
if select_all_weeks:
    selected_weeks = weeks
else:
    selected_weeks = st.sidebar.multiselect("Select Week(s)", weeks, default=weeks)

# ----- State filter -----
states = sorted(df["State"].dropna().unique())
select_all_states = st.sidebar.checkbox("Select All States", value=True)
if select_all_states:
    selected_states = states
else:
    selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)

# ----- Dealer filter -----
dealers = sorted(df["Dealer"].dropna().unique())
select_all_dealers = st.sidebar.checkbox("Select All Dealers", value=True)
if select_all_dealers:
    selected_dealers = dealers
else:
    selected_dealers = st.sidebar.multiselect("Select Dealer(s)", dealers, default=dealers)

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered = df.copy()

if selected_weeks:
    filtered = filtered[filtered["Week_Label"].isin(selected_weeks)]

if selected_states:
    filtered = filtered[filtered["State"].isin(selected_states)]

if selected_dealers:
    filtered = filtered[filtered["Dealer"].isin(selected_dealers)]

# --------------------------------
# KPIs
# --------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Leads", len(filtered))
col2.metric("Active Dealers", filtered["Dealer"].nunique())
col3.metric("States", filtered["State"].nunique())

st.markdown("---")

# --------------------------------
# CHARTS
# --------------------------------
if not filtered.empty:
    # Leads by Week
    weekly = (
        filtered.groupby("Week_Start").size().reset_index(name="Leads")
        .sort_values("Week_Start")
    )
    fig_week = px.line(
        weekly,
        x="Week_Start",
        y="Leads",
        markers=True,
        title="Leads Over Time (Weekly)"
    )
    st.plotly_chart(fig_week, use_container_width=True)

    # Leads by Dealer
    dealer_counts = (
        filtered.groupby("Dealer").size().reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )
    fig_dealer = px.bar(
        dealer_counts,
        x="Dealer",
        y="Leads",
        title="Leads by Dealer"
    )
    st.plotly_chart(fig_dealer, use_container_width=True)

    # Leads by State
    state_counts = (
        filtered.groupby("State").size().reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )
    fig_state = px.bar(
        state_counts,
        x="State",
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
    st.dataframe(
        filtered.sort_values("Lead_Date", ascending=False),
        use_container_width=True
    )
else:
    st.write("No rows match the current filters.")