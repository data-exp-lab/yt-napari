import json

import numpy as np
import pytest
import yt

from yt_napari import napari_get_reader

# the following should be a valid json, need to add some functionality to
# test infrastructure for loading an actual dataset... as is, this requires
# the IsolatedGalaxy file so will only pass locally.
valid_jdict = {
    "$schema": "yt-napari_0.0.1.json",
    "dataset": None,
    "field_type": "gas",
    "field_name": "density",
    "resolution": [50, 50, 50],
    "take_log": False,
}


@pytest.fixture(scope="session")
def yt_ugrid_ds_fn(tmpdir_factory):

    # this fixture generates a random yt dataset saved to disk that can be
    # re-loaded and sampled.
    arr = np.random.random(size=(64, 64, 64))
    d = dict(density=(arr, "g/cm**3"))
    bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
    shp = arr.shape
    ds = yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)
    ad = ds.all_data()
    fn = str(tmpdir_factory.mktemp("data").join("uniform_grid_data.h5"))
    ad.save_as_dataset(fields=("stream", "density"), filename=fn)

    return fn


@pytest.fixture
def json_file_fixture(tmp_path, yt_ugrid_ds_fn):
    # this fixture is the json file for napari to load, with
    # reference to the session-wide yt dataset
    valid_jdict["dataset"] = yt_ugrid_ds_fn

    json_file = str(tmp_path / "valid_json.json")
    with open(json_file, "w") as fp:
        json.dump(valid_jdict, fp)
    return json_file


@pytest.fixture
def invalid_json_file_fixture(tmp_path, yt_ugrid_ds_fn):
    # this fixture is the json file for napari to load, with
    # reference to the session-wide yt dataset
    valid_jdict["dataset"] = yt_ugrid_ds_fn
    valid_jdict["$schema"] = "unsupported_schema.json"
    json_file = str(tmp_path / "invalid_json.json")
    with open(json_file, "w") as fp:
        json.dump(valid_jdict, fp)
    return json_file


def cannot_load_file(dataset_file: str) -> bool:
    # returns True if yt cannot load the provided file.
    # There may be a simpler way to handle this, perhaps something in the
    # testing module in yt.
    try:
        _ = yt.load(dataset_file)
        skip_test = False
    except FileNotFoundError:
        skip_test = True
    return skip_test


# tmp_path is a pytest fixture for a temporary directory
def test_cannot_load_file(yt_ugrid_ds_fn):
    assert cannot_load_file("/this/file/does/not/exist")
    assert cannot_load_file(yt_ugrid_ds_fn) is False


def test_reader_identification(json_file_fixture):
    """tests that the plugin will succesfully identify a valid json"""
    # try to read it back in
    reader = napari_get_reader(json_file_fixture)
    assert callable(reader)
    reader = napari_get_reader([json_file_fixture])
    assert callable(reader)


def test_reader_load(json_file_fixture):
    # make sure we're delivering the right format

    # get the reader and then call it with the valid json
    reader = napari_get_reader(json_file_fixture)
    layer_data_list = reader(json_file_fixture)
    assert isinstance(layer_data_list, list) and len(layer_data_list) > 0
    layer_tuple = layer_data_list[0]
    assert isinstance(layer_tuple, tuple) and len(layer_tuple) > 0

    with pytest.raises(NotImplementedError):
        _ = reader([json_file_fixture])  # lists not suported here


def test_invalid_schema(invalid_json_file_fixture):
    reader = napari_get_reader(invalid_json_file_fixture)
    assert reader is None


def test_get_reader_pass():
    reader = napari_get_reader("fake.file")
    assert reader is None
