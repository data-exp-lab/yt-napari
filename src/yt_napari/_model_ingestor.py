from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from unyt import unit_object, unit_registry, unyt_array

from yt_napari._data_model import InputModel


def _le_re_to_cen_wid(
    left_edge: unyt_array, right_edge: unyt_array
) -> Tuple[unyt_array, unyt_array]:
    # return the center and width from a left and right edge
    center = (right_edge + left_edge) / 2.0
    width = right_edge - left_edge
    return center, width


class LayerDomain:
    # container for domain info for a single layer
    def __init__(
        self, left_edge: unyt_array, right_edge: unyt_array, resolution: tuple
    ):

        if len(left_edge) != len(right_edge):
            raise ValueError("length of edge arrays must match")

        if len(resolution) != len(left_edge):
            if len(resolution) == 1:
                resolution = resolution * 3  # assume same in every dim
            else:
                raise ValueError("length of resolution does not match edge arrays")

        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center, self.width = _le_re_to_cen_wid(left_edge, right_edge)
        self.resolution = unyt_array(resolution)
        self.grid_width = self.width / self.resolution


def create_metadata_dict(
    data: np.ndarray, layer_domain: LayerDomain, is_log: bool, **kwargs
) -> dict:
    """
    returns a metadata dict with some consistent keys for helping yt-napari
    functionality

    Parameters
    ----------
    data :
        the image data for the new layer
    layer_domain :
        the LayerDomain object of the new layer
    is_log :
        True if the data has been logged
    kwargs :
        any additional keyword arguments will be added to the dict

    Returns
    -------
    dict
        a metadata dict for napari with some consistent key-value pairs, will
        always include the following:
        _data_range : Tuple(float, float)
            the min/max value of the supplied data
        _layer_domain :
            the LayerDomain object of the new layer
        _is_log :
            True if the data has been logged
        _yt_napari_layer :
            bool, always True.
    """
    md = {}
    md["_data_range"] = (data.min(), data.max())
    md["_layer_domain"] = layer_domain
    md["_is_log"] = is_log
    md["_yt_napari_layer"] = True
    for ky, val in kwargs.items():
        md[ky] = val
    return md


Layer = Tuple[np.ndarray, dict, str]
SpatialLayer = Tuple[np.ndarray, dict, str, LayerDomain]


