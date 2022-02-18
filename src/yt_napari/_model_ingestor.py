from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from unyt import unit_object, unyt_array

from yt_napari._data_model import InputModel


def _le_re_to_cen_wid(
    left_edge: unyt_array, right_edge: unyt_array
) -> Tuple[unyt_array, unyt_array]:
    # return the center and width from a left and right edge
    center = (right_edge + left_edge) / 2.0
    width = right_edge - left_edge
    return center, width


class LayerDomain:
    # domain info for a single layer
    def __init__(self, left_edge: unyt_array, right_edge: unyt_array):
        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center, self.width = _le_re_to_cen_wid(left_edge, right_edge)


Layer = Tuple[np.ndarray, dict, str]
SpatialLayer = Tuple[np.ndarray, dict, str, LayerDomain]


class PhysicalDomainTracker:
    # a helpful container for tracking the domain coordinate extents in
    # physical units
    left_edge: unyt_array = None
    right_edge: unyt_array = None
    center: unyt_array = None
    width: unyt_array = None

    def __init__(self, unit: Union[str, unit_object.Unit] = "kpc"):
        self.unit = unit
        self.layer_extents = {}

    def update_unit(self, unit: Union[str, unit_object.Unit]):
        self.unit = unit

    def update_edges(
        self,
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        update_c_w: Optional[bool] = True,
    ):
        # update the left and/or the right edges. If update_c_w,
        # then width and center will be calculated and updated.
        edge_updated = False
        if left_edge is not None:
            new_edge = self._sanitize_input_edge(left_edge)
            edge_updated = True
            if self.left_edge is None:
                self.left_edge = new_edge
            else:
                new_edge = np.min([self.left_edge, new_edge], axis=0)
                self.left_edge = unyt_array(new_edge, self.unit)

        if right_edge is not None:
            new_edge = self._sanitize_input_edge(right_edge)
            edge_updated = True
            if self.right_edge is None:
                self.right_edge = new_edge
            else:
                new_edge = np.max([self.right_edge, new_edge], axis=0)
                self.right_edge = unyt_array(new_edge, self.unit)

        if edge_updated and update_c_w:
            self.update_width_and_center()

    def _sanitize_input_edge(self, input_edge: unyt_array):
        # ensures an input left/right edge are in correct units, necessary
        # because operations like np.min([unyt_array, unyt_array], axis=0)
        # will pull the value of the array without first converting units.
        return input_edge.to(self.unit)

    def update_width_and_center(self):
        # set the domain center and width based on current edges
        center_wid = _le_re_to_cen_wid(self.left_edge, self.right_edge)
        self.center, self.width = center_wid

    def align_sanitize_layers(self, layer_list: List[SpatialLayer]) -> List[Layer]:
        # calculate scale and translation for each layer using the
        # current domain extents, return a list of standard Layer tuple
        return [self.align_sanitize_layer(layer) for layer in layer_list]

    def align_sanitize_layer(self, layer: SpatialLayer) -> Layer:
        # align and scale a single SpatialLayer relative to the current domain
        # extents, return a standard Layer tuple

        # pull out the elements of the SpatialLayer tuple
        im_arr, im_kwargs, layer_type, domain = layer

        # image coordinates go from 0 to 1 in all dims, so in our full spatial
        # domain, self.width corresponds to an image width of 1. So we need to
        # normalize all distances by self.width
        scale = domain.width / self.width
        translate = (domain.center - self.center) / self.width  # sign here???

        # store these in the image layer keyword arguments only if they are
        # needed.
        if np.any(scale != 1.0):
            im_kwargs["scale"] = scale.tolist()
        if np.any(translate != 0):
            im_kwargs["translate"] = translate.tolist()

        # return a standard image layer tuple
        return (im_arr, im_kwargs, layer_type)


def _process_validated_model(
    model: InputModel, domain_info: PhysicalDomainTracker
) -> List[SpatialLayer]:
    # return a list of layer tuples with domain information

    layer_list = []

    # our model is already validated, so we can assume the fields exist with
    # their correct types. This is all the yt-specific code required to load a
    # dataset and return a plain numpy array

    ds = yt.load(model.dataset)

    for field_container in model.field_list:

        field = (field_container.field_type, field_container.field_name)

        # get the left, right edge as a unitful array, initialize the layer
        # domain tracking for this layer and update the global domain extent
        LE = ds.arr(model.left_edge, model.edge_units)
        RE = ds.arr(model.right_edge, model.edge_units)
        layer_domain = LayerDomain(left_edge=LE, right_edge=RE)
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

        layer_list.append((data, add_kwargs, layer_type, layer_domain))

    return layer_list


def load_from_json(json_paths: List[str]) -> List[Layer]:

    layer_lists = []  # we will concatenate layers across json paths

    domain_info = PhysicalDomainTracker()
    for i_path, json_path in enumerate(json_paths):
        # InputModel is a pydantic class, the following will validate the json
        model = InputModel.parse_file(json_path)

        if i_path == 0:
            # set the length unit to work in based on the first path
            domain_info.update_unit(model.edge_units)

        # now that we have a validated model, we can use the model attributes
        # to execute the code that will return our array for the image
        layer_lists += _process_validated_model(model, domain_info)

    # domain_info has tracked the overall domain here, so now we have the full
    # domain extent and can align and scale each layer
    domain_info.update_width_and_center()
    layer_lists = domain_info.align_sanitize_layers(layer_lists)

    return layer_lists
