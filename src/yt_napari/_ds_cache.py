import yt

from yt_napari import _special_loaders
from yt_napari.config import ytcfg
from yt_napari.logging import ytnapari_log


class DatasetCache:
    def __init__(self):
        self.available = {}
        self._most_recent: str = None

    def add_ds(self, ds, name: str):
        if name in self.available:
            ytnapari_log.warning(f"A dataset already exists for {name}. Overwriting.")
        self.available[name] = ds
        self._most_recent = name

    @property
    def most_recent(self):
        if self._most_recent is not None:
            return self.available[self._most_recent]
        return None

    def get_ds(self, name: str):
        if self.exists(name):
            return self.available[name]
        ytnapari_log.warning(f"{name} not found in cache.")
        return None

    def exists(self, name: str) -> bool:
        return name in self.available

    def rm_ds(self, name: str):
        self.available.pop(name, None)

    def rm_all(self):
        self.available = {}
        self._most_recent = None

    def check_then_load(self, filename: str, cache_if_not_found: bool = True):
        if self.exists(filename):
            ytnapari_log.info(f"loading {filename} from cache.")
            return self.get_ds(filename)
        elif filename.startswith("_ytnapari") and hasattr(_special_loaders, filename):
            # the filename is actually a function handle! get it, call it
            # this allows yt-napari to to use all the yt fake datasets in
            # testing without saving them to disk.
            ds_callable = getattr(_special_loaders, filename)
            ds = ds_callable()
        else:
            ds = yt.load(filename)

        if ytcfg.get("yt_napari", "in_memory_cache") and cache_if_not_found:
            self.add_ds(ds, filename)
        return ds


dataset_cache = DatasetCache()
