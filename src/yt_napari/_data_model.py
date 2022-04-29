import inspect
from pathlib import PosixPath
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from yt_napari.schemas import _manager


class ytField(BaseModel):
    field_type: str = Field(None, description="a field type in the yt dataset")
    field_name: str = Field(None, description="a field in the yt dataset")
    take_log: Optional[bool] = Field(
        True, description="if true, will apply log10 to the selected data"
    )


class SelectionObject(BaseModel):
    fields: List[ytField] = Field(
        None, description="list of fields to load for this selection"
    )
    left_edge: Optional[Tuple[float, float, float]] = Field(
        (0.0, 0.0, 0.0),
        description="the left edge (min x, min y, min z) in units of edge_units",
    )
    right_edge: Optional[Tuple[float, float, float]] = Field(
        (1.0, 1.0, 1.0),
        description="the right edge (max x, max y, max z) in units of edge_units",
    )
    resolution: Optional[Tuple[int, int, int]] = Field(
        (400, 400, 400),
        description="the resolution at which to sample between the edges.",
    )


class DataContainer(BaseModel):
    filename: str = Field(None, description="the filename for the dataset")
    selections: List[SelectionObject] = Field(
        None, description="list of selections to load in this dataset"
    )
    edge_units: Optional[str] = Field(
        "code_length",
        description="the units to use for left_edge and right_edge in the selections",
    )


class InputModel(BaseModel):
    data: List[DataContainer] = Field(None, description="list of datasets to load")
    _schema_prefix = "yt-napari"


def _store_schema(schema_db: Optional[Union[PosixPath, str]] = None, **kwargs):
    # save the current data model as a new schema
    if schema_db is None:
        schema_db = PosixPath(inspect.getfile(_manager)).parent
    m = _manager.Manager(schema_db)
    prefix = InputModel._schema_prefix
    schema_contents = InputModel.schema_json(indent=2)
    m.write_new_schema(schema_contents, schema_prefix=prefix, **kwargs)
