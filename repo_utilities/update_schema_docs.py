# copies over schema files to the docs/_static folder and updates the schema.rst
import argparse

from yt_napari._data_model import _store_schema
from yt_napari.schemas._manager import Manager


def run_update(source_dir, schema_dir):
    m = Manager(schema_dir)
    m.update_docs(source_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    msg = (
        "the schema version to write (form X.X.X). If not provided, "
        "will only copy over the current schema without writing a new one."
    )
    parser.add_argument("-v", "--version", type=str, default=None, help=msg)

    args = parser.parse_args()
    if args.version is not None:
        v = str(args.version)
        if v.startswith("v"):
            v = v.replace("v", "")
        _store_schema(version=v, overwrite_version=True)
    run_update("./docs", "./src/yt_napari/schemas")
