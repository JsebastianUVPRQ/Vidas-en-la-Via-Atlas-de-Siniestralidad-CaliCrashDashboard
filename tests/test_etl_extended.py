import pandas as pd

from src.data_sources import get_source
from src.etl_extended import (
    build_cali_accidents,
    _normalize_source,
    _postprocess_extended,
)


def test_normalize_cali_siniestralidad_maps_core_fields() -> None:
    raw = pd.DataFrame(
        {
            "Código": ["A1"],
            "Fecha": ["1/01/2024"],
            "Tipo confirmado": ["Solo daños"],
            "Dirección reporte": ["Calle 5 con Carrera 10"],
            "Tipo clase de accidente": ["Choque"],
            "Medio de reporte": ["RADIO"],
            "Tipo de vehículos implicados": ["MOTOCICLETA"],
        }
    )

    result = _postprocess_extended(
        _normalize_source(raw, get_source("cali_siniestralidad_2016_2024"))
    )

    assert result.loc[0, "municipio"] == "Cali"
    assert result.loc[0, "es_cali"]
    assert result.loc[0, "fecha"] == pd.Timestamp("2024-01-01")
    assert result.loc[0, "gravedad"] == "Solo daños"
    assert result.loc[0, "tipo_accidente"] == "Choque"


def test_normalize_tulua_extracts_point_coordinates() -> None:
    raw = pd.DataFrame(
        {
            "fecha": ["2023-01-03T00:00:00.000"],
            "hora": ["15:40:00"],
            "dia": ["martes"],
            "direccion_hecho": ["CARRERA 21 CALLE 32"],
            "barrio_hecho": ["SAJONIA"],
            "clase_de_accidente": ["CHOQUE"],
            "gravedad_del_accidente": ["CON HERIDOS"],
            "clase_de_vehiculo": ["MOTOCICLETA"],
            "cordenada_geografica_": ["POINT (-76.201795 4.080615)"],
        }
    )

    result = _postprocess_extended(
        _normalize_source(raw, get_source("valle_tulua_accidentalidad"))
    )

    assert result.loc[0, "municipio"] == "Tuluá"
    assert result.loc[0, "latitud"] == 4.080615
    assert result.loc[0, "longitud"] == -76.201795
    assert result.loc[0, "gravedad"] == "Herido"
    assert result.loc[0, "franja_horaria"] == "tarde"


def test_normalize_runt_month_year_date_and_cali_filter() -> None:
    raw = pd.DataFrame(
        {
            "marca_vehiculo": ["VICTORY"],
            "tipo_vehiculo": ["MOTOCICLETA"],
            "fecha_accidente": ["12/2025"],
            "gravedad_accidente": ["CON HERIDOS"],
            "departamento_accidente": ["VALLE DEL CAUCA"],
            "municipio_accidente": ["CALI"],
            "autoridad_de_transito": ["STRIA MCPAL TTO CALI"],
        }
    )

    extended = _postprocess_extended(
        _normalize_source(raw, get_source("runt_vehiculos_valle_ley2251"))
    )
    cali = build_cali_accidents(extended)

    assert extended.loc[0, "fecha"] == pd.Timestamp("2025-12-01")
    assert extended.loc[0, "unidad_observacion"] == "vehículo"
    assert extended.loc[0, "gravedad"] == "Herido"
    assert len(cali) == 1
