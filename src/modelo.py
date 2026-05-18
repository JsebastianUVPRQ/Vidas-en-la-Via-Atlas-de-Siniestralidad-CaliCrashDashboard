"""Frequency model helpers for Cali traffic crash records."""

import pandas as pd


def estimate_frequency(accidents: pd.DataFrame) -> pd.DataFrame:
    """Estimate observed daily accident frequency by commune and time band.

    This baseline model uses historical averages from the selected period. It
    is intentionally lightweight until a larger validated dataset is connected.
    """
    columns = [
        "comuna",
        "franja_horaria",
        "accidentes_observados",
        "dias_observados",
        "frecuencia_diaria_esperada",
        "nivel_riesgo",
    ]
    if accidents.empty:
        return pd.DataFrame(columns=columns)

    days = max(accidents["fecha"].dt.date.nunique(), 1)
    grouped = (
        accidents.groupby(["comuna", "franja_horaria"], dropna=False)
        .size()
        .reset_index(name="accidentes_observados")
    )
    grouped["dias_observados"] = days
    grouped["frecuencia_diaria_esperada"] = (
        grouped["accidentes_observados"] / grouped["dias_observados"]
    )
    grouped["nivel_riesgo"] = _risk_labels(grouped["frecuencia_diaria_esperada"])

    return grouped.sort_values(
        ["frecuencia_diaria_esperada", "accidentes_observados"],
        ascending=False,
    ).reset_index(drop=True)[columns]


def _risk_labels(values: pd.Series) -> pd.Series:
    if values.empty:
        return pd.Series(dtype=str)

    high_threshold = values.quantile(0.75)
    medium_threshold = values.quantile(0.40)

    return values.map(
        lambda value: _risk_label(
            value,
            medium_threshold=medium_threshold,
            high_threshold=high_threshold,
        )
    )


def _risk_label(
    value: float,
    medium_threshold: float,
    high_threshold: float,
) -> str:
    if value >= high_threshold:
        return "alto"
    if value >= medium_threshold:
        return "medio"
    return "bajo"
