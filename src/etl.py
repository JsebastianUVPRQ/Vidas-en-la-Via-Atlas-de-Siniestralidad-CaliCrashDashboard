"""Data loading and normalization for Cali traffic crash records."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "fecha",
    "hora",
    "latitud",
    "longitud",
    "comuna",
    "barrio",
    "tipo_accidente",
    "gravedad",
    "interseccion",
}

COLUMN_ALIASES = {
    "date": "fecha",
    "fecha_accidente": "fecha",
    "hora_accidente": "hora",
    "latitude": "latitud",
    "lat": "latitud",
    "y": "latitud",
    "longitude": "longitud",
    "lon": "longitud",
    "lng": "longitud",
    "x": "longitud",
    "comuna_nombre": "comuna",
    "tipo": "tipo_accidente",
    "clase_accidente": "tipo_accidente",
    "severidad": "gravedad",
    "cruce": "interseccion",
}

_TIME_BAND_BINS = [-1, 5, 11, 17, 23]
_TIME_BAND_LABELS = ["madrugada", "mañana", "tarde", "noche"]

WEEKDAY_NAMES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

CALI_LAT_RANGE = (3.0, 3.8)
CALI_LON_RANGE = (-77.0, -76.0)


@dataclass(frozen=True)
class DataQuality:
    total_raw: int
    total_clean: int
    null_fecha: int
    null_coords: int
    out_of_bounds: int


def load_accident_data(paths: Iterable[Path]) -> pd.DataFrame:
    """Load the first available accident dataset or return a small sample.

    Args:
        paths: Candidate file paths, ordered by preference. Supports CSV and Parquet.

    Returns:
        A normalized accident DataFrame ready for dashboard filters.
    """
    for path in paths:
        if path.exists():
            suffix = path.suffix.lower()
            if suffix == ".parquet":
                return normalize_accident_data(pd.read_parquet(path))
            return normalize_accident_data(pd.read_csv(path))

    return normalize_accident_data(build_sample_accidents())


def normalize_accident_data(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize accident fields, dates, coordinates, and derived columns."""
    normalized = _normalize_columns(data)
    normalized = _parse_and_validate(normalized)
    normalized = _derive_time_features(normalized)
    return normalized.sort_values("fecha").reset_index(drop=True)


def data_quality_report(raw: pd.DataFrame, cleaned: pd.DataFrame) -> DataQuality:
    """Compare raw input against cleaned output for quality metrics."""
    return DataQuality(
        total_raw=len(raw),
        total_clean=len(cleaned),
        null_fecha=int(raw["fecha"].isna().sum()) if "fecha" in raw else len(raw),
        null_coords=int(
            raw["latitud"].isna().sum() + raw["longitud"].isna().sum()
        )
        if "latitud" in raw and "longitud" in raw
        else len(raw),
        out_of_bounds=max(0, len(raw) - len(cleaned)),
    )


def assign_time_band(hour_value: object) -> str:
    """Return the Cali dashboard time band for a time-like value.

    Examples:
        ``assign_time_band("07:30")`` returns ``"mañana"``.
        ``assign_time_band("21")`` returns ``"noche"``.
    """
    hour = _extract_hour(hour_value)
    bands = [
        ("madrugada", 0, 5),
        ("mañana", 6, 11),
        ("tarde", 12, 17),
        ("noche", 18, 23),
    ]
    for band, start, end in bands:
        if start <= hour <= end:
            return band
    return "Sin dato"


