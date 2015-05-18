"""
# PLAN

- scan whole slide with *single regular matrix*
  - input template name
  - output leicaexperiment.Experiment
- find spots in whole slide
  - input leicaexperiment.Experiment
  - output list of dict
    - position: spatial position
    - well: well coordinate
- for every spot
  - do a scan
    - input
      - scan template name
      - x,y position in meters
    - output
      - stitched image -> added to dict, image: imgdata


# Keep

- whole glass marked with well positions
- compressed spot scan
- stitched spots
- list_of_wells.json without imgdata

"""
from skimage import io, transform
from .viewer import *
from leicascanningtemplate import ScanningTemplate
from microscopestitching import stitch, ImageCollection
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
        stitched = stitch(ic)

    return stitched

    

def set_stage_position(regions, scanning_template):
    """
    Parameters
    ----------
    regions : list of skimage.measure.regionprops
    scanning_template : str or ScanningTemplate
        Scanning template to the scan where the regions was found.
    """
    ##
    # Position of center pixel
    ##
    tmpl_path = experiment.scanning_template
    tmpl = ScanningTemplate(tmpl_path)
    field = tmpl.field(1, 1, 1, 1) # first field in first well
    y_center = field.FieldYCoordinate # in meters
    x_center = field.FieldXCoordinate

    ##
    # pixel size
    ##
    y_distance = tmpl.properties.ScanFieldStageDistanceY * 1e-6 # in microns - DAMN IT LEICA!"#$%
    x_distance = tmpl.properties.ScanFieldStageDistanceX * 1e-6

    img_shape = io.imread(experiment.images[0]).shape
    yoffset, xoffset = ic.median_translation()

    # do not trust reported px size in TIF metadata
    y_px_size = y_distance / (img_shape[0] + yoffset)
    x_px_size = x_distance / (img_shape[1] + xoffset)

    ##
    # top left pixel position
    ##
    y_start = y_center - img_shape[0]//2 * y_px_size
    x_start = x_center - img_shape[1]//2 * x_px_size
    for region in regions:
        region.real_x = x_start + region.x*x_px_size
        region.real_y = y_start + region.y*y_px_size

    x_wells = sorted(set(r.well_x for r in regions))
    y_wells = sorted(set(r.well_y for r in regions))

    # find mean dx/dy between wells
    dxs = []
    prev_median = get_x_median(regions, x_wells[0])
    for x in x_wells[1:]:
        median = get_x_median(regions, x)
        dxs.append(median - prev_median)
        prev_median = median

    dys = []
    prev_median = get_y_median(regions, y_wells[0])
    for y in y_wells[1:]:
        median = get_y_median(regions, y)
        dys.append(median - prev_median)
        prev_median = median

    dx = np.mean(dxs)
    dy = np.mean(dys)
    print('Well distance x in microns:', str(dx*1e6))
    print('Well distance y in microns:', str(dy*1e6))

    return regions


def print_offsets(regions):
    # print offsets
    first_x, first_y = next(((r.real_x, r.real_y) for r in regions
                            if r.well_x == 0 and r.well_y == 0), None)
    print('============')
    print('Well offsets')
    print('============')
    print('( well )   x[um], y[um]')
    print('-----------------------')

    # sort regions by well position
    regions = sorted(regions, key=lambda r: (r.well_x, r.well_y))

    for r in regions:
        expected_x, expected_y = (first_x + dx*r.well_x, first_y + dy*r.well_y)
        offset_x = round((r.real_x - expected_x)*1e6)
        offset_y = round((r.real_y - expected_y)*1e6)
        # only print if offset above 1 micron
        if abs(offset_x) > 10 or abs(offset_y) > 1:
            print('(%2d, %2d)   %5d, %5d' % (r.well_x, r.well_y, offset_x, offset_y))

    


def get_x_median(regions, x):
    """Get median position of given regions.

    Parameters
    ----------
    regions : list of RegionProperties
        List of regions with region.real_x and region.real_y set.
    x : int
        Which x well position to get median for.
    """
    return np.median([r.real_x for r in regions if r.well_x == x])


def get_y_median(regions, y):
    """Get median position of given regions.

    Parameters
    ----------
    regions : list of RegionProperties
        List of regions with region.real_x and region.real_y set.
    y : int
        Which y well position to get median for.
    """
    return np.median([r.real_y for r in regions if r.well_y == y])
