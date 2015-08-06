# -*- coding: UTF-8 -*-

from array import array
from bisect import bisect

from pandac.PandaModules import PNMImage, Point2D

from src import USE_COMPILED


class Table1 (object):
    """
    Tabulated function of one parameter.
    Linear interpolation inside the range,
    linear or clamping extrapolation outside.
    """

    def __init__ (self, p1, v, name=None):

        self.name = name

        self._p1 = p1
        self._v = v


    def __call__ (self, p1, clamp=False):

        il, ir = _get_interp_indices(self._p1, p1)
        p1l = self._p1[il]
        p1r = self._p1[ir]
        v1l = self._v[il]
        v1r = self._v[ir]
        if not clamp or p1l < p1 < p1r:
            ifac = (p1 - p1l) / float(p1r - p1l)
            if isinstance(v1l, (tuple, list)):
                v = [(v1l1 + (v1r1 - v1l1) * ifac) for v1l1, v1r1 in zip(v1l, v1r)]
            else:
                v = v1l + (v1r - v1l) * ifac
        elif p1 <= p1l:
            return v1l
        else: # p1 >= p1r
            return v1r
        return v


class Table2 (object):
    """
    Tabulated function of two parameters.
    Linear interpolation inside the range,
    linear or clamping extrapolation outside.
    """

    def __init__ (self, p1, p2, v, name=None):

        self.name = name

        self._p1 = tuple(p1)
        if not isinstance(p2[0], float):
            self._v = tuple(Table1(x, y) for x, y in zip(p2, v))
        else:
            self._v = tuple(Table1(p2, y) for y in v)


    def __call__ (self, p1, p2, clamp=False):

        il, ir = _get_interp_indices(self._p1, p1)
        p1l = self._p1[il]
        p1r = self._p1[ir]
        v1l = self._v[il](p2, clamp)
        v1r = self._v[ir](p2, clamp)
        if not clamp or p1l < p1 < p1r:
            ifac = (p1 - p1l) / float(p1r - p1l)
            if isinstance(v1l, (tuple, list)):
                v = [(v1l1 + (v1r1 - v1l1) * ifac) for v1l1, v1r1 in zip(v1l, v1r)]
            else:
                v = v1l + (v1r - v1l) * ifac
        elif p1 <= p1l:
            return v1l
        else: # p1 >= p1r
            return v1r
        return v


class Table3 (object):
    """
    Tabulated function of three parameters.
    Linear interpolation inside the range,
    linear or clamping extrapolation outside.
    """

    def __init__ (self, p1, p2, p3, v, name=None):

        self.name = name

        self._p1 = tuple(p1)
        if not isinstance(p2[0], float):
            self._v = tuple(Table2(x, y, z) for x, y, z in zip(p2, p3, v))
        else:
            self._v = tuple(Table2(p2, p3, z) for z in v)


    def __call__ (self, p1, p2, p3, clamp=False):

        il, ir = _get_interp_indices(self._p1, p1)
        p1l = self._p1[il]
        p1r = self._p1[ir]
        v1l = self._v[il](p2, p3, clamp)
        v1r = self._v[ir](p2, p3, clamp)
        if not clamp or p1l < p1 < p1r:
            ifac = (p1 - p1l) / float(p1r - p1l)
            if isinstance(v1l, (tuple, list)):
                v = [(v1l1 + (v1r1 - v1l1) * ifac) for v1l1, v1r1 in zip(v1l, v1r)]
            else:
                v = v1l + (v1r - v1l) * ifac
        elif p1 <= p1l:
            return v1l
        else: # p1 >= p1r
            return v1r
        return v


def _get_interp_indices (seq, val):

    ir = bisect(seq, val)
    il = ir - 1
    if il < 0:
        il += 1; ir += 1
    elif ir >= len(seq):
        il -= 1; ir -= 1
    return il, ir


