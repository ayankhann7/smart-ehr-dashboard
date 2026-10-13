"""Page 6 - Data quality and dataset information."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src import analytics, data_cleaning, file_manager, ui

ctx = ui.bootstrap("Data Quality & Dataset Information", "What was loaded, what was wrong with it, and what the "
                   "cleaning step did. Only aggregate counts are shown.", use_filters=False)
cd = ctx.cleaned
lo, hi = cd.date_range
q = cd.quality

ui.metric_cards([
    {"label": "Files loaded", "value": f"{int((q['status'] == 'loaded').sum())}", "sub": f"of {len(q)} expected", "icon": "clipboard"},
    {"label": "Encounter dates", "value": f"{lo.year}–{hi.year}" if lo is not None and pd.notna(lo) else "n/a",
     "sub": f"{lo.date()} to {hi.date()}" if lo is not None and pd.notna(lo) else None, "icon": "clock"},
    {"label": "Duplicates removed", "value": f"{int(q['duplicates_removed'].sum()):,}", "icon": "activity"},
    {"label": "Invalid dates", "value": f"{int(q['invalid_dates'].sum()):,}", "icon": "clock"},
])
st.caption(f"Last successful load: {cd.loaded_at} · Source: `{cd.source_dir}` · Ages computed as of {cd.reference_date.date()}.")

st.subheader("📁 Dataset File Management")
with st.expander("Upload, Add, or Delete Dataset CSV Files", expanded=True):
    file_manager.render_file_manager(cd.source_dir, is_sidebar=False, key_prefix="dq_fm")

st.subheader("Original vs. cleaned counts")
view = q.rename(columns={
    "table": "Table", "file": "File", "status": "Status", "rows_original": "Rows (original)",
    "rows_after_cleaning": "Rows (cleaned)", "rows_removed": "Rows removed", "columns_in_file": "Columns in file",
    "columns_used": "Columns used", "duplicates_removed": "Duplicates removed",
    "missing_patient_id_removed": "Missing patient ID removed", "unmatched_patient_refs_removed": "Unmatched patient IDs removed",
    "unmatched_encounter_refs": "Unmatched encounter refs (kept)", "invalid_dates": "Invalid dates", "invalid_date_detail": "Invalid dates by column"})
ui.show_table(view)
st.caption("Only the columns the dashboard needs are read; names, addresses and other direct identifiers in the source files are never loaded.")

st.subheader("Missing values")
mv = cd.missing_values.rename(columns={"table": "Table", "column": "Column", "missing_original": "Missing (original)",
                                       "pct_missing_original": "% missing (original)",
                                       "missing_or_unknown_after_cleaning": "Missing or 'Unknown' (cleaned)"})
ui.show_table(mv, height=300)

st.subheader("Cleaning operations performed")
if cd.cleaning_log:
    st.markdown("\n".join(f"- {line}" for line in cd.cleaning_log))
for w in cd.warnings:
    st.warning(w)
with st.expander("Column mapping (source header → canonical name)"):
    ui.show_table(cd.file_info[["table", "file", "mapped_columns"]])

st.subheader("Downloads")
report = data_cleaning.quality_report_frame(cd)
ui.download_csv("Download data-quality report (CSV)", report, "data_quality_report.csv", "dl_quality")
full = analytics.apply_filters(cd.tables, analytics.FilterState())
ui.download_csv("Download top conditions, whole dataset (CSV)", analytics.top_conditions(full.conditions, 50),
                "top_conditions_all.csv", "dl_top")
ui.download_csv("Download monthly encounters, whole dataset (CSV)", analytics.encounters_over_time(full.encounters, "Monthly"),
                "monthly_encounters_all.csv", "dl_month")
ui.footer()
