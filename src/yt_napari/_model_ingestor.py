from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from unyt import unit_object, unyt_array

from yt_napari._data_model import InputModel

Layer = Tuple[np.ndarray, dict, str]


class PhysicalDomainTracker:
    # a helpful container for tracking the domain coordinate extents in
    # physical units
    left_edge: unyt_array = None
    right_edge: unyt_array = None
    domain_center: unyt_array = None
    domain_width: unyt_array = None

    def __init__(self, unit: Union[str, unit_object.Unit] = "kpc"):
        self.unit = unit

    def update_unit(self, unit: Union[str, unit_object.Unit]):
        self.unit = unit

    def update_edges(
        self,
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        update_c_w: Optional[bool] = True,
    ):
        # update the left and/or the right edges. If update_c_w,
        # then domain_width and domain_center will be calculated and updated.
        if left_edge:
            new_edge = self._sanitize_input_edge(left_edge)
            new_edge = np.min([self.left_edge, new_edge], axis=0)
            self.left_edge = unyt_array(new_edge, self.units)

        if right_edge:
            new_edge = self._sanitize_input_edge(right_edge)
            new_edge = np.max([self.right_edge, new_edge], axis=0)
            self.right_edge = unyt_array(new_edge, self.units)

        if (left_edge or right_edge) and update_c_w:
            self.update_width_and_center()

    def _sanitize_input_edge(self, input_edge: unyt_array):
        # ensures an input left or right edge in in consistent units
        return input_edge.to(self.unit)

    def update_width_and_center(self):
        self.domain_center = (self.left_edge + self.right_edge) / 2.0
        self.domain_width = self.right_edge - self.left_edge

    def align_layers(self, layer_list: List[Layer]) -> List[Layer]:
        # calculate scale and translation for each layer
        for layer in layer_list:
            # calculate scale

            # calculate translation
            pass

        return layer_list


def _process_validated_model(
    model: InputModel, domain_info: PhysicalDomainTracker
) -> List[Layer]:
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

        # update the domain tracker
        domain_info.update_edges(left_edge=LE, right_edge=RE, update_c_w=False)

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


def load_from_json(json_paths: List[str]) -> List[Layer]:

    layer_lists = []  # we will concatenate layers across json paths

    domain_info = PhysicalDomainTracker()
    for i_path, json_path in enumerate(json_paths):
        # InputModel is a pydantic class, the following will validate the json
        model = InputModel.parse_file(json_path)

        if i_path == 0:
            domain_info.update_unit(model.edge_units)

        # now that we have a validated model, we can use the model attributes
        # to execute the code that will return our array for the image
        layer_lists += _process_validated_model(model, domain_info)

    if len(json_paths) > 1:
        # domain_info has tracked the overall domain here, so now we can
        # iterate through the layers and align them all
        layer_lists = domain_info.align_layers(layer_lists)

    return layer_lists
