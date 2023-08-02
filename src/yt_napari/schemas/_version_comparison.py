from typing import Tuple

from yt_napari._data_model import InputModel
from yt_napari._version import version, version_tuple
from yt_napari.logging import ytnapari_log


def _get_version_tuple():
    vt = tuple([int(i) for i in version_tuple[:3] if str(i).isnumeric()])
    if len(vt) < 3:
        # tox install can end up with 0.1.dev1, etc.
        vt = vt + (0,) * (3 - len(vt))
    return vt


def schema_version_is_valid(
    schema_version: str, dev_version_check: bool = True
) -> bool:
    pfx = InputModel._schema_prefix
    if schema_version is None or pfx not in schema_version:
        # the schema does not match a known schema for this plugin
        return False

    # now we check the actual version. since the schema prefix (yt-napari) is
    # in the supplied schema_version, we can assume a form of yt-napari_x.x.x.json
    sc_version = _schema_version_tuple_from_str(schema_version)
    _version_tuple = _get_version_tuple()
    if sc_version < _version_tuple:
        # using an old schema. lets try anyway, but pass along a warning.
        msg = (
            f"The version of the supplied schema:\n    {schema_version} \n"
            f"    does not match the installed version of yt-napari ({version}).\n"
            f"    To avoid unexpected errors, please update the json to use a schema\n"
            f"    version that matches your yt-napari installation or install the\n"
            f"    yt-napari version that matches your specified schema."
        )
        ytnapari_log.warning(msg)
    elif sc_version > _version_tuple:
        if dev_version_check and "dev" in version:
            msg = (
                "You are running a development version of yt-napari, so your "
                "specified schema may be valid if it corresponds to an upcoming"
                "release."
            )
            ytnapari_log.info(msg)
            return True
        # using a new schema with old yt-napari. always fail.
        msg = (
            f"The version of the supplied schema:\n    {schema_version} \n"
            f"    is newer than the installed version of yt-napari ({version}).\n"
            f"    update yt-napari to use your json file."
        )
        ytnapari_log.info(msg)
        return False
    return True


def _schema_version_tuple_from_str(schema_version_raw: str) -> Tuple[int, int, int]:
    # schema_version_raw may be a single string or a file-like address

    if "yt-napari_latest" in schema_version_raw:
        return _get_version_tuple()

    schema_end = schema_version_raw.split("/")[-1]
    v_schema = schema_end.replace(InputModel._schema_prefix, "")
    v_schema = v_schema.replace("_", "").replace(".json", "")
    return tuple([int(v) for v in v_schema.split(".")])
