import abc
import os.path
from typing import List, Optional, Tuple, Union

import numpy as np
import yt
from napari import Viewer
from unyt import unyt_array, unyt_quantity

from yt_napari import _data_model as _dm
from yt_napari._model_ingestor import _find_timeseries_files, _process_slice


class _Selection(abc.ABC):
    def __init__(self, field: Tuple[str, str], take_log: Optional[bool] = None):
        self.field = field
        self._take_log = take_log

    @abc.abstractmethod
    def sample_ds(self, ds):
        pass

    @abc.abstractmethod
    def _aspect_ratio(self):
        pass

    @property
    def _requires_scale(self):
        return any(self._aspect_ratio() != 1.0)

    @property
    def _scale(self):
        return 1.0 / self._aspect_ratio()

    def take_log(self, ds):
        if self._take_log is None:
            self._take_log = ds._get_field_info(self.field).take_log
        return self._take_log

    def _finalize_array(self, ds, sample):
        if self.take_log(ds) is True:
            return np.log10(sample)
        return sample


class Region(_Selection):
    """
    A 3D rectangular selection through a domain.

    Parameters
    ----------
    field: (str, str)
        a yt field present in all timeseries to load.
    left_edge: unyt_array
        (optional) a 3-element unyt_array defining the left edge of the region,
        defaults to the domain left_edge of the first loaded timestep.
    right_edge: unyt_array
        (optional) a 3-element unyt_array defining the right edge of the region,
        defaults to the domain right_edge of the first loaded timestep.
    resolution: (int, int, int)
        (optional) 3-element tuple defining the resolution to sample at. Default
        is (400, 400, 400).
    take_log: bool
        (optional) If True, take the log10 of the sampled field. Defaults to the
        default behavior for the field in the dataset.
    """

    def __init__(
        self,
        field: Tuple[str, str],
        left_edge: Optional[unyt_array] = None,
        right_edge: Optional[unyt_array] = None,
        resolution: Optional[Tuple[int, int, int]] = (400, 400, 400),
        take_log: Optional[bool] = None,
    ):

        super().__init__(field, take_log=take_log)
        self.left_edge = left_edge
        self.right_edge = right_edge
        self.resolution = resolution

    def sample_ds(self, ds):
        if self.left_edge is None:
            self.left_edge = ds.domain_left_edge

        if self.right_edge is None:
            self.right_edge = ds.domain_right_edge

        res = self.resolution
        RE = self.right_edge
        LE = self.left_edge

        # create the fixed resolution buffer
        frb = ds.r[
            LE[0] : RE[0] : complex(0, res[0]),  # noqa: E203
            LE[1] : RE[1] : complex(0, res[1]),  # noqa: E203
            LE[2] : RE[2] : complex(0, res[2]),  # noqa: E203
        ]

        data = frb[self.field]
        return self._finalize_array(ds, data)

    @property
    def _aspect_ratio(self):
        wid = self.right_edge - self.left_edge
        return wid / wid[0]


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
        to the domain center of the first loaded timestep.
    width: unyt_quantity
        (optional) a unyt_quantity defining the slice width, defaults to the
        domain width of the first loaded timestep
    height: unyt_quantity
        (optional) a unyt_quantity defining the slice height, defaults to the
        domain width of the first loaded timestep
    resolution: (int, int)
        (optional) 2-element tuple defining the resolution to sample at. Default
        is (400, 400).
    periodic: bool
        (optional, default is False) If True, treat domain as periodic
    take_log: bool
        (optional) If True, take the log10 of the sampled field. Defaults to the
        default behavior for the field in the dataset.
    """

    def __init__(
        self,
        field: Tuple[str, str],
        normal: Union[str, int],
        center: Optional[unyt_array] = None,
        width: Optional[unyt_quantity] = None,
        height: Optional[unyt_quantity] = None,
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

    def sample_ds(self, ds):
        if self.center is None:
            self.center = ds.domain_center

        axid = ds.coordinates.axis_id
        if self.width is None:
            x_ax = axid[ds.coordinates.image_axis_name[self.normal][0]]
            self.width = ds.domain_width[x_ax]

        if self.height is None:
            y_ax = axid[ds.coordinates.image_axis_name[self.normal][1]]
            self.height = ds.domain_width[y_ax]

        frb, _ = _process_slice(
            ds,
            self.normal,
            center=self.center,
            width=self.width,
            height=self.height,
            resolution=self.resolution,
            periodic=self.periodic,
        )

        if self.take_log is None:
            self.take_log = ds._get_field_info(self.field).take_log

        data = frb[self.field]  # extract the field (the slow part)
        return self._finalize_array(ds, data)

    @property
    def _aspect_ratio(self):
        return np.array([1.0, self.height / self.width])


def _load_and_sample(file, selection: Union[Slice, Region], is_dask):
    if is_dask:
        yt.set_log_level(40)  # errors and critical only
    ds = yt.load(file)
    return selection.sample_ds(ds)


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
    tfs = _dm.TimeSeriesFileSelection(
        file_pattern=file_pattern,
        directory=file_dir,
        file_list=file_list,
        file_range=file_range,
    )
    files = _find_timeseries_files(tfs)

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

    if selection._requires_scale:
        scale = selection._scale
        if "scale" in kwargs:
            _ = kwargs.pop("scale")
        kwargs["scale"] = scale

    if load_as_stack:
        im_data = np.stack(im_data)

    if use_dask and return_delayed is False:
        im_data = im_data.compute()

    if load_as_stack:
        viewer.add_image(im_data, **kwargs)
    else:
        basename = None
        if "name" in kwargs:
            basename = kwargs.pop("name")

        for im_id, im in enumerate(im_data):
            if basename is not None:
                name = f"{basename}_{im_id}"
            else:
                name = os.path.basename(files[im_id])
                name = f"{name}_{selection.field}"
            viewer.add_image(im, name=name, **kwargs)
