"""Streamlit dashboard composition for Cali traffic crash analysis."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.config import DATA_CANDIDATES, FATALITY_DATA_DIR, TIME_BAND_ORDER
from src.etl import build_sample_accidents, load_accident_data, normalize_accident_data
from src.fallecidos import (
    aggregate_fatalities_by_crash_class,
    aggregate_fatalities_by_time_range,
    aggregate_fatalities_by_year,
    build_fatality_kpis,
    load_fatality_data,
)
from src.insights import build_insights
from src.mapa import build_accident_map
from src.metrics import (
    aggregate_by_comuna,
    aggregate_by_hour,
    aggregate_by_time_band,
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
        page_title="Siniestralidad vial — Cali 2025",
        page_icon="🚦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_dashboard_css()

    uploaded_file = st.sidebar.file_uploader("CSV de accidentes", type=["csv"])
    accidents, raw_accidents = _load_data_with_raw(uploaded_file)
    fatalities = _load_fatalities()

    _render_header(accidents)
    if accidents.empty:
        st.warning("No hay registros válidos para visualizar.")
        st_folium(build_accident_map(accidents), use_container_width=True, height=560, key="mapa_vacio", returned_objects=[])
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

    _render_kpi_strip(filtered)
    _render_operations_view(filtered, filters.show_heatmap)
    _render_temporal_story(filtered)
    _render_fatalities_section(fatalities)
    _render_technical_detail(filtered, accidents, raw_accidents)


@st.cache_data(show_spinner=False)
def _load_data_with_raw(uploaded_file: object | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if uploaded_file is not None:
        raw = pd.read_csv(uploaded_file)
        return normalize_accident_data(raw), raw

    for path in DATA_CANDIDATES:
        if path.exists():
            suffix = path.suffix.lower()
            if suffix == ".parquet":
                raw = pd.read_parquet(path)
            else:
                raw = pd.read_csv(path)
            return normalize_accident_data(raw), raw

    sample = build_sample_accidents()
    return normalize_accident_data(sample), sample


@st.cache_data(show_spinner=False)
def _load_fatalities() -> pd.DataFrame:
    return load_fatality_data(FATALITY_DATA_DIR)


def _render_header(accidents: pd.DataFrame) -> None:
    min_date = accidents["fecha"].min().date() if not accidents.empty else "sin datos"
    max_date = accidents["fecha"].max().date() if not accidents.empty else "sin datos"
    st.markdown(
        f"""
        <section class="app-header">
            <div>
                <p class="eyebrow">Observatorio de movilidad urbana</p>
                <h1>Siniestralidad vial — Cali 2025</h1>
            </div>
            <div class="date-range">{min_date} · {max_date}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_filters(accidents: pd.DataFrame) -> DashboardFilters:
    with st.sidebar:
        st.markdown("### Filtros")

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


def _render_kpi_strip(accidents: pd.DataFrame) -> None:
    kpis = build_kpis(accidents)
    delta = _format_delta(kpis.weekly_trend_delta)
    cards = [
        ("Total accidentes", f"{kpis.total_accidents:,}", "Registros filtrados"),
        ("Comuna crítica", kpis.top_comuna, "Mayor concentración"),
        ("Hora crítica", kpis.critical_hour, "Pico observado"),
        ("Tendencia semanal", kpis.weekly_trend, delta),
    ]
    card_html = "".join(
        (
            '<article class="kpi-card">'
            f"<span>{label}</span>"
            f"<strong>{value}</strong>"
            f"<small>{caption}</small>"
            "</article>"
        )
        for label, value, caption in cards
    )
    st.markdown(
        f'<section class="kpi-strip">{card_html}</section>',
        unsafe_allow_html=True,
    )