def build_sample_accidents() -> pd.DataFrame:
    """Create a tiny Cali-centered sample for first-run dashboard validation."""
    return pd.DataFrame(
        [
            {
                "fecha": "2025-01-05",
                "hora": "07:30",
                "latitud": 3.4516,
                "longitud": -76.5320,
                "comuna": "2",
                "barrio": "Versalles",
                "tipo_accidente": "Choque",
                "gravedad": "Solo daños",
                "interseccion": "Avenida 6N con Calle 21N",
            },
            {
                "fecha": "2025-01-05",
                "hora": "08:05",
                "latitud": 3.4550,
                "longitud": -76.5310,
                "comuna": "2",
                "barrio": "Santa Mónica",
                "tipo_accidente": "Choque",
                "gravedad": "Herido",
                "interseccion": "Avenida 6N con Calle 30N",
            },
            {
                "fecha": "2025-01-05",
                "hora": "18:45",
                "latitud": 3.4206,
                "longitud": -76.5222,
                "comuna": "19",
                "barrio": "San Fernando",
                "tipo_accidente": "Atropello",
                "gravedad": "Herido",
                "interseccion": "Calle 5 con Carrera 34",
            },
            {
                "fecha": "2025-01-06",
                "hora": "06:20",
                "latitud": 3.4218,
                "longitud": -76.5205,
                "comuna": "19",
                "barrio": "San Fernando",
                "tipo_accidente": "Caída de ocupante",
                "gravedad": "Herido",
                "interseccion": "Calle 5 con Carrera 34",
            },
            {
                "fecha": "2025-01-06",
                "hora": "23:10",
                "latitud": 3.3731,
                "longitud": -76.5360,
                "comuna": "17",
                "barrio": "El Caney",
                "tipo_accidente": "Choque",
                "gravedad": "Solo daños",
                "interseccion": "Carrera 80 con Calle 42",
            },
            {
                "fecha": "2025-01-07",
                "hora": "13:40",
                "latitud": 3.3745,
                "longitud": -76.5385,
                "comuna": "17",
                "barrio": "Valle del Lili",
                "tipo_accidente": "Choque",
                "gravedad": "Solo daños",
                "interseccion": "Carrera 98 con Calle 25",
            },
            {
                "fecha": "2025-01-07",
                "hora": "17:15",
                "latitud": 3.4370,
                "longitud": -76.5233,
                "comuna": "3",
                "barrio": "San Nicolás",
                "tipo_accidente": "Atropello",
                "gravedad": "Herido",
                "interseccion": "Calle 15 con Carrera 8",
            },
            {
                "fecha": "2025-01-08",
                "hora": "01:35",
                "latitud": 3.4439,
                "longitud": -76.5074,
                "comuna": "8",
                "barrio": "Primitivo Crespo",
                "tipo_accidente": "Volcamiento",
                "gravedad": "Solo daños",
                "interseccion": "Autopista Sur con Carrera 23",
            },
            {
                "fecha": "2025-01-08",
                "hora": "19:25",
                "latitud": 3.3965,
                "longitud": -76.5487,
                "comuna": "18",
                "barrio": "Meléndez",
                "tipo_accidente": "Choque",
                "gravedad": "Fatal",
                "interseccion": "Calle 5 con Carrera 94",
            },
        ]
    )


def _normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    renamed = data.rename(columns=_normalize_column_name)
    renamed = renamed.rename(columns=COLUMN_ALIASES)
    for column in REQUIRED_COLUMNS.difference(renamed.columns):
        renamed[column] = pd.NA
    return renamed


def _parse_and_validate(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")
    data["hora"] = data["hora"].fillna("00:00").astype(str)
    data["latitud"] = pd.to_numeric(data["latitud"], errors="coerce")
    data["longitud"] = pd.to_numeric(data["longitud"], errors="coerce")
    for column in ["comuna", "barrio", "tipo_accidente", "gravedad", "interseccion"]:
        data[column] = data[column].fillna("Sin dato").astype(str)
    data = data.dropna(subset=["fecha", "latitud", "longitud"])
    return data[
        data["latitud"].between(*CALI_LAT_RANGE)
        & data["longitud"].between(*CALI_LON_RANGE)
    ].copy()


def _derive_time_features(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["franja_horaria"] = _assign_time_band_vectorized(data["hora"])
    data["dia_semana"] = data["fecha"].dt.weekday.map(WEEKDAY_NAMES)
    data["mes"] = data["fecha"].dt.to_period("M").astype(str)
    return data


def _assign_time_band_vectorized(hours: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(hours, format="%H:%M", errors="coerce")
    hour_numeric = parsed.dt.hour
    mask = hour_numeric.isna()
    if mask.any():
        numeric = pd.to_numeric(hours[mask].astype(str).str.strip(), errors="coerce")
        hour_numeric = hour_numeric.copy()
        hour_numeric[mask] = numeric % 24
    hour_numeric = hour_numeric.fillna(-1)
    result = pd.cut(
        hour_numeric,
        bins=_TIME_BAND_BINS,
        labels=_TIME_BAND_LABELS,
        right=True,
    )
    return result.cat.add_categories(["Sin dato"]).fillna("Sin dato")


def _normalize_column_name(column: str) -> str:
    return column.strip().lower().replace(" ", "_")


def _extract_hour(hour_value: object) -> int:
    text_value = str(hour_value).strip()
    parsed = pd.to_datetime(text_value, format="%H:%M", errors="coerce")
    if pd.isna(parsed):
        try:
            return int(float(text_value)) % 24
        except ValueError:
            pass
    if pd.isna(parsed):
        parsed = pd.to_datetime(text_value, errors="coerce")
    if pd.isna(parsed):
        return -1
    return int(parsed.hour)
