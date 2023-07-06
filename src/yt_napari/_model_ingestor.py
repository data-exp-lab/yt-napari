from typing import List, Optional, Tuple, Union

import numpy as np
from unyt import unit_object, unit_registry, unyt_array

from yt_napari._data_model import DataContainer, InputModel
from yt_napari._ds_cache import dataset_cache


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
        self,
        left_edge: unyt_array,
        right_edge: unyt_array,
        resolution: tuple,
        n_d: int = 3,
    ):

        if len(left_edge) != len(right_edge):
            raise ValueError("length of edge arrays must match")

        if len(resolution) != len(left_edge):
            if len(resolution) == 1:
                resolution = resolution * n_d  # assume same in every dim
            else:
                raise ValueError("length of resolution does not match edge arrays")

        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center, self.width = _le_re_to_cen_wid(left_edge, right_edge)
        self.resolution = unyt_array(resolution)
        self.grid_width = self.width / self.resolution
        self.aspect_ratio = self.width / self.width[0]
        self.requires_scale = np.any(self.aspect_ratio != unyt_array(1.0, ""))
        self.n_d = n_d


# define types for the napari layer tuples
Layer = Tuple[np.ndarray, dict, str]
SpatialLayer = Tuple[np.ndarray, dict, str, LayerDomain]


class ReferenceLayer:
    # a layer to use as reference from which to calculate transformations for
    # aligning layers.

    def __init__(self, ref_layer_domain: LayerDomain):

        # copy over standard layer attributes
        self.left_edge = ref_layer_domain.left_edge
        self.right_edge = ref_layer_domain.right_edge
        self.center = ref_layer_domain.center
        self.width = ref_layer_domain.width
        self.resolution = ref_layer_domain.resolution
        self.grid_width = ref_layer_domain.grid_width
        self.aspect_ratio = ref_layer_domain.aspect_ratio

    def calculate_scale(self, other_layer: LayerDomain) -> unyt_array:
        # calculate the pixel scale for a layer relative to the reference

        # the scale accounts for different grid resolutions and is calculated
        # relative to the minimum grid resolution in each direction across
        # layers. scale > 1 will take a small number of pixels and stretch them
        # to cover more pixels. scale < 1 will shrink them.
        sc = other_layer.grid_width / self.grid_width

        # we also need to multiply by the initial reference layer aspect ratio
        # to account for any initial distortion.
        return sc * self.aspect_ratio

    def calculate_translation(self, other_layer: LayerDomain) -> unyt_array:
        # get the translation vector for another layer relative to the left edge
        # of the reference layer

        # the translation vector is in PIXELS, so get a translation vector in
        # physical units and then normalize by the reference grid width to get
        # the number of pixels required to offset. Furthermore, the screen
        # origin is in standard image coordinates (origin is bottom
        # left corner), so translate relative to left edge not the domain center
        return (other_layer.left_edge - self.left_edge) / self.grid_width

    def align_sanitize_layer(self, layer: SpatialLayer) -> Layer:
        # align and scale a single SpatialLayer relative to the reference layer,
        # return a standard Layer tuple

        # pull out the elements of the SpatialLayer tuple
        im_arr, im_kwargs, layer_type, domain = layer

        # calculate scale and translation
        scale = self.calculate_scale(domain)
        translate = self.calculate_translation(domain)

        # store these in the image layer keyword arguments only if they are used
        if np.any(scale != 1.0):
            im_kwargs["scale"] = scale.tolist()
        if np.any(translate != 0):
            im_kwargs["translate"] = translate.tolist()

        if "metadata" not in im_kwargs:
            im_kwargs["metadata"] = {}
        im_kwargs["metadata"]["_reference_layer"] = self

        # return a standard image layer tuple
        return (im_arr, im_kwargs, layer_type)

    def align_sanitize_layers(self, layer_list: List[SpatialLayer]) -> List[Layer]:
        # calculate scale and translation for each layer
        # will use the current domain extents if process_layers is False
        # (the default), otherwise the domain extent will be updated with the
        # layer_list
        return [self.align_sanitize_layer(layer) for layer in layer_list]


