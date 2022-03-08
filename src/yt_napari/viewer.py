from typing import List, Optional, Tuple

import numpy as np
from napari import Viewer
from unyt import unyt_array

from yt_napari._model_ingestor import LayerDomain, PhysicalDomainTracker


class Scene:
    def __init__(self):
        self._domain: PhysicalDomainTracker = None

    def _setup_domain_from_layers(self, layers: list):
        # note: this may be problematic... if there exists more than one
        # layer initially, which is the "reference". Or if layers get deleted
        layer_domains = []
        for layer in layers:
            if "_layer_domain" in layer.metadata:
                layer_domains.append(layer.metadata["_layer_domain"])

        if layer_domains:
            # there is at least one existing layer to set up from
            pdt = PhysicalDomainTracker()
            for l_dom in layer_domains:
                pdt.update_from_layer(l_dom, update_c_w=False)
            pdt.update_width_and_center()
            self._domain = pdt

    def add_to_viewer(
        self,
        viewer: Viewer,
        ds,
        fields: List[Tuple[str, str]],
        resolution: Optional[Tuple[int, int, int]] = None,
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        log_fields: Optional[List[Tuple[str, str]]] = None,
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
        fields: List[Tuple[str, str]]
            a list of field to add in yt field tuples, e.g.:
                [('enzo', 'Density'), ('enzo', 'Temperature')]
        left_edge: unyt_array
            the left edge of the bounding box
        right_edge: unyt_array
            the right edge of the bounding box
        resolution: Tuple[int, int, int]
            the sampling resolution in each dimension, e.g., (400, 400, 400)
        log_fields : Optional[List[Tuple[str, str]]
            np.log10 will be applied to of the any fields in this list
        **kwargs :
            any keyword argument accepted by Viewer.add_image()
        """

        # check defaults
        if left_edge is None:
            left_edge = ds.domain_left_edge
        if right_edge is None:
            right_edge = ds.domain_right_edge
        if resolution is None:
            resolution = (400, 400, 400)

        # setup the domain tracker
        if self._domain is None:
            if len(viewer.layers):
                self._setup_domain_from_layers(viewer.layers)

        # add the bounds of this new layer
        layer_domain = LayerDomain(left_edge, right_edge, resolution)
        if self._domain is None:
            # there were no prior layers, create the tracker. All
            # subsequent layers that we add will be relative to this one.
            self._domain = PhysicalDomainTracker()
            self._domain.update_from_layer(layer_domain, update_c_w=True)

        # create the fixed resolution buffer
        frb = ds.r[
            left_edge[0] : right_edge[0] : complex(0, resolution[0]),  # noqa: E203
            left_edge[1] : right_edge[1] : complex(0, resolution[1]),  # noqa: E203
            left_edge[2] : right_edge[2] : complex(0, resolution[2]),  # noqa: E203
        ]

        if log_fields is None:
            # default is to log everything
            log_fields = fields

        for field in fields:
            data = frb[field]  # extract the field (the slow part)
            if field in log_fields:
                # NOTE: also check the ds default for the field??
                data = np.log10(data)

            splayer = (np.empty(0), {}, "image", layer_domain)
            _, im_kwargs, _ = self._domain.align_sanitize_layer(splayer)

            tr = im_kwargs.get("translate", None)
            sc = im_kwargs.get("scale", None)
            md = {"_layer_domain": layer_domain}
            fname = f"{field[0]}_{field[1]}"

            if "translate" in kwargs:
                raise RuntimeWarning(
                    "translate is calculated internally, ignoring provided value"
                )
                _ = kwargs.pop("translate")

            if "scale" in kwargs:
                raise RuntimeWarning(
                    "scale is calculated internally, ignoring provided value"
                )
                _ = kwargs.pop("scale")

            viewer.add_image(
                data, name=fname, translate=tr, scale=sc, metadata=md, **kwargs
            )
