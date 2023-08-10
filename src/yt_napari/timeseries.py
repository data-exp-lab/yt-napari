import abc
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

    def take_log(self, ds):
        if self._take_log is None:
            self._take_log = ds._get_field_info(self.field).take_log
        return self._take_log

    def _finalize_array(self, ds, sample):
        if self.take_log(ds) is True:
            return np.log10(sample)
        return sample


class Region(_Selection):
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


class Slice(_Selection):
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

    if load_as_stack:
        im_data = np.stack(im_data)

    if use_dask and return_delayed is False:
        im_data = im_data.compute()

    viewer.add_image(im_data, **kwargs)
