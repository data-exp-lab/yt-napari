from typing import List, Tuple

import numpy as np
import yt

from yt_napari._data_model import InputModel

Layer = Tuple[np.ndarray, dict, str]


def _process_validated_model(model: InputModel) -> List[Layer]:
    # return a list of napari layer-tuples

    layer_list = []

    # our model is already validated, so we can assume the fields exist with
    # their correct types. This is all the yt-specific code required to load a
    # dataset and return a plain numpy array

    ds = yt.load(model.dataset)

    for field_container in model.field_list:

        field = (field_container.field_type, field_container.field_name)

        # get the left, right edge as a unitful array
        LE = ds.arr(model.left_edge, model.edge_units)
        RE = ds.arr(model.right_edge, model.edge_units)

        # create the fixed resolution buffer
        frb = ds.r[
            LE[0] : RE[0] : complex(0, model.resolution[0]),  # noqa: E203
            LE[1] : RE[1] : complex(0, model.resolution[1]),  # noqa: E203
            LE[2] : RE[2] : complex(0, model.resolution[2]),  # noqa: E203
        ]

        data = frb[field]  # extract the field (the slow part)
        if field_container.take_log:
            data = np.log10(data)

        # writing the full pydanctic model dict to the metadata attribute for
        # now -- this does not actually seem to get displayed though.
        fieldname = ":".join(field)
        add_kwargs = {"name": fieldname, "metadata": model.dict()}
        layer_type = "image"

        layer_list.append((data, add_kwargs, layer_type))

    return layer_list


def load_from_json(json_path: str) -> List[Layer]:

    # InputModel is a pydantic class, the following will validate the json
    model = InputModel.parse_file(json_path)

    # now that we have a validated model, we can use the model attributes to
    # execute the code that will actually return our array for the image
    return _process_validated_model(model)
