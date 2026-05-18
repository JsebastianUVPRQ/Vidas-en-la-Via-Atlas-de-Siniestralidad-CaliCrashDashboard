import pandas as pd

from src.etl import assign_time_band, normalize_accident_data


def test_assign_time_band_from_hour_string() -> None:
    assert assign_time_band("02:15") == "madrugada"
    assert assign_time_band("08:00") == "mañana"
    assert assign_time_band("15:30") == "tarde"
    assert assign_time_band("21") == "noche"
    assert assign_time_band("21:45") == "noche"


def test_normalize_accident_data_adds_derived_columns() -> None:
    raw = pd.DataFrame(
        [
            {
                "Fecha Accidente": "2025-02-01",
                "Hora Accidente": "07:10",
                "lat": "3.45",
                "lng": "-76.53",
                "comuna": "2",
                "barrio": "Granada",
                "tipo": "Choque",
                "severidad": "Solo daños",
            }
        ]
    )

    result = normalize_accident_data(raw)

    assert len(result) == 1
    assert result.loc[0, "franja_horaria"] == "mañana"
    assert result.loc[0, "mes"] == "2025-02"
    assert result.loc[0, "interseccion"] == "Sin dato"


def test_normalize_accident_data_filters_outside_cali_coordinates() -> None:
    raw = pd.DataFrame(
        [
            {
                "fecha": "2025-02-01",
                "hora": "07:10",
                "latitud": 4.80,
                "longitud": -74.05,
                "comuna": "Bogotá",
            }
        ]
    )

    result = normalize_accident_data(raw)

    assert result.empty
