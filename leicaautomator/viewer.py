"""
scikit-image viewer plugins and widgets.
"""
from skimage import viewer, draw, filters, exposure, measure, color, morphology
import scipy.ndimage as nd
import numpy as np

# TODO: remove
#import pdb

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
    def __init__(self, **kwargs):
        super(RegionPlugin, self).__init__(**kwargs)
        self.max_regions = viewer.widgets.Slider('maximum number of regions',
                low=0, high=150, value=129, value_type='int', ptype='plugin')
        self.add_widget(self.max_regions)

    def attach(self, image_viewer):
        super(RegionPlugin, self).attach(image_viewer)
        self._overlay_plot = None
        self.regions = None

        self.move_region = MoveRegion(image_viewer, self)
        image_viewer.add_tool(self.move_region)



    def image_filter(self, img):
        self.labels = measure.label(img, background=0)
        # for checking if region.label is falsey, will change in skimage v0.12
        self.labels[self.labels==0] = self.labels.max() + 1
        # only keep number_of_regions
        if self.labels.max() > self.max_regions.val:
            # set them to background
            self.labels[self.labels > self.max_regions.val] = -1
        self.regions = [r for r in measure.regionprops(self.labels)]

        for r in self.regions:
            # creat .x and .y property for easy access
            r.y, r.x, r.y_end, r.x_end = r.bbox

        self.create_overlay()
        self.regions = set_well_positions(self.regions)
        # return overlay image
        return self.overlay


    def create_overlay(self):
        if not self.regions:
            return
        diameters = [r.equivalent_diameter for r in self.regions]
        # median as representation for area
        size = np.median(diameters) * 1.2

        self.overlay = np.zeros_like(self.labels)
        for r in self.regions:
            # draw square around regions of interest
            self.overlay[r.y:r.y + size, r.x:r.x + size] = r.label


    def display_filtered_image(self, overlay):
        "Override: display overlay, instead of filtered image."
        # yellow see through colormap
        cmap = viewer.utils.ClearColormap((0,1,1))
        ax = self.image_viewer.ax

        if not self.enabled:
            if self._overlay_plot:
                ax.images.remove(self._overlay_plot)
                self._overlay_plot = None
            self.image_viewer.image = self.arguments[0]
        else:
            if not self.image_viewer.image is self.image_viewer.original_image:
                # do not update image if its already printed
                self.image_viewer.image = self.image_viewer.original_image
            if self._overlay_plot:
                viewer.utils.update_axes_image(self._overlay_plot, overlay)
            else:
                self._overlay_plot = ax.imshow(overlay > 0, cmap=cmap, alpha=0.3)

            if self.image_viewer.useblit:
                self.image_viewer._blit_manager.background = None

            self.image_viewer.redraw()

    def output(self):
        return (self.labels, self.overlay, self.regions)



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


##
# Canvas tools
##
class MoveRegion(viewer.canvastools.base.CanvasToolBase):
    "Moves regions around by clicking on them."
    def __init__(self, image_viewer, region_plugin):
        super(MoveRegion, self).__init__(image_viewer)
        self.region_plugin = region_plugin
        self.label = None

    def on_mouse_press(self, event):
        self.x = int(event.xdata)
        self.y = int(event.ydata)
        label = self.region_plugin.overlay[self.y,self.x]
        if label:
            # not background
            self.label = label
            self.selected_region = next((r for r in self.region_plugin.regions if r.label == label), None)

    def on_mouse_release(self, event):
        self.label = None

    def on_move(self, event):
        if not self.label:
            return
        x = int(event.xdata)
        y = int(event.ydata)
        dx = x - self.x
        dy = y - self.y
        self.selected_region.x += dx
        self.selected_region.y += dy
        self.x = x
        self.y = y
        self.region_plugin.create_overlay()
        self.region_plugin.display_filtered_image(self.region_plugin.overlay)
