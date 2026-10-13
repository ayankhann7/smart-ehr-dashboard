from src.utils import CONDITION_PRESETS, get_conditions_for_preset


def test_condition_presets_exist():
    assert "All Conditions" in CONDITION_PRESETS
    assert "🩺 Diabetes & Metabolic" in CONDITION_PRESETS
    assert "❤️ Hypertension & Cardiovascular" in CONDITION_PRESETS
    assert "🫁 Asthma & Respiratory" in CONDITION_PRESETS


def test_get_conditions_for_preset():
    conditions = [
        "Diabetes mellitus (disorder)",
        "Prediabetes",
        "Hypertension",
        "Asthma",
        "Viral sinusitis (disorder)",
        "Stress (finding)",
        "Closed fracture of hip",
    ]

    # All conditions returns empty preset match (meaning no filtering)
    assert get_conditions_for_preset("All Conditions", conditions) == []

    # Diabetes
    diab = get_conditions_for_preset("🩺 Diabetes & Metabolic", conditions)
    assert set(diab) == {"Diabetes mellitus (disorder)", "Prediabetes"}

    # Hypertension
    hyp = get_conditions_for_preset("❤️ Hypertension & Cardiovascular", conditions)
    assert hyp == ["Hypertension"]

    # Asthma
    asthma = get_conditions_for_preset("🫁 Asthma & Respiratory", conditions)
    assert set(asthma) == {"Asthma", "Viral sinusitis (disorder)"}

    # Nonexistent preset
    assert get_conditions_for_preset("Nonexistent", conditions) == []
