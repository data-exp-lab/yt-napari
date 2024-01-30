import inspect
import json
from pathlib import PosixPath
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from yt_napari.config import ytcfg
from yt_napari.schemas import _manager


class _ytBaseModel(BaseModel):
    pass


class ytField(_ytBaseModel):
    field_type: str = Field(None, description="a field type in the yt dataset")
    field_name: str = Field(None, description="a field in the yt dataset")
    take_log: bool = Field(
        True, description="if true, will apply log10 to the selected data"
    )


class Length_Value(_ytBaseModel):
    value: float = Field(None, description="Single unitful value.")
    unit: str = Field("code_length", description="the unit length string.")


class Left_Edge(_ytBaseModel):
    value: Tuple[float, float, float] = Field(
        (0.0, 0.0, 0.0), description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Right_Edge(_ytBaseModel):
    value: Tuple[float, float, float] = Field(
        (1.0, 1.0, 1.0), description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Length_Tuple(_ytBaseModel):
    value: Tuple[float, float, float] = Field(
        None, description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Region(_ytBaseModel):
    fields: List[ytField] = Field(
        None, description="list of fields to load for this selection"
    )
    left_edge: Left_Edge = Field(
        None,
        description="the left edge (min x, min y, min z)",
    )
    right_edge: Right_Edge = Field(
        None,
        description="the right edge (max x, max y, max z)",
    )
    resolution: Tuple[int, int, int] = Field(
        (400, 400, 400),
        description="the resolution at which to sample between the edges.",
    )
    rescale: bool = Field(False, description="rescale the final image between 0,1")


class CoveringGrid(BaseModel):
    fields: List[ytField] = Field(
        None, description="list of fields to load for this selection"
    )
    left_edge: Optional[Left_Edge] = Field(
        None,
        description="the left edge (min x, min y, min z)",
    )
    right_edge: Optional[Right_Edge] = Field(
        None,
        description="the right edge (max x, max y, max z)",
    )
    level: Optional[int] = (Field(0, description="Grid level to sample at"),)
    num_ghost_zones: Optional[int] = (
        Field(None, description="Number of ghost zones to include"),
    )
    rescale: Optional[bool] = Field(
        False, description="rescale the final image between 0,1"
    )


class Slice(BaseModel):
    fields: List[ytField] = Field(
        None, description="list of fields to load for this selection"
    )
    normal: str = Field(None, description="the normal axis of the slice")
    center: Length_Tuple = Field(
        None, description="The center point of the slice, default domain center"
    )
    slice_width: Length_Value = Field(
        None, description="The slice width, defaults to full domain"
    )
    slice_height: Length_Value = Field(
        None, description="The slice width, defaults to full domain"
    )
    resolution: Tuple[int, int] = Field(
        (400, 400),
        description="the resolution at which to sample the slice",
    )
    periodic: bool = Field(
        False, description="should the slice be periodic? default False."
    )
    rescale: bool = Field(False, description="rescale the final image between 0,1")


class SelectionObject(_ytBaseModel):
    regions: List[Region] = Field(None, description="a list of regions to load")
    slices: List[Slice] = Field(None, description="a list of slices to load")
    covering_grids: List[CoveringGrid] = Field(
        None, description="a list of covering grids to load")

class DataContainer(_ytBaseModel):
    filename: str = Field(None, description="the filename for the dataset")
    selections: SelectionObject = Field(
        None, description="selections to load in this dataset"
    )
    store_in_cache: bool = Field(
        ytcfg.get("yt_napari", "in_memory_cache"),
        description="if enabled, will store references to yt datasets.",
    )


class TimeSeriesFileSelection(_ytBaseModel):
    directory: str = Field(None, description="The directory of the timseries")
    file_pattern: str = Field(None, description="The file pattern to match")
    file_list: List[str] = Field(None, description="List of files to load.")
    file_range: Tuple[int, int, int] = Field(
        None,
        description="Given files matched by file_pattern, "
        "this option will select a range. Argument order"
        "is taken as start:stop:step.",
    )


class Timeseries(_ytBaseModel):
    file_selection: TimeSeriesFileSelection
    selections: SelectionObject = Field(
        None, description="selections to load in this dataset"
    )
    load_as_stack: bool = Field(
        False, description="If True, will stack images along a new dimension."
    )
    # process_in_parallel: Optional[bool] = Field(
    #     False, description="If True, will attempt to load selections in parallel."
    # )


class InputModel(_ytBaseModel):
    datasets: List[DataContainer] = Field(
        None, description="list of dataset containers to load"
    )
    timeseries: List[Timeseries] = Field(None, description="List of timeseries to load")
    _schema_prefix = "yt-napari"


def _get_standard_schema_contents() -> Tuple[str, str]:
    prefix = InputModel._schema_prefix.default
    schema_contents = InputModel.model_json_schema()
    schema_contents = json.dumps(schema_contents, indent=2)
    return prefix, schema_contents


def _store_schema(schema_db: Optional[Union[PosixPath, str]] = None, **kwargs):
    # save the current data model as a new schema
    if schema_db is None:
        schema_db = PosixPath(inspect.getfile(_manager)).parent
    m = _manager.Manager(schema_db)
    prefix, schema_contents = _get_standard_schema_contents()
    m.write_new_schema(schema_contents, schema_prefix=prefix, **kwargs)


class MetadataModel(_ytBaseModel):
    filename: str = Field(None, description="the filename for the dataset")
    include_field_list: bool = Field(True, description="whether to list the fields")
    _ds_attrs: Tuple[str] = (
        "domain_left_edge",
        "domain_right_edge",
        "current_time",
        "domain_dimensions",
    )


def _get_dm_listing(locals_dict):
    _data_model_list = []
    for ky, val in locals_dict.items():
        if inspect.isclass(val) and issubclass(val, _ytBaseModel):
            _data_model_list.append(ky)
            _data_model_list.append(val)
            _data_model_list.append(val.__module__ + "." + ky)
    return tuple(_data_model_list)


_data_model_list = _get_dm_listing(locals())
