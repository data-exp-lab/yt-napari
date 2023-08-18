import numpy as np
import pytest

from yt_napari import _model_ingestor as mi
from yt_napari._data_model import InputModel
from yt_napari._schema_version import schema_name
from yt_napari._special_loaders import _construct_ugrid_timeseries

f_sel_dict = {
    "directory": "enzo_tiny_cosmology/",
    "file_list": ["DD0030/DD0030", "DD0045/DD0045"],
    "file_range": (0, 10, 1),
}

fields_to_load = [
    {
        "field_type": "stream",
        "field_name": "density",
    },
    {
        "field_type": "stream",
        "field_name": "temperature",
    },
]

slice_dict = {
    "fields": fields_to_load,
    "normal": "x",
    "center": {"value": [0.5, 0.5, 0.5], "unit": "code_length"},
    "slice_width": {"value": 0.25, "unit": "code_length"},
    "slice_height": {"value": 0.25, "unit": "code_length"},
    "resolution": [10, 10],
}

reg_dict = {
    "fields": fields_to_load,
    "resolution": [10, 10, 10],
}

jdicts = []
jdicts.append(
    {
        "$schema": schema_name,
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
jdicts.append(
    {
        "$schema": schema_name,
        "datasets": [],
        "timeseries": [
            {
                "file_selection": f_sel_dict,
                "selections": {
                    "regions": [
                        reg_dict,
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


@pytest.mark.parametrize("jdict,expected_res", zip(jdicts, [(10, 10), (10, 10, 10)]))
def test_full_load(tmp_path, jdict, expected_res):

    nfiles = 4

    fdir, flist = _construct_ugrid_timeseries(tmp_path, nfiles)

    f_dict = {"directory": fdir, "file_pattern": "_ytnapari_load_grid-????"}

    jdict_new = jdict.copy()
    jdict_new["timeseries"][0]["file_selection"] = f_dict
    im = InputModel.parse_obj(jdict_new)

    files = mi._find_timeseries_files(im.timeseries[0].file_selection)
    assert all([file in files for file in flist])

    _, ts_layers = mi._process_validated_model(im)
    assert ts_layers[0][0].shape == (nfiles,) + expected_res
    assert len(ts_layers) == 2  # two fields


@pytest.mark.parametrize("jdict", jdicts)
def test_unstacked_load(tmp_path, jdict):

    nfiles = 4
    fdir, flist = _construct_ugrid_timeseries(tmp_path, nfiles)

    f_dict = {"directory": fdir, "file_pattern": "_ytnapari_load_grid-????"}

    jdict_new = jdict.copy()
    jdict_new["timeseries"][0]["file_selection"] = f_dict
    jdict_new["timeseries"][0]["load_as_stack"] = False

    im = InputModel.parse_obj(jdict_new)
    _, ts_layers = mi._process_validated_model(im)
    assert len(ts_layers) == 2 * nfiles  # two fields per file


def test_load_with_timeseries_specials_check(yt_ugrid_ds_fn, tmp_path):
    nfiles = 4
    fdir, flist = _construct_ugrid_timeseries(tmp_path, nfiles)

    ds = mi._load_with_timeseries_specials_check(flist[0])
    assert hasattr(ds, "domain_center")

    with pytest.raises(AttributeError, match="The special loader"):
        _ = mi._load_with_timeseries_specials_check("_ytnapari_load_what-01")

    ds = mi._load_with_timeseries_specials_check(yt_ugrid_ds_fn)
    assert hasattr(ds, "domain_center")


def test_aspect_rat(tmp_path):
    nfiles = 4
    fdir, flist = _construct_ugrid_timeseries(tmp_path, nfiles)

    slice_1 = slice_dict.copy()
    slice_1["slice_width"] = {"value": 1.0, "unit": "code_length"}
    f_dict = {"directory": fdir, "file_pattern": "_ytnapari_load_grid-????"}
    jdict_ar = {
        "$schema": schema_name,
        "timeseries": [
            {
                "file_selection": f_dict,
                "selections": {
                    "slices": [
                        slice_1,
                    ]
                },
                "load_as_stack": True,
            }
        ],
    }

    im = InputModel.parse_obj(jdict_ar)
    _, ts_layers = mi._process_validated_model(im)
    for _, im_kwargs, _ in ts_layers:
        print(im_kwargs)
        assert np.sum(im_kwargs["scale"] != 1.0) > 0
