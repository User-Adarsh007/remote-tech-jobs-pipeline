import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Remote Tech Job Tracker", layout="wide")
st.title("🌐 Remote Tech Jobs Intelligence Dashboard")

engine = create_engine('sqlite:///remote_tech_jobs.db')

@st.cache_data(ttl=600)
def load_data():
    return pd.read_sql("SELECT * FROM jobs", con=engine)

df = load_data()

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Jobs", len(df))
c2.metric("Hiring Companies", df['company'].nunique())
sal_jobs = df[df['salary_min'].notna()]
c3.metric("Jobs with Salary", len(sal_jobs))
avg_sal = sal_jobs['salary_max'].mean()
c4.metric("Avg Max Salary", f"${avg_sal:,.0f}" if pd.notna(avg_sal) else "N/A")

st.divider()

# Charts
l_col, r_col = st.columns(2)
with l_col:
    st.subheader("Top Locations")
    loc_counts = df['location'].value_counts().head(8).reset_index()
    loc_counts.columns = ['Location', 'Job Count']
    fig_loc = px.bar(loc_counts, x='Job Count', y='Location', orientation='h', color='Job Count', color_continuous_scale='Blues')
    fig_loc.update_layout(yaxis={'autorange': 'reversed'}, showlegend=False)
    st.plotly_chart(fig_loc, use_container_width=True)

with r_col:
    st.subheader("Top Skills / Tags")
    tags_s = df['tags'].dropna().apply(lambda x: [t.strip() for t in str(x).split(',')])
    top_tags = tags_s.explode().value_counts().head(10).reset_index()
    top_tags.columns = ['Skill / Tag', 'Count']
    fig_tags = px.bar(top_tags, x='Skill / Tag', y='Count', color='Count', color_continuous_scale='Viridis')
    st.plotly_chart(fig_tags, use_container_width=True)

st.divider()
st.subheader("Explore Open Roles")
search = st.text_input("Filter by Position or Company")
filtered = df.copy()
if search:
    filtered = filtered[filtered['position'].str.contains(search, case=False, na=False) | filtered['company'].str.contains(search, case=False, na=False)]

# Include 'date' and configure headers
cols_to_show = ['date', 'company', 'position', 'location', 'salary_min', 'salary_max', 'apply_url']

st.dataframe(
    filtered[cols_to_show],
    column_config={
        "date": st.column_config.DateColumn("Date Posted", format="YYYY-MM-DD"),
        "company": st.column_config.TextColumn("Company"),
        "position": st.column_config.TextColumn("Position"),
        "location": st.column_config.TextColumn("Location"),
        "salary_min": st.column_config.NumberColumn("Min Salary", format="$%d"),
        "salary_max": st.column_config.NumberColumn("Max Salary", format="$%d"),
        "apply_url": st.column_config.LinkColumn("Apply Link")
    },
    hide_index=True,
    use_container_width=True
)
