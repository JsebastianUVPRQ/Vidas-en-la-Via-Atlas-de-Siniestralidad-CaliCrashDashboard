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


def test_build_kpis_ignores_unknown_comuna() -> None:
    accidents = _sample_accidents()
    accidents["comuna"] = ["Sin dato", "Sin dato", "17"]

    result = build_kpis(accidents)

    assert result.top_comuna == "17"


def test_aggregate_by_weekday_uses_calendar_order() -> None:
    result = aggregate_by_weekday(_sample_accidents())

    assert result["dia_semana"].tolist() == ["miércoles", "jueves"]


def test_aggregate_by_hour_returns_full_day() -> None:
    result = aggregate_by_hour(_sample_accidents())

    assert len(result) == 24
    assert result.loc[result["hora_dia"] == 8, "accidentes"].iloc[0] == 2
    assert result.loc[result["hora_dia"] == 21, "accidentes"].iloc[0] == 1


def test_filter_accidents_by_single_date() -> None:
    accidents = _sample_accidents()

    result = filter_accidents(
        accidents,
        date_range=(pd.Timestamp("2025-01-01").date(),)
    )

    assert len(result) == 2


def test_build_kpis_weekly_trend_long_period() -> None:
    # Create 14 days of data: day 0 to 13.
    # First week (day 0-6): 2 accidents/day = 14 accidents.
    # Second week (day 7-13): 1 accident/day = 7 accidents.
    # The trend should be "A la baja" with delta = -50%
    dates = []
    for i in range(14):
        date_str = f"2025-01-{i+1:02d}"
        count = 2 if i < 7 else 1
        for _ in range(count):
            dates.append(date_str)
    
    df = pd.DataFrame({
        "fecha": pd.to_datetime(dates),
        "hora": ["12:00"] * len(dates),
        "comuna": ["2"] * len(dates),
        "franja_horaria": ["tarde"] * len(dates),
        "tipo_accidente": ["Choque"] * len(dates),
        "gravedad": ["Solo daños"] * len(dates),
        "interseccion": ["A"] * len(dates),
        "dia_semana": ["lunes"] * len(dates)
    })
    
    result = build_kpis(df)
    assert result.weekly_trend == "A la baja"
    assert result.weekly_trend_delta == -50.0
