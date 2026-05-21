"""Narrative insight helpers for the dashboard."""

import pandas as pd


def build_insights(accidents: pd.DataFrame) -> list[str]:
    """Build up to three short narrative insights from filtered accidents."""
    if accidents.empty:
        return []

    insights = [
        _dominant_comuna(accidents),
        _dominant_time_band(accidents),
        _dominant_severity(accidents),
    ]
    return [insight for insight in insights if insight][:3]


def _dominant_comuna(accidents: pd.DataFrame) -> str:
    counts = accidents["comuna"].astype(str).value_counts()
    if counts.empty:
        return ""

    comuna = counts.idxmax()
    percentage = counts.max() / len(accidents) * 100
    return (
        f"La comuna {comuna} concentra "
        f"{percentage:.0f}% de los accidentes filtrados."
    )


def _dominant_time_band(accidents: pd.DataFrame) -> str:
    counts = accidents["franja_horaria"].astype(str).value_counts()
    if counts.empty:
        return ""

    band = counts.idxmax()
    percentage = counts.max() / len(accidents) * 100
    return f"La franja {band} domina el riesgo con {percentage:.0f}% de los casos."


def _dominant_severity(accidents: pd.DataFrame) -> str:
    if "gravedad" not in accidents.columns:
        return ""

    severity_counts = accidents["gravedad"].astype(str).value_counts()
    if severity_counts.empty:
        return ""

    severity = severity_counts.idxmax()
    if severity == "Sin dato":
        return ""

    percentage = severity_counts.max() / len(accidents) * 100
    return (
        f"La gravedad más frecuente es {severity.lower()}, "
        f"presente en {percentage:.0f}% de registros."
    )
