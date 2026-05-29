"""Folium map builders for Cali traffic crash records."""

import copy
import json
import math
import re
from collections.abc import Iterable
from html import escape
from pathlib import Path
from typing import Any

import folium
import pandas as pd
from branca.element import Element
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster

from src.config import CALI_CENTER, COMUNAS_GEOJSON_PATH


COMUNA_ZONE_COLORS = (
    "#38bdf8",
    "#22c55e",
    "#f59e0b",
    "#f97316",
    "#ef4444",
    "#a78bfa",
    "#14b8a6",
    "#eab308",
    "#f43f5e",
    "#60a5fa",
    "#84cc16",
    "#fb7185",
    "#2dd4bf",
    "#c084fc",
    "#facc15",
    "#34d399",
    "#fb923c",
    "#818cf8",
    "#4ade80",
    "#f472b6",
    "#67e8f9",
    "#c4b5fd",
)


def build_accident_map(
    accidents: pd.DataFrame,
    show_heatmap: bool = True,
    show_comuna_zones: bool = True,
    comunas_geojson_path: Path = COMUNAS_GEOJSON_PATH,
    max_markers: int | None = 20000,
) -> folium.Map:
    """Build an interactive map centered in Cali with accident markers."""
    crash_map = folium.Map(
        location=CALI_CENTER,
        zoom_start=12,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )
    _add_map_theme(crash_map)

    if show_comuna_zones:
        _add_comuna_zoning(crash_map, accidents, comunas_geojson_path)

    if accidents.empty:
        folium.LayerControl(collapsed=True).add_to(crash_map)
        return crash_map

    geocoded_accidents = accidents.dropna(subset=["latitud", "longitud"])
    if geocoded_accidents.empty:
        folium.LayerControl(collapsed=True).add_to(crash_map)
        return crash_map

    if show_heatmap:
        heat_points = geocoded_accidents[["latitud", "longitud"]].values.tolist()
        if heat_points:
            HeatMap(
                heat_points,
                name="Densidad",
                radius=24,
                blur=20,
                min_opacity=0.28,
                gradient={
                    0.18: "#6ec6e8",
                    0.42: "#4ade80",
                    0.68: "#d88a22",
                    0.86: "#f97316",
                    1.00: "#f06464",
                },
            ).add_to(crash_map)

    marker_cluster = MarkerCluster(name="Accidentes").add_to(crash_map)

    marker_data = geocoded_accidents
    if max_markers is not None and len(marker_data) > max_markers:
        marker_data = marker_data.sample(n=max_markers, random_state=42)

    for accident in marker_data.itertuples(index=False):
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
            radius=4.5,
            color="#0b1017",
            weight=1.2,
            fill=True,
            fill_color="#f1b35c",
            fill_opacity=0.9,
            popup=popup,
        ).add_to(marker_cluster)

    folium.LayerControl(collapsed=True).add_to(crash_map)
    return crash_map


def _add_map_theme(crash_map: folium.Map) -> None:
    """Attach dashboard-aligned styles to Leaflet controls and popups."""
    crash_map.get_root().header.add_child(
        Element(
            """
            <style>
            .leaflet-container {
                background: #0b1017;
                color: #f7f9fc;
                font-family: Inter, Segoe UI, sans-serif;
            }

            .leaflet-control-layers,
            .leaflet-bar a,
            .leaflet-control-scale-line {
                background: rgba(17, 24, 33, 0.94) !important;
                border: 1px solid rgba(166, 179, 199, 0.28) !important;
                color: #f7f9fc !important;
                box-shadow: 0 8px 22px rgba(0, 0, 0, 0.36) !important;
            }

            .leaflet-bar a {
                height: 32px !important;
                line-height: 30px !important;
                width: 32px !important;
            }

            .leaflet-control-layers {
                border-radius: 8px !important;
                padding: 0.35rem 0.45rem !important;
            }

            .leaflet-control-layers-expanded {
                min-width: 12rem;
            }

            .leaflet-control-layers label {
                color: #d7dee8;
                font-size: 12px;
                margin: 0.24rem 0;
            }

            .leaflet-control-layers-selector {
                accent-color: #d88a22;
                height: 14px;
                width: 14px;
            }

            .leaflet-popup-content-wrapper,
            .leaflet-popup-tip {
                background: #111821;
                border: 1px solid rgba(166, 179, 199, 0.26);
                color: #f7f9fc;
                box-shadow: 0 14px 30px rgba(0, 0, 0, 0.42);
            }

            .leaflet-popup-content {
                margin: 0;
            }

            .leaflet-tooltip {
                background: #111821;
                border: 1px solid rgba(166, 179, 199, 0.32);
                border-radius: 7px;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.34);
                color: #f7f9fc;
                font-size: 12px;
                padding: 0.42rem 0.55rem;
            }
            </style>
            """
        )
    )


