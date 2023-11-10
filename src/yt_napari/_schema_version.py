from yt_napari._version import version, version_tuple

schema_version_tuple = version_tuple[:3]
schema_version = ".".join([str(i) for i in schema_version_tuple])
schema_name = "yt-napari_" + version + ".json"
