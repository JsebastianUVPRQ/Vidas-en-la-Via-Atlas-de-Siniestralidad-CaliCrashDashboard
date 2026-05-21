"""ETL and aggregations for road fatality records."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


FATALITY_COLUMNS = {
    "Departamento",
    "Municipio",
    "EstadoVictima",
    "AnoHecho",
    "MesOCurrencia",
    "DiaOcurrencia",
    "Rango3horas",
    "Rango6horas",
    "Sexo",
    "RangoEdad",
    "ClaseAccidente",
    "Hipotesis",
    "TotalRegistros",
}

MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

WEEKDAY_BY_CODE = {
    "1": "lunes",
    "2": "martes",
    "3": "miércoles",
    "4": "jueves",
    "5": "viernes",
    "6": "sábado",
    "7": "domingo",
}


@dataclass(frozen=True)
class FatalityKpis:
    """Summary indicators for Cali fatality records."""

    total_fatalities: int
    top_year: str
    top_time_range: str
    top_crash_class: str


def load_fatality_data(directory: Path) -> pd.DataFrame:
    """Load and normalize all fatality CSV files from a directory."""
    files = sorted(directory.glob("*.csv")) if directory.exists() else []
    return normalize_fatality_data(_read_fatality_files(files))


def normalize_fatality_data(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize fatality records and keep only Cali, Valle del Cauca."""
    if data.empty:
        return _empty_fatalities()

    normalized = data.copy()
    for column in FATALITY_COLUMNS.difference(normalized.columns):
        normalized[column] = pd.NA

    normalized["Departamento"] = normalized["Departamento"].fillna("").astype(str)
    normalized["Municipio"] = normalized["Municipio"].fillna("").astype(str)
    normalized = normalized[
        normalized["Departamento"].map(_normalize_text).eq("VALLE DEL CAUCA")
        & normalized["Municipio"].map(_normalize_text).eq("CALI")
    ].copy()

    if normalized.empty:
        return _empty_fatalities()

    normalized["ano"] = pd.to_numeric(normalized["AnoHecho"], errors="coerce")
    normalized["mes"] = normalized["MesOCurrencia"].map(_extract_month)
    normalized["dia_semana"] = normalized["DiaOcurrencia"].map(_extract_weekday)
    normalized["rango_3h"] = _clean_text_column(normalized["Rango3horas"])
    normalized["rango_6h"] = _clean_text_column(normalized["Rango6horas"])
    normalized["sexo"] = _clean_text_column(normalized["Sexo"])
    normalized["rango_edad"] = _clean_text_column(normalized["RangoEdad"])
    normalized["clase_accidente"] = _clean_text_column(normalized["ClaseAccidente"])
    normalized["hipotesis"] = _clean_text_column(normalized["Hipotesis"])
    normalized["total_fallecidos"] = pd.to_numeric(
        normalized["TotalRegistros"],
        errors="coerce",
    ).fillna(1)

    columns = [
        "ano",
        "mes",
        "dia_semana",
        "rango_3h",
        "rango_6h",
        "sexo",
        "rango_edad",
        "clase_accidente",
        "hipotesis",
        "total_fallecidos",
    ]
    normalized = normalized.dropna(subset=["ano", "mes"])
    normalized["ano"] = normalized["ano"].astype(int)
    normalized["mes"] = normalized["mes"].astype(int)
    return normalized[columns].reset_index(drop=True)


def build_fatality_kpis(fatalities: pd.DataFrame) -> FatalityKpis:
    """Build top-level indicators for fatality records."""
    if fatalities.empty:
        return FatalityKpis(
            total_fatalities=0,
            top_year="Sin datos",
            top_time_range="Sin datos",
            top_crash_class="Sin datos",
        )

    return FatalityKpis(
        total_fatalities=int(fatalities["total_fallecidos"].sum()),
        top_year=str(_top_weighted_value(fatalities, "ano")),
        top_time_range=str(_top_weighted_value(fatalities, "rango_3h")),
        top_crash_class=str(_top_weighted_value(fatalities, "clase_accidente")),
    )


def aggregate_fatalities_by_year(fatalities: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fatality counts by year."""
    return _weighted_count(fatalities, "ano").rename(columns={"ano": "Año"})


def aggregate_fatalities_by_time_range(fatalities: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fatality counts by 3-hour range."""
    return _weighted_count(fatalities, "rango_3h")


def aggregate_fatalities_by_crash_class(fatalities: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fatality counts by crash class."""
    return _weighted_count(fatalities, "clase_accidente")


def _read_fatality_files(files: Iterable[Path]) -> pd.DataFrame:
    frames = [
        pd.read_csv(file, sep=";", encoding="utf-8", low_memory=False)
        for file in files
    ]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _weighted_count(data: pd.DataFrame, column: str) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=[column, "fallecidos"])
    return (
        data.groupby(column, dropna=False)["total_fallecidos"]
        .sum()
        .reset_index(name="fallecidos")
        .sort_values("fallecidos", ascending=False)
        .reset_index(drop=True)
    )


def _top_weighted_value(data: pd.DataFrame, column: str) -> object:
    counts = _weighted_count(data, column)
    counts = counts[~counts[column].astype(str).isin(["Sin información", "-1"])]
    if counts.empty:
        return "Sin datos"
    return counts.iloc[0][column]


def _clean_text_column(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("Sin información").astype(str).str.strip()
    return cleaned.replace({"-1": "Sin información", "": "Sin información"})


def _extract_month(value: object) -> int | None:
    text = _normalize_text(str(value).split(".", maxsplit=1)[-1])
    return MONTHS.get(text)


def _extract_weekday(value: object) -> str:
    code = str(value).split(".", maxsplit=1)[0].strip()
    return WEEKDAY_BY_CODE.get(code, "Sin información")


def _normalize_text(value: object) -> str:
    return str(value).strip().upper()


def _empty_fatalities() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "ano",
            "mes",
            "dia_semana",
            "rango_3h",
            "rango_6h",
            "sexo",
            "rango_edad",
            "clase_accidente",
            "hipotesis",
            "total_fallecidos",
        ]
    )
