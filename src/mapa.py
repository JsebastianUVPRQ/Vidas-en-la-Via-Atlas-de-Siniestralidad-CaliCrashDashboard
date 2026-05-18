"""Folium map builders for Cali traffic crash records."""

from html import escape

import folium
import pandas as pd
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster

from src.config import CALI_CENTER


def build_accident_map(
    accidents: pd.DataFrame,
    show_heatmap: bool = True,
) -> folium.Map:
    """Build an interactive map centered in Cali with accident markers."""
    crash_map = folium.Map(
        location=CALI_CENTER,
        zoom_start=12,
        tiles="CartoDB positron",
        control_scale=True,
    )

    if accidents.empty:
        return crash_map

    if show_heatmap:
        heat_points = accidents[["latitud", "longitud"]].dropna().values.tolist()
        HeatMap(
            heat_points,
            name="Densidad",
            radius=18,
            blur=14,
            min_opacity=0.25,
        ).add_to(crash_map)

    marker_cluster = MarkerCluster(name="Accidentes").add_to(crash_map)
    for accident in accidents.itertuples(index=False):
        popup = folium.Popup(
            _popup_html(
                comuna=str(accident.comuna),
                barrio=str(accident.barrio),
                tipo=str(accident.tipo_accidente),
                gravedad=str(accident.gravedad),
                fecha=str(accident.fecha.date()),
                hora=str(accident.hora),
            ),
            max_width=280,
        )
        folium.CircleMarker(
            location=(float(accident.latitud), float(accident.longitud)),
            radius=5,
            color="#b91c1c",
            fill=True,
            fill_color="#ef4444",
            fill_opacity=0.72,
            popup=popup,
        ).add_to(marker_cluster)

    folium.LayerControl().add_to(crash_map)
    return crash_map


def _popup_html(
    comuna: str,
    barrio: str,
    tipo: str,
    gravedad: str,
    fecha: str,
    hora: str,
) -> str:
    safe_tipo = escape(tipo)
    safe_fecha = escape(fecha)
    safe_hora = escape(hora)
    safe_comuna = escape(comuna)
    safe_barrio = escape(barrio)
    safe_gravedad = escape(gravedad)

    return f"""
    <strong>{safe_tipo}</strong><br>
    Fecha: {safe_fecha} {safe_hora}<br>
    Comuna: {safe_comuna}<br>
    Barrio: {safe_barrio}<br>
    Gravedad: {safe_gravedad}
    """
