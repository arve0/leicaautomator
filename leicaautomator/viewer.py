"""
scikit-image viewer plugins and widgets.
"""
from skimage import viewer, draw, filters, exposure, measure, color, morphology
from skimage.measure._regionprops import _RegionProperties as RegionProperties

import scipy.ndimage as nd
import numpy as np
from matplotlib.patches import Polygon

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
        enable = viewer.widgets.CheckBox('enabled', value=False, ptype='plugin')
        self.add_widget(enable)
        self.enabled = False

    def update_plugin(self, name, val):
        super(EnablePlugin, self).update_plugin(name,val)
        self.filter_image()

    def filter_image(self, *args, **kwargs):
        "Filter if plugin enabled and we have image."
        if self.enabled and len(self.arguments):
            arguments = [self._get_value(a) for a in self.arguments]
            kwargs = dict([(name, self._get_value(a))
                           for name, a in self.keyword_arguments.items()])
            filtered = self.image_filter(*arguments, **kwargs)
        elif len(self.arguments):
            # not enabled
            filtered = self.arguments[0]

        if self is self.image_viewer.plugins[-1]:
            # last plugin, update view
            self.display_filtered_image(filtered)

        # send to next plugin
        self.image_changed.emit(filtered)



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
    width = 4 # bandwith of intensity values

    def __init__(self, **kwargs):
        super(HistogramWidthPlugin, self).__init__(**kwargs)
        self.s0 = viewer.widgets.Slider('s0', low=0, high=10,
            value=self.width//2, value_type='int', update_on='release')
        self.s1 = viewer.widgets.Slider('s1', low=0, high=10,
            value=self.width//2, value_type='int', update_on='release')

        self.add_widget(self.s0)
        self.add_widget(self.s1)

    def image_filter(self, img, **kwargs):
        filtered = filters.rank.pop_bilateral(img, **kwargs)
        return exposure.rescale_intensity(-filtered)


class OtsuPlugin(EnablePlugin):
    name = "Otsu Threshold"

    def image_filter(self, image, **kwargs):
        t = filters.threshold_otsu(image)
        return image >= t


class LiThresholdPlugin(EnablePlugin):
    name = "Li Threshold"
    def __init__(self, **kwargs):
        super(LiThresholdPlugin, self).__init__(**kwargs)
        self._invert = viewer.widgets.CheckBox('invert', value=False, ptype='plugin')
        self.add_widget(self._invert)
        self.invert = False

    def image_filter(self, image, **kwargs):
        t = filters.threshold_li(image)
        if self.invert:
            return image < t
        else:
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
    def __init__(self, minimum_area=4000, **kwargs):
        super(MinimumAreaPlugin, self).__init__(**kwargs)
        self.name = "Minimum area"
        area = viewer.widgets.Slider('minimum_area', low=1000, high=100000,
                    value=minimum_area, value_type='int')
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
        self.regions = []

        self.move_region = MoveRegion(image_viewer, self)
        image_viewer.add_tool(self.move_region)


    def filter_image(self, *args, **kwargs):
        if self.regions:
            # remove previous regions from canvas
            for r in self.regions:
                try:
                    r._polygon.remove()
                    r._text.remove()
                except ValueError:
                    continue
        super(RegionPlugin, self).filter_image(*args, **kwargs)


    def image_filter(self, img):
        self.labels = measure.label(img, background=0)
        # do not use label 0
        self.labels[self.labels==0] = self.labels.max() + 1
        # sorted by size, largest first
        self.regions = sorted((r for r in measure.regionprops(self.labels)),
                              key=lambda r: -r.area)
        # only keep max_regions
        if len(self.regions) > self.max_regions.val:
            self.regions = self.regions[:self.max_regions.val]

        self.median_area = np.median([r.area for r in self.regions])

        self.set_coordinates()
        self.set_well_positions()
        self.create_polygons()
        # overlay on original image
        return self.image_viewer.original_image


    def set_coordinates(self):
        if not self.regions:
            return

        for r in self.regions:
            r.y, r.x, r.y_end, r.x_end = r.bbox


    def create_polygons(self):
        "Creates region._polygon which can be added to the mpl axes."
        if not self.regions:
            return

        for region in self.regions:
            region = create_polygon(region)


    def display_filtered_image(self, image):
        "Display original image with polygons, instead of segmented image."
        ax = self.image_viewer.ax

        # set image and add polygons if called with args
        self.image_viewer.image = image

        if self.enabled:
            for r in self.regions:
                ax.add_patch(r._polygon)
            self.set_texts()
            self.image_viewer.canvas.draw()


    def set_well_positions(self):
        """Set property well_x/y on region.

        Returns
        -------
        list of skimage.regionprops
            Regions with extra property ``well_x`` and ``well_y`` set.
        """
        for direction in ['x', 'y']:
            regions = sorted(self.regions, key=lambda r: getattr(r, direction))

            # calc dx
            previous = regions[0]
            for region in regions:
                dx = getattr(region, direction) - getattr(previous, direction)
                setattr(region, 'd' + direction, dx)
                previous = region

            dxs = np.array([getattr(r, 'd' + direction) for r in regions])
            min_threshold = dxs.max() * 0.5
            mask = np.index_exp[dxs > min_threshold][0]
            # do not include all high dxs
            max_threshold = dxs.max() * 0.9
            mask &= np.index_exp[dxs < max_threshold][0]
            step = np.median(dxs[mask])

            # add well_x/y property to region
            well = 0
            previous = regions[0]
            for r in regions:
                dx = getattr(r, direction) - getattr(previous, direction)
                # if gradient to prev coordinate is high, we have a new row/column
                if dx > min_threshold:
                    well += 1
                setattr(r, 'well_' + direction, well) # start at 1
                previous = r

        self.regions = regions
        return regions


    def set_texts(self):
        "create _text property of well positions"
        ax = self.image_viewer.ax
        for r in self.regions:
            text = '%s,%s' % (r.well_x+1, r.well_y+1) # (1,1) top left
            x = r.x + (r.x_end - r.x) / 4
            y = r.y_end - (r.y_end - r.y) / 3
            try:
                r._text.set_text(text)
                r._text.set_position((x, y))
            except AttributeError:
                r._text = ax.text(x, y, text, color='w',
                                  fontsize=14, backgroundcolor='k')


    def output(self):
        return (self.labels, self.regions)

##
# Helper functions
##
def create_polygon(r):
    r.vertices = ((r.x, r.y), (r.x, r.y_end),
                  (r.x_end, r.y_end), (r.x_end, r.y))
    r._polygon = Polygon(r.vertices, fill=False, edgecolor='y', linewidth=2)
    return r


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




##
# Canvas tools
##
class MoveRegion(viewer.canvastools.base.CanvasToolBase):
    """Moves regions around by clicking on them.

    http://matplotlib.org/users/event_handling.html#draggable-rectangle-exercise
    """
    def __init__(self, image_viewer, region_plugin):
        super(MoveRegion, self).__init__(image_viewer)
        self.region_plugin = region_plugin
        self.region = None # selected region
        self.canvas = self.viewer.canvas

    def on_mouse_press(self, event):
        if not event.xdata or not event.ydata:
            return
        x = int(event.xdata)
        y = int(event.ydata)
        # store position, for calculation dx/dy
        self.x = x
        self.y = y

        # will select first region if two regions overlap
        self.region = next((r for r in self.region_plugin.regions
                            if x >= r.x and x <= r.x_end and
                            y >= r.y and y <= r.y_end), None)
        if event.dblclick and self.region:
            # remove
            self.region_plugin.regions.remove(self.region)
            self.region._polygon.remove()
            self.region._text.remove()
            self.canvas.draw()
            self.region = None
            return

        elif event.dblclick:
            # add region where double click is at
            label = self.region_plugin.labels.max() + 1
            # square in label image
            width = (self.region_plugin.median_area)**0.5 / 2
            slice_ = (slice(y - width, y + width),
                      slice(x - width, x + width))
            self.region_plugin.labels[slice_] = label

            # add region
            r = RegionProperties(slice_, label, self.region_plugin.labels,
                                 intensity_image=None, cache_active=False)
            r.y, r.x = r.centroid
            r.x -= width
            r.y -= width
            # draw square around regions of interest
            r.x_end = r.x + 2*width
            r.y_end = r.y + 2*width

            r = create_polygon(r)
            self.ax.add_patch(r._polygon)
            self.region_plugin.regions.append(r)
            self.region_plugin.set_well_positions()
            self.region_plugin.set_texts()
            self.ax.draw_artist(r._polygon)
            self.ax.draw_artist(r._text)
            self.canvas.blit(self.ax.bbox)
            return
        elif self.region:
            self.region._polygon.set_animated(True)
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)

    def on_move(self, event):
        if not event.xdata or not event.ydata:
            return
        if not self.region:
            return
        x = int(event.xdata)
        y = int(event.ydata)
        dx = x - self.x
        dy = y - self.y
        if dx == 0 and dy == 0:
            return
        vertices = [(v[0]+dx, v[1]+dy) for v in self.region.vertices]
        self.region._polygon.set_xy(vertices)
        # draw
        self.canvas.restore_region(self.background)
        self.ax.draw_artist(self.region._polygon)
        self.canvas.blit(self.ax.bbox)

    def on_mouse_release(self, event):
        if not self.region:
            return
        x = int(event.xdata)
        y = int(event.ydata)
        dx = x - self.x
        dy = y - self.y
        if dx == 0 and dy == 0:
            # on release first click in double click
            return
        vertices = [(v[0]+dx, v[1]+dy) for v in self.region.vertices]
        self.region._polygon.set_xy(vertices)
        self.region.vertices = vertices
        self.region.x += dx
        self.region.x_end += dx
        self.region.y += dy
        self.region.y_end += dy
        self.region._polygon.set_animated(False)
        self.region_plugin.set_well_positions()
        self.region_plugin.set_texts()
        self.canvas.draw()
        self.region = None
