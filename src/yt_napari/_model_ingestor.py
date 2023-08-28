import os
from collections import defaultdict
from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from unyt import unit_object, unit_registry, unyt_array, unyt_quantity

from yt_napari import _special_loaders
from yt_napari._data_model import (
    DataContainer,
    InputModel,
    Region,
    SelectionObject,
    Slice,
    Timeseries,
    TimeSeriesFileSelection,
)
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
    # left_edge, right_edge, resolution, n_d are all self explanatory.
    # other parameters:
    #
    # new_dim_value: optional unyt_quantity.
    #   If n_d == 2, and upgrade_to_3D is subsequently called, then this value
    #   will be used for the new
    # new_dim_axis: optional int.
    #   the index position to add the new_dim_position, default is last
    def __init__(
        self,
        left_edge: unyt_array,
        right_edge: unyt_array,
        resolution: tuple,
        n_d: Optional[int] = 3,
        new_dim_value: Optional[unyt_quantity] = None,
        new_dim_axis: Optional[int] = 2,
    ):

        if len(left_edge) != len(right_edge):
            raise ValueError("length of edge arrays must match")

        if len(resolution) != len(left_edge):
            if len(resolution) == 1:
                resolution = resolution * n_d  # assume same in every dim
            else:
                msg = f"{len(resolution)}:{len(left_edge)}"
                raise ValueError(
                    f"length of resolution does not match edge arrays {msg}"
                )

        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center, self.width = _le_re_to_cen_wid(left_edge, right_edge)
        self.resolution = unyt_array(resolution)
        self.grid_width = self.width / self.resolution
        self.aspect_ratio = self.width / self.width[0]
        self.requires_scale = np.any(self.aspect_ratio != unyt_array(1.0, ""))
        self.n_d = n_d
        if new_dim_value is None:
            new_dim_value = unyt_quantity(0.0, left_edge.units)
        self.new_dim_value = new_dim_value
        self.new_dim_axis = new_dim_axis

    def upgrade_to_3D(self):
        # note: this is not (yet) used when loading planes in 3d scenes.
        if self.n_d == 3:
            return  # already 3D, nothing to do

        if self.n_d == 2:
            new_l_r = self.new_dim_value
            axid = self.new_dim_axis
            self.left_edge = _insert_to_unyt_array(self.left_edge, new_l_r, axid)
            self.right_edge = _insert_to_unyt_array(self.right_edge, new_l_r, axid)
            self.resolution = _insert_to_unyt_array(self.right_edge, 1, axid)
            self.grid_width = _insert_to_unyt_array(self.grid_width, 0, axid)
            self.aspect_ratio = _insert_to_unyt_array(self.aspect_ratio, 1.0, axid)
            self.n_d = 3


def _insert_to_unyt_array(
    x: unyt_array, new_value: Union[float, unyt_array], position: int
) -> unyt_array:
    # just for scalars
    if isinstance(new_value, unyt_array):
        # reminder: unyt_quantity is instance of unyt_array
        new_value = new_value.to(x.units).d

    return unyt_array(np.insert(x.d, position, new_value), x.units)


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

        # and store the full domain
        self.layer_domain = ref_layer_domain

    def calculate_scale(self, other_layer: LayerDomain) -> unyt_array:
        # calculate the pixel scale for a layer relative to the reference

        # the scale accounts for different grid resolutions and is calculated
        # relative to the minimum grid resolution in each direction across
        # layers. scale > 1 will take a small number of pixels and stretch them
        # to cover more pixels. scale < 1 will shrink them.
        sc = other_layer.grid_width / self.grid_width
        sc[sc == 0] = 1.0

        # we also need to account for any initial distortion relative to ref
        # layer
        return sc / self.aspect_ratio

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

        # bypass if adding a 2d layer
        if domain.n_d == 2 and self.layer_domain.n_d == 3:
            # when mixing 2d and 3d selections, cannot guarantee alignment
            # or scaling, simply return with no adjustment
            return (im_arr, im_kwargs, layer_type)

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


def selections_match(sel_1: Union[Slice, Region], sel_2: Union[Slice, Region]) -> bool:
    # compare selections, ignoring fields
    if not type(sel_2) == type(sel_1):
        return False

    for attr in sel_1.__fields__.keys():
        if attr != "fields":
            val_1 = getattr(sel_1, attr)
            val_2 = getattr(sel_2, attr)
            if val_2 != val_1:
                return False

    return True


