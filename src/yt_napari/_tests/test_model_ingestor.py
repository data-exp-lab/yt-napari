from typing import Optional, Tuple

import numpy as np
import pytest
import unyt
from yt.config import ytcfg

from yt_napari import _data_model as _dm, _model_ingestor as _mi

# indirect testing happens via test_reader, so the tests here focus on explicit
# testing of the domain tracking and alignment


class DomainExpectation:
    def __init__(
        self,
        left_edge: unyt.unyt_array,
        right_edge: unyt.unyt_array,
        center: unyt.unyt_array,
        width: unyt.unyt_array,
        res: Tuple[int, int, int],
        finest_grid: Optional[bool] = False,
    ):
        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center = center
        self.width = width
        self.resolution = res
        self.finest_grid = finest_grid


class Expectations:
    def __init__(self):
        # build a list of domain boundaries that will be combined, flagging
        # the one that should enclose all the others
        self.domain_sets = []
        # sets of left_edge, right_edge, center, width, res
        d = DomainExpectation(
            unyt.unyt_array([1, 1, 1], "km"),
            unyt.unyt_array([2000.0, 2000.0, 2000.0], "m"),
            unyt.unyt_array([1.5, 1.5, 1.5], "km"),
            unyt.unyt_array([1, 1, 1], "km"),
            (10, 20, 15),
        )
        self.domain_sets.append(d)

        d = DomainExpectation(
            unyt.unyt_array([0, 0, 0], "m"),
            unyt.unyt_array([10.0, 10.0, 10.0], "km"),
            unyt.unyt_array([5.0, 5.0, 5.0], "km"),
            unyt.unyt_array([10.0, 10.0, 10.0], "km"),
            (8, 15, 17),
        )
        self.domain_sets.append(d)
        self.enclosing_id = 1  # this one encloses others!

        d = DomainExpectation(
            unyt.unyt_array([5, 2, 3], "km"),
            unyt.unyt_array([10.0, 4.0, 6.0], "km"),
            unyt.unyt_array([7.5, 3.0, 4.5], "km"),
            unyt.unyt_array([5.0, 2.0, 3.0], "km"),
            (110, 111, 125),
            finest_grid=True,
        )
        self.domain_sets.append(d)


@pytest.fixture
def domains_to_test() -> Expectations:
    return Expectations()


def test_center_width_from_le_re(domains_to_test):
    for d in domains_to_test.domain_sets:
        cen, wid = _mi._le_re_to_cen_wid(d.left_edge, d.right_edge)
        assert np.all(cen == d.center)
        assert np.all(wid == d.width)


def test_layer_domain(domains_to_test):
    for d in domains_to_test.domain_sets:
        layer_domain = _mi.LayerDomain(d.left_edge, d.right_edge, d.resolution)
        assert np.all(layer_domain.center == d.center)
        assert np.all(layer_domain.width == d.width)

    # check some instantiation things
    with pytest.raises(ValueError, match="length of edge arrays must match"):
        _ = _mi.LayerDomain(d.left_edge, unyt.unyt_array([1, 2], "m"), d.resolution)

    with pytest.raises(ValueError, match="length of resolution does not"):
        _ = _mi.LayerDomain(d.left_edge, d.right_edge, (10, 12))

    ld = _mi.LayerDomain(d.left_edge, d.right_edge, (10,))
    assert len(ld.resolution) == 3


def test_layer_domain_dimensionality():
    # note: the code being tested here could be used to help orient the slices
    # in 3D but is not currently used.
    # sets of left_edge, right_edge, center, width, res
    le = unyt.unyt_array([1.0, 1.0], "km")
    re = unyt.unyt_array([2000.0, 2000.0], "m")
    res = (10, 20)
    ld = _mi.LayerDomain(le, re, res, n_d=2)
    assert ld.n_d == 2

    ld.upgrade_to_3D()
    assert ld.n_d == 3
    assert len(ld.left_edge) == 3
    assert ld.left_edge[-1] == 0.0
    ld.upgrade_to_3D()  # nothing should happen

    ld = _mi.LayerDomain(le, re, res, n_d=2, new_dim_value=0.5)
    ld.upgrade_to_3D()
    assert ld.left_edge[2] == unyt.unyt_quantity(0.5, le.units)

    new_val = unyt.unyt_quantity(0.5, "km")
    ld = _mi.LayerDomain(le, re, res, n_d=2, new_dim_value=new_val)
    ld.upgrade_to_3D()
    assert ld.left_edge[2].to("km") == new_val

    ld = _mi.LayerDomain(le, re, res, n_d=2, new_dim_value=new_val, new_dim_axis=0)
    ld.upgrade_to_3D()
    assert ld.left_edge[0].to("km") == new_val


