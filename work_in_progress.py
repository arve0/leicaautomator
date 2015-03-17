from leicaautomator import find_spots
from leicaautomator.utils import save_regions, flatten
from leicaexperiment import Experiment
from leicacam import CAM
import json
import numpy

experiment = Experiment('../data/experiment--whole')
regions = find_spots(experiment)
save_regions(regions, 'regions.json')

max_well_x = max(r.well_x for r in regions)
max_well_y = max(r.well_y for r in regions)

# initiate connection to microscope
cam = CAM()

tmpl_name = '{ScanningTemplate}leicaautomator'

for i in range(max_well_x):
    for j in range(max_well_y):
        # count downwards on every second column, scanning in zick zack
        if i % 2 == 1:
            j = -(j+1) % max_well_y

        well = next((r for r in regions if r.well_x == i and r.well_y == j), None)
        if not well:
            continue

        print('Scanning well ({},{})'.format(i,j))

        # create template, alternate between tmpl_name0/1.xml because of
        # a bug in LASAF (not loading the same name twice)
        tmpl = ScanningTemplate(tmpl_name + str(j%2) + '.xml')
        tmpl.move_well(1,1,region.x, region.y)
        tmpl.write()

        # load and start scan
        cam.load_template(tmpl.filename)
        cam.start_scan()
        # loop until done
        while True:
            msg = cam.receive()
            if not msg:
                sleep(1)
                continue
            
