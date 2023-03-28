from yt import testing as yt_testing

from yt_napari._ds_cache import dataset_cache


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
