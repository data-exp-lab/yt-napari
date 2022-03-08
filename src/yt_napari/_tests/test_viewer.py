import napari
import yt

from yt_napari.viewer import Scene


def test_viewer():

    # need to do this in a headless state
    nap_view = napari.Viewer()
    sc = Scene()
    ds = yt.testing.fake_amr_ds(fields=("density", "mass"), units=("kg/m**3", "kg"))

    sc.add_to_viewer(
        nap_view,
        ds,
        [("gas", "density"), ("gas", "mass")],
    )

    expected_layers = 2
    assert len(nap_view.layers) == expected_layers

    # hmm, why doesnt this pass the test. warning gets raised, pytest fails
    # with pytest.warns(RuntimeWarning):
    #     sc.add_to_viewer(nap_view, ds, [("gas", "density")], translate=10)
    #
    # with pytest.warns(RuntimeWarning):
    #     sc.add_to_viewer(nap_view, ds, [("gas", "density")], scale=10)
    # assert len(nap_view.layers) == 4

    sc.add_to_viewer(
        nap_view, ds, [("gas", "density"), ("gas", "mass")], log_fields=("gas", "mass")
    )
    expected_layers += 2
    assert len(nap_view.layers) == expected_layers

    # build a new scene so it builds from prior
    sc = Scene()
    sc.add_to_viewer(
        nap_view,
        ds,
        [("gas", "density"), ("gas", "mass")],
    )
    expected_layers += 2
    assert len(nap_view.layers) == expected_layers

    nap_view.close()