def create_metadata_dict(
    data: np.ndarray,
    layer_domain: LayerDomain,
    is_log: bool,
    reference_layer: Optional[ReferenceLayer] = None,
    **kwargs,
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
        _reference_layer :
            the ReferenceLayer object used in aligning this layer
    """
    md = {}
    md["_data_range"] = (data.min(), data.max())
    md["_layer_domain"] = layer_domain
    md["_is_log"] = is_log
    md["_yt_napari_layer"] = True
    md["_reference_layer"] = reference_layer
    for ky, val in kwargs.items():
        md[ky] = val
    return md


class PhysicalDomainTracker:
    # a container for tracking the domain coordinate extents across layers

    # the following track across layers
    left_edge: unyt_array = None
    right_edge: unyt_array = None
    center: unyt_array = None  # the true center of the domain
    width: unyt_array = None

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

        changed = False
        if unit is not None:
            if self.unit != unit:
                changed = True
                self.unit = unit

        if registry is not None:
            changed = True
            self.unit_registry = registry

        if changed:
            # re-initialize all the arrays so they have the proper registry
            for attr in ["left_edge", "right_edge", "center", "width"]:
                current = getattr(self, attr)
                if current is not None:
                    setattr(self, attr, self._register_array(current))

    def update_from_layer(
        self, layer_domain: LayerDomain, update_c_w: Optional[bool] = True
    ):
        """
        update the full extent of the domain given a new layer

        Parameters
        ----------
        layer_domain : LayerDomain
            the new layer to add
        update_c_w : Optional[bool]
            if True (default), will update the center and width value

        Note that if the current PhysicalDomainTracker does not have a grid_width
        value, then it will be set to that of layer_domain.
        """

        self.update_edges(
            left_edge=layer_domain.left_edge,
            right_edge=layer_domain.right_edge,
            update_c_w=update_c_w,
        )

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

    def _register_array(self, input_array: unyt_array) -> unyt_array:
        # return a new unyt array with proper registry in the expected unit
        new_array = unyt_array(input_array, registry=self.unit_registry)
        return self._sanitize_length(new_array)

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


def _load_3D_regions(ds, m_data: DataContainer, layer_list: list) -> list:

    for sel in m_data.selections.regions:
        # get the left, right edge as a unitful array, initialize the layer
        # domain tracking for this layer and update the global domain extent
        if sel.left_edge is None:
            LE = ds.domain_left_edge
        else:
            LE = ds.arr(sel.left_edge.value, sel.left_edge.unit)

        if sel.right_edge is None:
            RE = ds.domain_right_edge
        else:
            RE = ds.arr(sel.right_edge.value, sel.right_edge.unit)
        res = sel.resolution
        layer_domain = LayerDomain(left_edge=LE, right_edge=RE, resolution=res)

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


def _load_2D_slices(ds, m_data: DataContainer, layer_list: list) -> list:
    axis_id = ds.coordinates.axis_id
    for slice in m_data.selections.slices:
        if slice.normal == "":
            continue
        normal_ax = axis_id[slice.normal]

        if slice.center is None:
            c = ds.domain_center
        else:
            c = ds.arr(slice.center.value, slice.center.unit)

        slc = ds.slice(slice.normal, c[normal_ax])

        x_axis = axis_id[ds.coordinates.image_axis_name[slice.normal][0]]
        y_axis = axis_id[ds.coordinates.image_axis_name[slice.normal][1]]
        LE = ds.arr([0.0, 0.0], "code_length")
        RE = ds.arr([0.0, 0.0], "code_length")
        if slice.slice_width is None:
            w = ds.domain_width[x_axis]
        else:
            w = ds.quan(slice.slice_width.value, slice.slice_width.unit)
        LE[0] = c[x_axis] - w / 2.0
        RE[0] = c[x_axis] + w / 2.0

        if slice.slice_height is None:
            h = ds.domain_width[y_axis]
        else:
            h = ds.quan(slice.slice_height.value, slice.slice_height.unit)
        LE[1] = c[y_axis] - h / 2.0
        RE[1] = c[y_axis] + h / 2.0

        res = slice.resolution
        layer_domain = LayerDomain(left_edge=LE, right_edge=RE, resolution=res, n_d=2)

        frb = slc.to_frb(
            width=w,
            height=h,
            center=c,
            resolution=slice.resolution,
            periodic=slice.periodic,
        )

        for field_container in slice.fields:
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


def _process_validated_model(model: InputModel) -> List[SpatialLayer]:
    # return a list of layer tuples with domain information

    layer_list = []

    # our model is already validated, so we can assume the field exist with
    # their correct types. This is all the yt-specific code required to load a
    # dataset and return a plain numpy array
    for m_data in model.data:

        ds = dataset_cache.check_then_load(m_data.filename)
        if m_data.selections.regions is not None:
            layer_list = _load_3D_regions(ds, m_data, layer_list)
        if m_data.selections.slices is not None:
            layer_list = _load_2D_slices(ds, m_data, layer_list)

    return layer_list


def load_from_json(json_paths: List[str]) -> List[Layer]:

    layer_lists = []  # we will concatenate layers across json paths

    for json_path in json_paths:
        # InputModel is a pydantic class, the following will validate the json
        model = InputModel.parse_file(json_path)

        # now that we have a validated model, we can use the model attributes
        # to execute the code that will return our array for the image
        layer_lists += _process_validated_model(model)

    # now we need to align all our layers!
    # choose a reference layer -- using the first in the list at present, could
    # make this user configurable and/or use the layer with highest pixel density
    # as the reference so that high density layers do not lose resolution
    ref_layer = _choose_ref_layer(layer_lists)
    layer_lists = ref_layer.align_sanitize_layers(layer_lists)

    return layer_lists


def _choose_ref_layer(
    layer_list: List[SpatialLayer], method: Optional[str] = "first_in_list"
) -> ReferenceLayer:
    # decides on which layer to use as the reference
    if method == "first_in_list":
        print("using first in list")
        ref_layer_id = 0
    elif method == "smallest_volume":
        print("small vol")
        min_vol = None
        for layer_id, layer in enumerate(layer_list):
            ld = layer[3]  # the layer domain
            layer_vol = np.prod(ld.width)
            if min_vol is None:
                min_vol = layer_vol
                ref_layer_id = layer_id
            elif layer_vol < min_vol:
                min_vol = layer_vol
                ref_layer_id = layer_id
    else:
        vmeths = ("first_in_list", "smallest_volume")
        raise ValueError(f"method must be one of {vmeths}, found {method}")

    return ReferenceLayer(layer_list[ref_layer_id][3])
