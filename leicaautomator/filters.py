from numba import jit
import numpy as np


def pop_bilateral(img, selem, s0=10, s1=10):
    """Simple pop bilateral filter.

    Parameters
    ----------
    img : 2d array
        Padded image.
    selem : 2d array
        Selem. Only y-shape will be considered, resulting in a square selem.
    s0 : int
        Lower bound.
    s1 : int
        Higher bound.
    """
    img = img.astype(np.int16) # avoid overrun when calculating diff
    pad = selem.shape[0]//2 # square selem for now
    selem_size = 2*pad+1 # always center in center
    out = np.zeros(img.shape, dtype=np.uint8) # nopython, nogil
    img = np.pad(img, pad, mode='edge') # nopython, nogil
    _pop_bilateral(img, selem_size, out, s0, s1)
    return out


@jit(nogil=True, nopython=True)
def _pop_bilateral(img, selem_size, out, s0=10, s1=10):
    iy, ix = img.shape
    pad = selem_size//2
    for i in range(iy-2*pad):
        for j in range(ix-2*pad):
            val = img[i+pad, j+pad]
            o = 0
            for ii in range(selem_size):
                for jj in range(selem_size):
                    diff = img[i+ii, j+jj] - val
                    if diff <= -s0 or diff >= s1:
                        o += 1
            out[i, j] = o # cheaper than accessing array in each inner loop


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
    # 2n instead of 2^2
    for i in range(iy-2*pad):
        for j in range(ix-2*pad):
            o = 0
            for jj in range(selem_size):
                o += rows[i, j+jj]
            out[i, j] = o // selem_size**2
