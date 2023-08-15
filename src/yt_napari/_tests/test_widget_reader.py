from functools import partial

import numpy as np

from yt_napari import _widget_reader as _wr
from yt_napari._ds_cache import dataset_cache

# import ReaderWidget, SelectionEntry, TimeSeriesReader
from yt_napari._special_loaders import _construct_ugrid_timeseries

# note: the cache is disabled for all the tests in this file due to flakiness
# in github CI. It may be that loading from a true file, rather than the
# yt_ugrid_ds_fn fixture would fix that...


def test_widget_reader_add_selections(make_napari_viewer, yt_ugrid_ds_fn):
    viewer = make_napari_viewer()
    r = _wr.ReaderWidget(napari_viewer=viewer)
    r.add_new_button.click()
    assert len(r.active_selections) == 1
    sel = list(r.active_selections.values())[0]
    assert isinstance(sel, _wr.SelectionEntry)
    assert sel.selection_type == "Region"
    sel.expand()
    sel.expand()
    r.layer_deletion_button.click()
    assert len(r.active_selections) == 0

    r.new_selection_type.setCurrentIndex(1)
    r.add_new_button.click()
    assert len(r.active_selections) == 1
    sel = list(r.active_selections.values())[0]
    assert isinstance(sel, _wr.SelectionEntry)
    assert sel.selection_type == "Slice"

    r.deleteLater()


def _rebuild_data(final_shape, data):
    # the yt file thats being loaded from the pytest fixture is a saved
    # dataset created from an in-memory uniform grid, and the re-loaded
    # dataset will not have the full functionality of a ds. so here, we
    # inject a correctly shaped random array here. If we start using full
    # test datasets from yt in testing, this should be changed.
    return np.random.random(final_shape) * data.mean()


def test_widget_reader(make_napari_viewer, yt_ugrid_ds_fn):

    viewer = make_napari_viewer()
    r = _wr.ReaderWidget(napari_viewer=viewer)
    r.ds_container.filename.value = yt_ugrid_ds_fn
    r.ds_container.store_in_cache.value = False
    r.add_new_button.click()
    sel = list(r.active_selections.values())[0]
    assert isinstance(sel, _wr.SelectionEntry)

    mgui_region = sel.selection_container_raw
    mgui_region.fields.field_type.value = "gas"
    mgui_region.fields.field_name.value = "density"
    mgui_region.resolution.value = (10, 10, 10)

    rebuild = partial(_rebuild_data, mgui_region.resolution.value)
    r._post_load_function = rebuild
    r.load_data()
    r.deleteLater()


def test_subsequent_load(make_napari_viewer, yt_ugrid_ds_fn):
    viewer = make_napari_viewer()

    r = _wr.ReaderWidget(napari_viewer=viewer)
    r.ds_container.filename.value = yt_ugrid_ds_fn
    r.ds_container.store_in_cache.value = False
    r.add_new_button.click()

    sel = list(r.active_selections.values())[0]
    assert isinstance(sel, _wr.SelectionEntry)

    mgui_region = sel.selection_container_raw
    mgui_region.fields.field_type.value = "gas"
    mgui_region.fields.field_name.value = "density"
    mgui_region.resolution.value = (10, 10, 10)

    rebuild = partial(_rebuild_data, mgui_region.resolution.value)
    r._post_load_function = rebuild
    r.load_data()

    # alter parameters, load again
    mgui_region.fields.field_name.value = "temperature"
    mgui_region.left_edge.value.value = (0.4, 0.4, 0.4)
    mgui_region.right_edge.value.value = (0.6, 0.6, 0.6)
    r.load_data()

    # the viewer should now have two images
    assert len(viewer.layers) == 2

    temp_layer = viewer.layers[1]
    assert temp_layer.metadata["_yt_napari_layer"] is True

    r.clear_cache()
    assert len(dataset_cache.available) == 0

    r.deleteLater()


def test_timeseries_widget_reader(make_napari_viewer, tmp_path):
    viewer = make_napari_viewer()
    _wr._use_threading = False
    nfiles = 4
    file_dir, flist_actual = _construct_ugrid_timeseries(tmp_path, nfiles)

    tsr = _wr.TimeSeriesReader(napari_viewer=viewer)

    tsr.ds_container.file_selection.directory.value = file_dir
    tsr.ds_container.file_selection.file_pattern.value = "_ytnapari_load_grid-????"
    tsr.ds_container.load_as_stack.value = True
    tsr.add_new_button.click()
    sel = list(tsr.active_selections.values())[0]
    assert isinstance(sel, _wr.SelectionEntry)

    mgui_region = sel.selection_container_raw
    mgui_region.fields.field_type.value = "stream"
    mgui_region.fields.field_name.value = "density"
    mgui_region.resolution.value = (10, 10, 10)

    tsr.load_data()
    assert len(viewer.layers) == 1

    viewer.layers.clear()
    tsr.ds_container.load_as_stack.value = False
    tsr.load_data()
    assert len(viewer.layers) == nfiles

    viewer.layers.clear()
    filestr_list = "_ytnapari_load_grid-0001, _ytnapari_load_grid-0002"
    tsr.ds_container.file_selection.file_list.value = filestr_list
    tsr.ds_container.file_selection.file_pattern.value = ""
    tsr.load_data()
    assert len(viewer.layers) == 2

    tsr.deleteLater()
