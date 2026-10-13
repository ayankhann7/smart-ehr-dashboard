"""Locate, read and schema-map Synthea CSV files. No Streamlit or Plotly imports here.

Only the columns listed in SCHEMA are ever read from disk, so names, addresses and other
direct identifiers present in a Synthea export are never loaded into the application.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .utils import normalise_column_name

logger = logging.getLogger(__name__)

DEMO_MARKER = "DEMO_DATASET.txt"
TABLE_FILES = {
    "patients": "patients.csv",
    "encounters": "encounters.csv",
    "conditions": "conditions.csv",
    "observations": "observations.csv",
    "medications": "medications.csv",
}
REQUIRED_TABLES = ("patients", "encounters", "conditions")
OPTIONAL_TABLES = ("observations", "medications")

# Schema-mapping layer: canonical name -> accepted (normalised) source headers, in priority order.
# Extend or override via the `overrides` argument of load_tables() for other CSV layouts.
SCHEMA: dict[str, dict[str, list[str]]] = {
    "patients": {
        "patient_id": ["id", "patient_id", "patient", "patientid", "uuid"],
        "birth_date": ["birthdate", "birth_date", "dob", "date_of_birth"],
        "death_date": ["deathdate", "death_date", "date_of_death"],
        "gender": ["gender", "sex"],
        "race": ["race"],
        "ethnicity": ["ethnicity"],
    },
    "encounters": {
        "encounter_id": ["id", "encounter_id", "encounterid"],
        "patient_id": ["patient", "patient_id", "patientid"],
        "start": ["start", "start_date", "startdate", "encounter_date", "date"],
        "stop": ["stop", "stop_date", "stopdate", "end", "end_date"],
        "encounter_class": ["encounterclass", "encounter_class", "class", "encounter_type"],
        "description": ["description"],
    },
    "conditions": {
        "patient_id": ["patient", "patient_id", "patientid"],
        "encounter_id": ["encounter", "encounter_id", "encounterid"],
        "start": ["start", "start_date", "startdate", "onset", "date"],
        "stop": ["stop", "stop_date", "stopdate", "end"],
        "code": ["code", "condition_code"],
        "description": ["description", "condition", "condition_description"],
    },
    "observations": {
        "patient_id": ["patient", "patient_id", "patientid"],
        "encounter_id": ["encounter", "encounter_id", "encounterid"],
        "date": ["date", "start", "observation_date"],
        "code": ["code"],
        "description": ["description"],
        "value": ["value"],
        "units": ["units", "unit"],
        "type": ["type"],
    },
    "medications": {
        "patient_id": ["patient", "patient_id", "patientid"],
        "encounter_id": ["encounter", "encounter_id", "encounterid"],
        "start": ["start", "start_date", "startdate", "date"],
        "stop": ["stop", "stop_date", "stopdate", "end"],
        "code": ["code"],
        "description": ["description"],
    },
}
REQUIRED_COLUMNS = {
    "patients": ["patient_id"],
    "encounters": ["patient_id", "start"],
    "conditions": ["patient_id"],
    "observations": ["patient_id"],
    "medications": ["patient_id"],
}
# At least one of these must be present.
REQUIRED_ANY = {
    "conditions": ["description", "code"],
    "observations": ["description", "code"],
    "medications": ["description", "code"],
}


class DatasetError(Exception):
    """Raised with a user-friendly message when the dataset cannot be used."""


@dataclass
class LoadResult:
    tables: dict[str, pd.DataFrame]
    file_info: list[dict]
    warnings: list[str] = field(default_factory=list)
    source_dir: str = ""
    is_demo: bool = False


def _find_file(folder: Path, filename: str) -> Path | None:
    if not folder.is_dir():
        return None
    for path in folder.iterdir():
        if path.is_file() and path.name.lower() == filename.lower():
            return path
    return None


def find_dataset_dir(base) -> Path | None:
    """Return the folder holding patients.csv: `base` itself or an immediate sub-folder (e.g. csv/).

    A sub-folder named 'demo' is never auto-selected so demo data cannot be mistaken for real data.
    """
    base = Path(base)
    if _find_file(base, TABLE_FILES["patients"]):
        return base
    if base.is_dir():
        subs = sorted(p for p in base.iterdir() if p.is_dir() and p.name.lower() != "demo"
                      and not p.name.startswith("."))
        for sub in subs:
            if _find_file(sub, TABLE_FILES["patients"]):
                return sub
    return None


def is_demo_dataset(folder) -> bool:
    return _find_file(Path(folder), DEMO_MARKER) is not None


def dataset_signature(folder) -> tuple:
    """Cheap fingerprint (name, size, mtime) of the CSV files; used to invalidate the cache."""
    folder = Path(folder)
    sig = []
    for fname in TABLE_FILES.values():
        path = _find_file(folder, fname)
        if path is not None:
            stat = path.stat()
            sig.append((path.name, stat.st_size, stat.st_mtime_ns))
    return tuple(sig)


def resolve_columns(normalised_columns, table: str, overrides: dict | None = None) -> dict[str, str]:
    """Map canonical column names to the (normalised) source headers actually present."""
    cols = set(normalised_columns)
    schema = {k: list(v) for k, v in SCHEMA[table].items()}
    for canon, aliases in (overrides or {}).get(table, {}).items():
        schema[canon] = [normalise_column_name(a) for a in aliases] + schema.get(canon, [])
    mapping: dict[str, str] = {}
    for canon, aliases in schema.items():
        for alias in aliases:
            if alias in cols:
                mapping[canon] = alias
                break
    return mapping


def _check_required(table: str, mapping: dict[str, str]) -> list[str]:
    problems = [c for c in REQUIRED_COLUMNS.get(table, []) if c not in mapping]
    msgs = []
    for canon in problems:
        accepted = ", ".join(SCHEMA[table][canon][:4])
        msgs.append(f"'{canon}' (accepted headers: {accepted})")
    any_of = REQUIRED_ANY.get(table)
    if any_of and not any(c in mapping for c in any_of):
        msgs.append("one of " + " / ".join(f"'{c}'" for c in any_of))
    return msgs


def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""],
                               encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise DatasetError(f"{path.name} could not be read as a CSV file ({exc}).") from exc
    raise DatasetError(f"{path.name} could not be decoded (tried UTF-8 and Latin-1).")


def load_tables(data_dir, overrides: dict | None = None) -> LoadResult:
    """Read every available file, keeping only mapped columns, renamed to canonical names."""
    folder = find_dataset_dir(data_dir)
    expected = ", ".join(TABLE_FILES[t] for t in REQUIRED_TABLES)
    if folder is None:
        raise DatasetError(
            f"No dataset found in '{data_dir}'. Place the Synthea CSV files ({expected}) in that "
            "folder (or in a 'csv' sub-folder).")
    missing_files = [TABLE_FILES[t] for t in REQUIRED_TABLES if _find_file(folder, TABLE_FILES[t]) is None]
    if missing_files:
        raise DatasetError(f"Required file(s) missing in '{folder}': {', '.join(missing_files)}.")

    tables: dict[str, pd.DataFrame] = {}
    info: list[dict] = []
    warnings: list[str] = []
    for table, fname in TABLE_FILES.items():
        path = _find_file(folder, fname)
        if path is None:
            warnings.append(f"Optional file {fname} not found; related features are disabled.")
            continue
        raw_cols = list(_read_csv(path, nrows=0).columns)
        norm_of = {c: normalise_column_name(c) for c in raw_cols}
        orig_of = {v: k for k, v in norm_of.items()}
        mapping = resolve_columns(norm_of.values(), table, overrides)
        problems = _check_required(table, mapping)
        if problems:
            if table in REQUIRED_TABLES:
                raise DatasetError(f"{fname} is missing required column(s): {'; '.join(problems)}. "
                                   f"Columns found: {', '.join(raw_cols) or 'none'}.")
            warnings.append(f"{fname} skipped: missing {'; '.join(problems)}.")
            continue
        df = _read_csv(path, usecols=[orig_of[n] for n in mapping.values()])
        df = df.rename(columns={orig_of[n]: canon for canon, n in mapping.items()})[list(mapping)]
        tables[table] = df
        info.append({
            "table": table, "file": path.name, "original_rows": len(df),
            "original_columns": len(raw_cols), "columns_used": len(mapping),
            "mapped_columns": "; ".join(f"{canon} <- {orig_of[n]}" for canon, n in mapping.items()),
        })
        logger.info("Loaded %s: %d rows, %d/%d columns used", fname, len(df), len(mapping), len(raw_cols))
    return LoadResult(tables, info, warnings, str(folder), is_demo_dataset(folder))
