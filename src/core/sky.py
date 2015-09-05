# -*- coding: UTF-8 -*-

from math import pi, radians, degrees, ceil, sin, cos, atan2, exp
import os
from shutil import rmtree
from time import time

from pandac.PandaModules import Vec3, Vec3D, Vec4, Point2, Point3, Point3D
from pandac.PandaModules import Quat, QuatD
from pandac.PandaModules import AmbientLight, DirectionalLight
from pandac.PandaModules import GeomVertexArrayFormat, InternalName
from pandac.PandaModules import GeomVertexFormat
from pandac.PandaModules import GeomVertexWriter, GeomVertexData
from pandac.PandaModules import Geom, GeomNode, GeomTriangles
from pandac.PandaModules import NodePath, Shader
from pandac.PandaModules import TransparencyAttrib, ColorAttrib
from pandac.PandaModules import Texture

from src import join_path, path_exists, path_dirname
from src import internal_path, real_path, full_path
from src import GLSL_PROLOGUE
from src.core.misc import rgba, AutoProps, SimpleProps, pclamp, hrmin_to_sec
from src.core.misc import set_texture, make_quad
from src.core.misc import get_cache_key_section, key_to_hex
from src.core.misc import hprtovec
from src.core.misc import Random
from src.core.misc import intl01vr
from src.core.misc import report, dbgval
from src.core.shader import printsh, make_shader, make_shdfunc_sunbln
from src.core.shader import make_frag_outputs
from src.core.transl import *


