import os
import sys
from stat import S_IREAD

import pytest

from yt_napari.config import _ConfigContainer


def test_config(tmp_path):

    config_dir = str(tmp_path / "configdir")
    custom_config = _ConfigContainer(config_dir=config_dir)
    custom_config.set_option("in_memory_cache", False)  # default is True

    config_file = custom_config.config_file
    assert os.path.isfile(config_file)

    # load as new config object to make sure it updates from the on-disk config
    custom_config = _ConfigContainer(config_dir=config_dir)
    assert custom_config.get_option("in_memory_cache") is False

    with pytest.raises(KeyError, match="bad_key is not a valid option"):
        custom_config.set_option("bad_key", False)

    with pytest.raises(KeyError, match="bad_key is not a valid option"):
        custom_config.get_option("bad_key")


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Test not valid for windows")
def test_config_in_read_only(tmp_path, caplog):
    config_dir = tmp_path / "configdir"
    config_dir.mkdir()

    config_dir.chmod(mode=S_IREAD)

    custom_config = _ConfigContainer(config_dir=str(config_dir))
    custom_config.write_to_disk()

    assert "Could not write" in caplog.text

    custom_config = _ConfigContainer(config_dir=str(config_dir / "another_dir"))
    custom_config.write_to_disk()
    assert "Could not create" in caplog.text

    config_dir.chmod(0o0777)
    config_dir.rmdir()
