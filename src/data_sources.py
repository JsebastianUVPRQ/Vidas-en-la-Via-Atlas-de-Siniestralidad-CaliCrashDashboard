"""Catalog and download helpers for external road safety datasets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


RAW_EXTERNAL_DIR = Path("data/raw/external")
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DataSource:
    """External source used to enrich crash and fatality analysis."""

    source_id: str
    title: str
    geography: str
    publisher: str
    landing_url: str
    download_url: str
    output_filename: str
    notes: str
    csv_separator: str = ","
    encoding: str = "utf-8"
    enabled_by_default: bool = True


DATA_SOURCES: tuple[DataSource, ...] = (
    DataSource(
        source_id="cali_siniestralidad_2016_2024",
        title="Siniestralidad en Santiago de Cali",
        geography="Cali",
        publisher="Secretaría de Movilidad de Cali",
        landing_url="https://datos.cali.gov.co/dataset/reporte-de-accidentes-segun-tipo-ano-2018-al-2020",
        download_url=(
            "https://datos.cali.gov.co/dataset/cb62a408-9029-4331-8815-ca2caeb126c0/"
            "resource/e0572389-cc41-4c1f-b443-862be10b6cc3/download/"
            "siniestralidad_2016_2024.csv"
        ),
        output_filename="cali_siniestralidad_2016_2024.csv",
        notes="Reporte amplio de accidentes y actores viales involucrados en Cali.",
        csv_separator=";",
        encoding="latin1",
    ),
    DataSource(
        source_id="cali_lesionados_2016_2025",
        title="Lesionados en accidentes de tránsito",
        geography="Cali",
        publisher="Secretaría de Movilidad de Cali",
        landing_url="https://datos.cali.gov.co/dataset/lesionados-en-accidentes-de-transito",
        download_url=(
            "https://datos.cali.gov.co/dataset/75c089ba-7df3-4816-b80f-c69c6e5362ae/"
            "resource/b5e009ef-8739-487d-bb0a-ffab613ce5cb/download/"
            "lesionados-en-santiago-de-cali-del-2016-2025.csv"
        ),
        output_filename="cali_lesionados_2016_2025.csv",
        notes="Personas lesionadas y tipo de actor vial en accidentes de Cali.",
        csv_separator=";",
        encoding="latin1",
    ),
    DataSource(
        source_id="cali_muertes_2016_2023",
        title="Consolidado de muertes en accidentes de tránsito en Cali",
        geography="Cali",
        publisher="Secretaría de Movilidad de Cali",
        landing_url=(
            "https://datos.cali.gov.co/dataset/"
            "datos-cali-gov-co-dataset-consolidado-muertes-accidentes-cali"
        ),
        download_url=(
            "https://datos.cali.gov.co/dataset/eeb7508e-1b84-4582-9676-43cf5d6ce443/"
            "resource/8629eb9b-10e2-464c-a4ac-87fa9efc453a/download/"
            "consolidado_muertes_en_accidente_de_ransito_2016_al_2023.csv"
        ),
        output_filename="cali_muertes_2016_2023.csv",
        notes="Víctimas fatales por actor vial en Cali.",
        csv_separator=";",
    ),
    DataSource(
        source_id="valle_candelaria_accidentalidad",
        title="Accidentalidad vial Municipio de Candelaria, Valle",
        geography="Candelaria, Valle del Cauca",
        publisher="Alcaldía de Candelaria",
        landing_url="https://www.datos.gov.co/Transporte/Accidentalidad-Vial-Municipio-de-Candelaria-Valle-/7wbf-88zm",
        download_url="https://www.datos.gov.co/resource/7wbf-88zm.csv?$limit=50000",
        output_filename="valle_candelaria_accidentalidad.csv",
        notes="Accidentes por clase, gravedad, vía, corregimiento, fecha y hora.",
    ),
    DataSource(
        source_id="valle_tulua_accidentalidad",
        title="Accidentalidad vehicular en el Municipio de Tuluá",
        geography="Tuluá, Valle del Cauca",
        publisher="Alcaldía de Tuluá",
        landing_url="https://www.datos.gov.co/Transporte/Accidentalidad-Vehicular-en-el-Municipio-de-Tulu-/ezt8-5wyj",
        download_url="https://www.datos.gov.co/resource/ezt8-5wyj.csv?$limit=50000",
        output_filename="valle_tulua_accidentalidad.csv",
        notes="Accidentes con coordenada, gravedad, vehículo y dirección del hecho.",
    ),
    DataSource(
        source_id="valle_palmira_accidentes_2022_2023",
        title="Accidentes de tránsito Palmira",
        geography="Palmira, Valle del Cauca",
        publisher="Alcaldía de Palmira",
        landing_url="https://www.datos.gov.co/Transporte/Accidentes-de-transito-Palmira/esbz-zavy",
        download_url="https://www.datos.gov.co/resource/esbz-zavy.csv?$limit=50000",
        output_filename="valle_palmira_accidentes_2022_2023.csv",
        notes="Accidentes en Palmira con coordenadas, hipótesis y variables de víctima.",
    ),
    DataSource(
        source_id="valle_palmira_siniestros_2024",
        title="Siniestros viales Palmira",
        geography="Palmira, Valle del Cauca",
        publisher="Alcaldía de Palmira",
        landing_url="https://www.datos.gov.co/Transporte/Siniestros-Viales-Palmira/sjpx-eqfp",
        download_url="https://www.datos.gov.co/resource/sjpx-eqfp.csv?$limit=50000",
        output_filename="valle_palmira_siniestros_2024.csv",
        notes="Siniestros viales de Palmira con vigencia 2024.",
    ),
    DataSource(
        source_id="runt_vehiculos_valle_ley2251",
        title="Vehículos involucrados en accidentes de tránsito Ley 2251 de 2022",
        geography="Valle del Cauca",
        publisher="Ministerio de Transporte",
        landing_url="https://www.datos.gov.co/d/6jmc-vaxk",
        download_url=(
            "https://www.datos.gov.co/resource/6jmc-vaxk.csv?"
            "$limit=50000&$where=departamento_accidente='VALLE%20DEL%20CAUCA'"
        ),
        output_filename="runt_vehiculos_valle_ley2251.csv",
        notes=(
            "Vista nacional filtrada a Valle del Cauca. Es granular por vehículo "
            "involucrado, no por siniestro único."
        ),
        enabled_by_default=False,
    ),
)


def get_source(source_id: str) -> DataSource:
    """Return one configured source by id."""
    for source in DATA_SOURCES:
        if source.source_id == source_id:
            return source
    raise KeyError(f"Fuente no configurada: {source_id}")


def selected_sources(
    source_ids: list[str] | None = None,
    include_optional: bool = False,
) -> list[DataSource]:
    """Resolve source ids into source definitions."""
    if source_ids:
        return [get_source(source_id) for source_id in source_ids]

    return [
        source
        for source in DATA_SOURCES
        if source.enabled_by_default or include_optional
    ]


def download_source(
    source: DataSource,
    output_dir: Path = RAW_EXTERNAL_DIR,
    force: bool = False,
) -> Path:
    """Download one external CSV source and write a sidecar metadata file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / source.output_filename
    if destination.exists() and not force:
        return destination

    request = Request(
        source.download_url,
        headers={"User-Agent": "CaliCrashDashboard data acquisition"},
    )
    partial = destination.with_suffix(destination.suffix + ".part")
    with urlopen(request, timeout=120) as response, partial.open("wb") as file:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            file.write(chunk)

    partial.replace(destination)
    _write_metadata(source, destination)
    return destination


def download_sources(
    sources: list[DataSource],
    output_dir: Path = RAW_EXTERNAL_DIR,
    force: bool = False,
) -> list[Path]:
    """Download several external sources."""
    return [
        download_source(source, output_dir=output_dir, force=force)
        for source in sources
    ]


def _write_metadata(source: DataSource, destination: Path) -> None:
    metadata = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "bytes": destination.stat().st_size,
        "source": asdict(source),
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
