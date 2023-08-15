from pathlib import Path

import numpy as np
import yt


def _ytnapari_load_grid():
    arr = np.random.random(size=(64, 64, 64))
    d = dict(density=(arr, "g/cm**3"), temperature=(arr, "K"))
    bbox = np.array([[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5]])
    shp = arr.shape
    return yt.load_uniform_grid(d, shp, length_unit="Mpc", bbox=bbox, nprocs=64)


def _construct_ugrid_timeseries(top_dir: Path, nfiles: int):
    ts_dir = top_dir / "output_dir"
    ts_dir.mkdir()

    flist_actual = []
    for tstep in range(0, nfiles):
        tstepstr = str(tstep).zfill(4)
        fname = f"_ytnapari_load_grid-{tstepstr}"
        newfi = ts_dir / fname
        newfi.touch()

        flist_actual.append(str(newfi))
    return str(ts_dir), flist_actual
