from typing import Optional, Tuple

import numpy as np
import pytest
import unyt

from yt_napari import _model_ingestor as _mi

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
    with pytest.raises(ValueError):
        _ = _mi.LayerDomain(d.left_edge, unyt.unyt_array([1, 2], "m"), d.resolution)

    with pytest.raises(ValueError):
        _ = _mi.LayerDomain(d.left_edge, d.right_edge, (10, 12))

    ld = _mi.LayerDomain(d.left_edge, d.right_edge, (10,))
    assert len(ld.resolution) == 3


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