_test_cases_insert = [
    (
        unyt.unyt_array([1.0, 1.0], "km"),
        unyt.unyt_array(
            [
                1000.0,
            ],
            "m",
        ),
        unyt.unyt_array([1.0, 1.0, 1.0], "km"),
    ),
    (
        unyt.unyt_array([1.0, 1.0], "km"),
        unyt.unyt_quantity(1000.0, "m"),
        unyt.unyt_array([1.0, 1.0, 1.0], "km"),
    ),
    (unyt.unyt_array([1.0, 1.0], "km"), 0.5, unyt.unyt_array([1.0, 1.0, 0.5], "km")),
]


@pytest.mark.parametrize("x,x2,expected", _test_cases_insert)
def test_insert_to_unyt_array(x, x2, expected):
    result = _mi._insert_to_unyt_array(x, x2, 2)
    assert np.all(result == expected)


def test_domain_tracking(domains_to_test):

    full_domain = _mi.PhysicalDomainTracker()
    full_domain.update_unit_info(unit="m")

    full_domain.update_from_layer(domains_to_test.domain_sets[0])
    for d in domains_to_test.domain_sets[1:]:
        full_domain.update_edges(d.left_edge, d.right_edge, update_c_w=True)

    # the full domain extent should now match the enclosing domain
    enclosing_domain = domains_to_test.domain_sets[domains_to_test.enclosing_id]
    for attr in ["left_edge", "right_edge", "center", "width"]:
        expected = getattr(enclosing_domain, attr)
        actual = getattr(full_domain, attr)
        assert np.all(expected == actual)

    # test again with different combination of edge args
    full_domain = _mi.PhysicalDomainTracker()
    full_domain.update_unit_info(unit="m")

    for d in domains_to_test.domain_sets:
        full_domain.update_edges(left_edge=d.left_edge, update_c_w=False)
        full_domain.update_edges(right_edge=d.right_edge, update_c_w=False)

    # center, width should not be set yet: check and then update
    assert full_domain.center is None
    assert full_domain.width is None
    full_domain.update_width_and_center()

    # now it should match the enclosing domain
    for attr in ["left_edge", "right_edge", "center", "width"]:
        expected = getattr(enclosing_domain, attr)
        actual = getattr(full_domain, attr)
        assert np.all(expected == actual)

    # do some code length tests
    with pytest.raises(ValueError):
        # code length requires a registry!
        full_domain.update_unit_info(unit="code_length")

    # add a unit registry and switch to using code_length
    registry = unyt.unit_registry.UnitRegistry()
    registry.add("code_length", 1.0, unyt.dimensions.length)
    full_domain.update_unit_info(unit="code_length", registry=registry)
    assert str(full_domain.left_edge.units) == "code_length"

    # new arrays should have code_length_available
    arr = full_domain._arr(np.array([1.0, 2.0, 3.0, 4.0]), "m")  # attaches reg
    assert isinstance(arr, unyt.unyt_array)
    assert str(arr.units) == "m"
    arr = full_domain._sanitize_length(arr)  # will change units
    assert str(arr.units) == "code_length"
    # will attach registry and change units:
    arr = full_domain._register_array(unyt.unyt_array([1.0, 2.0], "m"))
    assert str(arr.units) == "code_length"


def test_reference_layer(domains_to_test):

    # assemble some fake layer tuples
    im_type = "image"

    spatial_layer_list = []
    for d in domains_to_test.domain_sets:
        layer_domain = _mi.LayerDomain(d.left_edge, d.right_edge, d.resolution)
        im = np.random.random(d.resolution)
        spatial_layer_list.append((im, {}, im_type, layer_domain))

    layer_for_ref = spatial_layer_list[0][3]
    ref_layer = _mi.ReferenceLayer(layer_for_ref)

    # check that transformations relative to the same layer are null
    scale = ref_layer.calculate_scale(layer_for_ref)
    assert np.all(scale == 1)
    assert isinstance(scale, unyt.unyt_array)
    translate = ref_layer.calculate_translation(layer_for_ref)
    assert isinstance(translate, unyt.unyt_array)
    assert np.all(translate == 0)

    # check alignment and sanitation of a single layer
    layer = ref_layer.align_sanitize_layer(spatial_layer_list[1])
    assert len(layer) == 3
    _, imkwargs, _ = layer
    scale = imkwargs["scale"]
    translate = imkwargs["translate"]
    assert np.all(scale != 1)
    assert np.all(translate != 0)

    # check alignment of multiple layers
    layer_list = ref_layer.align_sanitize_layers(spatial_layer_list)

    def check_layer_list(layer_list):
        # all the test layers should have a scale except the one used as ref
        sc_tr_counts = dict(scale=0, translate=0)
        for layer in layer_list:
            _, imkwargs, _ = layer
            if "scale" in imkwargs:
                sc_tr_counts["scale"] += 1
                assert np.all(imkwargs["scale"] != 1)
            if "translate" in imkwargs:
                sc_tr_counts["translate"] += 1
                assert np.all(imkwargs["translate"] != 0)
        assert sc_tr_counts["scale"] == len(layer_list) - 1
        assert sc_tr_counts["translate"] == len(layer_list) - 1

    check_layer_list(layer_list)


