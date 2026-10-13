"""Streamlit presentation layer: page shell, sidebar, filters, cards and small helpers."""
from __future__ import annotations

import html
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from . import analytics, charts, data_cleaning, data_loader, demo_data, file_manager
from .analytics import FilteredData, FilterState
from .data_cleaning import CleanedData
from .utils import CONDITION_PRESETS, DISCLAIMER, get_conditions_for_preset, to_csv_bytes

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DEMO_DIR = ROOT / "data" / "demo"
DEFAULT_DATA_DIR = os.environ.get("EHR_DATA_DIR", "data")
FILTER_KEYS = ["f_dates", "f_age", "f_gender", "f_class", "f_cond", "f_cond_cat"]

LOGO_ICON_SVG = """<svg width="40" height="40" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="ehrGradIcon" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F766E"/>
      <stop offset="100%" stop-color="#0D9488"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="40" height="40" rx="11" fill="url(#ehrGradIcon)"/>
  <path d="M22 11v22M11 22h22" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round"/>
  <path d="M11 23h5l2.5-5 3.5 10 3-7 2.5 4h5.5" fill="none" stroke="#5EEAD4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

CSS = """
<style>
html, body, .stApp {
  overflow-x: hidden !important;
  width: 100% !important;
  max-width: 100vw !important;
  box-sizing: border-box !important;
  background: #F8FAFC;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
.block-container {
  padding-top: 1rem;
  padding-bottom: 2.8rem;
  max-width: 1420px;
  width: 100% !important;
  box-sizing: border-box !important;
  overflow-x: hidden !important;
}
h1,h2,h3,h4{color:#0F172A;letter-spacing:-0.02em;}
[data-testid="stSidebar"]{border-right:1px solid #E2E8F0;background-color:#FFFFFF;}

/* Top Aligned Header Banner */
.ehr-header{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:1rem;
  background:#FFFFFF;
  border:1px solid #E2E8F0;
  border-radius:14px;
  padding:1.1rem 1.4rem;
  margin-bottom:1.25rem;
  box-shadow:0 1px 3px rgba(15,23,42,.04);
}
.ehr-header-main{
  display:flex;
  align-items:center;
  gap:1.1rem;
}
.ehr-header-badge{
  flex-shrink:0;
  display:flex;
  align-items:center;
  justify-content:center;
  transition: transform 0.2s ease;
}
.ehr-header-badge:hover {
  transform: scale(1.05);
}
.ehr-header-text{
  display:flex;
  flex-direction:column;
}
.ehr-header-title{
  margin:0;
  font-size:1.65rem;
  font-weight:750;
  color:#0F172A;
  line-height:1.2;
  letter-spacing:-0.02em;
}
.ehr-header-sub{
  margin:.25rem 0 0;
  font-size:.86rem;
  color:#64748B;
  line-height:1.4;
}
.ehr-header-meta{
  display:flex;
  align-items:center;
  flex-wrap:wrap;
  gap:.45rem;
}

/* Sidebar Brand Header */
.ehr-sidebar-brand{
  display:flex;
  align-items:center;
  gap:.85rem;
  padding:.4rem .2rem .9rem;
  border-bottom:1px solid #E2E8F0;
  margin-bottom:.8rem;
}
.ehr-sidebar-brand a:hover .ehr-brand-title {
  color: #0F766E !important;
}
.ehr-brand-title{
  font-size:1.05rem;
  font-weight:800;
  color:#0F172A;
  line-height:1.15;
  letter-spacing:-0.02em;
  transition: color 0.15s ease;
}
.ehr-brand-sub{
  font-size:.70rem;
  font-weight:700;
  color:#0F766E;
  text-transform:uppercase;
  letter-spacing:.06em;
}

/* Cards & Grid */
.ehr-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.8rem;margin:.5rem 0 1.1rem;}
@media(min-width:900px){.ehr-grid{grid-template-columns:repeat(auto-fit,minmax(220px,1fr));}}
.ehr-card{background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:1rem 1.15rem;min-width:0;
 box-shadow:0 1px 3px rgba(15,23,42,.05);transition:transform .15s ease, box-shadow .15s ease;}
.ehr-card:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(15,23,42,.08);}
.ehr-card .ico{width:36px;height:36px;border-radius:10px;background:#F0FDFA;color:#0F766E;display:flex;
 align-items:center;justify-content:center;margin-bottom:.5rem;border:1px solid #CCFBF1;}
.ehr-card .lbl{font-size:.74rem;color:#64748B;font-weight:650;text-transform:uppercase;letter-spacing:.05em;}
.ehr-card .val{font-size:1.75rem;font-weight:750;color:#0F172A;line-height:1.2;overflow-wrap:anywhere;}
.ehr-card .sub{font-size:.8rem;color:#64748B;margin-top:.2rem;}

.ehr-pill{display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .75rem;border-radius:999px;font-size:.8rem;font-weight:600;
 border:1px solid #E2E8F0;background:#fff;margin:.1rem .2rem;}
.ehr-pill.ok{color:#15803D;border-color:#BBF7D0;background:#F0FDF4;}
.ehr-pill.warn{color:#B45309;border-color:#FDE68A;background:#FFFBEB;}
.ehr-pill.info{color:#0369A1;border-color:#BAE6FD;background:#F0F9FF;}
.ehr-footer{margin-top:2.5rem;padding-top:.85rem;border-top:1px solid #E2E8F0;color:#64748B;font-size:.8rem;}
div.stButton>button,div.stDownloadButton>button{min-height:42px;border-radius:9px;font-weight:600;}
:focus-visible{outline:3px solid #0F766E !important;outline-offset:2px;}
@media(max-width:768px){
 .block-container{padding-left:.65rem;padding-right:.65rem;}
 .ehr-header{padding:.9rem 1rem;flex-direction:column;align-items:flex-start;}
 .ehr-header-title{font-size:1.35rem;}
 .ehr-card{padding:.75rem .85rem;} .ehr-card .val{font-size:1.4rem;}
}
@media(prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important;scroll-behavior:auto !important;}}
</style>
"""

_ICONS = {
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "clipboard": '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "pill": '<path d="M10.5 20.5 3.5 13.5a5 5 0 0 1 7-7l7 7a5 5 0 0 1-7 7z"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/>',
}


# ----------------------------------------------------------------------------- page shell
def configure_page() -> None:
    """Call once, first, from app.py (st.set_page_config must run before any other Streamlit call)."""
    st.set_page_config(page_title="Smart EHR | Hospital Patient Analytics", page_icon="🏥", layout="wide",
                       initial_sidebar_state="auto")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        st.logo(str(ASSETS / "logo.svg"), size="large")
    except Exception:
        pass
    with st.sidebar:
        brand_html = (
            '<div class="ehr-sidebar-brand">'
            '<a href="/" target="_self" style="text-decoration:none; display:flex; align-items:center; gap:0.85rem; color:inherit;">'
            f'<div aria-hidden="true">{LOGO_ICON_SVG}</div>'
            '<div>'
            '<div class="ehr-brand-title">Smart EHR Analytics</div>'
            '<div class="ehr-brand-sub">Hospital Intelligence</div>'
            '</div>'
            '</a>'
            '</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)


def stretch(func, *args, **kwargs):
    """Call a Streamlit element full-width across Streamlit versions (width= vs use_container_width=)."""
    try:
        return func(*args, width="stretch", **kwargs)
    except Exception:
        return func(*args, use_container_width=True, **kwargs)


def show_chart(fig, key: str | None = None) -> None:
    stretch(st.plotly_chart, fig, config=charts.CHART_CONFIG, key=key)


def show_table(df: pd.DataFrame, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = height
    stretch(st.dataframe, df, **kwargs)


def download_csv(label: str, df: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(label, to_csv_bytes(df), file_name=filename, mime="text/csv", key=key,
                       disabled=df.empty, help="Aggregated results only." if not df.empty else "Nothing to export.")


def metric_cards(cards: list[dict]) -> None:
    items = []
    for c in cards:
        icon = _ICONS.get(c.get("icon", "activity"), _ICONS["activity"])
        sub = f'<div class="sub">{html.escape(str(c["sub"]))}</div>' if c.get("sub") else ""
        items.append(
            f'<div class="ehr-card" role="group" aria-label="{html.escape(c["label"])}">'
            f'<div class="ico" aria-hidden="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{icon}</svg></div>'
            f'<div class="lbl">{html.escape(c["label"])}</div><div class="val">{html.escape(str(c["value"]))}</div>{sub}</div>')
    st.markdown('<div class="ehr-grid">' + "".join(items) + "</div>", unsafe_allow_html=True)


def empty_state(message: str = "No records match the selected filters.") -> None:
    st.info(f"{message} Adjust or reset the filters in the sidebar.", icon="ℹ️")


def footer() -> None:
    footer_html = (
        '<div class="ehr-footer" role="contentinfo">'
        '<div style="margin-bottom:0.4rem;">'
        '<strong>Smart EHR Analytics</strong> · © 2026 All rights reserved'
        '</div>'
        f'<div style="color:#94A3B8; font-size:0.75rem;">Educational & analytical use only · synthetic EHR data · {html.escape(DISCLAIMER)}</div>'
        '</div>'
    )
    st.markdown(footer_html, unsafe_allow_html=True)


def keep_filters() -> None:
    """On pages that do not draw the filter widgets, keep their state alive across navigation."""
    for key in FILTER_KEYS:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


# ----------------------------------------------------------------------------- data loading
@st.cache_data(show_spinner="Loading and cleaning dataset…")
def load_dataset(data_dir: str, signature: tuple) -> CleanedData:
    """Cached; `signature` (file names, sizes, mtimes) changes whenever a CSV changes, invalidating the cache."""
    return data_cleaning.clean_dataset(data_loader.load_tables(data_dir))


def _resolve(text: str) -> Path:
    p = Path(text).expanduser()
    return p if p.is_absolute() else ROOT / p


def _enable_demo() -> None:
    demo_data.generate_demo_dataset(DEMO_DIR)
    st.session_state["use_demo"] = True


def setup_screen(error: str | None) -> None:
    st.title("Dataset setup")
    if error:
        st.error(error)
    st.markdown("This dashboard analyses the **Synthea synthetic patient records** (CSV export). "
                "No valid dataset was detected yet.")

    target = file_manager.get_dataset_target_dir(_resolve(st.session_state.get("data_dir", DEFAULT_DATA_DIR)))
    with st.expander("📁 Upload Dataset CSV Files", expanded=True):
        file_manager.render_file_manager(target, is_sidebar=False, key_prefix="setup_fm")

    st.markdown("---")
    st.markdown("Or configure a folder / download:")
    st.markdown("**1.** Download a CSV sample set from "
                "[synthetichealth.github.io/downloads.html](https://synthetichealth.github.io/downloads.html).  \n"
                "**2.** Unzip it and copy the files below into the `data/` folder of this project "
                "(or point the sidebar *Data folder* box at the folder).  \n"
                "**3.** Click *Reload data* in the sidebar.")
    show_table(pd.DataFrame({
        "File": ["patients.csv", "encounters.csv", "conditions.csv", "observations.csv", "medications.csv"],
        "Status": ["Required", "Required", "Required", "Optional", "Optional"],
        "Key columns": ["Id, BIRTHDATE, GENDER (DEATHDATE, RACE, ETHNICITY)", "Id, PATIENT, START, ENCOUNTERCLASS",
                        "PATIENT, ENCOUNTER, START, DESCRIPTION", "PATIENT, DATE, DESCRIPTION, VALUE, UNITS",
                        "PATIENT, START, DESCRIPTION"]}))
    st.caption("Just want to try the app? A small randomly generated demo set (clearly labelled, not Synthea, "
               "not real) can be created locally.")
    st.button("Generate demo dataset", on_click=_enable_demo, key="gen_demo")
    footer()


def _status_pill(cleaned: CleanedData, n_patients: int) -> str:
    if cleaned.is_demo:
        return f'<span class="ehr-pill warn">⚠ DEMO data (not Synthea, not real) · {n_patients:,} patients</span>'
    return f'<span class="ehr-pill ok">✔ Dataset loaded · {n_patients:,} patients</span>'


def _sidebar_source() -> tuple[Path, str]:
    with st.sidebar:
        with st.expander("📁 Dataset Files & Source", expanded=False):
            st.text_input("Data folder", value=DEFAULT_DATA_DIR, key="data_dir",
                          help="Relative paths are resolved from the project folder.")
            st.checkbox("Use demo data", key="use_demo", help="Randomly generated; not Synthea, not real.")
            if st.button("🔄 Reload data", key="reload", help="Re-read and re-clean the CSV files."):
                load_dataset.clear()
                st.rerun()
            st.markdown("---")
            target = file_manager.get_dataset_target_dir(_resolve(st.session_state.get("data_dir", DEFAULT_DATA_DIR)))
            file_manager.render_file_manager(target, is_sidebar=True, key_prefix="sb_fm")
    if st.session_state.get("use_demo"):
        if not (DEMO_DIR / "patients.csv").exists():
            demo_data.generate_demo_dataset(DEMO_DIR)
        return DEMO_DIR, "demo"
    return _resolve(st.session_state.get("data_dir", DEFAULT_DATA_DIR)), "real"


# ----------------------------------------------------------------------------- filters
def _bounds(cleaned: CleanedData) -> dict:
    t = cleaned.tables
    ages = t["patients"]["age"].dropna()
    b = {"dates": None, "age_max": max(1, int(math.ceil(ages.max()))) if len(ages) else 0, "genders": [], "classes": [], "conds": []}
    lo, hi = cleaned.date_range
    if lo is not None and pd.notna(lo):
        b["dates"] = (lo.date(), hi.date())
    if "gender" in t["patients"]:
        b["genders"] = sorted(t["patients"]["gender"].dropna().astype(str).unique())
    if "encounter_class" in t["encounters"]:
        b["classes"] = sorted(t["encounters"]["encounter_class"].dropna().astype(str).unique())
    if "description" in t["conditions"]:
        b["conds"] = sorted(t["conditions"]["description"].dropna().astype(str).unique())
    return b


def _reset_filters() -> None:
    b = st.session_state.get("_bounds")
    if not b:
        return
    st.session_state["f_dates"] = b["dates"]
    st.session_state["f_age"] = (0, b["age_max"])
    st.session_state["f_gender"] = []
    st.session_state["f_class"] = []
    st.session_state["f_cond_cat"] = "All Conditions"
    st.session_state["f_cond"] = []


def render_filters(cleaned: CleanedData) -> FilterState:
    b = _bounds(cleaned)
    if st.session_state.get("_dataset_id") != cleaned.loaded_at:
        st.session_state["_bounds"] = b
        st.session_state["_dataset_id"] = cleaned.loaded_at
        _reset_filters()
    with st.sidebar:
        st.markdown("### Filters")
        st.button("Reset filters", on_click=_reset_filters, key="reset_filters")
        if b["dates"]:
            st.date_input("Date range (encounters & conditions)", value=b["dates"], key="f_dates", min_value=b["dates"][0], max_value=b["dates"][1])
        if b["age_max"] > 0:
            st.slider("Age range (years)", 0, b["age_max"], value=(0, b["age_max"]), key="f_age")
        if b["genders"]:
            st.multiselect("Gender", b["genders"], key="f_gender",
                           placeholder="All genders (or select specific)")
        if b["classes"]:
            st.multiselect("Encounter class", b["classes"], key="f_class",
                           placeholder="All classes (or select specific)")
        if b["conds"]:
            st.markdown("---")
            st.markdown("##### 🩺 Health Conditions")
            cat_list = list(CONDITION_PRESETS.keys())
            cur_cat = st.session_state.get("f_cond_cat", "All Conditions")
            if cur_cat not in cat_list:
                cur_cat = "All Conditions"
            chosen_cat = st.selectbox(
                "Condition Category / Preset",
                cat_list,
                index=cat_list.index(cur_cat),
                key="f_cond_cat",
                help="Quick preset to focus on chronic diseases like Diabetes, Hypertension, Asthma, etc."
            )
            preset_matches = get_conditions_for_preset(chosen_cat, b["conds"])
            if chosen_cat != "All Conditions":
                st.caption(f"Preset active: **{len(preset_matches)}** related condition(s) (e.g. Diabetes, Prediabetes).")
            st.multiselect(
                "Specific Condition(s)",
                b["conds"],
                key="f_cond",
                help="Search and pick specific condition descriptions, or leave empty to use preset."
            )
    ss = st.session_state
    start = end = None
    if b["dates"] and "f_dates" in ss:
        d = ss["f_dates"]
        d = tuple(d) if isinstance(d, (list, tuple)) else (d,)
        s, e = d[0], (d[1] if len(d) > 1 else b["dates"][1])
        if (s, e) != b["dates"]:
            start, end = pd.Timestamp(s), pd.Timestamp(e)
    age = None
    if b["age_max"] > 0 and "f_age" in ss:
        raw_age = ss["f_age"]
        if isinstance(raw_age, (list, tuple)) and len(raw_age) == 2:
            if (int(raw_age[0]), int(raw_age[1])) != (0, b["age_max"]):
                age = (int(raw_age[0]), int(raw_age[1]))
        elif isinstance(raw_age, (int, float)):
            if (0, int(raw_age)) != (0, b["age_max"]):
                age = (0, int(raw_age))

    # Empty multiselect or all selected means NO filter (all included)
    genders = tuple(ss["f_gender"]) if (ss.get("f_gender") and set(ss["f_gender"]) != set(b["genders"])) else None
    classes = tuple(ss["f_class"]) if (ss.get("f_class") and set(ss["f_class"]) != set(b["classes"])) else None

    cond_selected = list(ss.get("f_cond", []))
    chosen_cat = ss.get("f_cond_cat", "All Conditions")
    if chosen_cat != "All Conditions":
        preset_matches = get_conditions_for_preset(chosen_cat, b["conds"])
        active_conds = cond_selected if cond_selected else preset_matches
    else:
        active_conds = cond_selected

    return FilterState(start, end, age, genders, classes, tuple(active_conds))


def _filter_summary(f: FilterState) -> str:
    parts = []
    if f.start_date is not None:
        parts.append(f"{f.start_date.date()} → {f.end_date.date()}")
    if f.age_range is not None:
        parts.append(f"age {f.age_range[0]}–{f.age_range[1]}")
    if f.genders:
        parts.append("gender: " + ", ".join(f.genders))
    if f.encounter_classes:
        parts.append("class: " + ", ".join(f.encounter_classes))
    if f.conditions:
        if len(f.conditions) == 1:
            parts.append(f"condition: {f.conditions[0]}")
        else:
            parts.append(f"{len(f.conditions)} condition(s)")
    return " · ".join(parts)


# ----------------------------------------------------------------------------- bootstrap
@dataclass
class Context:
    cleaned: CleanedData
    fd: FilteredData
    filters: FilterState

    @property
    def tables(self) -> dict:
        return self.cleaned.tables


def page_header(title: str, subtitle: str, cleaned: CleanedData, n_patients: int, filters: FilterState | None = None) -> None:
    status_html = _status_pill(cleaned, n_patients)
    filter_html = f'<span class="ehr-pill info">🔍 Filters: {html.escape(_filter_summary(filters))}</span>' if (filters is not None and filters.any_active) else ""
    header_html = (
        '<div class="ehr-header">'
        '<div class="ehr-header-main">'
        f'<a href="/" target="_self" title="Go to Dashboard Home" style="text-decoration:none; display:flex; align-items:center; gap:1.1rem; color:inherit;">'
        f'<div class="ehr-header-badge" aria-hidden="true">{LOGO_ICON_SVG}</div>'
        '<div class="ehr-header-text">'
        f'<h1 class="ehr-header-title">{html.escape(title)}</h1>'
        f'<p class="ehr-header-sub">{html.escape(subtitle)}</p>'
        '</div>'
        '</a>'
        '</div>'
        '<div class="ehr-header-meta">'
        f'{status_html}'
        f'{filter_html}'
        '</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def bootstrap(title: str, subtitle: str, use_filters: bool = True, require_records: bool = True) -> Context:
    """Load data, draw the sidebar, apply filters and render the page header. Stops the script on failure."""
    folder, _ = _sidebar_source()
    try:
        found = data_loader.find_dataset_dir(folder)
        if found is None:
            raise data_loader.DatasetError(f"No dataset found in '{folder}'.")
        cleaned = load_dataset(str(found), data_loader.dataset_signature(found))
    except data_loader.DatasetError as exc:
        setup_screen(str(exc))
        st.stop()
    except Exception:  # unexpected: keep details in the log, show a plain message
        logger.exception("Unexpected error while loading the dataset")
        st.error("The dataset could not be processed. Check that the CSV files are valid Synthea exports "
                 "(see the Data Quality page and README). Details were written to the application log.")
        st.stop()
    if cleaned.tables["patients"].empty:
        st.error("The dataset contains no valid patient records after cleaning. See the Data Quality page.")
    if use_filters:
        filters = render_filters(cleaned)
    else:
        keep_filters()
        filters = FilterState()
    fd = analytics.apply_filters(cleaned.tables, filters)
    page_header(title, subtitle, cleaned, int(cleaned.tables["patients"]["patient_id"].nunique()), filters if use_filters else None)
    if cleaned.is_demo:
        st.warning("Demo mode: the values below come from a randomly generated demo set, not from Synthea or real "
                   "patients. Do not interpret them as findings.", icon="⚠️")
    if use_filters and require_records and fd.patients.empty and fd.encounters.empty and fd.conditions.empty:
        empty_state()
        st.button("Reset filters", on_click=_reset_filters, key="reset_filters_main")
        footer()
        st.stop()
    return Context(cleaned, fd, filters)
