import pandas as pd

from src.modelo import estimate_frequency


def test_estimate_frequency_by_comuna_and_time_band() -> None:
    accidents = pd.DataFrame(
        {
            "fecha": pd.to_datetime(
                ["2025-01-01", "2025-01-01", "2025-01-01", "2025-01-02"]
            ),
            "comuna": ["2", "2", "2", "17"],
            "franja_horaria": ["mañana", "mañana", "mañana", "noche"],
        }
    )

    result = estimate_frequency(accidents)
    result = result.set_index(["comuna", "franja_horaria"])

    assert result.loc[("2", "mañana"), "accidentes_observados"] == 3
    assert result.loc[("2", "mañana"), "dias_observados"] == 1
    assert result.loc[("2", "mañana"), "frecuencia_diaria_esperada"] == 3
    assert result.loc[("2", "mañana"), "nivel_riesgo"] == "alto"
    assert result.loc[("2", "mañana"), "intervalo_inferior"] >= 0
    assert (
        result.loc[("2", "mañana"), "intervalo_superior"]
        > result.loc[("2", "mañana"), "frecuencia_diaria_esperada"]
    )


def test_estimate_frequency_per_group_days() -> None:
    accidents = pd.DataFrame(
        {
            "fecha": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-01",
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                ]
            ),
            "comuna": ["2", "2", "2", "17", "17"],
            "franja_horaria": ["mañana", "mañana", "noche", "noche", "noche"],
        }
    )

    result = estimate_frequency(accidents)

    row = result.set_index(["comuna", "franja_horaria"])
    assert row.loc[("2", "mañana"), "dias_observados"] == 1
    assert row.loc[("2", "noche"), "dias_observados"] == 1
    assert row.loc[("17", "noche"), "dias_observados"] == 2


def test_estimate_frequency_handles_empty_data() -> None:
    result = estimate_frequency(pd.DataFrame())

    assert result.empty
    assert "frecuencia_diaria_esperada" in result.columns
    assert "intervalo_inferior" in result.columns
