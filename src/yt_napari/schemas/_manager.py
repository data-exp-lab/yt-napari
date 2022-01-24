from typing import Optional, DefaultDict, Set, Union
from collections import defaultdict
from packaging.version import Version
from pathlib import PosixPath


class Manager:
    # This is a simple on-disk schema version management class meant for
    # tracking development of new schema files.
    default_schema_prefix = "napari-schema"
    def __init__(self, schema_db: Union[str, PosixPath]):
        """
        schema_db : Union[str, PosixPath]
            filepath to where the schema are stored on disk.
        """

        self.schema_db: PosixPath = PosixPath(schema_db).expanduser()
        self.verions: DefaultDict[str, Set] = defaultdict(set)
        self.max_versions: DefaultDict[str, Version] = defaultdict(lambda : Version("0.0.0"))
        self._check_versions()

    def _check_versions(self):
        # assemble the versions in the schema_db for each prefix and record the
        # max version
        for path in self.schema_db.iterdir():
            if 'json' in path.suffix:
                prefix, vstr = path.stem.split('_')
                self.verions[prefix].update((vstr,))
                vers = Version(vstr)
                if vers > self.max_versions[prefix]:
                    self.max_versions[prefix] = vers

    def _validate_prefix(self, schema_prefix: Optional[str] = None) -> str:
        if schema_prefix is None:
            schema_prefix = self.default_schema_prefix
        if "_" in schema_prefix:
            raise ValueError("schema_prefix strings must not contain _ characters, use - instead")
        return schema_prefix

    def _filename(self, schema_prefix: str, schema_version: str) -> PosixPath:
        # returns filename with schema_db path
        fname = f"{schema_prefix}_{schema_version}.json"
        return self.schema_db.joinpath(fname)

    def write_new_schema(self,
                         schema_json: str,
                         schema_prefix: Optional[str] = None,
                         inc_micro: Optional[bool] = True,
                         inc_minor: Optional[bool] = False,
                         inc_major: Optional[bool] = False,
                         version: Optional[str] = None,
                         overwrite_version: Optional[bool] = False):
        """
        write a new schema to the schema_db of the form schema_prefix_0.1.2.json
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
        if new_version_string in self.verions[schema_prefix] and overwrite_version is False:
            raise FileExistsError(
                f"provide overwrite_version=True to overwrite {filename}")

        # write out json to filename
        print(f"writing new schema {filename}")
        with open(filename, 'w') as f:
            f.write(schema_json)