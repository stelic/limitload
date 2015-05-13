# -*- coding: UTF-8 -*-

from math import sqrt, degrees, sin, cos, asin, atan2

from pandac.PandaModules import Vec3D, Quat, QuatD

from src.core.misc import sign


INF_RADIUS = 1e30


class Curve (object):

    def param (self, s):

        raise StandardError("Not implemented.")


    def deriv1 (self, t):

        raise StandardError("Not implemented.")


    def deriv2 (self, t):

        raise StandardError("Not implemented.")


    def xtangent (self, t):

        d1 = self.deriv1(t)
        t = d1
        t.normalize()
        return t


    def xnormal (self, t):

        d1 = self.deriv1(t)
        d2 = self.deriv2(t)
        n = d2 * d1.dot(d1) - d1 * d1.dot(d2)
        n.normalize()
        return n


    def xradius (self, t):

        d1 = self.deriv1(t)
        d2 = self.deriv2(t)
        k = d1.cross(d2).length() / d1.length()**3
        r = 1.0 / k if k > 0.0 else INF_RADIUS
        return r


    def tangent (self, s):

        t = self.param(s)
        return self.xtangent(t)


    def normal (self, s):

        t = self.param(s)
        return self.xnormal(t)


    def radius (self, s):

        t = self.param(s)
        return self.xradius(t)


class Segment (Curve):

    def __init__ (self, p0, p1, n):

        dtyp = type(p0)
        self._p0 = p0
        self._p1 = p1
        self._t = p1 - p0
        self._t.normalize()
        self._n = self._t.cross(n).cross(self._t)
        self._n.normalize()
        # ...in case given normal is not normal to given tangent.
        self._l = (self._p1 - self._p0).length()


    def point (self, s):

        return self._p0 + self._t * s


    def tangent (self, s):

        return self._t


    def normal (self, s):

        return self._n


    def radius (self, s):

        return INF_RADIUS


    def length (self):

        return self._l



class Arc (Curve):

    def __init__ (self, r, a, p0, t0, n0):

        self._dtyp = type(p0)
        self._r = abs(r)
        self._a = abs(a)
        self._p0 = p0
        self._t0 = self._dtyp(t0)
        self._t0.normalize()
        self._n0 = self._t0.cross(n0).cross(self._t0)
        self._n0.normalize()
        # ...in case given normal is not normal to given tangent.
        self._b = self._t0.cross(self._n0)
        self._b.normalize()
        self._vr0 = -self._n0 * self._r
        if isinstance(self._p0, Vec3D):
            self._qx = QuatD()
        else:
            self._qx = Quat()


    def length (self):

        return self._r * self._a


    def _rot (self, s):

        a = s / self._r
        self._qx.setFromAxisAngleRad(a, self._b)
        return self._qx


    def point (self, s):

        q = self._rot(s)
        vr = self._dtyp(q.xform(self._vr0))
        p = self._p0 + (vr - self._vr0)
        return p


    def tangent (self, s):

        q = self._rot(s)
        t = self._dtyp(q.xform(self._t0))
        return t


    def normal (self, s):

        q = self._rot(s)
        n = self._dtyp(q.xform(self._n0))
        return n


    def radius (self, s):

        return self._r


class HelixZ (Curve):

    def __init__ (self, r, a, p0, t0):

        self._dtyp = type(p0)
        self._r = abs(r)
        self._a = abs(a)
        self._ka = sign(a)
        self._p = r * (t0.getZ() / t0.getXy().length())
        a0 = atan2(-t0.getX(), t0.getY() * self._ka)
        self._q = sqrt(self._r**2 + self._p**2)
        self._s0 = self._q * a0
        dp0 = self._dtyp(r * cos(a0 * self._ka),
                         r * sin(a0 * self._ka),
                         self._p * a0)
        self._pc = p0 - dp0


    def param (self, s):

        return (self._s0 + s) / self._q


    def deriv1 (self, a):

        d1 = self._dtyp(-self._r * sin(a * self._ka) * self._ka,
                        self._r * cos(a * self._ka) * self._ka,
                        self._p)
        return d1


    def deriv2 (self, a):

        d2 = self._dtyp(-self._r * cos(a * self._ka) * self._ka**2,
                        -self._r * sin(a * self._ka) * self._ka**2,
                        0.0)
        return d2


    def length (self):

        return self._q * self._a


    def point (self, s):

        a = self.param(s)
        dp = self._dtyp(self._r * cos(a * self._ka),
                        self._r * sin(a * self._ka),
                        self._p * a)
        p = self._pc + dp
        return p


    def radius (self, s):

        r = self._q**2 / self._r
        return r


