import json
import os.path
from os import PathLike

import yt

from yt_napari import _special_loaders, _utilities
from yt_napari.config import ytcfg
from yt_napari.logging import ytnapari_log


def _load_sample(filename: str):

    missing = False
    msg = (
        "Loading sample data requires additional dependencies but "
        "the following dependencies are missing:"
    )
    for dep in ("pooch", "pandas", "h5py", "libconf"):
        if _utilities.dependency_is_missing(dep):
            msg += f"\n    {dep}"
            missing = True

    if missing:
        msg += (
            "\ninstall individual dependencies with pip, or install them all with "
            "pip install yt-napari[full]."
        )

        raise ModuleNotFoundError(msg)

    ds = yt.load_sample(filename)
    return ds


def get_sample_set_list() -> list[str]:
    """
    return the names of the yt sample datasets that yt-napari can load

    Returns
    -------
    list[str]
        the sample dataset names, as accepted by ``yt.load_sample``
    """
    import importlib.resources as importlib_resources

    jdata = json.loads(
        importlib_resources.files("yt_napari")
        .joinpath("sample_data")
        .joinpath("sample_registry.json")
        .read_bytes()
    )
    return jdata["enabled"]


class DatasetCache:
    """
    An in-memory cache of loaded yt datasets, keyed by filename.

    The widgets and the JSON reader share a single module-level instance,
    :data:`dataset_cache`. Caching is enabled by the ``in_memory_cache``
    option in the ``[yt_napari]`` section of the yt configuration file
    (see :ref:`configfile`). Call :meth:`rm_all` to release the cached
    dataset handles.
    """

    def __init__(self):
        self.available = {}
        self._most_recent: str = None
        self.sample_sets: list[str] = get_sample_set_list()

    def add_ds(self, ds, name: str):
        """add a dataset to the cache, overwriting any existing entry for name"""
        if name in self.available:
            ytnapari_log.warning(f"A dataset already exists for {name}. Overwriting.")
        self.available[name] = ds
        self._most_recent = name

    @property
    def most_recent(self):
        """the most recently added dataset, or None if the cache is empty"""
        if self._most_recent is not None:
            return self.available[self._most_recent]
        return None

    def get_ds(self, name: str):
        """return the cached dataset for name, or None if it is not cached"""
        if self.exists(name):
            return self.available[name]
        ytnapari_log.warning(f"{name} not found in cache.")
        return None

    def exists(self, name: str) -> bool:
        """check if a dataset is in the cache"""
        return name in self.available

    def rm_ds(self, name: str):
        """remove a single dataset from the cache"""
        self.available.pop(name, None)

    def rm_all(self):
        """remove all datasets from the cache"""
        self.available = {}
        self._most_recent = None

    def check_then_load(self, filename: str, cache_if_not_found: bool = True):
        """
        return a dataset from the cache, loading it first if necessary

        Parameters
        ----------
        filename : str
            the dataset to load: a path for ``yt.load``, the name of one of the
            sample datasets (see :func:`get_sample_set_list`) or one of the
            internal ``_ytnapari_*`` test loaders.
        cache_if_not_found : bool
            if True (default) and ``in_memory_cache`` is enabled in the yt
            configuration, add a newly loaded dataset to the cache.

        Returns
        -------
        the yt dataset
        """
        if self.exists(filename):
            ytnapari_log.info(f"loading {filename} from cache.")
            return self.get_ds(filename)
        elif callable_name := _check_for_special(filename):
            # the filename is actually a function handle! get it, call it
            # this allows yt-napari to use all the yt fake datasets in
            # testing without saving them to disk.
            ds_callable = getattr(_special_loaders, callable_name)
            ds = ds_callable()
        else:
            if filename in self.sample_sets:
                ds = _load_sample(filename)
            else:
                ds = yt.load(filename)

        if ytcfg.get("yt_napari", "in_memory_cache") and cache_if_not_found:
            self.add_ds(ds, filename)
        return ds


#: the :class:`DatasetCache` instance shared by the widgets and the JSON reader
dataset_cache = DatasetCache()


def _check_for_special(filename: PathLike) -> str | None:
    # check if a "filename" is one of our short-circuiting special loaders
    # and return the function name if it is valid.
    basename = os.path.basename(filename)
    if basename.startswith("_ytnapari") and hasattr(_special_loaders, basename):
        return str(basename)
    return None
