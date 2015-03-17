"""
scikit-image viewer plugins and widgets.
"""
from skimage import viewer, draw, filters, exposure, measure, color, morphology
import scipy.ndimage as nd
import numpy as np


import pdb

##
# Viewer
##
class ImageViewer(viewer.viewers.ImageViewer):
    "override viewer to not emit plugin._update_original_image"

    #copied from scikit-image
    def __add__(self, plugin):
        """Add plugin to ImageViewer"""
        plugin.attach(self)
    # do not emit
    #    self.original_image_changed.connect(plugin._update_original_image)

        if plugin.dock:
            location = self.dock_areas[plugin.dock]
            dock_location = viewer.qt.Qt.DockWidgetArea(location)
            dock = viewer.qt.QtWidgets.QDockWidget()
            dock.setWidget(plugin)
            dock.setWindowTitle(plugin.name)
            self.addDockWidget(dock_location, dock)

            horiz = (self.dock_areas['left'], self.dock_areas['right'])
            dimension = 'width' if location in horiz else 'height'
            self._add_widget_size(plugin, dimension=dimension)

        return self

    def show(self):
        "Call filter_image of first plugin, then super.show()"
        # find first plugin which have image_filter != None
        for plugin in self.plugins:
            if plugin.image_filter:
                plugin.filter_image()
                break
        return super(ImageViewer, self).show()



##
# Plugins
##
class SeriesPlugin(viewer.plugins.Plugin):
    "Attach widgets in series. Output of one plugin is sent to the next one."

    def attach(self, image_viewer):
        """Override attach to link plugins with plugin.image_changed instead
        of all listening to image_viewer.original_image_changed
        """
        self.dock = 'right'
        self.setParent(image_viewer)
        self.setWindowFlags(viewer.qt.QtCore.Qt.Dialog)

        self.image_viewer = image_viewer
        if len(image_viewer.plugins) == 0:
            self.arguments = [image_viewer.image]
            image_viewer.original_image_changed.connect(self._update_original_image)
        else:
            self.arguments = [image_viewer.plugins[-1].arguments[0]]
            image_viewer.plugins[-1].image_changed.connect(self._update_original_image)

        image_viewer.plugins.append(self)
        # do not filter image, wait until plugin.show is called
        #self.filter_image()


class EnablePlugin(SeriesPlugin):
    "Plugin with checkbox for enable/disable"
    def __init__(self, **kwargs):
        super(EnablePlugin, self).__init__(**kwargs)
        enable = viewer.widgets.CheckBox('enabled', value=True, ptype='plugin')
        self.add_widget(enable)
        self.enabled = True

    def update_plugin(self, name, val):
        super(EnablePlugin, self).update_plugin(name,val)
        self.filter_image()

    def filter_image(self, **kwargs):
        "Filter if plugin enabled and we have image."
        if self.enabled and len(self.arguments):
            super(EnablePlugin, self).filter_image(**kwargs)
        elif len(self.arguments):
            self.display_filtered_image(self.arguments[0])
            self.image_changed.emit(self.arguments[0])


class SelemPlugin(EnablePlugin):
    """Add selem size widget for filters that use selem, instead of defining a
    separate filter-function for each of them.
    """
    selem_size = 2
    def __init__(self, **kwargs):
        super(SelemPlugin, self).__init__(**kwargs)
        size = viewer.widgets.Slider('selem', low=1, high=10,
            value=self.selem_size, value_type='float', ptype='plugin',
            update_on='release')
        self.add_widget(size)
        size.callback = self.update_selem
        self.keyword_arguments['selem'] = morphology.disk(self.selem_size)

    def update_selem(self, name, value):
        self.keyword_arguments['selem'] = morphology.disk(value)
        self.filter_image()


class CropPlugin(SeriesPlugin):
    "Crop plugin with reset button"
    def __init__(self, maxdist=10, **kwargs):
        super(CropPlugin, self).__init__(**kwargs)
        self.name = 'Crop'
        self.maxdist = maxdist

    def attach(self, image_viewer):
        super(CropPlugin, self).attach(image_viewer)
        self.rect_tool = viewer.canvastools.RectangleTool(image_viewer,
                                       maxdist=self.maxdist,
                                       on_enter=self.crop)
        self.artists.append(self.rect_tool)
        self.add_widget(ResetWidget())

    def crop(self, extents):
        xmin, xmax, ymin, ymax = extents
        cropped = self.arguments[0][ymin:ymax+1, xmin:xmax+1]

        self.display_filtered_image(cropped)
        self.image_changed.emit(cropped)


class EntropyPlugin(SelemPlugin):
    name = "Entropy"

    def image_filter(self, img, selem, **kwargs):
        ent = filters.rank.entropy(img, selem)
        return exposure.rescale_intensity(ent)


class HistogramWidthPlugin(SelemPlugin):
    name = "Histogram width"
    selem_size = 2

    def image_filter(self, img, selem, **kwargs):
        filtered = filters.rank.pop_bilateral(img, selem, s0=2, s1=2)
        thresh = filters.threshold_li(filtered)
        return filtered < thresh


