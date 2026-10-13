import pandas as pd
import pytest

from src import analytics as A
from src import data_cleaning, data_loader

from tests.fixtures import write_fixture_dataset


def make(tmp_path):
    write_fixture_dataset(tmp_path)
    return data_cleaning.clean_dataset(data_loader.load_tables(tmp_path))


def view(cleaned, **kw):
    return A.apply_filters(cleaned.tables, A.FilterState(**kw))


def test_summary_metrics_are_derived_from_data(tmp_path):
    c = make(tmp_path)
    m = A.summary_metrics(view(c))
    assert (m["patients"], m["encounters"], m["conditions"], m["distinct_conditions"]) == (5, 6, 5, 2)
    assert m["age_n"] == 3 and m["age_excluded"] == 2
    assert m["avg_age"] == pytest.approx((40 + 10 + 69) / 3)
    # changing the data changes the metrics (nothing hard-coded)
    c.tables["encounters"] = c.tables["encounters"].iloc[:2]
    assert A.summary_metrics(view(c))["encounters"] == 2


def test_empty_dataset_metrics():
    empty = {"patients": pd.DataFrame(columns=["patient_id", "age", "age_group"]),
             "encounters": pd.DataFrame(columns=["patient_id", "start"]),
             "conditions": pd.DataFrame(columns=["patient_id", "description"])}
    m = A.summary_metrics(A.apply_filters(empty, A.FilterState()))
    assert m["patients"] == 0 and m["avg_age"] is None and m["encounters_per_patient"] is None
    assert A.top_conditions(empty["conditions"]).empty
    assert A.encounters_over_time(empty["encounters"]).empty
    assert A.age_group_counts(empty["patients"])["patients"].sum() == 0


def test_diagnosis_counts(tmp_path):
    c = make(tmp_path)
    top = A.top_conditions(view(c).conditions).set_index("description")
    assert top.loc["Hypertension", "records"] == 3 and top.loc["Hypertension", "patients"] == 2
    assert top.loc["Asthma", "records"] == 2 and top.loc["Asthma", "patients"] == 2
    assert list(A.top_conditions(view(c).conditions, 1)["description"]) == ["Hypertension"]
    by_patients = A.top_conditions(view(c).conditions, 5, by="patients")
    assert set(by_patients["description"]) == {"Hypertension", "Asthma"}


def test_monthly_encounter_aggregation_fills_empty_months(tmp_path):
    c = make(tmp_path)
    monthly = A.encounters_over_time(view(c).encounters, "Monthly")
    assert len(monthly) == 13                        # Jan 2020 .. Jan 2021, no gaps
    assert monthly["encounters"].sum() == 5          # the encounter with an invalid date is excluded
    by_label = monthly.set_index("period_label")["encounters"]
    assert by_label["2020-01"] == 2 and by_label["2020-02"] == 2 and by_label["2020-03"] == 0 and by_label["2021-01"] == 1
    assert A.encounters_over_time(view(c).encounters, "Yearly").set_index("period_label")["encounters"].to_dict() == {"2020": 4, "2021": 1}
    assert A.encounters_over_time(view(c).encounters, "Daily")["encounters"].sum() == 5


def test_encounter_class_over_time_and_distribution(tmp_path):
    c = make(tmp_path)
    fd = view(c)
    long = A.encounters_by_class_over_time(fd.encounters, "Monthly")
    assert long["encounters"].sum() == 5
    dist = A.encounter_class_distribution(fd.encounters).set_index("encounter_class")["encounters"]
    assert dist["Ambulatory"] == 3 and dist["Emergency"] == 1


def test_date_filter_flows_through_patient_and_encounter_links(tmp_path):
    c = make(tmp_path)
    fd = view(c, start_date=pd.Timestamp("2020-02-01"), end_date=pd.Timestamp("2020-02-29"))
    assert set(fd.patients["patient_id"]) == {"p2", "p3"}
    assert set(fd.encounters["encounter_id"]) == {"e3", "e4"}
    assert set(fd.conditions["patient_id"]) == {"p2", "p3"}
    assert set(fd.observations["patient_id"]) == {"p2"}
    assert fd.medications.empty


def test_encounter_class_filter_limits_linked_conditions(tmp_path):
    c = make(tmp_path)
    fd = view(c, encounter_classes=("Emergency",))
    assert list(fd.encounters["encounter_id"]) == ["e2"]
    assert list(fd.conditions["description"]) == ["Asthma"]
    assert list(fd.patients["patient_id"]) == ["p1"]


