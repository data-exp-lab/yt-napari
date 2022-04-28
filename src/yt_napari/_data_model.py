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
    fields: List[ytField]
    left_edge: Optional[Tuple[float, float, float]] = (0.0, 0.0, 0.0)
    right_edge: Optional[Tuple[float, float, float]] = (1.0, 1.0, 1.0)
    resolution: Optional[Tuple[int, int, int]] = (400, 400, 400)


class DataContainer(BaseModel):
    filename: str = Field(None, description="the filename for the dataset to load")
    selections: List[SelectionObject]
    edge_units: Optional[str] = Field(
        "code_length", description="the units to use for left_edge and right_edge"
    )


class InputModel(BaseModel):
    data: List[DataContainer]
    _schema_prefix = "yt-napari"


def _store_schema(schema_db: Optional[Union[PosixPath, str]] = None, **kwargs):
    # save the current data model as a new schema
    if schema_db is None:
        schema_db = PosixPath(inspect.getfile(_manager)).parent
    m = _manager.Manager(schema_db)
    prefix = InputModel._schema_prefix
    schema_contents = InputModel.schema_json(indent=2)
    m.write_new_schema(schema_contents, schema_prefix=prefix, **kwargs)
