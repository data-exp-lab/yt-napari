import warnings
from typing import Any, List, Optional, Set, Tuple, Union

import numpy as np
from napari import Viewer
from napari.components.layerlist import LayerList
from napari.layers import Layer
from napari.layers.utils._link_layers import get_linked_layers
from unyt import unyt_array

import yt_napari._model_ingestor as _mi


class Scene:
    def __init__(self):
        self._domain: _mi.PhysicalDomainTracker = None

    def _setup_domain_from_layers(self, layers: list):
        # note: this may be problematic... if there exists more than one
        # layer initially, which is the "reference". Or if layers get deleted
        layer_domains = []
        for layer in layers:
            if "_layer_domain" in layer.metadata:
                layer_domains.append(layer.metadata["_layer_domain"])

        if layer_domains:
            # there is at least one existing layer to set up from
            pdt = _mi.PhysicalDomainTracker()
            for l_dom in layer_domains:
                pdt.update_from_layer(l_dom, update_c_w=False)
            pdt.update_width_and_center()
            self._domain = pdt

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
        """
        create a uniform sampling of ds and add it to the napari viewer

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
        >>> yt_scene.add_to_viewer(viewer, ds, ("enzo", "Temperature"))

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
        if colormap is None:
            # TO DO: make this a per-field default based on yt info?
            # or use ytcfg.get("yt", "default_colormap") ?
            # would need to check against available cmaps in napari
            colormap = "viridis"

        # setup the domain tracker
        if self._domain is None:
            if len(viewer.layers):
                self._setup_domain_from_layers(viewer.layers)

        # add the bounds of this new layer
        layer_domain = _mi.LayerDomain(left_edge, right_edge, resolution)
        if self._domain is None:
            # there were no prior layers, create the tracker. All
            # subsequent layers that we add will be relative to this one.
            self._domain = _mi.PhysicalDomainTracker()
            self._domain.update_from_layer(layer_domain, update_c_w=True)

        # create the fixed resolution buffer
        frb = ds.r[
            left_edge[0] : right_edge[0] : complex(0, resolution[0]),  # noqa: E203
            left_edge[1] : right_edge[1] : complex(0, resolution[1]),  # noqa: E203
            left_edge[2] : right_edge[2] : complex(0, resolution[2]),  # noqa: E203
        ]
        data = frb[field]
        if take_log:
            data = np.log10(data)

        # initialize the spatial layer then sanitize it
        splayer = (data, {}, "image", layer_domain)
        _, im_kwargs, _ = self._domain.align_sanitize_layer(splayer)

        # extract the translate and scale values
        tr = im_kwargs.get("translate", None)
        sc = im_kwargs.get("scale", None)
        # check that the user has not supplied translate or scale separately
        for attr in ["translate", "scale"]:
            if attr in kwargs:
                msg = f"{attr} is calculated internally, ignoring provided value"
                warnings.warn(msg, RuntimeWarning)
                _ = kwargs.pop(attr)

        # set the display name
        if "name" in kwargs:
            fname = kwargs.pop("name")
        else:
            fname = f"{field[0]}_{field[1]}"

        md = _mi.create_metadata_dict(data, layer_domain, take_log)

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
        >>> yt_scene.add_to_viewer(viewer,
        >>>                        ds,
        >>>                        ("enzo", "Density"),
        >>>                        left_edge = le,
        >>>                        right_edge = re,
        >>>                        resolution=(600, 600, 600),
        >>>                        name="Density_1")
        >>> le = ds.domain_center + ds.arr([10, 10, 10], 'kpc')
        >>> re = le + ds.arr([20, 20, 20], 'kpc')
        >>> yt_scene.add_to_viewer(viewer,
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

        Note that any existing layers that are linked to the provided layers
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
        >>> yt_scene.add_to_viewer(viewer, ds, ("enzo", "Temperature"))
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
