from numba import jit
import numpy as np


def pop_bilateral(img, selem, s0=10, s1=10, which=None):
    """Population bilateral filter.
    
    Parameters
    ----------
    img : 2d array uint
        Image. Should be of type unint (8, 16, 32 or 64).
    selem : 2d array
        Structuring element. Only y-shape will be considered,
        resulting in a square selem.
    s0 : int
        Lower bound.
    s1 : int
        Higher bound.

    Returns
    -------
    2d array
        Image with population of pixels in neighborhood which
        are within range [f-s0, f+s1] where f is the value of
        the center pixel. ``dtype`` will depend on input ``selem``.
    """
    limits = _check_type(img.dtype)
    hist = np.zeros(limits.max)

    pad = selem.shape[0]//2 # square selem for now
    selem_size = 2*pad+1

    t = _get_out_type(selem_size, 1)
    out = np.zeros(img.shape, dtype=t)
    img = np.pad(img, ((pad+1, pad), (pad, pad)), mode='edge') # one extra on top
    _pop_bilateral(img, hist, selem_size, out, s0, s1)
    return out


@jit(nogil=True, nopython=True)
def _pop_bilateral(img, hist, selem_size, out, s0=10, s1=10):
    "Sliding window histogram algo"
    iy, ix = img.shape
    pad = selem_size//2
    # initialize histogram
    for ii in range(selem_size):
        for jj in range(selem_size):
            val = img[ii, jj]
            hist[val] += 1
    
    # every pixel in zick zack
    for i in range(1, iy-2*pad): # rows
        if i%2 == 1: # zick
            r = range(ix-2*pad)
        else: # zack
            r = range(ix-2*pad-1, -1, -1)
        
        for j in r: # cols
            # update hist
            if ((j == 0 and i%2 == 1) or
                (j == ix-2*pad-1 and i%2 == 0)): # row step
                for jj in range(selem_size):
                    v1 = img[i-1, j+jj]
                    v2 = img[i+selem_size-1, j+jj]
                    hist[v1] -= 1
                    hist[v2] += 1
            elif i%2 == 1: # column step forward
                for ii in range(selem_size):
                    v1 = img[i+ii, j-1]
                    v2 = img[i+ii, j+selem_size-1]
                    hist[v1] -= 1
                    hist[v2] += 1
            else: # column step backward
                for ii in range(selem_size):
                    v1 = img[i+ii, j+selem_size]
                    v2 = img[i+ii, j]
                    hist[v1] -= 1
                    hist[v2] += 1
                
            # get out value
            val = img[i+pad, j+pad]
            o = 0
            for h in range(val-s0, val+s1+1):
                if h < 0 or h > 255:
                    continue
                o += hist[h]
            out[i-1, j] = o


def mean(img, selem):
    img = img.astype(np.uint32)
    out = np.empty(img.shape, dtype=np.uint8)
    pad = selem.shape[0]//2 # square selem for now
    img = np.pad(img, pad, mode='edge')
    rows = np.zeros(img.shape, dtype=np.uint32) # size of padded
    selem_size = 2*pad+1
    _mean(img, selem_size, rows, out)
    return out


@jit(nopython=True, nogil=True)
def _mean(img, selem_size, rows, out):
    iy, ix = img.shape
    pad = selem_size//2
    for i in range(iy-2*pad):
        for j in range(ix):
            for ii in range(selem_size):
                rows[i, j] += img[i+ii, j]
    # 2n instead of n^2
    for i in range(iy-2*pad):
        for j in range(ix-2*pad):
            o = 0
            for jj in range(selem_size):
                o += rows[i, j+jj]
            out[i, j] = o // selem_size**2


def _check_type(dtype):
    "Check that we are getting a uint, return limits of type"
    try:
        limits = np.iinfo(dtype)
    except ValueError:
        raise ValueError("Image should be uint type")
    if limits.min < 0 or limits.max < 255:
        raise ValueError("Image should be uint type")
    return limits


def _get_out_type(selem_size, max_per_pixel):
    "Return out type which can hold selem_size**2 * max_per_pixel"
    max_population = selem_size**2
    max_value = max_population * max_per_pixel
    if max_value < 2**8:
        return np.uint8
    elif max_value < 2**16:
        return np.uint16
    elif max_value < 2**32:
        return np.uint32
    else:
        return np.uint64
    
