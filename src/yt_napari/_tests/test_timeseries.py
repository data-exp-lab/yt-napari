import os.path

import numpy as np
import pytest
import yt
from yt.config import ytcfg

from yt_napari import _data_model as dm, _model_ingestor as mi, timeseries as ts


@pytest.fixture(scope="module")
def yt_ds_0():
    # this fixture generates a random yt dataset saved to disk that can be
    # re-loaded and sampled.
    arr = np.random.random(size=(16, 16, 16))
    d = dict(density=(arr, "g/cm**3"), temperature=(arr, "K"))
    bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
    shp = arr.shape
    ds = yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)
    return ds


def _construct_ugrid_timeseries(top_dir, nfiles):
    ts_dir = top_dir / "output_dir"
    ts_dir.mkdir()

    flist_actual = []
    for tstep in range(0, nfiles):
        tstepstr = str(tstep).zfill(4)
        fname = f"_ytnapari_load_grid-{tstepstr}"
        newfi = ts_dir / fname
        newfi.touch()

        flist_actual.append(str(newfi))
    return str(ts_dir), flist_actual


def test_timeseries_file_collection(tmp_path):

    nfiles = 8
    file_dir, flist_actual = _construct_ugrid_timeseries(tmp_path, nfiles)

    tfs = dm.TimeSeriesFileSelection(
        file_pattern="_ytnapari_load_grid-????",
        directory=file_dir,
        # file_list=file_list,
        # file_range=file_range,
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles
    assert all([fi in flist_actual for fi in files])

    tfs = dm.TimeSeriesFileSelection(
        directory=file_dir,
        file_list=flist_actual,
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles
    assert all([fi in flist_actual for fi in files])

    tfs = dm.TimeSeriesFileSelection(
        file_pattern="_ytnapari_load_grid-????",
        directory=file_dir,
        file_range=(0, nfiles, 2),
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles / 2


_field = ("stream", "density")


def test_region(yt_ds_0):
    sample_res = (20, 20, 20)
    reg = ts.Region(_field, resolution=sample_res)
    data = reg.sample_ds(yt_ds_0)
    assert data.shape == sample_res

    reg2 = ts.Region(
        _field,
        left_edge=yt_ds_0.domain_left_edge,
        right_edge=yt_ds_0.domain_right_edge,
        resolution=sample_res,
    )

    data2 = reg2.sample_ds(yt_ds_0)
    assert np.all(data == data2)

    le = np.array([-1.5, -1.5, -1.5])
    re = np.array([1.5, 1.5, 1.5])

    reg3 = ts.Region(
        _field, left_edge=(le, "Mpc"), right_edge=(re, "Mpc"), resolution=sample_res
    )

    data3 = reg3.sample_ds(yt_ds_0)
    assert np.all(data == data3)

    assert reg3._requires_scale is False
    assert np.all(reg3._scale == 1.0)

    reg4 = ts.Region(_field, resolution=sample_res, take_log=False)
    data4 = reg4.sample_ds(yt_ds_0)
    assert np.all(np.log10(data4) == data)


def test_slice(yt_ds_0):
    sample_res = (20, 20)
    slc = ts.Slice(_field, "x", resolution=sample_res)

    data = slc.sample_ds(yt_ds_0)
    assert data.shape == sample_res

    slc2 = ts.Slice(
        _field,
        "x",
        resolution=sample_res,
        center=(np.zeros((3,)), "Mpc"),
        width=(3.0, "Mpc"),
        height=(3.0, "Mpc"),
    )
    data2 = slc2.sample_ds(yt_ds_0)
    assert np.all(data2 == data)

    slc3 = ts.Slice(
        _field,
        "x",
        resolution=sample_res,
        center=yt_ds_0.domain_center,
        width=yt_ds_0.domain_width[1],
        height=yt_ds_0.domain_width[2],
    )
    data3 = slc3.sample_ds(yt_ds_0)
    assert np.all(data3 == data)


@pytest.mark.parametrize(
    "selection",
    [
        ts.Region(_field, resolution=(20, 20, 20)),
        ts.Slice(_field, "x", resolution=(20, 20)),
    ],
)
def test_timseries_selection(tmp_path, selection):

    nfiles = 4
    file_dir, flist_actual = _construct_ugrid_timeseries(tmp_path, nfiles)

    data = ts._load_and_sample(flist_actual[0], selection, False)
    assert data.shape == selection.resolution

    im_data, _, _ = ts._get_im_data(
        selection,
        file_dir=file_dir,
        file_pattern="_ytnapari_load_grid-????",
        load_as_stack=False,
    )

    assert len(im_data) == nfiles

    im_data, _, _ = ts._get_im_data(
        selection,
        file_dir=file_dir,
        file_pattern="_ytnapari_load_grid-????",
        load_as_stack=True,
    )

    assert im_data.shape == (nfiles,) + selection.resolution


@pytest.mark.parametrize(
    "selection",
    [
        ts.Region(_field, resolution=(20, 20, 20)),
        ts.Slice(_field, "x", resolution=(20, 20)),
    ],
)
def test_dask_selection(tmp_path, selection):
    ytcfg.set("yt", "store_parameter_files", False)
    nfiles = 4
    file_dir, flist_actual = _construct_ugrid_timeseries(tmp_path, nfiles)

    file_dir = os.path.abspath(file_dir)
    im_data2, _, _ = ts._get_im_data(
        selection,
        file_dir=file_dir,
        file_pattern="_ytnapari_load_grid-????",
        load_as_stack=True,
        use_dask=True,
    )

    # actually computing seems to have problems?
    # assert np.all(im_data2.compute() == im_data)
