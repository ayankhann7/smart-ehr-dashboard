"""Page 5 - Synthetic patient explorer (educational record viewer, read-only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import analytics, charts, ui

ctx = ui.bootstrap("Synthetic Patient Explorer", "Browse the records of one synthetic patient. Read-only educational "
                   "viewer, not a clinical EHR. Sidebar filters do not apply here; the patient ID is the only filter.",
                   use_filters=False)
tables = ctx.tables
ids, total = analytics.search_patient_ids(tables["patients"], st.text_input("Search synthetic patient ID", key="pe_q", placeholder="Type part of an ID"))
if not ids:
    st.info("No patient IDs match your search.")
    ui.footer()
    st.stop()
if total > len(ids):
    st.caption(f"{total:,} IDs match; showing the first {len(ids):,}. Type more characters to narrow the list.")
pid = st.selectbox("Select synthetic patient ID", ids, key="pe_pid")
rec = analytics.patient_record(tables, pid)
prof = rec["profile"]

ui.metric_cards([
    {"label": "Age", "value": f"{prof['age']:.0f} yrs" if prof.get("age") is not None else "n/a", "sub": prof.get("age_group") and f"Age group {prof['age_group']}", "icon": "clock"},
    {"label": "Gender", "value": str(prof.get("gender") or "n/a"), "sub": prof.get("status"), "icon": "users"},
    {"label": "Encounters", "value": f"{len(rec['encounters']):,}", "icon": "activity"},
    {"label": "Conditions", "value": f"{len(rec['conditions']):,}", "icon": "clipboard"},
])
demo = [f"{k.title()}: {prof[k]}" for k in ("race", "ethnicity") if prof.get(k) not in (None, "Unknown")]
if demo:
    st.caption(" · ".join(demo))

tab_e, tab_c, tab_o, tab_m = st.tabs(["Encounters", "Conditions", "Observations", "Medications"])
with tab_e:
    e = rec["encounters"]
    if e.empty:
        st.info("No encounters recorded for this patient.")
    else:
        ui.show_table(e.drop(columns=["patient_id"], errors="ignore"), height=320)
with tab_c:
    c = rec["conditions"]
    if c.empty:
        st.info("No conditions recorded for this patient.")
    else:
        ui.show_table(c.drop(columns=["patient_id"], errors="ignore"), height=320)
with tab_o:
    o = rec["observations"]
    if o is None:
        st.info("observations.csv was not provided, so measurements are unavailable.")
    elif o.empty:
        st.info("No observations recorded for this patient.")
    else:
        ui.show_table(o.drop(columns=["patient_id", "value_numeric"], errors="ignore"), height=320)
        numeric = sorted(o.dropna(subset=["value_numeric"])["description"].astype(str).unique()) if "value_numeric" in o else []
        if numeric:
            pick = st.selectbox("Plot a measurement", numeric, key="pe_obs")
            ui.show_chart(charts.patient_measurement_line(o[o["description"] == pick], pick), key="pe_obs_chart")
with tab_m:
    m = rec["medications"]
    if m is None:
        st.info("medications.csv was not provided, so medication records are unavailable.")
    elif m.empty:
        st.info("No medication records for this patient.")
    else:
        ui.show_table(m.drop(columns=["patient_id"], errors="ignore"), height=320)
ui.footer()
