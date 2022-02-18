import numpy as np
import pytest
from unyt import unyt_array

from yt_napari import _model_ingestor

# indirect testing happens via test_reader, so the tests here focus on explicit
# testing of the domain tracking and alignment


class DomainExpectation:
    def __init__(self, left_edge, right_edge, center, width):
        self.left_edge = left_edge
        self.right_edge = right_edge
        self.center = center
        self.width = width


class Expectations:
    def __init__(self):
        # build a list of domain boundaries that will be combined, flagging
        # the one that should enclose all the others
        self.domain_sets = []

        d = DomainExpectation(
            unyt_array([1, 1, 1], "km"),
            unyt_array([2000.0, 2000.0, 2000.0], "m"),
            unyt_array([1.5, 1.5, 1.5], "km"),
            unyt_array([1, 1, 1], "km"),
        )
        self.domain_sets.append(d)

        d = DomainExpectation(
            unyt_array([0, 0, 0], "m"),
            unyt_array([10.0, 10.0, 10.0], "km"),
            unyt_array([5.0, 5.0, 5.0], "km"),
            unyt_array([10.0, 10.0, 10.0], "km"),
        )
        self.domain_sets.append(d)
        self.enclosing_id = 1  # this one encloses others!

        d = DomainExpectation(
            unyt_array([5, 2, 3], "km"),
            unyt_array([10.0, 4.0, 6.0], "km"),
            unyt_array([7.5, 3.0, 4.5], "km"),
            unyt_array([5.0, 2.0, 3.0], "km"),
        )
        self.domain_sets.append(d)


@pytest.fixture
def domains_to_test() -> Expectations:
    return Expectations()


def test_center_width_from_le_re(domains_to_test):
    for d in domains_to_test.domain_sets:
        cen, wid = _model_ingestor._le_re_to_cen_wid(d.left_edge, d.right_edge)
        assert np.all(cen == d.center)
        assert np.all(wid == d.width)


def test_layer_domain(domains_to_test):
    for d in domains_to_test.domain_sets:
        layer_domain = _model_ingestor.LayerDomain(d.left_edge, d.right_edge)
        assert np.all(layer_domain.center == d.center)
        assert np.all(layer_domain.width == d.width)


def test_domain_tracking(domains_to_test):

    full_domain = _model_ingestor.PhysicalDomainTracker()
    full_domain.update_unit("m")

    for d in domains_to_test.domain_sets:
        full_domain.update_edges(d.left_edge, d.right_edge, update_c_w=True)

    # the full domain extent should now match the enclosing domain
    enclosing_domain = domains_to_test.domain_sets[domains_to_test.enclosing_id]
    for attr in ["left_edge", "right_edge", "center", "width"]:
        expected = getattr(enclosing_domain, attr)
        actual = getattr(full_domain, attr)
        assert np.all(expected == actual)

    # test again with different combination of edge args
    full_domain = _model_ingestor.PhysicalDomainTracker()
    full_domain.update_unit("m")

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


def test_layer_alignment(domains_to_test):
    pass
