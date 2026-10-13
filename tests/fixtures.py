"""Small hand-written synthetic CSV fixtures (deliberately dirty) used by the tests."""
from __future__ import annotations

from pathlib import Path

PATIENTS = """Id,BIRTHDATE,DEATHDATE,FIRST,LAST,RACE,ETHNICITY,GENDER,ADDRESS
p1,1980-05-15,,Ann,Smith,white,nonhispanic,F,1 Main St
p2,2010-03-01,,Bob,Jones,black,nonhispanic,M,2 Main St
p3,1950-12-31,2020-06-01,Cy,Lee,asian,nonhispanic,male,3 Main St
p4,not-a-date,,Di,Ray,white,hispanic,F,4 Main St
p5,,,Ed,Fox,white,nonhispanic,,5 Main St
p1,1980-05-15,,Ann,Smith,white,nonhispanic,F,1 Main St
"""
ENCOUNTERS = """Id,START,STOP,PATIENT,ENCOUNTERCLASS,DESCRIPTION
e1,2020-01-10T09:00:00Z,2020-01-10T09:30:00Z,p1,ambulatory,Check up
e2,2020-01-20T10:00:00Z,,p1,Emergency,ER visit
e3,2020-02-05T08:00:00Z,,p2,ambulatory,Check up
e4,2020-02-15T08:00:00Z,,p3,inpatient,Admission
e5,bad-date,,p2,ambulatory,Check up
e6,2020-03-01T08:00:00Z,,ghost,ambulatory,Orphan
e3,2020-02-05T08:00:00Z,,p2,ambulatory,Check up
e7,2021-01-01T08:00:00Z,,p1,wellness,Wellness
"""
CONDITIONS = """START,STOP,PATIENT,ENCOUNTER,CODE,DESCRIPTION
2020-01-10,,p1,e1,C1,Hypertension
2020-01-20,,p1,e2,C2,Asthma
2020-02-05,,p2,e3,C2,Asthma
2020-02-15,,p3,e4,C1,Hypertension
2020-02-15,,p3,e4,C1,Hypertension
2020-03-01,,ghost,e6,C3,Diabetes
2021-01-01,,p1,e99,C1,Hypertension
"""
OBSERVATIONS = """DATE,PATIENT,ENCOUNTER,CODE,DESCRIPTION,VALUE,UNITS,TYPE
2020-01-10T09:00:00Z,p1,e1,O1,Body Mass Index,27.5,kg/m2,numeric
2020-01-10T09:00:00Z,p1,e1,O2,Smoking status,Never smoker,,text
2020-02-05T08:00:00Z,p2,e3,O1,Body Mass Index,19.0,kg/m2,numeric
"""
MEDICATIONS = """START,STOP,PATIENT,ENCOUNTER,CODE,DESCRIPTION
2020-01-10,,p1,e1,M1,Lisinopril 10 MG
"""


def write_fixture_dataset(folder, include_optional: bool = True) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    files = {"patients.csv": PATIENTS, "encounters.csv": ENCOUNTERS, "conditions.csv": CONDITIONS}
    if include_optional:
        files.update({"observations.csv": OBSERVATIONS, "medications.csv": MEDICATIONS})
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder
