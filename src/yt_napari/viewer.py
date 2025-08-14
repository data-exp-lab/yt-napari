import warnings
from typing import Any, List, Optional, Set, Tuple, Union

import numpy as np
import yt
from napari import Viewer
from napari.components.layerlist import LayerList
from napari.layers import Layer
from napari.layers.utils._link_layers import get_linked_layers
from unyt import unyt_array, unyt_quantity
from yt.data_objects.static_output import Dataset as ytDataset

import yt_napari._model_ingestor as _mi
from yt_napari.logging import ytnapari_log


def _check_for_reference_layer(
    napari_layer_list: LayerList,
) -> Optional[_mi.ReferenceLayer]:
    # check the napari viewer layer list for an existing reference layer
    for layer in napari_layer_list:
        if "_yt_napari_layer" in layer.metadata:
            if layer.metadata["_reference_layer"] is not None:
                return layer.metadata["_reference_layer"]
    return None


class Scene:
    def __init__(self, reference_layer: Optional[_mi.ReferenceLayer] = None):
        self._reference_layer = reference_layer

    def _check_for_reference_layer(
        self, current_layers: list
    ) -> Optional[_mi.ReferenceLayer]:
        return _check_for_reference_layer(current_layers)

    def _get_reference_layer(
        self,
        layer_list: List[Layer],
        default_if_missing: Optional[_mi.LayerDomain] = None,
    ):
        if len(layer_list) == 0:
            # always check, in case all layers have been deleted.
            self._reference_layer = None

        if self._reference_layer is None:
            # first check the active layers for a reference
            ref_layer = self._check_for_reference_layer(layer_list)
            if ref_layer is None:
                # still None, use this layer:
                layer_domain = default_if_missing
                ref_layer = _mi.ReferenceLayer(layer_domain)
            self._reference_layer = ref_layer
        return self._reference_layer

    def _add_to_scene(
        self,
        viewer: Viewer,
        data,
        layer_domain,
        field,
        take_log,
        colormap=None,
        link_to=None,
        rescale=False,
        **kwargs,
    ):
        # adds any new data to the viewer

        if rescale:
            data = _mi._linear_rescale(data)

        if colormap is None:
            colormap = "viridis"

        # initialize the spatial layer then sanitize it
        splayer = (data, {}, "image", layer_domain)
        ref_layer = self._get_reference_layer(
            viewer.layers, default_if_missing=layer_domain
        )
        _, im_kwargs, _ = ref_layer.align_sanitize_layer(splayer)

        # extract the translate and scale values
        tr = im_kwargs.get("translate", None)
        sc = im_kwargs.get("scale", None)
        # check that the user has not supplied translate or scale separately
        for attr in ["translate", "scale"]:
            if attr in kwargs:
                msg = f"{attr} is calculated internally, ignoring provided value"
                ytnapari_log.warning(msg)
                _ = kwargs.pop(attr)

        # set the display name
        if "name" in kwargs:
            fname = kwargs.pop("name")
        else:
            fname = f"{field[0]}_{field[1]}"

        md = _mi.create_metadata_dict(
            data, layer_domain, take_log, reference_layer=ref_layer
        )
        viewer.add_image(
            data,
            name=fname,
            translate=tr,
            scale=sc,
            metadata=md,
            colormap=colormap,
            **kwargs,
        )

        if link_to is not None:
            # link the one we just added with the provided layer
            viewer.layers.link_layers([link_to, viewer.layers[-1]])

    def add_region(
        self,
        viewer: Viewer,
        ds,
        field: Tuple[str, str],
        resolution: Optional[Tuple[int, int, int]] = None,
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        take_log: Optional[bool] = None,
        colormap: Optional[str] = None,
        link_to: Optional[Union[str, Layer]] = None,
        rescale: Optional[bool] = False,
        **kwargs,
    ):
        """
        uniformly sample a region from a yt dataset and add it to a viewer

        Parameters
        ----------
        viewer: napari.Viewer
            the active napari viewer
        ds
            the yt dataset to sample
        field: Tuple[str, str]
            the field tuple to sample  e.g., ('enzo', 'Density')
        left_edge: unyt_array
            the left edge of the bounding box
        right_edge: unyt_array
            the right edge of the bounding box
        resolution: Tuple[int, int, int]
            the sampling resolution in each dimension, e.g., (400, 400, 400)
        take_log : Optional[bool]
            if True, will take the log of the extracted data. Defaults to the
            default behavior for the field set by ds.
        colormap : Optional[str]
            the color map to use, default is "viridis"
        link_to : Optional[Union[str, Layer]]
            specify a layer to which the new layer should link
        **kwargs :
            any keyword argument accepted by Viewer.add_image()

        Examples
        --------

        >>> import napari
        >>> import yt
        >>> from yt_napari.viewer import Scene
        >>> viewer = napari.Viewer()
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> yt_scene = Scene()
        >>> yt_scene.add_region(viewer, ds, ("enzo", "Temperature"))

        """

        # set defaults
        if left_edge is None:
            left_edge = ds.domain_left_edge
        if right_edge is None:
            right_edge = ds.domain_right_edge
        if resolution is None:
            resolution = (400, 400, 400)
        if take_log is None:
            take_log = ds._get_field_info(field).take_log

        # add the bounds of this new layer
        layer_domain = _mi.LayerDomain(left_edge, right_edge, resolution)

        # create the fixed resolution buffer
        frb = ds.r[
            left_edge[0] : right_edge[0] : complex(0, resolution[0]),  # noqa: E203
            left_edge[1] : right_edge[1] : complex(0, resolution[1]),  # noqa: E203
            left_edge[2] : right_edge[2] : complex(0, resolution[2]),  # noqa: E203
        ]
        data = frb[field]
        if take_log:
            data = np.log10(data)

        self._add_to_scene(
            viewer,
            data,
            layer_domain,
            field,
            take_log,
            colormap=colormap,
            link_to=link_to,
            rescale=rescale,
            **kwargs,
        )

    def add_covering_grid(
        self,
        viewer: Viewer,
        ds,
        field: Tuple[str, str],
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        level: Optional[int] = 0,
        num_ghost_zones: Optional[int] = 0,
        take_log: Optional[bool] = None,
        colormap: Optional[str] = None,
        link_to: Optional[Union[str, Layer]] = None,
        rescale: Optional[bool] = False,
        **kwargs,
    ):
        """
        uniformly sample a region from a yt dataset using a covering grid
        and add it to a viewer

        Parameters
        ----------
        viewer: napari.Viewer
            the active napari viewer
        ds
            the yt dataset to sample
        field: Tuple[str, str]
            the field tuple to sample  e.g., ('enzo', 'Density')
        left_edge: unyt_array
            the left edge of the bounding box
        right_edge: unyt_array
            the right edge of the bounding box
        level: int
            the level to sample at (default 0)
        num_ghost_zones: int
            number of ghost zones to inclue (default 0)
        take_log : Optional[bool]
            if True, will take the log of the extracted data. Defaults to the
            default behavior for the field set by ds.
        colormap : Optional[str]
            the color map to use, default is "viridis"
        link_to : Optional[Union[str, Layer]]
            specify a layer to which the new layer should link
        **kwargs :
            any keyword argument accepted by Viewer.add_image()

        Examples
        --------

        >>> import napari
        >>> import yt
        >>> from yt_napari.viewer import Scene
        >>> viewer = napari.Viewer()
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> yt_scene = Scene()
        >>> yt_scene.add_region(viewer, ds, ("enzo", "Temperature"))

        """

        # set defaults
        if left_edge is None:
            left_edge = ds.domain_left_edge
        if right_edge is None:
            right_edge = ds.domain_right_edge

        if take_log is None:
            take_log = ds._get_field_info(field).take_log

        # create the fixed resolution buffer
        frb, dims = _mi._get_covering_grid(
            ds, left_edge, right_edge, level, num_ghost_zones
        )
        data = frb[field]
        if take_log:
            data = np.log10(data)

        # add the bounds of this new layer
        layer_domain = _mi.LayerDomain(left_edge, right_edge, dims)

        self._add_to_scene(
            viewer,
            data,
            layer_domain,
            field,
            take_log,
            colormap=colormap,
            link_to=link_to,
            rescale=rescale,
            **kwargs,
        )

    def add_to_viewer(
        self,
        viewer: Viewer,
        ds,
        field: Tuple[str, str],
        resolution: Optional[Tuple[int, int, int]] = None,
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        take_log: Optional[bool] = None,
        colormap: Optional[str] = None,
        link_to: Optional[Union[str, Layer]] = None,
        **kwargs,
    ):
        """deprecated, will be removed in v>0.1.0. use add_region"""
        msg = (
            "add_to_viewer has been deprecated, use add_region "
            "instead. add_to_viewer will be removed in v>0.1.0"
        )
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        self.add_region(
            viewer,
            ds,
            field,
            resolution=resolution,
            left_edge=left_edge,
            right_edge=right_edge,
            take_log=take_log,
            colormap=colormap,
            link_to=link_to,
            **kwargs,
        )

    def add_slice(
        self,
        viewer: Viewer,
        ds,
        normal: Union[str, int],
        field: Tuple[str, str],
        center: Optional[unyt_array] = None,
        resolution: Optional[Tuple[int, int]] = (400, 400),
        width: Optional[unyt_quantity] = None,
        height: Optional[unyt_quantity] = None,
        take_log: Optional[bool] = None,
        periodic: Optional[bool] = False,
        colormap: Optional[str] = None,
        link_to: Optional[Union[str, Layer]] = None,
        rescale: Optional[bool] = False,
        **kwargs,
    ):
        """
        sample an orthogonal slice from a yt dataset and add it to a viewer

        Parameters
        ----------
        viewer: napari.Viewer
            the active napari viewer
        ds
            the yt dataset to sample
        normal: str, int
            the normal axis of the slice, either an axis name or number
        field: Tuple[str, str]
            the field tuple to sample  e.g., ('enzo', 'Density')
        center: unyt_array
            the center of the slice (3D)
        width: unyt_quantity
            the width of the slice
        height: unyt_quantity
            the height of the slice
        resolution: Tuple[int, int]
            the sampling resolution in each dimension, e.g., (400, 400)
        take_log : Optional[bool]
            if True, will take the log of the extracted data. Defaults to the
            default behavior for the field set by ds.
        periodic: Optional[bool]
            use periodic bounds for the slice, default False
        colormap : Optional[str]
            the color map to use, default is "viridis"
        link_to : Optional[Union[str, Layer]]
            specify a layer to which the new layer should link
        **kwargs :
            any keyword argument accepted by Viewer.add_image()

        Examples
        --------

        >>> import napari
        >>> import yt
        >>> from yt_napari.viewer import Scene
        >>> viewer = napari.Viewer()
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> yt_scene = Scene()
        >>> yt_scene.add_slice(viewer, ds, "x", ("enzo", "Temperature"))

        """

        if take_log is None:
            take_log = ds._get_field_info(field).take_log

        frb, layer_domain = _mi._process_slice(
            ds,
            normal,
            center=center,
            width=width,
            height=height,
            resolution=resolution,
            periodic=periodic,
        )

        data = frb[field]
        if take_log:
            data = np.log10(data)

        self._add_to_scene(
            viewer,
            data,
            layer_domain,
            field,
            take_log,
            colormap=colormap,
            link_to=link_to,
            rescale=rescale,
            **kwargs,
        )

    def normalize_color_limits(
        self,
        layers: List[Union[str, Layer]],
        layer_list: Optional[LayerList] = None,
        check_linked: Optional[bool] = True,
    ):
        """
        normalize the color limits (the `contrast_limits`) across layers.


        Parameters
        ----------
        layers: List[Union[str, Tuple]]
            a list of the layers to normalize across
        layer_list : Optional[LayerList]
            the LayerList from an active napari Viewer. Required if you are
            providing layers by layer name only
        check_linked: Optional[bool]
            if True (default), will also check for linked layers even if they
            are not explicitly included in `layers`.

        Notes
        -----
        This method does not affect the linked state of any layers.

        Examples
        --------
        The following adds two layers and then normalizes the color scale between
        the two:

        >>> import napari
        >>> import yt
        >>> from yt_napari.viewer import Scene
        >>> viewer = napari.Viewer()
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> yt_scene = Scene()
        >>> le = ds.domain_center - ds.arr([10, 10, 10], 'kpc')
        >>> re = ds.domain_center + ds.arr([10, 10, 10], 'kpc')
        >>> yt_scene.add_region(viewer,
        >>>                        ds,
        >>>                        ("enzo", "Density"),
        >>>                        left_edge = le,
        >>>                        right_edge = re,
        >>>                        resolution=(600, 600, 600),
        >>>                        name="Density_1")
        >>> le = ds.domain_center + ds.arr([10, 10, 10], 'kpc')
        >>> re = le + ds.arr([20, 20, 20], 'kpc')
        >>> yt_scene.add_region(viewer,
        >>>                        ds,
        >>>                        ("enzo", "Density"),
        >>>                        left_edge = le,
        >>>                        right_edge = re,
        >>>                        resolution=(300, 300, 300),
        >>>                        name="Density_2")
        >>> yt_scene.normalize_color_limits(["Density_2", "Density_1"], viewer.layers)

        """

        # sanitize
        clean_layers = self._sanitize_layers(layers, layer_list, check_linked)

        # the set  of layers already includes linked layers at this point, so
        # no need to check for linked again while getting the range
        data_range = self.get_data_range(clean_layers, check_linked=False)

        # now apply those limits
        self.set_across_layers(clean_layers, "contrast_limits", data_range)

    def set_across_layers(
        self,
        layers: List[Union[str, Layer]],
        attribute: str,
        value: Any,
        layer_list: Optional[LayerList] = None,
    ):
        """
        set the value of an attribute for all the provided layers

        Parameters
        ----------
        layers
            a list of napari Layer objects or string names of layers.
        attribute
            the layer attribute to set
        value
            the value of the attribute to set
        layer_list
            the active napari LayerList. required if providing layers by name.

        Notes
        -----
        Any existing layers that are linked to the provided layers
        will also be updated.
        """

        # note that we never need to check_linked since we are setting attributes
        # in this function, so any linked layers will always be updated as well.
        clean_layers = self._sanitize_layers(layers, layer_list, check_linked=False)

        # set a single attribute across layers without regard for linked status
        for layer in clean_layers:
            setattr(layer, attribute, value)

    @staticmethod
    def _sanitize_layers(
        layers: List[Union[str, Layer]],
        layer_list: Optional[LayerList] = None,
        check_linked: Optional[bool] = True,
    ) -> Set[Layer]:
        """
        returns a set of napari Layer objects scrubbed of string names

        Parameters
        ----------
        layers
            input layers
        layer_list
            the active LayerList, only needed if there are strings in layers
        check_linked
            if True (default), will add any linked layers to the final set

        Returns
        -------
        set
            the napari Layer objects
        """
        #

        if any([isinstance(i, str) for i in layers]):
            # scrub string names from the layers
            if layer_list is None:
                raise ValueError(
                    "must provide the active LayerList if using layer names"
                )

            clean_layers = set()
            for layer in layers:
                if isinstance(layer, str):
                    clean_layers.add(layer_list[layer])
                else:
                    clean_layers.add(layer)
        else:
            # everything is already a layer, just return the set
            clean_layers = set(layers)

        if check_linked:
            # add on any layers that are linked to any of those provided
            clean_layers = clean_layers.union(get_linked_layers(*clean_layers))
        return clean_layers

    def get_data_range(
        self,
        layers: List[Union[str, Layer]],
        layer_list: Optional[LayerList] = None,
        check_linked: Optional[bool] = True,
    ) -> Tuple[float, float]:
        """
        retrieve the extrema across layers

        Parameters
        ----------
        layers: List[Union[str, Tuple]]
            a list of the layers to normalize across
        layer_list : Optional[LayerList]
            the LayerList from an active napari Viewer. Required if you are
            providing layers by layer name only
        check_linked: Optional[bool]
            if True (default), will also check for linked layers even if they
            are not explicitly included in `layers`.

        Returns
        -------
        Tuple(float, float)
            length-2 tuple with the min and max values across layers.

        Examples
        --------

        >>> import napari
        >>> import yt
        >>> from yt_napari.viewer import Scene
        >>> viewer = napari.Viewer()
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> yt_scene = Scene()
        >>> yt_scene.add_region(viewer, ds, ("enzo", "Temperature"))
        >>> yt_scene.get_data_range(viewer.layers)
        (3.2446250040130398, 5.003147905498429)

        """

        clean_layers = self._sanitize_layers(layers, layer_list, check_linked)

        min_val = np.inf
        max_val = -np.inf
        for layer in clean_layers:
            if "_yt_napari_layer" in layer.metadata:
                min_val = min([min_val, layer.metadata["_data_range"][0]])
                max_val = max([max_val, layer.metadata["_data_range"][1]])
            else:
                min_val = min([min_val, layer.data.min()])
                max_val = max([max_val, layer.data.max()])

        return (min_val, max_val)