class Sky (object):

    def __init__ (self, world, latitude=0.0, longitude=0.0, moredayhr=0.0,
                  dome=None, fog=None, sun=None, moon=None, stars=None,
                  suncolors=None, mooncolors=None,
                  ambientcolors=None, ambientsmokefacs=None,
                  skycolors=None, fogcolors=None,
                  sundiskcolors=None, sunbrightcolors=None, sunhaloscales=None,
                  staralphas=None,
                  domealtcolfac=None, fogaltcolfac=None,
                  shadowblend=0.3):

        if world.sky:
            raise StandardError(
                "A sky has already been created for this world.")
        world.sky = self

        self.world = world
        self.dome = dome
        self.fog = fog
        self.sun = sun
        self.moon = moon
        self.stars = stars
        self._suncolors = suncolors
        self._mooncolors = mooncolors
        self._ambientcolors = ambientcolors
        self._ambientsmokefacs = ambientsmokefacs
        self._skycolors = skycolors
        self._fogcolors = fogcolors
        self._sundiskcolors = sundiskcolors
        self._sunbrightcolors = sunbrightcolors
        self._sunhaloscales = sunhaloscales
        self._staralphas = staralphas
        self._domealtcolfac = domealtcolfac
        self._fogaltcolfac = fogaltcolfac
        self.shadowblend = shadowblend

        # (hour, minute) point followed by crossfade factor to next point
        # sky_points = [
            # (6, 0), # sunrise
            # 1.0,
            # (12, 0), # noon
            # 10.0,
            # (18, 0), # sunset
            # 2.0,
            # (20, 0), # evening
            # 1.0,
            # (0, 0), # midnight
            # 16.0,
            # (5, 0), # dawn
            # 2.0,
        # ]
        sky_points = [
            (6, 0), # sunrise
            -10.0,
            (12, 0), # noon
            10.0,
            (18, 0), # sunset
            -1.0,
            (20, 30), # evening
            -1.0,
            (0, 0), # midnight
            1.0,
            (4, 30), # dawn
            1.0,
        ]
        dp = self.world.day_period
        mdhh = 0.5 * (moredayhr * 3600.0)
        moondhdg = 165.0
        self._timepts = []
        self._cintpows = []
        self._sunhdgs = []
        self._moonhdgs = []
        self._moonhdgs = []
        self._starshdgs = []
        for hrmin, ipw in zip(sky_points[::2], sky_points[1::2]):
            time = pclamp(hrmin_to_sec(*hrmin), 0.0, dp)
            sunhdg = -(time / dp) * 360.0 # based on non-modified time
            sunhdg = pclamp(sunhdg, 0.0, 360.0)
            if 0.0 <= time < 0.25 * dp: # midnight to sunrise
                time += -((time - 0.0 * dp) / (0.25 * dp)) * mdhh
            elif 0.25 * dp <= time < 0.5 * dp: # sunrise to noon
                time += -((0.5 * dp - time) / (0.25 * dp)) * mdhh
            elif 0.5 * dp <= time < 0.75 * dp: # noon to sunset
                time += +((time - 0.5 * dp) / (0.25 * dp)) * mdhh
            else: # elif 0.75 * dp <= time < 1.0 * dp # sunset to midnight
                time += +((1.0 * dp - time) / (0.25 * dp)) * mdhh
            time = pclamp(time, 0.0, dp)
            self._timepts.append(time)
            if abs(ipw) < 1.0:
                raise StandardError(
                    "Sky interpolation power must be >= 1.0 or <= -1.0.")
            self._cintpows.append(ipw)
            self._sunhdgs.append(sunhdg)
            moonhdg = pclamp(sunhdg + moondhdg, 0.0, 360.0)
            self._moonhdgs.append(moonhdg)
            starshdg = pclamp(sunhdg + longitude, 0.0, 360.0) #!!!
            self._starshdgs.append(starshdg)
        #print "--sky50 timepts", [x/3600.0 for x in self._timepts]
        #print "--sky51 sunhdgs", self._sunhdgs
        self._sunhdglock = -5.0
        self._moonhdglock = -5.0

        self.node = world.node.attachNewNode("sky")

        sunplane = self.node.attachNewNode("sun-plane")
        sunplane.setHpr(0, latitude - 90, 0)

        sunlightplat = sunplane.attachNewNode("sun")
        sunlightplat.setHpr(180, 0, 0)
        sunlt = DirectionalLight("sun-light")
        self.sunlight = sunlightplat.attachNewNode(sunlt)
        self.world.node.setLight(self.sunlight)

        moonplane = self.node.attachNewNode("moon-plane")
        moonplane.setHpr(0, latitude - 90, 0)

        moonlightplat = moonplane.attachNewNode("moon")
        moonlightplat.setHpr(180, 0, 0)
        moonlt = DirectionalLight("moon-light")
        self.moonlight = moonlightplat.attachNewNode(moonlt)
        self.world.node.setLight(self.moonlight)

        amblt = AmbientLight("ambient-light")
        self.amblight = self.node.attachNewNode(amblt)
        self.world.node.setLight(self.amblight)

        amblt_smoke = AmbientLight("ambient-light-smoke")
        self.amblight_smoke = self.node.attachNewNode(amblt_smoke)
        self.world.node.setLight(self.amblight_smoke)

        if self.dome:
            self.dome.node.reparentTo(self.node)
            self.dome.node.setPos(0, 0, 0)
        if self.stars:
            starsplane = self.node.attachNewNode("stars-plane")
            starsplane.setHpr(0, latitude - 90, 0)
            starsnode = starsplane.attachNewNode("stars")
            starsnode.setHpr(180, 0, 0)
            self.stars.node.reparentTo(starsnode)
            self.stars.node.setPos(0, 0, 0)
        if self.sun:
            self.sun.node.reparentTo(sunplane)
            self.sun.node.setPos(0, 0, 0)
        if self.moon:
            self.moon.node.reparentTo(moonplane)
            self.moon.node.setPos(0, 0, 0)

        self._updwait_slow = 0.0
        self._updperiod_slow = 4.87
        self._updwait_fast = 0.0
        self._updperiod_fast = 0.043

        self._need_alt_color_mod = (self._domealtcolfac is not None or
                                    self._fogaltcolfac is not None)
        self._curr_color_sky = Vec4()
        self._curr_color_fog = Vec4()

        self._relative_visibilities = [
            0.8, # sunrise
            1.0, # noon
            0.8, # sunset
            0.6, # evening
            0.5, # midnight
            0.6, # dawn
        ]
        self.relative_visibility = 1.0

        self.sun_dir = Vec3(0.0, 0.0, 1.0)

        self._sun_strengths = [
            0.0, # sunrise
            1.0, # noon
            0.0, # sunset
            0.0, # evening
            0.0, # midnight
            0.0, # dawn
        ]
        self.sun_strength = 1.0

        self.sun_bright_color = Vec4()

        self.alive = True
        # Should come before body loops.
        task = base.taskMgr.add(self._loop, "sky-loop", sort=-1)
        #self._loop(task) # initialize


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        if self.world.frame < 3:
            self._updwait_slow = 0.0
        self._updwait_slow -= self.world.dt * self.world.day_time_factor
        if self._updwait_slow <= 0.0:
            self._updwait_slow += self._updperiod_slow

            ntpts = len(self._timepts)
            t0 = self.world.day_time
            for i1 in range(ntpts):
                i2 = (i1 + 1) % ntpts
                t1 = self._timepts[i1]
                t2 = self._timepts[i2]
                if t2 > t1:
                    t = t0
                    if t1 <= t < t2:
                        break
                else:
                    t2 += self.world.day_period
                    t = t0
                    if t < t1:
                        t += self.world.day_period
                    if t1 <= t < t2:
                        break
            #(6, 12, 18, 0)
            #(8, 14, 20, 2)
            #(4, 10, 16, 22)
            ifac_lin = (t - t1) / (t2 - t1)
            ipw = self._cintpows[i1]
            if ipw > 0.0:
                ifac = ifac_lin**ipw
            else:
                ifac = 1.0 - (1.0 - ifac_lin)**(-ipw)

            cs = self._suncolors
            c = cs[i1] + (cs[i2] - cs[i1]) * ifac
            self.sunlight.node().setColor(c)
            # if self.sun:
                # self.sun.node.setColorScale(c)

            cs = self._mooncolors
            c = cs[i1] + (cs[i2] - cs[i1]) * ifac
            self.moonlight.node().setColor(c)
            # if self.moon:
                # self.moon.node.setColorScale(c)

            cs = self._ambientcolors
            c = cs[i1] + (cs[i2] - cs[i1]) * ifac
            self.amblight.node().setColor(c)
            fs = self._ambientsmokefacs
            f = fs[i1] + (fs[i2] - fs[i1]) * ifac
            cavg = min(((c[0] + c[1] + c[2]) / 3) * f, 1.0)
            c = Vec4(cavg, cavg, cavg, 1.0)
            self.amblight_smoke.node().setColor(c)

            if self.dome:
                scs = self._skycolors
                sc = scs[i1] + (scs[i2] - scs[i1]) * ifac
                self._curr_color_sky = sc
            if self.dome or self.fog:
                fcs = self._fogcolors
                fc = fcs[i1] + (fcs[i2] - fcs[i1]) * ifac
                self._curr_color_fog = fc
            if self.fog and not self._need_alt_color_mod:
                self.fog.set_color(fc)
            if self.sun:
                sdcs = self._sundiskcolors
                sdc = sdcs[i1] + (sdcs[i2] - sdcs[i1]) * ifac
                self.sun.node.setColorScale(sdc)
                scalenode = self.sun.halonode or self.sun.sunnode
                shscs = self._sunhaloscales
                shsc = shscs[i1] + (shscs[i2] - shscs[i1]) * ifac
                scalenode.setScale(shsc)
                self._curr_color_sdc = sdc
                sbcs = self._sunbrightcolors
                sbc = sbcs[i1] + (sbcs[i2] - sbcs[i1]) * ifac
                self.sun_bright_color = sbc
            elif self.dome:
                sdc = sc
                self._curr_color_sdc = sdc
            if self.moon:
                mas = self._staralphas
                ma = mas[i1] + (mas[i2] - mas[i1]) * ifac
                self.moon.node.setSa(ma)
            if self.stars:
                sas = self._staralphas
                sa = sas[i1] + (sas[i2] - sas[i1]) * ifac
                self.stars.node.setSa(sa)
            if self.dome and not self._need_alt_color_mod:
                self.dome.set_color(sc, fc)

            h1, h2 = self._sunhdgs[i1], self._sunhdgs[i2]
            if h2 > h1:
                h1 += 360.0
            h = pclamp(h1 + (h2 - h1) * ifac_lin, 0.0, 360.0)
            if self.sun:
                self.sun.node.setHpr(h, 0, 0)
            if h < 90.0 + self._sunhdglock:
                h1 = 90.0 + self._sunhdglock
            elif h > 270.0 - self._sunhdglock:
                h1 = 270.0 - self._sunhdglock
            else:
                h1 = h
            self.sunlight.setHpr(h1, 0, 0)

            h1, h2 = self._moonhdgs[i1], self._moonhdgs[i2]
            if h2 > h1:
                h1 += 360.0
            h = pclamp(h1 + (h2 - h1) * ifac_lin, 0.0, 360.0)
            if self.moon:
                self.moon.node.setHpr(h, 0, 0)
            if h < 90.0 + self._moonhdglock:
                h1 = 90.0 + self._moonhdglock
            elif h > 270.0 - self._moonhdglock:
                h1 = 270.0 - self._moonhdglock
            else:
                h1 = h
            self.moonlight.setHpr(h1, 0, 0)

            if self.stars:
                h1, h2 = self._starshdgs[i1], self._starshdgs[i2]
                if h2 > h1:
                    h1 += 360.0
                h = h1 + (h2 - h1) * ifac_lin
                self.stars.node.setHpr(h, 0, 0)

            rvs = self._relative_visibilities
            rv = rvs[i1] + (rvs[i2] - rvs[i1]) * ifac
            self.relative_visibility = rv

            self.sun_dir = -hprtovec(self.sunlight.getHpr(self.world.node))

            sts = self._sun_strengths
            st = sts[i1] + (sts[i2] - sts[i1]) * ifac
            self.sun_strength = st

            for terrain in self.world.terrains:
                for ngfn1 in terrain.nightglowfacn:
                    terrain.node.setShaderInput(ngfn1, 1.0 - self.sun_strength)

        # After slow, for correct first update.
        if self.world.frame < 3:
            self._updwait_fast = 0.0
        self._updwait_fast -= self.world.dt * self.world.day_time_factor
        if self._updwait_fast <= 0.0:
            self._updwait_fast += self._updperiod_fast

            # Conform to camera.
            chx, chy, chz = self.world.camera.getPos(self.world.node)
            pos = Point3(chx, chy, chz)
            self.node.setPos(pos)
            # if self.dome:
                # chh, chp, chr = self.world.chaser.node.getHpr(self.world.node)
                # hpr = Vec3(chh, 0.0, 0.0)
                # self.dome.node.setHpr(hpr)
            alt = chz

            # Update altitude-dependent colors.
            if self._need_alt_color_mod:
                if self.dome:
                    sc = self._curr_color_sky
                    if self._domealtcolfac is not None:
                        sc = self._mod_color_alt(sc, self._domealtcolfac, alt)
                if self.dome or self.fog:
                    fc = self._curr_color_fog
                    if self._fogaltcolfac is not None:
                        fc = self._mod_color_alt(fc, self._fogaltcolfac, alt)
                if self.fog:
                    self.fog.set_color(fc)
                if self.dome:
                    self.dome.set_color(sc, fc)

        return task.cont


    def _mod_color_alt (self, col, altfac, alt):

        acmr, acmg, acmb = [exp(alt * f) for f in altfac]
        modcol = Vec4(col[0] * acmr, col[1] * acmg, col[2] * acmb, 1.0)
        return modcol


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self.dome:
            self.dome.destroy()
        if self.fog:
            self.fog.destroy()
        if self.stars:
            self.stars.destroy()
        if self.sun:
            self.sun.destroy()
        if self.moon:
            self.moon.destroy()
        self.node.removeNode()


