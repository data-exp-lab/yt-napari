import pytest

from yt_napari import _model_ingestor as mi
from yt_napari._data_model import InputModel
from yt_napari._schema_version import schema_name
from yt_napari._special_loaders import _construct_ugrid_timeseries

f_sel_dict = {
    "directory": "enzo_tiny_cosmology/",
    "file_list": ["DD0030/DD0030", "DD0045/DD0045"],
}

slice_dict = {
    "fields": [
        {
            "field_type": "stream",
            "field_name": "density",
        }
    ],
    "normal": "x",
    "center": {"value": [0.5, 0.5, 0.5], "unit": "code_length"},
    "slice_width": {"value": 0.25, "unit": "code_length"},
    "slice_height": {"value": 0.25, "unit": "code_length"},
    "resolution": [10, 10],
}

jdicts = []
jdicts.append(
    {
        "$schema": schema_name,
        "datasets": [],
        "timeseries": [
            {
                "file_selection": f_sel_dict,
                "selections": {
                    "slices": [
                        slice_dict,
                    ]
                },
                "load_as_stack": True,
            }
        ],
    }
)


@pytest.mark.parametrize("jdict", jdicts)
def test_basic_validation(jdict):
    _ = InputModel.parse_obj(jdict)


@pytest.mark.parametrize("jdict", jdicts)
def test_full_load(tmp_path, jdict):

    nfiles = 4

    fdir, flist = _construct_ugrid_timeseries(tmp_path, nfiles)

    f_dict = {"directory": fdir, "file_pattern": "_ytnapari_load_grid-????"}

    jdict_new = jdict.copy()
    jdict_new["timeseries"][0]["file_selection"] = f_dict
    im = InputModel.parse_obj(jdict_new)

    files = mi._find_timeseries_files(im.timeseries[0].file_selection)
    assert all([file in files for file in flist])

    _, ts_layers = mi._process_validated_model(im)
    assert ts_layers[0][0].shape == (nfiles,) + (10, 10)
