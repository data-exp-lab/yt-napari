import abc
import os.path
from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from napari import Viewer
from unyt import unyt_array, unyt_quantity

from yt_napari import _data_model as _dm, _model_ingestor as _mi


class _Selection(abc.ABC):
    nd: int = None

    def __init__(self, field: Tuple[str, str], take_log: Optional[bool] = None):
        self.field = field
        self._take_log = take_log
        self._aspect_ratio = None

    @abc.abstractmethod
    def sample_ds(self, ds):
        """sample a yt dataset with the selection object"""

    @property
    def _requires_scale(self):
        return any(self._aspect_ratio != 1.0)

    @property
    def _scale(self):
        return 1.0 / self._aspect_ratio

    def take_log(self, ds):
        if self._take_log is None:
            self._take_log = ds._get_field_info(self.field).take_log
        return self._take_log

    def _finalize_array(self, ds, sample):
        if self.take_log(ds) is True:
            return np.log10(sample)
        return sample

    @staticmethod
    def _validate_unit_tuple(val):
        if isinstance(val, tuple):
            return val[0], val[1]
        return None, None


class Region(_Selection):
    """
    A 3D rectangular selection through a domain.

    Parameters
    ----------
    field: (str, str)
        a yt field present in all timeseries to load.
    left_edge: unyt_array or (ndarray, str)
        (optional) a 3-element unyt_array defining the left edge of the region,
        defaults to the domain left_edge of each active timestep.
    right_edge: unyt_array or (ndarray, str)
        (optional) a 3-element unyt_array defining the right edge of the region,
        defaults to the domain right_edge of each active timestep.
    resolution: (int, int, int)
        (optional) 3-element tuple defining the resolution to sample at. Default
        is (400, 400, 400).
    take_log: bool
        (optional) If True, take the log10 of the sampled field. Defaults to the
        default behavior for the field in the dataset.
    """

    nd = 3

    def __init__(
        self,
        field: Tuple[str, str],
        left_edge: Optional[Union[unyt_array, Tuple[np.ndarray, str]]] = None,
        right_edge: Optional[Union[unyt_array, Tuple[np.ndarray, str]]] = None,
        resolution: Optional[Tuple[int, int, int]] = (400, 400, 400),
        take_log: Optional[bool] = None,
    ):

        super().__init__(field, take_log=take_log)
        self.left_edge = left_edge
        self.right_edge = right_edge
        self.resolution = resolution
        self._le, self._le_units = self._validate_unit_tuple(left_edge)
        self._re, self._re_units = self._validate_unit_tuple(right_edge)

        if self.left_edge is not None and self.right_edge is not None:
            if self._le is not None:
                LE = self._le
            else:
                LE = self.left_edge

            if self._re is not None:
                RE = self._re
            else:
                RE = self.right_edge
            self._calc_aspect_ratio(LE, RE)

    def _calc_aspect_ratio(self, LE, RE):
        wid = RE - LE
        self._aspect_ratio = wid / wid[0]

    def sample_ds(self, ds):
        """
        return a fixed resolution sample of a field in a yt dataset.

        Parameters
        ----------
        ds : yt dataset
            the yt dataset to sample

        Examples
        --------

        >>> import yt
        >>> import numpy as np
        >>> from yt_napari.timeseries import Region
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> le = np.array([0.4, 0.4, 0.4], 'Mpc')
        >>> re = np.array([0.6, 0.6, 0.6], 'Mpc')
        >>> reg = Region(("enzo", "Density"), left_edge=le, right_edge=re)
        >>> reg_data = reg.sample_ds(ds)

        Notes
        -----
        This is equivalent to `ds.r[...,...,..][field]`, but is a useful
        abstraction for applying the same selection to a series of datasets.
        """
        if self.left_edge is None:
            LE = ds.domain_left_edge
        elif self._le is not None:
            LE = ds.arr(self._le, self._le_units)
        else:
            LE = self.left_edge

        if self.right_edge is None:
            RE = ds.domain_right_edge
        elif self._re is not None:
            RE = ds.arr(self._re, self._re_units)
        else:
            RE = self.right_edge

        res = self.resolution
        if self._aspect_ratio is None:
            self._calc_aspect_ratio(LE, RE)

        # create the fixed resolution buffer
        frb = ds.r[
            LE[0] : RE[0] : complex(0, res[0]),  # noqa: E203
            LE[1] : RE[1] : complex(0, res[1]),  # noqa: E203
            LE[2] : RE[2] : complex(0, res[2]),  # noqa: E203
        ]

        data = frb[self.field]
        return self._finalize_array(ds, data)


