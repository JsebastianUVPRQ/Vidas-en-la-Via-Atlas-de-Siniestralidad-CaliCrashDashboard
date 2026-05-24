import json
from pathlib import Path

import pandas as pd

from src.mapa import build_accident_map


def _sample_accidents() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "hora": ["08:15", "21:30"],
            "latitud": [3.4516, 3.4206],
            "longitud": [-76.5320, -76.5222],
            "comuna": ["2", "19"],
            "barrio": ["Versalles", "San Fernando"],
            "tipo_accidente": ["Choque", "Atropello"],
            "gravedad": ["Solo daños", "Herido"],
        }
    )


def test_build_accident_map_adds_local_comuna_geojson(tmp_path: Path) -> None:
    geojson_path = tmp_path / "comunas.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"COMUNA": 2, "NOMBRE": "Comuna 2"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [-76.54, 3.44],
                                    [-76.52, 3.44],
                                    [-76.52, 3.46],
                                    [-76.54, 3.46],
                                    [-76.54, 3.44],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rendered = build_accident_map(
        _sample_accidents(),
        show_heatmap=False,
        comunas_geojson_path=geojson_path,
    ).get_root().render()

    assert "Zonificaci" in rendered
    assert "ACCIDENTES" in rendered


def test_build_accident_map_adds_reference_layer_without_geojson(
    tmp_path: Path,
) -> None:
    rendered = build_accident_map(
        _sample_accidents(),
        show_heatmap=False,
        comunas_geojson_path=tmp_path / "missing.geojson",
    ).get_root().render()

    assert "Comunas (referencia por datos)" in rendered
    assert "Comuna 2: 1 accidentes" in rendered
