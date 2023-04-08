def test_config_update():

    # note: when the following import is at the top of the file, it errors:
    # UnboundLocalError: local variable 'ytcfg' referenced before assignment
    from yt_napari.config import _defaults, _get_updated_config, ytcfg

    current_vals = {}
    for setting in _defaults.keys():
        current_vals[setting] = ytcfg.get("yt_napari", setting)

    ytcfg.remove_section("yt_napari")
    ytcfg = _get_updated_config(ytcfg)
    assert ytcfg.has_section("yt_napari")
    for setting, val in _defaults.items():
        assert val == ytcfg.get("yt_napari", setting)

    # run it through again, make sure existing values are preserved
    ytcfg.set("yt_napari", "in_memory_cache", False)  # (default is True)
    ytcfg = _get_updated_config(ytcfg)
    assert ytcfg.get("yt_napari", "in_memory_cache") is False

    # remove it and add a blank so that the defaults get applied
    ytcfg.remove_section("yt_napari")
    ytcfg.add_section("yt_napari")
    ytcfg = _get_updated_config(ytcfg)
    for setting, val in _defaults.items():
        assert val == ytcfg.get("yt_napari", setting)

    # make sure our settings get reset to what they were coming in...
    ytcfg.update({"yt_napari": current_vals})
