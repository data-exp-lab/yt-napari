# copies over schema files to the docs/_static folder and updates the schema.rst
import argparse

from yt_napari._data_model import _store_schema
from yt_napari.schemas._manager import Manager


def run_update(source_dir, schema_dir):

    m = Manager(schema_dir)
    m.update_docs(source_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--version", type=str, default=None, help="the schema version to write"
    )

    args = parser.parse_args()
    if args.version is not None:
        _store_schema(version=args.version, overwrite_version=True)
    run_update("./docs", "./src/yt_napari/schemas")
