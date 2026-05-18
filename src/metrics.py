"""Aggregations and KPI helpers for dashboard views."""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.config import TIME_BAND_ORDER, WEEKDAY_ORDER


@dataclass(frozen=True)
class DashboardKpis:
    """Key figures shown at the top of the dashboard."""

    total_accidents: int
    daily_average: float
    top_comuna: str
    top_intersection: str


def filter_accidents(
    accidents: pd.DataFrame,
    comunas: list[str] | None = None,
    franjas_horarias: list[str] | None = None,
    tipos_accidente: list[str] | None = None,
    gravedades: list[str] | None = None,
    date_range: tuple[date, date] | list[date] | None = None,
) -> pd.DataFrame:
    """Filter accidents by commune, time band, type, severity, and date."""
    filtered = accidents

    if comunas:
        filtered = filtered[filtered["comuna"].astype(str).isin(comunas)]

    if franjas_horarias:
        filtered = filtered[filtered["franja_horaria"].isin(franjas_horarias)]

    if tipos_accidente:
        filtered = filtered[filtered["tipo_accidente"].isin(tipos_accidente)]

    if gravedades:
        filtered = filtered[filtered["gravedad"].isin(gravedades)]

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        dates = filtered["fecha"].dt.date
        filtered = filtered[(dates >= start_date) & (dates <= end_date)]

    return filtered.reset_index(drop=True)


def build_kpis(accidents: pd.DataFrame) -> DashboardKpis:
    """Build top-level dashboard KPIs from filtered accidents."""
    total = len(accidents)
    if accidents.empty:
        return DashboardKpis(
            total_accidents=0,
            daily_average=0.0,
            top_comuna="Sin datos",
            top_intersection="Sin datos",
        )

    date_count = accidents["fecha"].dt.date.nunique()
    top_comuna = aggregate_by_comuna(accidents).iloc[0]["comuna"]
    top_intersection = _top_value(accidents, "interseccion")

    return DashboardKpis(
        total_accidents=total,
        daily_average=total / max(date_count, 1),
        top_comuna=str(top_comuna),
        top_intersection=top_intersection,
    )


def aggregate_by_comuna(accidents: pd.DataFrame) -> pd.DataFrame:
    """Count accidents by commune in descending order."""
    return _count_by(accidents, "comuna")


def aggregate_by_time_band(accidents: pd.DataFrame) -> pd.DataFrame:
    """Count accidents by time band using a human-readable order."""
    return _aggregate_sorted(accidents, "franja_horaria", TIME_BAND_ORDER)


def aggregate_by_weekday(accidents: pd.DataFrame) -> pd.DataFrame:
    """Count accidents by weekday using Monday-first order in Spanish."""
    return _aggregate_sorted(accidents, "dia_semana", WEEKDAY_ORDER)


def _aggregate_sorted(
    accidents: pd.DataFrame, column: str, order: list[str]
) -> pd.DataFrame:
    counts = _count_by(accidents, column)
    counts["sort_order"] = counts[column].map(
        {value: index for index, value in enumerate(order)}
    )
    return counts.sort_values(["sort_order", column]).drop(columns="sort_order")


def _count_by(accidents: pd.DataFrame, column: str) -> pd.DataFrame:
    if accidents.empty:
        return pd.DataFrame(columns=[column, "accidentes"])

    return (
        accidents.groupby(column, dropna=False)
        .size()
        .reset_index(name="accidentes")
        .sort_values("accidentes", ascending=False)
        .reset_index(drop=True)
    )


def _top_value(accidents: pd.DataFrame, column: str) -> str:
    if column not in accidents.columns:
        return "Sin datos"

    values = accidents[column].dropna().astype(str)
    values = values[values.ne("Sin dato")]
    if values.empty:
        return "Sin datos"
    return str(values.value_counts().idxmax())
