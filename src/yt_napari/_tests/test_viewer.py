import numpy as np
import pytest
import yt
from napari.layers import Layer
from napari.layers.utils._link_layers import get_linked_layers

from yt_napari.viewer import Scene


@pytest.fixture
def yt_ds():
    return yt.testing.fake_amr_ds(fields=("density", "mass"), units=("kg/m**3", "kg"))


def test_viewer(make_napari_viewer, yt_ds):

    # make_napari_viewer is a pytest fixture. It takes any keyword arguments
    # that napari.Viewer() takes. The fixture takes care of teardown, do **not**
    # explicitly close it!
    viewer = make_napari_viewer()

    # also note that building the viewer takes a few seconds so all tests here
    # are in a single function.

    ####################
    # test add_to_viewer
    sc = Scene()
    res = (10, 10, 10)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), resolution=res)

    expected_layers = 1
    assert len(viewer.layers) == expected_layers

    with pytest.warns(RuntimeWarning):
        sc.add_to_viewer(
            viewer, yt_ds, ("gas", "density"), translate=10, resolution=res
        )
    with pytest.warns(RuntimeWarning):
        sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), scale=10, resolution=res)
    expected_layers += 2  # the above will add layers!
    assert len(viewer.layers) == expected_layers

    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), resolution=res)
    expected_layers += 1
    assert len(viewer.layers) == expected_layers

    # build a new scene so it builds from prior
    sc = Scene()
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), resolution=res)
    expected_layers += 1
    assert len(viewer.layers) == expected_layers


def test_sanitize_layers(make_napari_viewer, yt_ds):

    viewer = make_napari_viewer()

    sc = Scene()
    res = (10, 10, 10)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), name="layer0", resolution=res)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "mass"), name="layer1", resolution=res)

    clean_layers = sc._sanitize_layers(["layer0", "layer1"], viewer.layers)
    assert len(clean_layers) == 2
    assert all([isinstance(i, Layer) for i in clean_layers])

    clean_layers = sc._sanitize_layers([viewer.layers["layer1"]])
    assert len(clean_layers) == 1

    testlayers = [viewer.layers["layer1"], "layer0"]
    clean_layers = sc._sanitize_layers(testlayers, viewer.layers)
    assert len(clean_layers) == 2

    # check behavior when linked
    viewer.layers.link_layers(list(clean_layers))
    clean_layers = sc._sanitize_layers(["layer1"], viewer.layers)
    assert len(clean_layers) == 2
    assert all([isinstance(i, Layer) for i in clean_layers])

    clean_layers = sc._sanitize_layers(["layer1"], viewer.layers, check_linked=False)
    assert len(clean_layers) == 1
    assert all([isinstance(i, Layer) for i in clean_layers])

    with pytest.raises(ValueError):
        _ = sc._sanitize_layers(["layer1"])


def test_get_data_range(make_napari_viewer, yt_ds):

    viewer = make_napari_viewer()

    sc = Scene()
    res = (10, 10, 10)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), name="layer0", resolution=res)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), name="layer1", resolution=res)
    expected = (viewer.layers[0].data.min(), viewer.layers[0].data.max())
    actual = sc.get_data_range(viewer.layers)
    assert np.allclose(actual, expected)

    # check that a non yt-napari layer gets picked up too
    expected = (expected[0], expected[1] + 100.0)
    viewer.add_image(np.full((10, 10, 10), expected[1]))
    actual = sc.get_data_range(viewer.layers)
    assert np.allclose(actual, expected)


def test_cross_layer_features(make_napari_viewer, yt_ds):

    viewer = make_napari_viewer()

    sc = Scene()
    res = (10, 10, 10)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), name="layer0", resolution=res)
    sc.add_to_viewer(viewer, yt_ds, ("gas", "density"), name="layer1", resolution=res)

    sc.set_across_layers(viewer.layers, "colormap", "viridis")
    assert all([layer.colormap == "viridis"] for layer in viewer.layers)

    expected = (viewer.layers[0].data.min(), viewer.layers[0].data.max())
    sc.normalize_color_limits(viewer.layers)
    for layer in viewer.layers:
        assert np.allclose(layer.contrast_limits, expected)

    sc.add_to_viewer(
        viewer,
        yt_ds,
        ("gas", "density"),
        name="layer2",
        link_to="layer1",
        resolution=res,
    )
    linked = get_linked_layers(viewer.layers["layer2"])
    assert viewer.layers["layer1"] in linked