def test_metadata():
    left_edge = unyt.unyt_array([0, 0, 0], "m")
    right_edge = unyt.unyt_array([1, 1, 1], "m")
    layer_domain = _mi.LayerDomain(left_edge, right_edge, (100, 100, 100))
    fake_data = np.ones((10, 10))
    md = _mi.create_metadata_dict(fake_data, layer_domain, True, a="a")
    assert isinstance(md, dict)


def test_ref_layer_selection(domains_to_test):
    # assemble some fake layer tuples
    im_type = "image"

    spatial_layer_list = []
    for d in domains_to_test.domain_sets:
        layer_domain = _mi.LayerDomain(d.left_edge, d.right_edge, d.resolution)
        im = np.random.random(d.resolution)
        spatial_layer_list.append((im, {}, im_type, layer_domain))

    # add another small volume layer
    le = unyt.unyt_array([0.1, 0.1, 0.1], "m")
    re = unyt.unyt_array([0.2, 0.2, 0.2], "m")
    res = (3, 4, 5)
    small_vol_domain = _mi.LayerDomain(le, re, resolution=res)
    im = np.random.random(res)
    spatial_layer_list.append((im, {}, im_type, small_vol_domain))

    first_ref = _mi._choose_ref_layer(spatial_layer_list, method="first_in_list")
    expected_ref = spatial_layer_list[0][3]
    assert np.all(first_ref.left_edge == expected_ref.left_edge)
    assert np.all(first_ref.right_edge == expected_ref.right_edge)

    smal_ref = _mi._choose_ref_layer(spatial_layer_list, method="smallest_volume")
    assert np.all(small_vol_domain.left_edge == smal_ref.left_edge)
    assert np.all(small_vol_domain.right_edge == smal_ref.right_edge)

    with pytest.raises(ValueError, match="method must be one of"):
        _ = _mi._choose_ref_layer(spatial_layer_list, method="not_a_method")


def test_2d_3d_mix():

    le = unyt.unyt_array([1.0, 1.0, 1.0], "km")
    re = unyt.unyt_array([2000.0, 2000.0, 2000.0], "m")
    res = (10, 20, 15)
    layer_3d = _mi.LayerDomain(le, re, res)
    ref = _mi.ReferenceLayer(layer_3d)

    le = unyt.unyt_array([1, 1], "km")
    re = unyt.unyt_array([2000.0, 2000.0], "m")
    res = (10, 20)
    layer_2d = _mi.LayerDomain(
        le, re, res, n_d=2, new_dim_value=unyt.unyt_quantity(1, "km")
    )

    sp_layer = (np.random.random(res), {}, "testname", layer_2d)
    new_layer_2d = ref.align_sanitize_layer(sp_layer)
    assert "scale" not in new_layer_2d[1]  # no scale when it is all 1


@pytest.fixture
def selection_objs():
    slc_1 = _dm.Slice(
        flds=[
            _dm.ytField(field_type="enzo", field_name="density"),
        ],
        normal="x",
        center=_dm.Length_Tuple(value=[0.5, 0.5, 0.5]),
        slice_width=_dm.Length_Value(value=0.25),
        slice_height=_dm.Length_Value(value=0.25),
    )
    slc_2 = _dm.Slice(
        flds=[
            _dm.ytField(field_type="enzo", field_name="density"),
        ],
        normal="x",
        center=_dm.Length_Tuple(value=[0.5, 0.5, 0.5]),
        slice_width=_dm.Length_Value(value=0.25),
        slice_height=_dm.Length_Value(value=0.25),
        resolution=(10, 10),
    )

    slc_3 = _dm.Slice(
        flds=[
            _dm.ytField(field_type="enzo", field_name="temperature"),
        ],
        normal="x",
        center=_dm.Length_Tuple(value=[0.5, 0.5, 0.5]),
        slice_width=_dm.Length_Value(value=0.25),
        slice_height=_dm.Length_Value(value=0.25),
    )

    reg_1 = _dm.Region(
        flds=[
            _dm.ytField(field_type="enzo", field_name="temperature"),
        ],
        left_edge=_dm.Left_Edge(value=[0.0, 0.0, 0.0]),
        right_edge=_dm.Right_Edge(value=[1.0, 1.0, 1.0]),
    )

    reg_2 = _dm.Region(
        flds=[
            _dm.ytField(field_type="enzo", field_name="temperature"),
        ],
        left_edge=_dm.Left_Edge(value=[0.0, 0.0, 0.0]),
        right_edge=_dm.Right_Edge(value=[0.8, 1.0, 1.0]),
    )

    reg_3 = _dm.Region(
        flds=[
            _dm.ytField(field_type="enzo", field_name="density"),
        ],
        left_edge=_dm.Left_Edge(value=[0.0, 0.0, 0.0]),
        right_edge=_dm.Right_Edge(value=[1.0, 1.0, 1.0]),
    )
    return slc_1, slc_2, slc_3, reg_1, reg_2, reg_3


