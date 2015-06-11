# -*- coding: UTF-8 -*-

from math import degrees, radians, pi, sin, cos, asin, acos, tan, atan, atan2
from math import sqrt, log, exp
from time import time

from pandac.PandaModules import Vec3D, Point3D, QuatD

from src import join_path, internal_path
from src.core.curve import ArcedHelixZ
from src.core.misc import sign, clamp, unitv, vtod, norm_ang_delta
from src.core.misc import int1r0, intl01v, intl01r, intl01vr
from src.core.misc import intc01, intc10, intc10r, intc01vr
from src.core.misc import AutoProps, SimpleProps, intercept_time, solve_quad
from src.core.misc import get_cache_key_section
from src.core.misc import read_cache_object, write_cache_object
from src.core.misc import uniform, randvec
from src.core.misc import debug, dbgval
from src.core.table import Table2, Table3


fudge = AutoProps(
    sfcabzfac=0.5,
)

AIRBRAKE = SimpleProps(
    RETRACTED=0.0,
    EXTENDED=1.0,
)

FLAPS = SimpleProps(
    RETRACTED=0,
    LANDING=1,
    TAKEOFF=2,
)

GROUND = SimpleProps(
    RUNWAY=0,
    DIRT=1,
    GRASS=2,
    ICE=5,
    WATER=10,
)
GROUND._data = {
    GROUND.RUNWAY: (0.030, 0.400, 1.0),
    GROUND.DIRT: (0.050, 0.300, 4.0),
    GROUND.GRASS: (0.060, 0.200, 4.0),
    GROUND.ICE: (0.030, 0.100, 2.0),
    GROUND.WATER: (0.0, 0.0, 0.0),
}


class PlaneDynamics (object):

