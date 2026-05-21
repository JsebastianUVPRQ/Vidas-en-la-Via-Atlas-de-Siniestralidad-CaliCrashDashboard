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
            radius=20,
            blur=18,
            min_opacity=0.18,
            gradient={
                0.20: "#38bdf8",
                0.45: "#22c55e",
                0.70: "#f59e0b",
                1.00: "#ef4444",
            },
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
            radius=4,
            color="#0f172a",
            weight=1,
            fill=True,
            fill_color="#f59e0b",
            fill_opacity=0.84,
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
    <div style="font-family: Inter, Segoe UI, sans-serif; min-width: 190px;">
        <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px;">
            {safe_tipo}
        </div>
        <div style="color: #475569; font-size: 12px; margin-bottom: 6px;">
            {safe_fecha} · {safe_hora}
        </div>
        <div style="font-size: 12px;">Comuna <strong>{safe_comuna}</strong></div>
        <div style="font-size: 12px;">Barrio: {safe_barrio}</div>
        <div style="font-size: 12px;">Gravedad: {safe_gravedad}</div>
    </div>
    """
