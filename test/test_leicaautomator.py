"""
Tests for `leicaautomator` module.
"""
import pytest
from leicaautomator.automator import find_tma_regions
from leicaautomator.utils import stitch
from py import path

@pytest.fixture
def experiment(tmpdir):
    "'experiment--test' in tmpdir. Returns Experiment object."
    from leicaexperiment import Experiment
    e = path.local(__file__).dirpath().join('experiment')
    e.copy(tmpdir.mkdir('experiment'))

    return Experiment(tmpdir.join('experiment').strpath)


def test_stitch(experiment):
    stitched, offset = stitch(experiment)

    assert offset[0] < 0, "offset between rows should be negative"
    assert offset[1] < 0, "offset between cols should be negative"