def _render_operations_view(accidents: pd.DataFrame, show_heatmap: bool) -> None:
    map_col, insight_col = st.columns((2.35, 1), gap="large")
    with map_col:
        st.markdown(
            '<h2 class="section-title">Mapa operativo</h2>',
            unsafe_allow_html=True,
        )
        if len(accidents) > 1500:
            st.info(
                "💡 **Rendimiento:** Se muestra una muestra representativa de 1,500 marcadores individuales para "
                "evitar ralentizar el navegador, pero el mapa de calor y las estadísticas utilizan el 100% de los datos."
            )
        accident_map = build_accident_map(accidents, show_heatmap=show_heatmap)
        st_folium(accident_map, use_container_width=True, height=600, key="mapa_operativo", returned_objects=[])

    with insight_col:
        _render_insight_panel(accidents)
        _render_risk_rankings(accidents)


def _render_insight_panel(accidents: pd.DataFrame) -> None:
    insights = build_insights(accidents)
    st.markdown(
        '<h2 class="section-title">Lectura rápida</h2>',
        unsafe_allow_html=True,
    )
    if not insights:
        st.info("Sin datos suficientes para generar insights.")
        return

    for insight in insights:
        st.markdown(
            f'<div class="insight-item">{insight}</div>',
            unsafe_allow_html=True,
        )


def _render_risk_rankings(accidents: pd.DataFrame) -> None:
    st.markdown('<h3 class="panel-title">Top comunas</h3>', unsafe_allow_html=True)
    by_comuna = aggregate_by_comuna(accidents).head(5)
    if by_comuna.empty:
        st.info("Sin comunas para mostrar.")
    else:
        fig = px.bar(
            by_comuna.sort_values("accidentes"),
            x="accidentes",
            y="comuna",
            orientation="h",
            text="accidentes",
            labels={"accidentes": "Accidentes", "comuna": "Comuna"},
        )
        _style_bar_figure(fig, height=240)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<h3 class="panel-title">Franja horaria</h3>', unsafe_allow_html=True)
    by_band = aggregate_by_time_band(accidents)
    fig = px.bar(
        by_band,
        x="franja_horaria",
        y="accidentes",
        text="accidentes",
        labels={"accidentes": "Accidentes", "franja_horaria": ""},
    )
    _style_bar_figure(fig, height=220)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_temporal_story(accidents: pd.DataFrame) -> None:
    st.markdown(
        '<h2 class="section-title">Patrones temporales</h2>',
        unsafe_allow_html=True,
    )
    hour_col, day_col = st.columns(2, gap="large")

    with hour_col:
        hourly = aggregate_by_hour(accidents)
        fig = px.bar(
            hourly,
            x="hora_dia",
            y="accidentes",
            labels={"hora_dia": "Hora del día", "accidentes": "Accidentes"},
        )
        fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)))
        _style_bar_figure(fig, height=320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with day_col:
        daily = _daily_counts(accidents)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily["dia"],
                y=daily["accidentes"],
                mode="lines+markers",
                line={"color": "#f59e0b", "width": 3},
                marker={"color": "#f97316", "size": 7},
                fill="tozeroy",
                fillcolor="rgba(245, 158, 11, 0.12)",
            )
        )
        fig.update_layout(
            height=320,
            margin={"l": 8, "r": 8, "t": 12, "b": 8},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#d8dee9", "size": 12},
            yaxis_title="Accidentes",
            xaxis_title="Día",
            showlegend=False,
        )
        fig.update_xaxes(gridcolor="rgba(148, 163, 184, 0.16)")
        fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.16)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_fatalities_section(fatalities: pd.DataFrame) -> None:
    with st.expander("Mortalidad vial en Cali", expanded=False):
        if fatalities.empty:
            st.info("No hay registros de fallecidos para Cali en data/fallecidos.")
            return

        kpis = build_fatality_kpis(fatalities)
        fatality_cards = [
            ("Total Fallecidos", f"{kpis.total_fatalities:,}", "Registros históricos"),
            ("Año crítico", str(kpis.top_year), "Mayor mortalidad"),
            ("Horario crítico", str(kpis.top_time_range), "Franja de mayor riesgo"),
            ("Clase de siniestro", str(kpis.top_crash_class), "Tipo más frecuente"),
        ]
        card_html = "".join(
            (
                '<article class="kpi-card kpi-card-fatality">'
                f"<span>{label}</span>"
                f"<strong>{value}</strong>"
                f"<small>{caption}</small>"
                "</article>"
            )
            for label, value, caption in fatality_cards
        )
        st.markdown(
            f'<section class="kpi-strip fatality-strip">{card_html}</section>',
            unsafe_allow_html=True,
        )

        year_col, profile_col = st.columns(2, gap="large")
        with year_col:
            yearly = aggregate_fatalities_by_year(fatalities).sort_values("Año")
            fig = px.line(
                yearly,
                x="Año",
                y="fallecidos",
                markers=True,
                labels={"fallecidos": "Fallecidos"},
            )
            _style_line_figure(fig, height=300)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )

        with profile_col:
            by_time = aggregate_fatalities_by_time_range(fatalities).head(8)
            fig = px.bar(
                by_time.sort_values("fallecidos"),
                x="fallecidos",
                y="rango_3h",
                orientation="h",
                text="fallecidos",
                labels={"fallecidos": "Fallecidos", "rango_3h": ""},
            )
            _style_bar_figure(fig, height=300, color="#ef4444")
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )

        crash_class = aggregate_fatalities_by_crash_class(fatalities).head(10)
        st.dataframe(
            crash_class,
            hide_index=True,
            use_container_width=True,
            column_config={
                "clase_accidente": st.column_config.TextColumn("Clase de siniestro"),
                "fallecidos": st.column_config.ProgressColumn(
                    "Fallecidos",
                    format="%d",
                    min_value=0,
                    max_value=int(crash_class["fallecidos"].max()) if not crash_class.empty else 100,
                ),
            },
        )


