import argparse
import json
import os

from yt_napari._data_model import _get_standard_schema_contents
from yt_napari.logging import ytnapari_log
from yt_napari.schemas._manager import Manager


def validate(version: str):
    """run checks on the schema and version"""

    if version.startswith("v") is False:
        msg = f"supplied version string does not start with 'v': {version}"
        raise RuntimeError(msg)

    vnumber = version.replace("v", "")
    v_ = tuple([int(vi) for vi in vnumber.split(".")])
    if len(v_) != 3:
        msg = f"supplied version number does not have 3 elements: {vnumber} "
        raise RuntimeError(msg)

    ytnapari_log.info(f"Checking if the upcoming release, {version}, is ready...")

    # check that the upcoming version has a dedicated schema version
    schema_dir = "./src/yt_napari/schemas"
    schema_prefix = "yt-napari"

    ytnapari_log.info(f"Checking that {schema_dir} contains a schema for {version}")

    m = Manager(schema_dir)

    if vnumber not in m.verions[schema_prefix]:
        msg = (
            f"the upcoming release version {version} does not have a corresponding"
            f"schema file. Run 'task update_schema_docs' to create one and update the"
            f" documentation."
        )
        raise RuntimeError(msg)

    schema_file = m._filename(schema_prefix, vnumber)
    ytnapari_log.info(f"... schema exists: {schema_file}")
    ytnapari_log.info("Checking that the documentation contains the latest schema")

    docs_dir = os.path.join(".", "docs", "_static")
    docs_schema = []
    for fi in os.listdir(docs_dir):
        if str(fi).endswith("json") and str(fi).startswith("yt-napari"):
            docs_schema.append(fi)

    if schema_file.name not in docs_schema:
        msg = (
            "The schema for the upcoming release is not in the docs directory!"
            " Run 'task update_schema_docs' to copy it over."
        )

        raise RuntimeError(msg)

    ytnapari_log.info(
        "    ... the docs contain the schema! checking that they match..."
    )

    existing = os.path.join(docs_dir, schema_file.name)

    with open(existing, "r") as jdata:
        existing_in_docs = json.load(jdata)

    with open(schema_file, "r") as jdata:
        existing_in_yt_napari = json.load(jdata)

    if existing_in_docs != existing_in_yt_napari:
        msg = (
            "The schema in the docs does not match that in yt-napari for"
            f" version {vnumber}. Run 'task update_schema_docs' to copy over"
            " the current schema version to the docs."
        )
        raise RuntimeError(msg)

    ytnapari_log.info("    ... the docs and yt-napari schema match! ")

    ytnapari_log.info("Checking that the current pydantic model matches the schema...")

    prefix, contents_str = _get_standard_schema_contents()
    current_pydantic_schema = json.loads(contents_str)
    if current_pydantic_schema != existing_in_yt_napari:
        msg = (
            "The json schema generated for the existing data model does not match"
            " the on-disk schema. Run 'task update_schema_docs' to re-generate the"
            " on-disk schema for this version."
        )
        raise RuntimeError(msg)

    ytnapari_log.info("    ... the pydantic model schema mathces the on-disk schema!")

    ytnapari_log.info("All schema checks passed. Ready to release.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "version", help="The upcoming release string to check", type=str
    )
    args = parser.parse_args()
    validate(args.version)
