import json
import numpy
import pickle
import zlib
from io import StringIO


def _getattr(o, k):
    if 'image' in k or k[0] == '_':
        return None
    try:
        v = o[k]
        if type(v) == numpy.ndarray:
            v = v.tolist()
        return v
    except KeyError:
        return None

def _get(region):
    r = {}
    for k in region.__dict__:
        v = _getattr(region, k)
        if v is not None:
            r[k] = v
    return r

def save_regions(regions, filename):
    "Save regions as compressed (gzip) pickle."
    with open(filename, 'w') as fp:
        s = StringIO
        json.dump(regions, s)
        s.seek(0)
        zlib.compress(s.read())
        s.seek(0)
        fp.write(s.read())

def flatten(iterable):
    return [x for sub in iterable for x in sub]
