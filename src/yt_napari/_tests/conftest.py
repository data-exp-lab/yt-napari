import numpy as np
import pytest
import yt
from yt.funcs import mylog


@pytest.fixture(scope="session")
def yt_ugrid_ds_fn(tmpdir_factory):

    # disable logging here because of a conflict with pytest-qt and the way it
    # captures logs : it will cause type errors where yt expects number but gets
    # a string instead.

    # Save the original log level
    original_level = mylog.level
    # Disable yt logging (Level 50 / CRITICAL+1 suppresses all logs)
    mylog.setLevel(50)

    try:

        # this fixture generates a random yt dataset saved to disk that can be
        # re-loaded and sampled.
        rng = np.random.default_rng()
        arr = rng.random(size=(64, 64, 64))
        d = dict(density=(arr, "g/cm**3"), temperature=(arr, "K"))
        bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
        shp = arr.shape
        ds = yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)
        ad = ds.all_data()
        fn = str(tmpdir_factory.mktemp("data").join("uniform_grid_data.h5"))
        ad.save_as_dataset(
            fields=[("stream", "density"), ("stream", "temperature")], filename=fn
        )
        yield fn

    finally:
        # Reset logging to the original state after tests finish
        mylog.setLevel(original_level)