class ArcedHelixZ (Curve):

    def __init__ (self, r, a, rp, p0, t0):

        self._dtyp = type(p0)
        self._r = abs(r)
        self._a = abs(a)
        self._ka = sign(a)
        self._rp = rp
        self._p = r * (t0.getZ() / t0.getXy().length())
        self._a0 = atan2(-t0.getX(), t0.getY() * self._ka)
        self._q = sqrt(self._r**2 + self._p**2)
        self._z0 = self._p * self._a0
        dp0 = self._dtyp(r * cos(self._a0),
                         r * sin(self._a0) * self._ka,
                         0.0)
        self._pc = p0 - dp0
        self._b0 = atan2(t0.getZ(), t0.getXy().length())
        self._sb0 = sin(self._b0)
        self._cb0 = cos(self._b0)


    def param (self, s):

        a = (  (self._rp / self._r)
             * (sin(s / self._rp + self._b0) - self._sb0))
        return a


    def deriv1 (self, a):

        sb = (self._r / self._rp) * a + self._sb0
        ka = self._ka
        d1 = self._dtyp(-self._r * sin((self._a0 + a) * ka) * ka,
                        self._r * cos((self._a0 + a) * ka) * ka,
                        self._r * sb / sqrt(1.0 - sb**2))
        return d1


    def deriv2 (self, a):

        sb = (self._r / self._rp) * a + self._sb0
        ka = self._ka
        d2 = self._dtyp(-self._r * cos((self._a0 + a) * ka) * ka**2,
                        -self._r * sin((self._a0 + a) * ka) * ka**2,
                        (self._r**2 / self._rp) / (1 - sb**2)**1.5)
        return d2


    def length (self):

        sb = (self._r / self._rp) * self._a + self._sb0
        return abs(self._rp * (asin(sb) - self._b0))


    def point (self, s):

        a = self.param(s)
        sb = (self._r / self._rp) * a + self._sb0
        dp = self._dtyp(self._r * cos((self._a0 + a) * self._ka),
                        self._r * sin((self._a0 + a) * self._ka),
                        self._rp * (self._cb0 - sqrt(1.0 - sb**2)))
        p = self._pc + dp
        return p


