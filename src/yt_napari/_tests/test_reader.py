import numpy as np
from yt_napari import napari_get_reader
import json


# the following should be a valid json, need to add some functionality to
# test infrastructure for loading an actual dataset... as is, this requires
# the IsolatedGalaxy file so will only pass locally.
valid_json_dict = {
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


# tmp_path is a pytest fixture
def test_reader(tmp_path):
    """An example of how you might test your plugin."""

    # write some fake data using your supported file format
    json_file = str(tmp_path / "valid_json.json")
    with open(json_file, 'w') as fp:
        json.dump(valid_json_dict, fp)


    # try to read it back in
    reader = napari_get_reader(json_file)
    assert callable(reader)

    # make sure we're delivering the right format
    layer_data_list = reader(json_file)
    assert isinstance(layer_data_list, list) and len(layer_data_list) > 0
    layer_data_tuple = layer_data_list[0]
    assert isinstance(layer_data_tuple, tuple) and len(layer_data_tuple) > 0


def test_get_reader_pass():
    reader = napari_get_reader("fake.file")
    assert reader is None