def _add_comuna_zoning(
    crash_map: folium.Map,
    accidents: pd.DataFrame,
    geojson_path: Path,
) -> None:
    geojson_data = _load_comunas_geojson(geojson_path)
    if geojson_data is not None:
        _add_comuna_geojson_layer(crash_map, geojson_data, accidents)
        return

    _add_comuna_reference_layer(crash_map, accidents)


def _load_comunas_geojson(path: Path) -> dict[str, Any] | None:
    """Load a local Cali comunas GeoJSON if it exists and is valid."""
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as geojson_file:
            geojson_data = json.load(geojson_file)
    except (OSError, json.JSONDecodeError):
        return None

    if geojson_data.get("type") != "FeatureCollection":
        return None
    return geojson_data


def _add_comuna_geojson_layer(
    crash_map: folium.Map,
    geojson_data: dict[str, Any],
    accidents: pd.DataFrame,
) -> None:
    counts = _commune_counts(accidents)
    enriched_geojson = _enrich_comuna_geojson(geojson_data, counts)

    folium.GeoJson(
        enriched_geojson,
        name="Zonificación comunas",
        style_function=lambda feature: {
            "fillColor": feature["properties"].get("_fill_color", "#94a3b8"),
            "color": "#d7dee8",
            "weight": 1.25,
            "fillOpacity": 0.26,
        },
        highlight_function=lambda _: {
            "color": "#ffffff",
            "weight": 2.5,
            "fillOpacity": 0.42,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["COMUNA", "NOMBRE", "ACCIDENTES"],
            aliases=["Comuna", "Nombre", "Accidentes"],
            localize=True,
            sticky=False,
        ),
    ).add_to(crash_map)

    _add_comuna_labels(crash_map, enriched_geojson)


def _enrich_comuna_geojson(
    geojson_data: dict[str, Any],
    counts: dict[str, int],
) -> dict[str, Any]:
    enriched = copy.deepcopy(geojson_data)
    for feature in enriched.get("features", []):
        properties = feature.setdefault("properties", {})
        comuna = _normalize_comuna(properties.get("COMUNA"))
        properties["COMUNA"] = comuna
        properties["NOMBRE"] = properties.get("NOMBRE") or f"Comuna {comuna}"
        properties["ACCIDENTES"] = counts.get(comuna, 0)
        properties["_fill_color"] = _comuna_color(comuna)
    return enriched


def _add_comuna_labels(
    crash_map: folium.Map,
    geojson_data: dict[str, Any],
) -> None:
    label_group = folium.FeatureGroup(name="Etiquetas comunas", show=True)
    for feature in geojson_data.get("features", []):
        properties = feature.get("properties", {})
        location = _geometry_center(feature.get("geometry", {}))
        if location is None:
            continue

        comuna = escape(str(properties.get("COMUNA", "")))
        color = escape(str(properties.get("_fill_color", "#94a3b8")))
        folium.Marker(
            location=location,
            icon=folium.DivIcon(
                html=(
                    '<div style="'
                    f"background:{color};"
                    "border:1px solid rgba(15,23,42,.9);"
                    "border-radius:999px;"
                    "box-shadow:0 1px 6px rgba(0,0,0,.45);"
                    "color:#0f172a;"
                    "font:700 11px Inter,Segoe UI,sans-serif;"
                    "height:22px;"
                    "line-height:20px;"
                    "text-align:center;"
                    "width:22px;"
                    f'">C{comuna}</div>'
                ),
            ),
        ).add_to(label_group)

    label_group.add_to(crash_map)