class PhysicalDomainTracker:
    # a container for tracking the domain coordinate extents in
    # physical units for handling alignmnet between layers
    left_edge: unyt_array = None
    right_edge: unyt_array = None
    center: unyt_array = None  # the true center of the domain
    width: unyt_array = None
    grid_width: unyt_array = None
    scene_center: unyt_array = None  # user-supplied center to align

    def __init__(
        self,
        unit: Optional[Union[str, unit_object.Unit]] = "kpc",
        registry: Optional[unit_registry.UnitRegistry] = None,
    ):

        self.unit = None
        self.unit_registry = None
        self.update_unit_info(unit=unit, registry=registry)

    def update_unit_info(
        self,
        unit: Union[str, unit_object.Unit] = None,
        registry: Optional[unit_registry.UnitRegistry] = None,
    ):

        if unit == "code_length" and registry is None:
            raise ValueError("To use 'code_length', you must provide a unit_registry")

        if unit is not None:
            self.unit = unit

        if registry is not None:
            self.unit_registry = registry

    def update_from_layer(
        self, layer_domain: LayerDomain, update_c_w: Optional[bool] = True
    ):
        # update the full domain edges and effective grid width
        self.update_edges(
            left_edge=layer_domain.left_edge,
            right_edge=layer_domain.right_edge,
            update_c_w=update_c_w,
        )
        self.update_grid_width(layer_domain.grid_width)

    def update_grid_width(self, grid_width: unyt_array):
        # grid_width is the width of a single pixel in physical units. the
        # full domain tracks the smallest width, which is used for scaling
        # the pixels of each layer.

        grid_width = self._sanitize_length(grid_width)
        if self.grid_width is None:
            self.grid_width = grid_width
        else:
            new_gw = np.min([self.grid_width, grid_width], axis=0)
            self.grid_width = unyt_array(new_gw, self.unit)

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
            new_edge = self._sanitize_length(left_edge)
            edge_updated = True
            if self.left_edge is None:
                self.left_edge = new_edge
            else:
                new_edge = np.min([self.left_edge, new_edge], axis=0)
                self.left_edge = self._arr(new_edge, self.unit)

        if right_edge is not None:
            new_edge = self._sanitize_length(right_edge)
            edge_updated = True
            if self.right_edge is None:
                self.right_edge = new_edge
            else:
                new_edge = np.max([self.right_edge, new_edge], axis=0)
                # will not have code length
                self.right_edge = self._arr(new_edge, self.unit)

        if edge_updated and update_c_w:
            self.update_width_and_center()

    def _arr(self, x: np.ndarray, unit):
        # return an array with the full unit registry (handles code_length)
        return unyt_array(x, unit, registry=self.unit_registry)

    def _sanitize_length(self, input_edge: unyt_array):
        # ensures an input left/right edge are in correct units, necessary
        # because operations like np.min([unyt_array, unyt_array], axis=0)
        # will pull the value of the array without first converting units.
        return input_edge.to(self.unit)

    def update_width_and_center(self):
        # set the domain center and width based on current edges
        center_wid = _le_re_to_cen_wid(self.left_edge, self.right_edge)
        self.center, self.width = center_wid

    def set_scene_center(self, scene_center: unyt_array, update_c_w: bool = True):
        self.scene_center = scene_center.to(self.unit)

    def align_sanitize_layers(
        self, layer_list: List[SpatialLayer], process_layers: bool = False
    ) -> List[Layer]:
        # calculate scale and translation for each layer
        # will use the current domain extents if process_layers is False
        # (the default), otherwise the domain extent will be updated with the
        # layer_list
        if process_layers:
            for _, _, _, domain in layer_list:
                self.update_from_layer(domain, update_c_w=False)
            self.update_width_and_center()

        return [self.align_sanitize_layer(layer) for layer in layer_list]

    def align_sanitize_layer(self, layer: SpatialLayer) -> Layer:
        # align and scale a single SpatialLayer relative to the current domain
        # extents, return a standard Layer tuple

        if self.grid_width is None:
            raise RuntimeError("grid_width is not set!")

        # pull out the elements of the SpatialLayer tuple
        im_arr, im_kwargs, layer_type, domain = layer

        # the scale accounts for different grid resolutions and is calculated
        # relative to the minimum grid resolution in each direction across
        # layers. scale > 1 will take a small number of pixels and stretch them
        # to cover more pixels. Since we are scaling by the minimum grid_width,
        # scale >= 1  always. This avoids shrinking a fine resolution grid to
        # fewer screen-pixels (i.e., finest spacing is the width of one image
        # pixel).
        scale = domain.grid_width / self.grid_width

        # translation vector is in PIXELS, so get a translation vector in
        # physical units and then normalize by the reference grid width to get
        # the number of pixels required to offset. Furthermore, the screen
        # origin is in standard image coordinates (origin is bottom
        # left corner), so translate relative to left edge not the domain center
        if self.scene_center is not None:
            # the user provided a scene center, so use it!
            origin = self.scene_center
        else:
            # no user-provided center, use the calculated domain center
            origin = self.left_edge
        translate = (domain.left_edge - origin) / self.grid_width

        # store these in the image layer keyword arguments only if they are used
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

    # our model is already validated, so we can assume the field exist with
    # their correct types. This is all the yt-specific code required to load a
    # dataset and return a plain numpy array
    for m_data in model.data:

        ds = yt.load(m_data.filename)

        if domain_info.unit_registry is None:
            # this happens only once, so if using 'code_length', the datasets need
            # to have the same `code_length`, which is not verified...
            domain_info.update_unit_info(
                unit=m_data.edge_units, registry=ds.unit_registry
            )

        for sel in m_data.selections:
            # get the left, right edge as a unitful array, initialize the layer
            # domain tracking for this layer and update the global domain extent
            LE = ds.arr(sel.left_edge, m_data.edge_units)
            RE = ds.arr(sel.right_edge, m_data.edge_units)
            res = sel.resolution
            layer_domain = LayerDomain(left_edge=LE, right_edge=RE, resolution=res)
            domain_info.update_from_layer(layer_domain, update_c_w=False)

            # create the fixed resolution buffer
            frb = ds.r[
                LE[0] : RE[0] : complex(0, res[0]),  # noqa: E203
                LE[1] : RE[1] : complex(0, res[1]),  # noqa: E203
                LE[2] : RE[2] : complex(0, res[2]),  # noqa: E203
            ]

            for field_container in sel.fields:
                field = (field_container.field_type, field_container.field_name)

                data = frb[field]  # extract the field (the slow part)
                if field_container.take_log:
                    data = np.log10(data)

                # create a metadata dict and set a name
                fieldname = ":".join(field)
                md = create_metadata_dict(data, layer_domain, field_container.take_log)
                add_kwargs = {"name": fieldname, "metadata": md}
                layer_type = "image"

                layer_list.append((data, add_kwargs, layer_type, layer_domain))

    return layer_list


def load_from_json(json_paths: List[str]) -> List[Layer]:

    layer_lists = []  # we will concatenate layers across json paths

    domain_info = PhysicalDomainTracker()
    for json_path in json_paths:
        # InputModel is a pydantic class, the following will validate the json
        model = InputModel.parse_file(json_path)

        # now that we have a validated model, we can use the model attributes
        # to execute the code that will return our array for the image
        layer_lists += _process_validated_model(model, domain_info)

    # domain_info has tracked the overall domain here, so now we have the full
    # domain extent and can align and scale each layer
    domain_info.update_width_and_center()
    layer_lists = domain_info.align_sanitize_layers(layer_lists)

    return layer_lists