def test_condition_filter_keeps_patients_with_condition(tmp_path):
    c = make(tmp_path)
    fd = view(c, conditions=("Asthma",))
    assert set(fd.patients["patient_id"]) == {"p1", "p2"}
    assert set(fd.conditions["description"]) == {"Asthma"} and len(fd.conditions) == 2
    assert set(fd.encounters["patient_id"]) == {"p1", "p2"}
    none = view(c, conditions=("Nonexistent condition",))
    assert none.patients.empty and none.encounters.empty and none.conditions.empty


def test_demographic_filters(tmp_path):
    c = make(tmp_path)
    fd = view(c, genders=("Male",), age_range=(0, 20))
    assert list(fd.patients["patient_id"]) == ["p2"]
    assert set(fd.encounters["patient_id"]) == {"p2"}
    assert view(c, genders=()).patients.empty        # nothing selected -> nothing matches


def test_age_groups_and_excluded_counts(tmp_path):
    c = make(tmp_path)
    groups = A.age_group_counts(view(c).patients).set_index("age_group")["patients"]
    assert groups["0–17"] == 1 and groups["35–49"] == 1 and groups["65–79"] == 1 and groups.sum() == 3
    assert A.age_summary(view(c).patients)["excluded"] == 2


def test_patient_record_only_contains_selected_patient(tmp_path):
    c = make(tmp_path)
    rec = A.patient_record(c.tables, "p1")
    assert rec["profile"]["gender"] == "Female" and rec["profile"]["status"] == "Living"
    for name in ("encounters", "conditions", "observations", "medications"):
        assert set(rec[name]["patient_id"]) == {"p1"}
    assert len(rec["encounters"]) == 3
    empty = A.patient_record(c.tables, "p5")
    assert empty["encounters"].empty and empty["conditions"].empty
    assert A.patient_record(c.tables, "does-not-exist")["profile"] == {}


def test_patient_search():
    pats = pd.DataFrame({"patient_id": ["abc-1", "abd-2", "xyz-3"]})
    ids, total = A.search_patient_ids(pats, "AB")
    assert ids == ["abc-1", "abd-2"] and total == 2
    assert A.search_patient_ids(pats, "")[1] == 3
    assert A.search_patient_ids(pats, "zzz") == ([], 0)
    assert len(A.search_patient_ids(pats, "", limit=1)[0]) == 1


def test_condition_comparison_and_observation_summary(tmp_path):
    c = make(tmp_path)
    fd = view(c)
    cmp = A.condition_by_group(fd.conditions, fd.patients, "gender", ["Hypertension"]).set_index("gender")
    assert cmp.loc["Female", "records"] == 2 and cmp.loc["Female", "group_size"] == 2
    assert cmp.loc["Female", "records_per_100_patients"] == 100.0
    assert A.observation_options(fd.observations) == ["Body Mass Index"]
    obs = A.observation_by_age_group(fd.observations, fd.patients, "Body Mass Index").set_index("age_group")
    assert obs.loc["35–49", "mean"] == 27.5 and obs.loc["0–17", "n"] == 1


def test_granularity_options():
    short = pd.Series(pd.to_datetime(["2020-01-01", "2020-01-20"]))
    long_ = pd.Series(pd.to_datetime(["2000-01-01", "2020-01-20"]))
    assert A.allowed_granularities(short) == (["Daily", "Monthly"], "Daily")
    opts, default = A.allowed_granularities(long_)
    assert opts == ["Monthly", "Yearly"] and default == "Monthly"   # daily hidden for long spans
    assert A.allowed_granularities(pd.Series(dtype="datetime64[ns]")) == (["Monthly"], "Monthly")


def test_key_findings_come_from_data(tmp_path):
    c = make(tmp_path)
    text = " ".join(A.key_findings(view(c)))
    assert "Hypertension" in text and "5" in text
    assert A.key_findings(view(c, conditions=("Nonexistent",))) == []


def test_chart_builders_return_figures_from_inputs(tmp_path):
    pytest.importorskip("plotly")
    from src import charts
    c = make(tmp_path)
    fd = view(c)
    fig = charts.horizontal_bar(A.top_conditions(fd.conditions), "description", "records", "t", "x")
    assert sorted(fig.data[0].x) == [2, 3]
    assert charts.time_series(A.encounters_over_time(fd.encounters), "encounters", "t", "y").data[0].y is not None
    assert len(charts.empty_figure("t").layout.annotations) == 1
