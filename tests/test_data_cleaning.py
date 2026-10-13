import pandas as pd
import pytest

from src import data_cleaning, data_loader, demo_data
from src.data_loader import DatasetError
from src.utils import normalise_column_name, normalise_columns, to_csv_bytes

from tests.fixtures import write_fixture_dataset


def load_clean(folder):
    return data_cleaning.clean_dataset(data_loader.load_tables(folder))


def test_column_name_normalisation():
    assert normalise_column_name("  Birth Date ") == "birth_date"
    assert normalise_column_name("ENCOUNTERCLASS") == "encounterclass"
    assert normalise_column_name("\ufeffId") == "id"
    df = normalise_columns(pd.DataFrame(columns=["PATIENT", "Start Date"]))
    assert list(df.columns) == ["patient", "start_date"]


def test_csv_loading_keeps_only_mapped_columns(tmp_path):
    write_fixture_dataset(tmp_path)
    load = data_loader.load_tables(tmp_path)
    assert set(load.tables) == {"patients", "encounters", "conditions", "observations", "medications"}
    # privacy: names/addresses are never loaded
    for forbidden in ("first", "last", "address", "FIRST", "LAST", "ADDRESS"):
        assert forbidden not in load.tables["patients"].columns
    assert len(load.tables["patients"]) == 6  # raw rows, before cleaning
    assert not load.is_demo


def test_missing_required_file_gives_helpful_error(tmp_path):
    write_fixture_dataset(tmp_path)
    (tmp_path / "conditions.csv").unlink()
    with pytest.raises(DatasetError) as exc:
        data_loader.load_tables(tmp_path)
    assert "conditions.csv" in str(exc.value)


def test_missing_dataset_folder_gives_helpful_error(tmp_path):
    with pytest.raises(DatasetError) as exc:
        data_loader.load_tables(tmp_path / "nothing_here")
    assert "patients.csv" in str(exc.value)


def test_missing_required_column_gives_helpful_error(tmp_path):
    write_fixture_dataset(tmp_path)
    (tmp_path / "encounters.csv").write_text("Id,START,DESCRIPTION\ne1,2020-01-01,x\n", encoding="utf-8")
    with pytest.raises(DatasetError) as exc:
        data_loader.load_tables(tmp_path)
    assert "patient_id" in str(exc.value) and "encounters.csv" in str(exc.value)


def test_missing_optional_files_are_tolerated(tmp_path):
    write_fixture_dataset(tmp_path, include_optional=False)
    load = data_loader.load_tables(tmp_path)
    assert "observations" not in load.tables and "medications" not in load.tables
    assert any("observations.csv" in w for w in load.warnings)
    cleaned = data_cleaning.clean_dataset(load)
    assert set(cleaned.tables) == {"patients", "encounters", "conditions"}
    assert (cleaned.quality.set_index("table").loc["observations", "status"]) == "not provided"


def test_alternative_headers_are_mapped(tmp_path):
    (tmp_path / "patients.csv").write_text("patient_id,dob,sex\na,1990-01-01,male\n", encoding="utf-8")
    (tmp_path / "encounters.csv").write_text("encounter_id,patient_id,encounter_date,class\ne1,a,2020-05-05,Emergency\n", encoding="utf-8")
    (tmp_path / "conditions.csv").write_text("patient,onset,condition\na,2020-05-05,Asthma\n", encoding="utf-8")
    cleaned = load_clean(tmp_path)
    assert list(cleaned.tables["patients"]["gender"]) == ["Male"]
    assert list(cleaned.tables["conditions"]["description"]) == ["Asthma"]
    assert list(cleaned.tables["encounters"]["encounter_class"]) == ["Emergency"]


def test_schema_overrides_allow_custom_headers(tmp_path):
    (tmp_path / "patients.csv").write_text("MRN,BIRTHDATE\nz1,1990-01-01\n", encoding="utf-8")
    (tmp_path / "encounters.csv").write_text("PATIENT,START\nz1,2020-05-05\n", encoding="utf-8")
    (tmp_path / "conditions.csv").write_text("PATIENT,DESCRIPTION\nz1,Asthma\n", encoding="utf-8")
    load = data_loader.load_tables(tmp_path, overrides={"patients": {"patient_id": ["mrn"]}})
    assert list(load.tables["patients"]["patient_id"]) == ["z1"]


