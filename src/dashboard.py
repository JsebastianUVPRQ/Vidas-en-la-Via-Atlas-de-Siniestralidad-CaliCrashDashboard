"""Streamlit dashboard composition for Cali traffic crash analysis."""

from dataclasses import dataclass
from datetime import date
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.config import DATA_CANDIDATES, FATALITY_DATA_DIR, TIME_BAND_ORDER
from src.etl import build_sample_accidents, normalize_accident_data, read_csv_flexible
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


MONTH_ABBR_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


@dataclass(frozen=True)
class DashboardFilters:
    """Selected dashboard filters."""

    comunas: list[str]
    franjas_horarias: list[str]
    tipos_accidente: list[str]
    gravedades: list[str]
    date_range: tuple[date, date] | list[date] | None
    show_heatmap: bool
    show_comuna_zones: bool
    max_markers: int


@dataclass(frozen=True)
class TemporalSummary:
    """Narrative indicators for temporal accident patterns."""

    total_accidents: int
    daily_average: float
    critical_hour: str
    critical_hour_count: int
    critical_day: str
    critical_day_count: int
    daily_variation: str
    hourly_insight: str
    daily_insight: str


def render_dashboard() -> None:
    """Render the full Streamlit app."""
    st.set_page_config(
        page_title="Siniestralidad vial — Cali 2025",
        page_icon="🚦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_dashboard_css()

    _render_sidebar_source_note()
    accidents, raw_accidents = _load_data_with_raw()
    fatalities = _load_fatalities()

    _render_header(accidents)
    if accidents.empty:
        st.warning("No hay registros válidos para visualizar.")
        st_folium(
            build_accident_map(accidents),
            use_container_width=True,
            height=560,
            key="mapa_vacio",
            returned_objects=[],
        )
        return

    filters = _render_filter_bar(accidents)
    filtered = filter_accidents(
        accidents,
        comunas=filters.comunas,
        franjas_horarias=filters.franjas_horarias,
        tipos_accidente=filters.tipos_accidente,
        gravedades=filters.gravedades,
        date_range=filters.date_range,
    )

    _render_hero_insight(filtered)
    _render_kpi_strip(filtered)
    _render_operations_view(
        filtered,
        filters.show_heatmap,
        filters.show_comuna_zones,
        filters.max_markers,
    )
    _render_temporal_story(filtered)
    _render_fatalities_section(fatalities)
    _render_technical_detail(filtered, accidents, raw_accidents)


@st.cache_data(show_spinner=False)
def _load_data_with_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in DATA_CANDIDATES:
        if path.exists():
            suffix = path.suffix.lower()
            if suffix == ".parquet":
                raw = pd.read_parquet(path)
            else:
                raw = read_csv_flexible(path)
            return normalize_accident_data(raw), raw

    sample = build_sample_accidents()
    return normalize_accident_data(sample), sample


@st.cache_data(show_spinner=False)
def _load_fatalities() -> pd.DataFrame:
    return load_fatality_data(FATALITY_DATA_DIR)


def _render_sidebar_source_note() -> None:
    with st.sidebar:
        st.markdown("### Fuente de datos")
        st.caption("La aplicación usa únicamente los datos locales configurados.")


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


def _render_filter_bar(accidents: pd.DataFrame) -> DashboardFilters:
    st.markdown(
        '<section class="filter-heading"><span>Filtros de análisis</span></section>',
        unsafe_allow_html=True,
    )

    filter_cols = st.columns((1, 1.05, 1.45, 1.1, 1.45), gap="small")
    comunas = _sorted_unique(accidents, "comuna")
    with filter_cols[0]:
        selected_comunas = st.multiselect(
            "Comuna",
            comunas,
            default=[],
            placeholder="Todas",
        )

    available_bands = [
        band
        for band in TIME_BAND_ORDER
        if band in set(accidents["franja_horaria"].astype(str))
    ]
    with filter_cols[1]:
        selected_bands = st.multiselect(
            "Franja horaria",
            available_bands,
            default=[],
            placeholder="Todas",
        )

    tipos_accidente = _sorted_unique(accidents, "tipo_accidente")
    with filter_cols[2]:
        selected_types = st.multiselect(
            "Tipo de accidente",
            tipos_accidente,
            default=[],
            placeholder="Todos",
        )

    gravedades = _sorted_unique(accidents, "gravedad")
    with filter_cols[3]:
        selected_severities = st.multiselect(
            "Gravedad",
            gravedades,
            default=[],
            placeholder="Todas",
        )

    min_date = accidents["fecha"].min().date()
    max_date = accidents["fecha"].max().date()
    with filter_cols[4]:
        selected_dates = st.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    st.markdown(
        '<section class="filter-layer-heading"><span>Capas del mapa</span></section>',
        unsafe_allow_html=True,
    )
    layer_cols = st.columns((0.9, 1.05, 1.6, 2.4), gap="small")
    with layer_cols[0]:
        show_heatmap = st.toggle("Mapa de calor", value=True)
    with layer_cols[1]:
        show_comuna_zones = st.toggle("Comunas", value=True)
    with layer_cols[2]:
        geocoded_count = _geocoded_count(accidents)
        if geocoded_count > 500:
            max_markers = st.slider(
                "Marcadores",
                min_value=500,
                max_value=min(20000, geocoded_count),
                value=min(5000, geocoded_count),
                step=500,
            )
        else:
            max_markers = geocoded_count
            st.metric("Marcadores", f"{geocoded_count:,}")

    return DashboardFilters(
        comunas=selected_comunas,
        franjas_horarias=selected_bands,
        tipos_accidente=selected_types,
        gravedades=selected_severities,
        date_range=selected_dates,
        show_heatmap=show_heatmap,
        show_comuna_zones=show_comuna_zones,
        max_markers=max_markers,
    )


def _render_hero_insight(accidents: pd.DataFrame) -> None:
    kpis = build_kpis(accidents)
    insights = build_insights(accidents)
    primary_insight = insights[0] if insights else _empty_primary_insight(accidents)
    trend_class = _trend_class(kpis.weekly_trend)
    trend_label = _trend_copy(kpis.weekly_trend)

    st.markdown(
        f"""
        <section class="hero-insight">
            <div>
                <p class="hero-kicker">Lectura principal</p>
                <h2>{escape(primary_insight)}</h2>
            </div>
            <div class="hero-context">
                <span class="status-pill {trend_class}">{escape(trend_label)}</span>
                <strong>{escape(kpis.top_comuna)}</strong>
                <small>comuna con mayor concentración</small>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_strip(accidents: pd.DataFrame) -> None:
    kpis = build_kpis(accidents)
    delta = _format_delta(kpis.weekly_trend_delta)
    cards = [
        ("Total accidentes", f"{kpis.total_accidents:,}", "Registros filtrados", "primary"),
        ("Comuna crítica", kpis.top_comuna, "Mayor concentración", "neutral"),
        ("Hora crítica", kpis.critical_hour, "Pico observado", "neutral"),
        (
            "Tendencia semanal",
            _trend_copy(kpis.weekly_trend),
            delta,
            _trend_class(kpis.weekly_trend),
        ),
    ]
    card_html = "".join(
        (
            f'<article class="kpi-card kpi-card-{variant}">'
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(value)}</strong>"
            f"<small>{escape(caption)}</small>"
            "</article>"
        )
        for label, value, caption, variant in cards
    )
    st.markdown(
        f'<section class="kpi-strip">{card_html}</section>',
        unsafe_allow_html=True,
    )


def _render_operations_view(
    accidents: pd.DataFrame,
    show_heatmap: bool,
    show_comuna_zones: bool,
    max_markers: int,
) -> None:
    map_col, insight_col = st.columns((1.45, 1), gap="large")
    with map_col:
        st.markdown(
            '<div class="panel-heading"><h2>Mapa operativo</h2><span>Evidencia geográfica filtrada</span></div>',
            unsafe_allow_html=True,
        )
        geocoded_count = _geocoded_count(accidents)
        if geocoded_count > max_markers:
            st.info(
                f"💡 **Rendimiento:** Se muestran {max_markers:,} de {geocoded_count:,} marcadores georreferenciados. "
                "El mapa de calor y las estadísticas utilizan todos los puntos disponibles."
            )
        accident_map = build_accident_map(
            accidents,
            show_heatmap=show_heatmap,
            show_comuna_zones=show_comuna_zones,
            max_markers=max_markers,
        )
        st_folium(accident_map, use_container_width=True, height=600, key="mapa_operativo", returned_objects=[])

    with insight_col:
        _render_insight_panel(accidents)
        _render_risk_rankings(accidents)


def _geocoded_count(accidents: pd.DataFrame) -> int:
    if accidents.empty or {"latitud", "longitud"}.difference(accidents.columns):
        return 0
    return int(accidents[["latitud", "longitud"]].dropna().shape[0])


def _render_insight_panel(accidents: pd.DataFrame) -> None:
    insights = build_insights(accidents)
    st.markdown(
        '<div class="panel-heading"><h2>Lectura rápida</h2><span>Señales operativas</span></div>',
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown('<h3 class="panel-title">Franja horaria</h3>', unsafe_allow_html=True)
    by_band = aggregate_by_time_band(accidents)
    if by_band.empty:
        st.info("Sin franjas horarias para mostrar.")
    else:
        fig = px.bar(
            by_band,
            x="franja_horaria",
            y="accidentes",
            text="accidentes",
            labels={"accidentes": "Accidentes", "franja_horaria": ""},
        )
        _style_bar_figure(fig, height=220)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_temporal_story(accidents: pd.DataFrame) -> None:
    st.markdown(
        '<div class="panel-heading temporal-heading"><h2>Patrones temporales</h2><span>Distribución diaria y horaria</span></div>',
        unsafe_allow_html=True,
    )
    hourly = aggregate_by_hour(accidents)
    daily = _daily_counts(accidents)
    summary = _build_temporal_summary(accidents, hourly, daily)
    _render_temporal_kpis(summary)

    trend_col, hour_col = st.columns((1.35, 1), gap="large")

    with trend_col:
        st.markdown(
            '<h3 class="panel-title">Tendencia diaria</h3>',
            unsafe_allow_html=True,
        )
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
        max_daily = max(int(daily["accidentes"].max()), 1) if not daily.empty else 1
        fig.update_layout(
            height=260,
            yaxis_title="Accidentes",
            xaxis_title="Día",
        )
        _apply_plot_theme(fig)
        fig.update_xaxes(
            tickformat="%d/%m",
            ticklabelmode="period",
            nticks=min(len(daily), 6) if not daily.empty else 3,
        )
        fig.update_yaxes(
            range=[0, max_daily * 1.18],
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        _render_chart_note(summary.daily_insight, "daily-insight")

    with hour_col:
        st.markdown(
            '<h3 class="panel-title">Distribución por hora</h3>',
            unsafe_allow_html=True,
        )
        fig = px.bar(
            hourly,
            x="hora_dia",
            y="accidentes",
            labels={"hora_dia": "Hora", "accidentes": "Accidentes"},
        )
        fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 4)))
        _style_bar_figure(fig, height=260)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        _render_chart_note(summary.hourly_insight, "hourly-insight")


def _render_fatalities_section(fatalities: pd.DataFrame) -> None:
    with st.expander("Mortalidad vial en Cali", expanded=False):
        if fatalities.empty:
            _render_empty_state(
                "No se encontraron registros de mortalidad para Cali.",
                [
                    "Verificar que el archivo de mortalidad esté cargado.",
                    "Revisar el rango temporal disponible.",
                    "Restablecer filtros o cambiar la zona analizada.",
                ],
            )
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
                width="stretch",
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
                width="stretch",
                config={"displayModeBar": False},
            )

        crash_class = aggregate_fatalities_by_crash_class(fatalities).head(10)
        st.dataframe(
            crash_class,
            hide_index=True,
            width="stretch",
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
            width="stretch",
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
        accidents.assign(dia=accidents["fecha"].dt.floor("D"))
        .groupby("dia")
        .size()
        .reset_index(name="accidentes")
    )


def _build_temporal_summary(
    accidents: pd.DataFrame,
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
) -> TemporalSummary:
    total = len(accidents)
    if total == 0 or daily.empty:
        return TemporalSummary(
            total_accidents=0,
            daily_average=0.0,
            critical_hour="Sin datos",
            critical_hour_count=0,
            critical_day="Sin datos",
            critical_day_count=0,
            daily_variation="Sin tendencia",
            hourly_insight="No hay accidentes para interpretar con los filtros actuales.",
            daily_insight="No hay registros diarios para analizar en el periodo seleccionado.",
        )

    critical_hour_row = hourly.sort_values(
        ["accidentes", "hora_dia"],
        ascending=[False, True],
    ).iloc[0]
    critical_hour = int(critical_hour_row["hora_dia"])
    critical_hour_count = int(critical_hour_row["accidentes"])

    critical_day_row = daily.sort_values(
        ["accidentes", "dia"],
        ascending=[False, True],
    ).iloc[0]
    critical_day = pd.Timestamp(critical_day_row["dia"])
    critical_day_count = int(critical_day_row["accidentes"])
    daily_average = total / max(len(daily), 1)
    daily_variation = _daily_variation_label(daily)

    return TemporalSummary(
        total_accidents=total,
        daily_average=daily_average,
        critical_hour=f"{critical_hour:02d}:00",
        critical_hour_count=critical_hour_count,
        critical_day=_format_day_label(critical_day),
        critical_day_count=critical_day_count,
        daily_variation=daily_variation,
        hourly_insight=_hourly_insight(hourly, total),
        daily_insight=_daily_insight(daily, daily_average, daily_variation),
    )


def _render_temporal_kpis(summary: TemporalSummary) -> None:
    cards = [
        ("Accidentes", f"{summary.total_accidents:,}", "Registros filtrados"),
        ("Promedio diario", f"{summary.daily_average:.1f}", "Accidentes por día"),
        ("Hora crítica", summary.critical_hour, f"{summary.critical_hour_count} registros"),
        ("Día crítico", summary.critical_day, f"{summary.critical_day_count} registros"),
    ]
    card_html = "".join(
        (
            '<article class="temporal-kpi">'
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(value)}</strong>"
            f"<small>{escape(caption)}</small>"
            "</article>"
        )
        for label, value, caption in cards
    )
    st.markdown(
        f'<section class="temporal-kpi-strip">{card_html}</section>',
        unsafe_allow_html=True,
    )


def _render_chart_note(message: str, key: str) -> None:
    st.markdown(
        f'<div class="chart-note" data-note="{key}">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _render_empty_state(title: str, actions: list[str]) -> None:
    items = "".join(f"<li>{escape(action)}</li>" for action in actions)
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-badge">Info</div>
            <div>
                <strong>{escape(title)}</strong>
                <p>Esto no necesariamente indica un error de la aplicación.</p>
                <ul>{items}</ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empty_primary_insight(accidents: pd.DataFrame) -> str:
    if accidents.empty:
        return "No hay registros para interpretar con los filtros actuales."
    return "Los registros filtrados no muestran una concentración dominante."


def _hourly_insight(hourly: pd.DataFrame, total: int) -> str:
    if total == 0 or hourly.empty:
        return "No hay datos suficientes para identificar una concentración horaria."

    max_count = int(hourly["accidentes"].max())
    if max_count == 0:
        return "No hay datos suficientes para identificar una concentración horaria."

    active_hours = hourly[hourly["accidentes"].gt(0)]
    peak_hours = active_hours[active_hours["accidentes"].eq(max_count)]["hora_dia"].astype(int)
    share = max_count / total
    if len(peak_hours) > 3 or share < 0.2:
        return "La distribución horaria no presenta un patrón dominante; los eventos están dispersos durante el día."

    if len(peak_hours) == 1:
        hour = int(peak_hours.iloc[0])
        return f"La mayor frecuencia se observa a las {hour:02d}:00, con {max_count} accidentes registrados."

    formatted = ", ".join(f"{int(hour):02d}:00" for hour in peak_hours.tolist())
    return f"Las horas con mayor frecuencia son {formatted}, cada una con {max_count} accidentes registrados."


def _daily_insight(
    daily: pd.DataFrame,
    daily_average: float,
    daily_variation: str,
) -> str:
    if daily.empty:
        return "No hay registros diarios para analizar en el periodo seleccionado."

    max_row = daily.sort_values(["accidentes", "dia"], ascending=[False, True]).iloc[0]
    max_day = _format_day_label(pd.Timestamp(max_row["dia"]))
    max_count = int(max_row["accidentes"])
    if len(daily) == 1:
        return f"El periodo filtrado contiene un solo día: {max_day}, con {max_count} accidentes."

    return (
        f"La tendencia diaria se mantiene {daily_variation.lower()}; el máximo fue "
        f"{max_day} con {max_count} accidentes, frente a un promedio de {daily_average:.1f}."
    )


def _daily_variation_label(daily: pd.DataFrame) -> str:
    if len(daily) < 2:
        return "Sin tendencia"

    first = float(daily.iloc[0]["accidentes"])
    last = float(daily.iloc[-1]["accidentes"])
    if first == 0:
        delta = 100.0 if last > 0 else 0.0
    else:
        delta = ((last - first) / first) * 100

    if abs(delta) < 10:
        return "Estable"
    if delta > 0:
        return "Al alza"
    return "A la baja"


def _format_day_label(value: pd.Timestamp) -> str:
    month = MONTH_ABBR_ES.get(value.month, f"{value.month:02d}")
    return f"{value.day:02d} {month} {value.year}"


def _style_bar_figure(fig: go.Figure, height: int, color: str = "#7dd3fc") -> None:
    fig.update_traces(
        marker_color=color,
        marker_line_color="rgba(255,255,255,0)",
        textposition="outside",
        cliponaxis=False,
    )
    _apply_plot_theme(fig, height=height)


def _apply_plot_theme(fig: go.Figure, height: int | None = None) -> None:
    layout: dict[str, object] = {
        "margin": {"l": 8, "r": 8, "t": 12, "b": 8},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "#d7dee8", "size": 12, "family": "Outfit, sans-serif"},
        "showlegend": False,
    }
    if height is not None:
        layout["height"] = height
    fig.update_layout(
        **layout,
        hoverlabel={
            "bgcolor": "#121923",
            "bordercolor": "rgba(166, 179, 199, 0.28)",
            "font": {"color": "#f7f9fc", "family": "Outfit, sans-serif"},
        },
    )
    fig.update_xaxes(
        gridcolor="rgba(166, 179, 199, 0.14)",
        linecolor="rgba(166, 179, 199, 0.18)",
        tickfont={"color": "#a6b3c7", "size": 11},
        title_font={"color": "#c8d2df", "size": 12},
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor="rgba(166, 179, 199, 0.10)",
        linecolor="rgba(166, 179, 199, 0.18)",
        tickfont={"color": "#a6b3c7", "size": 11},
        title_font={"color": "#c8d2df", "size": 12},
        zeroline=False,
    )


def _style_line_figure(fig: go.Figure, height: int) -> None:
    fig.update_traces(
        line={"color": "#ef4444", "width": 3},
        marker={"color": "#f87171", "size": 7},
    )
    _apply_plot_theme(fig, height=height)


def _format_delta(delta: float) -> str:
    if delta == 0:
        return "Sin cambio vs. periodo previo"
    return f"{delta:+.0f}% vs. periodo previo"


def _trend_copy(trend: str) -> str:
    if trend == "Sin tendencia":
        return "Estable sin señal clara"
    return trend


def _trend_class(trend: str) -> str:
    if trend == "Al alza":
        return "risk"
    if trend == "A la baja":
        return "success"
    return "neutral"


def _sorted_unique(data: pd.DataFrame, column: str) -> list[str]:
    return sorted(data[column].dropna().astype(str).unique())


def _inject_dashboard_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        :root {
            --bg: #0b1017;
            --surface: #111821;
            --surface-2: #17212c;
            --surface-3: #1d2936;
            --line: rgba(166, 179, 199, 0.24);
            --line-strong: rgba(214, 224, 238, 0.34);
            --text: #f7f9fc;
            --text-soft: #d7dee8;
            --muted: #a6b3c7;
            --accent: #d88a22;
            --accent-soft: rgba(216, 138, 34, 0.16);
            --risk: #f06464;
            --success: #4ade80;
            --data: #6ec6e8;
            --focus: #f1b35c;
        }

        .stApp,
        .stApp label,
        .stApp p,
        .stApp h1,
        .stApp h2,
        .stApp h3 {
            font-family: 'Outfit', sans-serif !important;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1440px;
            padding: 1.25rem 2rem 3rem;
        }

        [data-testid="stSidebar"] {
            background: #111821;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            background: var(--surface-2);
            border: 1px solid var(--line);
            min-height: 5rem;
            padding: 0.8rem;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--text-soft);
            font-size: 0.88rem;
        }

        .app-header {
            align-items: flex-end;
            border-bottom: 1px solid var(--line);
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin-bottom: 0.9rem;
            padding-bottom: 0.85rem;
        }

        .eyebrow {
            color: var(--accent);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0;
            margin: 0 0 0.22rem;
            text-transform: uppercase;
        }

        .app-header h1 {
            color: var(--text);
            font-size: 1.82rem;
            line-height: 1.12;
            margin: 0;
        }

        .date-range {
            color: var(--text-soft);
            font-size: 0.94rem;
            padding-bottom: 0.12rem;
            white-space: nowrap;
        }

        .filter-heading {
            background: var(--surface);
            border: 1px solid var(--line);
            border-bottom: 0;
            border-radius: 8px 8px 0 0;
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            margin-top: 0.3rem;
            padding: 0.72rem 0.9rem 0.4rem;
            text-transform: uppercase;
        }

        div[data-testid="stHorizontalBlock"]:has([data-testid="stMultiSelect"]) {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 0 0 8px 8px;
            margin-bottom: 0;
            padding: 0.1rem 0.85rem 0.75rem;
        }

        .filter-layer-heading {
            background: var(--surface);
            border-left: 1px solid var(--line);
            border-right: 1px solid var(--line);
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 700;
            margin: 0;
            padding: 0 0.9rem 0.25rem;
            text-transform: uppercase;
        }

        div[data-testid="stHorizontalBlock"]:has([data-testid="stToggle"]) {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 0;
            border-radius: 0 0 8px 8px;
            margin-bottom: 0.9rem;
            padding: 0 0.85rem 0.68rem;
        }

        .stMultiSelect label,
        .stDateInput label,
        .stCheckbox label,
        [data-testid="stBaseButton-secondary"] {
            color: var(--text-soft) !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-testid="stDateInput"] input {
            background: #0d141d !important;
            border: 1px solid var(--line) !important;
            border-radius: 7px !important;
            color: var(--text) !important;
            min-height: 2.5rem !important;
        }

        [data-baseweb="select"] > div:hover,
        [data-baseweb="input"] > div:hover,
        [data-testid="stDateInput"] input:hover {
            border-color: var(--line-strong) !important;
        }

        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="input"] > div:focus-within,
        [data-testid="stDateInput"] input:focus {
            border-color: var(--focus) !important;
            box-shadow: 0 0 0 2px rgba(241, 179, 92, 0.16) !important;
        }

        [data-baseweb="tag"] {
            background: rgba(110, 198, 232, 0.14) !important;
            border: 1px solid rgba(110, 198, 232, 0.24) !important;
            border-radius: 6px !important;
            color: #dff5ff !important;
            min-height: 1.55rem !important;
        }

        [data-testid="stToggle"] {
            padding-top: 0;
        }

        [data-testid="stToggle"] label {
            min-height: 2.25rem;
        }

        .hero-insight {
            align-items: stretch;
            background: linear-gradient(135deg, #121b25, #17212c);
            border: 1px solid var(--line-strong);
            border-left: 4px solid var(--accent);
            border-radius: 8px;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin: 0.15rem 0 0.8rem;
            padding: 1rem 1.1rem;
        }

        .hero-kicker {
            color: var(--accent);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0;
            margin: 0 0 0.25rem;
            text-transform: uppercase;
        }

        .hero-insight h2 {
            color: var(--text);
            font-size: 1.42rem !important;
            line-height: 1.24;
            margin: 0;
        }

        .hero-context {
            align-items: flex-end;
            display: flex;
            flex: 0 0 15rem;
            flex-direction: column;
            justify-content: center;
            text-align: right;
        }

        .hero-context strong {
            color: var(--text);
            font-size: 1.8rem;
            line-height: 1.1;
            margin-top: 0.4rem;
        }

        .hero-context small {
            color: var(--muted);
            font-size: 0.83rem;
        }

        .kpi-strip {
            display: grid;
            grid-template-columns: 1.22fr repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            min-height: 5.6rem;
            padding: 0.82rem 0.95rem;
            transition: border-color 0.18s, background 0.18s, transform 0.18s;
        }

        .kpi-card:hover {
            background: var(--surface-2);
            border-color: var(--line-strong);
            transform: translateY(-1px);
        }

        .kpi-card-primary {
            background: linear-gradient(180deg, #182637, #121b25);
            border-color: rgba(216, 138, 34, 0.42);
        }

        .kpi-card-risk {
            border-left: 3px solid var(--risk);
        }

        .kpi-card-success {
            border-left: 3px solid var(--success);
        }

        .kpi-card-neutral {
            border-left: 3px solid rgba(166, 179, 199, 0.32);
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
            font-size: 0.84rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .kpi-card strong {
            display: block;
            color: var(--text);
            font-size: 1.58rem;
            line-height: 1.18;
            margin: 0.28rem 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .kpi-card-primary strong {
            font-size: 1.85rem;
        }

        .status-pill {
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.25rem 0.56rem;
        }

        .status-pill.risk {
            background: rgba(240, 100, 100, 0.14);
            color: #fecaca;
        }

        .status-pill.success {
            background: rgba(74, 222, 128, 0.12);
            color: #bbf7d0;
        }

        .status-pill.neutral {
            background: rgba(166, 179, 199, 0.14);
            color: var(--text-soft);
        }

        .panel-heading {
            align-items: flex-end;
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            margin: 0.35rem 0 0.55rem;
        }

        .panel-heading h2 {
            color: var(--text);
            font-size: 1.22rem !important;
            line-height: 1.2;
            margin: 0;
        }

        .panel-heading span {
            color: var(--muted);
            font-size: 0.83rem;
            text-align: right;
        }

        h3.panel-title {
            color: var(--text);
            font-size: 1.05rem !important;
            line-height: 1.2;
            margin: 0.75rem 0 0.2rem;
            padding: 0;
        }

        iframe[title="streamlit_folium.st_folium"] {
            border: 1px solid var(--line) !important;
            border-radius: 8px;
            overflow: hidden;
        }

        .temporal-kpi-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.65rem;
            margin: -0.2rem 0 0.5rem;
        }

        .temporal-kpi {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            min-height: 4.2rem;
            padding: 0.72rem 0.82rem;
        }

        .temporal-kpi span,
        .temporal-kpi small {
            display: block;
            color: var(--muted);
            font-size: 0.8rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .temporal-kpi strong {
            display: block;
            color: var(--text);
            font-size: 1.16rem;
            line-height: 1.2;
            margin: 0.16rem 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .chart-note {
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            color: var(--text-soft);
            font-size: 0.88rem;
            line-height: 1.35;
            margin: -0.05rem 0 0.7rem;
            padding: 0.62rem 0.72rem;
        }

        .chart-note[data-note="hourly-insight"] {
            border-left-color: var(--data);
        }

        .empty-state {
            display: flex;
            gap: 0.85rem;
            align-items: flex-start;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            color: var(--text-soft);
            margin: 0.75rem 0 0.15rem;
            padding: 0.9rem 1rem;
        }

        .empty-state-badge {
            flex: 0 0 auto;
            border: 1px solid rgba(125, 211, 252, 0.38);
            border-radius: 999px;
            color: #bae6fd;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.18rem 0.48rem;
            text-transform: uppercase;
        }

        .empty-state strong {
            color: var(--text);
            display: block;
            font-size: 0.94rem;
            margin-bottom: 0.2rem;
        }

        .empty-state p {
            color: var(--muted);
            font-size: 0.88rem;
            margin: 0 0 0.35rem;
        }

        .empty-state ul {
            color: var(--text-soft);
            font-size: 0.86rem;
            margin: 0;
            padding-left: 1rem;
        }

        .empty-state li {
            margin: 0.12rem 0;
        }

        .insight-item {
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 3px solid var(--data);
            border-radius: 8px;
            color: var(--text-soft);
            font-size: 0.94rem;
            line-height: 1.38;
            margin-bottom: 0.65rem;
            padding: 0.82rem 0.9rem;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface);
        }

        .stButton button,
        .stDownloadButton button {
            background: var(--accent);
            border: 0;
            color: #10151c;
            border-radius: 7px;
            font-weight: 700;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .stButton button:hover,
        .stDownloadButton button:hover {
            opacity: 0.9;
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(216, 138, 34, 0.24);
        }

        @media (max-width: 1100px) {
            div[data-testid="stHorizontalBlock"]:has([data-testid="stMultiSelect"]) {
                padding-bottom: 0.4rem;
            }

            .hero-insight {
                align-items: flex-start;
                flex-direction: column;
            }

            .hero-context {
                align-items: flex-start;
                flex: 0 0 auto;
                text-align: left;
            }

            .kpi-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 900px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding: 1.2rem 1rem 2rem;
            }

            .app-header {
                align-items: flex-start;
                flex-direction: column;
            }

            .temporal-kpi-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .empty-state {
                flex-direction: column;
            }
        }

        @media (max-width: 680px) {
            .app-header h1 {
                font-size: 1.5rem;
            }

            .hero-insight h2 {
                font-size: 1.16rem !important;
            }

            .kpi-strip,
            .temporal-kpi-strip {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
