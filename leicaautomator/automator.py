"""
Finds tissue micro arrays in an overview image and scan those regions.
"""
from skimage import io, transform
from .viewer import *
from leicascanningtemplate import ScanningTemplate
from microscopestitching import stitch as mstitch
from microscopestitching import ImageCollection
from leicaexperiment import Experiment, attributes
import numpy as np
from warnings import warn, filterwarnings, catch_warnings


def find_tma_regions(image):
    """Find tissue micro array regions in an overview scan. Opens a GUI
    which allows for adjusting filter settings and move, remove or add
    regions by mouse clicks.

    Parameters
    ----------
    image : 2d array
        Overview image to look for tissue samples.

    Returns
    -------
    skimage.measure.regionprops
        List of regions with the extra attributes:

        - ``x``, ``y``, ``x_end``, ``y_end`` : same as ``bbox``.
        - ``well_x`` : column coordinate, 0-indexed.
        - ``well_y`` : row coordinate, 0-indexed.
    """
    if type(image) is str:
        image = io.imread(image)

    viewer = ImageViewer(image)
    viewer += PopBilateralPlugin()
    viewer += MeanPlugin()
    viewer += OtsuPlugin()
    viewer += RegionPlugin()
    return viewer.show()[-1] # output of RegionPlugin


def stitch(experiment):
    if type(experiment) == str:
        experiment = Experiment(experiment)

    images = []
    for i in experiment.images:
        attr = attributes(i)
        if attr.u != 0 or attr.v != 0:
            warn('experiment have several wells, assuming top left well')
            continue
        images.append((i, attr.y, attr.x))

    ic = ImageCollection(images)
    with catch_warnings():
        filterwarnings("ignore")
        stitched = mstitch(ic)

    return stitched