class Slice(_Selection):
    """
    A 2D axis-normal slice through a domain.

    Parameters
    ----------
    field: (str, str)
        a yt field present in all timeseries to load.
    normal: int or str
        the normal axis for slicing
    center: unyt_array
        (optional) a 3-element unyt_array defining the slice center, defaults
        to the domain center of each active timestep.
    width: unyt_quantity or (value, unit)
        (optional) the slice width, defaults to the domain width  of each active
        timestep.
    height: unyt_quantity or (value, unit)
        (optional) the slice height, defaults to the domain height of each
        active timestep.
    resolution: (int, int)
        (optional) 2-element tuple defining the resolution to sample at. Default
        is (400, 400).
    periodic: bool
        (optional, default is False) If True, treat domain as periodic
    take_log: bool
        (optional) If True, take the log10 of the sampled field. Defaults to the
        default behavior for the field in the dataset.
    """

    nd = 2

    def __init__(
        self,
        field: Tuple[str, str],
        normal: Union[str, int],
        center: Optional[Union[unyt_array, Tuple[np.ndarray, str]]] = None,
        width: Optional[Union[unyt_quantity, Tuple[float, str]]] = None,
        height: Optional[Union[unyt_quantity, Tuple[float, str]]] = None,
        resolution: Optional[Tuple[int, int]] = (400, 400),
        periodic: Optional[bool] = False,
        take_log: Optional[bool] = None,
    ):
        super().__init__(field, take_log=take_log)

        self.normal = normal
        self.center = center
        self.height = height
        self.width = width
        self.resolution = resolution
        self.periodic = periodic

        # handle the case where the length arrays are value-unit tuples
        self._center_ndarray, self._center_units = self._validate_unit_tuple(center)
        self._width_val, self._width_units = self._validate_unit_tuple(width)
        self._height_val, self._height_units = self._validate_unit_tuple(height)

        if self.width is not None and self.height is not None:
            if self._width_val is not None:
                width = self._width_val
            else:
                width = self.width
            if self._height_val is not None:
                height = self._height_val
            else:
                height = self.height
            self._calc_aspect_ratio(width, height)

    def _calc_aspect_ratio(self, width, height):
        self._aspect_ratio = np.array([1.0, height / width])

    def sample_ds(self, ds):
        """
        return a fixed resolution slice of a field in a yt dataset.

        Parameters
        ----------
        ds : yt dataset
            the yt dataset to sample

        Examples
        --------

        >>> import yt
        >>> from unyt import unyt_quantity
        >>> from yt_napari.timeseries import Slice
        >>> ds = yt.load_sample("IsolatedGalaxy")
        >>> w = unyt_quantity(0.2, 'Mpc')
        >>> slc = Slice(("enzo", "Density"), "x", width=w, height=w)
        >>> slc_data = slc.sample_ds(ds)

        Notes
        -----
        This is equivalent to `ds.slice(...).to_frb()[field]`, but is a useful
        abstraction for applying the same selection to a series of datasets.
        """
        if self.center is None:
            center = ds.domain_center
        elif self._center_ndarray is not None:
            center = ds.arr(self._center_ndarray, self._center_units)
        else:
            center = self.center

        axid = ds.coordinates.axis_id
        if self.width is None:
            x_ax = axid[ds.coordinates.image_axis_name[self.normal][0]]
            width = ds.domain_width[x_ax]
        elif self._width_val is not None:
            width = ds.arr(self._width_val, self._width_units)
        else:
            width = self.width

        if self.height is None:
            y_ax = axid[ds.coordinates.image_axis_name[self.normal][1]]
            height = ds.domain_width[y_ax]
        elif self._height_val is not None:
            height = ds.arr(self._height_val, self._height_units)
        else:
            height = self.height

        if self._aspect_ratio is None:
            self._calc_aspect_ratio(width, height)

        frb, _ = _mi._process_slice(
            ds,
            self.normal,
            center=center,
            width=width,
            height=height,
            resolution=self.resolution,
            periodic=self.periodic,
        )

        data = frb[self.field]  # extract the field (the slow part)
        return self._finalize_array(ds, data)


def _load_and_sample(file, selection: Union[Slice, Region], is_dask):
    if is_dask:
        yt.set_log_level(40)  # errors and critical only
    ds = _mi._load_with_timeseries_specials_check(file)
    return selection.sample_ds(ds)


