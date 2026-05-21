"""Frequency model helpers for Cali traffic crash records."""

import numpy as np
import pandas as pd

from src.config import RISK_THRESHOLDS

_Z_SCORE = 1.96


def estimate_frequency(accidents: pd.DataFrame) -> pd.DataFrame:
    """Estimate observed daily accident frequency by commune and time band.

    Computes per-group accident counts, observed days, expected daily
    frequency, and a 95 % Poisson confidence interval.

    This baseline model uses historical averages from the selected period. It
    is intentionally lightweight until a larger validated dataset is connected.
    """
    columns = [
        "comuna",
        "franja_horaria",
        "accidentes_observados",
        "dias_observados",
        "frecuencia_diaria_esperada",
        "intervalo_inferior",
        "intervalo_superior",
        "nivel_riesgo",
    ]
    if accidents.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        accidents.groupby(["comuna", "franja_horaria"], dropna=False, observed=False)
        .agg(
            accidentes_observados=("fecha", "count"),
            dias_observados=("fecha", lambda col: col.dt.date.nunique()),
        )
        .reset_index()
    )

    rate = grouped["accidentes_observados"] / grouped["dias_observados"]
    se = np.sqrt(rate / grouped["dias_observados"])
    grouped["frecuencia_diaria_esperada"] = rate
    grouped["intervalo_inferior"] = (rate - _Z_SCORE * se).clip(lower=0)
    grouped["intervalo_superior"] = rate + _Z_SCORE * se
    grouped["nivel_riesgo"] = _risk_labels(grouped["frecuencia_diaria_esperada"])

    return grouped.sort_values(
        ["frecuencia_diaria_esperada", "accidentes_observados"],
        ascending=False,
    ).reset_index(drop=True)[columns]


def _risk_labels(values: pd.Series) -> pd.Series:
    if values.empty:
        return pd.Series(dtype=str)

    high_threshold = values.quantile(RISK_THRESHOLDS["medio"])
    medium_threshold = values.quantile(RISK_THRESHOLDS["bajo"])

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
