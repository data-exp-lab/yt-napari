import numpy as np
import pytest
import yt


@pytest.fixture(scope="session")
def yt_ugrid_ds_fn(tmpdir_factory):

    # this fixture generates a random yt dataset saved to disk that can be
    # re-loaded and sampled.
    arr = np.random.random(size=(64, 64, 64))
    d = dict(density=(arr, "g/cm**3"), temperature=(arr, "K"))
    bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
    shp = arr.shape
    ds = yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)
    ad = ds.all_data()
    fn = str(tmpdir_factory.mktemp("data").join("uniform_grid_data.h5"))
    ad.save_as_dataset(
        fields=[("stream", "density"), ("stream", "temperature")], filename=fn
    )

    return fn
