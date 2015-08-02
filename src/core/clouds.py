# -*- coding: UTF-8 -*-

from array import array
import cPickle as pickle
from math import pi, degrees, ceil, sqrt, sin, cos, acos, atan2
import os
from random import Random
from shutil import rmtree
from time import time

from pandac.PandaModules import Vec3, Vec4, Point3, Quat
from pandac.PandaModules import NodePath, LODNode
from pandac.PandaModules import Texture, PNMImage
from pandac.PandaModules import TransparencyAttrib, AntialiasAttrib
from pandac.PandaModules import GeomVertexArrayFormat, InternalName
from pandac.PandaModules import GeomVertexFormat
from pandac.PandaModules import GeomVertexWriter, GeomVertexData
from pandac.PandaModules import Geom, GeomNode, GeomTriangles
from pandac.PandaModules import Shader

from src import join_path, path_exists, path_dirname
from src import internal_path, real_path, full_path
from src import GLSL_PROLOGUE
from src.core.misc import AutoProps, SimpleProps, v3t4, set_texture
from src.core.misc import get_cache_key_section, key_to_hex, intl01v
#from src.core.misc import Random
from src.core.misc import report, dbgval
from src.core.shader import make_shdfunc_amblit
from src.core.shader import make_shdfunc_fogbln, make_shdfunc_fogapl
from src.core.shader import make_shdfunc_sunbln
from src.core.shader import make_frag_outputs
from src.core.shader import printsh
from src.core.table import UnitGrid2
from src.core.transl import *


class Clouds (object):

    def __init__ (self, world, sizex, sizey, visradius,
                  altitude, cloudwidth, cloudheight1, cloudheight2,
                  quaddens, quadsize, texture, texuvparts,
                  glowmap=None, cloudshape=0,
                  cloudmap=None, mingray=None, maxgray=None, clouddens=1.0,
                  wtilesizex=40000.0, wtilesizey=40000.0,
                  vsortbase=2, vsortdivs=0,
                  loddists=None, lodredfac=0.5, lodaccum=False,
                  maxnumquads=None, randseed=None, cloudbound=False,
                  sunblend=(), moonblend=(),
                  name=None):

        timeit = False

        sizex = float(sizex)
        sizey = float(sizey)
        wtilesizex = float(wtilesizex)
        wtilesizey = float(wtilesizey)
        if cloudshape not in (0, 1):
            raise StandardError("Unknown cloud shape '%s'." % cloudshape)
        visradius = float(visradius)

        if not loddists:
            loddists = []
        numlods = len(loddists) + 1

# @cache-key-start: clouds-generation
        carg = AutoProps(
            sizex=sizex, sizey=sizey,
            wtilesizex=wtilesizex, wtilesizey=wtilesizey,
            altitude=altitude, cloudwidth=cloudwidth,
            cloudheight1=cloudheight1, cloudheight2=cloudheight2,
            quaddens=quaddens, quadsize=quadsize, texuvparts=texuvparts,
            cloudshape=cloudshape,
            cloudmap=cloudmap, mingray=mingray, maxgray=maxgray,
            clouddens=clouddens, vsortbase=vsortbase, vsortdivs=vsortdivs,
            numlods=numlods, lodredfac=lodredfac, lodaccum=lodaccum,
            maxnumquads=maxnumquads, randseed=randseed, cloudbound=cloudbound,
        )
        ret = None
        keyhx = None
        if name and isinstance(cloudmap, basestring):
            tname = name
            fckey = [cloudmap]
            this_path = internal_path("data", __file__)
            key = (sorted(carg.props()),
                   get_cache_key_section(this_path.replace(".pyc", ".py"),
                                         "clouds-generation"))
            keyhx = key_to_hex(key, fckey)
# @cache-key-end: clouds-generation
            if timeit:
                t1 = time()
# @cache-key-start: clouds-generation
            ret = self._load_from_cache(tname, keyhx)
# @cache-key-end: clouds-generation
            if timeit:
                t2 = time()
                dbgval(1, "clouds-load-from-cache",
                       (t2 - t1, "%.3f", "time", "s"))
# @cache-key-start: clouds-generation
        if not ret:
            if timeit:
                t1 = time()
            ret = Clouds._construct(**dict(carg.props()))
            celldata, vsortdata, geomdata = ret
            if keyhx is not None:
# @cache-key-end: clouds-generation
                if timeit:
                    t1 = time()
# @cache-key-start: clouds-generation
                Clouds._write_to_cache(tname, keyhx, celldata, vsortdata, geomdata)
# @cache-key-end: clouds-generation
                if timeit:
                    t2 = time()
                    dbgval(1, "clouds-write-to-cache",
                           (t2 - t1, "%.3f", "time", "s"))
# @cache-key-start: clouds-generation
        else:
            celldata, vsortdata, geomdata = ret
# @cache-key-end: clouds-generation

        self.world = world

        numtilesx, numtilesy, tilesizex, tilesizey, numlods, offsetz = celldata
        vsortdirs, vsmaxoffangs, vsnbinds = vsortdata
        clroot, clbroot = geomdata

        self._cloudshape = cloudshape

        self.node = world.node.attachNewNode("clouds")
        clroot.reparentTo(self.node)
        clroot.setPos(0.0, 0.0, offsetz)
        self.world.add_altbin_node(clroot)
        cloudbound = clbroot.getChildren().isEmpty()
        if cloudbound:
            clbroot.reparentTo(self.node)

        # Setup view direction handling.
        self._vsortdirs = list(enumerate(vsortdirs))
        self._vsmaxoffangs = vsmaxoffangs
        self._vsnbvdirs = [(  [(i, vsortdirs[i])]
                            + [(j, vsortdirs[j]) for j in vsnbinds1])
                           for i, vsnbinds1 in enumerate(vsnbinds)]
        self._vsortdir_index = 0

        # Setup LOD handling.
        tileradius = 0.5 * sqrt(tilesizex**2 + tilesizey**2)
        if visradius > 0.0:
            outvisradius = visradius + tileradius
        else:
            outvisradius = 0.0
        actloddists = [0.0]
        actloddists.extend(ld for ld in loddists if ld < outvisradius)
        for kl in range(len(actloddists), numlods + 1):
            actloddists.append(outvisradius)

        # Initialize view direction and LOD handling per tile,
        # and collect data for loop.
        self._vtilings = []
        cvsind = self._vsortdir_index
        for vtiling in clroot.getChildren():
            self._vtilings.append(vtiling)
            for ijtile in vtiling.getChildren():
                tlod = ijtile.node()
                for kl in xrange(numlods):
                    tlod.setSwitch(kl, actloddists[kl + 1], actloddists[kl])
            vtiling.hide()
        self._vtilings[cvsind].show()

        # Setup tile rendering.
        clroot.setDepthWrite(False)
        clroot.setTransparency(TransparencyAttrib.MAlpha)
        clroot.setAntialias(AntialiasAttrib.MNone)
        if self._cloudshape == 1:
            clroot.setTwoSided(True)
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)

        self._min_amblfac = 1.0
        self._min_sunlfac = 0.4
        self._min_moonlfac = 0.6
        self._shdinp = SimpleProps()
        self._shdinp.amblfacn = "INamblfac"
        self._shdinp.sunlfacn = "INsunlfac"
        self._shdinp.moonlfacn = "INmoonlfac"
        shdinp = SimpleProps(**dict(self.world.shdinp.items() + self._shdinp.items()))
        shader = Clouds._make_shader(self._cloudshape, shdinp, glow,
                                     sunblend, moonblend)
        clroot.setShader(shader)
        set_texture(clroot, texture=texture, glowmap=glowmap,
                    filtr=False, clamp=True)
        self.node.setShaderInput(self._shdinp.amblfacn, 1.0)
        self.node.setShaderInput(self._shdinp.sunlfacn, 1.0)
        self.node.setShaderInput(self._shdinp.moonlfacn, 1.0)

        if cloudbound:
            # Initialize LOD handling per bounds tile.
            for cbtile in clbroot.getChildren():
                cblod = cbtile.node()
                cblod.setSwitch(0, outvisradius, 0.0)

            # Setup bounds tile rendering.
            btexture = base.load_texture("data", "images/ui/red.png")
            clbroot.setTexture(btexture)
            clbroot.setRenderModeWireframe()

        # Update states.
        self._updwait_vsortdir = 0.0
        self._updperiod_vsortdir = 0.267
        if self._cloudshape == 0:
            self._updwait_shdinp_refup = 0.0
            self._updperiod_shdinp_refup = 0.137
            self._prev_ref_up = Vec3(0.0, 0.0, 1.0)
        self._updwait_light_fac = 0.0
        self._updperiod_light_fac = 5.12

        self._input_shader(0.0, self.world.day_time_factor) # initialize
        self.alive = True
        base.taskMgr.add(self._loop, "clouds-loop")


