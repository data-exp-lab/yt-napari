import json

import pytest
import yt

from yt_napari import napari_get_reader

# the following should be a valid json, need to add some functionality to
# test infrastructure for loading an actual dataset... as is, this requires
# the IsolatedGalaxy file so will only pass locally.
valid_jdict = {
    "$schema": "yt-napari_0.0.1.json",
    "dataset": "IsolatedGalaxy/galaxy0030/galaxy0030",
    "field_type": "enzo",
    "field_name": "Density",
    "left_edge": [0.45, 0.45, 0.45],
    "right_edge": [0.55, 0.55, 0.55],
    "edge_units": "code_length",
    "resolution": [500, 500, 500],
    "take_log": False,
}


@pytest.fixture
def json_file_fixture(tmp_path):
    # write some fake data using your supported file format
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
def test_cannot_load_file():
    assert cannot_load_file("/this/file/does/not/exist")


def test_reader_identification(json_file_fixture):
    """tests that the plugin will succesfully identify a valid json"""
    # try to read it back in
    reader = napari_get_reader(json_file_fixture)
    assert callable(reader)


@pytest.mark.skipif(
    cannot_load_file(valid_jdict["dataset"]), reason="Cannot find test dataset"
)
def test_reader_load(json_file_fixture):
    # make sure we're delivering the right format

    # get the reader and then call it with the valid json
    reader = napari_get_reader(json_file_fixture)
    layer_data_list = reader(json_file_fixture)
    assert isinstance(layer_data_list, list) and len(layer_data_list) > 0
    layer_tuple = layer_data_list[0]
    assert isinstance(layer_tuple, tuple) and len(layer_tuple) > 0


def test_get_reader_pass():
    reader = napari_get_reader("fake.file")
    assert reader is None