# @cache-key-start: plane-dynamics

    def __init__ (self, name,
                  g0, htrop, hstrat,
                  gam, rhoz, rhoefac, prz, prefac, vsndz, vsndfacht,
                  mmin, mmax, mref, nmaxref,
                  s, ar, e, a0z, amaxz,
                  tmaxz, tmaxabz, tincab,
                  vmaxz, vmaxabz, crmaxz, voptcz,
                  vmaxh, vmaxabh,
                  pomaxz, romaxz,
                  mfmax, sfcz, sfcabz, cincab,
                  rsd0br,
                  da0fl1, damaxfl1, rsd0fl1,
                  da0fl2, damaxfl2, rsd0fl2,
                  lgny, lgnz, lgmx, lgmy, lgmz,
                  rmugbr, rsd0lg,
                  rep=False, envtab=False):

        self.name = name

        ff = self
        ff.rep = rep
        ff.envtab = envtab

        if tmaxabz:
            hasab = True
        else:
            tmaxabz = tmaxz
            tincab = 1.0
            cincab = 1.0
            vmaxabz = vmaxz
            vmaxabh = vmaxh
            sfcabz = sfcz
            hasab = False

        ad = AutoProps(
            g0=g0,
            htrop=htrop, hstrat=hstrat,
            gam=gam, rhoz=rhoz, rhoefac=rhoefac,
            prz=prz, prefac=prefac,
            vsndz=vsndz, vsndfacht=vsndfacht,
        )

        pd = AutoProps(
            mmin=mmin, mmax=mmax, mref=mref, nmaxref=nmaxref,
            s=s, ar=ar, e=e, a0z=a0z, amaxz=amaxz,
            tmaxz=tmaxz, tmaxabz=tmaxabz, tincab=tincab,
            vmaxz=vmaxz, vmaxabz=vmaxabz, crmaxz=crmaxz, voptcz=voptcz,
            vmaxh=vmaxh, vmaxabh=vmaxabh,
            pomaxz=pomaxz, romaxz=romaxz,
            mfmax=mfmax, sfcz=sfcz, sfcabz=sfcabz, cincab=cincab,
            rsd0br=rsd0br,
            da0fl1=da0fl1, damaxfl1=damaxfl1, rsd0fl1=rsd0fl1,
            da0fl2=da0fl2, damaxfl2=damaxfl2, rsd0fl2=rsd0fl2,
            lgny=lgny, lgnz=lgnz, lgmx=lgmx, lgmy=lgmy, lgmz=lgmz,
            rmugbr=rmugbr, rsd0lg=rsd0lg,
            hasab=hasab,
        )

        for qn, qv in ad.props() + pd.props():
            setattr(self, qn, qv)

        this_path = internal_path("data", __file__)
        ckey = (sorted(ad.props()), sorted(pd.props()), sorted(fudge.props()),
                get_cache_key_section(this_path.replace(".pyc", ".py"),
                                     "plane-dynamics"))

        ddcpath = join_path("pldyn", self.name, "basedat.pkl")
        dd = read_cache_object(ddcpath, ckey)
        if dd is None:
            dd = self._derive()
            write_cache_object(dd, ddcpath, ckey)
        else:
            for qn, qv in dd.props():
                setattr(self, qn, qv)

        if ff.envtab:
            tdcpath = join_path("pldyn", self.name, "tab.pkl")
            td = read_cache_object(tdcpath, ckey)
            if td is None:
                td = self._derive_envtab()
                write_cache_object(td, tdcpath, ckey)
            else:
                for qn, qv in td.props():
                    setattr(self, "tab_%s" % qn, qv)


    def _derive (self):

        ff, ad, pd = self, self, self

        rep = ff.rep

        if rep:
            debug(1, "type: name=%s" % self.name)

        t1 = time()

        dd = AutoProps()
        dd.set_silent(False)

        gam = ad.gam
        kgam = gam / (gam - 1.0)
        ad.kgam = kgam
        dd.kgam = kgam

        a0z, amaxz, s, ar, e = pd.a0z, pd.amaxz, pd.s, pd.ar, pd.e

        a1z = a0z + 0.9 * (amaxz - a0z) * (ar / 8.0)**0.5
        claz = (2 * pi) * ((0.5 * ar) / (1.0 + (1.0 + (0.5 * ar)**2)**0.5))
        slaz = claz * s
        sla1z = slaz * 0.25
        ks = (1.0 / (pi * ar * e)) / s
        pd.a1z, pd.slaz, pd.sla1z, pd.ks = a1z, slaz, sla1z, ks
        dd.a1z, dd.slaz, dd.sla1z, dd.ks = a1z, slaz, sla1z, ks

        ret = ff.derive_at_alt(rid="hgnd", h=0.0,
                               vmax=pd.vmaxz, vmaxab=pd.vmaxabz,
                               crmax=pd.crmaxz, voptc=pd.voptcz, rvoptc=None,
                               rsdcr=None)
        (pd.sd0crz, pd.sd0spz, pd.sd0spabz,
         pd.vminz, pd.vminabz, pd.vmaxz, pd.vmaxabz, pd.voptcz,
         pd.vminfl1z, pd.vminfl1abz, pd.vminfl2z, pd.vminfl2abz) = ret
        (dd.sd0crz, dd.sd0spz, dd.sd0spabz,
         dd.vminz, dd.vminabz, dd.vmaxz, dd.vmaxabz, dd.voptcz,
         dd.vminfl1z, dd.vminfl1abz, dd.vminfl2z, dd.vminfl2abz) = ret

        rvoptcz = (pd.voptcz - pd.vminz) / (pd.vmaxz - pd.vminz)
        rsdcrz = pd.sd0crz / pd.sd0spz
        ret = ff.derive_at_alt(rid="hspd", h=ad.htrop,
                               vmax=pd.vmaxh, vmaxab=pd.vmaxabh,
                               crmax=None, voptc=None, rvoptc=rvoptcz,
                               rsdcr=rsdcrz)
        (pd.sd0crh, pd.sd0sph, pd.sd0spabh,
         pd.vminh, pd.vminabh, pd.vmaxh, pd.vmaxabh, pd.voptch,
         pd.vminfl1h, pd.vminfl1abh, pd.vminfl2h, pd.vminfl2abh) = ret
        (dd.sd0crh, dd.sd0sph, dd.sd0spabh,
         dd.vminh, dd.vminabh, dd.vmaxh, dd.vmaxabh, dd.voptch,
         dd.vminfl1h, dd.vminfl1abh, dd.vminfl2h, dd.vminfl2abh) = ret

        ret = ff.derive_at_range()
        pd.rmax, pd.hrmax = ret
        dd.rmax, dd.hrmax = ret

        ret = ff.derive_for_roll()
        (pd.vzerorz, pd.vlinrz, pd.vmaxrz, pd.vzerorh, pd.vlinrh, pd.vmaxrh,
         pd.rfacmaxa, pd.rfacmaxm, pd.psmaxz, pd.rsmaxz) = ret
        (dd.vzerorz, dd.vlinrz, dd.vmaxrz, dd.vzerorh, dd.vlinrh, dd.vmaxrh,
         dd.rfacmaxa, dd.rfacmaxm, dd.psmaxz, dd.rsmaxz) = ret

        ret = ff.derive_lgear()
        pd.lghn, pd.lghvt = ret
        dd.lghn, dd.lghvt = ret

        t2 = time()
        if rep:
            debug(1, "basedat-comp: tm=%.1f[ms]" % ((t2 - t1) * 1e3))

        return dd


    def _derive_envtab (self):

        ff, ad, pd = self, self, self

        rep = ff.rep

        mmin, mmax = pd.mmin, pd.mmax
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz

        ms = []
        m0 = mmin; m1 = mmax; nm01 = 5
        dm01 = (m1 - m0) / nm01
        ms += [m0 + i * dm01 for i in xrange(nm01)]
        ms += [m1]
        if rep:
            debug(1, "tab: m=(%s)[kg]" % (", ".join("%.0f" % m for m in ms)))

        hs = []
        h0 = 0.0
        h1 = 10000.0; nh01 = 5
        dh01 = (h1 - h0) / nh01
        hs += [h0 + i * dh01 for i in xrange(nh01)]
        h2 = 30000.0; nh12 = 20
        dh12 = (h2 - h1) / nh12
        hs += [h1 + i * dh12 for i in xrange(nh12)]
        hs += [h2]
        if rep:
            debug(1, "tab: h=(%s)[m]" % (", ".join("%.0f" % h for h in hs)))

        tlmaxs = []
        tlmaxs += [1.0]
        if tmaxabz > tmaxz:
            tlmaxs += [2.0]
        if rep:
            debug(1, "tab: tlmax=(%s)" %
                  (", ".join("%.1f" % tl for tl in tlmaxs)))

        dv = 2.0
        if rep:
            debug(1, "tab: dv=%.1f[m/s]" % dv)

        # NOTE: Quantity set and ordering must be as returned by comp_env.
        envqns_mh = ["vmin", "vmax", "crmax", "voptc",
                     "trimax", "trsmax", "voptti", "voptts",
                     "rfmax", "voptrf", "tloptrf"]
        envqns_mhv = ["crmaxv", "trimaxv", "trsmaxv", "rfmaxv",
                      "ctmaxv", "tlvlv", "tmaxv", "sfcv",
                      "vias"] # "v" split out
        td = AutoProps()
        td.set_silent(False)
        td.update((qn, []) for qn in envqns_mh + envqns_mhv)
        td.all_mh = []
        td.all_mhv = []
        t1 = time()
        for tlmax in tlmaxs:
            hrs = []
            envqs_mh = []
            vs = []
            envqs_mhv = []
            for m in ms:
                hrs1 = []
                envqs1_mh = []
                vs1 = []
                envqs1_mhv = []
                for h in hs:
                    ret = ff.comp_env(m=m, h=h, tlmax=tlmax, dv=dv,
                                      withqv=True, rep=False)
                    envq, envqv = ret
                    if envq[0] is None:
                        break
                    hrs1.append(h)
                    envqs1_mh.append(envq)
                    vs1.append(envqv[0])
                    envqs1_mhv.append(zip(*envqv[1:]))
                hrs.append(hrs1)
                envqs_mh.append(envqs1_mh)
                vs.append(vs1)
                envqs_mhv.append(envqs1_mhv)
                if rep:
                    debug(1, "ceil: "
                          "tlmax=%4.2f  m=%6.0f[kg]  hmax=%6.0f[m]" %
                          (tlmax, m, hrs1[-1]))
            envqs_mh_t = zip(*map(lambda x:
                                  zip(*x), envqs_mh))
            for iq, qn in enumerate(envqns_mh):
                tab = Table2(ms, hrs, envqs_mh_t[iq], name=qn)
                td[qn].append(tab)
            tab = Table2(ms, hrs, envqs_mh, name="all_mh")
            td.all_mh.append(tab)
            envqs_mhv_t = zip(*map(lambda x:
                                   zip(*map(lambda y:
                                            zip(*y), x)), envqs_mhv))
            for iq, qn in enumerate(envqns_mhv):
                tab = Table3(ms, hrs, vs, envqs_mhv_t[iq], name=qn)
                td[qn].append(tab)
            tab = Table3(ms, hrs, vs, envqs_mhv, name="all_mhv")
            td.all_mhv.append(tab)

        t2 = time()
        if rep:
            debug(1, "envdat-comp: tm=%.1f[ms]" % ((t2 - t1) * 1e3))

        for qn, qv in td.props():
            setattr(pd, "tab_%s" % qn, qv)

        return td


    def resatm (self, h):

        ad = self

        g0 = ad.g0
        htrop = ad.htrop
        rhoz, rhoefac = ad.rhoz, ad.rhoefac
        prz, prefac = ad.prz, ad.prefac
        vsndz, vsndfacht = ad.vsndz, ad.vsndfacht

        g = g0

        rhofac = exp(rhoefac * h)
        rho = rhoz * rhofac

        prfac = exp(prefac * h)
        pr = prz * prfac

        if h < htrop:
            vsndfac = 1.0 + (vsndfacht - 1.0) * (h / htrop)
        else:
            vsndfac = vsndfacht
        vsnd = vsndz * vsndfac

        return g, rho, rhofac, pr, prfac, vsnd


    def reslifta (self, amin, a1m, a0, a1, amax, sla, sla1, a, q):

        if a1m <= a <= a1:
            sl = sla * (a - a0)
        elif a1 < a <= amax:
            sl = sla * (a1 - a0) + sla1 * (a - a1)
        elif a > amax:
            sl = None
        elif amin <= a < a1m:
            sl = sla * (a1m - a0) + sla1 * (a - a1m)
        elif a < amin:
            sl = None
        if sl is not None:
            l = sl * q
        else:
            l = None
        return sl, l


    def resliftafp (self, amin, a1m, a0, a1, amax, sla, sla1, a, q):

        if a1m <= a <= a1:
            sl = sla * (a - a0)
            slcdi = sl
        elif a1 < a <= amax:
            sl = sla * (a1 - a0) + sla1 * (a - a1)
            slcdi = sl
        elif a > amax:
            slcdi = sla * (a1 - a0) + sla1 * (a - a1)
            a0st = 2 * amax - a0
            if a < a0st:
                slmax = sla * (a1 - a0) + sla1 * (amax - a1)
                sl = slmax * (1.0 - (a - amax) / (a0st - amax))
            else:
                sl = 0.0
        elif amin <= a < a1m:
            sl = sla * (a1m - a0) + sla1 * (a - a1m)
            slcdi = sl
        elif a < amin:
            slcdi = sla * (a1m - a0) + sla1 * (a - a1m)
            a0mst = 2 * amin - a0
            if a > a0mst:
                slmin = sla * (a1m - a0) + sla1 * (amin - a1m)
                sl = slmin * (1.0 - (a - amin) / (a0mst - amin))
            else:
                sl = 0.0
        l = sl * q
        return sl, l, slcdi


    def resliftwt (self, amin, a1m, a0, a1, amax, sla, sla1, q, t, w,
                   ext=False):
        # Solve:
        #   l(a) + t * sin(a) - w = 0.0
        # for a.
        # Assume: sin(a) ~ a.
        a = (w + q * sla * a0) / (q * sla + t)
        if a1m <= a <= a1:
            sl = sla * (a - a0)
        elif a > a1:
            a = (w - q * sla * (a1 - a0) + q * sla1 * a1) / (q * sla1 + t)
            if a <= amax or ext:
                sl = sla * (a1 - a0) + sla1 * (a - a1)
            else:
                a = None
                sl = None
        elif a < a1m:
            a = (w - q * sla * (a1m - a0) + q * sla1 * a1m) / (q * sla1 + t)
            if a >= amin or ext:
                sl = sla * (a1m - a0) + sla1 * (a - a1m)
            else:
                a = None
                sl = None
        if sl is not None:
            l = sl * q
        else:
            l = None
        return a, sl, l


    def resdragwt (self, amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                   t, wt, ft, ext=False):
        # Solve:
        #   t * cos(a) - d(a) + wt = ft
        # for a.
        # assume: sin(a) ~ a, cos(a) ~ 1 - 0.5 * a^2
        k2 = -0.5 * t - q * ks * sla**2
        k1 = 2 * q * ks * sla**2 * a0
        k0 = t - q * sd0 - q * ks * sla**2 * a0**2 - (ft - wt)
        d = k1**2 - 4 * k2 * k0
        if d >= 0.0:
            a = (-k1 - d**0.5) / (2 * k2)
            if a1m <= a <= a1:
                sl = sla * (a - a0)
            elif a > a1:
                k2 = -0.5 * t - q * ks * sla1**2
                k1 = -2 * q * ks * (sla * sla1 * (a1 - a0) - sla1**2 * a1)
                k0 = (t - q * sd0 -
                      q * ks * (sla**2 * (a1 - a0)**2 -
                                2 * sla * sla1 * a1 * (a1 - a0) +
                                sla1**2 * a1**2) -
                      (ft - wt))
                d = k1**2 - 4 * k2 * k0
                if d >= 0.0:
                    a = (-k1 - d**0.5) / (2 * k2)
                    if a <= amax or ext:
                        sl = sla * (a1 - a0) + sla1 * (a - a1)
                    else:
                        a = None
                else:
                    a = None
            elif a < a1m:
                k2 = -0.5 * t - q * ks * sla1**2
                k1 = -2 * q * ks * (sla * sla1 * (a1m - a0) - sla1**2 * a1m)
                k0 = (t - q * sd0 -
                      q * ks * (sla**2 * (a1m - a0)**2 -
                                2 * sla * sla1 * a1m * (a1m - a0) +
                                sla1**2 * a1m**2) -
                      (ft - wt))
                d = k1**2 - 4 * k2 * k0
                if d >= 0.0:
                    a = (-k1 - d**0.5) / (2 * k2)
                    if a >= amin or ext:
                        sl = sla * (a1m - a0) + sla1 * (a - a1m)
                    else:
                        a = None
                else:
                    a = None
        else:
            a = None
        if a is not None:
            sd = sd0 + ks * sl**2
            d = sd * q
            l = sl * q
        else:
            sd = None
            d = None
            sl = None
            l = None
        return a, sd, d, sl, l


    def ressla (self, a0z, a1z, amaxz, slaz, sla1z, ma):

        ma1 = 0.85
        ma2 = 1.05
        if ma < ma1:
            ksla = 1.0 / (1.0 - ma**2)**0.5
            kamax = (1.0 - ma**2)**0.5
        elif ma < ma2:
            ksla1 = 1.0 / (1.0 - ma1**2)**0.5
            ksla = ksla1
            kamax1 = (1.0 - ma1**2)**0.5
            kamax = kamax1
        else:
            ksla1 = 1.0 / (1.0 - ma1**2)**0.5
            ksla2 = ksla1
            ksla = (ksla2 * (ma2**2 - 1.)**0.5) / (ma**2 - 1.)**0.5
            kamax1 = (1.0 - ma1**2)**0.5
            kamax2 = kamax1
            kamax = (kamax2 * (ma2**2 - 1.)**0.1) / (ma**2 - 1.)**0.1
        a0 = a0z
        a1 = a0z + kamax * (a1z - a0z)
        amax = a0z + kamax * (amaxz - a0)
        sla = slaz * ksla
        sla1 = sla1z * ksla
        fam = 0.5
        a1m = a0 - (a1 - a0) * fam
        amin = a1m - (amax - a1) * fam
        return amin, a1m, a0, a1, amax, sla, sla1


    def restmaxh (self, tmaxz, tmaxabz, h, rho, vsnd):

        ad = self
        htrop, rhoz, vsndz = ad.htrop, ad.rhoz, ad.vsndz
        #thcf = (rho / rhoz) * (vsnd / vsndz)
        thcf = rho / rhoz
        tmax1 = tmaxz * thcf
        tmaxab1 = tmaxabz * thcf
        return tmax1, tmaxab1


    def restmaxv (self, h, vsnd, vmax, vmaxab, tmax1, tmaxab1, v):

        # NOTE: Increases with v must have exponents smaller than 2,
        # to prevent v greater than vmax (as drag ~ v^2).

        ad, pd = self, self

        rh = h / ad.htrop
        rht = 1.0
        rhs = ad.hstrat / ad.htrop
        ma = v / vsnd
        mamax = max(vmax / vsnd, 1.2)
        mamaxab = max(vmaxab / vsnd, 2.0)

        rmatht = 1.2
        rmaths = 0.9
        rmat = intl01vr(rh, rht, rhs, rmatht, rmaths)
        ma1 = 0.7
        tmax1max = tmax1 * (1.0 + rmat * (mamax - ma1))
        tmax = intl01vr(ma, ma1, mamax, tmax1, tmax1max)
        #debug(1, "restmaxv10 %s %s %s %s %s" % (ma, rmat, tmax1, tmax1max, tmax))

        rmathtab = pd.tincab
        rmathsab = 1.2
        rmatab = intl01vr(rh, rht, rhs, rmathtab, rmathsab)
        ma1ab = 0.7
        tmaxab1max = tmaxab1 * (1.0 + rmatab * (mamaxab - ma1ab))
        tmaxab = intl01vr(ma, ma1ab, mamaxab, tmaxab1, tmaxab1max)
        #debug(1, "restmaxv20 %s %s %s %s %s" % (ma, rmatab, tmaxab1, tmaxab1max, tmaxab))

        return tmax, tmaxab


    def ressfc (self, h, vsnd, vmax, vmaxab, sfcz, sfcabz, v, tl):

        ad, pd = self, self

        htrop, hstrat = ad.htrop, ad.hstrat

        rh = h / ad.htrop
        rht = 1.0
        rhs = ad.hstrat / ad.htrop
        ma = v / vsnd
        mamax = max(vmax / vsnd, 1.2)
        mamaxab = max(vmaxab / vsnd, 2.0)

        cinch = 0.85
        cinch2 = 1.0
        if rh < 1.0:
            fsfch = intl01vr(rh, 0.0, rht, 1.0, cinch)
        else:
            fsfch = intl01vr(rh, rht, rhs, cinch, cinch2)
        cincma = 1.6
        fsfcma = intl01vr(ma, 0.0, mamax, 1.0, cincma)

        cincabh = 1.0
        cincabh2 = 1.05
        if rh < 1.0:
            fsfcabh = intl01vr(rh, 0.0, rht, 1.0, cincabh)
        else:
            fsfcabh = intl01vr(rh, rht, rhs, cincabh, cincabh2)
        cincabma = pd.cincab
        fsfcabma = intl01vr(ma, 0.0, mamaxab, 1.0, cincabma)

        sfch = sfcz * fsfch * fsfcma
        sfcabh = sfcabz * fsfcabh * fsfcabma
        if pd.hasab:
            sfcabh *= fudge.sfcabzfac

        sfc = intl01vr(tl, 1.0, 2.0, sfch, sfcabh)
        fsfc = sfc / sfcz

        return sfc, fsfc


    def ressd0 (self, vsnd, vopt, vmax, vmaxab, sd0cr, sd0sp, sd0spab, v, ma):

        ma2 = max(vmax / vsnd + 0.05, 1.05)
        if v < vopt:
            sd0 = sd0cr
        elif v < vmax:
            sd0 = sd0cr + (sd0sp - sd0cr) * (v - vopt) / (vmax - vopt)
        elif ma < ma2:
            sd0 = sd0sp
        elif v < vmaxab:
            vma2 = ma2 * vsnd
            vfac = (v - vma2) / (vmaxab - vma2)
            sd0 = sd0sp + (sd0spab - sd0sp) * vfac**0.5
        else:
            sd0 = sd0spab
        return sd0,


    def reshvsd (self, h):

        ad, pd = self, self

        htrop = ad.htrop
        vmaxz, vmaxabz, voptcz = pd.vmaxz, pd.vmaxabz, pd.voptcz
        vmaxh, vmaxabh, voptch = pd.vmaxh, pd.vmaxabh, pd.voptch
        sd0crz, sd0spz, sd0spabz = pd.sd0crz, pd.sd0spz, pd.sd0spabz
        sd0crh, sd0sph, sd0spabh = pd.sd0crh, pd.sd0sph, pd.sd0spabh
        rsd0br, rsd0lg = pd.rsd0br, pd.rsd0lg
        rsd0fl1, rsd0fl2 = pd.rsd0fl1, pd.rsd0fl2

        rh = h / htrop
        if rh <= 1.0:
            ifac = 1.0 - rh
        else:
            ifac = 0.0

        vsd0cr = (voptch + (voptcz - voptch) * ifac)
        vsd0sp = (vmaxh + (vmaxz - vmaxh) * ifac)
        vsd0spab = (vmaxabh + (vmaxabz - vmaxabh) * ifac)

        sd0cr = (sd0crh + (sd0crz - sd0crh) * ifac)
        sd0sp = (sd0sph + (sd0spz - sd0sph) * ifac)
        sd0spab = (sd0spabh + (sd0spabz - sd0spabh) * ifac)

        dsd0br = sd0cr * rsd0br
        dsd0lg = sd0cr * rsd0lg

        return (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
                dsd0br, dsd0lg)


    def resthtl (self, tl, tmax, tmaxab):

        if tl < 0.0:
            t = None
        elif tl <= 1.0:
            t = tl * tmax
        elif tl <= 2.0:
            t = tmax + (tl - 1.0) * (tmaxab - tmax)
        else:
            t = None
        return t


    def restlth (self, t, tmax, tmaxab):

        if t < 0.0:
            tl = None
        elif t <= tmax:
            tl = t / tmax
        elif t <= tmaxab:
            tl = (t - tmax) / (tmaxab - tmax) + 1.0
        else:
            tl = None
        return tl


    def resctmax (self, tmax, m, a, t):

        ctmax = (tmax - t) / m * cos(a)
        return ctmax


    def resslafl (self, fld, a0, a1, amax):

        pd = self
        if fld == FLAPS.RETRACTED:
            da0fl, damaxfl = 0.0, 0.0
        elif fld == FLAPS.LANDING:
            da0fl, damaxfl = pd.da0fl1, pd.damaxfl1
        elif fld == FLAPS.TAKEOFF:
            da0fl, damaxfl = pd.da0fl2, pd.damaxfl2
        a0fl = a0 + da0fl
        amaxfl = amax + damaxfl
        a1fl = a1 + damaxfl
        return a0fl, a1fl, amaxfl


    def ressd0fl (self, fld, sd0cr, sd0):

        pd = self
        if fld == FLAPS.RETRACTED:
            rsd0fl = 0.0
        elif fld == FLAPS.LANDING:
            rsd0fl = pd.rsd0fl1
        elif fld == FLAPS.TAKEOFF:
            rsd0fl = pd.rsd0fl2
        sd0fl = sd0 + sd0cr * rsd0fl
        return sd0fl


    def derive_at_alt (self, rid, h, vmax, vmaxab,
                       crmax, voptc, rvoptc, rsdcr):

        ff, ad, pd = self, self, self

        if (True
            and not (    crmax is not None and voptc is not None
                    and rvoptc is None and rsdcr is None)
            and not (    crmax is None and voptc is None
                    and rvoptc is not None and rsdcr is not None)
        ):
            raise StandardError(
                "Incompatible maximum climb rate specifications given.")

        rep = ff.rep

        mref = pd.mref
        s, ar, e = pd.s, pd.ar, pd.e
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        ks = pd.ks
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz

        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)

        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)

        def derive_at_vmax (withab):
            v = vmaxab if withab else vmax
            q = 0.5 * rho * v**2
            w = mref * g
            tht = radians(0.0)
            ma = v / vsnd
            amin, a1m, a0, a1, amax, sla, sla1 = (
                ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
            tmax, tmaxab = ff.restmaxv(h, vsnd, vmax, vmaxab, tmax1, tmaxab1, v)
            t = (tmaxab if withab else tmax) * 1.0
            a, sl, l = ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q, t, w)
            ca = 1.0 - 0.5 * a**2 # ~ cos(a)
            sdi = ks * sl**2
            sd0 = (t * ca - w * sin(tht)) / q - sdi
            sd = sd0 + sdi
            if rep:
                debug(1, "%s-vmax%s: "
                      "a=%.2f[deg]  cla=%.3f[1/deg]  cl=%.4f  "
                      "cd0=%.4f  cdi=%.4f  cd=%.4f  "
                      "v=%.1f[m/s]  ma=%.2f  t/tmaxz=%.2f  t/w=%.2f" %
                      (rid, ("ab" if withab else ""),
                       degrees(a), radians(sla / s), sl / s,
                       sd0 / s, sdi / s, sd / s,
                       v, ma, t / tmaxz, t / w))
            return sd0,
        sd0sp, = derive_at_vmax(withab=False)
        sd0spab, = derive_at_vmax(withab=True)

        if crmax is not None:
            def derive_at_voptc ():
                v = voptc
                q = 0.5 * rho * v**2
                w = mref * g
                ma = v / vsnd
                cr = crmax
                tht = asin(cr / v)
                amin, a1m, a0, a1, amax, sla, sla1 = (
                    ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
                tmax, tmaxab = ff.restmaxv(h, vsnd, vmax, vmaxab, tmax1, tmaxab1, v)
                t = tmaxab * 1.0
                a, sl, l = (
                    ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q,
                                 t, w * cos(tht)))
                ca = 1.0 - 0.5 * a**2 # ~ cos(a)
                sdi = ks * sl**2
                sd0 = (t * ca - w * sin(tht)) / q - sdi
                sd = sd0 + sdi
                if rep:
                    debug(1, "%s-voptc: "
                          "a=%.2f[deg]  tht=%.1f[deg]  cla=%.3f[1/deg]  "
                          "cl=%.4f  cd0=%.4f  cdi=%.4f  cd=%.4f  "
                          "v=%.1f[m/s]  ma=%.2f  cr=%.1f[m/s]  "
                          "t/tmaxz=%.2f  t/w=%.2f" %
                          (rid, degrees(a), degrees(tht), radians(sla / s),
                           sl / s, sd0 / s, sdi / s, sd / s,
                           v, ma, cr, t / tmaxz, t / w))
                return sd0,
            sd0cr, = derive_at_voptc()
        else:
            sd0cr = sd0sp * rsdcr

        if not sd0cr < sd0sp:
            raise StandardError(
                "It must hold cd0cr < cd0sp (rid=%s, cd0cr=%.4f, cd0sp=%.4f)."
                % (rid, sd0cr / s, sd0sp / s))

        def derive_at_vmin (withab, flaps=0):
            nit = 0
            v = 0.0
            w = mref * g
            afl0z, afl1z, amaxflz = ff.resslafl(flaps, a0z, a1z, amaxz)
            while True:
                nit += 1
                vp = v
                ma = v / vsnd
                amin, a1m, a0, a1, amax, sla, sla1 = (
                    ff.ressla(afl0z, afl1z, amaxflz, slaz, sla1z, ma))
                dslmax = 0.01 * s # safety margin
                a = amax - dslmax / sla1
                q = 0.5 * rho * v**2
                sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
                sd0 = sd0cr
                sd0 = ff.ressd0fl(flaps, sd0cr, sd0)
                sdi = ks * sl**2
                sd = sd0 + sdi
                ta = a / (1.0 - 0.5 * a**2) # ~ tan(a)
                v = (w / (0.5 * rho * (sl + ta * sd)))**0.5
                if abs(v - vp) < 0.001 * vp:
                    v = vp
                    break
            tmax, tmaxab = ff.restmaxv(h, vsnd, vmax, vmaxab, tmax1, tmaxab1, v)
            tmaxref = (tmaxab if withab else tmax) * 0.99
            ca = 1.0 - 0.5 * a**2 # ~ cos(a)
            t = (q * sd) / ca
            nit2 = 0
            if t > tmaxref:
                tp = t
                while True:
                    nit2 += 1
                    vp = v
                    v *= (t / tmaxref)**0.5
                    if t > tp and v > vp:
                        if flaps > 0:
                            v = -1.0
                            break
                        else:
                            raise StandardError(
                                "Cannot find thrust-limited minimum speed at "
                                "h=%.0f[m], withab=%s, flaps=%d."
                                % (h, withab, flaps))
                    ma = v / vsnd
                    amin, a1m, a0, a1, amax, sla, sla1 = (
                        ff.ressla(afl0z, afl1z, amaxflz, slaz, sla1z, ma))
                    q = 0.5 * rho * v**2
                    tmax, tmaxab = ff.restmaxv(h, vsnd, vmax, vmaxab,
                                               tmax1, tmaxab1, v)
                    tmaxref = (tmaxab if withab else tmax) * 0.99
                    a, sl, l = (
                        ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q,
                                     tmaxref, w))
                    ca = 1.0 - 0.5 * a**2 # ~ cos(a)
                    sd0 = sd0cr
                    sd0 = ff.ressd0fl(flaps, sd0cr, sd0)
                    sdi = ks * sl**2
                    sd = sd0 + sdi
                    tp = t
                    t = (q * sd) / ca
                    if abs(t - tmaxref) < 0.001 * tmaxref:
                        t = tp
                        break
            if rep:
                eid = (("fl%d" % flaps if flaps else "") +
                       ("ab" if withab else ""))
                if v >= 0.0:
                    debug(1, "%s-vmin%s: "
                          "nit=%d/%d  a=%.2f[deg]  cla=%.3f[1/deg]  cl=%.4f  "
                          "cd0=%.4f  cdi=%.4f  cd=%.4f  "
                          "v=%.1f[m/s]  ma=%.2f  t/tmaxz=%.2f  t/w=%.2f" %
                          (rid, eid, nit, nit2,
                           degrees(a), radians(sla / s), sl / s,
                           sd0 / s, sdi / s, sd / s,
                           v, ma, t / tmaxz, t / w))
                else:
                    debug(1, "%s-vmin%s: no-solution" % (rid, eid))
            return v,
        vmin, = derive_at_vmin(withab=False)
        vminab, = derive_at_vmin(withab=True)
        vminfl1, = derive_at_vmin(withab=False, flaps=1)
        vminfl1ab, = derive_at_vmin(withab=True, flaps=1)
        vminfl2, = derive_at_vmin(withab=False, flaps=2)
        vminfl2ab, = derive_at_vmin(withab=True, flaps=2)

        if crmax is not None:
            pass
        else:
            voptc = vmin + rvoptc * (vmax - vmin)
            if rep:
                debug(1, "%s-voptc: v=%.1f[m/s]" % (rid, voptc))

        return (sd0cr, sd0sp, sd0spab, vmin, vminab, vmax, vmaxab, voptc,
                vminfl1, vminfl1ab, vminfl2, vminfl2ab)


    def rescr (self, amin, a1m, a0, a1, amax, sla, sla1, sd0, ks,
               v, q, w, t, eps=radians(0.001), ai=None):

        ff = self

        nit = 0
        a = clamp(ai, amin, amax) if ai is not None else a0
        found = True
        while True:
            nit += 1
            ap = a
            sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
            sd = sd0 + ks * sl**2
            cr = v * (t * (1.0 - 0.5 * a**2) - q * sd) / w
            if not -v <= cr <= v:
                # Stationary climb not possible, set for vertical climb.
                cr = min(v, max(-v, cr))
                t = ((cr / v) * w + q * sd) # / (1.0 - 0.5 * a**2)
            ctht = (1.0 - (cr / v)**2)**0.5
            a, sl, l = (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1,
                             q, t, w * ctht))
            if a is None:
                found = False
                break
            if abs(a - ap) < eps:
                a = ap
                break
        ret = (nit, cr, a)
        if not found:
            ret = (nit,) + (None,) * (len(ret) - 1)
        return ret


    def restrmax (self, amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q, mv,
                  w, ws, tmax, nmax):

        ff = self

        # Instantaneous turn rate.
        a, sl, l = (
            ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q, tmax, w * nmax))
        if a is None:
            a = amax
            sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
        sd = sd0 + ks * sl**2
        tsust = (q * sd) / (1.0 - 0.5 * a**2)
        t = min(tsust, tmax)
        cnsq = (l + t * a)**2 - w**2
        cnsq = max(cnsq, 0.0)
        tri = cnsq**0.5 / mv
        atri = a

        # Sustained turn rate.
        a, sd, d, sl, l = (
            ff.resdragwt(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                         tmax, -ws, 0.0))
        if a is None: # can happen if amax too low
            trs = tri
        else:
            t = tmax
            cnsq = (l + t * a)**2 - w**2
            cnsq = max(cnsq, 0.0)
            trs = cnsq**0.5 / mv
        if trs > tri: # can happen if nmax too low
            trs = tri

        return tri, trs


    def respathq (self, amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                  wt, wn, wb, ft, fn, tmax, tmaxab,
                  tmaxref=None, invert=False,
                  eps=radians(0.001), maxit=None,
                  bleedv=False, bleedr=False):
        # Solve:
        #   t * cos(a) - d(a) + wt = ft
        #   (l(a) + t * sin(a)) * sin(phi) + wn = fn
        #   (l(a) + t * sin(a)) * cos(phi) + wb = 0.0
        # for a, t, phi.
        # Assume: sin(a) ~ a, cos(a) ~ 1 - 0.5 * a^2.
        ff = self

        sginv = -1 if invert else 1
        phi = atan2((fn - wn) * sginv, wb * sginv)
        if abs(sin(phi)) > 0.5:
            wr = (fn - wn) / sin(phi)
        else:
            wr = wb / cos(phi)
        tmaxref = tmaxab if tmaxref is None else min(tmaxref, tmaxab)
        a = a0
        da = None
        t = tmax
        nit = 0
        found = False
        while True:
            nit += 1
            ap = a
            dap = da
            a, sl, l = (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q, t, wr,
                             ext=True))
            sd = sd0 + ks * sl**2
            d = q * sd
            t = (ft - wt + d) / (1.0 - 0.5 * a**2)
            da = a - ap
            #debug(1, "rpq %s %s %s %s" % (nit, a, abs(a - ap), abs(a - ap) < eps))
            if nit > 3 and abs(da) > abs(dap) * 0.9:
                break
            if abs(da) < eps:
                found = True
                break
            if maxit and nit >= maxit:
                break
        if bleedv and not 0.0 <= t <= tmaxref:
            t = clamp(t, 0.0, tmaxref)
        if bleedr and not amin <= a <= amax:
            a = clamp(a, amin, amax)
            sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
        if not (amin <= a <= amax) or not (0.0 <= t <= tmaxref):
            found = False
        if 0.0 <= t <= tmaxref:
            tl = ff.restlth(t, tmax, tmaxab)
        else:
            tl = None
        ret = (nit, a, sl, l, sd, d, tl, t, phi)
        if not found:
            ret = (nit,) + (None,) * (len(ret) - 1)
        return ret


    def respathqa (self, amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                   wta, wna, wba, ft, fn, tmax, tmaxab,
                   tmaxref=None, invert=False,
                   eps=radians(0.001), maxit=None,
                   bleedv=False, bleedr=False):
        # Solve:
        #   t + l(a) * sin(a) - d(a) * cos(a) + wta = ft * cos(a) + fn * sin(phi) * sin(a)
        #   l(a) * cos(a) + d(a) * sin(a) + wna = -ft * sin(a) + fn * sin(phi) * cos(a)
        #   wba = fn * cos(phi)
        # for a, t, phi.
        # Assume: sin(a) ~ a, cos(a) ~ 1 - 0.5 * a^2.
        ff = self

        sginv = -1 if invert else 1
        tmaxref = tmaxab if tmaxref is None else min(tmaxref, tmaxab)
        a = a0
        t = tmax
        l = 0.0
        d = sd0 * q
        nit = 0
        found = False
        while True:
            nit += 1
            ap = a
            sa = a
            ca = (1.0 - 0.5 * a**2)
            ta = sa / ca
            phi = atan2(((ft + d) * ta + l + wna / ca) * sginv, wba * sginv)
            if not invert and phi < 0.0:
                phi += pi
            elif invert and phi > 0.0:
                phi -= pi
            wr = fn * sin(phi) - wta * sa - wna * ca
            a, sl, l = (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q, t, wr,
                             ext=True))
            sd = sd0 + ks * sl**2
            d = q * sd
            t = (ft + d) * ca + (fn * sin(phi) - l) * sa - wta
            if bleedv:
                t = clamp(t, 0.0, tmaxref)
            if not (amin + (amin - a1m) < a < amax + (amax - a1) or bleedr):
                break
            if abs(a - ap) < eps:
                found = True
                break
            if maxit and nit >= maxit:
                break
            if nit > 20:
                exit(1)
        if bleedr and not (amin <= a <= amax):
            a = clamp(a, amin, amax)
            sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
        if not (amin <= a <= amax) or not (0.0 <= t <= tmaxref):
            found = False
        tl = ff.restlth(t, tmax, tmaxab)
        ret = (nit, a, sl, l, sd, d, tl, t, phi)
        if not found:
            ret = (nit,) + (None,) * (len(ret) - 1)
        return ret


    def resnmax (self, mref, nmaxref, m):

        nmax = nmaxref * (mref / m)**0.5
        nmin = -0.5 * nmax
        return nmin, nmax


    def comp_env (self, m, h, tlmax, dv, withqv=False, rep=None):

        ff, ad, pd = self, self, self

        if rep is None:
            rep = ff.rep

        htrop = ad.htrop

        mref, nmaxref = pd.mref, pd.nmaxref
        s, ar, e = pd.s, pd.ar, pd.e
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        ks = pd.ks
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        vminz, vminabz, vmaxz, vmaxabz = (
            pd.vminz, pd.vminabz, pd.vmaxz, pd.vmaxabz)
        vminh, vminabh, vmaxh, vmaxabh = (
            pd.vminh, pd.vminabh, pd.vmaxh, pd.vmaxabh)
        sfcz, sfcabz = pd.sfcz, pd.sfcabz

        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)

        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)

        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)

        nmin, nmax = ff.resnmax(mref, nmaxref, m)

        vstart = min(vminabz, vminabh)
        vend = max(vmaxabz, vmaxabh)
        v = int(vstart / dv) * dv
        (vmin, vmax, crmax, voptc, trimax, trsmax, voptti, voptts,
        rfmax, voptrf, tloptrf) = [None] * 11
        (vs, crs, tris, trss, rfs, ctmaxs,
         tmaxrefs, ts, sfctmrs, viass) = [[] for i in range(10)]
        fixed_trsmax = False
        w = m * g
        while True:
            ma = v / vsnd
            q = 0.5 * rho * v**2
            amin, a1m, a0, a1, amax, sla, sla1 = (
                ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
            sd0, = (
                ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                          sd0cr, sd0sp, sd0spab, v, ma))
            tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
            tmaxref = ff.resthtl(tlmax, tmax, tmaxab)
            # - balance of lift, drag and thrust in level flight
            for invert in (False, True):
                ret = ff.respathq(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                                  0.0, 0.0, w, 0.0, 0.0, tmax, tmaxab,
                                  invert=invert)
                nit1, a, sl, l, sd, d, tl, t, phi = ret
                if a is not None:
                    if l + t * a > 0.0 and t <= tmaxref:
                        break
                    else:
                        a = None
            if a is not None:
                vs.append(v)
                ts.append(t)
                if vmin is None or vmin > v:
                    vmin = v
                if vmax is None or vmax < v:
                    vmax = v
                vias = ff.resvias(h, pr, q)[1]
                viass.append(vias)
                # - powerplant performance
                tmaxrefs.append(tmaxref)
                sfctmr = ff.ressfc(h, vsnd, vsd0sp, vsd0spab, sfcz, sfcabz,
                                   v, tlmax)[0]
                sfctmrs.append(sfctmr)
                # - level acceleration
                ctmax = ff.resctmax(tmaxref, m, a, t)
                ctmaxs.append(ctmax)
                # - range factor
                sfc = ff.ressfc(h, vsnd, vsd0sp, vsd0spab, sfcz, sfcabz,
                                v, tl)[0]
                rf = (v * (sl / sd)) / (sfc / sfcz)
                if rfmax is None or rfmax < rf:
                    rfmax = rf
                    voptrf = v
                    tloptrf = tl
                rfs.append(rf)
                # - climb rate
                nit2, cr, a_cr = (
                    ff.rescr(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks,
                             v, q, w, tmaxref, ai=a0))
                crs.append(cr)
                if crmax is None or crmax < cr:
                    crmax = cr
                    voptc = v
                # - instantaneous and sustained turn rate
                mv = m * v
                tri, trs = (
                    ff.restrmax(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks,
                                q, mv, w, 0.0, tmaxref, nmax))
                tris.append(tri)
                trss.append(trs)
                if trimax < tri:
                    trimax = tri
                    voptti = v
                #if trsmax < trs:
                    #trsmax = trs
                    #voptts = v
                # NOTE: Maximum sustained turn rate should be at speed around
                # the point of departure from maximum instantaneous turn rate,
                # but due to engine modeling it can slip too far outward.
                # So, just fix it at point of departure.
                if not fixed_trsmax:
                    if trsmax < trs:
                        trsmax = trs
                        voptts = v
                    if tri > trs + radians(0.1):
                        fixed_trsmax = True
                if rep:
                    debug(1, "env-pt: nit=(%2d, %2d)  "
                          "v=%6.1f[m/s]  vias=%6.1f[m/s]  "
                          "cr=%6.1f[m/s]  tri=%6.2f[deg/s]  trs=%6.2f[deg/s]  "
                          "tl=%5.3f  tmaxref=%6.2f[kN]  sfctmr=%4.2f[kg/daN/h]  "
                          "rfm=%6.3f  ctmax=%6.2f[m/s^2]" %
                          (nit1, nit2, v, vias, cr,
                           degrees(tri), degrees(trs),
                           tl, tmaxref * 1e-3, sfctmr * 3.6e4,
                           rf / vsnd, ctmax))
            v += dv
            if v > vend:
                break
        envq = (vmin, vmax, crmax, voptc, trimax, trsmax, voptti, voptts,
                rfmax, voptrf, tloptrf)
        if not withqv:
            return envq
        else:
            envqv = (vs, crs, tris, trss, rfs, ctmaxs, tmaxrefs, ts, sfctmrs,
                     viass)
            return envq, envqv


    def derive_at_range (self):

        ff, ad, pd = self, self, self

        rep = ff.rep

        htrop = ad.htrop
        mmin, mmax = pd.mmin, pd.mmax
        mfmax = pd.mfmax
        sfcz, sfcabz = pd.sfcz, pd.sfcabz

        mbase = mmin + (mmax - mmin) * 0.05
        m1 = mbase + mfmax
        m2 = mbase + mfmax * 0.05

        dh = 500.0
        dv = 5.0
        h = 0.0
        rmax = 0.0
        #hrmaxout = htrop
        #hrmaxout = htrop + 2000.0
        hrmaxout = 1e30
        ndm = 5
        dm = (m2 - m1) / ndm
        while True:
            g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
            rmaxi = 0.0
            for im in xrange(ndm):
                m1i = m1 + im * dm
                m2i = m1 + (im + 1) * dm
                mri = 0.5 * (m1i + m2i)
                ret = ff.comp_env(mri, h, tlmax=2.0, dv=dv, rep=False)
                rfmaxi, voptrfi, tloptrfi = ret[8:11]
                if im == 0:
                    voptrf1i = voptrfi
                    tloptrf1i = tloptrfi
                if im == ndm - 1:
                    voptrf2i = voptrfi
                    tloptrf2i = tloptrfi
                if rfmaxi is None:
                    break
                dr = (rfmaxi * log(m1i / m2i)) / (sfcz * g)
                rmaxi += dr
            if rfmaxi is None:
                break
            if rmax < rmaxi:
                rmax = rmaxi
                voptrf1 = voptrf1i
                voptrf2 = voptrf2i
                tloptrf1 = tloptrf1i
                tloptrf2 = tloptrf2i
                hrmax = h
            h += dh
            if h > hrmaxout + dh * 1e-3:
                break

        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(hrmax)
        vsd0sp, vsd0spab = ff.reshvsd(hrmax)[1:3]
        sfc1, fsfc1 = ff.ressfc(hrmax, vsnd, vsd0sp, vsd0spab, sfcz, sfcabz,
                                voptrf1, tloptrf1)
        sfc2, fsfc2 = ff.ressfc(hrmax, vsnd, vsd0sp, vsd0spab, sfcz, sfcabz,
                                voptrf2, tloptrf2)

        if rep:
            debug(1, "rmax: "
                  "rmax=%.1f[km]  hrmax=%.0f[m]  "
                  "v1=%.1f[m/s]  v2=%.1f[m/s]  "
                  "ma1=%.2f  ma2=%.2f  "
                  "tl1=%.3f  tl2=%.3f  "
                  "sfc1=%.2f[kg/hr/daN]  sfc2=%.2f[kg/hr/daN]  "
                  "fsfc1=%.3f  fsfc2=%.3f" %
                  (rmax * 1e-3, hrmax,
                   voptrf1, voptrf2, voptrf1 / vsnd, voptrf2 / vsnd,
                   tloptrf1, tloptrf2, sfc1 * 3.6e4, sfc2 * 3.6e4,
                   fsfc1, fsfc2))

        return rmax, hrmax


    def derive_for_roll (self):

        ff, ad, pd = self, self, self

        rep = ff.rep

        htrop = ad.htrop
        mmin, mmax, mref = pd.mmin, pd.mmax, pd.mref
        a0z, amaxz = pd.a0z, pd.amaxz
        pomaxz, romaxz = pd.pomaxz, pd.romaxz

        dv = 1.0
        ret = ff.comp_env(mref, 0.0, tlmax=2.0, dv=dv, rep=False)
        vminz, vopttsz = ret[0], ret[7]
        ret = ff.comp_env(mref, htrop, tlmax=2.0, dv=dv, rep=False)
        vminh, vopttsh = ret[0], ret[7]

        vmaxrz = vopttsz
        vmaxrh = vopttsh

        vlinrz = vminz
        vlinrh = vminh

        # TODO: Consider flaps better, do not rely on low vzerofac0.
        asp0 = radians(15.0)
        vzerofac0 = 0.5
        asp = amaxz - a0z
        vzerofac = int1r0(vzerofac0, asp / asp0)
        vzerorz = vminz * vzerofac
        vzerorh = vminh * vzerofac

        ar0 = 5.0
        tm0p = 0.2
        psmaxz = (pomaxz / tm0p) / (pd.ar / ar0)
        tm0r = 0.4
        rsmaxz = (romaxz / tm0r) / (pd.ar / ar0)

        asp0 = radians(15.0)
        rfacmaxa0 = 0.5
        asp = amaxz - a0z
        rfacmaxa = int1r0(rfacmaxa0, asp / asp0)

        ar0 = 5.0
        mrsp0 = 1.0
        rfacmaxm0 = 0.7
        mrsp = (mmax - mref) / mref
        mrsp = mrsp0
        rfacmaxm = int1r0(rfacmaxm0, (pd.ar / ar0) * (mrsp / mrsp0))

        if rep:
            debug(1, "roll: "
                  "psmaxz=%.1f[deg/s^2]  rsmaxz=%.1f[deg/s^2]  "
                  "vmaxrz=%.1f[m/s]  vmaxrh=%.1f[m/s]  "
                  "rfacmaxa=%.2f  rfacmaxm=%.2f" %
                  (degrees(psmaxz), degrees(rsmaxz),
                   vmaxrz, vmaxrh, rfacmaxa, rfacmaxm))

        return (vzerorz, vlinrz, vmaxrz, vzerorh, vlinrh, vmaxrh,
                rfacmaxa, rfacmaxm, psmaxz, rsmaxz)


    def derive_lgear (self):

        ff, ad, pd = self, self, self

        rep = ff.rep

        lgny, lgnz = pd.lgny, pd.lgnz
        lgmx, lgmy, lgmz = pd.lgmx, pd.lgmy, pd.lgmz

        p_n = Vec3D(0.0, lgny, lgnz)
        p_m = Vec3D(0.0, lgmy, lgmz) # at symmetry, so no lgmx
        l_cn = p_n.length()
        l_cm = p_m.length()
        l_mn = (p_m - p_n).length()
        l_s = (l_cn + l_cm + l_mn) / 2
        S = sqrt(l_s * (l_s - l_cn) * (l_s - l_cm) * (l_s - l_mn))
        h_mn = 2.0 * S / l_mn
        lghn = h_mn
        udp_mn = unitv(p_n - p_m)
        ex = Vec3D(1, 0, 0)
        rot = QuatD()
        rot.setFromAxisAngleRad(0.5 * pi, ex)
        udp_h = unitv(Vec3D(rot.xform(udp_mn)))
        p_h = udp_h * h_mn
        p_v = Vec3D(0.0, 0.0, intl01vr(0.0, lgny, lgmy, lgnz, lgmz))
        l_hv = (p_v - p_h).dot(udp_mn)
        lghvt = l_hv

        if rep:
            debug(1, "lgear:  lghn=%.3f[m]  lghvt=%.3f[m]" % (lghn, lghvt))

        return (lghn, lghvt)

