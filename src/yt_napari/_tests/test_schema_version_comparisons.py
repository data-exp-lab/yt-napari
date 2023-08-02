import pytest

from yt_napari._version import version
from yt_napari.schemas import _version_comparison as vc


@pytest.mark.parametrize(
    "string_to_test,expected",
    [
        ("yt-napari_0.1.3.json", (0, 1, 3)),
        ("yt-napari_2.1.0.json", (2, 1, 0)),
        ("/blah/blah/yt-napari_2.1.0.json", (2, 1, 0)),
        ("/blah/blah/yt-napari_latest.json", vc._get_version_tuple()),
    ],
)
def test_version_tupling(string_to_test, expected):
    assert vc._schema_version_tuple_from_str(string_to_test) == expected


@pytest.mark.parametrize(
    "string_to_test,expected",
    [
        ("yt-napari_0.0.2.json", True),
        ("yt-napari_0.0.1.json", True),
        ("yt-napari_1000.1.0.json", False),
        ("/blah/blah/yt-napari_latest.json", True),
    ],
)
def test_schema_str_validation(string_to_test, expected):
    assert (
        vc.schema_version_is_valid(string_to_test, dev_version_check=False) is expected
    )


def test_schema_str_dev_validation():
    expected = "dev" in version  # in test env, this should always be true
    _is_valid = vc.schema_version_is_valid(
        "yt-napari_1000.1.0.json", dev_version_check=True
    )
    assert _is_valid is expected
