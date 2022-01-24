from pydantic import BaseModel
from typing import Optional, Tuple, List, Union
from pathlib import PosixPath
import inspect
from yt_napari.schemas import _manager


class InputModel(BaseModel):

    dataset: str
    field_type: str
    field_name: str

    left_edge: Optional[Tuple[float, float, float]] = [0., 0., 0.]
    right_edge: Optional[Tuple[float, float, float]] = [1., 1., 1.]
    edge_units: Optional[str] = "code_length"
    resolution: Optional[Tuple[int, int, int]] = [400, 400, 400]
    take_log: Optional[bool] = True

    _schema_prefix = "yt-napari"


def _store_schema(schema_db: Optional[Union[PosixPath, str]]=None,
                  **kwargs):
    # save the current data model as a new schema
    if schema_db is None:
        schema_db = PosixPath(inspect.getfile(_manager)).parent
    m = _manager.Manager(schema_db)
    prefix = InputModel._schema_prefix
    m.write_new_schema(InputModel.schema_json(indent=2),
                       schema_prefix=prefix,
                       **kwargs)






