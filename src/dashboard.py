"""Streamlit dashboard composition for Cali traffic crash analysis."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from src.config import DATA_CANDIDATES, TIME_BAND_ORDER
from src.etl import load_accident_data, normalize_accident_data
from src.mapa import build_accident_map
from src.metrics import (
    aggregate_by_comuna,
    aggregate_by_time_band,
    aggregate_by_weekday,
    build_kpis,
    filter_accidents,
)
from src.modelo import estimate_frequency


@dataclass(frozen=True)
class DashboardFilters:
    """Selected dashboard filters."""

    comunas: list[str]
    franjas_horarias: list[str]
    tipos_accidente: list[str]
    gravedades: list[str]
    date_range: tuple[date, date] | list[date] | None
    show_heatmap: bool


def render_dashboard() -> None:
    """Render the full Streamlit app."""
    st.set_page_config(
        page_title="Siniestralidad vial en Cali",
        page_icon="🚦",
        layout="wide",
    )

    st.title("Siniestralidad vial en Cali")
    uploaded_file = st.sidebar.file_uploader("CSV de accidentes", type=["csv"])
    accidents = _load_data(uploaded_file)

    if accidents.empty:
        st.warning("No hay registros válidos para visualizar.")
        st_folium(build_accident_map(accidents), use_container_width=True, height=560)
        return

    filters = _render_filters(accidents)
    filtered = filter_accidents(
        accidents,
        comunas=filters.comunas,
        franjas_horarias=filters.franjas_horarias,
        tipos_accidente=filters.tipos_accidente,
        gravedades=filters.gravedades,
        date_range=filters.date_range,
    )

    _render_kpis(filtered)
    _render_map_and_rankings(filtered, filters.show_heatmap)
    _render_temporal_views(filtered)
    _render_frequency_table(filtered)
    _render_download(filtered)


@st.cache_data(show_spinner=False)
def _load_data(uploaded_file: object | None) -> pd.DataFrame:
    if uploaded_file is not None:
        return normalize_accident_data(pd.read_csv(uploaded_file))
    return load_accident_data(DATA_CANDIDATES)


def _render_filters(accidents: pd.DataFrame) -> DashboardFilters:
    with st.sidebar:
        st.header("Filtros")

        comunas = _sorted_unique(accidents, "comuna")
        selected_comunas = st.multiselect("Comuna", comunas, default=comunas)

        available_bands = [
            band
            for band in TIME_BAND_ORDER
            if band in set(accidents["franja_horaria"].astype(str))
        ]
        selected_bands = st.multiselect(
            "Franja horaria",
            available_bands,
            default=available_bands,
        )

        tipos_accidente = _sorted_unique(accidents, "tipo_accidente")
        selected_types = st.multiselect(
            "Tipo de accidente",
            tipos_accidente,
            default=tipos_accidente,
        )

        gravedades = _sorted_unique(accidents, "gravedad")
        selected_severities = st.multiselect(
            "Gravedad",
            gravedades,
            default=gravedades,
        )

        min_date = accidents["fecha"].min().date()
        max_date = accidents["fecha"].max().date()
        selected_dates = st.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        show_heatmap = st.toggle("Mapa de calor", value=True)

    return DashboardFilters(
        comunas=selected_comunas,
        franjas_horarias=selected_bands,
        tipos_accidente=selected_types,
        gravedades=selected_severities,
        date_range=selected_dates,
        show_heatmap=show_heatmap,
    )


def _render_kpis(accidents: pd.DataFrame) -> None:
    kpis = build_kpis(accidents)
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Accidentes", f"{kpis.total_accidents:,}")
    kpi_cols[1].metric("Promedio diario", f"{kpis.daily_average:.1f}")
    kpi_cols[2].metric("Comuna crítica", kpis.top_comuna)
    kpi_cols[3].metric("Intersección crítica", kpis.top_intersection)


def _render_map_and_rankings(accidents: pd.DataFrame, show_heatmap: bool) -> None:
    map_col, chart_col = st.columns((2, 1))
    with map_col:
        st.subheader("Mapa")
        accident_map = build_accident_map(accidents, show_heatmap=show_heatmap)
        st_folium(accident_map, use_container_width=True, height=560)

    with chart_col:
        st.subheader("Comunas")
        by_comuna = aggregate_by_comuna(accidents).head(12)
        if by_comuna.empty:
            st.info("Sin datos para los filtros seleccionados.")
        else:
            fig = px.bar(
                by_comuna,
                x="accidentes",
                y="comuna",
                orientation="h",
                color="accidentes",
                color_continuous_scale="Reds",
                labels={"accidentes": "Accidentes", "comuna": "Comuna"},
            )
            fig.update_layout(
                height=320,
                margin={"l": 12, "r": 12, "t": 12, "b": 12},
                coloraxis_showscale=False,
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Franja horaria")
        by_band = aggregate_by_time_band(accidents)
        st.bar_chart(by_band, x="franja_horaria", y="accidentes")


def _render_temporal_views(accidents: pd.DataFrame) -> None:
    st.subheader("Patrones temporales")
    weekday_col, band_col = st.columns(2)

    with weekday_col:
        weekday_counts = aggregate_by_weekday(accidents)
        st.bar_chart(weekday_counts, x="dia_semana", y="accidentes")

    with band_col:
        daily_counts = (
            accidents.assign(dia=accidents["fecha"].dt.date)
            .groupby("dia")
            .size()
            .reset_index(name="accidentes")
        )
        st.line_chart(daily_counts, x="dia", y="accidentes")


def _render_frequency_table(accidents: pd.DataFrame) -> None:
    st.subheader("Frecuencia esperada")
    frequency = estimate_frequency(accidents)
    st.dataframe(
        frequency,
        hide_index=True,
        use_container_width=True,
        column_config={
            "frecuencia_diaria_esperada": st.column_config.NumberColumn(
                "Frecuencia diaria",
                format="%.2f",
            ),
            "intervalo_inferior": st.column_config.NumberColumn(
                "IC 95 % inf.",
                format="%.2f",
            ),
            "intervalo_superior": st.column_config.NumberColumn(
                "IC 95 % sup.",
                format="%.2f",
            ),
        },
    )


def _render_download(accidents: pd.DataFrame) -> None:
    st.download_button(
        "Descargar datos filtrados",
        data=accidents.to_csv(index=False).encode("utf-8"),
        file_name="accidentes_filtrados.csv",
        mime="text/csv",
    )


def _sorted_unique(data: pd.DataFrame, column: str) -> list[str]:
    return sorted(data[column].dropna().astype(str).unique())
