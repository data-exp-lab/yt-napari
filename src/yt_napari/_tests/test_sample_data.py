import importlib.resources as importlib_resources
import json

import numpy as np
import pytest
import yt

from yt_napari import _ds_cache
from yt_napari._types import Layer
from yt_napari.sample_data import _generic_loader as gl, _sample_data as sd


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


# @pytest.mark.skip(reason="monkey not patching :/")
def test_sample_data_loaders(monkeypatch):

    # first, figure out how many loaders we have
    loaders = [attr for attr in dir(sd) if attr.startswith("sample_")]

    def mock_generic_loader(sample_name: str) -> list[Layer]:
        return [(np.zeros((10, 10, 10)), {}, sample_name)]

    enabled_samples = _ds_cache.get_sample_set_list()
    all_samples = []
    from yt_napari.sample_data import _generic_loader as gl

    monkeypatch.setattr(gl, "load_sample_data", mock_generic_loader)
    for loader in loaders:
        loader_func = getattr(sd, loader)
        assert callable(loader_func)
        result = loader_func()
        sample_name = result[0][-1]
        all_samples.append(sample_name)
        assert sample_name in enabled_samples

    # make sure every sample is represented
    assert set(all_samples) == set(enabled_samples)


def test_dataset_cache_samples(monkeypatch):
    dataset_cache = _ds_cache.dataset_cache
    assert len(dataset_cache.sample_sets) > 0

    def mock_load_sample(filename):
        return filename in dataset_cache.sample_sets

    monkeypatch.setattr(yt, "load_sample", mock_load_sample)
    for fname in dataset_cache.sample_sets:
        assert dataset_cache.check_then_load(fname)


def test_dataset_load_sample_deps(monkeypatch):
    from yt_napari import _utilities

    def dep_is_missing(dep: str) -> bool:
        return True

    monkeypatch.setattr(_utilities, "dependency_is_missing", dep_is_missing)

    with pytest.raises(ModuleNotFoundError, match="Loading sample data requires "):
        _ds_cache._load_sample("reallynicefilename")


def test_dependency_is_missing():
    from yt_napari import _utilities

    assert _utilities.dependency_is_missing("this_is_not_a_module")
    assert not _utilities.dependency_is_missing("yt_napari")
