import sys

import pytest

from yt_napari._data_model import InputModel, _store_schema
from yt_napari.schemas._manager import Manager

skip_win = "Schema manager is not for windows."


@pytest.mark.skipif(sys.platform == "win32", reason=skip_win)
def test_schema_version_management(tmp_path):

    m = Manager(schema_db=tmp_path)

    def get_expected(prefix, vstring):
        return tmp_path.joinpath(m._filename(prefix, vstring))

    # test with defaults
    pfx = m.default_schema_prefix
    expected_file = get_expected(pfx, "0.0.1")
    m.write_new_schema("any old string")
    assert expected_file.is_file()

    # run again with defaults, should increment
    expected_file = get_expected(pfx, "0.0.2")
    m.write_new_schema("any old string")
    assert expected_file.is_file()

    # test other increments
    expected_file = get_expected(pfx, "0.1.2")
    m.write_new_schema("any old string", inc_minor=True, inc_micro=False)
    assert expected_file.is_file()

    expected_file = get_expected(pfx, "1.1.2")
    m.write_new_schema("any old string", inc_major=True, inc_micro=False)
    assert expected_file.is_file()

    # test explicity version
    expected_file = get_expected(pfx, "2.0.0")
    m.write_new_schema("any old string", version="2.0.0")
    assert expected_file.is_file()

    # should error without override
    with pytest.raises(Exception):
        m.write_new_schema("any old string", version="2.0.0")

    # provide override, should have new text
    new_text = "different string"
    m.write_new_schema(new_text, version="2.0.0", overwrite_version=True)
    with open(expected_file) as f:
        assert "different string" in f.read()

    pfx = "new-yt-napari"
    expected_file = get_expected(pfx, "0.0.1")
    m.write_new_schema("any old string", schema_prefix=pfx)
    assert expected_file.is_file()


@pytest.mark.skipif(sys.platform == "win32", reason=skip_win)
def test_schema_generation(tmp_path):

    _store_schema(schema_db=tmp_path)
    m = Manager(schema_db=tmp_path)
    pfx = InputModel._schema_prefix
    expected_file = tmp_path.joinpath(m._filename(pfx, "0.0.1"))
    file_exists = expected_file.is_file()
    assert file_exists

    schema_contents = InputModel.schema_json(indent=2)
    with pytest.raises(ValueError):
        m.write_new_schema(schema_contents, schema_prefix="bad_prefix")


@pytest.mark.skipif(sys.platform == "win32", reason=skip_win)
def test_schema_update_docs(tmp_path):

    # directory setup
    docsdir = tmp_path / "docs"
    docsdir.mkdir()
    staticdir = docsdir / "_static"
    staticdir.mkdir()

    # create a schem.rst with the anchor test
    schema_rst = docsdir / "schema.rst"
    content = (
        "some stuff to put into a file\n" "\n with the special schemalistanchor! \n\n"
    )
    schema_rst.write_text(content)

    # store the schema a number of times
    _store_schema(schema_db=tmp_path)
    _store_schema(schema_db=tmp_path)
    _store_schema(schema_db=tmp_path, inc_micro=False, inc_major=True)

    m = Manager(schema_db=tmp_path)
    m.update_docs(docsdir)

    nfiles = len(list(staticdir.iterdir()))
    # should contain all the schema plus a copy in latest
    assert nfiles == 4

    new_content = schema_rst.read_text()
    assert content in new_content  # make sure the original is in the new

    m = Manager(schema_db=tmp_path)
    for fi in m.schema_files:
        # check that every schema file is now in the file
        assert fi.name in new_content
