import pandas as pd

from src.metrics import (
    aggregate_by_hour,
    aggregate_by_comuna,
    aggregate_by_weekday,
    build_kpis,
    filter_accidents,
)


def _sample_accidents() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02"]),
            "hora": ["08:15", "21:30", "08:45"],
            "comuna": ["2", "2", "17"],
            "franja_horaria": ["mañana", "noche", "mañana"],
            "tipo_accidente": ["Choque", "Atropello", "Choque"],
            "gravedad": ["Solo daños", "Herido", "Solo daños"],
            "interseccion": ["A", "B", "A"],
            "dia_semana": ["miércoles", "miércoles", "jueves"],
        }
    )


def test_filter_accidents_by_comuna_time_band_and_date() -> None:
    accidents = _sample_accidents()

    result = filter_accidents(
        accidents,
        comunas=["2"],
        franjas_horarias=["mañana"],
        tipos_accidente=["Choque"],
        gravedades=["Solo daños"],
        date_range=(pd.Timestamp("2025-01-01").date(), pd.Timestamp("2025-01-02").date()),
    )

    assert len(result) == 1
    assert result.loc[0, "comuna"] == "2"


def test_aggregate_by_comuna_counts_descending() -> None:
    result = aggregate_by_comuna(_sample_accidents())

    assert result.to_dict("records") == [
        {"comuna": "2", "accidentes": 2},
        {"comuna": "17", "accidentes": 1},
    ]


def test_build_kpis() -> None:
    result = build_kpis(_sample_accidents())

    assert result.total_accidents == 3
    assert result.daily_average == 1.5
    assert result.top_comuna == "2"
    assert result.top_intersection == "A"
    assert result.critical_hour == "08:00"
    assert result.weekly_trend == "A la baja"
    assert result.weekly_trend_delta == -50.0


def test_build_kpis_handles_empty_data() -> None:
    result = build_kpis(_sample_accidents().iloc[0:0])

    assert result.total_accidents == 0
    assert result.critical_hour == "Sin datos"
    assert result.weekly_trend == "Sin tendencia"
    assert result.weekly_trend_delta == 0.0


def test_aggregate_by_weekday_uses_calendar_order() -> None:
    result = aggregate_by_weekday(_sample_accidents())

    assert result["dia_semana"].tolist() == ["miércoles", "jueves"]


def test_aggregate_by_hour_returns_full_day() -> None:
    result = aggregate_by_hour(_sample_accidents())

    assert len(result) == 24
    assert result.loc[result["hora_dia"] == 8, "accidentes"].iloc[0] == 2
    assert result.loc[result["hora_dia"] == 21, "accidentes"].iloc[0] == 1