class Bezier3 (Curve):

    def __init__ (self, p0, p1, p2, p3, amax=0.1, dt0=0.1):

        self._dtyp = type(p0)

        self._p0 = p0
        self._p1 = p1
        self._p2 = p2
        self._p3 = p3

        self._calc_base()
        self._sample(amax, dt0)


    def _calc_base (self):

        # Prepare calculation with Taylor series around t=0.0.
        self._c0 = self._p0
        self._c1 = self._p1 * 3 - self._p0 * 3
        self._c2 = self._p0 * 6 - self._p1 * 12 + self._p2 * 6
        self._c3 = - self._p0 * 6 + self._p1 * 18 - self._p2 * 18 + self._p3 * 6


    def set_tlen (self, tlen1, tlen2):

        if tlen1 is not None:
            tdir = self._p1 - self._p0
            tdir.normalize()
            self._p1 = self._p0 + tdir * tlen
        if tlen2 is not None:
            tdir = self._p3 - self._p2
            tdir.normalize()
            self._p2 = self._p3 - tdir * tlen
        self._calc_base()
        self._sample(self._amax, self._dt0)


    def xpoint (self, t):

        p = (  self._c0 + self._c1 * t + self._c2 * (t**2 / 2)
             + self._c3 * (t**3 / 6))
        return p


    def deriv1 (self, t):

        d1 = self._c1 + self._c2 * t + self._c3 * (t**2 / 2)
        return d1


    def deriv2 (self, t):

        d2 = self._c2 + self._c3 * t
        return d2


    def _sample_at (self, t):

        p = self.xpoint(t)
        d1 = self.deriv1(t)
        d2 = self.deriv2(t)
        l = self._dtyp(d1)
        l.normalize()
        n = d2 * d1.dot(d1) - d1 * d1.dot(d2)
        k = d1.cross(d2).length() / d1.length()**3
        r = 1.0 / k if k > 0.0 else INF_RADIUS
        return p, l, n, r


    def _sample (self, amax=0.1, dt0=0.1):

        neval = 0
        rmin = INF_RADIUS; rmax = -INF_RADIUS
        s = 0.0; t = 0.0; tp = None
        ts = []; cs = []; pts = []; tangs = []; norms = []; rads = []
        while True:
            if tp is not None:
                dt = dtp * 1.2
                if tp + dt > 1.0:
                    dt = 1.0 - tp
                while True:
                    t = tp + dt
                    p, l, n, r = self._sample_at(t)
                    neval += 1
                    ds = (p - pp).length()
                    #rm = 0.5 * (r + rp)
                    #a = ds / rm
                    a = ds / r
                    if a <= amax:
                        break
                    dt *= 0.5
            else:
                p, l, n, r = self._sample_at(t)
                neval += 1
                rm = r
                dt = dt0
                ds = 0.0
                a = 0.0
            s += ds
            if rmin > r:
                rmin = r
            if rmax < r:
                rmax = r
            ts.append(t)
            cs.append(s)
            pts.append(p)
            tangs.append(l)
            norms.append(n)
            rads.append(r)
            #print ("t=%.4f  s=%.4e  r=%.4e  a=%.2f"
                   #% (t, s, r, degrees(a)))
            if t >= 1.0:
                break
            pp = p
            rp = r
            tp = t
            dtp = dt
        nseg = len(ts) - 1
        clen = cs[-1]
        #print ("neval=%d  nseg=%d  len=%.4e  rmin=%.4e"
               #% (neval, nseg, clen, rmin))
        # Add end points to be exactly tangent when out of range.
        p0, l0, n0, r0 = self._sample_at(0.0)
        cs.insert(0, -clen)
        ts.insert(0, -1.0)
        pts.insert(0, p0 - l0 * clen)
        tangs.insert(0, l0)
        norms.insert(0, n0)
        rads.insert(0, INF_RADIUS)
        p1, l1, n1, r1 = self._sample_at(1.0)
        cs.append(clen + clen)
        ts.append(2.0)
        pts.append(p1 + l1 * clen)
        tangs.append(l1)
        norms.append(n1)
        rads.append(INF_RADIUS)

        self._smp_amax = amax
        self._smp_dt0 = dt0
        self._smp_neval = neval
        self._smp_nseg = nseg
        self._smp_clen = clen
        self._smp_rmin = rmin
        self._smp_rmax = rmax
        self._smp_tab_s_t = Table1(cs, ts)
        self._smp_tab_s_p = Table1(cs, pts)
        self._smp_tab_s_l = Table1(cs, tangs)
        self._smp_tab_s_n = Table1(cs, norms)
        self._smp_tab_s_r = Table1(cs, rads)

        return neval, nseg, clen, rmin, rmax


    def point (self, s):

        return self._smp_tab_s_p(s)


    def tangent (self, s):

        l = self._smp_tab_s_l(s)
        l.normalize()
        return l


    def normal (self, s):

        n = self._smp_tab_s_n(s)
        n.normalize()
        return n


    def radius (self, s):

        return self._smp_tab_s_r(s)


    def length (self):

        return self._smp_clen


    def minrad (self):

        return self._smp_rmin


    def maxrad (self):

        return self._smp_rmax


