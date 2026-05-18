import pandas as pd

from src.modelo import estimate_frequency


def test_estimate_frequency_by_comuna_and_time_band() -> None:
    accidents = pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02"]),
            "comuna": ["2", "2", "17"],
            "franja_horaria": ["mañana", "mañana", "noche"],
        }
    )

    result = estimate_frequency(accidents)

    first = result.iloc[0]
    assert first["comuna"] == "2"
    assert first["franja_horaria"] == "mañana"
    assert first["accidentes_observados"] == 2
    assert first["dias_observados"] == 2
    assert first["frecuencia_diaria_esperada"] == 1
    assert first["nivel_riesgo"] == "alto"


def test_estimate_frequency_handles_empty_data() -> None:
    result = estimate_frequency(pd.DataFrame())

    assert result.empty
    assert "frecuencia_diaria_esperada" in result.columns