def _get_im_data(
    selection: Union[Slice, Region],
    file_dir: Optional[str] = None,
    file_pattern: Optional[str] = None,
    file_list: Optional[List[str]] = None,
    file_range: Optional[Tuple[int, int, int]] = None,
    load_as_stack: Optional[bool] = False,
    use_dask: Optional[bool] = False,
    return_delayed: Optional[bool] = True,
    stack_scaling: Optional[float] = 1.0,
    **kwargs,
):

    tfs = _dm.TimeSeriesFileSelection(
        file_pattern=file_pattern,
        directory=file_dir,
        file_list=file_list,
        file_range=file_range,
    )
    files = _mi._find_timeseries_files(tfs)

    im_data = []
    if use_dask is False:
        for file in files:
            im_data.append(_load_and_sample(file, selection, use_dask))
    else:
        try:
            from dask import array as da, delayed
        except ImportError:
            msg = (
                "This functionality requires dask: "
                'pip install "dask[distributed, array]"'
            )
            raise ImportError(msg)
        for file in files:
            data = delayed(_load_and_sample)(file, selection, use_dask)
            im_data.append(da.from_delayed(data, selection.resolution, dtype=float))

    # note: scale validation modifies kwargs in place
    _validate_scale(selection, kwargs, load_as_stack, stack_scaling)

    if load_as_stack:
        im_data = np.stack(im_data)

    if use_dask and return_delayed is False:
        im_data = im_data.compute()

    return im_data, kwargs, files


def _validate_scale(
    selection: Union[Slice, Region],
    kwargdict: dict,
    load_as_stack: bool,
    stack_scaling: float,
):

    if "scale" in kwargdict:
        # always use provided
        sc = np.asarray(kwargdict.pop("scale"))
    elif selection._aspect_ratio is not None:
        # with dask, might not know the aspect ratio until after computation
        sc = selection._scale
    else:
        sc = np.ones((selection.nd,))

    if len(sc) == selection.nd and load_as_stack:
        sc = np.concatenate(
            [
                [
                    stack_scaling,
                ],
                sc,
            ]
        )

    kwargdict["scale"] = sc


def add_to_viewer(
    viewer: Viewer,
    selection: Union[Slice, Region],
    file_dir: Optional[str] = None,
    file_pattern: Optional[str] = None,
    file_list: Optional[List[str]] = None,
    file_range: Optional[Tuple[int, int, int]] = None,
    load_as_stack: Optional[bool] = False,
    use_dask: Optional[bool] = False,
    return_delayed: Optional[bool] = True,
    stack_scaling: Optional[float] = 1.0,
    **kwargs,
):
    """
    Sample a timeseries and add to a napari viewer

    Parameters
    ----------
    viewer: napari.Viewer
        a napari Viewer instance
    selection: Slice or Region
        the selection to apply to each matched dataset
    file_dir: str
        (optional) a file directory to prepend to either the file_pattern or
        file_list argument.
    file_pattern: str
        (optional) a file pattern to match, not used if file_list is set. One of
        file_pattern or file_list must be set.
    file_list: str
        (optional) a list of files to use. One of file_list or file_pattern must
        be set.
    file_range: (int, int, int)
        (optional) A range to limit matched files in the form (start, stop, step).
    load_as_stack: bool
        (optional, default False) If True, the timeseries will be stacked to a
        single image array
    use_dask: bool
        (optional, default False) If True, use dask to assemble the image array
    return_delayed: bool
        (optional, default True) If True and if use_dask=True, then the image
        array will be a delayed array, resulting in lazy loading in napari. If
        False and if use_dask=True, then dask will distribute sampling tasks
        and assemble a final in-memory array.
    stack_scaling: float
        (optional, default 1.0) Applies a scaling to the effective image array
        in the stacked (time) dimension if load_as_stack is True. If scale is
        provided as a separate parameter, then stack_scaling is only used if
        the len(scale) matches the dimensionality of the spatial selection.
    **kwargs
        any additional keyword arguments are passed to napari.Viewer().add_image()

    Examples
    --------

    >>> import napari
    >>> from yt_napari.timeseries import Slice, add_to_viewer
    >>> viewer = napari.Viewer()
    >>> slc = Slice(("enzo", "Density"), "x")
    >>> enzo_files = "enzo_tiny_cosmology/DD????/DD????"
    >>> add_to_viewer(viewer, slc, file_pattern=enzo_files, file_range=(0,47, 5),
    >>>                load_as_stack=True)
    """

    im_data, im_kwargs, files = _get_im_data(
        selection,
        file_dir=file_dir,
        file_pattern=file_pattern,
        file_list=file_list,
        file_range=file_range,
        load_as_stack=load_as_stack,
        use_dask=use_dask,
        return_delayed=return_delayed,
        stack_scaling=stack_scaling,
        **kwargs,
    )
    if load_as_stack:
        viewer.add_image(im_data, **im_kwargs)
    else:
        basename = None
        if "name" in im_kwargs:
            basename = im_kwargs.pop("name")

        for im_id, im in enumerate(im_data):
            if basename is not None:
                name = f"{basename}_{im_id}"
            else:
                name = os.path.basename(files[im_id])
                name = f"{name}_{selection.field}"
            viewer.add_image(im, name=name, **im_kwargs)