# :also-compiled:
class UnitGrid2 (object):

    def __init__ (self, grid):

        if isinstance(grid, list):
            if isinstance(grid[0], array):
                pass
            else:
                grid = [array("d", grow) for grow in grid]
        elif isinstance(grid, basestring):
            grid = UnitGrid2._grid_from_pnm(PNMImage(grid))
        elif isinstance(grid, PNMImage):
            grid = UnitGrid2._grid_from_pnm(grid)
        elif isinstance(grid, (float, int)):
            grid = [array("d", [float(grid)])]
        else:
            raise StandardError("Unknown kind of grid.")

        self._grid = grid
        self._num_x = len(grid)
        self._num_y = len(grid[0])


    @staticmethod
    def _grid_from_pnm (pnm):

        sx = pnm.getReadXSize()
        sy = pnm.getReadYSize()
        grid = [array("d", [0.0] * sy) for i in xrange(sx)]
        for i in xrange(sx):
            for j in xrange(sy):
                grid[i][j] = pnm.getGray(i, sy - j - 1)
        return grid


    def num_x (self):

        return self._num_x


    def num_y (self):

        return self._num_y


    def __call__ (self, xr, yr, tol=0.0, periodic=False):

        return UnitGrid2._interpolate_unit(
            self._grid, self._num_x, self._num_y, xr, yr, tol, periodic)


    @staticmethod
    def _interpolate_unit (grid, numx, numy, xr, yr,
                           tol=0.0, periodic=False):

        cls = UnitGrid2
        Pt = Point2D
        #print "--interpolate-unit-05", "=========="

        #print ("--interpolate-unit-10  "
               #"xr=%.6f  yr=%.6f  numx=%d  numy=%d" % (xr, yr, numx, numy))

        ret = cls._unit_to_index2(numx, numy, xr, yr, tol, periodic)
        if not ret:
            raise StandardError("Point out of range.")
        i1, j1, xr, yr = ret
        #print ("--interpolate-unit-12  "
               #"xr=%.6f  yr=%.6f" % (xr, yr))
        x1 = (i1 + 0.5) / numx
        y1 = (j1 + 0.5) / numy
        di = 1 if xr > x1 else -1
        dj = 1 if yr > y1 else -1
        di2 = di; dj2 = 0
        i2, j2 = cls._shift_index2(numx, numy, i1, j1, di2, dj2, periodic)
        di3 = di; dj3 = dj
        i3, j3 = cls._shift_index2(numx, numy, i1, j1, di3, dj3, periodic)
        di4 = 0; dj4 = dj
        i4, j4 = cls._shift_index2(numx, numy, i1, j1, di4, dj4, periodic)
        # NOTE: Must not use iN, jN below when computing relative coordinates,
        # in case there was wrap due to periodicity.
        #print ("--interpolate-unit-20  "
               #"ij1=%s  ij2=%s  ij3=%s  ij4=%s" % ((i1, j1), (i2, j2), (i3, j3), (i4, j4)))

        if i2 >= 0 and i3 >= 0 and i4 >= 0: # three neighbors
            # Bilinear interpolation.
            x3 = (i1 + di3 + 0.5) / numx
            y3 = (j1 + dj3 + 0.5) / numy
            fd = (x3 - x1) * (y3 - y1)
            f1 = (x3 - xr) * (y3 - yr)
            f2 = (xr - x1) * (y3 - yr)
            f3 = (xr - x1) * (yr - y1)
            f4 = (x3 - xr) * (yr - y1)
            v1 = grid[i1][j1]
            v2 = grid[i2][j2]
            v3 = grid[i3][j3]
            v4 = grid[i4][j4]
            v = (v1 * f1 + v2 * f2 + v3 * f3 + v4 * f4) / fd
            #print ("--interpolate-unit-30  "
                   #"x1=%.6f  y1=%.6f  x3=%.6f  y3=%.6f" % (x1, y1, x3, y3))

        elif i2 >= 0 or i3 >= 0 or i4 >= 0: # one neighbor
            # Linear interpolation.
            if i2 >= 0:
                i2, j2, di2, dj2 = i2, j2, di2, dj2
            elif i3 >= 0:
                i2, j2, di2, dj2 = i3, j3, di3, dj3
            elif i4 >= 0:
                i2, j2, di2, dj2 = i4, j4, di4, dj4
            r = Pt(xr, yr)
            x2 = (i1 + di2 + 0.5) / numx
            y2 = (j1 + dj2 + 0.5) / numy
            r1 = Pt(x1, y1)
            r2 = Pt(x2, y2)
            udr = r2 - r1
            udr.normalize()
            l1 = (r - r1).dot(udr)
            l2 = (r2 - r).dot(udr)
            v1 = grid[i1][j1]
            v2 = grid[i2][j2]
            v = (v1 * l2 + v2 * l1) / (l1 + l2)
            #print ("--interpolate-unit-32  "
                   #"x1=%.6f  y1=%.6f  x2=%.6f  y2=%.6f" % (x1, y1, x2, y2))

        else: # no neighbors (two neighbors not possible)
            v = grid[i1][j1]
            #print ("--interpolate-unit-34  "
                   #"x1=%.6f  y1=%.6f" % (x1, y1))

        return v


    @staticmethod
    def _unit_to_index (num, u, tol=0.0, periodic=False):

        k = int(u * num)
        if k < 0:
            if periodic:
                while k < 0:
                    k += num
                    u += 1.0
            elif u > -tol / num:
                k = 0
                u = 0.0
            else: # not valid
                k = -1
                u = -1.0
        elif k >= num:
            if periodic:
                while k >= num:
                    k -= num
                    u -= 1.0
            elif u < 1.0 + tol / num:
                k = num - 1
                u = 1.0
            else: # not valid
                k = -1
                u = -1.0
        return k, u


    @staticmethod
    def _unit_to_index2 (numx, numy, xr, yr, tol=0.0, periodic=False):

        cls = UnitGrid2
        i, xr = cls._unit_to_index(numx, xr, tol, periodic)
        j, yr = cls._unit_to_index(numy, yr, tol, periodic)
        if i < 0 or j < 0: # not valid
            i = -1; j = -1
        return i, j, xr, yr


    @staticmethod
    def _shift_index (num, k, dk, periodic=False):

        k += dk
        if k < 0:
            if periodic:
                while k < 0:
                    k += num
            else: # not valid
                k = -1
        elif k >= num:
            if periodic:
                while k >= num:
                    k -= num
            else: # not valid
                k = -1
        return k


    @staticmethod
    def _shift_index2 (numx, numy, i, j, di, dj, periodic=False):

        cls = UnitGrid2
        i = cls._shift_index(numx, i, di, periodic)
        j = cls._shift_index(numy, j, dj, periodic)
        if i < 0 or j < 0: # not valid
            i = -1; j = -1
        return i, j


if USE_COMPILED:
    from table_c import *
