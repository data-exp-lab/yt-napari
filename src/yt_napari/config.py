from yt.config import ytcfg

_defaults = {"in_memory_cache": True}


def _get_updated_config(cfg):
    # adds the yt_napari section and missing settings to the base yt config
    if cfg.has_section("yt_napari"):
        for setting, default in _defaults.items():
            try:
                _ = cfg.get("yt_napari", setting)
            except KeyError:
                cfg.set("yt_napari", setting, default)
    else:
        cfg.add_section("yt_napari")
        cfg.update({"yt_napari": _defaults})
    return cfg


ytcfg = _get_updated_config(ytcfg)
