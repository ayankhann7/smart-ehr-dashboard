"""Page 2 - Patient demographics and population analytics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src import analytics, charts, ui

ctx = ui.bootstrap("Patient Analytics", "Demographics of the (filtered) synthetic patient population. "
                   "No medical risk is inferred from demographic characteristics.")
fd = ctx.fd
patients = fd.patients
a = analytics.age_summary(patients)

ui.metric_cards([
    {"label": "Patients in view", "value": f"{len(patients):,}", "icon": "users"},
    {"label": "Median age", "value": f"{a['median']:.0f} yrs" if a["median"] is not None else "n/a", "icon": "clock"},
    {"label": "Age range", "value": f"{a['min']:.0f}–{a['max']:.0f}" if a["median"] is not None else "n/a", "sub": "Youngest to oldest, years", "icon": "clock"},
    {"label": "Excluded from age analysis", "value": f"{a['excluded']:,}", "sub": "Missing/invalid birth date", "icon": "clipboard"},
])
if "death_date" in patients:
    deceased = int(patients["death_date"].notna().sum())
    st.caption(f"Records with a death date: {deceased:,}; living / no death date: {len(patients) - deceased:,}.")

st.subheader("Age groups")
groups = analytics.age_group_counts(patients)
left, right = st.columns(2)
with left:
    ui.show_chart(charts.age_group_bar(groups), key="pa_groups")
with right:
    ui.show_table(groups.rename(columns={"age_group": "Age group", "patients": "Patients", "percent": "% of patients with valid age"}))
    ui.download_csv("Download age-group counts (CSV)", groups, "age_group_counts.csv", "dl_age")
st.caption("Age groups: 0–17, 18–34, 35–49, 50–64, 65–79, 80+ (same definition on every page).")

st.subheader("Patient counts by category")
cats = [c for c in ("gender", "race", "ethnicity", "age_group") if c in patients.columns]
if cats:
    cat = st.selectbox("Group patients by", cats, format_func=lambda c: c.replace("_", " ").title(), key="pa_cat")
    counts = analytics.age_group_counts(patients) if cat == "age_group" else analytics.category_counts(patients, cat)
    left, right = st.columns(2)
    with left:
        ui.show_chart(charts.category_bar(counts, cat, f"Patients by {cat.replace('_', ' ')}"), key="pa_cat_chart")
    with right:
        ui.show_table(counts)
        ui.download_csv("Download this table (CSV)", counts, f"patients_by_{cat}.csv", "dl_cat")
else:
    st.info("No demographic columns are available.")

st.subheader("Synthetic patient ID list")
query = st.text_input("Search patient ID", key="pa_search", placeholder="Type part of an ID")
listing = patients[["patient_id"] + [c for c in ("age", "age_group", "gender") if c in patients]].copy()
listing["encounters"] = listing["patient_id"].map(fd.encounters["patient_id"].value_counts()).fillna(0).astype(int)
if query.strip():
    listing = listing[listing["patient_id"].astype(str).str.contains(query.strip(), case=False, regex=False)]
listing["age"] = listing["age"].round(0)
listing["age_group"] = listing["age_group"].astype(str).replace("nan", "n/a")
st.caption(f"{len(listing):,} patient(s) match. Open the Patient Explorer page to see one patient's records.")
if listing.empty:
    st.info("No patient IDs match your search.")
else:
    ui.show_table(listing.head(1000), height=320)
    if len(listing) > 1000:
        st.caption("Showing the first 1,000 matches.")

if fd.observations is not None:
    options = analytics.observation_options(fd.observations)
    if options:
        st.subheader("Clinical measurements by age group (optional)")
        choice = st.selectbox("Measurement", options, key="pa_obs")
        obs = analytics.observation_by_age_group(fd.observations, patients, choice)
        ui.show_chart(charts.observation_bar(obs, choice), key="pa_obs_chart")
        ui.show_table(obs)
        st.caption("Values are simulated. Age group is the patient's age at the dataset reference date, "
                   "not at the time of measurement. Not a clinical reference.")
ui.footer()
