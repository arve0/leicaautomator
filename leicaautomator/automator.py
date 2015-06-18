"""
Finds tissue micro arrays in an overview image and scan those regions.
"""
from skimage import io
from .viewer import *


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


