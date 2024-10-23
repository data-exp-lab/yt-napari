import importlib.resources as importlib_resources
import json

import numpy as np

from yt_napari.sample_data import _generic_loader as gl


def test_generic_load_sample_data(tmp_path, monkeypatch):

    sample_name = "my_test"
    mock_ytnapari_path = tmp_path / "yt_napari"
    mock_ytnapari_path.mkdir()
    sample_dir = mock_ytnapari_path / "sample_data"
    sample_dir.mkdir()
    json_file = sample_dir / gl._get_sample_json(sample_name)

    jdict = {
        "datasets": [
            {
                "filename": "_ytnapari_load_grid",
                "selections": {
                    "regions": [
                        {
                            "fields": [{"field_name": "density", "field_type": "gas"}],
                            "resolution": [10, 10, 10],
                        }
                    ]
                },
            }
        ],
    }

    with open(json_file, "w") as fi:
        json.dump(jdict, fi)

    # now monkeypatch so that importlib_resources.files("yt_napari")
    # points to the tmp sample_dir
    def mock_importlib_files(package_name: str):
        return mock_ytnapari_path

    monkeypatch.setattr(importlib_resources, "files", mock_importlib_files)

    result = gl.load_sample_data(sample_name)
    assert isinstance(result[0][0], np.ndarray)
