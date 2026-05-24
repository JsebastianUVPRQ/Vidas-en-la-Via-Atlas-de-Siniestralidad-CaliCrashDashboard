import pandas as pd

from src.dashboard import (
    _build_temporal_summary,
    _daily_counts,
    _daily_variation_label,
    _hourly_insight,
)
from src.metrics import aggregate_by_hour


def _accidents(hours: list[str], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fecha": pd.to_datetime(dates),
            "hora": hours,
            "comuna": ["2"] * len(hours),
            "franja_horaria": ["tarde"] * len(hours),
            "tipo_accidente": ["Choque"] * len(hours),
            "gravedad": ["Solo daños"] * len(hours),
            "interseccion": ["A"] * len(hours),
            "dia_semana": ["lunes"] * len(hours),
        }
    )


def test_hourly_insight_identifies_dominant_hour() -> None:
    accidents = _accidents(
        ["18:10", "18:20", "18:50", "07:00"],
        ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-02"],
    )
    hourly = aggregate_by_hour(accidents)

    result = _hourly_insight(hourly, len(accidents))

    assert "18:00" in result
    assert "3 accidentes" in result


def test_hourly_insight_reports_dispersed_distribution() -> None:
    accidents = _accidents(
        ["06:00", "07:00", "08:00", "13:00", "17:00", "18:00", "19:00"],
        ["2025-01-01"] * 7,
    )
    hourly = aggregate_by_hour(accidents)

    result = _hourly_insight(hourly, len(accidents))

    assert "no presenta un patrón dominante" in result


def test_temporal_summary_builds_daily_context() -> None:
    accidents = _accidents(
        ["08:00", "08:30", "09:00", "18:00", "18:30"],
        ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-03"],
    )
    hourly = aggregate_by_hour(accidents)
    daily = _daily_counts(accidents)

    result = _build_temporal_summary(accidents, hourly, daily)

    assert result.total_accidents == 5
    assert result.daily_average == 5 / 3
    assert result.critical_day == "01 ene 2025"
    assert result.daily_variation == "Estable"


def test_daily_variation_label_detects_direction() -> None:
    daily = pd.DataFrame(
        {
            "dia": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
            "accidentes": [4, 3, 1],
        }
    )

    assert _daily_variation_label(daily) == "A la baja"
