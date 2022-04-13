from yt_napari import _gui_utilities as gu


def test_set_default():
    assert gu.set_default(1, None) == 1
    assert gu.set_default(None, 1) == 1