def _render_technical_detail(filtered: pd.DataFrame, clean_full: pd.DataFrame, raw_full: pd.DataFrame) -> None:
    with st.expander("Ver detalle técnico y control de calidad", expanded=False):
        st.markdown("### Control de calidad de importación")
        from src.etl import data_quality_report
        quality = data_quality_report(raw_full, clean_full)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Registros cargados", f"{quality.total_raw:,}")
        col2.metric("Registros válidos", f"{quality.total_clean:,}")
        col3.metric("Fechas inválidas", f"{quality.null_fecha:,}")
        col4.metric("Coordenadas inválidas (o fuera de Cali)", f"{quality.null_coords + quality.out_of_bounds:,}")

        if quality.out_of_bounds > 0:
            st.caption(
                f"ℹ️ {quality.out_of_bounds:,} registros fueron filtrados por estar fuera de los límites geográficos de Cali."
            )

        st.write("---")
        st.markdown("### Frecuencia esperada por Comuna y Franja Horaria")
        frequency = estimate_frequency(filtered)
        st.dataframe(
            frequency,
            hide_index=True,
            use_container_width=True,
            column_config={
                "comuna": st.column_config.TextColumn("Comuna"),
                "franja_horaria": st.column_config.TextColumn("Franja Horaria"),
                "accidentes_observados": st.column_config.NumberColumn("Accidentes Observados", format="%d"),
                "dias_observados": st.column_config.NumberColumn("Días Observados", format="%d"),
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
                "nivel_riesgo": st.column_config.TextColumn("Nivel de Riesgo"),
            },
        )
        st.download_button(
            "Descargar datos filtrados (CSV)",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="accidentes_filtrados.csv",
            mime="text/csv",
        )


def _daily_counts(accidents: pd.DataFrame) -> pd.DataFrame:
    return (
        accidents.assign(dia=accidents["fecha"].dt.date)
        .groupby("dia")
        .size()
        .reset_index(name="accidentes")
    )


def _style_bar_figure(fig: go.Figure, height: int, color: str = "#7dd3fc") -> None:
    fig.update_traces(
        marker_color=color,
        marker_line_color="rgba(255,255,255,0)",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#d8dee9", "size": 12},
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="rgba(148, 163, 184, 0.16)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.10)", zeroline=False)


def _style_line_figure(fig: go.Figure, height: int) -> None:
    fig.update_traces(
        line={"color": "#ef4444", "width": 3},
        marker={"color": "#f87171", "size": 7},
    )
    fig.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#d8dee9", "size": 12},
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="rgba(148, 163, 184, 0.16)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.10)", zeroline=False)