def test_invalid_and_missing_dates():
    parsed, invalid = data_cleaning.parse_dates(pd.Series(["2020-01-05", "2020-01-05T10:00:00Z", "garbage", "", None, "  "]))
    assert parsed.notna().sum() == 2
    assert invalid == 1  # only "garbage"; blanks are missing, not invalid
    assert parsed.iloc[0] == pd.Timestamp("2020-01-05")


def test_duplicate_patient_ids_removed_and_logged(tmp_path):
    write_fixture_dataset(tmp_path)
    cleaned = load_clean(tmp_path)
    p = cleaned.tables["patients"]
    assert len(p) == 5 and p["patient_id"].is_unique
    row = cleaned.quality.set_index("table").loc["patients"]
    assert row["rows_original"] == 6 and row["rows_after_cleaning"] == 5 and row["duplicates_removed"] == 1
    assert any("duplicate patient ID" in line for line in cleaned.cleaning_log)


def test_age_calculation_from_dataset(tmp_path):
    write_fixture_dataset(tmp_path)
    cleaned = load_clean(tmp_path)
    assert cleaned.reference_date.date() == pd.Timestamp("2021-01-01").date()
    ages = cleaned.tables["patients"].set_index("patient_id")["age"]
    assert ages["p1"] == 40      # born 1980-05-15, birthday not yet reached on 2021-01-01
    assert ages["p2"] == 10
    assert ages["p3"] == 69      # deceased 2020-06-01: age at death
    assert pd.isna(ages["p4"]) and pd.isna(ages["p5"])  # invalid / missing birth date excluded, not invented


def test_compute_age_edge_cases():
    births = pd.Series(pd.to_datetime(["2000-02-29", "2000-06-15", "2090-01-01", None, "1850-01-01"]))
    ages = data_cleaning.compute_age(births, pd.Timestamp("2020-06-14"))
    assert ages.iloc[0] == 20 and ages.iloc[1] == 19
    assert ages.iloc[2:].isna().all()  # future birth, missing birth, implausible (>120) age


def test_unmatched_patient_ids_removed_and_counted(tmp_path):
    write_fixture_dataset(tmp_path)
    cleaned = load_clean(tmp_path)
    q = cleaned.quality.set_index("table")
    assert q.loc["encounters", "unmatched_patient_refs_removed"] == 1
    assert q.loc["conditions", "unmatched_patient_refs_removed"] == 1
    assert q.loc["conditions", "unmatched_encounter_refs"] == 1
    assert "ghost" not in set(cleaned.tables["encounters"]["patient_id"])
    assert q.loc["encounters", "invalid_dates"] == 1


def test_empty_datasets_do_not_crash(tmp_path):
    (tmp_path / "patients.csv").write_text("Id,BIRTHDATE,GENDER\n", encoding="utf-8")
    (tmp_path / "encounters.csv").write_text("Id,PATIENT,START\n", encoding="utf-8")
    (tmp_path / "conditions.csv").write_text("PATIENT,DESCRIPTION\n", encoding="utf-8")
    cleaned = load_clean(tmp_path)
    assert all(len(t) == 0 for t in cleaned.tables.values())
    assert cleaned.date_range == (None, None)
    assert not data_cleaning.quality_report_frame(cleaned).empty


def test_export_generation(tmp_path):
    write_fixture_dataset(tmp_path)
    cleaned = load_clean(tmp_path)
    report = data_cleaning.quality_report_frame(cleaned)
    assert list(report.columns) == ["section", "table", "metric", "value"]
    assert {"dataset", "table_summary", "missing_values", "cleaning_log"} <= set(report["section"])
    raw = to_csv_bytes(report).decode("utf-8")
    assert raw.splitlines()[0] == "section,table,metric,value"
    assert "p1" not in raw and "Smith" not in raw  # aggregate counts only, no row-level data


def test_demo_dataset_is_labelled_and_loads(tmp_path):
    demo_data.generate_demo_dataset(tmp_path, n_patients=40, seed=1)
    load = data_loader.load_tables(tmp_path)
    assert load.is_demo
    assert (tmp_path / "DEMO_DATASET.txt").exists()
    cleaned = data_cleaning.clean_dataset(load)
    assert cleaned.is_demo and len(cleaned.tables["patients"]) == 40
    assert data_loader.find_dataset_dir(tmp_path.parent / "no_such") is None


def test_demo_subfolder_is_never_auto_selected(tmp_path):
    demo_data.generate_demo_dataset(tmp_path / "demo", n_patients=10, seed=1)
    assert data_loader.find_dataset_dir(tmp_path) is None
    assert data_loader.find_dataset_dir(tmp_path / "demo") is not None