class TimeseriesContainer:
    # for storing image layers across timesteps by selections
    def __init__(self):
        self.layers_in_selections = defaultdict(lambda: [])
        self.selection_objs = {}
        self.selection_field = {}

    def check_for_selection(
        self, selection: Union[Slice, Region], current_field: Tuple[str, str]
    ) -> int:
        for sel_id, sel_obj in self.selection_objs.items():
            sel_field = self.selection_field[sel_id]
            if selections_match(sel_obj, selection) and current_field == sel_field:
                return sel_id

        # does not exist yet, add it
        sel_id = len(self.selection_objs)
        self.selection_objs[sel_id] = selection
        self.selection_field[sel_id] = current_field
        return sel_id

    def add(
        self,
        selection: Union[Slice, Region],
        current_field: Tuple[str, str],
        new_layer: SpatialLayer,
    ):
        sel_id = self.check_for_selection(selection, current_field)

        (im, im_kwargs, im_label, layer_domain) = new_layer
        if layer_domain.requires_scale:
            im_kwargs["scale"] = 1.0 / layer_domain.aspect_ratio
            new_layer = (im, im_kwargs, im_label, layer_domain)

        self.layers_in_selections[sel_id].append(new_layer)

    def concat_by_selection_id(self, id: int) -> Layer:
        the_layers = self.layers_in_selections[id]
        if len(the_layers) == 1:
            return the_layers[0]
        if len(the_layers) == 0:
            return None

        # assuming that im_kwargs, layer_type do not change. also dr
        _, im_kwargs, layer_type, domain = the_layers[0]
        im_arrays = [im[0] for im in the_layers]
        im = np.stack(im_arrays, axis=0)  # this operation will preserve dask arrays
        return im, im_kwargs, layer_type

    def concat_by_selection(self):
        return [self.concat_by_selection_id(id) for id in self.selection_objs.keys()]

    @property
    def layer_list(self) -> List[Layer]:
        layer_list = []
        for layers in self.layers_in_selections.values():
            for im_data, im_kwargs, layer_type, _ in layers:
                layer_list.append((im_data, im_kwargs, layer_type))
        return layer_list


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


def _load_3D_regions(
    ds,
    selections: SelectionObject,
    layer_list: list,
    timeseries_container: Optional[TimeseriesContainer] = None,
) -> list:

    for sel in selections.regions:
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

            new_layer = (data, add_kwargs, layer_type, layer_domain)
            layer_list.append(new_layer)
            if timeseries_container is not None:
                timeseries_container.add(sel, field, new_layer)

    return layer_list


def _process_slice(
    ds,
    normal: Union[str, int],
    center: Optional[unyt_array] = None,
    width: Optional[unyt_quantity] = None,
    height: Optional[unyt_quantity] = None,
    resolution: Optional[Tuple[int, int]] = (400, 400),
    periodic: Optional[bool] = False,
) -> tuple:
    # returns a slice frb and a LayerDomain for a slice
    axis_id = ds.coordinates.axis_id
    normal_ax = axis_id[normal]
    x_axis = axis_id[ds.coordinates.image_axis_name[normal][0]]
    y_axis = axis_id[ds.coordinates.image_axis_name[normal][1]]

    if center is None:
        center = ds.domain_center
    if width is None:
        width = ds.domain_width[x_axis]
    if height is None:
        height = ds.domain_width[y_axis]

    LE = ds.arr([0.0, 0.0], "code_length")
    RE = ds.arr([0.0, 0.0], "code_length")
    LE[0] = center[x_axis] - width / 2.0
    RE[0] = center[x_axis] + width / 2.0
    LE[1] = center[y_axis] - height / 2.0
    RE[1] = center[y_axis] + height / 2.0

    slc = ds.slice(normal_ax, center[normal_ax])
    frb = slc.to_frb(
        width=width,
        height=height,
        center=center,
        resolution=resolution,
        periodic=periodic,
    )

    layer_domain = LayerDomain(
        left_edge=LE,
        right_edge=RE,
        resolution=resolution,
        n_d=2,
        new_dim_axis=2,
        new_dim_value=0.0,
    )

    return frb, layer_domain


