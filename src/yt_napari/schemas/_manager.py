import shutil
from collections import defaultdict
from os import PathLike
from pathlib import PosixPath
from typing import DefaultDict, Optional, Set, Union

from packaging.version import Version


class Manager:
    # This is a simple on-disk schema version management class meant for
    # tracking development of new schema files.
    default_schema_prefix = "yt-napari"

    def __init__(self, schema_db: Union[str, PosixPath]):
        """
        schema_db : Union[str, PosixPath]
            filepath to where the schema are stored on disk.
        """

        self.schema_db: PosixPath = PosixPath(schema_db).expanduser()
        self.verions: DefaultDict[str, Set] = defaultdict(set)
        self.max_versions: DefaultDict[str, Version] = defaultdict(
            lambda: Version("0.0.0")
        )
        self.schema_files = []
        self._check_versions()

    def _check_versions(self):
        # assemble the versions in the schema_db for each prefix and record the
        # max version
        for path in self.schema_db.iterdir():
            if "json" in path.suffix:
                prefix, vstr = path.stem.split("_")
                self.verions[prefix].update((vstr,))
                vers = Version(vstr)
                if vers > self.max_versions[prefix]:
                    self.max_versions[prefix] = vers
                self.schema_files.append(path)

    def _validate_prefix(self, schema_prefix: Optional[str] = None) -> str:
        if schema_prefix is None:
            schema_prefix = self.default_schema_prefix
        if "_" in schema_prefix:
            msg = "schema_prefix strings must not contain _ character"
            raise ValueError(msg)
        return schema_prefix

    def _filename(self, schema_prefix: str, schema_version: str) -> PosixPath:
        # returns filename with schema_db path
        fname = f"{schema_prefix}_{schema_version}.json"
        return self.schema_db.joinpath(fname)

    def write_new_schema(
        self,
        schema_json: str,
        schema_prefix: Optional[str] = None,
        inc_micro: Optional[bool] = True,
        inc_minor: Optional[bool] = False,
        inc_major: Optional[bool] = False,
        version: Optional[str] = None,
        overwrite_version: Optional[bool] = False,
    ):
        """
        write a schema to the schema_db of the form schema_prefix_0.1.2.json
        where 0, 1, 2 are the major, minor and patch version numbers.

        Parameters:
        -----------
        schema_json: str
            the json string to write, assumes that it is already validated
        schema_prefix: Optional[str]
            file prefix for the schema. Version incrementing will only check
            schemas with matching prefix for determining the current version.
        inc_micro: Optional[bool]
            increment the micro (patch) version (default True)
        inc_minor: Optional[bool]
            increment the minor version (default False)
        inc_major: Optional[bool]
            increment the major version (default False)
        version: Optional[str]
            use this to fully specify the version, will ignore any increment
            parameters and will error if file exists (and if overwrite_version
            is False)
        overwrite_version: Optional[bool]
            allows overwriting if the version parameter is used. not used when
            using the increment parameters. Default False.
        """

        schema_prefix = self._validate_prefix(schema_prefix)
        # always update list of current versions in case of recent writes
        self._check_versions()

        if version:
            v = Version(version)
            new_version_string = v.base_version
        else:
            max_v = self.max_versions[schema_prefix]
            mj, mn, mc = (max_v.major, max_v.minor, max_v.micro)
            if inc_micro:
                mc += 1
            if inc_minor:
                mn += 1
            if inc_major:
                mj += 1
            new_version_string = ".".join([str(c) for c in [mj, mn, mc]])

        # get the full filename for the new schema
        filename = self._filename(schema_prefix, new_version_string)
        if (
            new_version_string in self.verions[schema_prefix]
            and overwrite_version is False
        ):
            raise FileExistsError(
                f"provide overwrite_version=True to overwrite {filename}"
            )

        # write out json to filename
        print(f"writing new schema {filename}")
        with open(filename, "w") as f:
            f.write(schema_json)

    def update_docs(
        self, source: Union[str, PathLike], schema_prefix: Optional[str] = None
    ):
        """
        copies all schema to _static, updates latest and updates schema.rst

        Parameters:
        ----------
        source: the docs directory path
        schema_prefix: the schema prefix to include (default yt-napari).

        Examples:
        ---------

        From the top level of the repository:

        >>> from yt_napari.schemas._manager import Manager
        >>> m = Manager("./src/yt_napari/schemas")
        >>> m.schema_files
        >>> source_dir = './docs'
        >>> m.update_docs(source_dir)

        """

        schema_prefix = self._validate_prefix(schema_prefix)
        source_dir = PosixPath(source)
        source_static = source_dir.joinpath("_static")

        # copy all json files to docs/_static/
        copied_files = []
        for fi in self.schema_files:
            if schema_prefix in fi.name:
                target = source_static.joinpath(fi.name)
                shutil.copy2(fi, target)
                copied_files.append(fi)

        copied_files.sort(reverse=True)

        # copy the latest to docs/_static/yt-napari_latest.json
        latest = self._filename(schema_prefix, self.max_versions[schema_prefix])
        target = source_static.joinpath(f"{schema_prefix}_latest.json")
        shutil.copy2(latest, target)

        # update the table in docs/schema.rst

        # build the new list of schema versions
        table_entry = []
        for fi in copied_files:
            nm = fi.name
            table_entry.append(
                f"{nm} : `view <_static/{nm}>`_ , :download:`download <_static/{nm}>`"
            )
            table_entry.append("")
        table_entry.append("")

        sch_docs = source_dir.joinpath("schema.rst")

        with open(sch_docs) as file:
            contents = file.read().splitlines()

        new_contents = []
        for line in contents:
            new_contents.append(line)
            if "schemalistanchor" in line:
                new_contents.append("")
                break

        new_contents = new_contents + table_entry
        with open(sch_docs, "w") as file:
            file.write("\n".join(new_contents))
