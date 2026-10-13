"""Entry point:  streamlit run app.py

Sets up the page shell once and routes between the six pages with st.navigation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from src import ui

ui.configure_page()

pages = [
    st.Page("pages/0_Executive_Dashboard.py", title="Executive Dashboard", icon=":material/dashboard:", default=True),
    st.Page("pages/1_Patient_Analytics.py", title="Patient Analytics", icon=":material/groups:"),
    st.Page("pages/2_Diagnosis_Analysis.py", title="Diagnosis Analysis", icon=":material/stethoscope:"),
    st.Page("pages/3_Visit_Trends.py", title="Visit Trends", icon=":material/trending_up:"),
    st.Page("pages/4_Patient_Explorer.py", title="Patient Explorer", icon=":material/person_search:"),
    st.Page("pages/5_Data_Quality.py", title="Data Quality", icon=":material/fact_check:"),
]
st.navigation(pages).run()
