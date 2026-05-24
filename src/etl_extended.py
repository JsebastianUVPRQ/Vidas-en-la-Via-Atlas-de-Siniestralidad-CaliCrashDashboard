"""ETL for broad Valle del Cauca road crash datasets."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.data_sources import DATA_SOURCES, RAW_EXTERNAL_DIR, DataSource
from src.etl import assign_time_band


EXTENDED_COLUMNS = [
    "source_id",
    "fuente",
    "departamento",
    "municipio",
    "fecha",
    "hora",
    "anio",
    "mes",
    "dia_semana",
    "franja_horaria",
    "tipo_accidente",
    "gravedad",
    "direccion",
    "barrio",
    "comuna",
    "zona",
    "latitud",
    "longitud",
    "actor_vial",
    "clase_vehiculo",
    "marca_vehiculo",
    "hipotesis",
    "autoridad",
    "unidad_observacion",
    "registro_origen",
    "es_cali",
]


def build_extended_accidents(
    input_dir: Path = RAW_EXTERNAL_DIR,
    include_optional: bool = True,
) -> pd.DataFrame:
    """Load and normalize all downloaded external sources into one table."""
    frames: list[pd.DataFrame] = []
    for source in DATA_SOURCES:
        if not source.enabled_by_default and not include_optional:
            continue

        path = input_dir / source.output_filename
        if not path.exists():
            continue
        raw = pd.read_csv(
            path,
            sep=source.csv_separator,
            encoding=source.encoding,
            dtype=str,
            low_memory=False,
        )
        frames.append(_normalize_source(raw, source))

    if not frames:
        return pd.DataFrame(columns=EXTENDED_COLUMNS)

    result = pd.concat(frames, ignore_index=True)
    result = _postprocess_extended(result)
    return result[EXTENDED_COLUMNS].sort_values(
        ["fecha", "municipio", "source_id"],
        na_position="last",
    ).reset_index(drop=True)


def build_cali_accidents(extended: pd.DataFrame) -> pd.DataFrame:
    """Return the Cali subset from the extended Valle table."""
    if extended.empty:
        return extended.copy()
    return extended[extended["es_cali"]].reset_index(drop=True)


def write_extended_outputs(
    output_dir: Path = Path("data/processed"),
    input_dir: Path = RAW_EXTERNAL_DIR,
    include_optional: bool = True,
) -> tuple[Path, Path]:
    """Build and write Valle-wide and Cali-only processed CSV outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    extended = build_extended_accidents(
        input_dir=input_dir,
        include_optional=include_optional,
    )
    cali = build_cali_accidents(extended)
    extended_path = output_dir / "accidentes_ampliados.csv"
    cali_path = output_dir / "accidentes_cali_ampliados.csv"
    extended.to_csv(extended_path, index=False, encoding="utf-8")
    cali.to_csv(cali_path, index=False, encoding="utf-8")
    return extended_path, cali_path


def _normalize_source(raw: pd.DataFrame, source: DataSource) -> pd.DataFrame:
    normalizers = {
        "cali_siniestralidad_2016_2024": _normalize_cali_siniestralidad,
        "cali_lesionados_2016_2025": _normalize_cali_lesionados,
        "cali_muertes_2016_2023": _normalize_cali_muertes,
        "valle_candelaria_accidentalidad": _normalize_candelaria,
        "valle_tulua_accidentalidad": _normalize_tulua,
        "valle_palmira_accidentes_2022_2023": _normalize_palmira_2022_2023,
        "valle_palmira_siniestros_2024": _normalize_palmira_2024,
        "runt_vehiculos_valle_ley2251": _normalize_runt_vehiculos,
    }
    try:
        frame = normalizers[source.source_id](raw)
    except KeyError as exc:
        raise ValueError(f"No hay normalizador para {source.source_id}") from exc

    frame["source_id"] = source.source_id
    frame["fuente"] = source.title
    return _ensure_extended_columns(frame)


