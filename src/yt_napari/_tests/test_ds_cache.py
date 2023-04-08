from yt import testing as yt_testing

from yt_napari._ds_cache import dataset_cache
from yt_napari.config import ytcfg


def get_new_ds():
    return yt_testing.fake_amr_ds(fields=("density", "mass"), units=("kg/m**3", "kg"))


def test_ds_cache(caplog):
    ds = get_new_ds()
    ds_name = "test_name"
    dataset_cache.add_ds(ds, ds_name)
    assert dataset_cache.exists(ds_name)
    assert dataset_cache.exists("test_name_bad") is False
    assert dataset_cache._most_recent == ds_name

    dataset_cache.add_ds(ds, ds_name)
    assert "A dataset already exists" in caplog.text

    ds_from_store = dataset_cache.get_ds(ds_name)
    assert ds_from_store == ds
    ds_from_store = dataset_cache.most_recent
    assert ds_from_store == ds

    dataset_cache.rm_ds(ds_name)
    assert dataset_cache.exists(ds_name) is False
    assert len(dataset_cache.available) == 0

    ds_none = dataset_cache.get_ds("doesnotexist")
    assert ds_none is None
    assert "doesnotexist not found in cache" in caplog.text

    dataset_cache.add_ds(ds, ds_name)
    assert dataset_cache.exists(ds_name)
    dataset_cache.rm_all()
    assert len(dataset_cache.available) == 0
    assert dataset_cache.most_recent is None


def test_ds_destruction():
    ds = get_new_ds()
    dataset_cache.add_ds(ds, "hellotest")
    dataset_cache.rm_ds("hellotest")
    assert dataset_cache.exists("hellotest") is False


def test_config_option(yt_ugrid_ds_fn):
    dataset_cache.rm_all()
    ytcfg.set("yt_napari", "in_memory_cache", False)
    _ = dataset_cache.check_then_load(yt_ugrid_ds_fn)
    assert yt_ugrid_ds_fn not in dataset_cache.available
    ytcfg.set("yt_napari", "in_memory_cache", True)
