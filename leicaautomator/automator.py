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

from skimage import io
from .viewer import *
from leicascanningtemplate import ScanningTemplate
from os import path

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
    list of leicaautomator.Spot

    """
    stitched = experiment.stitched
    if not len(stitched):
        return []
    img_path = stitched[0]
    img = io.imread(img_path)

    # viewer
    viewer = ImageViewer(img)
    #viewer += CropPlugin()
    #viewer += EntropyPlugin()
    viewer += HistogramWidthPlugin()
    viewer += OtsuPlugin()
    viewer += ErosionPlugin()
    viewer += DilationPlugin()
    viewer += MinimumAreaPlugin()
    viewer += FillHolesPlugin()
    #viewer += LabelPlugin()
    viewer += RegionPlugin()
    image, regions = viewer.show()[-1] # output of last plugin

    tmpl_path = experiment.scanning_template
    tmpl = ScanningTemplate(tmpl_path)
    field = tmpl.field(1, 1, 1, 1) # first field in first well
    x_start = field.FieldXCoordinate
    y_start = field.FieldYCoordinate







class Spot:
    def __init__(self, position, well):
        """Object for spots found on glass slides.

        Properties
        ----------
        position : tuple
            Spatial stage position of well in meters.
        well : tuple
            Coordinates of well. Example (1,1) is top left well.
        image : ndarray
            Image data of well.
        """
        self.position = position
        self.well = well
        self.image = None
