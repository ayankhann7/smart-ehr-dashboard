"""Page 1 - Executive healthcare dashboard (landing page)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import analytics, charts, ui
from src.utils import CONDITION_PRESETS, get_conditions_for_preset

ctx = ui.bootstrap("Executive Healthcare Dashboard",
                   "Headline numbers and distributions for the loaded Synthea synthetic records. "
                   "All figures are computed from the CSV files and respond to the sidebar filters.")
fd = ctx.fd
m = analytics.summary_metrics(fd)

ref = ctx.cleaned.reference_date.date()
ui.metric_cards([
    {"label": "Unique patients", "value": f"{m['patients']:,}", "sub": "Distinct synthetic patient IDs", "icon": "users"},
    {"label": "Encounters", "value": f"{m['encounters']:,}",
     "sub": f"{m['encounters_per_patient']:.1f} per patient on average" if m["encounters_per_patient"] is not None else None,
     "icon": "activity"},
    {"label": "Condition records", "value": f"{m['conditions']:,}", "sub": f"{m['distinct_conditions']:,} distinct conditions", "icon": "clipboard"},
    {"label": "Average age", "value": f"{m['avg_age']:.1f} yrs" if m["avg_age"] is not None else "n/a",
     "sub": f"As of {ref}; {m['age_excluded']:,} patient(s) without a valid age excluded", "icon": "clock"},
])
with st.expander("Patients vs. encounters vs. condition records"):
    st.markdown("- **Patients** are unique synthetic people.\n"
                "- **Encounters** are healthcare visits; one patient can have many.\n"
                "- **Condition records** are diagnoses recorded during visits; a patient can have the same "
                "condition recorded more than once.\n\nCounts are records in the supplied dataset, not real hospital activity.")

st.subheader("Who is in the data?")
left, right = st.columns(2)
with left:
    ui.show_chart(charts.age_histogram(fd.patients["age"]), key="exec_age")
    st.caption("Distribution of patient ages (completed years). Patients without a valid birth date are excluded.")
with right:
    if "gender" in fd.patients:
        ui.show_chart(charts.donut(analytics.category_counts(fd.patients, "gender"), "gender", "patients",
                                   "Patient gender distribution"), key="exec_gender")
    else:
        st.info("The dataset has no gender column.")
    st.caption("Share of patients per gender category present in the dataset.")

st.subheader("What is recorded?")
left, right = st.columns(2)
with left:
    cat_sel = st.selectbox("Spotlight condition group", list(CONDITION_PRESETS.keys()), index=0, key="exec_cat_sel",
                           help="Filter the top conditions bar chart to specific disease groups like Diabetes, Asthma, etc.")
    if cat_sel != "All Conditions":
        all_c_names = list(fd.conditions["description"].dropna().unique())
        c_matches = get_conditions_for_preset(cat_sel, all_c_names)
        disp_conds = fd.conditions[fd.conditions["description"].isin(c_matches)]
    else:
        disp_conds = fd.conditions
    top = analytics.top_conditions(disp_conds, 10)
    chart_title = f"Top {cat_sel}" if cat_sel != "All Conditions" else "Top 10 recorded conditions"
    ui.show_chart(charts.horizontal_bar(top, "description", "records", chart_title, "Condition records"), key="exec_top")
    st.caption("Number of condition records per diagnosis (not disease prevalence).")
with right:
    if "encounter_class" in fd.encounters:
        ui.show_chart(charts.donut(analytics.encounter_class_distribution(fd.encounters), "encounter_class",
                                   "encounters", "Encounter class distribution", unit="encounters"), key="exec_class")
    else:
        st.info("The encounters file has no encounter-class column.")
    st.caption("Share of encounters by class (e.g. ambulatory, emergency, inpatient).")

st.subheader("Encounters over time")
options, default = analytics.allowed_granularities(fd.encounters["start"] if "start" in fd.encounters else None)
grain = st.radio("Group by", options, index=options.index(default), horizontal=True, key="exec_grain")
ui.show_chart(charts.time_series(analytics.encounters_over_time(fd.encounters, grain), "encounters",
                                 f"{grain} encounters", "Encounters"), key="exec_time")
undated = int(fd.encounters["start"].isna().sum()) if "start" in fd.encounters else 0
if undated:
    st.caption(f"{undated:,} encounter(s) with a missing/invalid date are not shown on this chart.")

findings = analytics.key_findings(fd)
if findings:
    st.subheader("Key findings")
    st.markdown("\n".join(f"- {f}" for f in findings))
ui.footer()
