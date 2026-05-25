"""Shared configuration for the Cali crash dashboard."""

from pathlib import Path


CALI_CENTER = (3.4516, -76.5320)

DATA_CANDIDATES = (
    Path("data/processed/accidentes_limpios.parquet"),
    Path("data/processed/accidentes_limpios.csv"),
    Path("data/processed/accidentes_cali_ampliados.csv"),
    Path("data/processed/accidentes_ampliados.csv"),
    Path("data/raw/accidentes.csv"),
    Path("data/raw/cali_lesionados_2016_2025.csv"),
    Path("data/raw/cali_siniestralidad_2016_2024.csv"),
)

FATALITY_DATA_DIR = Path("data/fallecidos")

TIME_BAND_ORDER = ["madrugada", "mañana", "tarde", "noche", "Sin dato"]

WEEKDAY_ORDER = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

RISK_THRESHOLDS = {"bajo": 0.40, "medio": 0.75}
