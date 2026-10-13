"""Shared constants and small helpers. No Streamlit or Plotly imports here."""
from __future__ import annotations

import re

import pandas as pd

# One consistent age-group definition used across the whole application.
AGE_BINS = [0, 18, 35, 50, 65, 80, 200]
AGE_LABELS = ["0–17", "18–34", "35–49", "50–64", "65–79", "80+"]
MAX_PLAUSIBLE_AGE = 120

DISCLAIMER = (
    "Educational and analytical use only. This dashboard uses synthetic data and is not "
    "intended for clinical diagnosis, treatment decisions, or real patient care."
)

CONDITION_PRESETS: dict[str, list[str]] = {
    "All Conditions": [],
    "🩺 Diabetes & Metabolic": ["diabet", "prediabet", "hyperglycemia", "metabolic"],
    "❤️ Hypertension & Cardiovascular": ["hypertens", "heart", "coronary", "cardiac", "infarct", "ischemi"],
    "🫁 Asthma & Respiratory": ["asthma", "bronch", "respirat", "sinus", "copd", "pulmon", "pneumon"],
    "🧠 Stress, Anxiety & Mental Health": ["stress", "depress", "anxiety", "social isolat"],
    "🦠 Viral Infections & COVID-19": ["covid", "viral", "infect", "flu", "influenza", "fever", "cough"],
    "🦴 Musculoskeletal & Arthritis": ["arthrit", "joint", "fractur", "back pain", "osteopor"],
}


def get_conditions_for_preset(preset: str, available_conditions: list[str]) -> list[str]:
    """Return all conditions from available_conditions that match the preset keywords."""
    keywords = CONDITION_PRESETS.get(preset, [])
    if not keywords:
        return []
    return [
        c for c in available_conditions
        if any(k in str(c).lower() for k in keywords)
    ]


def normalise_column_name(name) -> str:
    """'  Birth Date ' -> 'birth_date'; 'ENCOUNTERCLASS' -> 'encounterclass'."""
    text = str(name).replace("\ufeff", "").strip().lower()
    return re.sub(r"[^0-9a-z]+", "_", text).strip("_")


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalise_column_name(c) for c in out.columns]
    return out


def age_group_series(ages: pd.Series) -> pd.Series:
    """Map ages (years) to the shared age groups; missing ages stay missing."""
    return pd.cut(ages, bins=AGE_BINS, labels=AGE_LABELS, right=False)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def fmt_int(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "n/a"
