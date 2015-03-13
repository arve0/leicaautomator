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
