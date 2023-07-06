import numpy as np
import yt


def _ytnapari_load_grid():
    arr = np.random.random(size=(64, 64, 64))
    d = dict(density=(arr, "g/cm**3"), temperature=(arr, "K"))
    bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
    shp = arr.shape
    return yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)