def layers_to_yt(
    viewer: Viewer,
    layers: Optional[List[Union[str, int]]] = None,
    bbox: Optional[np.ndarray] = None,
    **kwargs,
) -> ytDataset:
    """
    Load layers from the napari viewer as a yt uniformg grid dataset.

    Parameters
    ----------
    viewer: napari.Viewer
        the active napari Viewer instance
    layers: List[str, int]
        optional list of layers to load. If not supplied, will attempt
        to use all available layers.
    bbox: np.ndarray
        optional bounding box array
    kwargs
        any additional keyword arguments are passed to yt.load_uniform_grid

    Returns
    -------
    Dataset
        a yt dataset

    Notes
    -----

    Current limitations:
    * Multi-level data is not currently supported
    * Selected layers must all have the same shape (and extent)
    * Data is copied

    """

    available_layers = viewer.layers
    available_layer_names = [layer.name for layer in available_layers]
    available_layer_ids = range(0, len(available_layers))
    if layers is None:
        # try to load them all
        layers = available_layer_names

    # some validation
    for layer in layers:
        if isinstance(layer, int) and layer not in available_layer_ids:
            msg = (
                f"Layer {layer} not found in valid range of layer ids: "
                f"{available_layer_ids}."
            )
            raise RuntimeError(msg)
        elif isinstance(layer, str) and layer not in available_layers:
            msg = (
                f"Layer {layer} not found in list of available layers: "
                f"{available_layer_names}."
            )
            raise RuntimeError(msg)

    layer_shape = available_layers[layers[0]].data.shape
    # ndim = available_layers[layers[0]].ndim  # use below...
    for layer in layers:
        active_layer = available_layers[layer]
        if layer_shape != active_layer.data.shape:
            msg = (
                "Can only export layers as a yt dataset if they have "
                f"the same dimensions. {layers[0]} has shape of {layer_shape},"
                f" while {layer} has shape {active_layer.data.shape}"
            )
            raise RuntimeError(msg)

    # first go: just copy the data.
    # note: not using layer for name directly, because it could be an integer
    # index or
    data = {
        available_layers[layer].name: available_layers[layer].data for layer in layers
    }

    # TODO: check dimensionality (2D layers)

    # TODO: check for multi-level and just load the finest level?
    # layer.level_shapes is a list of shapes for each level

    # TODO: axis order? common for bio images to be ordered z, y, x...
    #       is there metadata for that?

    if bbox is None:
        bbox = np.array([[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]])
        # TODO: layers have an extent attribute, looks like, e.g.,:
        # Extent(data=array([[  0.,   0.,   0.],
        # [ 16., 512., 512.]]), world=array([[-5.000e-01, -5.000e-01, -5.000e-01],
        # [ 1.550e+01,  5.115e+02,  5.115e+02]]), step=array([1., 1., 1.]))
        # that world array could be used as a bounding box.

    if "length_unit" in kwargs:
        lu = kwargs.pop("length_unit")
    else:
        lu = 1.0

    ds = yt.load_uniform_grid(data, layer_shape, bbox=bbox, length_unit=lu, **kwargs)

    return ds
