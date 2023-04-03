import os

import platformdirs
import tomli
import tomli_w

from yt_napari.logging import ytnapari_log

_defaults = {"in_memory_cache": True}


class _ConfigContainer:
    def __init__(self, config_dir=None):
        if config_dir is None:
            app_dirs = platformdirs.AppDirs("yt-napari")
            self.dir = app_dirs.user_config_dir
        else:
            self.dir = config_dir
        self.config_file_name = "yt-napari.yaml"
        self.config_file = os.path.join(self.dir, self.config_file_name)
        self.config_dict = {}
        self.load_config()

    def load_config(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, "rb") as fi:
                config_dict = tomli.load(fi)
        else:
            config_dict = {}

        self.config_dict = _defaults.copy()
        self.config_dict.update(config_dict)

    def set_option(self, option: str, value):
        if option not in _defaults:
            raise KeyError(f"{option} is not a valid option")

        self.config_dict[option] = value
        self.write_to_disk()

    def write_to_disk(self):
        if os.path.exists(self.dir) is False:
            try:
                os.makedirs(self.dir, exist_ok=True)
            except OSError:
                ytnapari_log.warning(f"Could not create {self.dir}")

        try:
            with open(self.config_file, "wb") as fi:
                tomli_w.dump(self.config_dict, fi)
        except OSError:
            ytnapari_log.warning(f"Could not write {self.config_file}")

    def get_option(self, option: str):
        if option not in self.config_dict:
            raise KeyError(f"{option} is not a valid option")

        return self.config_dict[option]


ytnapari_config = _ConfigContainer()
