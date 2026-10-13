"""Page 4 - Healthcare visit (encounter) trends."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import analytics, charts, ui

ctx = ui.bootstrap("Healthcare Visit Trends", "Encounters over time. Counts are records in the supplied dataset, "
                   "not real-time hospital activity.")
fd = ctx.fd
enc = fd.encounters
if enc.empty or "start" not in enc or enc["start"].notna().sum() == 0:
    ui.empty_state("There are no dated encounters in the current view.")
    ui.footer()
    st.stop()

missing = int(enc["start"].isna().sum())
if missing:
    st.caption(f"{missing:,} encounter(s) with a missing or invalid date are excluded from these time-based views.")

options, default = analytics.allowed_granularities(enc["start"])
c1, c2 = st.columns(2)
with c1:
    grain = st.radio("Group by", options, index=options.index(default), horizontal=True, key="vt_grain",
                     help="Daily is only offered for date ranges of about three years or less.")
with c2:
    kind = st.radio("Chart type", ["Line", "Bar"], horizontal=True, key="vt_kind")

series = analytics.encounters_over_time(enc, grain)
ui.show_chart(charts.time_series(series, "encounters", f"{grain} encounters", "Encounters", "bar" if kind == "Bar" else "line"), key="vt_main")
if grain == "Yearly":
    st.caption("The first and last years may be partial, so they can look smaller than complete years.")

if "encounter_class" in enc:
    st.subheader("Encounter classes")
    left, right = st.columns(2)
    dist = analytics.encounter_class_distribution(enc)
    with left:
        ui.show_chart(charts.category_bar(dist, "encounter_class", "Encounters by class", "encounters", "Encounters"), key="vt_class")
    with right:
        ui.show_table(dist)
    classes = list(dist["encounter_class"])
    chosen = st.multiselect("Compare classes over time", classes, default=classes[:4], key="vt_cmp")
    by_class = analytics.encounters_by_class_over_time(enc[enc["encounter_class"].astype(str).isin(chosen)], grain)
    ui.show_chart(charts.multi_line(by_class, "encounter_class", "encounters", f"{grain} encounters by class", "Encounters"), key="vt_cls_time")
    table = by_class.pivot(index="period_label", columns="encounter_class", values="encounters").reset_index() if not by_class.empty else by_class
else:
    st.info("The encounters file has no encounter-class column, so class comparisons are unavailable.")
    table = series

st.subheader("Aggregated results")
ui.show_table(table.rename(columns={"period_label": "Period"}) if "period_label" in table else table, height=320)
ui.download_csv("Download aggregated encounters (CSV)", table, f"encounters_{grain.lower()}.csv", "dl_vt")
ui.footer()