class OtsuPlugin(EnablePlugin):
    name = "Otsu"

    def image_filter(self, image, **kwargs):
        t = filters.threshold_otsu(image)
        return image >= t


class ErosionPlugin(SelemPlugin):
    name = "Erosion"
    selem_size = 2.5

    def image_filter(self, image, selem, **kwargs):
        from skimage import morphology
        return morphology.erosion(image, selem)


class DilationPlugin(SelemPlugin):
    name = "Dilation"
    selem_size = 2

    def image_filter(self, image, selem, **kwargs):
        from skimage import morphology
        return morphology.dilation(image, selem)


class MinimumAreaPlugin(EnablePlugin):
    def __init__(self, minimum_area=1000, **kwargs):
        super(MinimumAreaPlugin, self).__init__(**kwargs)
        self.name = "Minimum area"
        area = viewer.widgets.Slider('minimum_area', low=1, high=10000, value=minimum_area,
                        value_type='int')
        self.add_widget(area)


    def image_filter(self, img, minimum_area, **kwargs):
        from numpy import bincount

        labels = measure.label(img)
        counts = bincount(labels.ravel())
        # set background count to zero
        counts[counts.argmax()] = 0
        mask = counts > minimum_area
        return mask[labels]


class FillHolesPlugin(EnablePlugin):
    def __init__(self, **kwargs):
        super(FillHolesPlugin, self).__init__(**kwargs)
        self.name = 'Fill holes'
        self.add_widget(viewer.widgets.CheckBox('clear_border'))
        self.add_widget(viewer.widgets.Slider('zero_border', low=0, high=20,
                            value=3, value_type='int'))

    def image_filter(self, img, clear_border, zero_border):
        cleared = img.copy()
        if zero_border:
            a = zero_border
            cleared[ :a,:] = 0
            cleared[-a:,:] = 0
            cleared[:, :a] = 0
            cleared[:,-a:] = 0
        if clear_border:
            segmentation.clear_border(cleared)
        return nd.morphology.binary_fill_holes(cleared)


class LabelPlugin(EnablePlugin):
    name = 'Label'
    def image_filter(self, img, **kwargs):
        l = measure.label(img, background=0)
        if l.max() > 2**16-1:
            print('more than 2^16 labels, aborting labeling')
            return img
        return color.label2rgb(l, image=self.image_viewer.original_image)
                                #bg_color=(0,0,0))


class RegionPlugin(EnablePlugin):
    name = 'Region'
    def image_filter(self, img):
        labels = measure.label(img, background=0)
        self.circles = np.zeros_like(labels)
        self.regions = [r for r in measure.regionprops(labels)]
        rs = [reg.equivalent_diameter/2 for reg in self.regions]

        # median as representation for area
        r = np.median(rs)

        for region in self.regions:
            # draw circle around regions of interest
            rr, cc = draw.circle(*region.centroid + (r,))
            self.circles[rr, cc] = region.label
            # creat .x and .y property for easy access
            region.y, region.x, region.y_end, region.x_end = region.bbox

        self.regions = set_well_positions(self.regions)

        # set background to -1, label2rbg will not draw -1
        # ** this will change in skimage v0.12 -1 -> 0 **
        self.circles[self.circles==0] = -1

        # return overlay image
        return color.label2rgb(self.circles, image=self.image_viewer.original_image)

    def output(self):
        return (self.circles, self.regions)



##
# Widgets
##
class ResetWidget(viewer.widgets.BaseWidget):
    "Reset button which sets image to original_image"
    def __init__(self):
        super(ResetWidget, self).__init__(self)
        self.reset_button = viewer.qt.QtGui.QPushButton('Reset')
        self.reset_button.clicked.connect(self.reset)

        self.layout = viewer.qt.QtGui.QHBoxLayout(self)
        self.layout.addWidget(self.reset_button)

    def reset(self):
        img = self.plugin.image_viewer.original_image.copy()
        self.plugin.display_filtered_image(img)
        self.plugin.image_changed.emit(img)


def set_well_positions(regions):
    """Set property well_x/y on region. Helper function for RegionPlugin.

    Parameters
    ----------
    regions : list of skimage.regionprops
        Region should also have set ``x`` and ``y`` property.

    Returns
    -------
    list of skimage.regionprops
        Regions with extra property ``well_x`` and ``well_y`` set.
    """
    for direction in ['x', 'y']:
        regions = sorted(regions, key=lambda r: getattr(r, direction))
        gradients = np.gradient([getattr(r, direction) for r in regions])
        gradient_treshold = max(gradients) / 2

        # add well_x/y property to region
        well = 0
        previous = regions[0]
        for region in regions:
            dx = getattr(region, direction) - getattr(previous, direction)
            # if gradient to prev coordinate is high, we have a new row/column
            if dx > gradient_treshold:
                well += 1
            setattr(region, 'well_' + direction, well)
            previous = region

    return regions
