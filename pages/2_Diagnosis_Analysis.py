"""Page 3 - Condition / diagnosis analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import analytics, charts, ui
from src.utils import CONDITION_PRESETS, get_conditions_for_preset

ctx = ui.bootstrap("Diagnosis Analysis", "Frequency of recorded conditions. Frequency is not disease prevalence, "
                   "and nothing here is clinical advice.")
fd = ctx.fd
if fd.conditions.empty:
    ui.empty_state("There are no condition records in the current view.")
    ui.footer()
    st.stop()

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    cat_focus = st.selectbox(
        "Disease Category Focus",
        list(CONDITION_PRESETS.keys()),
        index=0,
        key="dx_page_cat",
        help="Quickly zoom into Diabetes, Cardiovascular, Asthma, or other condition groups."
    )
with c2:
    n = st.slider("Number of conditions to show", 5, 30, 10, key="dx_n")
with c3:
    by_label = st.radio("Rank by", ["Condition records", "Unique patients"], horizontal=True, key="dx_by")

by = "records" if by_label == "Condition records" else "patients"

# Filter conditions by selected category if not 'All Conditions'
if cat_focus != "All Conditions":
    all_cond_names = list(fd.conditions["description"].dropna().unique())
    matches = get_conditions_for_preset(cat_focus, all_cond_names)
    display_conditions = fd.conditions[fd.conditions["description"].isin(matches)]
    st.info(f"Showing **{cat_focus}** ({len(matches)} matching conditions in view).")
else:
    display_conditions = fd.conditions

top = analytics.top_conditions(display_conditions, n, by)
ui.show_chart(charts.horizontal_bar(top, "description", by, f"Top {len(top)} conditions by {by_label.lower()}", by_label), key="dx_bar")
st.caption("**Condition records** count every recorded diagnosis (a patient can appear several times). "
           "**Unique patients** counts each patient once per condition.")

st.subheader("Searchable condition table")
q = st.text_input("Search conditions", key="dx_search", placeholder="e.g. diabetes")
full = analytics.top_conditions(display_conditions, None, by)
if q.strip():
    full = full[full["description"].str.contains(q.strip(), case=False, regex=False)]
table = full.rename(columns={"description": "Condition", "records": "Condition records", "patients": "Unique patients",
                             "percent_of_records": "% of condition records"})
st.caption(f"{len(table):,} condition(s) shown.")
ui.show_table(table, height=320)
ui.download_csv("Download condition counts (CSV)", full, "condition_counts.csv", "dl_dx")

st.subheader("Conditions over time")
options, default = analytics.allowed_granularities(display_conditions["start"] if "start" in display_conditions else None)
c1, c2 = st.columns(2)
with c1:
    cond_options = list(analytics.top_conditions(display_conditions, None)["description"])
    chosen = st.multiselect("Conditions", cond_options,
                            default=list(top["description"].head(3)) if not top.empty else [], key="dx_time_sel")
with c2:
    grain = st.radio("Group by", options, index=options.index(default), horizontal=True, key="dx_grain")
series = analytics.conditions_over_time(display_conditions, chosen, grain)
ui.show_chart(charts.multi_line(series, "description", "records", f"Condition records per {grain.lower()[:-2] if grain != 'Daily' else 'day'}", "Condition records"), key="dx_time")

st.subheader("Demographic comparison")
group_opts = [c for c in ("gender", "age_group", "race") if c in fd.patients.columns]
if group_opts:
    c1, c2 = st.columns(2)
    with c1:
        group = st.selectbox("Compare by", group_opts, format_func=lambda c: c.replace("_", " ").title(), key="dx_group")
    with c2:
        picks = st.multiselect("Conditions to compare", list(top["description"]), default=list(top["description"].head(5)), key="dx_cmp")
    cmp = analytics.condition_by_group(fd.conditions, fd.patients, group, picks)
    ui.show_chart(charts.grouped_bar(cmp, "description", group, "records_per_100_patients", "Condition records per 100 patients in each group", "Records per 100 patients"), key="dx_cmp_chart")
    st.caption("Records per 100 patients divides by the number of patients in each group so groups of different size "
               "can be compared. This is a record frequency in synthetic data, not prevalence or risk.")
    with st.expander("Comparison table"):
        ui.show_table(cmp)
        ui.download_csv("Download comparison (CSV)", cmp, "condition_comparison.csv", "dl_cmp")
ui.footer()