def _add_comuna_reference_layer(
    crash_map: folium.Map,
    accidents: pd.DataFrame,
) -> None:
    if accidents.empty:
        return

    points = accidents.dropna(subset=["latitud", "longitud"]).copy()
    if points.empty:
        return

    points["comuna_key"] = points["comuna"].map(_normalize_comuna)
    grouped = (
        points.groupby("comuna_key", as_index=False)
        .agg(
            latitud=("latitud", "mean"),
            longitud=("longitud", "mean"),
            accidentes=("comuna", "size"),
        )
        .sort_values("comuna_key", key=lambda series: series.map(_comuna_sort_value))
    )

    zone_group = folium.FeatureGroup(
        name="Comunas (referencia por datos)",
        show=True,
    )
    for row in grouped.itertuples(index=False):
        color = _comuna_color(str(row.comuna_key))
        radius = min(24.0, 8.0 + math.sqrt(float(row.accidentes)) * 2.4)
        tooltip = f"Comuna {row.comuna_key}: {row.accidentes:,} accidentes"
        folium.CircleMarker(
            location=(float(row.latitud), float(row.longitud)),
            radius=radius,
            color="#e2e8f0",
            weight=1.4,
            fill=True,
            fill_color=color,
            fill_opacity=0.38,
            tooltip=tooltip,
        ).add_to(zone_group)
        folium.Marker(
            location=(float(row.latitud), float(row.longitud)),
            icon=folium.DivIcon(
                html=(
                    '<div style="'
                    f"background:{color};"
                    "border:1px solid rgba(15,23,42,.9);"
                    "border-radius:999px;"
                    "color:#0f172a;"
                    "font:700 11px Inter,Segoe UI,sans-serif;"
                    "height:22px;"
                    "line-height:20px;"
                    "text-align:center;"
                    "width:22px;"
                    f'">C{escape(str(row.comuna_key))}</div>'
                ),
            ),
        ).add_to(zone_group)

    zone_group.add_to(crash_map)


def _commune_counts(accidents: pd.DataFrame) -> dict[str, int]:
    if accidents.empty or "comuna" not in accidents:
        return {}

    counts = accidents["comuna"].map(_normalize_comuna).value_counts()
    return {str(comuna): int(count) for comuna, count in counts.items()}


def _normalize_comuna(value: object) -> str:
    text_value = str(value).strip()
    if not text_value or text_value.lower() in {"nan", "none", "<na>"}:
        return "Sin dato"

    match = re.search(r"\d+", text_value)
    if match is None:
        return text_value
    return str(int(match.group(0)))


def _comuna_sort_value(value: object) -> int:
    normalized = _normalize_comuna(value)
    return int(normalized) if normalized.isdigit() else 999


def _comuna_color(comuna: str) -> str:
    if not comuna.isdigit():
        return "#94a3b8"
    return COMUNA_ZONE_COLORS[(int(comuna) - 1) % len(COMUNA_ZONE_COLORS)]


def _geometry_center(geometry: dict[str, Any]) -> tuple[float, float] | None:
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        return None

    pairs = list(_coordinate_pairs(coordinates))
    if not pairs:
        return None

    longitude = sum(pair[0] for pair in pairs) / len(pairs)
    latitude = sum(pair[1] for pair in pairs) / len(pairs)
    return latitude, longitude


def _coordinate_pairs(coordinates: Iterable[Any]) -> Iterable[tuple[float, float]]:
    if _is_coordinate_pair(coordinates):
        coordinate_pair = list(coordinates)
        yield float(coordinate_pair[0]), float(coordinate_pair[1])
        return

    for item in coordinates:
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            yield from _coordinate_pairs(item)


def _is_coordinate_pair(value: object) -> bool:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return False

    items = list(value)
    if len(items) < 2:
        return False
    return isinstance(items[0], (int, float)) and isinstance(items[1], (int, float))


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
    <div style="font-family: Inter, Segoe UI, sans-serif; min-width: 210px; padding: 10px 12px;">
        <div style="color: #f7f9fc; font-weight: 700; font-size: 14px; margin-bottom: 6px;">
            {safe_tipo}
        </div>
        <div style="color: #a6b3c7; font-size: 12px; margin-bottom: 8px;">
            {safe_fecha} | {safe_hora}
        </div>
        <div style="color: #d7dee8; font-size: 12px; line-height: 1.45;">
            <div>Comuna <strong style="color: #f1b35c;">{safe_comuna}</strong></div>
            <div>Barrio: {safe_barrio}</div>
            <div>Gravedad: {safe_gravedad}</div>
        </div>
    </div>
    """
