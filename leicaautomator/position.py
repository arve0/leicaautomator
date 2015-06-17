"""
Conversion between stage coordinate system and image pixels.
"""

from leicascanningtemplate import ScanningTemplate
import numpy as np


def construct_stage_position(experiment, offset):
    """Constructor for ``stage_position(pixel_position)`` which translates pixel
    position to stage position.

    Parameters
    ----------
    experiment : leicaexperiment.Experiment
        Stage displacement is read from this experiment.
    offset : tuple (y, x)
        Registered offset between images in pixels.
    """
    # experiment must have 2 or more rows/columns
    assert len(experiment.field_rows(0, 0)) > 1, \
            "Experiment must have 2 or more rows"
    assert len(experiment.field_columns(0, 0)) > 1, \
            "Experiment must have 2 or more columns"

    # load template
    tmpl_path = experiment.scanning_template
    tmpl = ScanningTemplate(tmpl_path)

    # pixel size
    yoffset, xoffset = offset
    y_distance = tmpl.properties.ScanFieldStageDistanceY * 1e-6 # in microns
    x_distance = tmpl.properties.ScanFieldStageDistanceX * 1e-6
    img_shape = io.imread(experiment.images[0]).shape
    # do not trust reported px size in TIF metadata
    y_px_size = y_distance / (yoffset % img_shape[0]) # wrap to positive
    x_px_size = x_distance / (xoffset % img_shape[1])

    # reference position, pixel 0,0 in top left image
    field = tmpl.field(1, 1, 1, 1)    # first field in first well
    y_center = field.FieldYCoordinate # in meters
    x_center = field.FieldXCoordinate
    y_start = y_center - img_shape[0]//2 * y_px_size
    x_start = x_center - img_shape[1]//2 * x_px_size

    def stage_position(y, x):
        """Get stage position by pixel coordinate.
        
        Parameters
        ----------
        y : int
            Pixel y coordinate.
        x : int
            Pixel x coordinate.

        Returns
        -------
        tuple (Y, X)
            Stage position of pixel (y, x).
        """
        return (y_start + y*y_px_size, x_start + x*x_px_size)

    return stage_position


def mean_well_displacement(regions):
    """Find mean well displacement.

    Parameters
    ----------
    regions : skimage regionprops
        Regions to find displacement between.

    Returns
    -------
    list [y, x]
        Mean displacement between rows and columns.
    """
    rows_cols = (sorted(set(r.well_y for r in regions)),
                 sorted(set(r.well_x for r in regions)))

    # same algorithm for x/y direction
    result = []
    for i, p, w in [(0, 'y', 'well_y'), (1, 'x', 'well_x')]:
        dxs = []
        # median y/x-position of regions in first row/col
        prev_median = _median(regions, p, w, rows_cols[i][0])
        for x in rows_cols[i][1:]:
            median = _median(regions, p, w, x)
            dxs.append(median - prev_median)
            prev_median = median

        result.append(np.mean(dxs))

    return result


def _median(regions, p, w, x):
    "get median position for given row/col"
    return np.median([getattr(r, p) for r in regions if getattr(r, w) == x])
