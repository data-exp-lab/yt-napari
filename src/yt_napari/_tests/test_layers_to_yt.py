import napari
import numpy as np
import pytest
from yt.data_objects.static_output import Dataset

from yt_napari.viewer import layers_to_yt


@pytest.fixture
def some_images():

    sh = (8, 16, 32)
    n_images = 4
    images = []

    for im in range(n_images):
        images.append(
            {
                "value": np.random.random(sh),
                "name": f"image_{im}",
            }
        )

    return images


def test_layers_to_yt(
    make_napari_viewer,
    some_images,
):

    viewer: napari.Viewer = make_napari_viewer()

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    bbox = np.array([[-1.0, 1.0], [-1.0, 1.0], [-1.5, 2.0]])
    ds = layers_to_yt(viewer, layers=["image_0", "image_1"], bbox=bbox)

    assert isinstance(ds, Dataset)
    assert len(ds.field_list) == 2


def test_layers_bad_names(make_napari_viewer, some_images):
    viewer: napari.Viewer = make_napari_viewer()
    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    with pytest.raises(RuntimeError, match="Layer notalayer not found"):
        _ = layers_to_yt(viewer, layers=["image_0", "notalayer"])

    with pytest.raises(RuntimeError, match="Layer 100 not found"):
        _ = layers_to_yt(viewer, layers=[0, 100])


def test_layers_bad_shape(make_napari_viewer, some_images):
    viewer: napari.Viewer = make_napari_viewer()
    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    viewer.add_image(np.random.random((10, 10, 20)), name="bad_shape")

    with pytest.raises(RuntimeError, match="Layer notalayer not found"):
        _ = layers_to_yt(viewer, layers=["image_0", "notalayer"])

    with pytest.raises(RuntimeError, match="Can only export layers as a yt dataset"):
        _ = layers_to_yt(viewer)


def test_additional_kwargs(
    make_napari_viewer,
    some_images,
):
    viewer: napari.Viewer = make_napari_viewer()

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    ds = layers_to_yt(viewer, length_unit="km")
    assert len(ds.field_list) == len(some_images)
    assert ds.domain_right_edge.to("km")[2].d == 1
