from leicaautomator import find_spots
from leicaexperiment import Experiment


experiment = Experiment('../master/data/experiment--whole')
find_spots(experiment)
