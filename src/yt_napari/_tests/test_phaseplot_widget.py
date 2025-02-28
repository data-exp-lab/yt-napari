import os

import numpy as np
import pytest
from napari import Viewer
from qtpy.QtWidgets import QComboBox, QVBoxLayout
from yt.visualization.profile_plotter import PhasePlot

from yt_napari._widget_2d_plots import YTPhasePlot, _validate_cmyt_name


@pytest.fixture
def some_images():

    sh = (8, 16, 32)
    n_images = 3
    images = []

    for im in range(n_images):
        images.append(
            {
                "value": np.random.random(sh),
                "name": f"image_{im}",
            }
        )

    return images


def test_phaseplot_widget(
    make_napari_viewer,
    some_images,
    tmp_path,
):

    viewer: Viewer = make_napari_viewer()
    r = YTPhasePlot(napari_viewer=viewer)

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    # check that layers are populated
    r.update_layers.native.click()
    for layer in viewer.layers:
        assert layer.name in r.available_layer_list

    r.render_button.native.click()
    assert isinstance(r.phase_plot, PhasePlot)

    r.callback_container.apply_logx.value = True
    r.callback_container.apply_logy.value = True
    r.callback_container.apply_logz.value = True
    r.callback_container.reverse_cmap.value = True
    r.callback_container.save.value = True

    svfig = str(tmp_path / "pp_fig.png")
    r.callback_container.savename.value = svfig
    r.run_callback_button.native.click()
    assert os.path.isfile(svfig)

    r.deleteLater()


def test_phaseplot_fields(
    make_napari_viewer,
    some_images,
):
    viewer: Viewer = make_napari_viewer()
    r = YTPhasePlot(napari_viewer=viewer)

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    r.update_layers.native.click()

    r.layer_1.setCurrentIndex(len(some_images))
    assert r.layer_1.currentText() == r._default_index_fields[0]
    assert r.layer_1.currentIndex() == len(some_images)

    r.render_button.native.click()

    r.deleteLater()


def test_weight_field(
    make_napari_viewer,
    some_images,
):
    viewer: Viewer = make_napari_viewer()
    r = YTPhasePlot(napari_viewer=viewer)

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    r.update_layers.native.click()

    r.layer_4_weight.setCurrentIndex(1)
    assert r.layer_4_weight.currentText() == some_images[0]["name"]

    r.render_button.native.click()
    r.deleteLater()


def test_apply_callbacks_without_render(
    make_napari_viewer,
    some_images,
):
    viewer: Viewer = make_napari_viewer()
    r = YTPhasePlot(napari_viewer=viewer)

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    r.update_layers.native.click()

    assert r.phase_plot is None
    r.run_callback_button.native.click()
    assert isinstance(r.phase_plot, PhasePlot)
    r.deleteLater()


@pytest.mark.parametrize(
    "input_name,expected",
    [("cmapname.cmyt", "cmyt.cmapname"), ("notacmytcmap", "notacmytcmap")],
)
def test_validate_cmyt_name(input_name: str, expected: str):
    result = _validate_cmyt_name(input_name)
    assert result == expected


def test_add_layer_dropdown(
    make_napari_viewer,
    some_images,
):
    viewer: Viewer = make_napari_viewer()
    r = YTPhasePlot(napari_viewer=viewer)

    for im in some_images:
        viewer.add_image(im["value"], name=im["name"])

    r.update_layers.native.click()

    sub_QVbox = QVBoxLayout()

    r.add_layer_dropdown(
        "teststr",
        "teststr2",
        sub_QVbox,
        value=None,
    )
    n_items = sub_QVbox.count()
    index = n_items - 1
    # dropdown gets added to an inner layout
    layer_hbox = sub_QVbox.itemAt(index).layout()
    # should be 2 widgets here
    n_items = layer_hbox.count()
    assert n_items == 2
    assert isinstance(layer_hbox.itemAt(1).widget(), QComboBox)

    r.add_layer_dropdown(
        "teststr",
        "teststr2",
        sub_QVbox,
        value=None,
        value_index=100,
    )

    sub_QVbox.deleteLater()

    r.deleteLater()
