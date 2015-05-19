import json
import numpy
import pickle
import zlib
from io import StringIO
from operator import attrgetter

from math import ceil
from multiprocessing import cpu_count
import dask.array as da


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


def zick_zack_sort(list_, sortby):
    """
    Example
    -------
    > class R:
    > def __init__(self, x, y):
    >     self.x = x
    >     self.y = y
    > def __repr__(self):
    >     return "R(%s,%s)" % (self.x, self.y)
    > regions = [R(1,1), R(1,2), R(1,3), R(2,1), R(2,2), R(2,3), R(3,1), R(3,2), R(3,3)]
    > zick_zack_sort(regions, ('y', 'x'))
    [R(1,1), R(2,1), R(3,1), R(3,2), R(2,2), R(1,2), R(1,3), R(2,3), R(3,3)]

    Parameters
    ----------
    list_ : list
        List of objects to sort.
    sortby : iterable
        Attributes in object to sort by.

    Returns
    -------
    list
        Sorted in zick zack.
    """
    if type(sortby) is str:
        sortby = (sortby,)

    list_.sort(key=attrgetter(*sortby))
    
    firstgetter = attrgetter(sortby[0])
    prev = firstgetter(list_[0])

    out = []
    revert = False
    for i in list_:
        cur = firstgetter(i)
        if not revert and cur != prev:
            revert = True
            part = []
        elif revert and cur != prev:
            out.extend(part[::-1])
            revert = False
        if revert:
            part.append(i)
        if not revert:
            out.append(i)
        prev = cur
    return out


def _get_chunks(shape, ncpu):
    """
    Split the array into equal sized chunks based on the number of
    available processors. The last chunk in each dimension absorbs the
    remainder array elements if the number of cpus does not divide evenly into
    the number of array elements.
    >>> _get_chunks((4, 4), 4)
    ((2, 2), (2, 2))
    >>> _get_chunks((4, 4), 2)
    ((2, 2), (4,))
    >>> _get_chunks((5, 5), 2)
    ((2, 3), (5,))
    >>> _get_chunks((2, 4), 2)
    ((1, 1), (4,))
    """
    chunks = []
    nchunks_per_dim = int(ceil(ncpu ** (1./len(shape))))

    used_chunks = 1
    for i in shape:
        if used_chunks < ncpu:
            regular_chunk = i // nchunks_per_dim
            remainder_chunk = regular_chunk + (i % nchunks_per_dim)

            if regular_chunk == 0:
                chunk_lens = (remainder_chunk,)
            else:
                chunk_lens = ((regular_chunk,) * (nchunks_per_dim - 1) +
                              (remainder_chunk,))
        else:
            chunk_lens = (i,)

        chunks.append(chunk_lens)
        used_chunks *= nchunks_per_dim
    return tuple(chunks)


def apply_chunks(function, array, chunks=None, depth=0, mode=None,
                 extra_arguments=(), extra_keywords={}):
    """Map a function in parallel across an array.
    Split an array into possibly overlapping chunks of a given depth and
    boundary type, call the given function in parallel on the chunks, combine
    the chunks and return the resulting array.
    Parameters
    ----------
    function : function
        Function to be mapped which takes an array as an argument.
    array : numpy array
        Array which the function will be applied to.
    chunks : int, tuple, or tuple of tuples, optional
        A single integer is interpreted as the length of one side of a square
        chunk that should be tiled across the array.  One tuple of length
        ``array.ndim`` represents the shape of a chunk, and it is tiled across
        the array.  A list of tuples of length ``ndim``, where each sub-tuple
        is a sequence of chunk sizes along the corresponding dimension. If
        None, the array is broken up into chunks based on the number of
        available cpus. More information about chunks is in the documentation
        `here <https://dask.pydata.org/en/latest/array-design.html>`_.
    depth : int, optional
        Integer equal to the depth of the added boundary cells. Defaults to
        zero.
    mode : 'reflect', 'periodic', 'wrap', 'nearest', optional
        type of external boundary padding
    extra_arguments : tuple, optional
        Tuple of arguments to be passed to the function.
    extra_keywords : dictionary, optional
        Dictionary of keyword arguments to be passed to the function.
    """
    if chunks is None:
        shape = array.shape
        ncpu = cpu_count()
        chunks = _get_chunks(shape, ncpu)

    if mode == 'wrap':
        mode = 'periodic'

    def wrapped_func(arr):
        return function(arr, *extra_arguments, **extra_keywords)

    darr = da.from_array(array, chunks=chunks)
    return darr.map_overlap(wrapped_func, depth, boundary=mode).compute()