def _format_delta(delta: float) -> str:
    if delta == 0:
        return "0% vs. periodo previo"
    return f"{delta:+.0f}% vs. periodo previo"


def _sorted_unique(data: pd.DataFrame, column: str) -> list[str]:
    return sorted(data[column].dropna().astype(str).unique())


def _inject_dashboard_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        :root {
            --bg: #0b0f14;
            --panel: #111820;
            --panel-soft: #151d27;
            --line: rgba(148, 163, 184, 0.18);
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #f59e0b;
            --risk: #ef4444;
            --data: #7dd3fc;
        }

        .stApp, .stApp label, .stApp p, .stApp h1, .stApp h2, .stApp h3 {
            font-family: 'Outfit', sans-serif !important;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1480px;
            padding: 2rem 2.2rem 3rem;
        }

        [data-testid="stSidebar"] {
            background: #171b24;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            padding: 0.7rem;
            min-height: 5.5rem;
            border: 1px solid var(--line);
            background: #0f141b;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            font-size: 0.82rem;
        }

        [data-baseweb="tag"] {
            background: rgba(245, 158, 11, 0.16) !important;
            color: #ffedd5 !important;
            border-radius: 6px !important;
            min-height: 1.45rem !important;
        }

        .app-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .eyebrow {
            color: var(--accent);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0;
            margin: 0 0 0.2rem;
            text-transform: uppercase;
        }

        .app-header h1 {
            color: var(--text);
            font-size: 1.95rem;
            line-height: 1.1;
            margin: 0;
        }

        .date-range {
            color: var(--muted);
            font-size: 0.9rem;
            padding-bottom: 0.22rem;
        }

        .kpi-strip {
            position: sticky;
            top: 0;
            z-index: 5;
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            padding: 0.75rem 0;
            margin-bottom: 0.8rem;
            background: rgba(11, 15, 20, 0.94);
            backdrop-filter: blur(12px);
        }

        .kpi-card {
            background: linear-gradient(180deg, var(--panel-soft), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.78rem 0.9rem;
            min-height: 5rem;
            transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.22s, box-shadow 0.22s;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(245, 158, 11, 0.35);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
        }

        .kpi-card-fatality {
            border-left: 3px solid var(--risk) !important;
        }

        .kpi-card-fatality:hover {
            border-color: rgba(239, 68, 68, 0.35);
            box-shadow: 0 6px 16px rgba(239, 68, 68, 0.08);
        }

        .kpi-card-fatality strong {
            color: #fca5a5 !important;
        }

        .fatality-strip {
            position: static !important;
            backdrop-filter: none !important;
            background: transparent !important;
            padding: 0 0 1rem 0 !important;
            margin-bottom: 0.5rem !important;
        }

        .kpi-card span,
        .kpi-card small {
            display: block;
            color: var(--muted);
            font-size: 0.78rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .kpi-card strong {
            display: block;
            color: var(--text);
            font-size: 1.55rem;
            line-height: 1.25;
            margin: 0.2rem 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .section-title {
            color: var(--text);
            font-size: 1.05rem;
            line-height: 1.2;
            margin: 0.3rem 0 0.7rem;
        }

        .panel-title {
            color: var(--text);
            font-size: 0.9rem;
            margin: 1rem 0 0.2rem;
        }

        .insight-item {
            background: var(--panel);
            border: 1px solid var(--line);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            color: #e5e7eb;
            font-size: 0.9rem;
            line-height: 1.38;
            margin-bottom: 0.65rem;
            padding: 0.78rem 0.85rem;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
        }

        .stButton button,
        .stDownloadButton button {
            background: var(--accent);
            border: 0;
            color: #111827;
            border-radius: 7px;
            font-weight: 700;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .stButton button:hover,
        .stDownloadButton button:hover {
            opacity: 0.9;
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.25);
        }

        @media (max-width: 900px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding: 1.2rem 1rem 2rem;
            }

            .app-header {
                align-items: flex-start;
                flex-direction: column;
            }

            .kpi-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
