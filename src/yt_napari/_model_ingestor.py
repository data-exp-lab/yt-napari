import numpy as np
import yt

from yt_napari._data_model import InputModel


def _validate_edges(ds, model):
    LE = ds.arr(model.left_edge, model.edge_units)
    RE = ds.arr(model.right_edge, model.edge_units)
    return LE, RE


def load_from_json(json_path: str):
    model = InputModel.parse_file(json_path)

    ds = yt.load(model.dataset)
    field = (model.field_type, model.field_name)
    # To do: check for field in ds

    LE, RE = _validate_edges(ds, model)

    # create the fixed resolution buffer
    frb = ds.r[
        LE[0] : RE[0] : complex(0, model.resolution[0]),  # noqa: E203
        LE[1] : RE[1] : complex(0, model.resolution[1]),  # noqa: E203
        LE[2] : RE[2] : complex(0, model.resolution[2]),  # noqa: E203
    ]

    data = frb[field]

    if model.take_log:
        return np.log10(data)

    return data