def _normalize_cali_siniestralidad(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Cali"
    data["fecha"] = _column(raw, "Fecha")
    data["hora"] = pd.NA
    data["tipo_accidente"] = _first_available(
        raw,
        ["Tipo clase de accidente", "Tipo clase de accidente.1"],
    )
    data["gravedad"] = _first_available(raw, ["Tipo confirmado", "Tipo confirmado.1"])
    data["direccion"] = _column(raw, "Dirección reporte")
    data["clase_vehiculo"] = _column(raw, "Tipo de vehículos implicados")
    data["autoridad"] = _column(raw, "Medio de reporte")
    data["registro_origen"] = _column(raw, "Código")
    data["unidad_observacion"] = "siniestro"
    return data


def _normalize_cali_lesionados(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Cali"
    data["fecha"] = _column(raw, "Fecha")
    data["hora"] = _column(raw, "Hora")
    data["tipo_accidente"] = _column(raw, "Tipo_Confirmado.1")
    data["gravedad"] = _column(raw, "Tipo_Confirmado")
    data["direccion"] = _column(raw, "Dirección_Reporte")
    data["autoridad"] = _column(raw, "Placa Agente de Transito")
    data["actor_vial"] = raw.apply(_actor_from_cali_lesionados, axis=1)
    data["unidad_observacion"] = "lesionado"
    return data


def _normalize_cali_muertes(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Cali"
    data["fecha"] = _column(raw, "FECHA HECHO")
    data["hora"] = _column(raw, "HORA HECHO")
    data["gravedad"] = "Fatal"
    data["tipo_accidente"] = "Muerte en accidente de tránsito"
    data["actor_vial"] = _column(raw, "CONDICION")
    data["unidad_observacion"] = "fallecido"
    return data


def _normalize_candelaria(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Candelaria"
    data["fecha"] = _column(raw, "fecha_de_ocurrecia")
    data["hora"] = _column(raw, "hora_ocurrencia")
    data["dia_semana"] = _column(raw, "d_a_semana")
    data["tipo_accidente"] = _column(raw, "clase_de_accidente")
    data["gravedad"] = _column(raw, "gravedad")
    data["direccion"] = _column(raw, "vias")
    data["barrio"] = _column(raw, "corregimiento")
    data["unidad_observacion"] = "siniestro"
    return data


def _normalize_tulua(raw: pd.DataFrame) -> pd.DataFrame:
    lat_lon = _parse_point_column(_column(raw, "cordenada_geografica_"))
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Tuluá"
    data["fecha"] = _column(raw, "fecha")
    data["hora"] = _column(raw, "hora")
    data["dia_semana"] = _column(raw, "dia")
    data["tipo_accidente"] = _column(raw, "clase_de_accidente")
    data["gravedad"] = _column(raw, "gravedad_del_accidente")
    data["direccion"] = _column(raw, "direccion_hecho")
    data["barrio"] = _column(raw, "barrio_hecho")
    data["zona"] = _column(raw, "area")
    data["clase_vehiculo"] = _column(raw, "clase_de_vehiculo")
    data["latitud"] = lat_lon["latitud"]
    data["longitud"] = lat_lon["longitud"]
    data["unidad_observacion"] = "siniestro"
    return data


def _normalize_palmira_2022_2023(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Palmira"
    data["fecha"] = _column(raw, "fecha")
    data["hora"] = _column(raw, "hora")
    data["dia_semana"] = _column(raw, "dia_semana")
    data["tipo_accidente"] = _column(raw, "gravedad")
    data["gravedad"] = _column(raw, "clase_accidente")
    data["direccion"] = _column(raw, "direccion")
    data["barrio"] = _column(raw, "barrios_corregimiento_via")
    data["zona"] = _column(raw, "zona")
    data["latitud"] = _column(raw, "lat")
    data["longitud"] = _column(raw, "long")
    data["hipotesis"] = _column(raw, "hipotesis")
    data["actor_vial"] = _column(raw, "condicion_de_la_victima")
    data["clase_vehiculo"] = _column(raw, "clase_vehiculo")
    data["marca_vehiculo"] = _column(raw, "marca")
    data["autoridad"] = _column(raw, "autoridad")
    data["unidad_observacion"] = "víctima"
    return data


def _normalize_palmira_2024(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = "Valle del Cauca"
    data["municipio"] = "Palmira"
    data["fecha"] = _column(raw, "fecha")
    data["hora"] = _column(raw, "hora")
    data["dia_semana"] = _column(raw, "dia_semana")
    data["tipo_accidente"] = _column(raw, "clase_siniestro")
    data["gravedad"] = _column(raw, "lesionados_y_muertos")
    data["direccion"] = _column(raw, "direccion")
    data["barrio"] = _column(raw, "barrios_corregimiento_via")
    data["zona"] = _column(raw, "zona")
    data["latitud"] = _column(raw, "lat")
    data["longitud"] = _column(raw, "long")
    data["hipotesis"] = _column(raw, "hipotesis")
    data["actor_vial"] = _column(raw, "condicion_de_la_victima")
    data["autoridad"] = _column(raw, "autoridad")
    data["registro_origen"] = _column(raw, "ipat")
    data["unidad_observacion"] = "víctima"
    return data


def _normalize_runt_vehiculos(raw: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["departamento"] = _column(raw, "departamento_accidente")
    data["municipio"] = _column(raw, "municipio_accidente")
    data["fecha"] = _column(raw, "fecha_accidente")
    data["gravedad"] = _column(raw, "gravedad_accidente")
    data["tipo_accidente"] = "Vehículo involucrado"
    data["clase_vehiculo"] = _column(raw, "tipo_vehiculo")
    data["marca_vehiculo"] = _column(raw, "marca_vehiculo")
    data["autoridad"] = _column(raw, "autoridad_de_transito")
    data["unidad_observacion"] = "vehículo"
    return data


def _postprocess_extended(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["fecha"] = _parse_dates(data["fecha"])
    data["hora"] = data["hora"].map(_normalize_hour)
    data["latitud"] = _to_decimal_number(data["latitud"])
    data["longitud"] = _to_decimal_number(data["longitud"])

    text_columns = [
        "source_id",
        "fuente",
        "departamento",
        "municipio",
        "dia_semana",
        "tipo_accidente",
        "gravedad",
        "direccion",
        "barrio",
        "comuna",
        "zona",
        "actor_vial",
        "clase_vehiculo",
        "marca_vehiculo",
        "hipotesis",
        "autoridad",
        "unidad_observacion",
        "registro_origen",
    ]
    for column in text_columns:
        data[column] = data[column].map(_clean_text)

    missing_weekday = data["dia_semana"].eq("Sin dato") & data["fecha"].notna()
    data.loc[missing_weekday, "dia_semana"] = data.loc[missing_weekday, "fecha"].dt.day_name().map(
        _weekday_to_spanish
    )
    data["dia_semana"] = data["dia_semana"].map(_normalize_weekday)
    data["gravedad"] = data["gravedad"].map(_normalize_severity)
    data["tipo_accidente"] = data["tipo_accidente"].map(_normalize_crash_type)
    data["franja_horaria"] = data["hora"].map(assign_time_band)
    data["anio"] = data["fecha"].dt.year.astype("Int64")
    data["mes"] = data["fecha"].dt.to_period("M").astype(str).replace("NaT", "Sin dato")
    data["es_cali"] = data["municipio"].map(_normalize_ascii).eq("CALI")
    return data


def _ensure_extended_columns(data: pd.DataFrame) -> pd.DataFrame:
    for column in EXTENDED_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA
    return data


def _column(data: pd.DataFrame, name: str) -> pd.Series:
    if name in data.columns:
        return data[name]
    normalized_lookup = {_normalize_ascii(column): column for column in data.columns}
    resolved = normalized_lookup.get(_normalize_ascii(name))
    if resolved is not None:
        return data[resolved]
    return pd.Series([pd.NA] * len(data), index=data.index)


def _first_available(data: pd.DataFrame, names: list[str]) -> pd.Series:
    result = pd.Series([pd.NA] * len(data), index=data.index, dtype="object")
    for name in names:
        candidate = _column(data, name)
        result = result.where(result.notna() & result.astype(str).str.strip().ne("."), candidate)
    return result


def _actor_from_cali_lesionados(row: pd.Series) -> str:
    actors = []
    for column, actor in [
        ("Automovil", "Automóvil"),
        ("Moto", "Motocicleta"),
        ("Ciclista", "Ciclista"),
        ("Peaton", "Peatón"),
    ]:
        value = row.get(column)
        if pd.notna(value) and str(value).strip() not in {"", "."}:
            actors.append(actor)
    return ", ".join(actors) if actors else "Sin dato"


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.fillna("").astype(str).str.strip()
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    month_year = parsed.isna() & text.str.fullmatch(r"\d{1,2}/\d{4}")
    if month_year.any():
        parsed.loc[month_year] = pd.to_datetime(
            "01/" + text.loc[month_year],
            errors="coerce",
            dayfirst=True,
        )
    return parsed


def _normalize_hour(value: object) -> str:
    text = _clean_text(value)
    if text == "Sin dato":
        return "00:00"
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        match = re.search(r"(\d{1,2})(?::(\d{1,2}))?", text)
        if not match:
            return "00:00"
        hour = int(match.group(1)) % 24
        minute = int(match.group(2) or 0) % 60
        return f"{hour:02d}:{minute:02d}"
    return f"{int(parsed.hour):02d}:{int(parsed.minute):02d}"


def _parse_point_column(values: pd.Series) -> pd.DataFrame:
    extracted = values.astype(str).str.extract(
        r"POINT\s*\(\s*(?P<longitud>-?\d+(?:\.\d+)?)\s+(?P<latitud>-?\d+(?:\.\d+)?)\s*\)"
    )
    return extracted


def _to_decimal_number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(
        values.astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return "Sin dato"
    text = str(value).strip()
    if text in {"", ".", "nan", "NaN", "N/A", "NO APLICA", "No informa"}:
        return "Sin dato"
    return " ".join(text.split())


def _normalize_ascii(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")


def _normalize_weekday(value: str) -> str:
    lookup = {
        "LUNES": "lunes",
        "MARTES": "martes",
        "MIERCOLES": "miércoles",
        "JUEVES": "jueves",
        "VIERNES": "viernes",
        "SABADO": "sábado",
        "DOMINGO": "domingo",
        "MONDAY": "lunes",
        "TUESDAY": "martes",
        "WEDNESDAY": "miércoles",
        "THURSDAY": "jueves",
        "FRIDAY": "viernes",
        "SATURDAY": "sábado",
        "SUNDAY": "domingo",
    }
    return lookup.get(_normalize_ascii(value), "Sin dato")


def _weekday_to_spanish(value: object) -> str:
    return _normalize_weekday(str(value))


def _normalize_severity(value: str) -> str:
    key = _normalize_ascii(value)
    if "MUERTO" in key or "FATAL" in key:
        return "Fatal"
    if "HERIDO" in key or "LESION" in key:
        return "Herido"
    if "DANO" in key or "SOLO_DANOS" in key:
        return "Solo daños"
    if key in {"SIN_DATO", "NEGATIVO"}:
        return "Sin dato"
    return value.title()


def _normalize_crash_type(value: str) -> str:
    text = value.replace("Por ", "").replace("por ", "")
    if _normalize_ascii(text) == "SIN_DATO":
        return "Sin dato"
    return text.title()
