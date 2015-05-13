# -*- coding: UTF-8 -*-

from bisect import bisect


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


