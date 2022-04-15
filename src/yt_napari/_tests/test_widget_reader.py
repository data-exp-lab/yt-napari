from functools import partial

import numpy as np

from yt_napari._widget_reader import ReaderWidget


def test_widget_reader(make_napari_viewer, yt_ugrid_ds_fn):

    # make_napari_viewer is a pytest fixture. It takes any keyword arguments
    # that napari.Viewer() takes. The fixture takes care of teardown, do **not**
    # explicitly close it!
    viewer = make_napari_viewer()

    r = ReaderWidget(napari_viewer=viewer)

    r.data_container.filename.value = yt_ugrid_ds_fn
    r.data_container.selections.fields.field_type.value = "gas"
    r.data_container.selections.fields.field_name.value = "density"
    res = (10, 10, 10)
    r.data_container.selections.resolution.value = res
    r.data_container.edge_units.value = "code_length"

    def rebuild_data(final_shape, data):
        # the yt file thats being loaded from the pytest fixture is a saved
        # dataset created from an in-memory uniform grid, and the re-loaded
        # dataset will not have the full functionality of a ds. so here, we
        # inject a correctly shaped random array here. If we start using full
        # test datasets from yt in testing, this should be changed.
        return np.random.random(final_shape) * data.mean()

    rebuild = partial(rebuild_data, res)
    r._post_load_function = rebuild
    r.load_data()

    r.data_container.selections.fields.field_name.value = "temperature"
    r.data_container.selections.left_edge.value = (0.4, 0.4, 0.4)
    r.data_container.selections.right_edge.value = (0.6, 0.6, 0.6)
    r.load_data()

    # the viewer should now have two images
    assert len(viewer.layers) == 2

    temp_layer = viewer.layers[1]
    assert temp_layer.metadata["_yt_napari_layer"] is True