class Dome (object):

    def __init__ (self, world, baserad, height, nbasesegs,
                  hscale=1.0, extang=(0.2 * pi),
                  expalpha=16.0, sunblend=()):

        if nbasesegs < 3:
            raise StandardError("Must have at least 3 base segments.")

        self.world = world

        self.node = world.node.attachNewNode("dome")
        self.node.setScale(hscale, 1.0, 1.0)

        gvformat = GeomVertexFormat.getV3n3c4t2()
        gvdata = GeomVertexData("dome", gvformat, Geom.UHStatic)
        gvwvertex = GeomVertexWriter(gvdata, "vertex")
        gvwnormal = GeomVertexWriter(gvdata, "normal")
        gvwcolor = GeomVertexWriter(gvdata, "color")
        gvwtexcoord = GeomVertexWriter(gvdata, "texcoord")
        gtris = GeomTriangles(Geom.UHStatic)

        pos = Point3()
        rot = Vec3()
        rad = (height**2 + baserad**2) / (2 * height)
        ang = atan2(baserad, rad - height)
        uoff, voff = 0.0, 0.0
        ret = Dome._add_dome(gvwvertex, gvwnormal, gvwcolor, gvwtexcoord, gtris,
                             pos, rot, rad, ang, nbasesegs, extang, uoff, voff,
                             expalpha)
        nvertices, ntris = ret
        #print "--dome-create-50", nvertices, ntris

        geom = Geom(gvdata)
        geom.addPrimitive(gtris)
        gnode = GeomNode("dome")
        gnode.addGeom(geom)
        domend = NodePath("dome")
        domend.attachNewNode(gnode)
        #domend.setAttrib(ColorAttrib.makeVertex())
        #if texpath:
            #set_texture(domend, texpath)
        domend.reparentTo(self.node)
        domend.setTwoSided(True)
        domend.setTransparency(TransparencyAttrib.MAlpha)

        self.node.setDepthWrite(False)
        self.node.setBin("background", -int(baserad))
        self._shdinp = SimpleProps()
        self._shdinp.basecoln = "INbasecol"
        self._shdinp.horizcoln = "INhorizcol"
        shader = Dome._make_shader(self.world.shdinp.camn,
                                   self._shdinp.basecoln,
                                   self._shdinp.horizcoln,
                                   sunblend,
                                   self.world.shdinp.sunposn,
                                   self.world.shdinp.sunbcoln)
        self.node.setShader(shader)
        #self.node.setRenderModeWireframe()
        self._basecol_spec = AmbientLight("dome-base-color")
        self._horizcol_spec = AmbientLight("dome-horiz-color")
        self.node.setShaderInput(self._shdinp.basecoln,
                                 NodePath(self._basecol_spec))
        self.node.setShaderInput(self._shdinp.horizcoln,
                                 NodePath(self._horizcol_spec))

        self._input_shader(0.0, self.world.day_time_factor) # initialize
        self.alive = True
        base.taskMgr.add(self._loop, "dome-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    @staticmethod
    def _add_dome (gvwvertex, gvwnormal, gvwcolor, gvwtexcoord, gtris,
                   pos, rot, rad, ang, nbprsegs, extang, uoff, voff, expalpha,
                   eggfac=1.0):

        qrot = Quat()
        qrot.setHpr(rot)
        sgz = 1 if rad >= 0.0 else -1
        rad = abs(rad)
        bprrad = rad * sin(ang)
        bseglen = 2 * pi * bprrad / nbprsegs
        nmdsegs = int(ceil(rad * ang / bseglen))
        mdanglen = ang / nmdsegs
        nmdsegs += int(extang / mdanglen)
        ptc = pos + Point3(0.0, 0.0, -sgz * rad * cos(ang))
        if gvwtexcoord is not None:
            uvoff = Point2(uoff, voff)
            uvc1 = Point2(0.0, 0.0)
            uvc2 = Point2(1.0, 0.0)
            uvc3 = Point2(1.0, 1.0)
            uvc4 = Point2(0.0, 1.0)
            uvt = Point2(0.5, 0.5)
        if gvwvertex is not None:
            vind0 = gvwvertex.getWriteRow()
        else:
            vind0 = 0
        nvertices = 0
        ntris = 0
        prvinds = []
        vpts = []
        for imd in range(nmdsegs + 1):
            prvinds.append([])

            # Create vertices on current parallel.
            mdang = mdanglen * imd
            prrad = rad * sin(mdang)
            if mdang > 0:
                nprsegs = max(int(ceil(nbprsegs * prrad / bprrad)), 3)
            else:
                nprsegs = 1
            dprang = 2 * pi / nprsegs
            z = sgz * rad * cos(mdang) * eggfac
            ifacmd = mdang / ang
            for ipr in range(nprsegs + 1):
                prang = ipr * dprang
                x = prrad * cos(prang)
                y = prrad * sin(prang)
                dpt = Point3(qrot.xform(Point3(x, y, z)))
                pt = ptc + dpt
                vpts.append(pt)
                if gvwvertex is not None:
                    gvwvertex.addData3f(*pt)
                if gvwnormal is not None:
                    n = Vec3(dpt)
                    n.normalize()
                    gvwnormal.addData3f(*n)
                if gvwcolor is not None:
                    a = min(ifacmd, 1.0)**expalpha
                    gvwcolor.addData4f(1.0, 1.0, 1.0, a)
                prvinds[-1].append(nvertices)
                nvertices += 1
                # Compute texture coordinates for this vertex.
                if gvwtexcoord is not None:
                    #u = prang / (2 * pi)
                    #v = 1.0 - ifacmd
                    if prang < 0.5 * pi:
                        rprang = prang
                        uvca, uvcb = uvc1, uvc2
                    elif prang < 1.0 * pi:
                        rprang = prang - 0.5 * pi
                        uvca, uvcb = uvc2, uvc3
                    elif prang < 1.5 * pi:
                        rprang = prang - 1.0 * pi
                        uvca, uvcb = uvc3, uvc4
                    else:
                        rprang = prang - 1.5 * pi
                        uvca, uvcb = uvc4, uvc1
                    ifacpr = rprang / (0.5 * pi)
                    uv1 = uvca + (uvcb - uvca) * ifacpr
                    uv = uvt + (uv1 - uvt) * ifacmd
                    uv += uvoff
                    gvwtexcoord.addData2f(*uv)
                #print ("--add-dome-20  x=%+10.2f y=%+10.2f z=%+10.2f "
                       #"u=%+.5f v=%+.5f" % (pt[0], pt[1], pt[2], u[0], v[0]))

            if imd == 0:
                continue

            # Create triangles between current and previous parallel.
            prvinds1 = prvinds[-2]
            prvinds2 = prvinds[-1]
            ipr1a = 0
            ipr2a = 0
            exhausted1 = False
            exhausted2 = False
            while not exhausted1 or not exhausted2:
                ipr1b = ipr1a + 1 if ipr1a + 1 < len(prvinds1) else 0
                ipr2b = ipr2a + 1 if ipr2a + 1 < len(prvinds2) else 0
                ind2a = prvinds2[ipr2a]; ind2b = prvinds2[ipr2b]
                ind1a = prvinds1[ipr1a]; ind1b = prvinds1[ipr1b]
                el2a1b = (vpts[ind2a] - vpts[ind1b]).length()
                el2b1a = (vpts[ind2b] - vpts[ind1a]).length()
                if (el2a1b < el2b1a and not exhausted1) or exhausted2:
                    trivinds = [ind2a, ind1b, ind1a]
                    ipr1a = ipr1b
                    if ipr1a == len(prvinds1) - 1:
                        exhausted1 = True
                else:
                    trivinds = [ind2a, ind2b, ind1a]
                    ipr2a = ipr2b
                    if ipr2a == len(prvinds2) - 1:
                        exhausted2 = True
                trivinds = [vind0 + vind for vind in trivinds]
                if gtris is not None:
                    gtris.addVertices(*trivinds)
                    gtris.closePrimitive()
                ntris += 1

        return nvertices, ntris


    _shader_cache = {}

    @staticmethod
    def _make_shader (camn, basecoln, horizcoln,
                      sunblend, sunposn, sunbcoln):

        if not sunblend:
            camn = None

        shdkey = (camn, basecoln, horizcoln,
                  tuple(sunblend), sunposn, sunbcoln)
        shader = Dome._shader_cache.get(shdkey)
        if shader is not None:
            return shader

        vshstr = GLSL_PROLOGUE

        if sunblend:
            vshstr += make_shdfunc_sunbln(sunblend=sunblend)

        vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

struct HorizColSpec {
    vec4 ambient;
};
uniform HorizColSpec %(basecoln)s;
uniform HorizColSpec %(horizcoln)s;
""" % locals()
        if sunblend:
            vshstr += """
uniform vec4 wspos_%(camn)s;
uniform vec4 wspos_%(sunposn)s;
uniform SunBlendSpec %(sunbcoln)s;
""" % locals()
        vshstr += """
in vec4 p3d_Vertex;
in vec4 p3d_Color;

out vec4 l_color;
out vec4 l_bloom;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    vec4 basecol = %(basecoln)s.ambient;
    vec4 horizcol = %(horizcoln)s.ambient;
    float altblfac = p3d_Color.a;
    l_color.rgb = mix(basecol.rgb, horizcol.rgb, altblfac);
    l_bloom = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
        if sunblend:
            vshstr += """
    vec4 pw = p3d_ModelMatrix * p3d_Vertex;
    sunbln(pw, wspos_%(sunposn)s, wspos_%(camn)s, l_color,
           %(sunbcoln)s.ambient, l_color);
""" % locals()
        vshstr += """
    l_color.a = 1.0;
}
"""

        fshstr = GLSL_PROLOGUE
        ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
        odeclstr, ocolorn, osunvisn = ret[:3]
        if base.with_bloom:
            obloomn = ret[3]
        fshstr += """
in vec4 l_color;
in vec4 l_bloom;
"""
        fshstr += odeclstr
        fshstr += """
void main ()
{
    vec4 color = l_color;
    vec4 bloom = l_bloom;
"""
        if base.with_glow_add and not base.with_bloom:
            fshstr += """
    color.rgb += bloom.rgb;
"""
        fshstr += """
    %(ocolorn)s = color;
    %(osunvisn)s = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
        if base.with_bloom:
            fshstr += """
    %(obloomn)s = bloom;
""" % locals()
        fshstr += """
}
"""

        if 0:
            printsh((vshstr, fshstr), "dome-shader")
        shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
        Dome._shader_cache[shdkey] = shader
        return shader


    def _input_shader (self, dt, tmf):

        pass


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        self._input_shader(self.world.dt, self.world.day_time_factor)

        return task.cont


    def set_color (self, basecol, horizcol):

        self._basecol_spec.setColor(basecol)
        self._horizcol_spec.setColor(horizcol)


class Fog (object):

    def __init__ (self, world, onsetdist=None, opaquedist=None,
                  falloff=None, color=None,
                  onsetdistgnd=None, opaquedistgnd=None, altvardist=None):

        self.world = world

        self.color = color
        self.falloff = falloff
        self.onsetdist = onsetdist
        self.opaquedist = opaquedist
        self.onsetdistgnd = onsetdistgnd
        self.opaquedistgnd = opaquedistgnd
        self.altvardist = altvardist


    def set_color (self, color):

        self.color = color


    def destroy (self):

        pass


    def dist_for_alt (self, alt):

        if self.altvardist is not None:
            onsetdist = intl01vr(alt, 0.0, self.altvardist,
                                 self.onsetdistgnd, self.onsetdist)
            opaquedist = intl01vr(alt, 0.0, self.altvardist,
                                  self.opaquedistgnd, self.opaquedist)
        else:
            onsetdist = self.onsetdist
            opaquedist = self.opaquedist
        return onsetdist, opaquedist


class Sun (object):

    def __init__ (self, world, radius, size, texpath,
                  halosize=None, halotexpath=None,
                  color=None, ftnearest=False):

        self.node = world.node.attachNewNode("sun")
        self.node.clearFog()
        self.node.setDepthWrite(False)

        use_glow = True
        if use_glow:
            glowmap = "images/sky/sun_gw.png"
            shader = make_shader(glow=True, modcol=True, sunstr=1.0)
            #halosize = None
        else:
            glowmap = None
            shader = make_shader(modcol=True, sunstr=1.0)
        self.node.setShader(shader)

        sundiam = radius * size
        sunnode = make_quad(size=sundiam, texture=texpath, glowmap=glowmap)
        sunnode.reparentTo(self.node)
        sunnode.setPos(0.0, radius, 0.0)
        sunnode.setBin("background", -int(radius))
        sunnode.setTransparency(TransparencyAttrib.MAlpha)
        self.sunnode = sunnode

        if halosize is not None and halotexpath is not None:
            halodiam = radius * halosize
            halonode = make_quad(size=halodiam, texture=halotexpath,
                                 glowmap=glowmap)
            halonode.reparentTo(self.node)
            haloradius = radius + 1 # must be int(haloradius) < int(radius)
            halonode.setPos(0.0, haloradius, 0.0)
            halonode.setBin("background", -int(haloradius))
            halonode.setTransparency(TransparencyAttrib.MAlpha)
            if ftnearest:
                suntex = sunnode.getTexture()
                suntex.setMinfilter(Texture.FTNearest)
                suntex.setMagfilter(Texture.FTNearest)
            self.halonode = halonode
        else:
            self.halonode = None

        self.size = size
        self.diameter = sundiam

        if color is not None:
            self.node.setColorScale(color)


    def destroy (self):

        self.node.removeNode()


class Moon (object):

    def __init__ (self, world, radius, size, texpath,
                  halosize=None, halotexpath=None,
                  color=None, ftnearest=False):

        self.node = world.node.attachNewNode("moon")
        self.node.clearFog()
        self.node.setDepthWrite(False)

        use_glow = True
        if use_glow:
            glowmap = "images/sky/moon_gw.png"
            shader = make_shader(glow=True, modcol=True)
            halosize = None
        else:
            glowmap = None
            shader = make_shader(modcol=True)
        self.node.setShader(shader)

        moondiam = radius * size
        moonnode = make_quad(size=moondiam, texture=texpath, glowmap=glowmap)
        moonnode.reparentTo(self.node)
        moonnode.setPos(0.0, radius, 0.0)
        moonnode.setBin("background", -int(radius))
        moonnode.setTransparency(TransparencyAttrib.MAlpha)
        self.moonnode = moonnode

        if halosize is not None and halotexpath is not None:
            halodiam = radius * halosize
            halonode = make_quad(size=halodiam, texture=halotexpath,
                                 glowmap=glowmap)
            halonode.reparentTo(self.node)
            haloradius = radius + 1 # must be int(haloradius) > int(radius)
            halonode.setPos(0.0, haloradius, 0.0)
            halonode.setBin("background", -int(haloradius))
            halonode.setTransparency(TransparencyAttrib.MAlpha)
            if ftnearest:
                moontex = moonnode.getTexture()
                moontex.setMagfilter(Texture.FTNearest)
                moontex.setMinfilter(Texture.FTNearest)

        self.size = size
        self.diameter = moondiam

        if color is not None:
            self.node.setColorScale(color)


    def destroy (self):

        self.node.removeNode()


class Stars (object):

# @cache-key-start: stars-generation
    def __init__ (self, world, datapath, radius,
                  mag1, mag2, size1, size2, alpha1, alpha2, poly1, poly2,
                  reffov=None, name=None):
# @cache-key-end: stars-generation

        timeit = False

        self.world = world

        self.node = world.node.attachNewNode("stars")
        self.node.clearFog()

        self._reffov = reffov
        self._camfov = None

# @cache-key-start: stars-generation
        carg = AutoProps(
            radius=radius,
            mag1=mag1, mag2=mag2, size1=size1, size2=size2,
            alpha1=alpha1, alpha2=alpha2, poly1=poly1, poly2=poly2,
        )
        fcarg = AutoProps(datapath=datapath)
        ret = None
        keyhx = None
        if name:
            sname = name
            fckey = [datapath]
            this_path = internal_path("data", __file__)
            key = (sorted(carg.props()), sorted(fcarg.props()),
                   get_cache_key_section(this_path.replace(".pyc", ".py"),
                                         "stars-generation"))
            keyhx = key_to_hex(key, fckey)
# @cache-key-end: stars-generation
            if timeit:
                t1 = time()
# @cache-key-start: stars-generation
            ret = self._load_from_cache(sname, keyhx)
# @cache-key-start: stars-generation
            if timeit and ret:
                t2 = time()
                dbgval(1, "stars-load-from-cache",
                       (t2 - t1, "%.3f", "time", "s"))
# @cache-key-end: stars-generation
        if not ret:
            ret = Stars._construct(**dict(carg.props() + fcarg.props()))
            starnode = ret
            if keyhx is not None:
# @cache-key-end: stars-generation
                if timeit:
                    t1 = time()
# @cache-key-start: stars-generation
                Stars._write_to_cache(sname, keyhx, starnode)
# @cache-key-end: stars-generation
                if timeit:
                    t2 = time()
                    dbgval(1, "stars-write-to-cache",
                           (t2 - t1, "%.3f", "time", "s"))
# @cache-key-start: stars-generation
        else:
            starnode = ret
# @cache-key-end: stars-generation
        t2 = time()
        # print "--stars-construction time=%.1f[ms]" % ((t2 - t1) * 1000)
        starnode.reparentTo(self.node)

        self.node.setDepthWrite(False)
        self.node.setBin("background", -int(radius))
        shader = Stars._make_shader(self.world.shdinp)
        self.node.setShader(shader)

        self._updwait_shdinp_alpha = 0.0
        self._updperiod_shdinp_alpha = 1.023

        self._input_shader(0.0, self.world.day_time_factor) # initialize
        self.alive = True
        base.taskMgr.add(self._loop, "stars-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()

# @cache-key-start: stars-generation
    @staticmethod
    def _construct (datapath, radius,
                    mag1, mag2, size1, size2, alpha1, alpha2, poly1, poly2):

# @cache-key-end: stars-generation
        report(_("Constructing stars."))
        timeit = False
# @cache-key-start: stars-generation

# @cache-key-end: stars-generation
        if timeit:
            t0 = time()
            t1 = t0
# @cache-key-start: stars-generation
        stardata = Stars._load_stars(datapath)
# @cache-key-end: stars-generation
        if timeit:
            t2 = time()
            dbgval(1, "stars-load-definitions",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: stars-generation
        starnode = Stars._make_star_sphere(
            stardata, radius,
            mag1, mag2, size1, size2, alpha1, alpha2, poly1, poly2)
# @cache-key-end: stars-generation
        if timeit:
            t2 = time()
            dbgval(1, "stars-make-sphere",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: stars-generation

        return starnode


    _cache_pdir = "stars"

    @staticmethod
    def _cache_key_path (sname):

        return join_path(Stars._cache_pdir, sname, "stars.key")


    @staticmethod
    def _cache_geom_path (sname):

        return join_path(Stars._cache_pdir, sname, "stars.bam")


    @staticmethod
    def _load_from_cache (sname, keyhx):

        keypath = Stars._cache_key_path(sname)
        if not path_exists("cache", keypath):
            return None
        okeyhx = open(real_path("cache", keypath), "rb").read()
        if okeyhx != keyhx:
            return None

        geompath = Stars._cache_geom_path(sname)
        if not path_exists("cache", geompath):
            return None
        starnode = base.load_model("cache", geompath, cache=False)

        return starnode


    @staticmethod
    def _write_to_cache (sname, keyhx, starnode):

        keypath = Stars._cache_key_path(sname)

        cdirpath = path_dirname(keypath)
        if path_exists("cache", cdirpath):
            rmtree(real_path("cache", cdirpath))
        os.makedirs(real_path("cache", cdirpath))

        geompath = Stars._cache_geom_path(sname)
        base.write_model_bam(starnode, "cache", geompath)

        fh = open(real_path("cache", keypath), "wb")
        fh.write(keyhx)
        fh.close()


    class StarData (object): pass

    @staticmethod
    def _load_stars (datapath):

        stardata = []
        ls = open(real_path("data", datapath)).readlines()
        ls = [l.decode("UTF-8") for l in ls]
        for l1, l2, l3, l4 in zip(ls[0::4], ls[1::4], ls[2::4], ls[3::4]):
            sd = Stars.StarData()
            lst = l1.split()
            sd.ra = float(lst[2]) * (2 * pi / 24)
            sd.dec = float(lst[3]) * (2 * pi / 360)
            sd.mag = float(lst[4])
            specl = l4.strip()[:2]
            sd.col = Stars._specl_to_color(specl)
            if sd.col is not None: # known spectral class
                stardata.append(sd)

        return stardata


    _specl_color = [
            ("O", rgba(154, 175, 255, 1.0)),
            ("B", rgba(202, 215, 255, 1.0)),
            ("A", rgba(248, 247, 255, 1.0)),
            ("F", rgba(252, 255, 211, 1.0)),
            ("G", rgba(255, 242, 161, 1.0)),
            ("K", rgba(255, 163, 81, 1.0)),
            ("M", rgba(255, 97, 81, 1.0)),
    ]
    _specl_color_map = None

    @staticmethod
    def _specl_to_color (specl):

        if Stars._specl_color_map is None:
            spcl = Stars._specl_color
            Stars._specl_color_map = dict(
                (spcl[i][0],
                 (spcl[i][1],
                  spcl[i + 1][1] if i + 1 < len(spcl)
                                 else spcl[i][1]))
                for i in range(len(spcl)))

        l = specl[:1]
        d = specl[1:]
        if not l in Stars._specl_color_map or not d.isdigit():
            return None # unknown spectral class
        d = int(d)
        if not 0 <= d <= 9:
            return None # unknown spectral subclass
        el = Stars._specl_color_map[l]
        c1, c2 = el
        ifac = float(d) / 10
        color = c1 + (c2 - c1) * ifac
        return color

    _gvformat = None

    @staticmethod
    def _make_star_sphere (stardata, radius,
                           mag1, mag2, size1, size2, alpha1, alpha2,
                           poly1, poly2):

        randgen = Random(101)

        gvformat = Stars._gvformat
        if gvformat is None:
            gvarray = GeomVertexArrayFormat()
            gvarray.addColumn(InternalName.getVertex(), 3,
                              Geom.NTFloat32, Geom.CPoint)
            gvarray.addColumn(InternalName.getColor(), 4,
                              Geom.NTFloat32, Geom.CColor)
            gvarray.addColumn(InternalName.make("offcenter"), 3,
                              Geom.NTFloat32, Geom.CVector)
            gvarray.addColumn(InternalName.make("shimmer"), 4,
                              Geom.NTFloat32, Geom.CVector)
            gvformat = GeomVertexFormat()
            gvformat.addArray(gvarray)
            gvformat = GeomVertexFormat.registerFormat(gvformat)
            Stars._gvformat = gvformat

        # Derive visual star data.
        minsize = radians(1e-4)
        minalpha = 1e-4
        nverts = 0
        ntris = 0
        for sd in stardata:
            rmag = (sd.mag - mag1) / (mag2 - mag1)
            sd.size = size1 + (size2 - size1) * rmag
            sd.alpha = min(alpha1 + (alpha2 - alpha1) * rmag, 1.0)
            if sd.size >= minsize and sd.alpha >= minalpha:
                sd.npoly = max(int(round(poly1 + (poly2 - poly1) * rmag)), 4)
                nverts += sd.npoly + 1
                ntris += sd.npoly
            else:
                sd.npoly = 0

        gvdata = GeomVertexData("starsphere", gvformat, Geom.UHStatic)
        gvdata.uncleanSetNumRows(nverts)
        gvwvertex = GeomVertexWriter(gvdata, InternalName.getVertex())
        gvwcolor = GeomVertexWriter(gvdata, InternalName.getColor())
        gvwoffcenter = GeomVertexWriter(gvdata, "offcenter")
        gvwshimmer = GeomVertexWriter(gvdata, "shimmer")
        gtris = GeomTriangles(Geom.UHStatic)
        gvdtris = gtris.modifyVertices()
        gvdtris.uncleanSetNumRows(ntris * 3)
        gvwtris = GeomVertexWriter(gvdtris, 0)

        iv0 = 0
        # NOTE: Double precision for rotation because radius >> prad.
        rot = QuatD()
        pxf = lambda x, y, z: Point3(*rot.xform(Point3D(x, y, z)))
        for sd in stardata:
            if sd.npoly == 0:
                continue
            prad = radius * sd.size
            rot.setHpr(Vec3D(degrees(sd.ra), degrees(sd.dec), 0.0))
            cp = pxf(0.0, radius, 0.0)
            gvwvertex.addData3f(*cp)
            gvwcolor.addData4f(1.0, 1.0, 1.0, sd.alpha)
            gvwoffcenter.addData3f(*Vec3())
            da = 2 * pi / sd.npoly
            for ip in range(sd.npoly):
                a = -da * ip
                # NOTE: First point on vertical z.
                p = pxf(prad * sin(a), radius, prad * cos(a))
                gvwvertex.addData3f(*p)
                gvwcolor.addData4f(sd.col[0], sd.col[1], sd.col[2], sd.alpha)
                oc = p - cp
                gvwoffcenter.addData3f(*oc)
            twopi = 2 * pi
            omg = randgen.uniform(twopi / 0.5, twopi / 1.0)
            phi = randgen.uniform(0.0, twopi)
            szf = randgen.uniform(0.05, 0.10)
            brf = randgen.uniform(0.10, 0.30)
            gvwshimmer.addData4f(omg, phi, 0.0, brf)
            for ip in range(sd.npoly):
                gvwshimmer.addData4f(omg, phi, szf, 0.0)
            for ip in range(sd.npoly):
                ip1 = ip + 1 if ip + 1 < sd.npoly else 0
                #gtris.addVertices(iv0, iv0 + 1 + ip, iv0 + 1 + ip1)
                gvwtris.addData1i(iv0)
                gvwtris.addData1i(iv0 + 1 + ip)
                gvwtris.addData1i(iv0 + 1 + ip1)
                #gtris.closePrimitive()
            iv0 += sd.npoly + 1

        geom = Geom(gvdata)
        geom.addPrimitive(gtris)
        gnode = GeomNode("starsphere")
        gnode.addGeom(geom)

        node = NodePath("starsphere")
        node.attachNewNode(gnode)
        node.setTransparency(TransparencyAttrib.MAlpha)
        #node.setAttrib(ColorAttrib.makeVertex())

        return node
# @cache-key-end: stars-generation


    _shader_cache = {}

    @staticmethod
    def _make_shader (shdinp):

        shdkey = ()
        shader = Stars._shader_cache.get(shdkey)
        if shader is not None:
            return shader

        vshstr = GLSL_PROLOGUE
        vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;

struct GameTime {
    vec4 ambient;
};
uniform GameTime %(gtimen)s;

uniform float alpha;
uniform float sizefac;

in vec4 p3d_Vertex;
in vec4 p3d_Color;

in vec3 offcenter;
in vec4 shimmer;

out vec4 l_color;
out vec4 l_bloom;

void main ()
{
    float t = %(gtimen)s.ambient.x;
    float omg = shimmer.x;
    float phi = shimmer.y;
    float szf = shimmer.z;
    float brf = shimmer.w;
    float targ = omg * t + phi;
    float shfac = (sin(targ) + sin(targ * 1.39) + sin(targ * 0.47)) / 3.0;

    vec3 p = p3d_Vertex.xyz;
    vec3 oc = offcenter.xyz;
    vec3 c = p - oc;
    float szshfac = 1.0 + shfac * szf;
    vec3 p1 = c + oc * sizefac * szshfac;
    gl_Position = p3d_ModelViewProjectionMatrix * vec4(p1, 1.0);

    float colshfac = 1.0 + shfac * brf;
    l_color = p3d_Color * colshfac;
    l_color.a *= alpha;

    //l_bloom.a = ((shfac + 1.0) * 0.5) * brf;
    //l_bloom.rgb = l_color.rgb * l_bloom.a;
    l_bloom = vec4(0.0, 0.0, 0.0, 0.0);
}
""" % shdinp

        fshstr = GLSL_PROLOGUE
        ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
        odeclstr, ocolorn, osunvisn = ret[:3]
        if base.with_bloom:
            obloomn = ret[3]
        fshstr += """
in vec4 l_color;
in vec4 l_bloom;
"""
        fshstr += odeclstr
        fshstr += """
void main ()
{
    vec4 color = l_color;
    vec4 bloom = l_bloom;
"""
        if base.with_glow_add and not base.with_bloom:
            fshstr += """
    color.rgb += bloom.rgb;
"""
        fshstr += """
    %(ocolorn)s = color;
    %(osunvisn)s = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
        if base.with_bloom:
            fshstr += """
    %(obloomn)s = bloom;
""" % locals()
        fshstr += """
}
"""

        if 0:
            printsh((vshstr, fshstr), "stars-shader")
        shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
        Stars._shader_cache[shdkey] = shader
        return shader


    def _input_shader (self, dt, tmf):

        camfov = degrees(self.world.vfov)
        if self._camfov != camfov:
            self._camfov = camfov
            if self._reffov is not None:
                sf = float(self._camfov) / self._reffov
            else:
                sf = 1.0
            self.node.setShaderInput("sizefac", sf)

        if self.world.frame < 3:
            self._updwait_shdinp_alpha = 0.0
        self._updwait_shdinp_alpha -= dt * tmf
        if self._updwait_shdinp_alpha <= 0.0:
            self._updwait_shdinp_alpha += self._updperiod_shdinp_alpha
            alpha = self.node.getSa()
            self.node.setShaderInput("alpha", alpha)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        self._input_shader(self.world.dt, self.world.day_time_factor)

        return task.cont