# @cache-key-end: plane-dynamics

    def respros (self, m, h, rho, v, amin, a1m, a0, a1, amax, a):

        pd, ad = self, self

        rhoz, htrop = ad.rhoz, ad.htrop
        pomaxz, romaxz = pd.pomaxz, pd.romaxz
        psmaxz, rsmaxz = pd.psmaxz, pd.rsmaxz
        vzerorz, vlinrz, vmaxrz = pd.vzerorz, pd.vlinrz, pd.vmaxrz
        vzerorh, vlinrh, vmaxrh = pd.vzerorh, pd.vlinrh, pd.vmaxrh
        rfacmaxa, rfacmaxm = pd.rfacmaxa, pd.rfacmaxm
        mref, mmax = pd.mref, pd.mmax

        hfac = h / htrop
        vzeror = vzerorz + (vzerorh - vzerorz) * hfac
        vlinr = vlinrz + (vlinrh - vlinrz) * hfac
        vmaxr = vmaxrz + (vmaxrh - vmaxrz) * hfac
        rhofac = rho / rhoz
        if v > vlinr:
            vfac = v / vmaxr
            pomax = pomaxz * vfac
            romax = romaxz * vfac
            psmax = psmaxz * rhofac
            rsmax = rsmaxz * rhofac
            pomax = clamp(pomax, 0.0, pomaxz)
            romax = clamp(romax, 0.0, romaxz)
        elif v > vzeror:
            vlinfac = vlinr / vmaxr
            vfac = ((v - vzeror) / (vlinr - vzeror))
            pomax = pomaxz * vlinfac * vfac
            romax = romaxz * vlinfac * vfac
            psmax = psmaxz * rhofac * vfac**0.5
            rsmax = rsmaxz * rhofac * vfac**0.5
        else:
            pomax = radians(1.0)
            romax = radians(1.0)
            psmax = radians(1.0)
            rsmax = radians(1.0)
            # NOTE: Must not be zero, or else update_input can crash.

        if m > mref:
            mfac = int1r0(rfacmaxm, (m - mref) / (mmax - mref))
        else:
            mfac = 1.0
        pomax *= mfac
        romax *= mfac
        psmax *= mfac
        rsmax *= mfac

        if a > a0:
            afac = int1r0(rfacmaxa, (a - a0) / (amax - a0))
        else:
            afac = int1r0(rfacmaxa, (a - a0) / (amin - a0))
        pomax *= afac
        romax *= afac
        psmax *= afac
        rsmax *= afac

        return pomax, romax, psmax, rsmax


    def resvias (self, h, pr, q):

        ad = self
        rhoz, prz, kgam = ad.rhoz, ad.prz, ad.kgam
        qcmp = pr * ((q / (pr * kgam) + 1.0)**kgam - 1.0)
        vias = sqrt((prz / rhoz) * 2.0 * kgam * ((qcmp / prz + 1.0)**(1.0 / kgam) - 1.0))
        return qcmp, vias


    def resolve_stat (self, dq, m, p, u, hg, ng, tg):

        if u.length() < PlaneDynamics.MINSPEED:
            raise StandardError("Cannot input too small velocity.")
        if hg is not None:
            return self._resolve_stat_ground(dq, m, p, u, hg, ng, tg)
        else:
            return self._resolve_stat_air(dq, m, p, u)


    def _resolve_stat_air (self, dq, m, p, u):

        ff, ad, pd = self, self, self

        h = p[2]
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        v = u.length()
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        ma = v / vsnd
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks

        w = m * g
        q = 0.5 * rho * v**2
        ez = Vec3D(0, 0, 1)
        xit = unitv(u)
        tht = 0.5 * pi - acos(clamp(xit.dot(ez), -1.0, 1.0))
        stht, ctht = sin(tht), cos(tht)
        nit = 0
        tmaxref = tmaxab
        a = a0
        brd = AIRBRAKE.RETRACTED
        fld = FLAPS.RETRACTED
        while True:
            nit += 1
            ap = a
            sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
            d = (sd0 + ks * sl**2) * q
            t = (d + w * stht) / (1.0 - 0.5 * a**2)
            t = min(t, tmaxref)
            a_p = a
            a, sl, l = (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1, q, t, w * ctht))
            # TODO: If a is None, try with full flaps (fld = FLAPS.LANDING).
            if a is None:
                a = 0.5 * (a_p + amax)
            if abs(a - ap) < radians(0.01):
                a = ap
                break
        # TODO: If t < 0, try with air brake (brd = AIRBRAKE.EXTENDED).
        tl = ff.restlth(t, tmax, tmaxab) or 0.0
        c = (t * (1.0 - 0.5 * a**2) - d - w * stht) / m
        b = xit * c

        if abs(xit.dot(ez)) < (1.0 -1e-5): # if not vertical flight
            ab = unitv(xit.cross(ez))
        else:
            ab = Vec3D(1, 0, 0)
        ant = unitv(ab.cross(xit))
        rot = QuatD()
        rot.setFromAxisAngleRad(a, ab)
        an = unitv(Vec3D(rot.xform(ant)))
        phi = 0.5 * pi
        o = Vec3D()
        s = Vec3D()

        # NOTE: To replace the above with this, respathq would have to be
        # updated to handle t_needed > tmaxab, and return acceleration.
        #w = m * g
        #q = 0.5 * rho * v**2
        #ez = Vec3D(0, 0, 1)
        #xit = unitv(u)
        #tht = 0.5 * pi - acos(clamp(xit.dot(ez), -1.0, 1.0))
        #wt = w * -sin(tht)
        #wn = w * -cos(tht)
        #wb = 0.0
        #fn = 0.0
        #ft = 0.0
        #nit, a, sl, l, sd, d, tl, t, phi = (
            #ff.respathq(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q,
                        #wt, wn, wb, fn, ft, tmax, tmaxab))
        #c = (t * (1.0 - 0.5 * a**2) - d + wt) / m
        #b = xit * c
        #if abs(xit.dot(ez)) < (1.0 -1e-5): # if not vertical flight
            #ab = unitv(xit.cross(ez))
        #else:
            #ab = unitv(1.0, 0.0, 0.0)
        #ant = unitv(ab.cross(xit))
        #rot = QuatD()
        #rot.setFromAxisAngleRad(a, ab)
        #an = unitv(Vec3D(rot.xform(ant)))
        #o = Vec3D()
        #s = Vec3D()

        gc = False
        ag = 0.0
        brw = False
        gso = 0.0
        gsp = 0.0
        gsr = 0.0
        grh = 1.0
        tg = -1

        dq.p, dq.u, dq.b, dq.o, dq.s, dq.gc = p, u, b, o, s, gc
        dq.m, dq.an, dq.phi, dq.tl, dq.brd, dq.fld = m, an, phi, tl, brd, fld
        dq.ag, dq.brw, dq.gso, dq.gsp, dq.gsr = ag, brw, gso, gsp, gsr
        dq.tg, dq.grh = tg, grh
        return dq


    def resgc (self, p, u, b, a, hg, ng):

        pd = self

        h_nm, l_hv = pd.lghn, pd.lghvt
        ez = Vec3D(0, 0, 1)
        p_g = Vec3D(p[0], p[1], hg)
        xit_b = unitv(u)
        xib = -ng
        xit = unitv(xit_b - xib * xit_b.dot(xib))
        xin = unitv(xib.cross(xit))
        k_pz = h_nm / sqrt(1.0 - ez.dot(xit)**2 - ez.dot(xin)**2)
        p = p_g + ez * k_pz
        u = xit * u.length()
        b = b - xib * b.dot(xib)
        k_ht = k_pz * ez.dot(xit)
        k_hn = k_pz * ez.dot(xin)
        an_g = unitv(ez * k_pz - (xit * (k_ht + l_hv) + xin * k_hn))
        a_g = acos(clamp(xit.dot(an_g), -1.0, 1.0)) - 0.5 * pi
        ab = unitv(xit.cross(an_g))
        rot = QuatD()
        rot.setFromAxisAngleRad(a - a_g, ab)
        an = unitv(Vec3D(rot.xform(an_g)))
        at = unitv(an.cross(ab))
        phi = xin.signedAngleRad(ab, xit)
        assert abs(phi) < 1e-5
        phi = 0.0

        return p, u, b, xit, xin, xib, at, an, ab, a_g, phi


    def resgatt (self, ng, at, an, ab):

        ngb = unitv(ng - ab * ng.dot(ab))
        gsp = ngb.signedAngleRad(an, ab)
        ngt = unitv(ng - at * ng.dot(at))
        gsr = ngt.signedAngleRad(an, at)
        return gsp, gsr


    def resgt (self, tg):

        mug, mub, grh = GROUND._data[tg]
        return mug, mub, grh


    def _resolve_stat_ground (self, dq, m, p, u, hg, ng, tg):

        ff, ad, pd = self, self, self

        b = Vec3D()
        a = 0.0
        p, u, b, xit, xin, xib, at, an, ab, ag, phi = (
            ff.resgc(p, u, b, a, hg, ng))

        h = p[2]
        fld = FLAPS.TAKEOFF
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        mug, mub, grh = ff.resgt(tg)
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        v = u.length()
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        a0z, a1z, amaxz = ff.resslafl(fld, a0z, a1z, amaxz)
        ma = v / vsnd
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        sd0 = ff.ressd0fl(fld, sd0cr, sd0)
        ks = pd.ks

        w = m * g
        ez = Vec3D(0, 0, 1)
        wez = -ez * w
        wt = wez.dot(xit)
        wb = wez.dot(xib)
        q = 0.5 * rho * v**2
        sl, l = ff.reslifta(amin, a1m, a0, a1, amax, sla, sla1, a, q)
        sina = a
        cosa = 1.0 - 0.5 * a**2
        tana = sina / cosa
        d = (sd0 + ks * sl**2) * q
        mu = mug
        rb = ((wb - (l + (d - wt) * tana)) / (1.0 + mu * tana))
        assert rb >= 0.0
        tmaxref = tmaxab
        t = (d - wt + rb * mu) / cosa
        t = min(t, tmaxref)
        # TODO: If t < 0, try with wheel brake (brw = True, mu = mub).
        tl = ff.restlth(t, tmax, tmaxab) or 0.0
        c = (t * cosa - d + wt - rb * mu) / m
        b = xit * c
        o = Vec3D()
        s = Vec3D()

        gc = True
        brd = AIRBRAKE.RETRACTED
        brw = False
        gso = 0.0
        gsp = 0.0
        gsr = 0.0

        dq.p, dq.u, dq.b, dq.o, dq.s, dq.gc = p, u, b, o, s, gc
        dq.m, dq.an, dq.phi, dq.tl, dq.brd, dq.fld = m, an, phi, tl, brd, fld
        dq.ag, dq.brw, dq.gso, dq.gsp, dq.gsr = ag, brw, gso, gsp, gsr
        dq.tg, dq.grh = tg, grh
        return dq


    MINSPEED = 1e-5

    def update_fstep (self, dq, da, dr, dtl, dbrd, dgso, dtm, hg, ng, tg,
                      eps=radians(0.001), maxit=5, extraq=False):

        ff, ad, pd = self, self, self
        #debug(1, "fstep:  da=% .6e  dr=% .6e  dtl=% .6e  dtm=% .6e" %
              #(degrees(da), degrees(dr), dtl, dtm))

        p, u, b, o, s, gc = dq.p, dq.u, dq.b, dq.o, dq.s, dq.gc
        m, an, phi, tl, brd, fld = dq.m, dq.an, dq.phi, dq.tl, dq.brd, dq.fld
        lg, ag, brw, gso = dq.lg, dq.ag, dq.brw, dq.gso

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        if hg is not None:
            mug, mub, grh = ff.resgt(tg)
        else:
            grh = 0.0
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        a0z, a1z, amaxz = ff.resslafl(fld, a0z, a1z, amaxz)
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        sd0 = ff.ressd0fl(fld, sd0cr, sd0)
        if brd:
            sd0 += dsd0br * brd
        if lg:
            sd0 += dsd0lg
        ks = pd.ks
        sfcz, sfcabz = pd.sfcz, pd.sfcabz
        mref, nmaxref = pd.mref, pd.nmaxref

        if hg is not None:
            mu = mub if brw else mug

        w = m * g

        tlmax = 2.0 if pd.hasab else 1.0
        tl_n = clamp(tl + dtl, 0.0, tlmax)
        t_n = ff.resthtl(tl_n, tmax, tmaxab)
        if t_n is None:
            raise StandardError("Throttle out of range.")
        sfc_n = ff.ressfc(h, vsnd, vsd0sp, vsd0spab, sfcz, sfcabz, v, tl_n)[0]
        rot = QuatD()

        brd_n = clamp(brd + dbrd, 0.0, 1.0)

        ez = Vec3D(0.0, 0.0, 1.0)
        xit = unitv(u)
        ab = unitv(xit.cross(an))
        a = acos(clamp(xit.dot(an), -1.0, 1.0)) - 0.5 * pi

        gc_n = gc
        v_msw = 2.0
        if gc:
            rot.setFromAxisAngleRad(-phi, xit)
            xin = unitv(Vec3D(rot.xform(ab)))
            xib = unitv(xit.cross(xin))
            v = u.length()
            xit_n = xit
            xin_n = xin
            xib_n = xib
            ag_n = ag
            a_n = a
            u_n = u
            v_n = v
            phi_n = phi

        veps = PlaneDynamics.MINSPEED

        i_gc = 0
        while True:
            gc_np = gc_n

            if not gc_n:
                a_n = a + da
                u_n, xit_n = u, xit
                drxit_n = 0.5 * da
                phi_n = phi
                it = 0
                last = False
                while True:
                    it += 1

                    rot.setFromAxisAngleRad(dr, xit)
                    ab_n = unitv(Vec3D(rot.xform(ab)))
                    rot.setFromAxisAngleRad(-phi_n, xit)
                    xin_n = unitv(Vec3D(rot.xform(ab_n)))
                    xib_n = unitv(xit_n.cross(xin_n))

                    m_n = m - t_n * sfc_n * dtm
                    w_n = m_n * g
                    wez_n = -ez * w_n
                    wt_n = wez_n.dot(xit_n)
                    wn_n = wez_n.dot(xin_n)
                    wb_n = wez_n.dot(xib_n)
                    v_n = u_n.length()
                    q_n = 0.5 * rho * v_n**2
                    ret = ff.resliftafp(amin, a1m, a0, a1, amax, sla, sla1, a_n, q_n)
                    sl_n, l_n, slcdi_n = ret
                    sd_n = sd0 + ks * slcdi_n**2
                    d_n = q_n * sd_n
                    sina_n = a_n
                    cosa_n = 1.0 - 0.5 * a_n**2
                    ft_n = t_n * cosa_n - d_n + wt_n
                    lpt_n = l_n + t_n * sina_n
                    fn_n = lpt_n * sin(phi_n) + wn_n
                    # In straight line phi is arbitrary, so fb may not be zero.
                    fb_n = -lpt_n * cos(phi_n) + wb_n
                    ct_n = ft_n / m_n
                    cn_n = fn_n / m_n
                    cb_n = fb_n / m_n
                    b_n = xit_n * ct_n + xin_n * cn_n + xib_n * cb_n
                    #debug(1, "xit_n (% .8e, % .8e, % .8e)" % (tuple(xit_n)))
                    #debug(1, "phi_n=%s a_n=%s" % (degrees(phi_n), degrees(a_n)))
                    #debug(1, "ct_n=%s cn_n=%s cb_n=%s" % (ct_n, cn_n, cb_n))
                    #debug(1, "b_n (% .8e, % .8e, % .8e)" % (tuple(b_n)))

                    u_n = u + (b + b_n) * (0.5 * dtm)
                    if u_n.dot(xit_n) < veps:
                        u_n = xit * veps

                    #debug(1, "fstep:  it=%d  "
                          #"ct_n=%.2f[m^2/s]  cn_n=%.2f[m^2/s]  cb_n=%.2f[m^2/s]  "
                          #"phi_n=%.4f[deg]  rn_n=%.1f[m]  rb_n=%.1f[m]  xib=%s" %
                          #(it, ct_n, cn_n, cb_n, degrees(phi_n),
                           #(m_n * v_n**2) / fn_n, (m_n * v_n**2) / fb_n,
                           #"(% .6e, % .6e, % .6e)" % tuple(xib_n)))
                    if last:
                        break

                    xit_n = unitv(u_n)
                    drxit_np = drxit_n
                    drxit_n = xit.signedAngleRad(xit_n, ab)

                    sglpt = sign(lpt_n)
                    phi_n = atan2((fn_n - wn_n) * sglpt, (fb_n - wb_n) * -sglpt)

                    #if abs(wb_n) > abs(fn_n - wn_n): # keep radius on normal
                        ##debug(1, "fstep-inv-bn")
                        #fn_n, wb_n = wb_n + wn_n, fn_n - wn_n
                    #sglpt = sign(lpt_n) * sign(fn_n)
                    #phi_n = atan2((fn_n - wn_n) * sglpt, (- wb_n) * -sglpt)

                    dqce = abs(drxit_n - drxit_np)
                    #debug(1, "dqce=% .2e  qc=%s" % (degrees(dqce), qc_n))
                    if dqce < eps or it >= maxit:
                        last = True

                p_n = p + u * dtm + (b * 2.0 + b_n) * ((1.0 / 6.0) * dtm**2)

                gso_n = 0.0
                gsp_n = 0.0
                gsr_n = 0.0

                if i_gc == 0 and hg is not None:
                    h_nm, l_hv = pd.lghn, pd.lghvt
                    if p_n[2] - hg < h_nm:
                        gc_n = True

            else:
                assert abs(phi_n) < 1e-5
                gso_n = gso + dgso
                dgs_n = gso_n * dtm
                rot.setFromAxisAngleRad(dgs_n, xib_n)

                htrop = ad.htrop
                vminz, vminflz, vminflh = pd.vminz, pd.vminfl1abz, pd.vminfl1abh
                if vminflz >= 0.0 and vminflh >= 0.0:
                    vmin = intl01vr(h, 0.0, htrop, vminflz, vminflh)
                elif vminflz >= 0.0:
                    vmin = vminflz
                else:
                    vmin = vminz
                vrot = vmin * 0.8
                da_in = da
                if da > 0.0:
                    da = intl01vr(v_n, vrot, vmin, 0.0, da)
                a_n = a + da
                a_n = max(ag_n, a_n)
                sina_n = a_n
                cosa_n = 1.0 - 0.5 * a_n**2
                tana_n = sina_n / cosa_n

                m_n = m - t_n * sfc_n * dtm
                w_n = m_n * g
                wez_n = -ez * w_n
                wt_n = wez_n.dot(xit_n)
                wn_n = wez_n.dot(xin_n)
                wb_n = wez_n.dot(xib_n)
                v_n = u_n.length()
                q_n = 0.5 * rho * v_n**2
                ret = ff.resliftafp(amin, a1m, a0, a1, amax, sla, sla1, a_n, q_n)
                sl_n, l_n, slcdi_n = ret
                sd_n = sd0 + ks * slcdi_n**2
                d_n = q_n * sd_n
                if abs(v_n - veps) < veps * 1e-3:
                    mu = 0.0
                rb_n = ((wb_n - (l_n + (d_n - wt_n) * tana_n)) / (1.0 + mu * tana_n))
                if rb_n > 0.0:
                    rt_n = rb_n * mu
                    ft_n = t_n * cosa_n - d_n + wt_n - rt_n
                    fn_n = m_n * v_n * gso_n
                    #rn_n = fn_n - wn_n
                    fb_n = 0.0
                    ct_n = ft_n / m_n
                    cn_n = fn_n / m_n
                    cb_n = fb_n / m_n
                    #debug(1, "here55 %s %s %s %s %s %s %s" %
                          #(degrees(da_in), v_n, vrot, vmin,
                           #degrees(da), degrees(a_n), ct_n))
                    b_n = xit_n * ct_n + xin_n * cn_n + xib_n * cb_n
                    u_n = u + (b + b_n) * (0.5 * dtm)
                    if u_n.dot(xit_n) > veps:
                        p_n = p + u * dtm + (b * 2.0 + b_n) * ((1.0 / 6.0) * dtm**2)
                    else:
                        b_n = Vec3D()
                        u_n = xit * veps
                        p_n = p
                    drxit_n = 0.0
                    dqce = 0.0
                else:
                    if i_gc == 0:
                        gc_n = False

            if gc_n:
                (p_n, u_n, b_n, xit_n, xin_n, xib_n, at_n, an_n, ab_n,
                 ag_n, phi_n) = (
                     ff.resgc(p_n, u_n, b_n, a_n, hg, ng))
            else:
                ag_n = 0.0

            i_gc += 1
            if gc_n == gc_np or i_gc == 2:
                break

        rot.setFromAxisAngleRad(a_n, ab_n)
        at_n = unitv(Vec3D(rot.xform(xit_n)))
        ant_n = unitv(ab_n.cross(xit_n))
        an_n = unitv(Vec3D(rot.xform(ant_n)))
        if hg is not None:
            gsp_n, gsr_n = ff.resgatt(ng, at_n, an_n, ab_n)

        if dtm > 0.0:
            o_n = ab_n * ((da + drxit_n) / dtm) + xit_n * (dr / dtm)
            s_n = (o_n - o) / dtm
        else:
            o_n = Vec3D()
            s_n = Vec3D()

        if dqce >= eps:
            debug(1, "fstep-end:  it=%d  "
                  "da=%+8.4f[deg]  dr=%+8.4f[deg]  dtl=%+7.4f  dbrd=%+7.4f" %
                  (it, da, dr, dtl, dbrd))
            #debug(1, "fstep-end2:  "
                  #"xit=(% .4f, % .4f, % .4f)  xin=(% .4f, % .4f, % .4f)" %
                  #(xit_n[0], xit_n[1], xit_n[2],
                   #xin_n[0], xin_n[1], xin_n[2]))

        dq.p, dq.u, dq.b, dq.o, dq.s, dq.gc = p_n, u_n, b_n, o_n, s_n, gc_n
        dq.m, dq.an, dq.phi, dq.tl, dq.brd = m_n, an_n, phi_n, tl_n, brd_n
        dq.ag, dq.gso, dq.gsp, dq.gsr = ag_n, gso_n, gsp_n, gsr_n
        dq.tg, dq.grh = tg, grh

        #debug(1, "fstep30 %s %s %s %s" % (xit_n, xin_n, xib_n, cn_n))
        if extraq:

            da = a_n - a
            dr = ab.signedAngleRad(ab_n, xit_n)
            dtl = tl_n - tl

            dbrd = brd_n - brd

            #tr0, rr0 = dq.tr or 0.0, dq.rr or 0.0
            tr, rr = 0.0, 0.0
            if dtm > 0.0:
                xitz = xit.dot(ez)
                xitz_n = xit_n.dot(ez)
                if abs(xitz) < 1-1e-10 and abs(xitz_n) < 1-1e-10:
                    xith = unitv(xit - ez * xitz)
                    xith_n = unitv(xit_n - ez * xitz_n)
                    tr =  xith.signedAngleRad(xith_n, ez) / dtm
                    #tr = 2.0 * xith.signedAngleRad(xith_n, ez) / dtm - tr0
                rr = dr / dtm
                #rr = 2.0 * (dr / dtm) - rr0

            m, p, u, b, o, s = m_n, p_n, u_n, b_n, o_n, s_n
            a, phi, fn = a_n, phi_n, fn_n
            xit, xib, xin, at, an, ab = xit_n, xib_n, xin_n, at_n, an_n, ab_n
            q, l, sl, d, sd, t, tl = q_n, l_n, sl_n, d_n, sd_n, t_n, tl_n
            brd = brd_n
            ag = ag_n
            sfc = sfc_n
            drxit = drxit_n

            xitz = xit.dot(ez)
            if abs(xitz) < 1-1e-10:
                xith = unitv(xit - ez * xitz)
            else:
                xith = Vec3D()

            ant = unitv(xit.cross(an).cross(xit))

            if abs(xit.dot(ez)) < 1.0 -1e-5: # if not vertical flight
                nxy = unitv(ez.cross(xit).cross(ez))
                ey = Vec3D(0.0, 1.0, 0.0)
                hdg = ey.signedAngleRad(nxy, ez)
                nz = unitv(xit.cross(ez).cross(xit))
                bnk = nz.signedAngleRad(ant, xit)
            else:
                hdg = dq.hdg if dq.hdg else 0.0
                bnk = dq.bnk if dq.bnk else 0.0
            pch = atan2(at.dot(ez), at.getXy().length())

            h = p[2]
            v = u.length()
            ma = v / vsnd
            cr = u[2]
            tht = asin(cr / v)

            ct = b.dot(xit)
            cn = b.dot(xin)
            cb = b.dot(xib) # zero by construction

            n = (l + t * a) / w
            nmin, nmax = ff.resnmax(mref, nmaxref, m)

            rn = (m * v**2) / fn if abs(fn) > 1e-10 else 1e10

            # Linear throttle (same as normal in non-afterburning,
            # then same slope through afterburning).
            ltl = t / tmax

            #if abs(bnk) < 0.5 * pi:
                #wf = w / cos(bnk)
                #crmax_freeze = lambda: (
                    #ff.rescr(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, v, q,
                             #wf, tmax, ai=a)[1])
                #crmaxab_freeze = lambda: (
                    #ff.rescr(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, v, q,
                             #wf, tmaxab, ai=a)[1])
            #else:
                #crmax_freeze = lambda: None
                #crmaxab_freeze = lambda: None
            #mv = m * v
            #ws = w * sin(tht)
            #trmax_freeze = lambda: (
                #ff.restrmax(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q, mv,
                            #w, ws, tmax, nmax))
            #trmaxab_freeze = lambda: (
                #ff.restrmax(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q, mv,
                            #w, ws, tmaxab, nmax))

            anmin_freeze = lambda: (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1,
                             q, t, w * nmin)[0])
            anmax_freeze = lambda: (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1,
                             q, t, w * nmax)[0])
            anone_freeze = lambda: (
                ff.resliftwt(amin, a1m, a0, a1, amax, sla, sla1,
                             q, t, w)[0])

            wt = w * -sin(tht)
            def natmax_w (t):
                ret = ff.resdragwt(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks,
                                   q, t, wt, 0.0)
                a, sd, d, sl, l = ret
                n = (l + t * a) / w if a is not None else None
                return a, n
            def natmax_freeze ():
                return natmax_w(tmax)
            def natmaxab_freeze ():
                return natmax_w(tmaxab)

            def nmaxv_w (t):
                a = amax
                ret = ff.resliftafp(amin, a1m, a0, a1, amax, sla, sla1, a, q)
                sl, l, slcd = ret
                n = (l + t * a) / w if a is not None else None
                return n
            def nmaxv_freeze ():
                return nmaxv_w(tmax)
            def nmaxvab_freeze ():
                return nmaxv_w(tmaxab)

            pomax, romax, psmax, rsmax = (
                ff.respros(m, h, rho, v, amin, a1m, a0, a1, amax, a))

            ao0, ro0, tlv0 = dq.ao or 0.0, dq.ro or 0.0, dq.tlv or 0.0
            if dtm > 0.0:
                ao = da / dtm
                #ao = 2.0 * (da / dtm) - ao0
                ro = dr / dtm
                #ro = 2.0 * (dr / dtm) - ro0
                #debug(1, "fstep: ro=%f dr=%f dtm=%f ro0=%f" %
                      #(degrees(ro), degrees(dr), dtm, degrees(ro0)))
                tlv = dtl / dtm
                #tlv = 2.0 * (dtl / dtm) - tlv0
            else:
                ao = ao0
                ro = ro0
                tlv = tlv0

            xito = drxit / dtm if dtm > 0.0 else 0.0

            vias_freeze = lambda: ff.resvias(h, pr, q)[1]

            dq.da, dq.dr, dq.dtl, dq.dbrd = da, dr, dtl, dq.dbrd
            dq.g, dq.rho, dq.pr, dq.vsnd = g, rho, pr, vsnd
            dq.gb = ez * -g
            dq.nmin, dq.nmax = nmin, nmax
            dq.xit, dq.xin, dq.xib, dq.xith = xit, xin, xib, xith
            dq.at, dq.ab, dq.ant = at, ab, ant
            dq.h, dq.v, dq.ma, dq.cr, dq.a, dq.n, dq.rn = h, v, ma, cr, a, n, rn
            dq.hdg, dq.bnk, dq.tht, dq.pch = hdg, bnk, tht, pch
            dq.ct, dq.cn, dq.cb = ct, cn, cb
            dq.t, dq.tmax, dq.tmaxab, dq.ltl = t, tmax, tmaxab, ltl
            dq.l, dq.sl, dq.d, dq.sd = l, sl, d, sd
            #dq.freeze("crmax", crmax_freeze)
            #dq.freeze("crmaxab", crmaxab_freeze)
            #dq.freeze(("trmaxi", "trmaxs"), trmax_freeze)
            #dq.freeze(("trmaxiab", "trmaxsab"), trmaxab_freeze)
            dq.tr, dq.rr = tr, rr
            dq.sfc = sfc
            dq.pomax, dq.psmax = pomax, psmax
            dq.romax, dq.rsmax = romax, rsmax
            dq.tlvmax, dq.tlcmax = 1.0, 10.0
            dq.brdvmax = 0.5
            dq.ao, dq.ro, dq.tlv = ao, ro, tlv
            dq.xito = xito
            dq.amin, dq.a1m, dq.a0, dq.a1, dq.amax = amin, a1m, a0, a1, amax
            dq.freeze("anmin", anmin_freeze)
            dq.freeze("anmax", anmax_freeze)
            dq.freeze("anone", anone_freeze)
            dq.freeze(("atmax", "ntmax"), natmax_freeze)
            dq.freeze(("atmaxab", "ntmaxab"), natmaxab_freeze)
            dq.freeze("nmaxv", nmaxv_freeze)
            dq.freeze("nmaxvab", nmaxvab_freeze)
            dq.freeze("vias", vias_freeze)

        return dq


    def diff_to_path_tnr (self, dq, xitt, xint, rnt, vt, ctt,
                          tmaxref=None, nmininv=None, facedir=None,
                          bleedv=False, bleedr=False, mon=False):

        ff, ad, pd = self, self, self

        xit_t, xin_t = xitt, xint
        rn_t, v_t, ct_t = rnt, vt, ctt

        m, p, u, b, an, tl, phi = dq.m, dq.p, dq.u, dq.b, dq.an, dq.tl, dq.phi
        brd = dq.brd

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks

        w = m * g
        ez = Vec3D(0.0, 0.0, 1.0)
        wez = -ez * w

        xit = unitv(u)
        ab = unitv(xit.cross(an))
        a = acos(clamp(xit.dot(an), -1.0, 1.0)) - 0.5 * pi

        xib_t = xit_t.cross(xin_t)
        wt_t = wez.dot(xit_t)
        wn_t = wez.dot(xin_t)
        wb_t = wez.dot(xib_t)
        ft_t = m * ct_t
        fn_t = (m * v_t**2 / rn_t) if abs(rn_t) > 0.0 else 0.0
        q_t = 0.5 * rho * v_t**2
        nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
            ff.respathq(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q_t,
                        wt_t, wn_t, wb_t, ft_t, fn_t, tmax, tmaxab,
                        tmaxref=tmaxref, invert=False,
                        bleedv=bleedv, bleedr=bleedr))
        if nmininv is not None or a_t is None:
            nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti = (
                ff.respathq(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q_t,
                            wt_t, wn_t, wb_t, ft_t, fn_t, tmax, tmaxab,
                            tmaxref=tmaxref, invert=True,
                            bleedv=bleedv, bleedr=bleedr))
            if a_ti is None:
                nmininv = None
            elif a_t is None:
                nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
                    nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti)
                nmininv = None
        if a_t is not None:
            rot = QuatD()
            rot.setFromAxisAngleRad(phi_t, xit_t)
            ab_t = unitv(Vec3D(rot.xform(xin_t)))
            da = a_t - a
            dr = ab.signedAngleRad(ab_t, xit)
            dtl = tl_t - tl
            brd_t = AIRBRAKE.RETRACTED
            dbrd = brd_t - brd
            fld = FLAPS.RETRACTED
            inv = False
            if nmininv is not None:
                n_ti = (l_ti + t_ti * a_ti) / w
                if n_ti > nmininv:
                    rot.setFromAxisAngleRad(phi_ti, xit_t)
                    ab_ti = unitv(Vec3D(rot.xform(xin_t)))
                    dr_i = ab.signedAngleRad(ab_ti, xit)
                    if facedir is not None:
                        ant_t = unitv(ab_t.cross(xit_t))
                        ant_ti = unitv(ab_ti.cross(xit_t))
                        inv = (ant_ti[2] > 0.0 and ant_ti[2] > ant_t[2])
                    else:
                        inv = (abs(dr_i) < abs(dr))
            if inv:
                da = a_ti - a
                dr = dr_i
                dtl = tl_ti - tl
                phi_t = phi_ti
                nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
                    nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti)
            if mon:
                debug(1, "diff-to-path-tnr:  "
                      "a=% 8.4f[deg]  at=% 8.4f[deg]  "
                      "phi=% 8.4f[deg]  phit=% 8.4f[deg]  "
                      "tl=%7.4f  tlt=% 8.4f  inv=%s" %
                      (degrees(a), degrees(a_t),
                       degrees(phi), degrees(phi_t),
                       tl, tl_t, inv))
        else:
            # TODO: Try with air brake (brd = AIRBRAKE.EXTENDED, sd0 + dsd0br * brd).
            da = None
            dr = None
            dtl = None
            dbrd = None
            fld = None
            inv = None
            if mon:
                debug(1, "diff-to-path-tnr:  none")

        return da, dr, dtl, dbrd, fld, phi_t, inv


    def diff_to_path_tnra (self, dq, att, ant, rnt, vt, ctt,
                           tmaxref=None, nmininv=None,
                           bleedv=False, bleedr=False, mon=False):

        ff, ad, pd = self, self, self

        at_t, an_t = att, ant
        rn_t, v_t, ct_t = rnt, vt, ctt

        m, p, u, b, an, tl, phi = dq.m, dq.p, dq.u, dq.b, dq.an, dq.tl, dq.phi
        brd = dq.brd

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks

        w = m * g
        ez = Vec3D(0.0, 0.0, 1.0)
        wez = -ez * w

        xit = unitv(u)
        ab = unitv(xit.cross(an))
        a = acos(clamp(xit.dot(an), -1.0, 1.0)) - 0.5 * pi

        ab_t = at_t.cross(an_t)
        wta_t = wez.dot(at_t)
        wna_t = wez.dot(an_t)
        wba_t = wez.dot(ab_t)
        ft_t = m * ct_t
        fn_t = (m * v_t**2 / rn_t) if abs(rn_t) > 0.0 else 0.0
        q_t = 0.5 * rho * v_t**2
        nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
            ff.respathqa(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q_t,
                         wta_t, wna_t, wba_t, ft_t, fn_t, tmax, tmaxab,
                         tmaxref=tmaxref, invert=False,
                         bleedv=bleedv, bleedr=bleedr))
        if nmininv is not None or a_t is None:
            nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti = (
                ff.respathqa(amin, a1m, a0, a1, amax, sla, sla1, sd0, ks, q_t,
                             wta_t, -wna_t, -wba_t, ft_t, fn_t, tmax, tmaxab,
                             tmaxref=tmaxref, invert=True,
                             bleedv=bleedv, bleedr=bleedr))
            if a_ti is None:
                nmininv = None
            elif a_t is None:
                nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
                    nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti)
                nmininv = None
        if a_t is not None:
            da = a_t - a
            dr = ab.signedAngleRad(ab_t, xit)
            dtl = tl_t - tl
            brd_t = AIRBRAKE.RETRACTED
            dbrd = brd_t - brd
            fld = FLAPS.RETRACTED
            inv = False
            if nmininv is not None:
                n_ti = (l_ti + t_ti * a_ti) / w
                if n_ti > nmininv:
                    dr_i = ab.signedAngleRad(-ab_t, xit)
                    inv = (abs(dr_i) < abs(dr))
            if inv:
                da = a_ti - a
                dr = dr_i
                dtl = tl_ti - tl
                phi_t = phi_ti
                nit_t, a_t, sl_t, l_t, sd_t, d_t, tl_t, t_t, phi_t = (
                    nit_ti, a_ti, sl_ti, l_ti, sd_ti, d_ti, tl_ti, t_ti, phi_ti)
            if mon:
                debug(1, "diff-to-path-tnra:  "
                      "a=% 8.4f[deg]  at=% 8.4f[deg]  "
                      "phi=% 8.4f[deg]  phit=% 8.4f[deg]  "
                      "tl=%7.4f  tlt=% 8.4f  inv=%s" %
                      (degrees(a), degrees(a_t),
                       degrees(phi), degrees(phi_t),
                       tl, tl_t, inv))
        else:
            # TODO: Try with air brake (brd = AIRBRAKE.EXTENDED, sd0 + dsd0br * brd).
            da = None
            dr = None
            dtl = None
            dbrd = None
            fld = None
            inv = None
            if mon:
                debug(1, "diff-to-path-tnra:  none")

        return da, dr, dtl, dbrd, fld, phi_t, inv


    def diff_to_path_gatk (self, cq, dq, tm, dtm, gh,
                           tp, tu, tb, tsz, shd, shldf, freeab,
                           skill=None, mon=False):

        if mon:
            debug(1, "gatk ==================== start")

        ff, ad, pd = self, self, self

        m, p, u, b, an, tl, phi = dq.m, dq.p, dq.u, dq.b, dq.an, dq.tl, dq.phi
        brd = dq.brd

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks
        mref, nmaxref = pd.mref, pd.nmaxref
        nmin, nmax = ff.resnmax(mref, nmaxref, m)

        a = dq.a
        at, an, ab, ant = dq.at, dq.an, dq.ab, dq.ant
        xit, xib = dq.xit, dq.xib
        ao, ro, tlv = dq.ao, dq.ro, dq.tlv
        pomax, romax, tlvmax = dq.pomax, dq.romax, dq.tlvmax
        psmax, rsmax, tlcmax = dq.psmax, dq.rsmax, dq.tlcmax
        brdvmax = dq.brdvmax

        if not cq.inited:
            cq.inited = True
            cq.ao, cq.ro, cq.tlv = ao, ro, tlv
            cq.dac = 0.0
            cq.da_ib = [0.0, 0.0]
            cq.dtmu = 0.0
            cq.inintc = False
            #cq.dtm_tdec_min = 3.0
            #cq.dtm_tdec_max = 5.0
            #cq.tm_tdec = tm
            #cq.dtm_rtdec_min = 5.0
            #cq.dtm_rtdec_max = 8.0
            #cq.tm_rtdec = tm
            # For skill modifiers:
            cq.dtm_btp_min = 4.0
            cq.dtm_btp_max = 12.0
            cq.tm_btp = tm
            cq.dtm_bvi_min = 2.0
            cq.dtm_bvi_max = 10.0
            cq.tm_bvi = tm

        cao, cro, ctlv = cq.ao, cq.ro, cq.tlv
        da_ib_p = cq.da_ib[:]
        dac = cq.dac
        dtmu = cq.dtmu

        ez = Vec3D(0.0, 0.0, 1.0)
        dtmeps = dtm * 1e-2

        if mon:
            vf = lambda v, d=6: "(%s)" % ", ".join(("%% .%df" % d) % e for e in v)

        shd *= intl01vr(tsz / 15.0, 0.5, 2.0, 0.8, 1.1)

        txit = unitv(tu)
        sig_av = acos(clamp(txit.dot(xit), -1.0, 1.0))
        shd *= intl01vr(sig_av, radians(170.0), radians(180.0), 1.0, 3.0)

        #shd_p = shd
        if skill:
            shd *= intl01v(skill.aiming, 0.6, 1.0)
        #assert abs(shd_p - shd) < 1e-5

        # Positional data for the target.
        dp = tp - p
        ad = Vec3D(unitv(dp))
        td = dp.length()
        sig_oc = acos(ad.dot(at))
        if False: #skill:
            ifac_btp = intl01r(sig_oc, radians(30.0), radians(120.0))
            if ifac_btp > 0.0:
                if cq.tm_btp <= tm:
                    cq.rdp_btp = intl01v(skill.awareness, 1.0, 0.0)
                    cq.udp_btp = vtod(randvec())
                    cq.tm_btp = tm + intl01v(ifac_btp, cq.dtm_btp_min, cq.dtm_btp_max)
                dtd = (intl01v(ifac_btp, 0.0, shd * 2.0) *
                       intl01r(td, 0.0, shd * 4.0) *
                       cq.rdp_btp)
                tp = tp + cq.udp_btp * dtd # copy
                dp = tp - p
                ad = Vec3D(unitv(dp))
                td = dp.length()
                sig_oc = acos(ad.dot(at))

        # Performance limits.
        # NOTE: Quantity set and ordering as returned by comp_env.
        abd = 5000.0 #!!!
        useab = int((freeab or td < abd) and pd.hasab)
        ret_mh = ff.tab_all_mh[useab](m, h)
        (vmin, vmax, crmaxa, voptc, trimaxa, trsmaxa, voptti, voptts,
         rfmaxa, voptrf, tloptrf) = ret_mh
        ret_mhv = ff.tab_all_mhv[useab](m, h, v)
        (crmax, trimax, trsmax, rfmax, ctmaxv, tmaxv, tlvlv, sfcv,
         vias) = ret_mhv
        if mon:
            debug(1, "gatk:  crmax=%.1f[m/s]  "
                  "trimax=%.1f[deg/s]  trsmax=%.1f[deg/s]  "
                  "nmin=%.2f  nmax=%.2f" %
                  (crmax, degrees(trimax), degrees(trsmax), nmin, nmax))

        # Alignment offset to target direction.
        batad = unitv(at.cross(ad))
        if batad.lengthSquared() > 0.5:
            sig_ad = at.signedAngleRad(ad, batad)
        else:
            sig_ad = 0.0
        release = False

        # Choose intercept or turn.
        if cq.inintc:
            sigout_hc = radians(60.0)
            #sigout_hc_p = sigout_hc
            if skill:
                sigout_hc *= intl01v(skill.awareness, 0.5, 1.0)
            #assert abs(sigout_hc_p - sigout_hc) < 1e-5
            if abs(sig_ad) > sigout_hc:
                cq.inintc = False
        else:
            sigin_hc = radians(30.0)
            #sigin_hc_p = sigin_hc
            if skill:
                sigin_hc *= intl01v(skill.awareness, 0.5, 1.0)
            #assert abs(sigin_hc_p - sigin_hc) < 1e-5
            tr = dq.tr
            #sigin_av = radians(60.0)
            #sigin_av += intl01vr(td, shd, 2.0 * shd, (td / (v / (tr or 1e-10))), 0.0)
            sigin_av = radians(90.0)
            #sigin_av_p = sigin_av
            if skill:
                sigin_av *= intl01v(skill.awareness, 0.5, 1.0)
            #assert abs(sigin_av_p - sigin_av) < 1e-5
            sigin_avn = radians(10.0)
            sig_av = acos(clamp(txit.dot(xit), -1.0, 1.0))
            if mon:
                debug(1, "gatk:  sig_ad=%.1f[deg]  sig_av=%.1f[deg]" %
                      (degrees(sig_ad), degrees(sig_av)))
            if (abs(sig_ad) < sigin_hc and
                (abs(sig_av) < sigin_av or abs(sig_av) > pi - sigin_avn)):
                cq.inintc = True

        if cq.inintc:
            # Control to intercept.

            # Time to next update limits.
            dtmumax = 2.0
            dtmumini = 0.2
            #dtmumini_p = dtmumini
            if skill:
                dtmumini *= intl01v(skill.piloting, 2.0, 1.0)
            #assert abs(dtmumini_p - dtmumini) < 1e-5
            dtmumino = dtmumax
            dtmumin = intc01vr(td, shd * 1.1, shd * 10.0, dtmumini, dtmumino)

            # Intercept direction.
            tant = unitv(tb)
            txib = unitv(txit.cross(tant))
            ru = tu - u
            rv = ru.dot(ad)
            ctm = 1.0
            #ctm_p = ctm
            if skill:
                ctm *= intl01v(skill.piloting, 2.0, 1.0)
            #assert abs(ctm_p - ctm) < 1e-5
            #if mon:
                #debug(1, "gatk-evd %s %s %s" % (td, rv, td - rv * ctm))
            if td + rv * ctm < 0.0 and abs(sig_av) > radians(170.0):
                dirch = "evade"
                dtint = 0.0
                evd = unitv(ad.cross(ez))
                #evd *= -sign(tu.dot(evd))
                if evd.length() < 1e-5:
                    evd = an
                eoff = 0.5 * shd
                dpi = dp + evd * eoff
                ati = Vec3D(unitv(dpi))
            #elif td > rv * 1.0 or txit.dot(xit) > 0.5:
            #elif td > rv * 1.0 and txit.dot(xit) > 0.5 and ad.dot(xit) > 0.5:
            elif True:
                dtm1 = 0.0 #-1 * dtm
                dp1 = dp + tu * dtm1 + tb * (0.5 * dtm1**2)
                tu1 = tu + tb * dtm1
                tb1 = tb
                shp = Point3D()
                sfu, sdup, sfb, sdbp, setm = shldf()
                dp1p = Point3D(dp1)
                ret = intercept_time(dp1p, tu1, tb1, shp, sfu, sdup, sfb, sdbp,
                                     finetime=setm, epstime=dtm, maxiter=5)
                if ret:
                    dtint, dpia, atia = ret
                    dtintmax = 2.0
                    if dtint < dtintmax:
                        dirch = "in-near"
                        dpi = dpia
                        ati = atia
                    else:
                        dpib = dp1 + tu1 * dtintmax
                        #rdt = (dtint - dtintmax) / dtintmax - 1.0
                        rdt = intl01r(dtint, dtintmax, dtintmax * 2.0)
                        if rdt < 1.0:
                            dirch = "in-mid"
                            dpi = dpia + (dpib - dpia) * rdt
                        else:
                            dirch = "in-far"
                            dpi = dpib
                        ati = Vec3D(unitv(dpi))
                else:
                    dtint = 0.0
                    dirch = "in-off"
                    dpi = dp1
                    ati = Vec3D(unitv(dpi))
            else:
                dirch = "out"
                #txith = unitv(Vec3D(txit[0], txit[1], 0.0))
                #dpi = dp - txith * shd
                dtint = 0.0
                dpi = dp
                ati = Vec3D(unitv(dpi))
            if mon:
                debug(1, "gatk:  td=%.0f[m]  dtint=%.2f[s]  dirch=%s" %
                      (td, dtint, dirch))
                debug(1, "gatk:  p=%s[m]  tp=%s[m]  dp=%s[m]  xit=%s  txit=%s" %
                      (vf(p, 0), vf(tp, 0), vf(dp, 0),
                       vf(xit, 3), vf(txit, 3)))
                debug(1, "gatk:  cao=%.2f[deg/s]  cro=%.2f[deg/s]  "
                      "ctlv=%.2f[1/s]" %
                      (degrees(cao), degrees(cro), ctlv))
            cq.dirch = dirch

            # Speed away from firing distance.
            v_a = intc01vr(td, shd, shd * 2.0, tu.dot(xit), tu.length())
            vmin_i = max(0.6 * v_a, 0.9 * voptts, vmin)
            vmax_i = min(1.4 * v_a, max(1.2 * v_a, 1.2 * voptti), vmax)
            if vmin_i > vmax_i:
                vmax_i = vmin_i
            td_eqv = shd * 0.8 # must be < 1.0
            v_i = clamp(v_a + 0.1 * (td - td_eqv), vmin_i, vmax_i)
            #v_i_p = v_i
            if skill:
                if cq.tm_bvi <= tm:
                    rdv_max = intl01v(skill.piloting, 0.2, 0.0)
                    cq.rdv_bvi = uniform(-rdv_max, rdv_max)
                    cq.tm_bvi = tm + intl01vr(td, shd * 1.0, shd * 5.0,
                                              cq.dtm_bvi_min, cq.dtm_bvi_max)
                dvi = v_i * cq.rdv_bvi
                v_i += dvi
            #assert abs(v_i_p - v_i) < 1e-5
            dtmc = 2.0 #!!!
            ct_i = (v_i - v) / dtmc
            #ctmax_i = 10.0 #!!!
            #ct_i = clamp((v_i - v) / dtmc, -ctmax_i, ctmax_i)
            if mon:
                debug(1, "gatk:  v_a=%.1f[m/s]  "
                      "voptti=%.1f[m/s]  voptts=%1f[m/s]  v_i=%.1f[m/s]" %
                      (v_a, voptti, voptts, v_i))

            w = m * g
            wt = -ez.dot(xit) * w
            q = 0.5 * rho * v**2
            ft_i = m * ct_i

            tmaxref = tmaxab if useab else tmax

            # Alignment offset to intercept direction.
            batati = unitv(at.cross(ati))
            if batati.lengthSquared() > 0.5:
                sig_ati = at.signedAngleRad(ati, batati)
            else:
                sig_ati = 0.0
            ati_b = unitv(ati - ab * ati.dot(ab))
            sig_atib = at.signedAngleRad(ati_b, ab)
            ati_n = unitv(ati - an * ati.dot(an))
            sig_atin = at.signedAngleRad(ati_n, an)
            thszref = 0.5 * (0.6 * tsz)
            sigmax_ati = atan(thszref / td)
            sigmax_ati *= intl01vr(sig_av, radians(45.0), radians(120.0),
                                   1.0, 3.0)
            romax_ati = radians(360.0)
            #romax_ati_p = romax_ati
            if skill:
                sigmax_ati *= intl01v(skill.aiming, 4.0, 1.0)
                romax_ati *= intl01v(skill.aiming, 0.2, 1.0)
            #assert abs(romax_ati_p - romax_ati) < 1e-5
            release = (dirch == "in-near" and td < shd and
                       abs(sig_ati) < sigmax_ati and abs(cro) < romax_ati)
            if mon:
                debug(1, "gatk:  at=%s  ati=%s  "
                      "sig_ati=%.3f[deg]  sigmax_ati=%.3f[deg]  "
                      "sig_atib=%.3f[deg]  sig_atin=%.3f[deg]  "
                      "release=%s" %
                      (vf(at), vf(ati), degrees(sig_ati), degrees(sigmax_ati),
                       degrees(sig_atib), degrees(sig_atin),
                       release))

            # Control to intercept direction.

            # Compute minimum and maximum acceptable angle of attack
            # at current distance, considering aerodynamic and power limits.
            nmin_i = max(nmin, -2.0)
            nmax_i = min(nmax, 9.0)
            # NOTE: dq.a* are freezes, do not move to top.
            anminr = dq.anmin
            anmaxr = dq.anmax
            amin_in = max(amin, anminr) if anminr is not None else amin
            amax_in = min(amax, anmaxr) if anmaxr is not None else amax
            atminr = dq.atminab if useab else dq.atmin
            atmaxr = dq.atmaxab if useab else dq.atmax
            shdi = shd * 4.0
            shdo = shd * 8.0
            sigi = radians(120.0)
            sigo = radians(180.0)
            #shdi_p = shdi; shdo_p = shdo
            #sigi_p = sigi; sigo_p = sigo
            if skill:
                shdi *= intl01v(skill.piloting, 0.3, 1.0)
                shdo *= intl01v(skill.piloting, 0.4, 1.0)
                sigi *= intl01v(skill.piloting, 0.3, 1.0)
                sigo *= intl01v(skill.piloting, 0.5, 1.0)
            #assert abs(shdi_p - shdi) < 1e-5 and abs(shdo_p - shdo) < 1e-5
            #assert abs(sigi_p - sigi) < 1e-5 and abs(sigo_p - sigo) < 1e-5
            amin_it = max(amin_in, atminr) if atminr is not None else amin_in
            amax_it = min(amax_in, atmaxr) if atmaxr is not None else amax_in
            ifac_atl = (intc10r(td, shdi, shdo) *
                        intc10r(abs(sig_atin), sigi, sigo))
            amin_i = amin_it + (amin_in - amin_it) * ifac_atl
            amax_i = amax_it + (amax_in - amax_it) * ifac_atl
            #amin_i = amin_in
            #amax_i = amax_in
            if mon:
                debug(1, "gatk:  amax=%.2f[deg]  "
                      "anmaxr=%.2f[deg]  atmaxr=%.2f[deg]  "
                      "ifac_atl=%.2f  amax_i=%.2f[deg]" %
                      (degrees(amax),
                       degrees(anmaxr or 0.0), degrees(atmaxr or 0.0),
                       ifac_atl, degrees(amax_i)))

            # Compute control for two possible rolls, current and inverted,
            # giving preference to current unless too high negative load
            # (and possibly some other finer criteria).
            # NOTE: m, v change slowly, so keep at current.
            da_i_s, dr_i_s, dtl_i_s, dbrd_i_s = None, None, None, None
            n_i_s, dalc_i_s, dtmsr_i_s = None, None, None
            for i_sg, sginv_i in enumerate((1, -1)):
                if mon:
                    debug(1, "gatk:  sginv_i=%+d" % sginv_i)

                # Compute roll delta to intercept direction.
                ant_sg = ant * sginv_i
                ant_sgxit = unitv(ant_sg - xit * ant_sg.dot(xit))
                dr_sg = ant.signedAngleRad(ant_sgxit, xit)
                ati_xit = unitv(ati - xit * ati.dot(xit))
                if ati_xit.lengthSquared() > 0.5:
                    dr_ib = ant_sgxit.signedAngleRad(ati_xit, xit)
                    brn_ib = 0
                else:
                    dr_ib = dr_sg
                    brn_ib = 1

                dr_iblim = intc01vr(td, shd, shd * 2.0, radians(5.0), radians(0.1))
                #dr_iblim = radians(1.0)

                # Dampen roll when target very near.
                dpi_ati_xit = dpi.dot(ati_xit)
                roff = thszref * intc01(abs(dr_ib) / dr_iblim) * sign(dr_ib)
                if abs(dpi_ati_xit) > abs(roff):
                    dr_sig = asin(roff / dpi_ati_xit)
                    if abs(dr_sig) < abs(dr_ib):
                        dr_is = dr_ib - dr_sig
                        brn_roff = 0
                    else:
                        dr_is = 0.0
                        brn_roff = 1
                else:
                    dr_sig = 0.0
                    dr_is = 0.0
                    brn_roff = 2

                #dr_sig = 0.0
                #dr_is = dr_ib
                #brn_roff = -1

                dr_i = dr_is

                #rot = QuatD()
                #rot.setFromAxisAngleRad(dr_i, xit)
                #ab_i = unitv(Vec3D(rot.xform(ab)))
                #rtu_ab_i = (tu - u).dot(ab_i)
                #dpi_ati_xit = dpi.dot(ati_xit)
                #if abs(dpi_ati_xit) > 1e-10:
                    #tcro_i = rtu_ab_i / dpi_ati_xit
                #else:
                    #tcro_i = 0.0
                #debug(1, "here70 %s %s %s %s %s %s" %
                      #(degrees(tcro_i), degrees(cro), degrees(ro),
                       #degrees(dr_i / dtmu), rtu_ab_i, dpi_ati_xit))
                #tcro_i = (tu - u).dot(ab_sg) / dpi_ati_xit
                tcro_i = 0.0

                # Compute pitch delta to intercept direction, after roll.
                rot_i = QuatD()
                rot_i.setFromAxisAngleRad(dr_i, xit)
                at_i = unitv(Vec3D(rot_i.xform(at)))
                ab_i = unitv(Vec3D(rot_i.xform(ab)))
                ati_ab = unitv(ati - ab_i * ati.dot(ab_i))
                if ati_ab.lengthSquared() > 0.5:
                    da_ib = at_i.signedAngleRad(ati_ab, ab_i)
                else:
                    da_ib = 0.0

                # If near release, correct pitch delta by achieved control
                # during previous cycle.
                cq.da_ib[i_sg] = da_ib
                da_sgb = da_ib - da_ib_p[i_sg] + dac
                ifac_sgb = (intc10r(td, shd * 0.8, shd * 1.1) *
                            intc10r(abs(sig_atin), radians(1.0), radians(5.0)))
                da_is = da_ib + da_sgb * ifac_sgb

                #tcao_i = (tu - u).dot(ant_sgxit) / dpi_ati_xit
                tcao_i = 0.0

                # Correct pitch delta according to limit angle of attack.
                a_i = a + da_is
                a_i_nc = a_i
                a_i = clamp(a_i, amin_i + radians(0.5), amax_i - radians(0.5))
                dalc_i = a_i_nc - a_i
                da_i = a_i - a

                # Compute throttle for target angle of attack and acceleration.
                ret = ff.resliftafp(amin, a1m, a0, a1, amax, sla, sla1, a_i, q)
                sl_i, l_i, slcd_i = ret
                sd_i = sd0 + ks * slcd_i**2
                d_i = q * sd_i
                t_i = (ft_i + d_i - wt) / (1.0 - 0.5 * a_i**2)
                t_i = clamp(t_i, 0.0, tmaxref)
                n_i = (l_i + t_i * a_i) / w
                tl_i = ff.restlth(t_i, tmax, tmaxab)
                dtl_i = tl_i - tl

                brd_i = AIRBRAKE.RETRACTED
                dbrd_i = brd_i - brd

                tctlv_i = 0.0

                if mon:
                    debug(1, "gatk:  da_ib=%.2f[deg]  da_sgb=%.2f[deg]  "
                          "da_is=%.2f[deg]  dr_ib=%.2f[deg]  roff=%.2f[m]  "
                          "dpi_ati_xit=%.2f[m]  dr_sig=%.2f[deg]  "
                          "dr_is=%.2f[deg]  brn_ib=%d  brn_roff=%d" %
                          (degrees(da_ib), degrees(da_sgb), degrees(da_is),
                           degrees(dr_ib), roff, dpi_ati_xit, degrees(dr_sig),
                           degrees(dr_is), brn_ib, brn_roff))
                    debug(1, "gatk:  da_i=%.2f[deg]  dr_i=%.2f[deg]  "
                          "dtl_i=%.2f[deg] dbrd_i=%.2f  "
                          "tcao_i=%.2f[deg/s]  tcro_i=%.2f[deg/s]  tctlv_i=%.2f[1/s]" %
                          (degrees(da_i), degrees(dr_i), dtl_i, dbrd_i,
                           degrees(tcao_i), degrees(tcro_i), tctlv_i))

                # Compute input program for control time criterion.
                ret = self.input_program_mintm(dr_i, cro, tcro_i, romax, rsmax,
                                               dtmeps=dtmeps)
                dtmdr_i, dtmsr_i = ret

                # Allow higher negative load if near release.
                ifac_nmr = (intc10r(td, shd, 2.0 * shd) *
                            intc10(abs(dr_i) / radians(10.0)))
                nmin_i_rc = max(nmin_i + (nmin - nmin_i) * ifac_nmr, -4.0)

                if (n_i_s is None or
                    (n_i > nmin_i_rc
                    #and n_i > nmin
                    #and abs(dalc_i) <= abs(dalc_i_s)
                    #and abs(dr_i) * abs(n_i - 1.0) < abs(dr_i_s) * abs(n_i_s - 1.0)
                    #and abs(dr_i) < abs(dr_i_s)
                    and dtmsr_i < dtmsr_i_s
                    )):
                    da_i_s, dr_i_s, dtl_i_s, dbrd_i_s = da_i, dr_i, dtl_i, dbrd_i
                    tcao_i_s, tcro_i_s, tctlv_i_s = tcao_i, tcro_i, tctlv_i
                    n_i_s, dalc_i_s, dtmsr_i_s = n_i, dalc_i, dtmsr_i
                if mon:
                    debug(1, "gatk:  n_i=%.2f  nmin_i_rc=%.2f  dalc_i=%.2f[deg]  "
                          "dtmsr_i=%.2f[s]" %
                          (n_i, nmin_i_rc, degrees(dalc_i), dtmsr_i))

            da, dr, dtl, dbrd = da_i_s, dr_i_s, dtl_i_s, dbrd_i_s
            tcao, tcro, tctlv = tcao_i_s, tcro_i_s, tctlv_i_s
            # skill: non-perfect da_i, dr_i, dtl_i?

            rfacdtmu = intc01vr(abs(sig_ati), 0.0, radians(30.0), 0.5, 0.9)

        else:
            # Control to turn.

            sig_ati = sig_ad

            # Time to next update limits.
            dtmumax = 2.0
            dtmumin = 1.0

            ##if cq.tm_tdec <= tm:
                ###txit = unitv(tu)
                ###tant = unitv(tb)
                ###if abs(tant.dot(ez)) < 0.5:
                    ###cq.sgtr = sign(txit.cross(tant).dot(ez))
                ###else:
                    ###cq.sgtr = sign(ez.cross(xit).dot(ad))
                ##cq.sgtr = sign(ez.cross(xit).dot(ad))
                ##cq.tm_tdec = tm + uniform(cq.dtm_tdec_min, cq.dtm_tdec_max)

            #cr = dq.cr
            #th = tp[2]
            #dth = -50.0
            #if skill:
                #dthu = 100.0
                #dth += (dthu - dth) * intl01v(skill.piloting, 0.0, 1.0)
            #h_hct = th + dth
            #dgh = 500.0
            #if skill:
                #dgh *= intl01v(skill.piloting, 2.0, 1.0)
            #h_hcg = gh + dgh
            #h_hc = max(h_hct, h_hcg)
            #atm = 5.0
            #crmaxref = crmax
            #if skill:
                #crmaxref *= intl01v(skill.piloting, 0.7, 1.0)
            #if h < h_hc:
                #cr_hc = min((h_hc - h) / atm, crmaxref, 0.9 * v)
            #else:
                #cr_hc = max((h_hc - h) / atm, -0.9 * v)

            #trmaxref = trimaxa
            #if skill:
                #trmaxref *= intl01v(skill.piloting, 0.7, 1.0)

            #cq.sgtr = sign(ez.cross(xit).dot(ad))
            #tr_hc = max(trmaxref, radians(1.0)) * cq.sgtr
            #xit_hc = xit

            ##xith = dq.xith
            ##txit = unitv(tu)
            ##txith = unitv(Vec3D(txit[0], txit[1], 0.0))
            ##adh = unitv(Vec3D(ad[0], ad[1], 0.0))
            ##adhs = adh * (adh.dot(txith) > 0.0 and 1.0 or -1.0)
            ##ang_irh = acos(clamp(adhs.dot(txith), -1.0, 1.0))
            ##r_hc = (0.5 * td) / (sin(ang_irh) or 1e-10)
            ##tr_hc = v / r_hc
            ##xit_hc = txith - adhs * (txith.dot(adhs) * 2)

            #cr_hc_p, tr_hc_p = cr_hc, tr_hc
            #ret = self.correct_turn_climb(cr_hc, tr_hc, crmaxref, trmaxref, wtcr=0.5)
            #cr_hc, tr_hc = ret
            ##dtmu_hc = max(10.0 / max(abs(cr_hc - cr), 1.0), dtmumini)
            #dtmu_hc = 1.0
            ##tth_hc = cr_hc / (v**2 - cr_hc**2)**0.5
            #r_hct = v / tr_hc
            #if cr_hc > cr:
                #nmax_hcp = min(nmax, 6.0)
                #nmax_hcpc = intc01vr(cr_hc - cr, 0.0, 30.0, 1.1, nmax_hcp)
                #r_hcp = v**2 / ((nmax_hcpc - 1.0) * g)
            #else:
                #nmin_hcp = max(nmin, -2.5)
                #nmin_hcpc = intc01vr(cr_hc - cr, 0.0, -30.0, 0.9, nmin_hcp)
                #r_hcp = v**2 / ((nmin_hcpc - 1.0) * g)

            nmax_hc = min(nmax, 9.0)
            nmin_hc = max(nmin, -2.5)

            crmaxref = crmax

            trmaxref = trimaxa
            #trmaxref_p = trmaxref
            if skill:
                trmaxref *= intl01v(skill.piloting, 0.7, 1.0)
            #assert abs(trmaxref_p - trmaxref) < 1e-5

            hdg = dq.hdg
            thdg = atan2(-ad.getX(), ad.getY())
            dhdg = norm_ang_delta(hdg, thdg)

            #dtmu_ti = clamp((td - shd) / v, 0.0, dtmumax)
            dtmu_ti = dtmumax
            dp_ti = dp + tu * dtmu_ti + tb * (0.5 * dtmu_ti**2)
            ad_ti = Vec3D(unitv(dp_ti))
            thdg_ti = atan2(-ad_ti.getX(), ad_ti.getY())
            dhdg_ti = norm_ang_delta(hdg, thdg_ti)
            dhdg = intl01vr(abs(dhdg), radians(60.0), radians(120.0), dhdg, dhdg_ti)

            #if cq.tm_rtdec <= tm:
                #cq.rtdec_inv = False
                #if cq.rtdec_last_dhdg is not None:
                    #if abs(dhdg) > radians(90.0):
                        #if abs(dhdg) > abs(cq.rtdec_last_dhdg):
                            #cq.rtdec_inv = True
                #dtm_rt = uniform(cq.dtm_rtdec_min, cq.dtm_rtdec_max)
                #if skill:
                    #dtm_rt *= intl01v(skill.awareness, 3.0, 1.0)
                #cq.tm_rtdec = tm + dtm_rt
                #cq.rtdec_last_dhdg = dhdg
            #if abs(dhdg) < radians(90.0):
                #cq.rtdec_inv = False
            #if cq.rtdec_inv:
                #dhdg += 2 * pi * (1 if dhdg < 0.0 else -1)

            trimax_hcn = g * (nmax_hc**2 - 1.0)**0.5 / v
            trimax_hc = min(trimax, trimax_hcn)
            dtmc_hc = dtmumax
            tr_hc = clamp(dhdg / dtmc_hc, -trimax_hc, trimax_hc)

            #v_hca = intc01vr(td, shd * 0.5, shd * 2.0, tu.dot(xit), tu.length())
            ##v_hca = tu.length()
            ##vmin_hc = max(0.6 * v_hca, 0.9 * voptts, vmin)
            #vmin_hc = max(0.8 * voptts, vmin)
            ##vmax_hc = min(1.4 * v_hca, max(1.2 * v_hca, 1.2 * voptti), vmax)
            #vmax_hc = vmax
            #if vmin_hc > vmax_hc:
                #vmax_hc = vmin_hc
            #v_hc = clamp(v_hca + 0.1 * (td - shd), vmin_hc, vmax_hc)

            v_tr = intl01vr(td, 1.5 * shd, 3.0 * shd, voptts, voptti)
            vmin_ci = max(0.8 * voptts, vmin)
            vmax_ci = vmax
            v_ci0 = intc01vr(td, shd * 0.5, shd * 2.0, tu.dot(xit), tu.length())
            v_ci = clamp(v_ci0 + 0.1 * (td - shd), vmin_ci, vmax_ci)
            sig_av = acos(clamp(txit.dot(xit), -1.0, 1.0))
            v_hc = intl01vr(sig_av, radians(60.0), radians(90.0), v_ci, v_tr)

            dtmc_hcv = 2.0 #!!!
            ct_hc = (v_hc - v) / dtmc_hcv

            th = tp[2]
            dth = 0.0
            #dth_p = dth
            if skill:
                dthu = 100.0
                dth += (dthu - dth) * intl01v(skill.piloting, 1.0, 0.0)
            #assert abs(dth_p - dth) < 1e-5
            h_hct = th + dth
            dgh = 500.0
            #dgh_p = dgh
            if skill:
                dgh *= intl01v(skill.piloting, 2.0, 1.0)
            #assert abs(dgh_p - dgh) < 1e-5
            h_hcg = gh + dgh
            h_hc = max(h_hct, h_hcg)
            tht_hc = atan2(h_hc - h, td)
            cr = dq.cr
            cr_hc = v_hc * sin(tht_hc)

            cr_hc_p, tr_hc_p = cr_hc, tr_hc
            ret = self.correct_turn_climb(cr_hc, tr_hc, crmaxref, trmaxref, wtcr=0.5)
            cr_hc, tr_hc = ret

            tht = dq.tht
            tht_hc = asin(clamp(cr_hc / v_hc, -0.99, 0.99))
            dtht = tht_hc - tht
            n_hcp = nmax_hc if dtht > 0.0 else nmin_hc
            r_hcp = abs(v**2 / ((n_hcp - 1.0) * g))
            r_hcpb = abs(v * dtmc_hc / (dtht or 1e-10))
            r_hcp = max(r_hcp, r_hcpb)
            r_hcp *= sign(dtht) or 1

            r_hct = abs(v / tr_hc) if abs(tr_hc) > 1e-5 else 1e30
            n_hct = (v**2 / (r_hct * g))**2 + 1.0
            r_hctb = abs(v * dtmc_hc / (dhdg or 1e-10))
            r_hct = max(r_hct, r_hctb)

            path = ArcedHelixZ(r_hct, dhdg, r_hcp, Vec3D(), xit)
            xit_hc = path.tangent(0.0)
            xin_hc = path.normal(0.0)
            r_hc = path.radius(0.0)
            #xit_hc = unitv(xith + ez * tth_hc)
            #xin_hc = unitv(ez.cross(xit_hc))
            ##xin_hc *= sign(xin_hc.dot(ad))
            #v_hc_p = v_hc
            if skill:
                v_hc *= intl01v(skill.piloting, 0.8, 1.0)
            #assert abs(v_hc_p - v_hc) < 1e-5
            tmaxref = tmaxab if useab else tmax
            nmin_hc = max(nmin, -2.5)
            fdir_hc = 1
            ret = self.diff_to_path_tnr(dq, xit_hc, xin_hc, r_hc,
                                        v_hc, ct_hc, tmaxref=tmaxref,
                                        nmininv=nmin_hc, facedir=fdir_hc,
                                        bleedv=True, bleedr=True)
            da_hc, dr_hc, dtl_hc, dbrd_hc = ret[:4]
            if da_hc is None:
                da_hc, dr_hc, dtl_hc, dbrd_hc = 0.0, 0.0, 0.0, 0.0
                if mon:
                    debug(1, "gatk:  cannot resolve turn")
            if mon:
                debug(1, "gatk:  td=%.0f[m]  h_hc=%.0f[m]  h=%.0f[m]  "
                      "cr_hc_p=%.1f[m/s]  cr_hc=%.1f[m/s]  "
                      "tr_hc_p=%.1f[m/s]  tr_hc=%.1f[m/s]  "
                      "r_hct=%.0f[m]  r_hcp=%.0f[m]" %
                      (td, h_hc, h, cr_hc_p, cr_hc,
                       degrees(tr_hc_p), degrees(tr_hc),
                       r_hct, r_hcp))
            if mon:
                debug(1, "gatk:  "
                      "cr=%.1f[m/s]  cr_hc=%.1f[m/s]  tr_hc=%.1f[deg/s]  "
                      "xit_hc=%s  xin_hc=%s  fdir_hc=%d" %
                      (cr, cr_hc, degrees(tr_hc),
                       vf(xit_hc), vf(xin_hc), fdir_hc))

            da, dr, dtl, dbrd = da_hc, dr_hc, dtl_hc, dbrd_hc
            tcao, tcro, tctlv = 0.0, 0.0, 0.0
            # skill: non-perfect da_hc, dr_hc, dtl_hc?

            rfacdtmu = 1.0

        if mon:
            debug(1, "gatk:  inintc=%s  "
                  "da=%.2f[deg]  dr=%.2f[deg]  dtl=%.2f  dbrd=%.2f  "
                  "tcao=%.2f[deg/s]  tcro=%.2f[deg/s]  tctlv=%.2f[1/s]" %
                  (cq.inintc, degrees(da), degrees(dr), dtl, dbrd,
                   degrees(tcao), degrees(tcro), tctlv))

        pomax1 = pomax
        #pomax1 = pomax * min(abs(da / (amax - amin)), 1.0)
        psmax1 = psmax
        #psmax1 = min(pomax1 / (dtmumin * 0.5), psmax)

        romax1 = romax
        #romax1 = romax * min(abs(dr / (pi * 1.0)), 1.0)
        rsmax1 = rsmax
        #rsmax1 = min(romax1 / (dtmumin * 0.5), rsmax)

        tlvmax1 = tlvmax
        #tlcmax1 = min(tlvmax / (dtmu * 2.0), tlcmax)
        tlcmax1 = tlcmax

        brdvmax1 = brdvmax

        ret = self.input_program(cq,
                                 da, cao, tcao, pomax1, psmax1,
                                 dr, cro, tcro, romax1, rsmax1,
                                 dtl, ctlv, tctlv, tlvmax1, tlcmax1,
                                 dbrd, brdvmax,
                                 dtmumin, dtmumax, rfacdtmu, dtmeps,
                                 mon=mon)

        cq.dtmu = ret[0]

        if mon:
            debug(1, "gatk ==================== end")

        return ret + (sig_ati, release)


    def diff_to_path_gtrk (self, cq, dq, tm, dtm, gh,
                           tp, tu, tb, tant, tsz, shd, shldf, freeab,
                           skill=None, mon=False):

        vec = Vec3D

        if mon:
            debug(1, "gtrk ==================== start")
            vf = lambda v, d=6: "(%s)" % ", ".join(("%% .%df" % d) % e for e in v)

        ff, ad, pd = self, self, self

        m, p, u, b, an, tl, phi = dq.m, dq.p, dq.u, dq.b, dq.an, dq.tl, dq.phi
        brd = dq.brd

        ez = vec(0.0, 0.0, 1.0)

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks
        mref, nmaxref = pd.mref, pd.nmaxref
        nmin, nmax = ff.resnmax(mref, nmaxref, m)
        pomax, romax, tlvmax = dq.pomax, dq.romax, dq.tlvmax
        psmax, rsmax, tlcmax = dq.psmax, dq.rsmax, dq.tlcmax
        brdvmax = dq.brdvmax

        a = dq.a
        at, an, ab, ant = dq.at, dq.an, dq.ab, dq.ant
        xit, xin, xib = dq.xit, dq.xin, dq.xib
        ao, ro, tlv = dq.ao, dq.ro, dq.tlv
        if not cq.inited:
            cq.inited = True
            cq.ao, cq.ro, cq.tlv = ao, ro, tlv
            cq.dtmu = 0.0
            cq.dac, cq.drc = 0.0, 0.0
            cq.da_base, cq.dr_base = 0.0, 0.0
        cao, cro, ctlv = cq.ao, cq.ro, cq.tlv
        dac, drc = cq.dac, cq.drc
        dtmu = cq.dtmu

        # Target position and attitude.
        th = tp[2]
        dh = th - h
        tv = tu.length()
        txit = unitv(tu)
        tbn = tb - txit * tb.dot(txit)
        tcn = tbn.length()
        txin = unitv(tbn)
        trd = tv**2 / (tcn + 1e-10)
        ttr = tv / (trd + 1e-10)
        txib = txit.cross(txin)
        dp = tp - p
        td = dp.length()
        if mon:
            debug(1, "gtrk:  td=%.0f[m]  dh=%.0f[m]  "
                  "tv=%.2f[m/s]  ttr=%.1f[deg/s]" %
                  (td, dh, tv, degrees(ttr)))

        # Target direction.
        ad = unitv(vec(dp))
        ad_atn = unitv(ad - ab * ad.dot(ab))
        ad_atb = unitv(ad - an * ad.dot(an))
        sig_atn = at.signedAngleRad(ad_atn, ab)
        sig_atb = at.signedAngleRad(ad_atb, an)
        ad_xitn = unitv(ad - xib * ad.dot(xib))
        ad_xitb = unitv(ad - xin * ad.dot(xin))
        sig_xitn = xit.signedAngleRad(ad_xitn, xib)
        sig_xitb = xit.signedAngleRad(ad_xitb, xin)
        if mon:
            debug(1, "gtrk:  "
                  "sig_atn=%.1f[deg]  sig_atb=%.1f[deg]  "
                  "sig_xitn=%.1f[deg]  sig_xitb=%.1f[deg]" %
                  (degrees(sig_atn), degrees(sig_atb),
                   degrees(sig_xitn), degrees(sig_xitb)))

        # Target cannon intercept direction.
        sfu, sdup, sfb, sdbp, setm = shldf()
        ret = intercept_time(tp, tu, tb, p, sfu, sdup, sfb, sdbp,
                             finetime=setm, epstime=dtm, maxiter=5)
        if not ret:
            debug(1, "gtrk:  nointc")
            ret = 0.0, tp, unitv(dp)
        dtint, tp1, adi = ret
        adi_atn = unitv(adi - ab * adi.dot(ab))
        adi_atb = unitv(adi - an * adi.dot(an))
        sig_atni = at.signedAngleRad(adi_atn, ab)
        sig_atbi = at.signedAngleRad(adi_atb, an)
        batadi = unitv(at.cross(adi))
        if batadi.lengthSquared() > 0.5:
            sig_adi = at.signedAngleRad(adi, batadi)
        else:
            sig_adi = 0.0
        thszref = 0.5 * (0.6 * tsz)
        sigmax_adi = atan(thszref / td)
        romax_adi = radians(900.0)
        release = (td < shd and abs(sig_adi) < sigmax_adi and
                   abs(cro) < romax_adi)
        if mon:
            debug(1, "gtrk:  "
                  "sig_atni=%.2f[deg]  sig_atbi=%.2f[deg]  "
                  "sig_adi=%.2f[deg]  sigmax_adi=%.2f[deg]  "
                  "release=%s" %
                  (degrees(sig_atni), degrees(sig_atbi),
                   degrees(sig_adi), degrees(sigmax_adi),
                   release))

        # Performance limits.
        # NOTE: Quantity set and ordering as returned by comp_env.
        useab = True and pd.hasab
        ret_mh = ff.tab_all_mh[useab](m, h)
        (vmin, vmax, crmaxa, voptc, trimaxa, trsmaxa, voptti, voptts,
         rfmaxa, voptrf, tloptrf) = ret_mh
        ret_mhv = ff.tab_all_mhv[useab](m, h, v)
        (crmax, trimax, trsmax, rfmax, ctmaxv, tmaxv, tlvlv, sfcv,
         vias) = ret_mhv
        if mon:
            debug(1, "gtrk:  crmax=%.1f[m/s]  "
                  "trimax=%.1f[deg/s]  trsmax=%.1f[deg/s]  "
                  "nmin=%.2f  nmax=%.2f" %
                  (crmax, degrees(trimax), degrees(trsmax),
                   nmin, nmax))

        # Angle of attack limits.
        # Note: dq.a* are freezes.
        a_min_i = dq.anmin if dq.anmin is not None else amin
        a_max_i = dq.anmax if dq.anmax is not None else amax
        #a_min_s = dq.atminab if dq.atminab is not None else amin
        #a_max_s = dq.atmaxab if dq.atmaxab is not None else amax
        a_min = a_min_i
        a_max = a_max_i

        # Roll delta to intercept-vertical plane.
        # Two possible, pick the one nearer to target's path-up.
        adi_xnb = unitv(adi - xit * adi.dot(xit))
        tant_xnb = unitv(tant - xit * tant.dot(xit))
        max_tant_dot_adi = -1.1 # < -1
        for sg in (1, -1):
            adi_xnb_sg = adi_xnb * sg
            tant_dot_adi = adi_xnb_sg.dot(tant_xnb)
            if max_tant_dot_adi < tant_dot_adi:
                max_tant_dot_adi = tant_dot_adi
                dr_i = ant.signedAngleRad(adi_xnb_sg, xit)
        dr = dr_i

        # Correct roll delta by achieved control in previous cycle.
        ddr_cc = dr - cq.dr_base + drc
        cq.dr_base = dr
        dr_cc = intc01vr(abs(sig_atbi), sigmax_adi, sigmax_adi + radians(30.0),
                         dr + ddr_cc, dr)

        if mon:
            debug(1, "gtrk:  "
                  "dr_i=%.2f[deg]  dr_cc=%.2f[deg]" %
                  (degrees(dr_i), degrees(dr_cc)))

        # Pitch delta to intercept-horizontal plane, after roll.
        rot = QuatD()
        rot.setFromAxisAngleRad(dr, xit)
        at_ar = unitv(Vec3D(rot.xform(at)))
        ab_ar = unitv(Vec3D(rot.xform(ab)))
        da_ar = at_ar.signedAngleRad(adi, ab_ar)
        da = da_ar

        # Correct pitch delta for far roll.
        da_fr = intl01vr(abs(dr), sigmax_adi, sigmax_adi + radians(60.0),
                         da, 0.0)
        da = da_fr

        # Correct pitch delta for limit angle of attack.
        a_lc = clamp(a + da, a_min + radians(0.5), a_max - radians(0.5))
        da_lc = a_lc - a
        da = da_lc

        # Correct pitch delta by achieved control in previous cycle.
        dda_cc = da - cq.da_base + dac
        cq.da_base = da
        da_cc = intc01vr(abs(sig_atni), sigmax_adi, sigmax_adi + radians(5.0),
                         da + dda_cc, da)
        da = da_cc

        if mon:
            debug(1, "gtrk:  "
                  "da_ar=%.2f[deg]  da_fr=%.2f[deg]  da_lc=%.2f[deg]  "
                  "da_cc=%.2f[deg]" %
                  (degrees(da_ar), degrees(da_fr), degrees(da_lc),
                   degrees(da_cc)))

        # Target acceleration.
        v_a = intc01vr(td, shd * 1.0, shd * 2.0, tu.dot(xit), tu.length())
        vmin_i = max(0.6 * v_a, 0.9 * voptts, vmin)
        vmax_i = min(1.4 * v_a, max(1.2 * v_a, 1.2 * voptti), vmax)
        if vmin_i > vmax_i:
            vmax_i = vmin_i
        td_eqv = shd * 0.3 # must be < 1.0
        v_i = clamp(v_a + 0.1 * (td - td_eqv), vmin_i, vmax_i)
        dtmc = 2.0
        ct_i = (v_i - v) / dtmc

        # Throttle delta for target angle of attack and acceleration.
        a_i = da
        q = 0.5 * rho * v**2
        ret = ff.resliftafp(amin, a1m, a0, a1, amax, sla, sla1, a_i, q)
        sl_i, l_i, slcd_i = ret
        sd_i = sd0 + ks * slcd_i**2
        d_i = q * sd_i
        w = m * g
        wt = -ez.dot(xit) * w
        ft_i = m * ct_i
        t_i = (ft_i + d_i - wt) / (1.0 - 0.5 * a_i**2)
        tmaxref = tmaxab if useab else tmax
        t_i = clamp(t_i, 0.0, tmaxref)
        n_i = (l_i + t_i * a_i) / w
        tl_i = ff.restlth(t_i, tmax, tmaxab)
        dtl_i = tl_i - tl

        dtl = dtl_i

        if mon:
            debug(1, "gtrk:  "
                  "v=%.1f[m/s]  v_i=%.1f[m/s]  ct_i=%.2f[m/s^2]  dtl_i=%.4f" %
                  (v, v_i, ct_i, dtl_i))

        # Air brake.
        brd_i = AIRBRAKE.RETRACTED
        dbrd = brd_i - brd

        #xib1 = unitv(ad.cross(txin))
        ##xit1 = unitv(xit - xib1 * xit.dot(xib1))
        #xit1 = xit
        #xin1 = unitv(xib1.cross(xit1))
        #rd1 = trd * 0.9

        #v1 = tv * 1.2
        #dtmc = 2.0 #!!!
        #ct1 = (v1 - v) / dtmc

        #tmaxref = tmaxab #if useab else tmax
        #nmin1 = max(nmin, -2.5)
        #fdir1 = 1
        #ret = self.diff_to_path_tnr(dq, xit1, xin1, rd1,
                                    #v1, ct1, tmaxref=tmaxref,
                                    #nmininv=nmin1, facedir=fdir1,
                                    #bleedv=True, bleedr=True)
        #da, dr, dtl, dbrd = ret[:4]
        #if da is None:
            #da, dr, dtl, dbrd = 0.0, 0.0, 0.0, 0.0
            #if mon:
                #debug(1, "gtrk:  noturn")

        if mon:
            debug(1, "gtrk:  "
                  "da=%.2f[deg]  dr=%.2f[deg]  dtl=%.2f  dbrd=%.2f" %
                  (degrees(da), degrees(dr), dtl, dbrd))

        tcao, tcro, tctlv = 0.0, 0.0, 0.0

        pomax1 = pomax; psmax1 = psmax
        romax1 = romax; rsmax1 = rsmax
        tlvmax1 = tlvmax; tlcmax1 = tlcmax
        brdvmax1 = brdvmax

        #dtmumin, dtmumax = 0.5, 1.0
        dtmumin, dtmumax = 0.2, 0.4
        #dtmumin, dtmumax = 0.1, 0.2
        rfacdtmu = 1.0 # must be 1.0, for the correction by achieved control
        dtmeps = dtm * 1e-2

        ret = self.input_program(cq,
                                 da, cao, tcao, pomax1, psmax1,
                                 dr, cro, tcro, romax1, rsmax1,
                                 dtl, ctlv, tctlv, tlvmax1, tlcmax1,
                                 dbrd, brdvmax,
                                 dtmumin, dtmumax, rfacdtmu, dtmeps,
                                 mon=mon)

        cq.dtmu = ret[0]

        if mon:
            debug(1, "gtrk ==================== end")

        return ret + (sig_adi, release)


    def diff_to_path_mevd (self, cq, dq, tm, dtm, gh,
                           mp, mu, mb, freeab,
                           skill=None, mon=False):

        vec = Vec3D

        if mon:
            debug(1, "mevd ==================== start")
            vf = lambda v, d=6: "(%s)" % ", ".join(("%% .%df" % d) % e for e in v)

        ff, ad, pd = self, self, self

        # State.
        m, p, u, b, an, tl, phi = dq.m, dq.p, dq.u, dq.b, dq.an, dq.tl, dq.phi

        h = p[2]
        v = u.length()
        g, rho, rhofac, pr, prfac, vsnd = ff.resatm(h)
        ma = v / vsnd
        tmaxz, tmaxabz = pd.tmaxz, pd.tmaxabz
        tmax1, tmaxab1 = ff.restmaxh(tmaxz, tmaxabz, h, rho, vsnd)
        (vsd0cr, vsd0sp, vsd0spab, sd0cr, sd0sp, sd0spab,
         dsd0br, dsd0lg) = ff.reshvsd(h)
        tmax, tmaxab = ff.restmaxv(h, vsnd, vsd0sp, vsd0spab, tmax1, tmaxab1, v)
        a0z, amaxz, a1z, slaz, sla1z = pd.a0z, pd.amaxz, pd.a1z, pd.slaz, pd.sla1z
        amin, a1m, a0, a1, amax, sla, sla1 = (
            ff.ressla(a0z, a1z, amaxz, slaz, sla1z, ma))
        sd0, = (
            ff.ressd0(vsnd, vsd0cr, vsd0sp, vsd0spab,
                      sd0cr, sd0sp, sd0spab, v, ma))
        ks = pd.ks
        mref, nmaxref = pd.mref, pd.nmaxref
        nmin, nmax = ff.resnmax(mref, nmaxref, m)
        pomax, romax, tlvmax = dq.pomax, dq.romax, dq.tlvmax
        psmax, rsmax, tlcmax = dq.psmax, dq.rsmax, dq.tlcmax
        brdvmax = dq.brdvmax

        at, an, ab = dq.at, dq.an, dq.ab
        xit, xin, xib = dq.xit, dq.xin, dq.xib
        ao, ro, tlv = dq.ao, dq.ro, dq.tlv
        if not cq.inited:
            cq.inited = True
            cq.ao, cq.ro, cq.tlv = ao, ro, tlv
            #cq.dac = 0.0
            cq.dtmu = 0.0
            cq.state = 0
        cao, cro, ctlv = cq.ao, cq.ro, cq.tlv
        #dac = cq.dac
        dtmu = cq.dtmu

        # Performance limits.
        # NOTE: Quantity set and ordering as returned by comp_env.
        tdab = 5000.0 #!!!
        useab = int(freeab and pd.hasab)
        ret_mh = ff.tab_all_mh[useab](m, h)
        (vmin, vmax, crmaxa, voptc, trimaxa, trsmaxa, voptti, voptts,
         rfmaxa, voptrf, tloptrf) = ret_mh
        ret_mhv = ff.tab_all_mhv[useab](m, h, v)
        (crmax, trimax, trsmax, rfmax, ctmaxv, tmaxv, tlvlv, sfcv,
         vias) = ret_mhv
        rdimin = v / trimax; rdsmin = v / trsmax
        if mon:
            debug(1, "mevd:  crmax=%.1f[m/s]  "
                  "trimax=%.1f[deg/s]  trsmax=%.1f[deg/s]  "
                  "rdimin=%.0f[m]  rdsmin=%.0f[m]  "
                  "nmin=%.2f  nmax=%.2f" %
                  (crmax, degrees(trimax), degrees(trsmax),
                   rdimin, rdsmin, nmin, nmax))

        # Logic.
        dtmumax = 1.0
        dtmumin = 0.5
        ez = Vec3D(0.0, 0.0, 1.0)
        dp = p - mp
        md = dp.length()
        mxit = unitv(mu)
        #ad = unitv(vec(dp))
        ad = mxit
        adh = unitv(ad - ez * ad.dot(ez))
        if cq.state == 0:
            mv = mu.length()
            aot1 = radians(90.0)
            xith = unitv(xit - ez * xit.dot(ez))
            aot = acos(clamp(adh.dot(xith), -1.0, 1.0))
            #tmi = v / (mv * trimax) # for aot1 = 90 [deg]
            #extf = intl01vr(abs(aot - aot1), 0.0, radians(90.0), 1.0, 4.0)
            #limmd = (tmi * extf + dtmumax) * mv
            r = v / (trimax * 0.9)
            daot1 = aot1 - aot
            sgaot = sign(daot1) or 1
            rmd = ((mv * (daot1) - v) / trimax) * sgaot
            limmd = sqrt(r**2 + rmd**2 - 2 * r * rmd * cos(daot1 * sgaot))
            mvr = (mu - u).length()
            limmd += dtmumax * mvr
            if md > limmd:
                rot = QuatD()
                xib1 = -unitv(xith.cross(adh)) * sgaot
                rot.setFromAxisAngleRad(daot1, xib1)
                xit1 = unitv(vec(rot.xform(xith)))
                xin1 = unitv(xib1.cross(xit1))
                tr = trsmax * intl01r(abs(aot1 - aot), 0.0, trsmax * 1.0)
                rd1 = v / tr
                v1 = voptti
                ct1 = 0.0
            else:
                xib1t = unitv(ad.cross(xit))
                xib1 = ez * (sign(ez.dot(xib1t)) or 1)
                if mxit.dot(xit) < 0.0:
                    xib1 *= -1
                cq.xib1 = xib1
                cq.state = 1
            #debug(1, "mevd51 %s %s %s %s %s %s" %
                  #(v, voptti, degrees(aot), degrees(aot1), md, limmd))
        if cq.state == 1:
            xib1 = cq.xib1
            xin1 = -adh
            xit1 = unitv(xin1.cross(xib1))
            rd1 = v / trimax
            v1 = v
            ct1 = 0.0
            #debug(1, "mevd52 %s %s %s" %
                  #(degrees(dq.tr), degrees(trimax), degrees(trimaxa))

        # Target controls.
        tmaxref = tmaxab
        nmin1 = max(nmin, -4.0)
        fdir1 = 1
        ret = self.diff_to_path_tnr(dq, xit1, xin1, rd1, v1, ct1,
                                    tmaxref=tmaxref,
                                    nmininv=nmin1, facedir=fdir1,
                                    bleedv=True, bleedr=True)
        da, dr, dtl, dbrd = ret[:4]
        if da is None:
            da, dr, dtl, dbrd = 0.0, 0.0, 0.0, 0.0
            if mon:
                debug(1, "mevd:  noturn")

        if mon:
            debug(1, "mevd:  "
                  "da=%.2f[deg]  dr=%.2f[deg]  dtl=%.2f  dbrd=%.2f" %
                  (degrees(da), degrees(dr), dtl, dbrd))

        tcao, tcro, tctlv = 0.0, 0.0, 0.0

        # Actual controls.
        pomax1 = pomax; psmax1 = psmax
        romax1 = romax; rsmax1 = rsmax
        tlvmax1 = tlvmax; tlcmax1 = tlcmax
        brdvmax1 = brdvmax

        rfacdtmu = 0.9
        dtmeps = dtm * 1e-2

        ret = self.input_program(cq,
                                 da, cao, tcao, pomax1, psmax1,
                                 dr, cro, tcro, romax1, rsmax1,
                                 dtl, ctlv, tctlv, tlvmax1, tlcmax1,
                                 dbrd, brdvmax,
                                 dtmumin, dtmumax, rfacdtmu, dtmeps,
                                 mon=mon)

        cq.dtmu = ret[0]

        if mon:
            debug(1, "mevd ==================== end")

        return ret


    @staticmethod
    def input_program (cq,
                       da, cao, tcao, pomax, psmax,
                       dr, cro, tcro, romax, rsmax,
                       dtl, ctlv, tctlv, tlvmax, tlcmax,
                       dbrd, brdvmax,
                       dtmumin, dtmumax, rfacdtmu, dtmeps,
                       mon=False):

        def getca ():
            return cq.dtmca, cq.dac, cq.ao
        def setca (dtmca, dac, ao):
            cq.dtmca, cq.dac, cq.ao = dtmca, dac, ao
        def getcr ():
            return cq.dtmcr, cq.drc, cq.ro
        def setcr (dtmcr, drc, ro):
            cq.dtmcr, cq.drc, cq.ro = dtmcr, drc, ro
        def getctl ():
            return cq.dtmctl, cq.dtlc, cq.tlv
        def setctl (dtmctl, dtlc, tlv):
            cq.dtmctl, cq.dtlc, cq.tlv = dtmctl, dtlc, tlv
        def getcbrd ():
            return cq.dtmcbrd, cq.dbrdc
        def setcbrd (dtmcbrd, dbrdc):
            cq.dtmcbrd, cq.dbrdc = dtmcbrd, dbrdc

        tcls = PlaneDynamics

        ret = tcls.input_program_mintm(da, cao, tcao, pomax, psmax,
                                       getca, setca, dtmeps)
        inpfa, dtmda, dtmsa = ret
        dtmsa_mt = dtmsa

        ret = tcls.input_program_mintm(dr, cro, tcro, romax, rsmax,
                                       getcr, setcr, dtmeps)
        inpfr, dtmdr, dtmsr = ret
        dtmsr_mt = dtmsr

        ret = tcls.input_program_mintm(dtl, ctlv, tctlv, tlvmax, tlcmax,
                                       getctl, setctl, dtmeps)
        inpftl, dtmdtl, dtmstl = ret
        dtmstl_mt = dtmstl

        dtmu = clamp(max(dtmda, dtmdr), dtmumin, dtmumax)

        dtmsu = dtmu * rfacdtmu

        if dtmsa < dtmsu:
            ret = tcls.input_program_settm(da, cao, tcao, pomax, psmax, dtmsu,
                                           getca, setca)
            inpfa, dtmda, dtmsa = ret

        if dtmsr < dtmsu:
            ret = tcls.input_program_settm(dr, cro, tcro, romax, rsmax, dtmsu,
                                           getcr, setcr)
            inpfr, dtmdr, dtmsr = ret

        if dtmstl < dtmsu:
            ret = tcls.input_program_settm(dtl, ctlv, tctlv, tlvmax, tlcmax,
                                           dtmsu, getctl, setctl)
            inpftl, dtmdtl, dtmstl = ret

        ret = tcls.input_program_constv(dbrd, brdvmax,
                                        getcbrd, setcbrd)
        inpfbrd, dtmbrd = ret

        if mon:
            debug(1, "inpprg:  dtmu=%.2f[s]  "
                  "dtmsa_mt=%.2f[s]  dtmsr_mt=%.2f[s]  dtmstl_mt=%.2f[s]" %
                  (dtmu, dtmsa_mt, dtmsr_mt, dtmstl_mt))

        return dtmu, inpfa, inpfr, inpftl, inpfbrd


    @staticmethod
    def input_program_mintm (dit, v0, v1, vmax, cmax,
                             getc=None, setc=None, dtmeps=0.0, mon=False):

        if mon:
            debug(1, "inpprgmt40 %s %s %s %s %s" %
                  (degrees(dit), degrees(v0), degrees(v1), degrees(vmax),
                   degrees(cmax)))

        inppack = []

        for s in (1, -1):
            c = s * cmax
            k2 = c**2
            k1 = 2.0 * c * (v0 + v1)
            k0 = -(v1 - v0)**2 - 4.0 * c * dit
            for dtms in solve_quad(k2, k1, k0):
                if dtms is not None:
                    dtma = 0.5 * (dtms + (v1 - v0) / c)
                    va = v0 + c * dtma
                    if mon:
                        debug(1, "inpprgmt45 %s %s %s %s %s" %
                              (0.0, dtma, dtms, degrees(va), degrees(c)))
                        #debug(1, "inpprgmt46  %s %s" %
                              #(v1 - (v0 + c * dtma - c * (dtms - dtma)),
                               #dit - (v0 * dtma + 0.5 * c * dtma**2 + (v0 + c * dtma) * (dtms - dtma) - 0.5 * c * (dtms - dtma)**2)))
                    if 0.0 - dtmeps <= dtma <= dtms + dtmeps and abs(va) <= vmax:
                        dtmx = (0.0, dtma, dtms)
                        cx = (c, -c)
                        if mon:
                            debug(1, "inpprgmt47")
                        inppack.append((dtma, dtms, dtmx, cx))

        for s1 in (1, -1):
            for s2 in (1, -1):
                for s3 in (1, -1):
                    vad = s1 * vmax
                    cd = s2 * cmax
                    ca = s3 * cmax
                    ka = s2 * s3
                    dtms = (ca * dit + 0.5 * (vad - v0)**2 - 0.5 * ka * (v1 - vad)**2) / (ca * vad)
                    dtma = (vad - v0) / ca
                    dtmd = dtms - (v1 - vad) / cd
                    if mon:
                        debug(1, "inpprgmt55 %s %s %s %s %s %s %s" %
                              (0.0, dtma, dtmd, dtms,
                               degrees(vad), degrees(ca), degrees(cd)))
                        #debug(1, "inpprgmt56 %s %s" %
                              #(v1 - (v0 + ca * dtma + cd * (dtms - dtmd)),
                               #dit - (v0 * dtma + 0.5 * ca * dtma**2 + vad * (dtmd - dtma) + vad * (dtms - dtmd) + 0.5 * cd * (dtms - dtmd)**2)))
                    if 0.0 - dtmeps <= dtma <= dtmd + dtmeps <= dtms + 2 * dtmeps:
                        dtmx = (0.0, dtma, dtmd, dtms)
                        cx = (ca, 0.0, cd)
                        if mon:
                            debug(1, "inpprgmt57")
                        inppack.append((dtmd, dtms, dtmx, cx))

        try:
            assert len(inppack) > 0
        except:
            debug(1, "inpprgmt90 %s %s %s %s %s" %
                  (degrees(dit), degrees(v0), degrees(v1), degrees(vmax),
                   degrees(cmax)))
            raise
        dtmd, dtms, dtmx, cx = sorted(inppack)[0]

        if getc and setc:
            setc(0.0, 0.0, v0)
            def inpf (dq, dtm, mon=False):
                dtmc, dic, v = getc()
                di = 0.0
                #if mon:
                    #debug(1, "here80 %s %s %s %s" %
                          #(dtmc, degrees(dic), degrees(v), dtmx))
                for seg in range(len(dtmx) - 1):
                    dtml, dtmu = dtmx[seg], dtmx[seg + 1]
                    dtm1 = min(dtm, dtmu - dtmc)
                    #if mon:
                        #debug(1, "here84 %s %s %s" % (dtml, dtmu, dtm1))
                    if 0.0 <= dtm1 <= dtmu - dtml:
                        c = cx[seg]
                        di += v * dtm1 + 0.5 * c * dtm1**2
                        v += c * dtm1
                        dtmc += dtm1
                        dtm -= dtm1
                        if dtm <= 0.0:
                            break
                dic += di
                #if mon:
                    #debug(1, "here89 %s %s %s" % (dtmc, degrees(dic), degrees(v)))
                setc(dtmc, dic, v)
                return di
            return inpf, dtmd, dtms
        else:
            return dtmd, dtms


    @staticmethod
    def input_program_settm (dit, v0, v1, vmax, cmax, dtms,
                             getc=None, setc=None, mon=False):

        if mon:
            debug(1, "inpprgst40 %s %s %s %s %s %s" %
                  (degrees(dit), degrees(v0), degrees(v1), degrees(vmax),
                   degrees(cmax), dtms))

        inppack = []
        epsz = 1e-10

        k2 = dtms**2
        k1 = 2.0 * (v0 + v1) * dtms - 4.0 * dit
        k0 = -(v1 - v0)**2
        for c in solve_quad(k2, k1, k0):
            if c is not None:
                if abs(c) > epsz:
                    dtma = 0.5 * (dtms + (v1 - v0) / c)
                    va = v0 + c * dtma
                    if mon:
                        debug(1, "inpprgst45 %s %s %s %s %s" %
                              (0.0, dtma, dtms, degrees(va), degrees(c)))
                        #debug(1, "inpprgst46 %s %s" %
                              #(v1 - (v0 + c * dtma - c * (dtms - dtma)),
                               #dit - (v0 * dtma + 0.5 * c * dtma**2 + (v0 + c * dtma) * (dtms - dtma) - 0.5 * c * (dtms - dtma)**2)))
                    if 0.0 <= dtma <= dtms and abs(va) <= vmax and abs(c) <= cmax:
                        dtmx = (0.0, dtma, dtms)
                        cx = (c, -c)
                        inppack.append((dtma, dtms, dtmx, cx))
                elif abs(dtms * v0 - dit) < 1e-5 * (dit + 1e-3):
                    va = v0
                    dtma = dtms
                    if mon:
                        debug(1, "inpprgst47 %s %s %s %s %s" %
                              (0.0, dtma, dtms, degrees(va), degrees(c)))
                    dtmx = (0.0, dtma, dtms)
                    cx = (c, -c)
                    inppack.append((dtma, dtms, dtmx, cx))

        for s1 in (1, -1):
            for ka in (1, -1):
                vad = s1 * vmax
                dit0 = dit - vad * dtms
                if abs(dit0) > epsz:
                    cd = (0.5 * ka * vad**2 - 0.5 * (vad - v0)**2) / (ka * dit0)
                    ca = ka * cd
                    if abs(cd) > epsz:
                        dtma = (vad - v0) / ca
                        dtmd = dtms - (v1 - vad) / cd
                        if mon:
                            debug(1, "inpprgst55 %s %s %s %s %s %s %s" %
                                  (0.0, dtma, dtmd, dtms,
                                   degrees(vad), degrees(ca), degrees(cd)))
                            #debug(1, "inpprgst56 %s %s" %
                                  #(v1 - (v0 + ca * dtma + cd * (dtms - dtmd)),
                                   #dit - (v0 * dtma + 0.5 * ca * dtma**2 + vad * (dtmd - dtma) + vad * (dtms - dtmd) + 0.5 * cd * (dtms - dtmd)**2)))
                        if 0.0 <= dtma <= dtmd <= dtms and abs(cd) <= cmax:
                            dtmx = (0.0, dtma, dtmd, dtms)
                            cx = (ca, 0.0, cd)
                            inppack.append((dtmd, dtms, dtmx, cx))
                    elif False:
                        dtma = 0.0
                        dtmd = dtms
                        if mon:
                            debug(1, "inpprgst57 %s %s %s %s %s %s %s" %
                                  (0.0, dtma, dtmd, dtms,
                                   degrees(vad), degrees(ca), degrees(cd)))
                        dtmx = (0.0, dtma, dtmd, dtms)
                        cx = (ca, 0.0, cd)
                        inppack.append((dtmd, dtms, dtmx, cx))

        if len(inppack) > 0:
            dtmd, dtms, dtmx, cx = sorted(inppack)[0]
            if mon:
                debug(1, "inpprgst61 %s %s" % (dtmx, cx))
            if getc and setc:
                setc(0.0, 0.0, v0)
                def inpf (dq, dtm, mon=False):
                    dtmc, dic, v = getc()
                    di = 0.0
                    #if mon:
                        #debug(1, "here80 %s %s %s %s" %
                              #(dtmc, degrees(dic), degrees(v), dtmx)
                    for seg in range(len(dtmx) - 1):
                        dtml, dtmu = dtmx[seg], dtmx[seg + 1]
                        dtm1 = min(dtm, dtmu - dtmc)
                        #if mon:
                            #debug(1, "here84 %s %s %s" % (dtml, dtmu, dtm1))
                        if 0.0 <= dtm1 <= dtmu - dtml:
                            c = cx[seg]
                            di += v * dtm1 + 0.5 * c * dtm1**2
                            v += c * dtm1
                            dtmc += dtm1
                            dtm -= dtm1
                            if dtm <= 0.0:
                                break
                    dic += di
                    #if mon:
                        #debug(1, "here89 %s %s %s" % (dtmc, degrees(dic), degrees(v)))
                    setc(dtmc, dic, v)
                    return di
                return inpf, dtmd, dtms
            else:
                return dtmd, dtms
        else:
            if getc and setc:
                return None, None, None
            else:
                return None, None


    @staticmethod
    def input_program_constv (dit, v,
                              getc=None, setc=None, mon=False):

        if mon:
            debug(1, "inpprgcv40 %s %s" % (degrees(dit), degrees(v)))

        dtms = abs(dit / v)
        kv = sign(dit)

        if getc and setc:
            setc(0.0, 0.0)
            def inpf (dq, dtm, mon=False):
                dtmc, dic = getc()
                di = 0.0
                dtm1 = min(dtm, dtms - dtmc)
                if 0.0 < dtm1:
                    di += (v * kv) * dtm1
                    dtmc += dtm1
                dic += di
                setc(dtmc, dic)
                return di
            return inpf, dtms
        else:
            return dtms


    @staticmethod
    def correct_turn_climb (cr, tr, crmax, trmax, wtcr=0.5):

        if cr > 0.0:
            assert 0.0 <= wtcr <= 1.0
            wttr = 1.0 - wtcr
            crref = crmax
            trref = trmax
            cr1rel = abs(cr) / crref
            tr1rel = abs(tr) / trref
            cr2rel = (cr1rel * wtcr) / (cr1rel * wtcr + tr1rel * wttr)
            tr2rel = (tr1rel * wttr) / (tr1rel * wttr + cr1rel * wtcr)
            if cr2rel < cr1rel:
                cr = cr2rel * crref * sign(cr)
            if tr2rel < tr1rel:
                tr = tr2rel * trref * sign(tr)

        return cr, tr


    @staticmethod
    def lead_circle_position (u_t, r_t, u_i, l_r_t, mon=False):

        assert u_i > u_t

        gam_a = - l_r_t / r_t
        k_u2 = - u_i / (u_i - u_t)
        r_a = r_t * (1.0 - 0.5 * (gam_a * k_u2)**2)
        k_u1 = u_t / (u_i - u_t)
        gam_t_i = -gam_a * k_u1
        if mon:
            dt_i = (r_t * gam_t_i) / u_t
            u_a = (r_a / r_t) * u_t
            debug(1, "lcp12:  u_a=%.1f[m/s]  r_a=%.1f[m]  "
                  "gam_a=%.1f[deg]  gam_t_i=%.1f[deg]  dt_i=%.2f[s]" %
                  (u_a, r_a, degrees(gam_a), degrees(gam_t_i), dt_i))
        r_a_p = 0.0
        it = 0
        while abs(r_a - r_a_p) > 1.0 and it < 5:
            r_a_p = r_a
            gam_t_i = (u_t / u_i) * sin(gam_t_i - gam_a)
            r_a = r_t * cos(gam_t_i - gam_a)
            it += 1
        dt_i = (r_t * gam_t_i) / u_t
        u_a = (r_a / r_t) * u_t
        if mon:
            debug(1, "lcp16:  it=%d  u_a=%.1f[m/s]  r_a=%.1f[m]  "
                  "gam_a=%.1f[deg]  gam_t_i=%.1f[deg]  dt_i=%.2f[s]" %
                  (it, u_a, r_a, degrees(gam_a), degrees(gam_t_i), dt_i))

        return u_a, r_a, gam_a, gam_t_i, dt_i


    @staticmethod
    def circle_insertion_path (p_0, v_0, xin_0, r_0, trsmax_0,
                               p_1, v_1, xin_1, r_1, trsmax_1,
                               mon=False):

        ez = Vec3D(0.0, 0.0, 1.0)
        u_0 = v_0.length()
        u_1 = v_1.length()
        xit_0 = unitv(v_0)
        xit_1 = unitv(v_1)
        r_min_0 = u_0 / trsmax_0
        r_min_1 = u_1 / trsmax_1
        if mon:
            debug(1, "cip10:  r_min_0=%.1f[m]  r_min_1=%.1f[m]" %
                  (r_min_0, r_min_1))

        # Project everything to maneuver plane, containing p_1, p_0, xit_0.
        # Center on p_0, x-axis to xit_0.
        ez_m = xit_0.cross(unitv(p_1 - p_0))
        ez_m = unitv(ez_m) if ez_m.length() > 1e-6 else ez
        ex_m = xit_0
        ey_m = ez_m.cross(ex_m)
        projp = lambda p: (p - p_0) - ez_m * (p - p_0).dot(ez_m)
        projv = lambda v: v - ez_m * v.dot(ez_m)
        xin_0m = ey_m
        xit_0m = ex_m
        p_0m = projp(p_0)
        p_1m = projp(p_1)
        xit_1m = projv(xit_1)
        xit_1m = unitv(xit_1m) if xit_1m.length() > 1e-6 else unitv(p_1m)
        xin_1mb = projv(xin_1)
        xin_1m = xit_1m.cross(xin_1mb).cross(xit_1m)
        xin_1m = unitv(xin_1m) if xin_1m.length() > 1e-6 else ez_m.cross(xit_1m)
        r_0m = r_0
        r_1m = r_1 # not projected

        # Pick arc radii.
        r_a0m = r_min_0
        r_a1m = r_min_1

        # Examine all possible arc-segment-arc insertions.
        if mon:
            debug(1, "cip12 %s %s" % (p_0m, p_1m))
        for k_0 in (1, -1):
            xin_0mk = xin_0m * k_0
            p_r0m = p_0m + xin_0mk * r_a0m
            xib_0mk = xit_0m.cross(xin_0mk)
            for k_1 in (1, -1):
                xin_1mk = xin_1m * k_1
                p_r1m = p_1m + xin_1mk * r_a1m
                xib_1mk = xit_1m.cross(xin_1mk)
                dp_rm = p_r1m - p_r0m
                d_rm = dp_rm.length()
                if mon:
                    debug(1, "cip14 %s %s %s" % (p_r0m, p_r1m, d_rm))
                k_ts = xib_0mk.dot(xib_1mk)
                phi = None
                if k_ts > 0.0 and d_rm > abs(r_a0m - r_a1m):
                    # Outer tangent insertion possible.
                    phi = acos((r_a0m - r_a1m) / d_rm)
                    k_io = 1
                    if mon:
                        debug(1, "cip15a outer %s %s %s" % (r_a0m, r_a1m, d_rm))
                elif k_ts < 0.0 and d_rm > r_a0m + r_a1m:
                    # Inner tangent insertion possible.
                    phi = acos((r_a0m + r_a1m) / d_rm)
                    k_io = -1
                    if mon:
                        debug(1, "cip15b inner %s %s %s" % (r_a0m, r_a1m, d_rm))
                if phi is not None:
                    rot0 = QuatD()
                    rot0.setFromAxisAngleRad(-phi, xib_0mk)
                    xin_a0mk = -unitv(Vec3D(rot0.xform(unitv(dp_rm))))
                    sig_a0mk = (-xin_0mk).signedAngleRad(-xin_a0mk, xib_0mk)
                    if sig_a0mk < 0.0:
                        sig_a0mk += 2 * pi
                    l_a0mk = r_a0m * sig_a0mk
                    rot1 = QuatD()
                    rot1.setFromAxisAngleRad(-phi * k_io, xib_1mk)
                    xin_a1mk = -unitv(Vec3D(rot1.xform(unitv(dp_rm * k_io))))
                    sig_a1mk = (-xin_a1mk).signedAngleRad(-xin_1mk, xib_1mk)
                    if sig_a1mk < 0.0:
                        sig_a1mk += 2 * pi
                    l_a1mk = r_a1m * sig_a1mk
                    l_smk = d_rm * cos(0.5 * pi - phi)
                    l_mk = l_a0mk + l_smk + l_a1mk
                    if mon:
                        debug(1, "cip18:  k_0=%d  k_1=%d  phi=%.1f[deg]  "
                              "sig_a0mk=%.1f[deg]  sig_a1mk=%.1f[deg]  "
                              "l_a0mk=%.1f[m]  l_a1mk=%.1f[m]  "
                              "l_smk=%.1f[m]  l_mk=%.1f[m]" %
                              (k_0, k_1, degrees(phi),
                               degrees(sig_a0mk), degrees(sig_a1mk),
                               l_a0mk, l_a1mk, l_smk, l_mk))

        path = None
        return path


class PlaneSkill (object):

    def __init__ (self, piloting=1.0, aiming=1.0, awareness=1.0):

        assert 0.0 <= piloting <= 1.0
        assert 0.0 <= aiming <= 1.0
        assert 0.0 <= awareness <= 1.0

        self.piloting = piloting
        self.aiming = aiming
        self.awareness = awareness


    @staticmethod
    def preset (key):

        if key == "rookie":
            return PlaneSkill(piloting=0.0, aiming=0.0, awareness=1.0)
        elif key == "pilot":
            return PlaneSkill(piloting=0.4, aiming=0.4, awareness=1.0)
        elif key == "veteran":
            return PlaneSkill(piloting=0.7, aiming=0.7, awareness=1.0)
        elif key == "ace":
            return PlaneSkill(piloting=1.0, aiming=1.0, awareness=1.0)
        elif key == "testpilot":
            return PlaneSkill(piloting=0.999, aiming=0.999, awareness=0.999)
        else:
            raise StandardError("Unknown skill preset '%s'." % key)