def _load_2D_slices(
    ds,
    selections: SelectionObject,
    layer_list: list,
    timeseries_container: Optional[TimeseriesContainer] = None,
) -> list:

    for slice in selections.slices:

        if slice.center is None:
            c = None
        else:
            c = ds.arr(slice.center.value, slice.center.unit)

        if slice.slice_width is None:
            w = None
        else:
            w = ds.quan(slice.slice_width.value, slice.slice_width.unit)

        if slice.slice_height is None:
            h = None
        else:
            h = ds.quan(slice.slice_height.value, slice.slice_height.unit)

        frb, layer_domain = _process_slice(
            ds,
            slice.normal,
            center=c,
            width=w,
            height=h,
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
            new_layer = (data, add_kwargs, layer_type, layer_domain)
            layer_list.append(new_layer)
            if timeseries_container is not None:
                timeseries_container.add(slice, field, new_layer)

    return layer_list


def _load_selections_from_ds(
    ds,
    selections: SelectionObject,
    layer_list: List[SpatialLayer],
    timeseries_container: Optional[TimeseriesContainer] = None,
) -> List[SpatialLayer]:
    if selections.regions is not None:
        layer_list = _load_3D_regions(
            ds, selections, layer_list, timeseries_container=timeseries_container
        )
    if selections.slices is not None:
        layer_list = _load_2D_slices(
            ds, selections, layer_list, timeseries_container=timeseries_container
        )
    return layer_list


def _load_dataset_selections(
    m_data: DataContainer, layer_list: List[SpatialLayer]
) -> List[SpatialLayer]:
    ds = dataset_cache.check_then_load(m_data.filename)
    return _load_selections_from_ds(ds, m_data.selections, layer_list)


def _validate_files(files):

    valid_files = [f for f in files if os.path.isfile(f)]

    if len(valid_files) == 0:
        # try the yt directory
        yt_data_dir = yt.config.ytcfg.get("yt", "test_data_dir")
        test_files = [os.path.join(yt_data_dir, f) for f in files]
        valid_files = [f for f in test_files if os.path.isfile(f)]

    return valid_files


def _generate_file_list(fpat, fdir=None):
    import glob

    # try with
    match_this = fpat
    if fdir is not None:
        match_this = os.path.join(fdir, match_this)

    files = glob.glob(match_this)
    if len(files) == 0:
        yt_data_dir = yt.config.ytcfg.get("yt", "test_data_dir")
        files = glob.glob(os.path.join(yt_data_dir, match_this))

    files.sort()
    return files


def _find_timeseries_files(file_selection: TimeSeriesFileSelection):

    fdir = file_selection.directory
    fpat = file_selection.file_pattern
    frange = file_selection.file_range

    if file_selection.file_list is not None:
        # we have a list of files, load them explicitly as dataseries
        files = file_selection.file_list
        if fdir is not None:
            files = [os.path.join(fdir, fi) for fi in files]
        return _validate_files(files)

    if fpat is None:
        fpat = "*"

    files = _generate_file_list(fpat, fdir)
    if frange is not None:
        # limit the selected files
        f1, f2, f3 = frange
        if f2 > len(files):
            f2 = len(files)
        picked_files = [files[fileid] for fileid in range(f1, f2, f3)]
        return picked_files

    return files


def _load_timeseries(m_data: Timeseries, layer_list: list) -> list:

    files = _find_timeseries_files(m_data.file_selection)

    # process_in_parallel = False  # future model attribute

    tc = TimeseriesContainer()
    temp_list = []
    for file in files:
        # note: managing the files independently makes parallel approaches
        # without MPI feasible. in some limited testing, this actually
        # was thread safe with logging disabled, so it is possible to
        # build dask arrays pretty easily for single regions and single
        # fields.
        ds = _load_with_timeseries_specials_check(file)
        sels = m_data.selections
        temp_list = _load_selections_from_ds(
            ds, sels, temp_list, timeseries_container=tc
        )

    if m_data.load_as_stack is False:
        new_layers = tc.layer_list
    else:
        new_layers = tc.concat_by_selection()

    for layer in new_layers:
        layer_list.append(layer)
    return layer_list


def _process_validated_model(
    model: InputModel,
) -> Tuple[List[SpatialLayer], List[Layer]]:
    # return a list of layer tuples with domain information

    if model.datasets is None:
        model.datasets = []

    if model.timeseries is None:
        model.timeseries = []

    layer_list = []
    # our model is already validated, so we can assume the field exist with
    # their correct types. This is all the yt-specific code required to load a
    # dataset and return a plain numpy array
    for m_data in model.datasets:
        layer_list = _load_dataset_selections(m_data, layer_list)

    timeseries_layers = []
    for m_data in model.timeseries:
        timeseries_layers = _load_timeseries(m_data, timeseries_layers)

    return layer_list, timeseries_layers


def load_from_json(json_paths: List[str]) -> List[Layer]:

    layer_lists = []  # we will concatenate layers across json paths
    timeseries_layers = []  # timeseries layers handled separately
    for json_path in json_paths:
        # InputModel is a pydantic class, the following will validate the json
        model = InputModel.parse_file(json_path)

        # now that we have a validated model, we can use the model attributes
        # to execute the code that will return our array for the image
        layer_lists_j, timeseries_layers_j = _process_validated_model(model)
        timeseries_layers += timeseries_layers_j
        layer_lists += layer_lists_j

    # now we need to align all our layers!
    # choose a reference layer -- using the first in the list at present, could
    # make this user configurable and/or use the layer with highest pixel density
    # as the reference so that high density layers do not lose resolution
    if len(layer_lists) > 0:
        ref_layer = _choose_ref_layer(layer_lists)
        layer_lists = ref_layer.align_sanitize_layers(layer_lists)

    # timeseries layers are internally aligned
    out_layers = layer_lists + timeseries_layers
    return out_layers


def _choose_ref_layer(
    layer_list: List[SpatialLayer], method: Optional[str] = "first_in_list"
) -> ReferenceLayer:
    # decides on which layer to use as the reference
    if method == "first_in_list":
        ref_layer_id = 0
    elif method == "smallest_volume":
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


def _load_with_timeseries_specials_check(file):
    fname = os.path.basename(file)
    if fname.startswith("_ytnapari") and "-" in fname:
        # check form of, e.g., _ytnapari_load_grid-001
        loader, _ = str(fname).split("-")
        if hasattr(_special_loaders, loader):
            ds = getattr(_special_loaders, loader)()
        else:
            msg = (
                f"The special loader function, yt_napari._special_loaders.{loader} "
                f"does not exist."
            )
            raise AttributeError(msg)
    else:
        ds = yt.load(file)
    return ds
