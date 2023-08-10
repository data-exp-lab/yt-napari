import inspect
from pathlib import PosixPath
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from yt_napari.config import ytcfg
from yt_napari.schemas import _manager


class ytField(BaseModel):
    field_type: str = Field(None, description="a field type in the yt dataset")
    field_name: str = Field(None, description="a field in the yt dataset")
    take_log: Optional[bool] = Field(
        True, description="if true, will apply log10 to the selected data"
    )


class Length_Value(BaseModel):
    value: float = Field(None, description="Single unitful value.")
    unit: str = Field("code_length", description="the unit length string.")


class Left_Edge(BaseModel):
    value: Tuple[float, float, float] = Field(
        (0.0, 0.0, 0.0), description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Right_Edge(BaseModel):
    value: Tuple[float, float, float] = Field(
        (1.0, 1.0, 1.0), description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Length_Tuple(BaseModel):
    value: Tuple[float, float, float] = Field(
        None, description="3-element unitful tuple."
    )
    unit: str = Field("code_length", description="the unit length string.")


class Region(BaseModel):
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
    resolution: Optional[Tuple[int, int, int]] = Field(
        (400, 400, 400),
        description="the resolution at which to sample between the edges.",
    )


class Slice(BaseModel):
    fields: List[ytField] = Field(
        None, description="list of fields to load for this selection"
    )
    normal: str = Field(None, description="the normal axis of the slice")
    center: Optional[Length_Tuple] = Field(
        None, description="The center point of the slice, default domain center"
    )
    slice_width: Optional[Length_Value] = Field(
        None, description="The slice width, defaults to full domain"
    )
    slice_height: Optional[Length_Value] = Field(
        None, description="The slice width, defaults to full domain"
    )
    resolution: Optional[Tuple[int, int]] = Field(
        (400, 400),
        description="the resolution at which to sample the slice",
    )
    periodic: Optional[bool] = Field(
        False, description="should the slice be periodic? default False."
    )


class SelectionObject(BaseModel):
    regions: Optional[List[Region]] = Field(
        None, description="a list of regions to load"
    )
    slices: Optional[List[Slice]] = Field(None, description="a list of slices to load")


class DataContainer(BaseModel):
    filename: str = Field(None, description="the filename for the dataset")
    selections: SelectionObject = Field(
        None, description="selections to load in this dataset"
    )
    store_in_cache: Optional[bool] = Field(
        ytcfg.get("yt_napari", "in_memory_cache"),
        description="if enabled, will store references to yt datasets.",
    )


class TimeSeriesFileSelection(BaseModel):
    directory: str = Field(None, description="The directory of the timseries")
    file_pattern: Optional[str] = Field(None, description="The file pattern to match")
    file_list: Optional[List[str]] = Field(None, description="List of files to load.")
    file_range: Optional[Tuple[int, int, int]] = Field(
        None,
        description="Given files matched by file_pattern, "
        "this option will select a range. Argument order"
        "is taken as start:stop:step.",
    )


class Timeseries(BaseModel):

    file_selection: TimeSeriesFileSelection
    selections: SelectionObject = Field(
        None, description="selections to load in this dataset"
    )
    load_as_stack: Optional[bool] = Field(
        False, description="If True, will stack images along a new dimension."
    )
    # process_in_parallel: Optional[bool] = Field(
    #     False, description="If True, will attempt to load selections in parallel."
    # )


class InputModel(BaseModel):
    datasets: List[DataContainer] = Field(
        None, description="list of dataset containers to load"
    )
    timeseries: List[Timeseries] = Field(None, description="List of timeseries to load")
    _schema_prefix = "yt-napari"


def _get_standard_schema_contents() -> Tuple[str, str]:
    prefix = InputModel._schema_prefix
    schema_contents = InputModel.schema_json(indent=2)
    return prefix, schema_contents


def _store_schema(schema_db: Optional[Union[PosixPath, str]] = None, **kwargs):
    # save the current data model as a new schema
    if schema_db is None:
        schema_db = PosixPath(inspect.getfile(_manager)).parent
    m = _manager.Manager(schema_db)
    prefix, schema_contents = _get_standard_schema_contents()
    m.write_new_schema(schema_contents, schema_prefix=prefix, **kwargs)
