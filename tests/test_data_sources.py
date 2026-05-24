from src.data_sources import DATA_SOURCES, get_source, selected_sources


def test_source_ids_are_unique() -> None:
    source_ids = [source.source_id for source in DATA_SOURCES]

    assert len(source_ids) == len(set(source_ids))


def test_sources_have_csv_outputs_and_urls() -> None:
    for source in DATA_SOURCES:
        assert source.output_filename.endswith(".csv")
        assert source.download_url.startswith("https://")
        assert source.landing_url.startswith("https://")


def test_selected_sources_excludes_optional_by_default() -> None:
    result = selected_sources()

    assert result
    assert all(source.enabled_by_default for source in result)


def test_get_source_returns_configured_source() -> None:
    result = get_source("cali_siniestralidad_2016_2024")

    assert result.geography == "Cali"
