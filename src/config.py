"""Shared configuration for the Cali crash dashboard."""

from pathlib import Path


CALI_CENTER = (3.4516, -76.5320)

DATA_CANDIDATES = (
    Path("data/processed/accidentes_limpios.csv"),
    Path("data/raw/accidentes.csv"),
)

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
