import os

import numpy as np
import pytest
from napari import Viewer
from yt.visualization.profile_plotter import PhasePlot

from yt_napari._widget_2d_plots import YTPhasePlot


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

    r.callback_container.save.value = True

    svfig = str(tmp_path / "pp_fig.png")
    r.callback_container.savename.value = svfig
    r.run_callback_button.native.click()
    assert os.path.isfile(svfig)

    r.deleteLater()
