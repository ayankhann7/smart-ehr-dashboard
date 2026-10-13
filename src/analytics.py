"""Filtering and descriptive analytics (pure pandas). No Streamlit or Plotly imports here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .utils import AGE_LABELS

GRAINS = ("Daily", "Monthly", "Yearly")
_FREQ = {"Daily": "D", "Monthly": "MS", "Yearly": "YS"}
_LABEL_FMT = {"Daily": "%Y-%m-%d", "Monthly": "%Y-%m", "Yearly": "%Y"}


# ----------------------------------------------------------------------------- filtering
@dataclass(frozen=True)
class FilterState:
    """None means 'filter not active'."""
    start_date: Optional[pd.Timestamp] = None
    end_date: Optional[pd.Timestamp] = None            # inclusive
    age_range: Optional[tuple] = None                  # (min, max) years
    genders: Optional[tuple] = None
    encounter_classes: Optional[tuple] = None
    conditions: tuple = ()                             # empty = not active

    @property
    def any_active(self) -> bool:
        return any([self.start_date is not None, self.end_date is not None, self.age_range is not None,
                    self.genders is not None, self.encounter_classes is not None, bool(self.conditions)])


@dataclass
class FilteredData:
    patients: pd.DataFrame
    encounters: pd.DataFrame
    conditions: pd.DataFrame
    observations: Optional[pd.DataFrame]
    medications: Optional[pd.DataFrame]
    filters: FilterState


def _in_range(df: pd.DataFrame, col: str, f: FilterState) -> pd.DataFrame:
    if df is None or col not in df.columns or (f.start_date is None and f.end_date is None):
        return df
    mask = df[col].notna()
    if f.start_date is not None:
        mask &= df[col] >= f.start_date
    if f.end_date is not None:
        mask &= df[col] < (f.end_date + pd.Timedelta(days=1))
    return df[mask]


def apply_filters(tables: dict, f: FilterState) -> FilteredData:
    """Apply filters consistently through patient IDs and encounter relationships.

    * Age / gender restrict which patients are eligible.
    * Date range and encounter class restrict encounters, conditions, observations and medications;
      patients are then those with at least one matching encounter or condition record.
    * A diagnosis filter keeps only the selected condition records and the patients who have them
      (and those patients' encounters).
    """
    patients, enc, cond = tables["patients"], tables["encounters"], tables["conditions"]
    obs, med = tables.get("observations"), tables.get("medications")

    eligible = patients
    if f.age_range is not None and "age" in eligible:
        eligible = eligible[eligible["age"].between(f.age_range[0], f.age_range[1])]
    if f.genders is not None and "gender" in eligible:
        eligible = eligible[eligible["gender"].isin(list(f.genders))]
    ids = eligible["patient_id"]

    e0 = _in_range(enc[enc["patient_id"].isin(ids)], "start", f)
    c0 = _in_range(cond[cond["patient_id"].isin(ids)], "start", f)
    class_active = f.encounter_classes is not None and "encounter_class" in e0
    if class_active:
        e0 = e0[e0["encounter_class"].isin(list(f.encounter_classes))]
        if "encounter_id" in c0 and "encounter_id" in e0:
            c0 = c0[c0["encounter_id"].isin(e0["encounter_id"])]

    activity_active = f.start_date is not None or f.end_date is not None or class_active
    if f.conditions and "description" in c0:
        c = c0[c0["description"].isin(list(f.conditions))]
        keep = pd.Index(c["patient_id"].unique())
        e = e0[e0["patient_id"].isin(keep)]
    elif activity_active:
        keep = pd.Index(pd.concat([e0["patient_id"], c0["patient_id"]]).unique())
        c, e = c0, e0
    else:
        keep, c, e = ids, c0, e0

    def sub(df, date_col):
        if df is None:
            return None
        return _in_range(df[df["patient_id"].isin(keep)], date_col, f)

    return FilteredData(eligible[eligible["patient_id"].isin(keep)], e, c,
                        sub(obs, "date"), sub(med, "start"), f)


# ----------------------------------------------------------------------------- metrics
def summary_metrics(fd: FilteredData) -> dict:
    p = fd.patients
    ages = p["age"].dropna() if "age" in p else pd.Series(dtype="float64")
    n_pat = int(p["patient_id"].nunique()) if len(p) else 0
    n_enc, n_cond = len(fd.encounters), len(fd.conditions)
    return {
        "patients": n_pat,
        "encounters": n_enc,
        "conditions": n_cond,
        "distinct_conditions": int(fd.conditions["description"].nunique()) if n_cond and "description" in fd.conditions else 0,
        "avg_age": float(ages.mean()) if len(ages) else None,
        "age_n": int(len(ages)),
        "age_excluded": int(n_pat - len(ages)),
        "encounters_per_patient": (n_enc / n_pat) if n_pat else None,
    }


def age_summary(patients: pd.DataFrame) -> dict:
    ages = patients["age"].dropna() if "age" in patients else pd.Series(dtype="float64")
    if ages.empty:
        return {"n": 0, "median": None, "min": None, "max": None, "excluded": len(patients)}
    return {"n": int(len(ages)), "median": float(ages.median()), "min": float(ages.min()),
            "max": float(ages.max()), "excluded": int(len(patients) - len(ages))}


def age_group_counts(patients: pd.DataFrame) -> pd.DataFrame:
    """Patients per shared age group (zeros included); patients without a valid age are excluded."""
    if "age_group" in patients and len(patients):
        counts = patients["age_group"].astype("object").value_counts()
    else:
        counts = pd.Series(dtype="int64")
    counts = counts.reindex(AGE_LABELS, fill_value=0).astype(int)
    total = int(counts.sum())
    return pd.DataFrame({"age_group": AGE_LABELS, "patients": counts.values,
                         "percent": [round(100 * v / total, 1) if total else 0.0 for v in counts.values]})


def category_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Patients (rows) per category of `column`, with percentages."""
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame(columns=[column, "patients", "percent"])
    s = df[column].astype("object").where(df[column].notna(), "Unknown").astype(str)
    counts = s.value_counts().rename_axis(column).reset_index(name="patients")
    counts["percent"] = (counts["patients"] / counts["patients"].sum() * 100).round(1)
    return counts


def top_conditions(conditions: pd.DataFrame, n: Optional[int] = 10, by: str = "records") -> pd.DataFrame:
    """Condition frequency. `records` = condition records, `patients` = unique patients."""
    cols = ["description", "records", "patients", "percent_of_records"]
    if conditions is None or conditions.empty or "description" not in conditions:
        return pd.DataFrame(columns=cols)
    g = (conditions.groupby("description", observed=True)
         .agg(records=("patient_id", "size"), patients=("patient_id", "nunique")).reset_index())
    g["description"] = g["description"].astype(str)
    g["percent_of_records"] = (g["records"] / g["records"].sum() * 100).round(2)
    g = g.sort_values([by, "description"], ascending=[False, True]).reset_index(drop=True)
    return g.head(n) if n else g


# ----------------------------------------------------------------------------- time series
def allowed_granularities(dates: pd.Series) -> tuple[list[str], str]:
    """Granularities sensible for the date span, and the default."""
    d = dates.dropna() if dates is not None else pd.Series(dtype="datetime64[ns]")
    if d.empty:
        return ["Monthly"], "Monthly"
    span = (d.max() - d.min()).days
    options = ["Monthly"]
    if span <= 1100:
        options.insert(0, "Daily")
    if span >= 365:
        options.append("Yearly")
    return options, ("Daily" if span <= 62 else "Monthly")


def period_start(dates: pd.Series, grain: str) -> pd.Series:
    if grain == "Daily":
        return dates.dt.floor("D")
    if grain == "Monthly":
        return dates.dt.to_period("M").dt.to_timestamp()
    if grain == "Yearly":
        return dates.dt.to_period("Y").dt.to_timestamp()
    raise ValueError(f"Unknown granularity: {grain}")


def _full_index(keys: pd.Series, grain: str) -> pd.DatetimeIndex:
    return pd.date_range(keys.min(), keys.max(), freq=_FREQ[grain])


def _label(period: pd.Series, grain: str) -> pd.Series:
    return period.dt.strftime(_LABEL_FMT[grain])


def encounters_over_time(encounters: pd.DataFrame, grain: str = "Monthly") -> pd.DataFrame:
    """Encounter counts per period, empty periods included as zero. Missing dates are excluded."""
    empty = pd.DataFrame(columns=["period", "period_label", "encounters"])
    if encounters is None or encounters.empty or "start" not in encounters:
        return empty
    dates = encounters["start"].dropna()
    if dates.empty:
        return empty
    keys = period_start(dates, grain)
    full = _full_index(keys, grain)
    counts = keys.value_counts().sort_index()
    counts.index = pd.DatetimeIndex(counts.index).as_unit(full.unit) if hasattr(full, "unit") else counts.index
    counts = counts.reindex(full, fill_value=0).astype(int)
    out = counts.rename_axis("period").reset_index(name="encounters")
    out.insert(1, "period_label", _label(out["period"], grain))
    return out


def encounters_by_class_over_time(encounters: pd.DataFrame, grain: str = "Monthly") -> pd.DataFrame:
    empty = pd.DataFrame(columns=["period", "period_label", "encounter_class", "encounters"])
    if encounters is None or encounters.empty or not {"start", "encounter_class"} <= set(encounters.columns):
        return empty
    e = encounters.dropna(subset=["start"])
    if e.empty:
        return empty
    keys = period_start(e["start"], grain)
    table = (pd.DataFrame({"period": keys.values, "encounter_class": e["encounter_class"].astype(str).values})
             .groupby(["period", "encounter_class"]).size().unstack(fill_value=0))
    full = _full_index(keys, grain)
    table.index = pd.DatetimeIndex(table.index).as_unit(full.unit) if hasattr(full, "unit") else table.index
    table = table.reindex(full, fill_value=0)
    long = (table.rename_axis("period").reset_index()
            .melt(id_vars="period", var_name="encounter_class", value_name="encounters"))
    long.insert(1, "period_label", _label(long["period"], grain))
    return long


def encounter_class_distribution(encounters: pd.DataFrame) -> pd.DataFrame:
    if encounters is None or encounters.empty or "encounter_class" not in encounters:
        return pd.DataFrame(columns=["encounter_class", "encounters", "percent"])
    c = encounters["encounter_class"].astype(str).value_counts().rename_axis("encounter_class").reset_index(name="encounters")
    c["percent"] = (c["encounters"] / c["encounters"].sum() * 100).round(1)
    return c


def conditions_over_time(conditions: pd.DataFrame, descriptions: list, grain: str = "Monthly") -> pd.DataFrame:
    empty = pd.DataFrame(columns=["period", "period_label", "description", "records"])
    if conditions is None or conditions.empty or "start" not in conditions or not descriptions:
        return empty
    c = conditions[conditions["description"].isin(descriptions)].dropna(subset=["start"])
    if c.empty:
        return empty
    keys = period_start(c["start"], grain)
    table = (pd.DataFrame({"period": keys.values, "description": c["description"].astype(str).values})
             .groupby(["period", "description"]).size().unstack(fill_value=0))
    full = _full_index(keys, grain)
    table.index = pd.DatetimeIndex(table.index).as_unit(full.unit) if hasattr(full, "unit") else table.index
    table = table.reindex(full, fill_value=0)
    long = (table.rename_axis("period").reset_index()
            .melt(id_vars="period", var_name="description", value_name="records"))
    long.insert(1, "period_label", _label(long["period"], grain))
    return long


# ----------------------------------------------------------------------------- comparisons
def condition_by_group(conditions: pd.DataFrame, patients: pd.DataFrame, group_col: str,
                       descriptions: list) -> pd.DataFrame:
    """Condition records per demographic group for the chosen conditions.

    `records_per_100_patients` divides by the number of patients in that group in the current view,
    so groups of different size can be compared. It is a record frequency, not disease prevalence.
    """
    cols = ["description", group_col, "records", "patients", "group_size", "records_per_100_patients"]
    if conditions.empty or patients.empty or group_col not in patients or not descriptions:
        return pd.DataFrame(columns=cols)
    pg = patients[["patient_id", group_col]].dropna(subset=[group_col]).copy()
    pg[group_col] = pg[group_col].astype(str)
    sizes = pg[group_col].value_counts()
    m = conditions[conditions["description"].isin(descriptions)].merge(pg, on="patient_id", how="inner")
    if m.empty:
        return pd.DataFrame(columns=cols)
    m["description"] = m["description"].astype(str)
    g = (m.groupby(["description", group_col]).agg(records=("patient_id", "size"), patients=("patient_id", "nunique"))
         .reset_index())
    g["group_size"] = g[group_col].map(sizes).astype(int)
    g["records_per_100_patients"] = (g["records"] / g["group_size"] * 100).round(1)
    if group_col == "age_group":
        g[group_col] = pd.Categorical(g[group_col], categories=AGE_LABELS, ordered=True)
        g = g.sort_values(["description", group_col])
    return g.reset_index(drop=True)


def observation_options(obs: Optional[pd.DataFrame], limit: int = 50) -> list:
    if obs is None or obs.empty or "value_numeric" not in obs or "description" not in obs:
        return []
    s = obs.dropna(subset=["value_numeric"]).groupby("description").size().sort_values(ascending=False)
    return [str(i) for i in s.head(limit).index]


def observation_by_age_group(obs: Optional[pd.DataFrame], patients: pd.DataFrame, description: str) -> pd.DataFrame:
    cols = ["age_group", "n", "mean", "median", "units"]
    if obs is None or obs.empty or "value_numeric" not in obs:
        return pd.DataFrame(columns=cols)
    o = obs[(obs["description"] == description) & obs["value_numeric"].notna()]
    m = o.merge(patients[["patient_id", "age_group"]], on="patient_id", how="inner").dropna(subset=["age_group"])
    if m.empty:
        return pd.DataFrame(columns=cols)
    m["age_group"] = m["age_group"].astype(str)
    g = m.groupby("age_group")["value_numeric"].agg(n="size", mean="mean", median="median")
    g = g.reindex([a for a in AGE_LABELS if a in g.index]).reset_index()
    units = m["units"].dropna().mode() if "units" in m else pd.Series(dtype="string")
    g["units"] = str(units.iloc[0]) if len(units) else ""
    g[["mean", "median"]] = g[["mean", "median"]].round(2)
    return g


# ----------------------------------------------------------------------------- findings
def key_findings(fd: FilteredData) -> list[str]:
    """Plain-language descriptive findings computed from the filtered data."""
    out: list[str] = []
    m = summary_metrics(fd)
    if m["patients"]:
        out.append(f"The current view covers **{m['patients']:,}** synthetic patients, **{m['encounters']:,}** "
                   f"encounters and **{m['conditions']:,}** condition records.")
    top = top_conditions(fd.conditions, 1)
    if not top.empty:
        r = top.iloc[0]
        out.append(f"The most frequently recorded condition is **{r['description']}** — {int(r['records']):,} "
                   f"records across {int(r['patients']):,} patients ({r['percent_of_records']:.1f}% of condition records).")
    ag = age_group_counts(fd.patients)
    if ag["patients"].sum() > 0:
        r = ag.loc[ag["patients"].idxmax()]
        out.append(f"The largest age group is **{r['age_group']}** with {int(r['patients']):,} patients ({r['percent']:.1f}% of patients with a valid age).")
    cls = encounter_class_distribution(fd.encounters)
    if not cls.empty:
        r = cls.iloc[0]
        out.append(f"**{r['encounter_class']}** is the most common encounter class ({r['percent']:.1f}% of encounters).")
    monthly = encounters_over_time(fd.encounters, "Monthly")
    if not monthly.empty and monthly["encounters"].max() > 0:
        r = monthly.loc[monthly["encounters"].idxmax()]
        out.append(f"The busiest month in the dataset is **{r['period_label']}** with {int(r['encounters']):,} encounters.")
    if out:
        out.append("These are descriptive counts from synthetic data generated by simulation rules; they do not "
                   "represent real-world prevalence and show no causal relationship.")
    return out


# ----------------------------------------------------------------------------- patient explorer
def search_patient_ids(patients: pd.DataFrame, query: str = "", limit: int = 500) -> tuple[list, int]:
    """Case-insensitive 'contains' search on synthetic IDs. Returns (ids up to limit, total matches)."""
    ids = patients["patient_id"].astype(str)
    q = (query or "").strip().lower()
    if q:
        ids = ids[ids.str.lower().str.contains(q, regex=False)]
    ids = ids.sort_values()
    return ids.head(limit).tolist(), int(len(ids))


def patient_record(tables: dict, patient_id: str) -> dict:
    """All records for ONE patient only (strict equality on patient_id)."""
    def pick(name, sort_col=None):
        df = tables.get(name)
        if df is None:
            return None
        sub = df[df["patient_id"] == patient_id]
        if sort_col and sort_col in sub:
            sub = sub.sort_values(sort_col, ascending=False, na_position="last")
        return sub.reset_index(drop=True)

    prof = tables["patients"]
    row = prof[prof["patient_id"] == patient_id]
    profile = {}
    if len(row):
        r = row.iloc[0]
        profile = {"patient_id": patient_id,
                   "age": None if pd.isna(r.get("age")) else float(r["age"]),
                   "age_group": None if pd.isna(r.get("age_group")) else str(r["age_group"]),
                   "gender": r.get("gender"), "race": r.get("race"), "ethnicity": r.get("ethnicity"),
                   "status": None if "death_date" not in row else ("Deceased" if pd.notna(r["death_date"]) else "Living")}
    return {"profile": profile, "encounters": pick("encounters", "start"), "conditions": pick("conditions", "start"),
            "observations": pick("observations", "date"), "medications": pick("medications", "start")}
