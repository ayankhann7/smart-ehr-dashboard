"""Cleaning, validation and enrichment of the loaded tables. No Streamlit or Plotly imports.

Nothing is silently invented: unparseable dates become missing (NaT) and are counted, rows that
cannot be linked to a patient are removed and counted, and every operation is written to a log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .data_loader import LoadResult
from .utils import MAX_PLAUSIBLE_AGE, age_group_series

DATE_COLUMNS = {
    "patients": ["birth_date", "death_date"],
    "encounters": ["start", "stop"],
    "conditions": ["start", "stop"],
    "observations": ["date"],
    "medications": ["start", "stop"],
}
UNKNOWN_COLUMNS = {"patients": ["gender", "race", "ethnicity"], "encounters": ["encounter_class"]}
DEDUP_SUBSET = {
    "conditions": ["patient_id", "encounter_id", "start", "code", "description"],
    "observations": ["patient_id", "encounter_id", "date", "code", "description", "value", "units"],
    "medications": ["patient_id", "encounter_id", "start", "stop", "code", "description"],
}
_GENDER_MAP = {"M": "Male", "MALE": "Male", "F": "Female", "FEMALE": "Female",
               "O": "Other", "OTHER": "Other", "U": "Unknown", "UNKNOWN": "Unknown"}
_ETHNICITY_MAP = {"nonhispanic": "Non-Hispanic", "non-hispanic": "Non-Hispanic", "hispanic": "Hispanic"}
_CLASS_MAP = {"urgentcare": "Urgent Care", "urgent care": "Urgent Care", "snf": "SNF"}


@dataclass
class CleanedData:
    tables: dict[str, pd.DataFrame]
    cleaning_log: list[str]
    quality: pd.DataFrame
    missing_values: pd.DataFrame
    file_info: pd.DataFrame
    date_range: tuple
    reference_date: pd.Timestamp
    loaded_at: str
    source_dir: str = ""
    is_demo: bool = False
    warnings: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------- helpers
def _text(series: pd.Series) -> pd.Series:
    """Trim whitespace and turn blank strings into missing values."""
    s = series.astype("string").str.strip()
    return s.where(~(s == "").fillna(False), pd.NA)


def parse_dates(series: pd.Series) -> tuple[pd.Series, int]:
    """Error-tolerant date parsing. Returns (naive UTC timestamps, count of non-blank unparseable values)."""
    s = _text(series)
    parsed = pd.to_datetime(s, errors="coerce", utc=True, format="ISO8601")
    unparsed = parsed.isna() & s.notna()
    if unparsed.any():
        retry = pd.to_datetime(s[unparsed], errors="coerce", utc=True, format="mixed")
        parsed = parsed.where(~unparsed, retry)
    parsed = parsed.dt.tz_convert(None)
    return parsed, int((parsed.isna() & s.notna()).sum())


def compute_age(birth_date: pd.Series, reference_date, death_date: pd.Series | None = None) -> pd.Series:
    """Completed years at `reference_date` (or at death if earlier). Implausible ages become NaN."""
    ref = pd.Timestamp(reference_date)
    end = pd.Series(ref, index=birth_date.index)
    if death_date is not None:
        end = death_date.where(death_date.notna() & (death_date <= ref), ref)
        end = pd.to_datetime(end)
    before_birthday = (end.dt.month < birth_date.dt.month) | (
        (end.dt.month == birth_date.dt.month) & (end.dt.day < birth_date.dt.day))
    years = (end.dt.year.astype("float64") - birth_date.dt.year.astype("float64")
             - before_birthday.astype("float64"))
    years = years.where(birth_date.notna())
    return years.where((years >= 0) & (years <= MAX_PLAUSIBLE_AGE))


def _category(series: pd.Series, mapping: dict, key=lambda s: s.str.lower()) -> pd.Series:
    mapped = key(series).map(mapping)
    out = mapped.where(mapped.notna(), series.str.title())
    return out.fillna("Unknown").astype("string")


def _normalise_gender(series: pd.Series) -> pd.Series:
    return _category(series, _GENDER_MAP, key=lambda s: s.str.upper())


def _normalise_class(series: pd.Series) -> pd.Series:
    return _category(series, _CLASS_MAP)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        out[col] = _text(out[col])
    return out


def _parse_date_cols(df: pd.DataFrame, table: str) -> tuple[pd.DataFrame, int, dict]:
    total, detail = 0, {}
    for col in DATE_COLUMNS.get(table, []):
        if col in df.columns:
            df[col], n = parse_dates(df[col])
            detail[col] = n
            total += n
    return df, total, detail


def _detail(detail: dict) -> str:
    return "; ".join(f"{k}: {v}" for k, v in detail.items() if v) or "none"


def _qrow(table, file, status, rows_original, rows_after, cols_file, cols_used, duplicates=0,
          missing_id=0, unmatched_patient=0, unmatched_encounter=0, invalid=0, detail="none") -> dict:
    return {"table": table, "file": file, "status": status, "rows_original": rows_original,
            "rows_after_cleaning": rows_after, "rows_removed": rows_original - rows_after,
            "columns_in_file": cols_file, "columns_used": cols_used,
            "duplicates_removed": duplicates, "missing_patient_id_removed": missing_id,
            "unmatched_patient_refs_removed": unmatched_patient,
            "unmatched_encounter_refs": unmatched_encounter,
            "invalid_dates": invalid, "invalid_date_detail": detail}


# ----------------------------------------------------------------------------- main entry
def clean_dataset(load: LoadResult, reference_date=None) -> CleanedData:
    raw = load.tables
    info = {i["table"]: i for i in load.file_info}
    log: list[str] = []
    qrows: list[dict] = []
    snapshots: dict[str, dict[str, int]] = {}
    out: dict[str, pd.DataFrame] = {}

    def snap(table, df):
        snapshots[table] = {c: int(df[c].isna().sum()) for c in df.columns}

    def file_meta(table):
        i = info.get(table, {})
        return i.get("file", ""), i.get("original_columns", 0), i.get("columns_used", 0)

    # ---- patients
    p = _prepare(raw["patients"])
    n_orig = len(p)
    snap("patients", p)
    p = p[p["patient_id"].notna()]
    miss_id = n_orig - len(p)
    dup = p.duplicated("patient_id", keep="first")
    n_dup = int(dup.sum())
    p = p[~dup].copy()
    p, invalid, detail = _parse_date_cols(p, "patients")
    today = pd.Timestamp.today().normalize()
    if "birth_date" in p:
        future = p["birth_date"] > today
        if future.any():
            p.loc[future, "birth_date"] = pd.NaT
            invalid += int(future.sum())
            detail["birth_date"] = detail.get("birth_date", 0) + int(future.sum())
            log.append(f"patients: {int(future.sum())} birth date(s) in the future set to missing.")
        if "death_date" in p:
            bad = p["death_date"].notna() & (p["death_date"] < p["birth_date"])
            if bad.any():
                p.loc[bad, "death_date"] = pd.NaT
                invalid += int(bad.sum())
                detail["death_date"] = detail.get("death_date", 0) + int(bad.sum())
                log.append(f"patients: {int(bad.sum())} death date(s) earlier than birth set to missing.")
    for col, fn in (("gender", _normalise_gender),
                    ("race", lambda s: _category(s, {})),
                    ("ethnicity", lambda s: _category(s, _ETHNICITY_MAP))):
        if col in p:
            before = p[col]
            p[col] = fn(before)
            changed = int((before.notna() & (before != p[col])).sum())
            if changed:
                log.append(f"patients: harmonised {changed} '{col}' label(s) (case/abbreviation).")
    if miss_id:
        log.append(f"patients: removed {miss_id} row(s) with no patient ID.")
    if n_dup:
        log.append(f"patients: removed {n_dup} duplicate patient ID row(s) (first kept).")
    if invalid:
        log.append(f"patients: {invalid} unparseable/invalid date value(s) set to missing ({_detail(detail)}).")
    patient_ids = p["patient_id"]
    f, cf, cu = file_meta("patients")
    qrows.append(_qrow("patients", f, "loaded", n_orig, len(p), cf, cu, n_dup, miss_id, 0, 0, invalid, _detail(detail)))
    out["patients"] = p

    # ---- encounters
    e = _prepare(raw["encounters"])
    n_orig = len(e)
    snap("encounters", e)
    e = e[e["patient_id"].notna()]
    miss_id = n_orig - len(e)
    if "encounter_id" in e:
        dup = e.duplicated("encounter_id", keep="first") & e["encounter_id"].notna()
    else:
        dup = e.duplicated(keep="first")
    n_dup = int(dup.sum())
    e = e[~dup]
    orphan = ~e["patient_id"].isin(patient_ids)
    n_orphan = int(orphan.sum())
    e = e[~orphan].copy()
    e, invalid, detail = _parse_date_cols(e, "encounters")
    if "encounter_class" in e:
        before = e["encounter_class"]
        e["encounter_class"] = _normalise_class(before)
        changed = int((before.notna() & (before != e["encounter_class"])).sum())
        if changed:
            log.append(f"encounters: harmonised {changed} encounter class label(s).")
    if miss_id:
        log.append(f"encounters: removed {miss_id} row(s) with no patient ID.")
    if n_dup:
        log.append(f"encounters: removed {n_dup} duplicate encounter row(s).")
    if n_orphan:
        log.append(f"encounters: removed {n_orphan} row(s) whose patient ID is not in patients.csv.")
    if invalid:
        log.append(f"encounters: {invalid} unparseable date value(s) set to missing ({_detail(detail)}); "
                   "those rows are kept but excluded from time-based analyses.")
    f, cf, cu = file_meta("encounters")
    qrows.append(_qrow("encounters", f, "loaded", n_orig, len(e), cf, cu, n_dup, miss_id, n_orphan, 0, invalid, _detail(detail)))
    out["encounters"] = e
    encounter_ids = e["encounter_id"] if "encounter_id" in e else pd.Series(dtype="string")

    # ---- conditions / observations / medications
    for table in ("conditions", "observations", "medications"):
        if table not in raw:
            qrows.append(_qrow(table, "", "not provided", 0, 0, 0, 0))
            continue
        d = _prepare(raw[table])
        n_orig = len(d)
        snap(table, d)
        d = d[d["patient_id"].notna()]
        miss_id = n_orig - len(d)
        d = d.copy()
        if "description" not in d.columns and "code" in d.columns:
            d["description"] = d["code"]
            log.append(f"{table}: no description column; using codes as labels.")
        elif "description" in d.columns and "code" in d.columns:
            filled = int((d["description"].isna() & d["code"].notna()).sum())
            if filled:
                d["description"] = d["description"].fillna(d["code"])
                log.append(f"{table}: {filled} missing description(s) replaced by the record's code.")
        if "description" in d.columns:
            n_unspec = int(d["description"].isna().sum())
            d["description"] = d["description"].fillna("Unspecified")
            if n_unspec:
                log.append(f"{table}: {n_unspec} record(s) with no description or code labelled 'Unspecified'.")
        d, invalid, detail = _parse_date_cols(d, table)
        subset = [c for c in DEDUP_SUBSET[table] if c in d.columns]
        dup = d.duplicated(subset=subset, keep="first")
        n_dup = int(dup.sum())
        d = d[~dup]
        orphan = ~d["patient_id"].isin(patient_ids)
        n_orphan = int(orphan.sum())
        d = d[~orphan].copy()
        unmatched_enc = 0
        if "encounter_id" in d.columns and "encounter_id" in e.columns:
            unmatched_enc = int((d["encounter_id"].notna() & ~d["encounter_id"].isin(encounter_ids)).sum())
        if table == "observations" and "value" in d.columns:
            d["value_numeric"] = pd.to_numeric(d["value"], errors="coerce").astype("float64")
        if miss_id:
            log.append(f"{table}: removed {miss_id} row(s) with no patient ID.")
        if n_dup:
            log.append(f"{table}: removed {n_dup} duplicate record(s).")
        if n_orphan:
            log.append(f"{table}: removed {n_orphan} row(s) whose patient ID is not in patients.csv.")
        if unmatched_enc:
            log.append(f"{table}: {unmatched_enc} row(s) reference an encounter ID not found in encounters.csv (kept).")
        if invalid:
            log.append(f"{table}: {invalid} unparseable date value(s) set to missing ({_detail(detail)}).")
        f, cf, cu = file_meta(table)
        qrows.append(_qrow(table, f, "loaded", n_orig, len(d), cf, cu, n_dup, miss_id, n_orphan, unmatched_enc, invalid, _detail(detail)))
        out[table] = d

    # ---- reference date and ages
    if reference_date is None:
        starts = out["encounters"]["start"].dropna() if "start" in out["encounters"] else pd.Series(dtype="datetime64[ns]")
        reference_date = starts.max() if len(starts) else pd.Timestamp.today().normalize()
    reference_date = pd.Timestamp(reference_date)
    p = out["patients"]
    if "birth_date" in p:
        p["age"] = compute_age(p["birth_date"], reference_date, p["death_date"] if "death_date" in p else None)
    else:
        p["age"] = np.nan
    p["age_group"] = age_group_series(p["age"])
    n_noage = int(p["age"].isna().sum())
    if n_noage:
        log.append(f"patients: {n_noage} patient(s) have a missing/invalid birth date or implausible age "
                   "and are excluded from age-specific calculations.")
    log.append(f"Ages are completed years as of {reference_date.date()} (latest encounter date), "
               "or at death where a death date exists.")

    for table in out:
        out[table] = out[table].reset_index(drop=True)

    # ---- missing-value table (original vs after cleaning)
    mrows = []
    for table, df in out.items():
        n_orig = int(info[table]["original_rows"])
        for col in snapshots[table]:
            if col not in df.columns:
                continue
            after = int(df[col].isna().sum())
            if col in UNKNOWN_COLUMNS.get(table, []):
                after += int((df[col] == "Unknown").sum())
            mrows.append({"table": table, "column": col, "missing_original": snapshots[table][col],
                          "pct_missing_original": round(100 * snapshots[table][col] / n_orig, 2) if n_orig else 0.0,
                          "missing_or_unknown_after_cleaning": after})
    enc_starts = out["encounters"]["start"].dropna() if "start" in out["encounters"] else pd.Series(dtype="datetime64[ns]")
    date_range = (enc_starts.min(), enc_starts.max()) if len(enc_starts) else (None, None)

    return CleanedData(
        tables=out, cleaning_log=log, quality=pd.DataFrame(qrows),
        missing_values=pd.DataFrame(mrows), file_info=pd.DataFrame(load.file_info),
        date_range=date_range, reference_date=reference_date,
        loaded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source_dir=load.source_dir, is_demo=load.is_demo, warnings=list(load.warnings))


def quality_report_frame(cleaned: CleanedData) -> pd.DataFrame:
    """Long-format data-quality report (aggregate counts only; no row-level clinical data)."""
    rows = []
    dr = cleaned.date_range
    for metric, value in (("source_directory", cleaned.source_dir), ("loaded_at", cleaned.loaded_at),
                          ("demo_dataset", cleaned.is_demo),
                          ("encounter_date_min", dr[0].date() if dr[0] is not None and pd.notna(dr[0]) else "n/a"),
                          ("encounter_date_max", dr[1].date() if dr[1] is not None and pd.notna(dr[1]) else "n/a"),
                          ("age_reference_date", cleaned.reference_date.date())):
        rows.append({"section": "dataset", "table": "", "metric": metric, "value": str(value)})
    for rec in cleaned.quality.to_dict("records"):
        for metric, value in rec.items():
            if metric != "table":
                rows.append({"section": "table_summary", "table": rec["table"], "metric": metric, "value": str(value)})
    for rec in cleaned.missing_values.to_dict("records"):
        for metric in ("missing_original", "pct_missing_original", "missing_or_unknown_after_cleaning"):
            rows.append({"section": "missing_values", "table": rec["table"], "metric": f"{rec['column']}.{metric}",
                         "value": str(rec[metric])})
    for i, text in enumerate(cleaned.cleaning_log, 1):
        rows.append({"section": "cleaning_log", "table": "", "metric": f"step_{i}", "value": text})
    for i, text in enumerate(cleaned.warnings, 1):
        rows.append({"section": "warnings", "table": "", "metric": f"warning_{i}", "value": text})
    return pd.DataFrame(rows, columns=["section", "table", "metric", "value"])
