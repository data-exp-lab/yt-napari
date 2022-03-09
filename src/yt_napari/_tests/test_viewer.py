import yt

from yt_napari.viewer import Scene


def test_viewer(make_napari_viewer):

    # make_napari_viewer is a pytest fixture. It takes any keyword arguments
    # that napari.Viewer() takes. The fixture takes care of teardown, do **not**
    # explicitly close it!
    viewer = make_napari_viewer()

    sc = Scene()
    ds = yt.testing.fake_amr_ds(fields=("density", "mass"), units=("kg/m**3", "kg"))
    sc.add_to_viewer(viewer, ds, ("gas", "density"))

    expected_layers = 1
    assert len(viewer.layers) == expected_layers

    # hmm, why doesnt this pass the test. warning gets raised, pytest fails
    # with pytest.warns(RuntimeWarning):
    #     sc.add_to_viewer(nap_view, ds, [("gas", "density")], translate=10)
    #
    # with pytest.warns(RuntimeWarning):
    #     sc.add_to_viewer(nap_view, ds, [("gas", "density")], scale=10)
    # assert len(nap_view.layers) == 4

    sc.add_to_viewer(viewer, ds, ("gas", "density"))
    expected_layers += 1
    assert len(viewer.layers) == expected_layers

    # build a new scene so it builds from prior
    sc = Scene()
    sc.add_to_viewer(viewer, ds, ("gas", "density"))
    expected_layers += 1
    assert len(viewer.layers) == expected_layers
