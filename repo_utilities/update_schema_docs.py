# copies over schema files to the docs/_static folder and updates the schema.rst
from yt_napari.schemas._manager import Manager


def run_update(source_dir, schema_dir):
    m = Manager(schema_dir)
    m.update_docs(source_dir)


if __name__ == "__main__":
    run_update("./docs", "./src/yt_napari/schemas")
