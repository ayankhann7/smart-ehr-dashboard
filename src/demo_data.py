"""Generator for a small, clearly labelled DEMO dataset in Synthea's CSV layout.

This is NOT Synthea output and NOT real data. All values are random draws made only so the
application can be exercised (smoke tests, screenshots) when the real dataset is not installed.
A DEMO_DATASET.txt marker file is written so the app always labels the data as demo data.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from .data_loader import DEMO_MARKER

CONDITIONS = ["Hypertension", "Acute viral pharyngitis", "Hyperlipidemia", "Prediabetes", "Acute bronchitis",
              "Type 2 diabetes mellitus", "Chronic sinusitis", "Obesity", "Anemia", "Osteoarthritis", "Asthma",
              "Otitis media", "Seasonal allergic rhinitis", "Major depressive disorder", "Anxiety disorder",
              "Low back pain", "Gastroesophageal reflux disease", "Migraine", "Chronic kidney disease",
              "Coronary heart disease", "Sprain of ankle", "Streptococcal sore throat", "Chronic pain",
              "Sleep apnea"]
MEDICATIONS = ["Lisinopril 10 MG Oral Tablet", "Metformin 500 MG Oral Tablet", "Atorvastatin 20 MG Oral Tablet",
               "Amoxicillin 500 MG Oral Capsule", "Ibuprofen 200 MG Oral Tablet", "Albuterol 0.09 MG/ACTUAT Inhaler",
               "Sertraline 50 MG Oral Tablet", "Omeprazole 20 MG Oral Capsule"]
CLASSES = ["ambulatory", "wellness", "outpatient", "emergency", "inpatient", "urgentcare"]
CLASS_P = [0.40, 0.20, 0.15, 0.10, 0.05, 0.10]
OBS = [("DEMO-O1", "Body Height", "cm", 165, 12), ("DEMO-O2", "Body Weight", "kg", 72, 15),
       ("DEMO-O3", "Body Mass Index", "kg/m2", 26.5, 4), ("DEMO-O4", "Systolic Blood Pressure", "mm[Hg]", 122, 14),
       ("DEMO-O5", "Diastolic Blood Pressure", "mm[Hg]", 78, 9)]


def generate_demo_dataset(out_dir, n_patients: int = 300, seed: int = 42) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    def ids(n):
        return [str(uuid.UUID(bytes=rng.bytes(16), version=4)) for _ in range(n)]

    n = n_patients
    pid = np.array(ids(n))
    day0 = np.datetime64("1930-01-01")
    birth = day0 + rng.integers(0, int((np.datetime64("2020-12-31") - day0).astype(int)), n).astype("timedelta64[D]")
    older = birth < np.datetime64("1950-01-01")
    d_start = np.datetime64("2016-01-01")
    death = np.where(older & (rng.random(n) < 0.25),
                     d_start + rng.integers(0, 3500, n).astype("timedelta64[D]"), np.datetime64("NaT"))
    gender = rng.choice(["M", "F"], n, p=[0.49, 0.51])
    pd.DataFrame({
        "Id": pid, "BIRTHDATE": pd.Series(birth).dt.strftime("%Y-%m-%d"),
        "DEATHDATE": pd.Series(death).dt.strftime("%Y-%m-%d"),
        "FIRST": [f"DemoFirst{i}" for i in range(n)], "LAST": [f"DemoLast{i}" for i in range(n)],
        "RACE": rng.choice(["white", "black", "asian", "native", "other"], n, p=[.62, .15, .12, .03, .08]),
        "ETHNICITY": rng.choice(["nonhispanic", "hispanic"], n, p=[.8, .2]), "GENDER": gender,
        "ADDRESS": "1 Demo Street"}).to_csv(out / "patients.csv", index=False)

    counts = 1 + rng.poisson(6, n)
    idx = np.repeat(np.arange(n), counts)
    m = len(idx)
    lower = np.maximum(birth, np.datetime64("2015-01-01"))
    upper = np.where(np.isnat(death), np.datetime64("2025-12-31"), death)
    span = (upper - lower).astype(int)
    start = (lower[idx].astype("datetime64[s]") + (rng.random(m) * span[idx]).astype(int).astype("timedelta64[D]")
             + rng.integers(0, 86400, m).astype("timedelta64[s]"))
    eid = np.array(ids(m))
    eclass = rng.choice(CLASSES, m, p=CLASS_P)
    enc = pd.DataFrame({"Id": eid, "START": pd.Series(start).dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "STOP": "",
                        "PATIENT": pid[idx], "ENCOUNTERCLASS": eclass,
                        "DESCRIPTION": [f"Demo {c} encounter" for c in eclass]})
    enc.to_csv(out / "encounters.csv", index=False)

    weights = 1 / np.arange(1, len(CONDITIONS) + 1)
    weights /= weights.sum()
    ci = rng.integers(0, m, int(m * 0.9))
    cdx = rng.choice(len(CONDITIONS), len(ci), p=weights)
    pd.DataFrame({"START": enc["START"].str[:10].values[ci], "STOP": "", "PATIENT": enc["PATIENT"].values[ci],
                  "ENCOUNTER": eid[ci], "CODE": [f"DEMO-C{k + 1:02d}" for k in cdx],
                  "DESCRIPTION": np.array(CONDITIONS)[cdx]}).to_csv(out / "conditions.csv", index=False)

    oi = rng.integers(0, m, int(m * 0.5))
    frames = []
    for code, desc, unit, mu, sd in OBS:
        vals = np.clip(rng.normal(mu, sd, len(oi)), mu - 3 * sd, mu + 3 * sd).round(1)
        frames.append(pd.DataFrame({"DATE": enc["START"].values[oi], "PATIENT": enc["PATIENT"].values[oi],
                                    "ENCOUNTER": eid[oi], "CODE": code, "DESCRIPTION": desc, "VALUE": vals,
                                    "UNITS": unit, "TYPE": "numeric"}))
    pd.concat(frames, ignore_index=True).to_csv(out / "observations.csv", index=False)

    mi = rng.integers(0, m, int(m * 0.35))
    mdx = rng.integers(0, len(MEDICATIONS), len(mi))
    pd.DataFrame({"START": enc["START"].str[:10].values[mi], "STOP": "", "PATIENT": enc["PATIENT"].values[mi],
                  "ENCOUNTER": eid[mi], "CODE": [f"DEMO-M{k + 1:02d}" for k in mdx],
                  "DESCRIPTION": np.array(MEDICATIONS)[mdx]}).to_csv(out / "medications.csv", index=False)

    (out / DEMO_MARKER).write_text(
        "DEMO DATASET - randomly generated by src/demo_data.py.\n"
        "This is NOT Synthea output and NOT real data. Do not draw conclusions from it.\n"
        "Download the real Synthea CSV export for your analysis (see README.md).\n", encoding="utf-8")
    return out
