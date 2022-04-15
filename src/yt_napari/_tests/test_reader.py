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
    "data": [
        {
            "filename": None,
            "selections": [
                {
                    "fields": [
                        {
                            "field_type": "gas",
                            "field_name": "density",
                            "take_log": False,
                        },
                        {
                            "field_type": "gas",
                            "field_name": "temperature",
                            "take_log": True,
                        },
                    ],
                    "resolution": [50, 50, 50],
                }
            ],
            "edge_units": "Mpc",
        }
    ],
}


@pytest.fixture
def json_file_fixture(tmp_path, yt_ugrid_ds_fn):
    # this fixture is the json file for napari to load, with
    # reference to the session-wide yt dataset
    valid_jdict["data"][0]["filename"] = yt_ugrid_ds_fn

    json_file = str(tmp_path / "valid_json.json")
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
    assert isinstance(layer_tuple[0][0], np.ndarray)
    assert "temperature" in layer_data_list[1][1]["name"]

    layer_data_list_2 = reader([json_file_fixture])
    layer_tuple_2 = layer_data_list_2[0]
    assert np.all(layer_tuple_2[0] == layer_tuple[0])


def test_invalid_schema(tmp_path, json_file_fixture):

    # test invalid schema
    with open(json_file_fixture) as jhandle:
        jdict = json.load(jhandle)

    # check that invlaid schema does not return a reader
    jdict["$schema"] = "unsupported_schema.json"
    json_file = str(tmp_path / "invalid_json.json")
    with open(json_file, "w") as fp:
        json.dump(jdict, fp)
    reader = napari_get_reader(json_file)
    assert reader is None

    # test that including one invalid raises a warning
    jpaths = [json_file_fixture, json_file]
    reader = napari_get_reader(jpaths)  # should succeed
    with pytest.raises(RuntimeWarning):
        _ = reader(jpaths)


def test_get_reader_pass():
    reader = napari_get_reader("fake.file")
    assert reader is None
