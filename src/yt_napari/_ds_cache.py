import weakref

import yt

from yt_napari.config import ytcfg
from yt_napari.logging import ytnapari_log


class DatasetCache:
    def __init__(self):
        self.available = {}
        self._most_recent: str = None

    def add_ds(self, ds, name: str):
        if name in self.available:
            ytnapari_log.warning(f"A dataset already exists for {name}. Overwriting.")
        self.available[name] = weakref.proxy(ds)
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

    def reference_exists(self, name: str) -> bool:
        if self.exists(name):
            ds = self.get_ds(name)
            ref_exists = True
            try:
                _ = ds.basename
            except ReferenceError:
                ref_exists = False
            return ref_exists
        return False

    def rm_ds(self, name: str):
        self.available.pop(name, None)

    def rm_all(self):
        self.available = {}
        self._most_recent = None

    def check_then_load(self, filename: str):
        if self.reference_exists(filename):
            ytnapari_log.info(f"loading {filename} from cache.")
            return self.get_ds(filename)
        else:
            ds = yt.load(filename)
            if ytcfg.get("yt_napari", "in_memory_cache"):
                self.add_ds(ds, filename)
            return ds


dataset_cache = DatasetCache()
