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
@st.cache_data
def load_data():
    df = pd.read_csv(
        "cleaned_digital_dealer_full.csv",
        parse_dates=["Lead_Date", "Week_Start"]
    )

    # Rename columns so code is consistent
    df = df.rename(
        columns={
            "Dealer/Website": "Dealer",
            "STATE": "State"
        }
    )

    return df

df = load_data()

# Sanity check – should show 2491
st.caption(f"Total rows in CSV: {len(df)}")

# --------------------------------
# TITLE
# --------------------------------
st.title("📊 Digital Dealer Leads Dashboard")

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

# ----- Week filter -----
# dropna() avoids float/string mix when sorting
weeks = sorted(df["Week_Label"].dropna().unique())
select_all_weeks = st.sidebar.checkbox("Select All Weeks", value=True)

if select_all_weeks:
    selected_weeks = weeks          # we will NOT filter by week later
else:
    selected_weeks = st.sidebar.multiselect("Select Week(s)", weeks, default=weeks)

# ----- State filter -----
states = sorted(df["State"].dropna().unique())
select_all_states = st.sidebar.checkbox("Select All States", value=True)

if select_all_states:
    selected_states = states        # we will NOT filter by state later
else:
    selected_states = st.sidebar.multiselect("Select State(s)", states, default=states)

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered = df.copy()

# Only filter by Week_Label if user actually narrowed weeks
if not select_all_weeks:
    if selected_weeks:
        filtered = filtered[filtered["Week_Label"].isin(selected_weeks)]
    else:
        # user deselected all weeks → empty
        filtered = filtered.iloc[0:0]

# Only filter by State if user actually narrowed states
if not select_all_states:
    if selected_states:
        filtered = filtered[filtered["State"].isin(selected_states)]
    else:
        filtered = filtered.iloc[0:0]

# Should be 2491 when both "Select All" are checked
st.caption(f"Rows after filters: {len(filtered)}")

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
    fig_week.update_layout(margin=dict(l=40, r=40, t=60, b=40))

    # Full-width, first row
    st.plotly_chart(fig_week, use_container_width=True)

    # ---------- 2. Leads by Dealer ----------
    dealer_counts = (
        filtered
        .groupby("Dealer")
        .size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_dealer = px.bar(
        dealer_counts.head(25),  # top 25 dealers for readability
        x="Dealer",
        y="Leads",
        title="Leads by Dealer",
        height=CHART_HEIGHT
    )
    fig_dealer.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=80)
    )

    # Full-width, second row
    st.plotly_chart(fig_dealer, use_container_width=True)

    # ---------- 3. Leads by State ----------
    state_counts = (
        filtered
        .groupby("State")
        .size()
        .reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )

    fig_state = px.bar(
        state_counts,
        x="State",
        y="Leads",
        title="Leads by State",
        height=CHART_HEIGHT
    )
    fig_state.update_layout(margin=dict(l=40, r=40, t=60, b=40))

    # Full-width, third row
    st.plotly_chart(fig_state, use_container_width=True)

    # ---------- Raw Data Table ----------
    st.subheader("Filtered Leads")
    st.dataframe(
        filtered.sort_values("Lead_Date", ascending=False),
        use_container_width=True
    )
else:
    st.warning("No data for the selected filters.")