# @cache-key-start: clouds-generation
    _gvformat = {}
    _bgvformat = None

    @staticmethod
    def _construct (sizex, sizey, wtilesizex, wtilesizey,
                    altitude, cloudwidth, cloudheight1, cloudheight2,
                    quaddens, quadsize, texuvparts,
                    cloudshape, cloudmap, mingray, maxgray, clouddens,
                    vsortbase, vsortdivs, numlods, lodredfac, lodaccum,
                    maxnumquads, randseed, cloudbound):

# @cache-key-end: clouds-generation
        report(_("Constructing clouds."))
        timeit = False
# @cache-key-start: clouds-generation

# @cache-key-end: clouds-generation
        if timeit:
            t0 = time()
            t1 = t0
# @cache-key-start: clouds-generation

        randgen = Random(randseed)

        # Derive cell data.
        def derive_cell_data (size, wtilesize):
            numtiles = int(ceil(size / wtilesize))
            tilesize = size / numtiles
            return numtiles, tilesize
        ret = derive_cell_data(sizex, wtilesizex)
        numtilesx, tilesizex = ret
        ret = derive_cell_data(sizey, wtilesizey)
        numtilesy, tilesizey = ret

        # Load cloud map.
        if isinstance(cloudmap, basestring):
            cloudmap = UnitGrid2(full_path("data", cloudmap))
        elif isinstance(cloudmap, PNMImage):
            cloudmap = UnitGrid2(cloudmap)
        elif cloudmap is None:
            cloudmap = UnitGrid2(0.0)

        # Derive any non-initialized cloudmap data.
        if isinstance(quadsize, (int, float)):
            quadsize = (quadsize, quadsize)
        if mingray is None:
            mingray = 0
        if maxgray is None:
            maxgray = 255
        if isinstance(altitude, (int, float)):
            altitude = (altitude, altitude)
        altitude = map(float, altitude)
        if isinstance(cloudwidth, (int, float)):
            cloudwidth = (cloudwidth, cloudwidth)
        cloudwidth = map(float, cloudwidth)
        if isinstance(cloudheight1, (int, float)):
            cloudheight1 = (cloudheight1, cloudheight1)
        cloudheight1 = map(float, cloudheight1)
        if isinstance(cloudheight2, (int, float)):
            cloudheight2 = (cloudheight2, cloudheight2)
        cloudheight2 = map(float, cloudheight2)

        cloudheight1 = sorted(cloudheight1)
        if cloudheight1[0] >= 0.0 or cloudheight1[1] >= 0.0:
            raise StandardError(
                "Parameter '%s' must be smaller than zero." % "cloudheight1")
        cloudheight2 = sorted(cloudheight2)
        if cloudheight2[0] <= 0.0 or cloudheight2[1] <= 0.0:
            raise StandardError(
                "Parameter '%s' must be greater than zero." % "cloudheight2")

        # Distribute clouds.
        mingu = float(mingray) / 255
        maxgu = float(maxgray) / 255
        fgu0 = 1.0 / (maxgu - mingu)
        fgu1 = -mingu * fgu0
        mincloudwidth, maxcloudwidth = cloudwidth
        sizex = numtilesx * tilesizex
        sizey = numtilesy * tilesizey
        midsize = 0.5 * (sizex + sizey)
        ntc = int(((midsize / maxcloudwidth) * clouddens)**2)
        nsmpxy = 5
        dxypu = (maxcloudwidth / midsize) / nsmpxy
        dxypu0 = -0.5 * (dxypu * nsmpxy)
        cloudspecs = []
        cloudvol = []
        minavggu = 0.1
        offsetx = -0.5 * sizex
        offsety = -0.5 * sizey
        minaltitude, maxaltitude = altitude
        offsetz = 0.5 * (minaltitude + maxaltitude)
        # ...+ offsetz will be set at top node, for proper altitude binning.
        dz1 = minaltitude - offsetz
        dz2 = maxaltitude - offsetz
        mincloudheight1, maxcloudheight1 = cloudheight1[0], cloudheight1[1]
        mincloudheight2, maxcloudheight2 = cloudheight2[0], cloudheight2[1]
        for kc in xrange(ntc):
            xcu = randgen.uniform(0.0, 1.0)
            ycu = randgen.uniform(0.0, 1.0)
            # Quick check to avoid nsmpxy**2 samplings on coarser cloud maps.
            if cloudmap(xcu, ycu, periodic=True) == 0.0:
                continue
            avggu = 0.0
            for ip in xrange(nsmpxy):
                xpu = xcu + dxypu0 + dxypu * ip
                for jp in xrange(nsmpxy):
                    ypu = ycu + dxypu0 + dxypu * jp
                    gu = cloudmap(xpu, ypu, periodic=True)
                    avggu += min(max(gu * fgu0 + fgu1, 0.0), 1.0)
            avggu /= nsmpxy**2
            if avggu < minavggu:
                continue
            cwidth = randgen.uniform(mincloudwidth, maxcloudwidth) * avggu
            cheight1 = randgen.uniform(mincloudheight1, maxcloudheight1) * avggu
            cheight2 = randgen.uniform(mincloudheight2, maxcloudheight2) * avggu
            xc = xcu * sizex + offsetx
            yc = ycu * sizey + offsety
            zc = randgen.uniform(dz1, dz2) * avggu
            pc = Point3(xc, yc, zc)
            cquads = [0] * numlods
            cloudspecs.append((pc, cwidth, cheight1, cheight2, cquads))
            if cloudshape == 0:
                cvol = (1.333 * pi) * (0.5 * cwidth)**2 * (0.5 * (cheight2 - cheight1))
            elif cloudshape == 1:
                cvol = pi * (0.5 * cwidth)**2 * (cheight2 - cheight1)
            cloudvol.append(cvol)
