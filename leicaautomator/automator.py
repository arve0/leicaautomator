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
# avoid agg backend warning
import matplotlib
matplotlib.use('Agg')

from skimage import io, transform
from .viewer import *
from leicascanningtemplate import ScanningTemplate
import numpy as np

def find_spots(experiment):
    """Finds spots and return position of them in a list.

    Parameters
    ----------
    experiment : leicaexperiment.Experiment
        Matrix Screener experiment to search for spots. Its assumed that the
        experiment contain a single well. If it contain several wells, only
        the first well will be searched for spots.

    Returns
    -------
    list of regions from skimage.measure.regionprops
        Regions have these extra attributes:

        - ``real_x`` : ``x`` in meters.
        - ``real_y`` : ``y`` in meters.
        - ``x``, ``y``, ``x_end``, ``y_end`` : same as ``bbox``.
        - ``well_x`` : well x coordinate, from 0.
        - ``well_y`` : well y coordinate, from 0.
    """
    stitched = experiment.stitched
    if not len(stitched):
        # try stitching
        stitched = experiment.stitch()
        if not len(stitched):
            return []

    img_path = stitched[0]
    img = io.imread(img_path)

    ##
    # Position of pixel 0,0
    ##
    tmpl_path = experiment.scanning_template
    tmpl = ScanningTemplate(tmpl_path)
    field = tmpl.field(1, 1, 1, 1) # first field in first well
    # in meters
    x_start = field.FieldXCoordinate
    y_start = field.FieldYCoordinate

    # coordinates in pixels from TileConfiguration.registered.txt
    stitch_coord = experiment.stitch_coordinates(0,0)
    xmin = min(stitch_coord[0])
    ymin = min(stitch_coord[1])

    # pixel size in microns
    # http://www.openmicroscopy.org/site/support/ome-model/specifications/
    metadata = experiment.field_metadata()
    x_px_size = float(metadata.Image.Pixels.attrib['PhysicalSizeX'])*1e-6
    y_px_size = float(metadata.Image.Pixels.attrib['PhysicalSizeY'])*1e-6

    # adjust in case first field is not placed at 0,0
    # in meters
    real_x_start = x_start + xmin*x_px_size
    real_y_start = y_start + ymin*y_px_size


    ##
    # Find spots with different kind of filters
    ##
    viewer = ImageViewer(img)
    #viewer += CropPlugin()
    #viewer += EntropyPlugin()
    viewer += HistogramWidthPlugin()
    # Li threshold gives lower threshold values then Otsu
    viewer += LiThresholdPlugin()
    #viewer += OtsuPlugin()
    viewer += ErosionPlugin()
    viewer += DilationPlugin()
    viewer += MinimumAreaPlugin()
    viewer += FillHolesPlugin()
    #viewer += LabelPlugin()
    viewer += RegionPlugin()
    # regions is a list of skimage.measure.regionprops
    labels, regions = viewer.show()[-1] # output of last plugin


    for region in regions:
        region.real_x = real_x_start + region.x*x_px_size
        region.real_y = real_y_start + region.y*y_px_size

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

    return labels, regions


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