def test_selection_comparison(selection_objs):
    slc_1, slc_2, slc_3, reg_1, reg_2, reg_3 = selection_objs
    assert _mi.selections_match(slc_1, slc_2) is False
    assert _mi.selections_match(slc_1, slc_3)
    assert _mi.selections_match(slc_1, reg_1) is False
    assert _mi.selections_match(reg_1, reg_2) is False
    assert _mi.selections_match(reg_1, reg_3) is True


def test_timeseries_container(selection_objs):
    slc_1, slc_2, slc_3, reg_1, reg_2, reg_3 = selection_objs
    tc = _mi.TimeseriesContainer()

    im_kwargs = {}
    shp = (10, 10, 10)
    # note: domain here is a placeholder, not actually used in tc
    domain = _mi.LayerDomain(
        unyt.unyt_array([0, 0, 0], "m"), unyt.unyt_array([1.0, 1.0, 1.0], "m"), shp
    )
    im = np.random.random(shp)

    print("what what")
    for _ in range(3):
        tc.add(reg_1, ("enzo", "temperature"), (im, im_kwargs, "image", domain))

    assert len(tc.layers_in_selections[0]) == 3

    shp = (10, 10)
    # note: domain here is a placeholder, not actually used in tc
    domain = _mi.LayerDomain(
        unyt.unyt_array([0, 0], "m"),
        unyt.unyt_array([1.0, 1.0], "m"),
        shp,
        n_d=2,
    )
    im = np.random.random(shp)

    for _ in range(2):
        tc.add(slc_1, ("enzo", "temperature"), (im, im_kwargs, "image", domain))
    for _ in range(2):
        tc.add(slc_3, ("enzo", "temperature"), (im, im_kwargs, "image", domain))

    assert len(tc.layers_in_selections[1]) == 4

    for _ in range(2):
        tc.add(slc_2, ("enzo", "temperature"), (im, im_kwargs, "image", domain))

    assert len(tc.layers_in_selections[2]) == 2

    for _ in range(2):
        tc.add(slc_2, ("enzo", "density"), (im, im_kwargs, "image", domain))

    assert len(tc.layers_in_selections[3]) == 2

    concatd = tc.concat_by_selection()
    assert len(concatd) == 4
    assert concatd[0][0].shape == (3, 10, 10, 10)
    assert concatd[1][0].shape == (4, 10, 10)
    assert concatd[2][0].shape == (2, 10, 10)
    assert concatd[3][0].shape == (2, 10, 10)


file_sel_dicts = [
    {"file_pattern": "test_fi_???"},
    {},  # just the directory
    {"file_list": ["test_fi_001", "test_fi_002"]},
    {
        "file_pattern": "test_fi_???",
        "file_range": (0, 100, 1),
    },
]


@pytest.mark.parametrize("file_sel_dict", file_sel_dicts)
def test_find_timeseries_file_selection(tmp_path, file_sel_dict):

    fdir = tmp_path / "output"
    fdir.mkdir()

    base_name = "test_fi_"
    nfiles = 10
    for ifile in range(0, nfiles):
        fname = base_name + str(ifile).zfill(3)
        newfi = fdir / fname
        newfi.touch()

    fdir = str(fdir)
    file_sel_dict["directory"] = fdir

    tsfs = _mi.TimeSeriesFileSelection.parse_obj(file_sel_dict)

    files = _mi._find_timeseries_files(tsfs)
    if "file_list" not in file_sel_dict:
        assert len(files) == nfiles


def test_yt_data_dir_check(tmp_path):

    fdir = tmp_path / "output"
    fdir.mkdir()

    init_dir = ytcfg.get("yt", "test_data_dir")

    fname_list = []
    base_name = "test_fi_blah_"
    nfiles = 7
    for ifile in range(0, nfiles):
        fname = base_name + str(ifile).zfill(3)
        newfi = fdir / fname
        newfi.touch()
        fname_list.append(fname)

    ytcfg.set("yt", "test_data_dir", str(fdir.absolute()))

    files = _mi._validate_files(fname_list)
    assert len(files) == nfiles

    files = _mi._generate_file_list("test_fi_blah_???")
    assert len(files) == nfiles
    ytcfg.set("yt", "test_data_dir", init_dir)