# @cache-key-end: clouds-generation
        if timeit:
            t2 = time()
            dbgval(1, "clouds-distribute",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        # Number of quads per LOD level.
        sumcloudvol = sum(cloudvol)
        if quaddens > 0.0:
            numquads = int(quaddens * sumcloudvol)
        else:
            numquads = int(-quaddens)
        if maxnumquads is not None:
            numquads = min(numquads, maxnumquads)
        quaddens1 = numquads / sumcloudvol if sumcloudvol > 0.0 else 0.0
        if lodaccum:
            plrfac = [lodredfac**kl for kl in xrange(numlods)]
            sumplrfac = sum(plrfac)
            plqfac = [x / sumplrfac for x in plrfac]
            numquads = [int(numquads * x) for x in plqfac]
        else:
            numquads = [numquads]
            for kl in xrange(1, numlods):
                numquads.append(int(numquads[-1] * lodredfac))

        # Distribute quads among clouds.
        numclouds = len(cloudspecs)
        for kl in xrange(numlods):
            cloudvol_m = array("d", cloudvol)
            numquads_m = numquads[kl]
            while True:
                if numquads_m <= 0:
                    break
                sumcloudvol = sum(cloudvol_m)
                midcloudvol = 0.9 * (min(cloudvol_m) + max(cloudvol_m))
                numquads_ms = 0
                for kc in xrange(numclouds):
                    cq = int(numquads_m * (cloudvol_m[kc] / sumcloudvol))
                    if cq == 0 and cloudvol_m[kc] > midcloudvol:
                        cq += 1
                    cq = min(cq, numquads_m - numquads_ms)
                    cloudspecs[kc][4][kl] += cq
                    numquads_ms += cq
                    if numquads_ms == numquads_m:
                        break
                    cloudvol_m[kc] -= (cq * sumcloudvol) / numquads_m
                    cloudvol_m[kc] = max(cloudvol_m[kc], 0.0)
                numquads_m -= numquads_ms
        # Eliminate zero-quad clouds.
        cloudspecs_m = []
        refkl = numlods - 1
        for cloudspec in cloudspecs:
            if cloudspec[4][refkl] > 0:
                cloudspecs_m.append(cloudspec)
            else:
                for kl in xrange(numlods):
                    numquads[kl] -= cloudspec[4][kl]
        cloudspecs = cloudspecs_m
        numclouds = len(cloudspecs)
# @cache-key-end: clouds-generation
        if timeit:
            if lodaccum:
                cqs1 = [0] * numclouds
            for kl in reversed(xrange(numlods)):
                cqs1na = [cs[4][kl] for cs in cloudspecs]
                nqs1na = sum(cqs1na)
                if lodaccum:
                    cqs1 = [x + y for x, y in zip(cqs1, cqs1na)]
                else:
                    cqs1 = cqs1na
                nqs1 = sum(cqs1)
                dbgval(1, "clouds-quads-in-lod",
                       (kl, "%d", "lod"),
                       (quaddens1 * 1e9, "%.1f", "quaddens", "1/km^3"),
                       (nqs1, "%d", "numquads"),
                       (nqs1na, "%d", "numquads1"),
                       (min(cqs1), "%d", "minqpc"),
                       (max(cqs1), "%d", "maxqpc"),
                       (float(nqs1) / numclouds, "%.2f", "avgqpc"))
        if timeit:
            t2 = time()
            dbgval(1, "clouds-distribute-quads",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        # Create view direction sorting data.
        if vsortbase >= 0:
            ret = geodesic_sphere(base=vsortbase, numdivs=vsortdivs)
            vsortdirs, vsmaxoffangs, vsnbinds = ret[2:5]
# @cache-key-end: clouds-generation
            if timeit:
                vsavgmaxoffang = sum(vsmaxoffangs) / len(vsortdirs)
                vsmaxoffangsd = (sum((ma - vsavgmaxoffang)**2 for ma in vsmaxoffangs) /
                                 (len(vsortdirs) - 1))**0.5
                dbgval(1, "clouds-view-sorting",
                       (len(vsortdirs), "%d", "numvsortdirs"),
                       (degrees(max(vsmaxoffangs)), "%.1f", "maxmaxoffang", "deg"),
                       (degrees(min(vsmaxoffangs)), "%.1f", "minmaxoffang", "deg"),
                       (degrees(vsavgmaxoffang), "%.1f", "avgmaxoffang", "deg"),
                       (degrees(vsmaxoffangsd), "%.2f", "maxoffangsd", "deg"))
# @cache-key-start: clouds-generation
        else:
            vsortdirs = [Vec3(0.0, 1.0, 0.0)]
            vsmaxoffangs = [pi + 1e-6]
            vsnbinds = [[]]
        numvsortdirs = len(vsortdirs)

        # Vertex format for cloud textures.
        gvformat = Clouds._gvformat.get(cloudshape)
        if gvformat is None:
            gvarray = GeomVertexArrayFormat()
            gvarray.addColumn(InternalName.getVertex(), 3,
                              Geom.NTFloat32, Geom.CPoint)
            gvarray.addColumn(InternalName.getTexcoord(), 2,
                              Geom.NTFloat32, Geom.CTexcoord)
            if cloudshape == 0:
                gvarray.addColumn(InternalName.make("offcenter"), 3,
                                Geom.NTFloat32, Geom.CVector)
                gvarray.addColumn(InternalName.make("grpoffcenter"), 3,
                                Geom.NTFloat32, Geom.CVector)
                gvarray.addColumn(InternalName.make("haxislen"), 4,
                                Geom.NTFloat32, Geom.CVector)
            gvformat = GeomVertexFormat()
            gvformat.addArray(gvarray)
            gvformat = GeomVertexFormat.registerFormat(gvformat)
            Clouds._gvformat[cloudshape] = gvformat

        # Initialize tiles.
        class Data: pass
        tilespecs = []
        for it in xrange(numtilesx):
            tilespecs1 = []
            tilespecs.append(tilespecs1)
            for jt in xrange(numtilesy):
                ts = Data()
                ts.pos = Point3(offsetx + (it + 0.5) * tilesizex,
                                offsety + (jt + 0.5) * tilesizey,
                                0.0)
                ts.gvdata = GeomVertexData("cloud", gvformat, Geom.UHStatic)
                ts.gvwvertex = GeomVertexWriter(ts.gvdata, InternalName.getVertex())
                ts.gvwtexcoord = GeomVertexWriter(ts.gvdata, InternalName.getTexcoord())
                if cloudshape == 0:
                    ts.gvwoffcenter = GeomVertexWriter(ts.gvdata, "offcenter")
                    ts.gvwgrpoffcenter = GeomVertexWriter(ts.gvdata, "grpoffcenter")
                    ts.gvwhaxislen = GeomVertexWriter(ts.gvdata, "haxislen")
                ts.gtris = [[GeomTriangles(Geom.UHStatic) for kl in xrange(numlods)]
                            for kv in xrange(numvsortdirs)]
                ts.qvspecs = [[] for kl in xrange(numlods)]
                ts.nverts = 0
                tilespecs1.append(ts)

        # Create quads.
        minquadsize, maxquadsize = quadsize
        minquadsizes, maxquadsizes = [], []
        qszplod = float(maxquadsize - minquadsize) / (numlods // 2 + 1)
        for kl in xrange(numlods):
            minquadsizes.append(minquadsize + qszplod * kl)
            maxquadsizes.append(maxquadsize)
        if cloudshape == 0:
            vfw = Vec3(0.0, 1.0, 0.0)
            vup = Vec3(0.0, 0.0, 1.0)
        elif cloudshape == 1:
            vfw = Vec3(0.0, 0.0, 1.0)
            vup = Vec3(0.0, 1.0, 0.0)
        vrt = vfw.cross(vup)
        rot = Quat()
        krt_kup = ((+1, -1), (-1, -1), (-1, +1), (+1, +1))
        for ic, cloudspec in enumerate(cloudspecs):
            cpos, cwidth, cheight1, cheight2, cquads = cloudspec
            assert cheight1 < 0.0 and cheight2 > 0.0
            hx = 0.5 * cwidth
            hy = 0.5 * cwidth
            hz1 = -cheight1
            hz2 = cheight2
            for kl in xrange(numlods):
                lminquadsize = minquadsizes[kl]
                lmaxquadsize = maxquadsizes[kl]
                dhsz = 0.5 * (lminquadsize - minquadsize)
                lhx = max(hx + dhsz, 0.0)
                lhy = max(hy + dhsz, 0.0)
                lhz1 = max(hz1 + dhsz, 0.0)
                lhz2 = max(hz2 + dhsz, 0.0)
                lcqspecs = []
                kq = 0
                while kq < cquads[kl]:
                    qoff = Point3(randgen.uniform(-lhx, lhx),
                                  randgen.uniform(-lhy, lhy),
                                  randgen.uniform(-lhz1, lhz2))
                    if cloudshape == 0:
                        rad = qoff.length()
                        tht = atan2(qoff[1], qoff[0])
                        phi = acos(qoff[2] / rad)
                        stht, ctht = sin(tht), cos(tht)
                        sphi, cphi = sin(phi), cos(phi)
                        hz = hz1 if qoff[2] < 0.0 else hz2
                        rad0 = 1.0 / sqrt(ctht**2 * sphi**2 / hx**2 +
                                          stht**2 * sphi**2 / hy**2 +
                                          cphi**2 / hz**2)
                        inside = (rad <= rad0)
                    elif cloudshape == 1:
                        rad = qoff.getXy().length()
                        rad0 = sqrt(hx**2 + hy**2)
                        inside = (rad <= rad0)
                    if inside:
                        qsz = randgen.uniform(lminquadsize, lmaxquadsize)
                        lcqspecs.append((qoff, qsz))
                        kq += 1
                for qoff, qsz in lcqspecs:
                    qpos = cpos + qoff
                    it = min(max(int((qpos[0] - offsetx) / tilesizex), 0), numtilesx - 1)
                    jt = min(max(int((qpos[1] - offsety) / tilesizey), 0), numtilesy - 1)
                    ts = tilespecs[it][jt]
                    qtpos = qpos - ts.pos
                    ang = randgen.uniform(-pi, pi)
                    rot.setFromAxisAngleRad(ang, vfw)
                    drt = Vec3(rot.xform(vrt)) * (0.5 * qsz)
                    dup = Vec3(rot.xform(vup)) * (0.5 * qsz)
                    uoff, voff, ulen, vlen = randgen.choice(texuvparts)
                    for krt, kup in krt_kup:
                        poff = drt * krt + dup * kup
                        ts.gvwvertex.addData3f(*(qtpos + poff))
                        qpoff = qoff + poff
                        qprad = qpoff.length()
                        klu = (1 - krt) / 2; klv = (1 + kup) / 2
                        ts.gvwtexcoord.addData2f(uoff + ulen * klu,
                                                 voff + vlen * klv)
                        if cloudshape == 0:
                            ts.gvwoffcenter.addData3f(*poff)
                            ts.gvwgrpoffcenter.addData3f(*qoff)
                            ts.gvwhaxislen.addData4f(hx, hy, hz1, hz2)
                    ts.qvspecs[kl].append((qtpos, ts.nverts))
                    ts.nverts += 4
# @cache-key-end: clouds-generation
        if timeit:
            t2 = time()
            dbgval(1, "clouds-create-vertices",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        # Create tiles.
        for tilespecs1 in tilespecs:
            for ts in tilespecs1:
                for vd, gtris in zip(vsortdirs, ts.gtris):
                    for qvspecs in ts.qvspecs:
                        qvspecs.sort(key=lambda qs: -(qs[0].dot(vd)))
                    for kl, gtris1 in enumerate(gtris):
                        if lodaccum:
                            qvspecs = ts.qvspecs[kl:]
                        else:
                            qvspecs = [ts.qvspecs[kl]]
                        for qvspecs1 in qvspecs:
                            for qtpos, kv0 in qvspecs1:
                                gtris1.addVertices(kv0 + 0, kv0 + 1, kv0 + 2)
                                gtris1.closePrimitive()
                                gtris1.addVertices(kv0 + 0, kv0 + 2, kv0 + 3)
                                gtris1.closePrimitive()
# @cache-key-end: clouds-generation
        if timeit:
            t2 = time()
            dbgval(1, "clouds-create-triangles",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        # Finalize tiles.
        clroot = NodePath("clouds")
        tileradius = 0.5 * sqrt(tilesizex**2 + tilesizey**2)
        tiles = []
        for kv in xrange(numvsortdirs):
            vtiling = clroot.attachNewNode("tiling-v%d" % kv)
            for it in xrange(numtilesx):
                for jt in xrange(numtilesy):
                    ts = tilespecs[it][jt]
                    tlod = LODNode("tile-v%d-i%d-j%d" % (kv, it, jt))
                    ijtile = vtiling.attachNewNode(tlod)
                    ijtile.setPos(ts.pos)
                    for kl in xrange(numlods):
                        tname = "tile-v%d-i%d-j%d-l%d" % (kv, it, jt, kl)
                        gtris = ts.gtris[kv][kl]
                        tgeom = Geom(ts.gvdata)
                        tgeom.addPrimitive(gtris)
                        tnode = GeomNode(tname)
                        tnode.addGeom(tgeom)
                        ltile = NodePath(tnode)
                        tlod.addSwitch(tileradius * (kl + 1), tileradius * kl)
                        ltile.reparentTo(ijtile)
# @cache-key-end: clouds-generation
        if timeit:
            t2 = time()
            dbgval(1, "clouds-create-tiles",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        # Create cloud bounds if requested.
        clbroot = NodePath("bounds")
        if cloudbound:
            if cloudshape not in (0,):
                raise StandardError(
                    "Cloud bounds not yet implemented "
                    "for cloud shape '%s'." % cloudshape)

            # Vertex format for bounds textures.
            bgvformat = Clouds._bgvformat
            if bgvformat is None:
                bgvarray = GeomVertexArrayFormat()
                bgvarray.addColumn(InternalName.getVertex(), 3,
                                   Geom.NTFloat32, Geom.CPoint)
                bgvarray.addColumn(InternalName.getTexcoord(), 2,
                                   Geom.NTFloat32, Geom.CTexcoord)
                bgvformat = GeomVertexFormat()
                bgvformat.addArray(bgvarray)
                bgvformat = GeomVertexFormat.registerFormat(bgvformat)
                Clouds._bgvformat = bgvformat

            # Setup writers.
            for it in xrange(numtilesx):
                for jt in xrange(numtilesy):
                    ts = tilespecs[it][jt]
                    ts.bgvdata = GeomVertexData("bound", bgvformat, Geom.UHStatic)
                    ts.bgvwvertex = GeomVertexWriter(ts.bgvdata, InternalName.getVertex())
                    ts.bgvwtexcoord = GeomVertexWriter(ts.bgvdata, InternalName.getTexcoord())
                    ts.bgtris = GeomTriangles(Geom.UHStatic)

            # Construct bound nodes.
            for cloudspec in cloudspecs:
                cpos, cwidth, cheight1, cheight2 = cloudspec[:4]
                it = min(max(int((cpos[0] - offsetx) / tilesizex), 0), numtilesx - 1)
                jt = min(max(int((cpos[1] - offsety) / tilesizey), 0), numtilesy - 1)
                ts = tilespecs[it][jt]
                bpos = cpos - ts.pos
                Dome._add_dome(gvwvertex=ts.bgvwvertex, gvwnormal=None,
                               gvwcolor=None, gvwtexcoord=ts.bgvwtexcoord,
                               gtris=ts.bgtris,
                               pos=bpos, rot=Vec3(),
                               rad=(0.5 * cwidth), ang=(0.5 * pi),
                               nbprsegs=6, extang=0.0,
                               uoff=0.0, voff=0.0, expalpha=0.0,
                               eggfac=(cheight1 / (0.5 * cwidth)))
                Dome._add_dome(gvwvertex=ts.bgvwvertex, gvwnormal=None,
                               gvwcolor=None, gvwtexcoord=ts.bgvwtexcoord,
                               gtris=ts.bgtris,
                               pos=bpos, rot=Vec3(),
                               rad=(0.5 * cwidth), ang=(0.5 * pi),
                               nbprsegs=6, extang=0.0,
                               uoff=0.0, voff=0.0, expalpha=0.0,
                               eggfac=(cheight2 / (0.5 * cwidth)))

            # Distribute bound nodes over tiles.
            for it in xrange(numtilesx):
                for jt in xrange(numtilesy):
                    ts = tilespecs[it][jt]
                    cbname = "cbound-i%d-j%d" % (it, jt)
                    cblod = LODNode(cbname)
                    cblnd = clbroot.attachNewNode(cblod)
                    cblnd.setPos(ts.pos)
                    cbgeom = Geom(ts.bgvdata)
                    cbgeom.addPrimitive(ts.bgtris)
                    cbgnode = GeomNode(bname)
                    cbgnode.addGeom(bgeom)
                    cbtile = NodePath(cbgnode)
                    cblod.addSwitch(tileradius * (numlods + 1), 0.0)
                    cbtile.reparentTo(cblnd)

# @cache-key-end: clouds-generation
            if timeit:
                t2 = time()
                dbgval(1, "clouds-create-bounds",
                       (t2 - t1, "%.3f", "time", "s"))
                t1 = t2
# @cache-key-start: clouds-generation

# @cache-key-end: clouds-generation
        if timeit:
            t2 = time()
            dbgval(1, "clouds-cumulative",
                   (t2 - t0, "%.3f", "time", "s"))
            t1 = t2
# @cache-key-start: clouds-generation

        celldata = (numtilesx, numtilesy, tilesizex, tilesizey, numlods,
                    offsetz)
        vsortdata = (vsortdirs, vsmaxoffangs, vsnbinds)
        geomdata = (clroot, clbroot)
        return celldata, vsortdata, geomdata


    _cache_pdir = "clouds"

    @staticmethod
    def _cache_key_path (tname):

        return join_path(Clouds._cache_pdir, tname, "clouds.key")


    @staticmethod
    def _cache_celldata_path (tname):

        return join_path(Clouds._cache_pdir, tname, "celldata.pkl")


    @staticmethod
    def _cache_vsortdata_path (tname):

        return join_path(Clouds._cache_pdir, tname, "vsortdata.pkl")


    @staticmethod
    def _cache_geomdata_path (tname):

        return join_path(Clouds._cache_pdir, tname, "geomdata.bam")


    @staticmethod
    def _load_from_cache (tname, keyhx):

        keypath = Clouds._cache_key_path(tname)
        if not path_exists("cache", keypath):
            return None
        okeyhx = open(real_path("cache", keypath), "rb").read()
        if okeyhx != keyhx:
            return None

        celldatapath = Clouds._cache_celldata_path(tname)
        if not path_exists("cache", celldatapath):
            return None
        fh = open(real_path("cache", celldatapath), "rb")
        celldata = pickle.load(fh)
        fh.close()

        vsortdatapath = Clouds._cache_vsortdata_path(tname)
        if not path_exists("cache", vsortdatapath):
            return None
        fh = open(real_path("cache", vsortdatapath), "rb")
        vsortdata = pickle.load(fh)
        fh.close()

        geomdatapath = Clouds._cache_geomdata_path(tname)
        if not path_exists("cache", geomdatapath):
            return None
        geomroot = base.load_model("cache", geomdatapath, cache=False)
        geomdata = geomroot.getChildren().getPaths()

        return celldata, vsortdata, geomdata


    @staticmethod
    def _write_to_cache (tname, keyhx, celldata, vsortdata, geomdata):

        keypath = Clouds._cache_key_path(tname)

        cdirpath = path_dirname(keypath)
        if path_exists("cache", cdirpath):
            rmtree(real_path("cache", cdirpath))
        os.makedirs(real_path("cache", cdirpath))

        geomdatapath = Clouds._cache_geomdata_path(tname)
        geomroot = NodePath("root")
        for np in geomdata:
            np.reparentTo(geomroot)
        base.write_model_bam(geomroot, "cache", geomdatapath)

        vsortdatapath = Clouds._cache_vsortdata_path(tname)
        fh = open(real_path("cache", vsortdatapath), "wb")
        pickle.dump(vsortdata, fh, -1)
        fh.close()

        celldatapath = Clouds._cache_celldata_path(tname)
        fh = open(real_path("cache", celldatapath), "wb")
        pickle.dump(celldata, fh, -1)
        fh.close()

        fh = open(real_path("cache", keypath), "wb")
        fh.write(keyhx)
        fh.close()

# @cache-key-end: clouds-generation

    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    _shader_cache = {}

    @staticmethod
    def _make_shader (cloudshape, shdinp, glow, sunblend, moonblend):

        if isinstance(glow, Vec4):
            glow = tuple(glow)

        shdkey = (cloudshape,
                  shdinp.camn, shdinp.ambln, (shdinp.sunln, shdinp.moonln),
                  shdinp.fogn, glow, tuple(sunblend), tuple(moonblend))
        shader = Clouds._shader_cache.get(shdkey)
        if shader is not None:
            return shader

        vshstr = GLSL_PROLOGUE

        vshstr += make_shdfunc_amblit()
        if sunblend:
            vshstr += make_shdfunc_sunbln(sunblend=sunblend)
        vshstr += make_shdfunc_fogbln(sunblend=sunblend)

        vshstr += """
struct DirLight {
  vec4 diffuse;
  //vec4 specular;
  vec4 position;
};
"""

        vshstr_lfac = """
    float sunlfac = 1.0;
    float moonlfac = 1.0;
    float amblfac = 1.0;
"""
        if sunblend or moonblend:
            vshstr_lfac += """
    vec4 pcv = normalize(pw - wspos_%(camn)s);
    float sundfac = 0.0;
    float moondfac = 0.0;
""" % shdinp
        if sunblend:
            sundexp = sunblend[0]
            vshstr_lfac += """
    sundfac = dot(pcv, normalize(wspos_%(sunposn)s - wspos_%(camn)s));
""" % shdinp
            vshstr_lfac += """
    sundfac = pow(clamp(sundfac, 0.0, 1.0), %(sundexp)f);
""" % locals()
            vshstr_lfac += """
    sunlfac = mix(%(sunlfacn)s, 1.0, sundfac);
""" % shdinp
        if moonblend:
            moondexp = moonblend[0]
            vshstr_lfac += """
    moondfac = dot(pcv, normalize(wspos_%(moonposn)s - wspos_%(camn)s));
""" % shdinp
            vshstr_lfac += """
    moondfac = pow(clamp(moondfac, 0.0, 1.0), %(moondexp)f);
""" % locals()
            vshstr_lfac += """
    moonlfac = mix(%(moonlfacn)s, 1.0, moondfac);
""" % shdinp
        if sunblend or moonblend:
            vshstr_lfac += """
    amblfac = mix(%(amblfacn)s, 1.0, max(sundfac, moondfac));
""" % shdinp

        if cloudshape == 0:
            vshstr += """
void point_on_ellipsoid (vec4 ha0w, vec3 p,
                         out vec3 n)
{
    float r = length(p);
    float tht = atan(p.y, p.x);
    float phi = acos(p.z / r);
    float stht = sin(tht);
    float ctht = cos(tht);
    float sphi = sin(phi);
    float cphi = cos(phi);
    vec3 ha0 = p.z < 0.0 ? ha0w.xyz : ha0w.xyw;
    float r0 = 1.0 / sqrt((ctht * ctht) * (sphi * sphi) / (ha0.x * ha0.x) +
                          (stht * stht) * (sphi * sphi) / (ha0.y * ha0.y) +
                          (cphi * cphi) / (ha0.z * ha0.z));
    vec3 ha = ha0 * (r / r0);
    n = normalize(vec3(p.x / (ha.x * ha.x),
                       p.y / (ha.y * ha.y),
                       p.z / (ha.z * ha.z)));
}
"""
            vshstr += """
const float isqrt3 = 0.577350;
const vec3 ez = vec3(0.0, 0.0, 1.0);

void celbody_cloud_lighting (DirLight lspc, float kcol, vec3 vnrm,
                             inout vec4 lit)
{
    vec3 ldir = lspc.position.xyz;
    vec4 lcol = lspc.diffuse * kcol;

    float strength = length(lcol.xyz) * isqrt3;
    float dirpn = dot(vnrm, ldir);
    //float sctfac = mix(0.0, 1.5, pow(max(dot(ldir, ez), 0.0), 0.2));
    float sctfac = 1.5;
    dirpn += mix(strength * sctfac, 0.0, 0.5 * (dirpn + 1.0));
    float ifac = 0.5 * (dirpn + 1.0);
    vec4 vcol = lcol * ifac;
    lit += vcol;
}
"""
            vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_ModelMatrixInverse;
uniform vec4 wspos_%(camn)s;
uniform vec4 wspos_%(camtargn)s;
uniform vec3 ref_up;
uniform AmbLight %(ambln)s;
uniform DirLight %(sunln)s;
uniform DirLight %(moonln)s;
uniform FogSpec %(fogn)s;
""" % shdinp
            if sunblend or moonblend:
                vshstr += """
uniform float %(amblfacn)s;
""" % shdinp
            if sunblend:
                vshstr += """
uniform vec4 wspos_%(sunposn)s;
uniform SunBlendSpec %(sunbcoln)s;
uniform float %(sunlfacn)s;
""" % shdinp
            if moonblend:
                vshstr += """
uniform vec4 wspos_%(moonposn)s;
uniform float %(moonlfacn)s;
""" % shdinp
            vshstr += """
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 offcenter;
in vec3 grpoffcenter;
in vec4 haxislen;
out vec2 l_texcoord0;
out vec4 l_lit;
out vec4 l_fog;

void main ()
{
    vec4 pw = p3d_ModelMatrix * p3d_Vertex;
    vec3 oc = offcenter;
    vec3 cp = wspos_%(camn)s.xyz;
    vec3 cv = normalize(wspos_%(camtargn)s.xyz - wspos_%(camn)s.xyz);
    vec3 u = normalize(ref_up);
    vec3 c = pw.xyz - oc;
    float ll0 = length(oc) * 4.0;
    float ll1 = ll0 * 2.0;
    vec3 ry0 = -cv;
    vec3 ry1 = cp - c;
    float lry1 = length(ry1); // can be 0
    if (lry1 > ll0) ry1 = normalize(ry1);
    float ifry = smoothstep(ll0, ll1, lry1);
    vec3 ry = normalize(mix(ry0, ry1, ifry));
    vec3 rx = cross(ry, u);
    vec3 rz = normalize(cross(rx, ry));
    mat3 rmat_t = mat3(rx, ry, rz);
    vec3 oc1 = rmat_t * oc;
    vec3 pw1 = c + oc1;
    vec4 p1 = p3d_ModelMatrixInverse * vec4(pw1.xyz, 1.0);
    gl_Position = p3d_ModelViewProjectionMatrix * p1;

    l_texcoord0 = p3d_MultiTexCoord0;
""" % shdinp
            vshstr += vshstr_lfac
            vshstr += """
    l_lit = vec4(0.0, 0.0, 0.0, 0.0);
    amblit(%(ambln)s, amblfac, l_lit);
    vec3 gc = grpoffcenter;
    vec3 gp1 = gc + oc1;
    vec3 n1;
    point_on_ellipsoid(haxislen, gp1, n1);
    vec3 n1v = p3d_NormalMatrix * n1;
    celbody_cloud_lighting(%(sunln)s, sunlfac, n1v, l_lit);
    celbody_cloud_lighting(%(moonln)s, moonlfac, n1v, l_lit);

    l_fog = vec4(0.0, 0.0, 0.0, 0.0);
""" % shdinp
            if sunblend:
                vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw,
           wspos_%(sunposn)s, %(sunbcoln)s.ambient,
           l_fog);
""" % shdinp
            else:
                vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw, l_fog);
""" % shdinp
            vshstr += """
}
"""

        elif cloudshape == 1:
            vshstr += """
void celbody_cloud_lighting (DirLight lspc, float kcol, vec3 vnrm,
                             inout vec4 lit)
{
    vec3 ldir = lspc.position.xyz;
    vec4 lcol = lspc.diffuse * kcol;
    float dirpn = dot(vnrm, ldir);
    float ifac = pow(abs(dirpn), 0.15);
    vec4 vcol = lcol * ifac;
    lit += vcol;
}
"""
            vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
uniform vec4 wspos_%(camn)s;
uniform AmbLight %(ambln)s;
uniform DirLight %(sunln)s;
uniform DirLight %(moonln)s;
uniform FogSpec %(fogn)s;
""" % shdinp
            if sunblend or moonblend:
                vshstr += """
uniform float %(amblfacn)s;
""" % shdinp
            if sunblend:
                vshstr += """
uniform vec4 wspos_%(sunposn)s;
uniform SunBlendSpec %(sunbcoln)s;
uniform float %(sunlfacn)s;
""" % shdinp
            if moonblend:
                vshstr += """
uniform vec4 wspos_%(moonposn)s;
uniform float %(moonlfacn)s;
""" % shdinp
            vshstr += """
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;
out vec4 l_lit;
out vec4 l_fog;

void main ()
{
    vec4 pw = p3d_ModelMatrix * p3d_Vertex;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    l_texcoord0 = p3d_MultiTexCoord0;
""" % shdinp
            vshstr += vshstr_lfac
            vshstr += """
    l_lit = vec4(0.0, 0.0, 0.0, 0.0);
    amblit(%(ambln)s, amblfac, l_lit);
    vec3 n1 = vec3(0.0, 0.0, 1.0);
    vec3 n1v = p3d_NormalMatrix * n1;
    celbody_cloud_lighting(%(sunln)s, sunlfac, n1v, l_lit);
    celbody_cloud_lighting(%(moonln)s, moonlfac, n1v, l_lit);

    l_fog = vec4(0.0, 0.0, 0.0, 0.0);
""" % shdinp
            if sunblend:
                vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw,
           wspos_%(sunposn)s, %(sunbcoln)s.ambient,
           l_fog);
""" % shdinp
            else:
                vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw, l_fog);
""" % shdinp
            vshstr += """
}
"""

        fshstr = GLSL_PROLOGUE

        ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
        odeclstr, ocolorn, osunvisn = ret[:3]
        if base.with_bloom:
            obloomn = ret[3]

        fshstr += make_shdfunc_fogapl()

        fshstr += """
uniform sampler2D p3d_Texture0;
"""
        if glow and not isinstance(glow, tuple):
            fshstr += """
uniform sampler2D p3d_Texture1;
"""
        fshstr += """
in vec2 l_texcoord0;
in vec4 l_lit;
in vec4 l_fog;
"""
        fshstr += odeclstr
        fshstr += """
void main ()
{
    vec4 color = texture(p3d_Texture0, l_texcoord0);
    vec4 lit = l_lit;
""" % shdinp
        if isinstance(glow, tuple):
            gr, gg, gb, ga = glow
            fshstr += """
    vec4 glwm = vec4(%(gr)f, %(gg)f, %(gb)f, %(ga)f);
""" % locals()
        elif glow:
            fshstr += """
    vec4 glwm = texture(p3d_Texture1, l_texcoord0);
"""
        if glow:
            fshstr += """
    lit.rgb += glwm.rgb;
"""
        fshstr += """
    //color.rgb *= clamp(lit.rgb, 0.0, 1.0);
    color.rgb *= lit.rgb; // no cutoff
"""
        fshstr += """
    fogapl(color, l_fog, color);
"""
        if glow:
            fshstr += """
    vec4 bloom;
    bloom.a = glwm.a * color.a;
    bloom.rgb = color.rgb * bloom.a;
"""
        else:
            fshstr += """
    vec4 bloom = vec4(0.0, 0.0, 0.0, color.a);
"""
        if base.with_glow_add and not base.with_bloom:
            fshstr += """
    color.rgb += bloom.rgb;
"""
        fshstr += """
    %(ocolorn)s = color;
    %(osunvisn)s = vec4(0.0, 0.0, 0.0, color.a);
""" % locals()
        if base.with_bloom:
            fshstr += """
    %(obloomn)s = bloom;
""" % locals()
        fshstr += """
}
"""

        if 0:
            printsh((vshstr, fshstr), "clouds-shader")
        shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
        Clouds._shader_cache[shdkey] = shader
        return shader


    def _input_shader (self, dt, tmf):

        if self._cloudshape == 0:
            self._updwait_shdinp_refup -= dt * tmf
            if self._updwait_shdinp_refup <= 0.0:
                self._updwait_shdinp_refup += self._updperiod_shdinp_refup
                dir_z = Vec3(0.0, 0.0, 1.0)
                cam_quat = self.world.camera.getQuat(self.world.node)
                cam_fw = cam_quat.getForward()
                cam_up = cam_quat.getUp()
                ref_up = self._prev_ref_up - cam_fw * self._prev_ref_up.dot(cam_fw)
                if ref_up.length() > 0.1:
                    ref_up.normalize()
                elif abs(cam_up.dot(dir_z)) > 0.1:
                    ref_up = dir_z
                else:
                    ref_up = cam_up
                self._prev_ref_up = ref_up
                self.node.setShaderInput("ref_up", v3t4(ref_up))

        if self.world.frame < 5:
            self._updwait_light_fac = 0.0
        self._updwait_light_fac -= dt * tmf
        if self._updwait_light_fac <= 0.0:
            self._updwait_light_fac += self._updperiod_light_fac
            sunstr = self.world.sky.sun_strength
            amblfac = intl01v(sunstr, self._min_amblfac, 1.0)
            sunlfac = intl01v(sunstr, self._min_sunlfac, 1.0)
            moonlfac = intl01v(sunstr, self._min_moonlfac, 1.0)
            self.node.setShaderInput(self._shdinp.amblfacn, amblfac)
            self.node.setShaderInput(self._shdinp.sunlfacn, sunlfac)
            self.node.setShaderInput(self._shdinp.moonlfacn, moonlfac)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        # Switch to new sorting direction if needed.
        self._updwait_vsortdir -= self.world.dt
        if self._updwait_vsortdir <= 0.0:
            self._updwait_vsortdir = self._updperiod_vsortdir
            camdir = self.world.camera.getQuat(self.world.node).getForward()
            vsnbvdirs = self._vsnbvdirs[self._vsortdir_index]
            vsortdir = self._vsortdirs[self._vsortdir_index][1]
            vsmaxoffang0 = self._vsmaxoffangs[self._vsortdir_index]
            if vsnbvdirs:
                vsind = max(vsnbvdirs, key=lambda x: camdir.dot(x[1]))[0]
            else:
                vsind = self._vsortdir_index
            vsortdir = self._vsortdirs[vsind][1]
            vsoffang = acos(min(max(camdir.dot(vsortdir), -1.0), 1.0))
            if vsoffang > 2 * vsmaxoffang0:
                vsind = max(self._vsortdirs, key=lambda x: camdir.dot(x[1]))[0]
                vsortdir = self._vsortdirs[vsind][1]
            if self._vsortdir_index != vsind:
                self._vtilings[self._vsortdir_index].hide()
                self._vtilings[vsind].show()
                self._vsortdir_index = vsind

        # Update shader inputs.
        self._input_shader(self.world.dt, self.world.day_time_factor)

        return task.cont


# @cache-key-start: clouds-generation
# base: 0 tetrahedron, 1 octahedron, 2 icosahedron
def geodesic_sphere (base=2, numdivs=0, radius=1.0,
                     gvwvertex=None, gvwnormal=None, gvwcolor=None,
                     gtris=None):

    if gvwvertex is not None:
        gvwioff = gvwvertex.getWriteRow()
    else:
        gvwioff = 0
    numverts = [0]
    numtris = [0]
    norms = []
    tris = []
    edgesplits = {}

    if gvwcolor is not None:
        col = Vec4(1.0, 1.0, 1.0, 1.0)

    def add_vert (v, n):

        norms.append(n)
        if gvwvertex is not None:
            gvwvertex.addData3f(*v)
        if gvwnormal is not None:
            gvwnormal.addData3f(*n)
        if gvwcolor is not None:
            gvwcolor.addData4f(*col)

    def add_tri (i1, i2, i3):

        tris.append((i1, i2, i3))
        numtris[0] += 1
        if gtris is not None:
            gtris.addVertices(gvwioff + i1, gvwioff + i2, gwvioff + i3)
            gtris.closePrimitive()

    def split_triangle (i1, i2, i3, v1, v2, v3, numdivs):

        if numdivs == 0:
            add_tri(i1, i2, i3)
        else:
            n12 = (v1 + v2) * 0.5
            n12.normalize()
            n23 = (v2 + v3) * 0.5
            n23.normalize()
            n31 = (v3 + v1) * 0.5
            n31.normalize()

            v12 = n12 * radius
            v23 = n23 * radius
            v31 = n31 * radius

            eis = []
            for ia, ib, v, n in (
                (i1, i2, v12, n12),
                (i2, i3, v23, n23),
                (i3, i1, v31, n31)):
                if ia > ib:
                    ia, ib = ib, ia
                iab = edgesplits.get((ia, ib))
                if iab is None:
                    iab = numverts[0]
                    numverts[0] += 1
                    edgesplits[(ia, ib)] = iab
                    add_vert(v, n)
                eis.append(iab)
            i12, i23, i31 = eis

            split_triangle(i1, i12, i31, v1, v12, v31, numdivs - 1)
            split_triangle(i2, i23, i12, v2, v23, v12, numdivs - 1)
            split_triangle(i3, i31, i23, v3, v31, v23, numdivs - 1)
            split_triangle(i12, i23, i31, v12, v23, v31, numdivs - 1)

    # Create canonical polyhedron points.
    if base == 0: # tetrahedron
        phi = 1.0 / sqrt(2.0)
        ps = []
        for k1 in (-1, 1):
            p1 = Point3(k1 * 1.0, 0.0, -phi)
            p2 = Point3(0.0, k1 * 1.0, phi)
            ps.extend((p1, p2))
    elif base == 1: # octahedron
        ps = []
        for k1 in (-1, 1):
            p1 = Point3(k1 * 1.0, 0.0, 0.0)
            p2 = Point3(0.0, k1 * 1.0, 0.0)
            p3 = Point3(0.0, 0.0, k1 * 1.0)
            ps.extend((p1, p2, p3))
    elif base == 2: # icosahedron
        phi = 0.5 * (1.0 + sqrt(5.0))
        ps = []
        for k1, k2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p1 = Point3(0.0, k1 * 1.0, k2 * phi)
            p2 = Point3(k1 * 1.0, k2 * phi, 0.0)
            p3 = Point3(k2 * phi, 0.0, k1 * 1.0)
            ps.extend((p1, p2, p3))
    else:
        raise StandardError("Expected base in (0, 1, 2), got %d." % base)

    # Create base vertices and normals from canonical points.
    vs = []
    ns = []
    for p in ps:
        n = Vec3(p)
        n.normalize()
        ns.append(n)
        v = Point3(n * radius)
        vs.append(v)
        add_vert(v, n)

    # Brute force assembly of triangle-faced regular polyhedron.
    # Determine edge length as minimum distance between two vertices.
    # Go through each vertex, collecting all neighboring vertices as those
    # at edge lenght distance, and making all combinations of triangles
    # between the center vertex and neighboring verticess at edge lenght
    # from one another. Accept only triangles whose normal dot product
    # with center vertex normal is positive. First vertex index
    # of triangle must be the smallest. Add such triangles to a set,
    # so that non-unique triangles are ignored.
    nbvs = len(ns)
    iis = range(nbvs)
    l = radius * 2
    for i in xrange(nbvs - 1):
        for j in xrange(i + 1, nbvs):
            d = (vs[i] - vs[j]).length()
            l = min(l, d)
    btris = set()
    for ic, vc in enumerate(vs):
        ins = []
        for i, v in enumerate(vs):
            if i != ic and (v - vc).length() < l * 1.001:
                ins.append(i)
        nins = len(ins)
        nc = ns[ic]
        for k1 in xrange(nins - 1):
            i1 = ins[k1]
            v1 = vs[i1]
            for k2 in xrange(k1 + 1, nins):
                i2 = ins[k2]
                v2 = vs[i2]
                if (v1 - v2).length() < l * 1.001:
                    btri = [ic, i1, i2]
                    btri.sort()
                    v1s, v2s, v3s = vs[btri[0]], vs[btri[1]], vs[btri[2]]
                    nt = (v2s - v1s).cross(v3s - v1s)
                    nt.normalize()
                    if nt.dot(nc) < 0.0:
                        btri[1], btri[2] = btri[2], btri[1]
                    btri = tuple(btri)
                    btris.add(btri)

    # Subdivide basic triangles.
    numverts[0] = len(vs)
    for btri in sorted(btris):
        i1, i2, i3 = btri
        split_triangle(i1, i2, i3, vs[i1], vs[i2], vs[i3], numdivs)

    # For each vertex, compute maximum half-angle between its normal and
    # neighboring normals. To this end, for each vertex nearest
    # neighbors must be determined.
    nbinds = []
    maxoffangs = []
    for ic, nc in enumerate(norms):
        ins = set()
        nt1 = 0
        for tri in tris:
            if ic in tri:
                nt1 += 1
                ins.update(tri)
        ins.remove(ic)
        ins = sorted(ins)
        nbinds.append(ins)
        maxoffang = 0.0
        for i in ins:
            n = norms[i]
            offang = 0.5 * acos(min(max(nc.dot(n), -1.0), 1.0))
            maxoffang = max(maxoffang, offang)
        maxoffangs.append(maxoffang)

    return len(norms), len(tris), norms, maxoffangs, nbinds
# @cache-key-end: clouds-generation


