from typing import Optional, Tuple

import numpy as np
import pytest
from unyt import unyt_array

from yt_napari import _model_ingestor as _mi

# indirect testing happens via test_reader, so the tests here focus on explicit
# testing of the domain tracking and alignment


class DomainExpectation:
    def __init__(
        self,
        left_edge: unyt_array,
        right_edge: unyt_array,
        center: unyt_array,
        width: unyt_array,
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
            unyt_array([1, 1, 1], "km"),
            unyt_array([2000.0, 2000.0, 2000.0], "m"),
            unyt_array([1.5, 1.5, 1.5], "km"),
            unyt_array([1, 1, 1], "km"),
            (10, 20, 15),
        )
        self.domain_sets.append(d)

        d = DomainExpectation(
            unyt_array([0, 0, 0], "m"),
            unyt_array([10.0, 10.0, 10.0], "km"),
            unyt_array([5.0, 5.0, 5.0], "km"),
            unyt_array([10.0, 10.0, 10.0], "km"),
            (8, 15, 17),
        )
        self.domain_sets.append(d)
        self.enclosing_id = 1  # this one encloses others!

        d = DomainExpectation(
            unyt_array([5, 2, 3], "km"),
            unyt_array([10.0, 4.0, 6.0], "km"),
            unyt_array([7.5, 3.0, 4.5], "km"),
            unyt_array([5.0, 2.0, 3.0], "km"),
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
        _ = _mi.LayerDomain(d.left_edge, unyt_array([1, 2], "m"), d.resolution)

    with pytest.raises(ValueError):
        _ = _mi.LayerDomain(d.left_edge, d.right_edge, (10, 12))

    ld = _mi.LayerDomain(d.left_edge, d.right_edge, (10,))
    assert len(ld.resolution) == 3


def test_domain_tracking(domains_to_test):

    full_domain = _mi.PhysicalDomainTracker()
    full_domain.update_unit_info(unit="m")

    for d in domains_to_test.domain_sets:
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

    with pytest.raises(ValueError):
        full_domain.update_unit_info(unit="code_length")


def test_layer_alignment(domains_to_test):

    # assemble some fake layer tuples
    im_type = "image"

    full_domain = _mi.PhysicalDomainTracker(unit="m")

    spatial_layer_list = []
    for d in domains_to_test.domain_sets:
        layer_domain = _mi.LayerDomain(d.left_edge, d.right_edge, d.resolution)
        im = np.random.random(d.resolution)
        spatial_layer_list.append((im, {}, im_type, layer_domain))
        full_domain.update_from_layer(layer_domain, update_c_w=False)

    full_domain.update_width_and_center()

    # ready to align the layers
    layer_list = full_domain.align_sanitize_layers(spatial_layer_list)

    def check_layer_list(layer_list):
        sc_tr_counts = dict(scale=0, translate=0)
        for layer in layer_list:
            _, imkwargs, _ = layer
            for ky, minval in zip(["scale", "translate"], [1, None]):
                if ky in imkwargs:
                    val = imkwargs[ky]
                    if minval:
                        assert np.all(np.array(val) > minval)
                    sc_tr_counts[ky] += 1

        assert sc_tr_counts["scale"] == len(layer_list) - 1
        assert sc_tr_counts["translate"] == len(layer_list) - 1

    check_layer_list(layer_list)

    # also test separate layer assembly and alignment
    full_domain = _mi.PhysicalDomainTracker()
    layer_list = full_domain.align_sanitize_layers(
        spatial_layer_list, process_layers=True
    )
    check_layer_list(layer_list)

    full_domain = _mi.PhysicalDomainTracker()
    with pytest.raises(RuntimeError):
        # grid_width will not be set, raise error
        layer_list = full_domain.align_sanitize_layer(spatial_layer_list[0])

    # check that a scene center outside the domain results in a translation for
    # all layers
    scene_center = unyt_array([1000.0, 1000.0, 1000.0], "km")
    full_domain.set_scene_center(scene_center)
    assert np.all(full_domain.scene_center == scene_center)
    layer_list = full_domain.align_sanitize_layers(
        spatial_layer_list, process_layers=True
    )
    for _, imkwargs, _ in layer_list:
        assert np.all(np.array(imkwargs["translate"]) != 0)
