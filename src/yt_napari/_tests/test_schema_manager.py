from yt_napari.schemas._manager import Manager
import pytest


def test_schema_version_management(tmp_path):

    m = Manager(schema_db=tmp_path)

    def get_expected(prefix, vstring):
        return tmp_path.joinpath(m._filename(prefix, vstring))

    # test with defaults
    pfx = m.default_schema_prefix
    expected_file = get_expected(pfx, '0.0.1')
    m.write_new_schema("any old string")
    assert expected_file.is_file()

    # run again with defaults, should increment
    expected_file = get_expected(pfx, '0.0.2')
    m.write_new_schema("any old string")
    assert expected_file.is_file()

    # test other increments
    expected_file = get_expected(pfx, '0.1.2')
    m.write_new_schema("any old string", inc_minor=True, inc_micro=False)
    assert expected_file.is_file()

    expected_file = get_expected(pfx, '1.1.2')
    m.write_new_schema("any old string", inc_major=True, inc_micro=False)
    assert expected_file.is_file()

    # test explicity version
    expected_file = get_expected(pfx, '2.0.0')
    m.write_new_schema("any old string", version='2.0.0')
    assert expected_file.is_file()

    # should error without override
    with pytest.raises(Exception):
        m.write_new_schema("any old string", version='2.0.0')

    # provide override, should have new text
    m.write_new_schema("different string", version='2.0.0', overwrite_version=True)
    with open(expected_file, 'r') as f:
        assert "different string" in f.read()

    pfx = "new-yt-napari"
    expected_file = get_expected(pfx, '0.0.1')
    m.write_new_schema("any old string", schema_prefix=pfx)
    assert expected_file.is_file()
