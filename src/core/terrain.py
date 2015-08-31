# -*- coding: UTF-8 -*-

from array import array
import cPickle as pickle
import codecs
from ConfigParser import SafeConfigParser
from gzip import GzipFile
from math import radians, ceil, sqrt, sin, cos
import os
from shutil import rmtree
from time import time

from pandac.PandaModules import Point2, Point2D, Point3, Point3D
from pandac.PandaModules import Vec2D, Vec3, Vec3D, Vec4
from pandac.PandaModules import LVector3i
from pandac.PandaModules import QuatD
from pandac.PandaModules import Texture, TextureStage
from pandac.PandaModules import GeomVertexArrayFormat, InternalName
from pandac.PandaModules import GeomVertexFormat
from pandac.PandaModules import GeomVertexWriter, GeomVertexData
from pandac.PandaModules import Geom, GeomNode, GeomTriangles
from pandac.PandaModules import NodePath, LODNode
from pandac.PandaModules import Shader, Triangulator

from src import join_path, path_exists, path_dirname
from src import internal_path, real_path, full_path
from src import USE_COMPILED, GLSL_PROLOGUE
from src.core.misc import AutoProps, unitv, clamp, set_texture
from src.core.misc import get_cache_key_section, key_to_hex
from src.core.misc import is_inside_poly, is_inside_convex_poly
from src.core.misc import make_image
from src.core.misc import report, dbgval
from src.core.misc import enc_lst_string, dec_lst_string
from src.core.misc import enc_lst_bool, dec_lst_bool
from src.core.planedyn import GROUND
from src.core.shader import make_shdfunc_amblit, make_shdfunc_dirlit
from src.core.shader import make_shdfunc_pntlit, printsh
from src.core.shader import make_shdfunc_fogbln, make_shdfunc_fogapl
from src.core.shader import make_shdfunc_sunbln
from src.core.shader import make_shdfunc_shdcrd, make_shdfunc_shdfac, SHADOWBLUR
from src.core.shader import make_frag_outputs
from src.core.table import UnitGrid2
from src.core.transl import *


class CutSpec (object):

    _counter = 0

    def __init__ (self, name=None,
                  cutmask=None, blendmask=None, blends=None):

        if name is None:
            name = "cut-%d" % CutSpec._counter

        self.name = name
        self.cutmask = cutmask
        self.blendmask = blendmask
        self.blends = blends or []

        CutSpec._counter += 1


class BlendSpec (object):

    _counter = 0

    def __init__ (self, name=None,
                  normalblendmode="cover", glossblendmode="cover",
                  nightglowfacn=None,
                  modcolorscale=None, modbrightness=None, modcontrast=None,
                  layers=None):

        if name is None:
            name = "blend-%d" % BlendSpec._counter

        self.name = name
        self.normalblendmode = normalblendmode
        self.glossblendmode = glossblendmode
        self.nightglowfacn = nightglowfacn
        self.modcolorscale = modcolorscale
        self.modbrightness = modbrightness
        self.modcontrast = modcontrast
        self.layers = layers or []

        BlendSpec._counter += 1


class LayerSpec (object):

    _counter = 0

    def __init__ (self, name=None,
                  altitude=None, radius=None, alpha=None,
                  uvscale=1.0, nmuvscale=None,
                  normalflow=None, glossflow=None,
                  blendmaskindex=None,
                  spans=None):

        if name is None:
            name = "layer-%d" % LayerSpec._counter

        self.name = name
        self.altitude = altitude
        self.radius = radius
        self.alpha = alpha
        self.uvscale = uvscale
        self.nmuvscale = nmuvscale
        self.normalflow = normalflow
        self.glossflow = glossflow
        self.blendmaskindex = blendmaskindex
        self.spans = spans or []

        LayerSpec._counter += 1


class SpanSpec (object):

    _counter = 0

    def __init__ (self, name=None,
                  extents=None, relative=False, tilemode=1,
                  texture=None, normalmap=None, glowmap=None, glossmap=None):

        if name is None:
            name = "span-%d" % SpanSpec._counter

        self.name = name
        self.extents = extents
        self.relative = relative
        self.tilemode = tilemode
        self.texture = texture
        self.normalmap = normalmap
        if isinstance(glowmap, Vec4):
            glowmap = tuple(glowmap)
        self.glowmap = glowmap
        self.glossmap = glossmap

        SpanSpec._counter += 1


class VirtualSurface (object):

    def __init__ (self, extents, flush):

        self._extents = extents
        self._flush = flush


    def extents (self):

        return map(Point3, self._extents)


    def flush (self):

        return self._flush


    def height (self, x, y, wnorm=False):

        z = 0.0
        t = GROUND.RUNWAY
        if wnorm:
            n = Vec3(0.0, 0.0, 1.0)
            return z, n, t
        else:
            return z, t


class VirtualHorizPoly (VirtualSurface):

    def __init__ (self, poly, elev, gtype, flush=False, convex=False):

        p0 = poly[0]
        e0 = Point3(p0[0], p0[1], elev)
        e1 = Point3(p0[0], p0[1], elev)
        for p in poly:
            e0[0] = min(e0[0], p[0])
            e0[1] = min(e0[1], p[1])
            e1[0] = max(e1[0], p[0])
            e1[1] = max(e1[1], p[1])
        extents = (e0, e1)

        VirtualSurface.__init__(self, extents, flush)

        self._poly = poly
        self._convex = convex
        self._elev = elev
        self._gtype = gtype
        self._norm = Vec3(0.0, 0.0, 1.0)


    def height (self, x, y, wnorm=False):

        if self._convex:
            inside = is_inside_convex_poly(self._poly, Point2(x, y))
        else:
            inside = is_inside_poly(self._poly, Point2(x, y))
        if inside:
            if wnorm:
                return self._elev, self._norm, self._gtype
            else:
                return self._elev, self._gtype
        else:
            return None


class Terrain (object):

    def __init__ (self, world, sizex, sizey, visradius,
                  name=None, heightmap=None,
                  maxsizex=None, maxsizey=None,
                  centerx=None, centery=None,
                  mingray=None, maxgray=None,
                  minheight=None, maxheight=None,
                  celldensity=1.0, periodic=False,
                  tiledivx=None, tiledivy=None,
                  cuts=[], pntlit=0, sunblend=(),
                  wshadows=None,
                  pos=None):

        if maxheight is None:
            maxheight = minheight

        if isinstance(maxsizex, tuple):
            maxsizexa, maxsizexb = maxsizex
        else:
            maxsizexa = maxsizexb = maxsizex

        sizex = float(sizex)
        sizey = float(sizey)
        visradius = float(visradius)
        celldensity = float(celldensity)
        tiledivx = int(tiledivx or 1) or 1
        tiledivy = int(tiledivy or 1) or 1
        def fix_num_tiles(size, wtilesize, tilediv):
            numtiles = int(size / wtilesize - 0.5) + 1
            return (numtiles // tilediv) * tilediv
        numtilesx = fix_num_tiles(sizex, 20000.0, tiledivx)
        numtilesy = fix_num_tiles(sizey, 20000.0, tiledivy)

        self.world = world

        self._visradius = visradius
        self._sizex = sizex
        self._sizey = sizey

        # Position of bottom left corner of the terrain, wrt. (0, 0).
        offsetx = -0.5 * self._sizex
        offsety = -0.5 * self._sizey
        self._offsetx = offsetx
        self._offsety = offsety

        # Extract cut masks.
        cutmaskpaths = []
        levints = [False]
        for ic, cutspec in enumerate(cuts):
            if ic == 0 and cutspec.cutmask is not None:
                raise StandardError(
                    "A cut mask is specified for cut %d (%s) "
                    "but it should not be." % (ic, cutspec.name))
            elif ic > 0 and cutspec.cutmask is None:
                raise StandardError(
                    "No cut mask is specified for cut %d (%s) "
                    "but it should be." % (ic, cutspec.name))
            if cutspec.cutmask is not None:
                if not isinstance(cutspec.cutmask, tuple):
                    cutmask, levint = cutspec.cutmask, True
                else:
                    cutmask, levint = cutspec.cutmask
                cutmaskpath = full_path("data", cutmask)
                cutmaskpaths.append(cutmaskpath)
                levints.append(levint)

        haveheightmappath = False
        heightmappath = ""
        havehmdatapath = False
        hmdatapath = ""
        if heightmap:
            heightmappath = full_path("data", heightmap)
            haveheightmappath = True
            hmdata = heightmap[:heightmap.rfind(".")] + ".dat"
            if path_exists("data", hmdata):
                hmdatapath = real_path("data", hmdata)
                havehmdatapath = True

        maxsizexa, maxsizexb, havemaxsizex = (0.0, 0.0, False) if maxsizex is None else (maxsizexa, maxsizexb, True)
        maxsizey, havemaxsizey = (0.0, False) if maxsizey is None else (maxsizey, True)
        centerx, havecenterx = (0.0, False) if centerx is None else (centerx, True)
        centery, havecentery = (0.0, False) if centery is None else (centery, True)
        mingray, havemingray = (0, False) if mingray is None else (mingray, True)
        maxgray, havemaxgray = (0, False) if maxgray is None else (maxgray, True)
        minheight, haveminheight = (0.0, False) if minheight is None else (minheight, True)
        maxheight, havemaxheight = (0.0, False) if maxheight is None else (maxheight, True)

        if USE_COMPILED:
            report(_("Constructing terrain."))
            # For Python version reported from within TerrainGeom,
            # because it may either construct or read from cache.
        self._geom = TerrainGeom(
            name,
            sizex, sizey, offsetx, offsety,
            heightmappath, haveheightmappath, hmdatapath, havehmdatapath,
            maxsizexa, maxsizexb, havemaxsizex, maxsizey, havemaxsizey,
            centerx, havecenterx, centery, havecentery,
            mingray, havemingray, maxgray, havemaxgray,
            minheight, haveminheight, maxheight, havemaxheight,
            numtilesx, numtilesy,
            celldensity, periodic,
            enc_lst_string(cutmaskpaths), enc_lst_bool(levints))

        numquadsx = self._geom.num_quads_x()
        numquadsy = self._geom.num_quads_y()
        numtilesx = self._geom.num_tiles_x()
        numtilesy = self._geom.num_tiles_y()
        tilesizex = self._geom.tile_size_x()
        tilesizey = self._geom.tile_size_y()
        numcuts = self._geom.num_cuts()
        tileroot = self._geom.tile_root()
        self.numtilesx = numtilesx
        self.numtilesy = numtilesy
        self._numquadsx = numquadsx
        self._numquadsy = numquadsy

        self.node = world.node.attachNewNode("terrain")
        if pos is None:
            pos = Point3()
        pos = Point3(pos)
        self.node.setPos(pos)
        self._pos = pos
        self._pos_x, self._pos_y = pos[0], pos[1]
        tileroot.reparentTo(self.node)

        # Get tile pointers and set LOD distances.
        self._tiles = [[[None] * numcuts for jt in xrange(numtilesy)]
                       for it in xrange(numtilesx)]
        tileradius = 0.5 * sqrt(tilesizex**2 + tilesizey**2)
        maxaltitude = 30000.0
        outvisradius = sqrt((visradius + tileradius)**2 + maxaltitude**2)
        it = 0; jt = 0
        for ijtlnp in tileroot.getChildren():
            ijtlod = ijtlnp.node()
            ijtlod.setSwitch(0, outvisradius, 0.0)
            ijtile = ijtlnp.getChild(0)
            ic = 0
            for ctile in ijtile.getChildren():
                self._tiles[it][jt][ic] = ctile
                ic += 1
            jt += 1
            if jt >= numtilesy:
                it += 1; jt = 0

        # Derive data for external use of heightmap as terrain chart.
        self.geomap_path = None
        if heightmap:
            self.geomap_path = heightmap
            maxsizexa, maxsizexb, maxsizey = self._geom.heightmap_size()
            self.geomap_uvext = []
            self.geomap_uvext_arena = []
            for kx, ky in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                x = self._offsetx + 0.5 * (1 + kx) * self._sizex
                y = self._offsety + 0.5 * (1 + ky) * self._sizey
                uv = self._geom.to_unit_trap(maxsizexa, maxsizexb, maxsizey, x, y)
                xa = x - kx * visradius
                ya = y - ky * visradius
                self.geomap_uvext.append(uv)
                uva = self._geom.to_unit_trap(maxsizexa, maxsizexb, maxsizey, xa, ya)
                self.geomap_uvext_arena.append(uva)

        # Resolve None/empty-valued data to needed equivalents.
        for ic, cutspec in enumerate(cuts):
            numblends = 0
            for ib, blendspec in enumerate(cutspec.blends):
                if blendspec is None:
                    continue
                numblends += 1
                for il, layerspec in enumerate(blendspec.layers):
                    if len(layerspec.spans) == 0:
                        layerspec.spans.append(SpanSpec())
            if cutspec.blendmask is None and numblends > 1:
                cutspec.blendmask = "images/terrain/_black.png"

        # Construct texture stages.
        maxblends = max(len(cs.blends) for cs in cuts)
        maxlayers = max(len(bs.layers) for cs in cuts for bs in cs.blends if bs)
        tsort = 0
        with_shadows = wshadows
        if with_shadows is None or not base.with_world_shadows:
            with_shadows = base.with_world_shadows
        if with_shadows:
            ts = TextureStage("shadow")
            ts.setSort(tsort)
            tsort += 1
            texstage_shadow = ts
        ts = TextureStage("blend")
        ts.setSort(tsort)
        tsort += 1
        texstage_blend = ts
        texstage_color = []
        texstage_normal = []
        texstage_glow = []
        texstage_gloss = []
        for ib in range(maxblends):
            texstage_color_1 = []
            for il in xrange(maxlayers):
                ts = TextureStage("color-b%d-l%d" % (ib, il))
                ts.setSort(tsort)
                tsort += 1
                texstage_color_1.append(ts)
            texstage_color.append(texstage_color_1)
            texstage_normal_1 = []
            for il in xrange(maxlayers):
                ts = TextureStage("normal-b%d-l%d" % (ib, il))
                ts.setSort(tsort)
                tsort += 1
                texstage_normal_1.append(ts)
            texstage_normal.append(texstage_normal_1)
            texstage_glow_1 = []
            for il in xrange(maxlayers):
                ts = TextureStage("glow-b%d-l%d" % (ib, il))
                ts.setSort(tsort)
                tsort += 1
                texstage_glow_1.append(ts)
            texstage_glow.append(texstage_glow_1)
            texstage_gloss_1 = []
            for il in xrange(maxlayers):
                ts = TextureStage("gloss-b%d-l%d" % (ib, il))
                ts.setSort(tsort)
                tsort += 1
                texstage_gloss_1.append(ts)
            texstage_gloss.append(texstage_gloss_1)
        self._texstage_map = {
            "color": texstage_color,
            "normal": texstage_normal,
            "glow": texstage_glow,
            "gloss": texstage_gloss,
        }

        # Assign textures.
        tile_grid = lambda: [[[] for j in xrange(numtilesy)] for i in xrange(numtilesx)]
        extras = []
        texstack = []
        for ic, cutspec in enumerate(cuts):
            texstack.append(tile_grid())
            for it in xrange(numtilesx):
                for jt in xrange(numtilesy):
                    if with_shadows:
                        # Do not set wrap, do not set filter.
                        texstack[ic][it][jt].append(
                            (texstage_shadow, base.world_shadow_texture, False, None))
                    if cutspec.blendmask is not None:
                        texstack[ic][it][jt].append(
                            (texstage_blend, cutspec.blendmask))
            for ib, blendspec in enumerate(cutspec.blends):
                if blendspec is None:
                    continue
                texstack_color = tile_grid()
                texstack_normal = tile_grid()
                texstack_glow = tile_grid()
                texstack_gloss = tile_grid()
                for il, layerspec in enumerate(blendspec.layers):
                    any_color_layer = any(s.texture for s in layerspec.spans)
                    any_normal_layer = any(s.normalmap for s in layerspec.spans)
                    any_glow_layer = any(s.glowmap for s in layerspec.spans)
                    any_gloss_layer = any(s.glossmap for s in layerspec.spans)
                    glowmap_none = "images/terrain/_clear_black.png"
                    for ip, spanspec in enumerate(layerspec.spans):
                        if isinstance(spanspec.glowmap, tuple):
                            glowmap_none = (0, 0, 0, 0)
                            break
                    for ip, spanspec in enumerate(layerspec.spans):
                        tilespec = Terrain._select_tiles(
                            self._sizex, self._sizey,
                            self._offsetx, self._offsety,
                            numtilesx, numtilesy,
                            spanspec.extents, spanspec.relative,
                            spanspec.tilemode)
                        for it, jt in tilespec:
                            if any_color_layer:
                                texture = spanspec.texture or "images/terrain/_black.png"
                                texstack_color[it][jt].append(
                                    (texstage_color[ib][il], texture))
                            if any_normal_layer:
                                normalmap = spanspec.normalmap or "images/terrain/_blue.png"
                                texstack_normal[it][jt].append(
                                    (texstage_normal[ib][il], normalmap))
                            if any_glow_layer:
                                glowmap = spanspec.glowmap or glowmap_none
                                if not isinstance(glowmap, tuple):
                                    texstack_glow[it][jt].append(
                                        (texstage_glow[ib][il], glowmap))
                            if any_gloss_layer:
                                glossmap = spanspec.glossmap or "images/terrain/_black.png"
                                texstack_gloss[it][jt].append(
                                    (texstage_gloss[ib][il], glossmap))
                for it in xrange(numtilesx):
                    for jt in xrange(numtilesy):
                        texstack[ic][it][jt].extend(texstack_color[it][jt])
                        texstack[ic][it][jt].extend(texstack_normal[it][jt])
                        texstack[ic][it][jt].extend(texstack_glow[it][jt])
                        texstack[ic][it][jt].extend(texstack_gloss[it][jt])
        for ic in xrange(len(cuts)):
            for it in xrange(numtilesx):
                for jt in xrange(numtilesy):
                    tile = self._tiles[it][jt][ic]
                    if tile is not None:
                        set_texture(tile, extras=texstack[ic][it][jt], clamp=False)
        self._texstack = texstack

        # Convert texture stack tuples to dictionaries,
        # for fast lookups in replace_texture.
        tm = [[[dict((id(sp[0]), k) for k, sp in enumerate(ts3))
                for ts3 in ts2] for ts2 in ts1] for ts1 in texstack]
        self._texstack_stmap = tm

        # Setup shader.
        nightglowfacn_all = set()
        for ic, cutspec in enumerate(cuts):
            for ib, blendspec in enumerate(cutspec.blends):
                if blendspec is None:
                    continue
                if blendspec.nightglowfacn:
                    self.node.setShaderInput(blendspec.nightglowfacn, 0.0)
                    nightglowfacn_all.add(blendspec.nightglowfacn)
        self.nightglowfacn = sorted(nightglowfacn_all)
        def set_shader ():
            for ic, cutspec in enumerate(cuts):
                shader = Terrain._make_shader(
                    shdinp=self.world.shdinp,
                    pntlit=pntlit,
                    sunblend=sunblend,
                    cutspec=cutspec,
                    shdshow=with_shadows,
                    #showas=("terrain-cut-%d" % ic),
                )
                for it in xrange(numtilesx):
                    for jt in xrange(numtilesy):
                        self._tiles[it][jt][ic].setShader(shader)

        # NOTE: Make sure all textures are loaded right here,
        # by displaying the whole terrain on screen in one frame.
        # This is done weirdly as it is, because:
        # - configuration option preload-textures does not seem to work;
        # - doing frame-on-screen independently (putting arbitrary quad
        # with texture) corrupts texture application to terrain.
        load_tex = base.uiface_root.attachNewNode("terran-cache-tex")
        self.node.reparentTo(load_tex)
        self.node.setPos(0.0, 0.0, 0.0)
        self.node.setP(90.0)
        lsize = max(numtilesx * tilesizex, numtilesy * tilesizey)
        self.node.setScale(1.0 / lsize)
        hw = base.aspect_ratio
        make_image("images/ui/black.png", size=(hw * 2, 2.0), parent=load_tex)
        def remove_load_tex (task):
            if task.getElapsedFrames() >= 1:
                self.node.reparentTo(self.world.node)
                self.node.setPos(self._pos)
                self.node.setScale(1.0)
                self.node.setP(0.0)
                set_shader()
                load_tex.removeNode()
                return task.done
            return task.cont
        task = taskMgr.add(remove_load_tex, "terrain-cache-tex")

        self.pntlit = pntlit

        # Setup ground types by cut.
        self._ground_type_by_cut = [-1] * numcuts
        if numcuts > 0:
            self._ground_type_by_cut[0] = GROUND.DIRT
        if numcuts > 1:
            self._ground_type_by_cut[1] = GROUND.WATER

        # Setup virtual surfaces.
        self._virtsurf_store = []
        self._virtsurf_per_quad = {}

        self._input_shader(0.0) # initialize
        self.alive = True
        base.taskMgr.add(self._loop, "terrain-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self._geom.destroy()
        self.node.removeNode()
        self._prod_gc()


    def _prod_gc (self):

        for tiles1 in self._tiles:
            for tiles2 in tiles1:
                for tile in tiles2:
                    tile.removeNode()
        self._tiles = []
        del self._geom


    _shader_cache = {}

    @staticmethod
    def _make_shader (shdinp, pntlit, sunblend, cutspec, shdshow,
                      showas=False):

        pntlns = shdinp.pntlns[:pntlit]

        blendkey = []
        for ib, blendspec in enumerate(cutspec.blends):
            if blendspec is None:
                blendkey.append(None)
                continue
            for layerspec in blendspec.layers:
                blendkey.append(layerspec.altitude)
                blendkey.append(layerspec.radius)
                blendkey.append(layerspec.alpha)
                blendkey.append(layerspec.uvscale)
                blendkey.append(layerspec.nmuvscale)
                for spanspec in layerspec.spans:
                    blendkey.append(spanspec.texture is not None)
                    blendkey.append(spanspec.normalmap is not None)
                    blendkey.append(spanspec.glowmap is not None)
                    blendkey.append(spanspec.glossmap is not None)
                    if isinstance(spanspec.glowmap, tuple):
                        blendkey.append(spanspec.glowmap)

        shdkey = (shdinp.camn, shdinp.ambln, (shdinp.sunln, shdinp.moonln),
                  tuple(sorted(pntlns)), shdinp.fogn, tuple(sunblend),
                  shdinp.sunposn, shdinp.sunbcoln, shdshow,
                  tuple(blendkey),
                  shdinp.shadowrefn, shdinp.shadowdirlin, shdinp.shadowblendn)
        ret = Terrain._shader_cache.get(shdkey)
        if ret is not None:
            return ret

        blend_ind_to_chn = (None, "r", "g", "b", "a")

        any_altitude = False
        any_radius = False
        any_alpha = False
        any_normal = False
        any_glow = False
        any_gloss = False
        any_non_gloss = False
        #layers_with_anything = set()
        max_num_layers = 0
        any_flow = False
        any_modcol = False
        for blendspec in cutspec.blends:
            if blendspec is None:
                continue
            any_color_layer = False
            any_normal_layer = False
            any_glow_layer = False
            any_gloss_layer = False
            for il, layerspec in enumerate(blendspec.layers):
                any_altitude = any_altitude or bool(layerspec.altitude)
                any_radius = any_radius or bool(layerspec.radius)
                any_alpha = any_alpha or bool(layerspec.alpha)
                any_color_span = any(s.texture for s in layerspec.spans)
                any_normal_span = any(s.normalmap for s in layerspec.spans)
                any_glow_span = any(s.glowmap for s in layerspec.spans)
                any_gloss_span = any(s.glossmap for s in layerspec.spans)
                any_color_layer = any_color_layer or any_color_span
                any_normal_layer = any_normal_layer or any_normal_span
                any_glow_layer = any_glow_layer or any_glow_span
                any_gloss_layer = any_gloss_layer or any_gloss_span
                any_flow = any_flow or ((any_normal_span and layerspec.normalflow) or
                                        (any_gloss_span and layerspec.glossflow))
                #if any_color_span or any_normal_span or any_glow_span or any_gloss_span:
                    #layers_with_anything.add(il)
            max_num_layers = max(max_num_layers, len(blendspec.layers))
            any_normal = any_normal or any_normal_layer
            any_glow = any_glow or any_glow_layer
            any_gloss = any_gloss or any_gloss_layer
            any_non_gloss = any_non_gloss or (not any_gloss_layer and blendspec.layers)
            any_modcol = any_modcol or (blendspec.modcolorscale or
                                        blendspec.modbrightness or
                                        blendspec.modcontrast)
        #layers_with_anything = sorted(layers_with_anything)

        vshstr = GLSL_PROLOGUE

        vshstr += make_shdfunc_amblit()
        if sunblend:
            vshstr += make_shdfunc_sunbln(sunblend=sunblend)
        vshstr += make_shdfunc_fogbln(sunblend=sunblend)
        if shdshow:
            vshstr += make_shdfunc_shdcrd(push=0.002)

        vshstr += """
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_ModelViewProjectionMatrix;
"""
        if any_altitude or any_radius:
            vshstr += """
out vec4 l_worldpos;
"""
        vshstr += """
in vec4 p3d_Vertex;

in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord;

uniform vec4 wspos_%(camn)s;
in vec3 p3d_Normal;
""" % shdinp
        if any_normal:
            vshstr += """
in vec3 p3d_Tangent;
"""
        vshstr += """
uniform AmbLight %(ambln)s;
out vec4 l_lit;

out vec4 l_vertpos;
out vec3 l_vertnrm;
""" % shdinp
        if any_normal:
            vshstr += """
out vec3 l_verttng;
"""
        vshstr += """
uniform FogSpec %(fogn)s;
""" % shdinp
        if sunblend:
            vshstr += """
uniform vec4 wspos_%(sunposn)s;
uniform SunBlendSpec %(sunbcoln)s;
""" % shdinp
        if shdshow:
            vshstr += """
uniform mat4 trans_model_to_clip_of_%(shadowrefn)s;
uniform float %(shadowblendn)s;
out vec4 l_shdcoord;
""" % shdinp
        vshstr += """
out vec4 l_fog;

void main ()
{
"""
        vshstr += """
    vec4 worldpos = p3d_ModelMatrix * p3d_Vertex;
"""
        if any_altitude or any_radius:
            vshstr += """
    l_worldpos = worldpos;
"""
        vshstr += """
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    l_texcoord = p3d_MultiTexCoord0;

    l_lit = vec4(0.0, 0.0, 0.0, 0.0);
    amblit(%(ambln)s, 1.0, l_lit);

    l_vertpos = p3d_ModelViewMatrix * p3d_Vertex;
    l_vertnrm = p3d_NormalMatrix * p3d_Normal;
""" % shdinp
        if any_normal:
            vshstr += """
    l_verttng = p3d_NormalMatrix * p3d_Tangent;
"""
        if shdshow:
            vshstr += """
    l_shdcoord = shdcrd(trans_model_to_clip_of_%(shadowrefn)s, p3d_Vertex,
                        %(shadowblendn)s);
""" % shdinp
        vshstr += """
    l_fog = vec4(0.0);
"""
        if sunblend:
            vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, worldpos,
           wspos_%(sunposn)s, %(sunbcoln)s.ambient,
           l_fog);
""" % shdinp
        else:
            vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, worldpos, l_fog);
""" % shdinp
        vshstr += """
}
""" % shdinp

        fshstr = GLSL_PROLOGUE

        ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
        odeclstr, ocolorn, osunvisn = ret[:3]
        if base.with_bloom:
            obloomn = ret[3]

        if any_non_gloss:
            fshstr += make_shdfunc_dirlit()
        if any_gloss:
            fshstr += make_shdfunc_dirlit(gloss=True, extname="_gs")
        if pntlns:
            if any_non_gloss:
                fshstr += make_shdfunc_pntlit()
            if any_gloss:
                fshstr += make_shdfunc_pntlit(gloss=True, extname="_gs")
        fshstr += make_shdfunc_fogapl()
        if shdshow:
            fshstr += make_shdfunc_shdfac(blur=SHADOWBLUR.NONE)

        if any_flow:
            fshstr += """
struct GameTime {
    vec4 ambient;
};
uniform GameTime %(gtimen)s;
""" % shdinp
        tsn = 0
        if shdshow:
            fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // shadow
""" % locals()
            tsn += 1
        if cutspec.blendmask:
            fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // mask
""" % locals()
            tsn += 1
        for ib, blendspec in enumerate(cutspec.blends):
            if blendspec is None:
                continue
            for il, layerspec in enumerate(blendspec.layers):
                if any(s.texture for s in layerspec.spans):
                    fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // color-b%(ib)s-l%(il)s
""" % locals()
                    tsn += 1
            for il, layerspec in enumerate(blendspec.layers):
                if any(s.normalmap for s in layerspec.spans):
                    fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // normal-b%(ib)s-l%(il)s
""" % locals()
                    tsn += 1
            for il, layerspec in enumerate(blendspec.layers):
                if any(s.glowmap for s in layerspec.spans):
                    if any(not isinstance(s.glowmap, tuple) for s in layerspec.spans):
                        fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // glow-b%(ib)s-l%(il)s
""" % locals()
                        tsn += 1
            for il, layerspec in enumerate(blendspec.layers):
                if any(s.glossmap for s in layerspec.spans):
                    fshstr += """
uniform sampler2D p3d_Texture%(tsn)d; // gloss-b%(ib)s-l%(il)s
""" % locals()
                    tsn += 1
        for ib, blendspec in enumerate(cutspec.blends):
            if blendspec is None:
                continue
            if blendspec.nightglowfacn:
                glowfacn = blendspec.nightglowfacn
                fshstr += """
uniform float %(glowfacn)s;
""" % locals()
        if any_altitude or any_radius:
            fshstr += """
in vec4 l_worldpos;
uniform vec4 wspos_%(camn)s;
""" % shdinp
        fshstr += """
in vec2 l_texcoord;

in vec4 l_lit;

in vec4 l_vertpos;
in vec3 l_vertnrm;
"""
        if any_normal:
            fshstr += """
in vec3 l_verttng;
"""
        fshstr += """
uniform DirLight %(sunln)s;
uniform DirLight %(moonln)s;
""" % shdinp
        for pntln in pntlns:
            fshstr += """
uniform PntLight %(pntln)s;
""" % locals()
        if any_gloss:
            fshstr += """
uniform vec4 vspos_%(camn)s;
""" % shdinp
        if shdshow:
            fshstr += """
in vec4 l_shdcoord;
uniform int %(shadowdirlin)s;
""" % shdinp
        fshstr += """
in vec4 l_fog;
"""
        fshstr += odeclstr
        fshstr += """
void main ()
{
"""
        tsn = 0
        fshstr += """
    vec3 vertnrm = l_vertnrm;
    vertnrm = normalize(vertnrm); // due to interpolation
"""
        if any_normal:
            fshstr += """
    vec3 verttng = l_verttng;
    verttng = normalize(verttng); // also
    vec3 vertbnr = cross(verttng, vertnrm);
"""
        if any_altitude or any_radius:
            fshstr += """
    vec3 vp = wspos_%(camn)s.xyz;
    vec3 p = l_worldpos.xyz;
""" % shdinp
        if any_altitude:
            fshstr += """
    float h = max(vp.z - p.z, 0.0);
    float hfac;
"""
        if any_radius:
            fshstr += """
    float r = distance(vp.xy, p.xy);
    float rfac;
"""
        if any_alpha:
            fshstr += """
    float afac;
"""
        if shdshow:
            # NOTE: Using if (...) because raw texture sampling
            # with wrap mode set to border-color does not work properly.
            fshstr += """
    float kshdb = shdfac(p3d_Texture%(tsn)d, l_shdcoord);
""" % locals()
            tsn += 1
            fshstr += """
    float kshds = %(shadowdirlin)s == 0 ? kshdb : 1.0;
    float kshdm = %(shadowdirlin)s == 1 ? kshdb : 1.0;
""" % shdinp
        else:
            fshstr += """
    float kshds = 1.0;
    float kshdm = 1.0;
"""
        fshstr += """
    vec4 tc0, tc1, tc0p;
    vec4 lit;
    vec3 nrm;
    vec2 uv;
"""
        #for il in sorted(layers_with_anything):
        for il in range(max_num_layers):
            fshstr += """
    float ifac_%(il)s, afac_%(il)s;
""" % locals()
        if any_normal:
            fshstr += """
    vec3 dnz, dn0, dn1;
    dnz = vec3(0.0, 0.0, 1.0);
"""
        if any_glow:
            fshstr += """
    vec4 tgw0, tgw1, tgw0p;
    tgw0 = vec4(0.0, 0.0, 0.0, 0.0);
"""
        if any_gloss:
            fshstr += """
    vec3 cdir = normalize(vspos_%(camn)s.xyz - l_vertpos.xyz);
    vec4 tgs0, tgs1, lgs;
""" % shdinp
        if cutspec.blendmask:
            fshstr += """
    vec4 mc;
    mc = texture(p3d_Texture%(tsn)d, l_texcoord);
""" % locals()
            tsn += 1
        fshstr += """
    tc0 = vec4(0.0, 0.0, 0.0, 0.0);
"""
        for ib, blendspec in enumerate(cutspec.blends):
            if blendspec is None or not blendspec.layers:
                continue
            bchn = blend_ind_to_chn[ib]
            if ib > 0:
                fshstr += """
    if (mc.%(bchn)s > 0.0) {
        tc0p = tc0;
""" % locals()
                if any_glow:
                    fshstr += """
        tgw0p = tgw0;
"""
            else:
                fshstr += """
    {
"""
            fshstr += """
        // Compute interpolation factors per layer.
""" % locals()
            for il, layerspec in enumerate(blendspec.layers):
                fshstr += """
        ifac_%(il)d = 1.0;
""" % locals()
                if layerspec.altitude:
                    lh0, lh1 = layerspec.altitude
                    if lh0 < lh1:
                        raise StandardError(
                            "Upper altitude smaller than lower altitude "
                            "(%.0f < %.0f)." % (lh0, lh1))
                    fshstr += """
        hfac = clamp((h - %(lh0)f) / (%(lh1)f - %(lh0)f), 0.0, 1.0);
        ifac_%(il)d *= hfac;
""" % locals()
                if layerspec.radius:
                    lr0, lr1 = layerspec.radius
                    if lr0 < lr1:
                        raise StandardError(
                            "Outer radius smaller than inner radius "
                            "(%.0f < %.0f)." % (lr0, lr1))
                    fshstr += """
        rfac = clamp((r - %(lr0)f) / (%(lr1)f - %(lr0)f), 0.0, 1.0);
        ifac_%(il)d *= rfac;
""" % locals()
                if layerspec.blendmaskindex is not None:
                    bchnl = blend_ind_to_chn[layerspec.blendmaskindex]
                    fshstr += """
        ifac_%(il)d *= mc.%(bchnl)s;
""" % locals()
                if layerspec.alpha:
                    la0, la1 = layerspec.alpha
                    if la0 != la1:
                        fshstr += """
        afac = 1.0;
"""
                        if layerspec.altitude:
                            fshstr += """
        afac *= hfac;
"""
                        if layerspec.radius:
                            fshstr += """
        afac *= rfac;
"""
                        fshstr += """
        afac_%(il)d = mix(%(la0)f, %(la1)f, afac);
""" % locals()
                    else:
                        fshstr += """
        afac_%(il)d = %(la0)f;
""" % locals()
                else:
                    fshstr += """
        afac_%(il)d = 1.0;
""" % locals()
            fshstr += """
        // Interpolate color.
        tc0 = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
            any_color_layer = any(s.texture for l in blendspec.layers for s in l.spans)
            if any_color_layer:
                for il, layerspec in enumerate(blendspec.layers):
                    if any(s.texture for s in layerspec.spans):
                        uvsc = layerspec.uvscale
                        fshstr += """
        uv = l_texcoord;
        tc1 = texture(p3d_Texture%(tsn)d, uv * %(uvsc)f);
        tc0 = mix(tc0, tc1, ifac_%(il)d * afac_%(il)d * tc1.a);
""" % locals()
                        tsn += 1
            fshstr += """
        // Interpolate normal.
        nrm = vec3(vertnrm);
"""
            any_normal_layer = any(s.normalmap for l in blendspec.layers for s in l.spans)
            if any_normal_layer:
                if blendspec.normalblendmode == "add":
                    fshstr += """
        dn0 = vec3(0.0);
"""
                else:
                    fshstr += """
        dn0 = vec3(dnz);
"""
                for il, layerspec in enumerate(blendspec.layers):
                    if any(s.normalmap for s in layerspec.spans):
                        if layerspec.normalflow:
                            uvhdg, uvspd = layerspec.normalflow
                            uvel = cos(radians(uvhdg)) * uvspd
                            vvel = sin(radians(uvhdg)) * uvspd
                            gtmn = "%(gtimen)s.ambient" % shdinp
                            fshstr += """
        uv = l_texcoord + vec2(%(uvel)f * %(gtmn)s.x, %(vvel)f * %(gtmn)s.x);
        uv -= floor(uv);
""" % locals()
                        else:
                            fshstr += """
        uv = l_texcoord;
"""
                        nmuvsc = layerspec.nmuvscale or layerspec.uvscale
                        fshstr += """
        dn1 = texture(p3d_Texture%(tsn)d, uv * %(nmuvsc)f).rgb * 2.0 - 1.0;
        dn1 = mix(dnz, dn1, ifac_%(il)d);
""" % locals()
                        if blendspec.normalblendmode == "cover":
                            fshstr += """
        dn0 = mix(dn0, dn1, ifac_%(il)d);
""" % locals()
                        elif blendspec.normalblendmode == "add":
                            fshstr += """
        dn0 += dn1;
"""
                        elif blendspec.normalblendmode == "multiply":
                            fshstr += """
        dn0 *= dn1;
"""
                        else:
                            raise StandardError(
                                "Unknown normal blend mode for "
                                "blend %(ib)s layer %(il)s." % locals())
                        tsn += 1
                fshstr += """
        nrm = normalize(nrm * dn0.z + verttng * dn0.x + vertbnr * dn0.y);
"""
            any_glow_layer = any(s.glowmap for l in blendspec.layers for s in l.spans)
            if any_glow_layer:
                fshstr += """
        // Interpolate glow.
        tgw0 = vec4(0.0);
"""
                for il, layerspec in enumerate(blendspec.layers):
                    if any(s.glowmap for s in layerspec.spans):
                        if any(not isinstance(s.glowmap, tuple) for s in layerspec.spans):
                            gwuvsc = layerspec.uvscale
                            fshstr += """
        uv = l_texcoord;
        tgw1 = texture(p3d_Texture%(tsn)d, uv * %(gwuvsc)f);
""" % locals()
                            tsn += 1
                        else:
                            for spanspec in layerspec.spans:
                                if spanspec.glowmap:
                                    gr, gg, gb, ga = spanspec.glowmap
                                    break
                            fshstr += """
        tgw1 = vec4(%(gr)f, %(gg)f, %(gb)f, %(ga)f);
""" % locals()
                        if blendspec.nightglowfacn:
                            glowfacn = blendspec.nightglowfacn
                            fshstr += """
        tgw1 *= %(glowfacn)s;
""" % locals()
                        fshstr += """
        tgw0 = mix(tgw0, tgw1, ifac_%(il)d);
""" % locals()

            any_gloss_layer = any(s.glossmap for l in blendspec.layers for s in l.spans)
            if any_gloss_layer:
                fshstr += """
        // Interpolate gloss.
"""
                if blendspec.glossblendmode == "add":
                    fshstr += """
        tgs0 = vec4(0.0);
"""
                else:
                    fshstr += """
        tgs0 = vec4(1.0);
"""
                fshstr += """
        uv = vec2(l_texcoord);
"""
                for il, layerspec in enumerate(blendspec.layers):
                    if any(s.glossmap for s in layerspec.spans):
                        if layerspec.glossflow:
                            uvhdg, uvspd = layerspec.glossflow
                            uvel = cos(radians(uvhdg)) * uvspd
                            vvel = sin(radians(uvhdg)) * uvspd
                            gtmn = "%(gtimen)s.ambient" % shdinp
                            fshstr += """
        uv = l_texcoord + vec2(%(uvel)f * %(gtmn)s.x, %(vvel)f * %(gtmn)s.x);
        uv -= floor(uv);
""" % locals()
                        else:
                            fshstr += """
        uv = l_texcoord;
"""
                        gsuvsc = layerspec.uvscale
                        fshstr += """
        tgs1 = texture(p3d_Texture%(tsn)d, uv * %(gsuvsc)f);
        tgs1 = mix(vec4(1.0), tgs1, ifac_%(il)d);
""" % locals()
                        if blendspec.glossblendmode == "cover":
                            fshstr += """
        tgs0 = mix(tgs0, tgs1, ifac_%(il)d);
""" % locals()
                        elif blendspec.glossblendmode == "add":
                            fshstr += """
        tgs0 += tgs1;
"""
                        elif blendspec.glossblendmode == "multiply":
                            fshstr += """
        tgs0 *= tgs1;
"""
                        else:
                            raise StandardError(
                                "Unknown gloss blend mode for "
                                "blend %(ib)s layer %(il)s." % locals())
                        tsn += 1
            fshstr += """
        // Apply lighting.
        lit = vec4(l_lit);
"""
            if any_glow_layer:
                fshstr += """
        lit.rgb += tgw0.rgb;
"""
            if any_gloss_layer:
                fshstr += """
        lgs = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
            if any_gloss_layer:
                fshstr += """
        dirlit_gs(%(sunln)s, nrm, kshds, cdir, tgs0, lgs, lit);
        dirlit_gs(%(moonln)s, nrm, kshdm, cdir, tgs0, lgs, lit);
""" % shdinp
            else:
                fshstr += """
        dirlit(%(sunln)s, nrm, kshds, lit);
        dirlit(%(moonln)s, nrm, kshdm, lit);
""" % shdinp
            for pntln in pntlns:
                if any_gloss_layer:
                    fshstr += """
        pntlit_gs(%(pntln)s, l_vertpos, nrm, cdir, tgs0, lgs, lit);
""" % locals()
                else:
                    fshstr += """
        pntlit(%(pntln)s, l_vertpos, nrm, lit);
""" % locals()
            fshstr += """
        //tc0.rgb *= clamp(lit.rgb, 0.0, 1.0);
        tc0.rgb *= lit.rgb; // no cutoff
"""
            if any_gloss_layer:
                fshstr += """
        tc0.rgb = clamp(tc0.rgb + lgs.rgb, 0.0, 1.0);
        //tc0 = clamp(tc0 + lgs, 0.0, 1.0); // opaque reflection
"""
            if ib > 0:
                bchn = blend_ind_to_chn[ib]
                fshstr += """
        // Merge with previous blend.
        tc0 = mix(tc0p, tc0, mc.%(bchn)s);
""" % locals()
                if any_glow_layer:
                    fshstr += """
        tgw0 = mix(tgw0p, tgw0, mc.%(bchn)s);
""" % locals()
            fshstr += """
    }
"""
        fshstr += """
    vec4 color = tc0;
"""
        fshstr += """
    fogapl(color, l_fog, color);
""" % shdinp
        if any_glow:
            fshstr += """
    vec4 bloom;
    bloom.a = tgw0.a * color.a;
    bloom.rgb = tc0.rgb * bloom.a;
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
    %(osunvisn)s = vec4(0.0, 0.0, 0.0, 1.0);
""" % locals()
        if base.with_bloom:
            fshstr += """
    %(obloomn)s = bloom;
""" % locals()
        fshstr += """
}
"""
        if showas:
            printsh((vshstr, fshstr), showas)
        shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
        Terrain._shader_cache[shdkey] = shader
        return shader


    @staticmethod
    def _select_tiles (sizex, sizey,
                       offsetx, offsety,
                       numtilesx, numtilesy,
                       extents, relative, selmode):

        if extents is None:
            tilespec = []
            for i in xrange(numtilesx):
                for j in xrange(numtilesy):
                    tilespec.append((i, j))

        elif isinstance(extents, tuple):
            # Rectangle selection.
            (x1, y1), (x2, y2) = extents
            if relative:
                fi1 = x1 * numtilesx
                fj1 = y1 * numtilesy
                fi2 = x2 * numtilesx
                fj2 = y2 * numtilesy
            else:
                fi1 = ((x1 - offsetx) / sizex) * numtilesx
                fj1 = ((y1 - offsety) / sizey) * numtilesy
                fi2 = ((x2 - offsetx) / sizex) * numtilesx
                fj2 = ((y2 - offsety) / sizey) * numtilesy
            if selmode == 0: # any tile part inside rectangle
                i1 = int(fi1)
                j1 = int(fj1)
                i2 = int(fi2)
                j2 = int(fj2)
            elif selmode == 1: # tile center inside rectangle
                i1 = int(fi1 + 0.5)
                j1 = int(fj1 + 0.5)
                i2 = int(fi2 - 0.5)
                j2 = int(fj2 - 0.5)
            elif selmode == 2: # complete tile inside rectangle
                i1 = int(fi1 + 1.0)
                j1 = int(fj1 + 1.0)
                i2 = int(fi2 - 1.0)
                j2 = int(fj2 - 1.0)
            else:
                raise StandardError(
                    "Unknown mode '%d' for selecting tiles by rectangle."
                    % selmode)
            tilespec = []
            for i in xrange(i1, i2 + 1):
                for j in xrange(j1, j2 + 1):
                    tilespec.append((i, j))

        else:
                raise StandardError(
                    "Unknown type of extents for selecting tiles.")

        return tilespec


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        self._input_shader(dt)

        return task.cont


    def _input_shader (self, dt):

        pass


    def _mod_height_virtsurf (self, x, y, z, n, t, flush=False):

        if not self._virtsurf_store: # shortcut for performance
            return z, n, t

        q = self._geom.quad_index_for_xy(x - self._pos_x, y - self._pos_y)
        wnorm = (n is not None)
        for surf_ind in self._virtsurf_per_quad.get(q, ()):
            surf = self._virtsurf_store[surf_ind]
            if flush or not surf.flush():
                ret = surf.height(x, y, wnorm)
                if ret is not None:
                    zv = ret[0]
                    if z <= zv: # <= important for priority
                        if wnorm:
                            z, n, t = ret
                        else:
                            z, t = ret
        return z, n, t


    def height (self, x, y, flush=False):

        norm = Vec3D()
        pcz = Vec3D()
        tvinds = LVector3i()
        self._geom.interpolate_z(x, y, self._pos,
                                 pcz,
                                 norm=norm, wnorm=True,
                                 tvinds=tvinds, wtvinds=False)
        p, c, z = pcz; c = int(c)
        n = norm
        t = self._ground_type_by_cut[c]

        z, n, t = self._mod_height_virtsurf(x, y, z, n, t, flush=flush)

        return z, n, t


    def height_q (self, x, y, flush=False): # shortcut for performance

        norm = Vec3D()
        pcz = Vec3D()
        tvinds = LVector3i()
        self._geom.interpolate_z(x, y, self._pos,
                                 pcz,
                                 norm=norm, wnorm=False,
                                 tvinds=tvinds, wtvinds=False)
        p, c, z = pcz; c = int(c)
        n = None
        t = None

        z, n, t = self._mod_height_virtsurf(x, y, z, n, t, flush=flush)

        return z


    def max_height (self):

        return self._geom.max_z()


    def below_surface (self, x, y, z):

        if z < self._geom.max_z():
            q = self._geom.quad_index_for_xy(x - self._pos_x, y - self._pos_y)
            if q >= 0:
                # height(x, y) is very expensive,
                # execute it only if quad_max_z check passes.
                return z < self._geom.quad_max_z(q) and z < self.height_q(x, y)
            else:
                # This limit should not be zero, as this may be
                # a small embedded terrain while the main terrain
                # has a depression somewhere.
                # Check against a reasonable sub-SL altitude so that
                # vehicle physics don't go crazy.
                return z < -1000.0
        else:
            return False


    def extents (self):

        minx = -self._sizex * 0.5 + self._pos_x
        maxx = self._sizex * 0.5 + self._pos_x
        miny = -self._sizey * 0.5 + self._pos_y
        maxy = self._sizey * 0.5 + self._pos_y
        return minx, miny, maxx, maxy, self._visradius


    #def num_polys (self):

        #return self._globpoly, self._tilepoly, self._maxvispoly


    def set_render_wireframe (self, on=True):

        if on:
            self._geom.tile_root().setRenderModeWireframe()
        else:
            self._geom.tile_root().setRenderModeFilled()


    def pos (self, refbody=None, offset=None):

        refbody = refbody or self
        if offset is None:
            if refbody is self:
                return self.node.getPos()
            else:
                return self.node.getPos(refbody.node)
        else:
            return refbody.node.getRelativePoint(self.node, offset)


    def set_ground_type_for_cut (self, cut, gtype):

        self._ground_type_by_cut[cut] = gtype


    def add_virtual_surface (self, surf):

        surf_ind = len(self._virtsurf_store)
        self._virtsurf_store.append(surf)

        e1, e2 = surf.extents()
        e1 -= self._pos
        e2 -= self._pos
        x1, y1 = e1.getXy()
        x2, y2 = e2.getXy()
        fi1 = ((x1 - self._offsetx) / self._sizex) * self._numquadsx
        fj1 = ((y1 - self._offsety) / self._sizey) * self._numquadsy
        fi2 = ((x2 - self._offsetx) / self._sizex) * self._numquadsx
        fj2 = ((y2 - self._offsety) / self._sizey) * self._numquadsy
        # Any quad part inside rectangle.
        i1 = int(fi1)
        j1 = int(fj1)
        i2 = int(fi2)
        j2 = int(fj2)
        surf_maxz = e2[2]
        flush = surf.flush()
        if not flush:
            self._geom.update_max_z(surf_maxz)
        for i in xrange(i1, i2 + 1):
            for j in xrange(j1, j2 + 1):
                q = i * self._numquadsy + j
                if not flush:
                    self._geom.update_quad_max_z(q, surf_maxz)
                vsq = self._virtsurf_per_quad.get(q)
                if vsq is None:
                    vsq = []
                    self._virtsurf_per_quad[q] = vsq
                vsq.append(surf_ind)


    def replace_texture (self, cut, corner0, corner1, replspec):

        ic = cut
        it0, jt0 = corner0
        it1, jt1 = corner1
        for it in xrange(it0, it1 + 1):
            for jt in xrange(jt0, jt1 + 1):
                tile = self._tiles[it][jt][ic]
                if tile is not None:
                    texstack = self._texstack[ic][it][jt]
                    mod_texstack = texstack[:]
                    texstack_stmap = self._texstack_stmap[ic][it][jt]
                    for ttyp, ib, il, tpath in replspec:
                        ts = self._texstage_map[ttyp][ib][il]
                        k = texstack_stmap[id(ts)]
                        mod_texstack[k] = (ts, tpath)
                    self._texstack[ic][it][jt] = mod_texstack
                    set_texture(tile, extras=mod_texstack, clamp=False)


# :also-compiled:
class TerrainGeom (object):

    def __init__ (self, name,
                  sizex, sizey, offsetx, offsety,
                  heightmappath, haveheightmappath, hmdatapath, havehmdatapath,
                  maxsizexa, maxsizexb, havemaxsizex, maxsizey, havemaxsizey,
                  centerx, havecenterx, centery, havecentery,
                  mingray, havemingray, maxgray, havemaxgray,
                  minheight, haveminheight, maxheight, havemaxheight,
                  numtilesx, numtilesy,
                  celldensity, periodic,
                  cutmaskpaths, levints):

        cutmaskpaths = dec_lst_string(cutmaskpaths)
        levints = dec_lst_bool(levints)

        timeit = False

# @cache-key-start: terrain-generation

        # Construct everything.
        carg = AutoProps(
            sizex=sizex, sizey=sizey,
            offsetx=offsetx, offsety=offsety,
            heightmappath=heightmappath, haveheightmappath=haveheightmappath,
            hmdatapath=hmdatapath, havehmdatapath=havehmdatapath,
            maxsizexa=maxsizexa, maxsizexb=maxsizexb, havemaxsizex=havemaxsizex,
            maxsizey=maxsizey, havemaxsizey=havemaxsizey,
            centerx=centerx, havecenterx=havecenterx,
            centery=centery, havecentery=havecentery,
            mingray=mingray, havemingray=havemingray,
            maxgray=maxgray, havemaxgray=havemaxgray,
            minheight=minheight, haveminheight=haveminheight,
            maxheight=maxheight, havemaxheight=havemaxheight,
            numtilesx=numtilesx, numtilesy=numtilesy,
            celldensity=celldensity, periodic=periodic,
            cutmaskpaths=cutmaskpaths, levints=levints,
        )
        ret = None
        keyhx = None
        if name:
            tname = name
            fckey = []
            fckey.extend(cutmaskpaths)
            ecarg = AutoProps()
            if haveheightmappath:
                fckey.append(heightmappath)
                if havehmdatapath:
                    ecarg.hmdatapath = hmdatapath
                    fckey.append(hmdatapath)
            this_path = internal_path("data", __file__)
            key = (sorted(carg.props()), sorted(ecarg.props()),
                   get_cache_key_section(this_path.replace(".pyc", ".py"),
                                         "terrain-generation"))
            keyhx = key_to_hex(key, fckey)
# @cache-key-end: terrain-generation
            if timeit:
                t1 = time()
# @cache-key-start: terrain-generation
            ret = TerrainGeom._load_from_cache(tname, keyhx)
# @cache-key-end: terrain-generation
            if timeit and ret:
                t2 = time()
                dbgval(1, "terrain-load-from-cache",
                       (t2 - t1, "%.3f", "time", "s"))
# @cache-key-start: terrain-generation
        if not ret:
            ret = TerrainGeom._construct(**dict(carg.props()))
            celldata, elevdata, geomdata = ret
            if keyhx is not None:
# @cache-key-end: terrain-generation
                if timeit:
                    t1 = time()
# @cache-key-start: terrain-generation
                TerrainGeom._write_to_cache(tname, keyhx, celldata, elevdata, geomdata)
# @cache-key-end: terrain-generation
                if timeit:
                    t2 = time()
                    dbgval(1, "terrain-write-to-cache",
                           (t2 - t1, "%.3f", "time", "s"))
# @cache-key-start: terrain-generation
        else:
            celldata, elevdata, geomdata = ret
# @cache-key-end: terrain-generation

        (self._verts, self._tris, self._quadmap,
         self._maxz, self._maxqzs) = elevdata
        (self._numquadsx, self._numquadsy, self._numtilesx, self._numtilesy,
         self._tilesizex, self._tilesizey, self._numcuts,
         self._centerx, self._centery,
         self._maxsizexa, self._maxsizexb, self._maxsizey) = celldata
        self._tileroot, = geomdata

        self._sizex = sizex
        self._sizey = sizey
        self._offsetx = offsetx
        self._offsety = offsety


    def destroy (self):

        # Let it try harder to collect garbage.
        e1, e2, e3 = self._verts
        e1[:] = array("d", [0.0])
        e2[:] = array("d", [0.0])
        e3[:] = array("d", [0.0])
        self._verts = None
        del e1, e2, e3
        e1, e2, e3, e4 = self._tris
        e1[:] = array("l", [0])
        e2[:] = array("l", [0])
        e3[:] = array("l", [0])
        e4[:] = array("l", [0])
        self._tris = None
        del e1, e2, e3, e4
        e1, e2 = self._quadmap
        e1[:] = array("l", [0])
        e2[:] = array("l", [0])
        self._quadmap = None
        del e1, e2
        e1 = self._maxqzs
        e1[:] = array("d", [0.0])
        self._maxqzs = None
        del e1

        self._tileroot.removeNode()


    def tile_root (self):

        return self._tileroot


    def num_quads_x (self):

        return self._numquadsx

    def num_quads_y (self):

        return self._numquadsy


    def num_tiles_x (self):

        return self._numtilesx


    def num_tiles_y (self):

        return self._numtilesy


    def tile_size_x (self):

        return self._tilesizex


    def tile_size_y (self):

        return self._tilesizey


    def num_cuts (self):

        return self._numcuts


    def max_z (self):

        return self._maxz


    def update_max_z (self, z):

        self._maxz = max(self._maxz, z)


    def quad_max_z (self, q):

        return self._maxqzs[q]


    def update_quad_max_z (self, q, z):

        self._maxqzs[q] = max(self._maxqzs[q], z)


# @cache-key-start: terrain-generation
    class FlatCircle:

        def __init__ (self, name, centerx, centery, radius,
                      centerz=None, radiusout=0.0):
            self._name = name
            self._centerx = centerx
            self._centery = centery
            self._centerz = centerz
            self._radius = radius
            self._radiusout = 0.0

        def name (self):
            return self._name

        def refxy (self):
            return self._centerx, self._centery

        def refz (self):
            return self._centerz

        def set_refz (self, z):
            self._centerz = z

        def correct_z (self, x, y, z):

            if self._centerz is None:
                return None
            rdist = ((x - self._centerx)**2 + (y - self._centery)**2)**0.5
            if rdist <= self._radius:
                return self._centerz
            elif rdist <= self._radiusout:
                ifc = (rdist - self._radius) / (self._radiusout - self._radius)
                return self._centerz + (z - self._centerz) * ifc
            else:
                return None


    _gvformat = None

    @staticmethod
    def _construct (sizex, sizey, offsetx, offsety,
                    heightmappath, haveheightmappath, hmdatapath, havehmdatapath,
                    maxsizexa, maxsizexb, havemaxsizex, maxsizey, havemaxsizey,
                    centerx, havecenterx, centery, havecentery,
                    mingray, havemingray, maxgray, havemaxgray,
                    minheight, haveminheight, maxheight, havemaxheight,
                    numtilesx, numtilesy,
                    celldensity, periodic,
                    cutmaskpaths, levints):

# @cache-key-end: terrain-generation
        report(_("Constructing terrain."))
        timeit = False
        memit = False
# @cache-key-start: terrain-generation

# @cache-key-end: terrain-generation
        if timeit:
            t0 = time()
            t1 = t0
# @cache-key-start: terrain-generation

        # Load the height map.
        flats = []
        if haveheightmappath:
            if havehmdatapath:
                ret = TerrainGeom._read_heightmap_data(hmdatapath)
                # Conctructor arguments override read data.
                sxa, sxb, sy, mnz, mxz, mng, mxg, flats = ret
                if not havemaxsizex:
                    maxsizexa = sxa
                    maxsizexb = sxb
                    havemaxsizex = True
                if not havemaxsizey:
                    maxsizey = sy
                    havemaxsizey = True
                if not havemingray:
                    mingray = mng
                    havemingray = True
                if not havemaxgray:
                    maxgray = mxg
                    havemaxgray = True
                if not haveminheight:
                    minheight = mnz
                    haveminheight = True
                if not havemaxheight:
                    maxheight = mxz
                    havemaxheight = True
            heightmap = UnitGrid2(heightmappath)
        else:
            heightmap = UnitGrid2(0.0)

        # Derive any non-initialized heightmap data.
        if not havemaxsizex:
            maxsizexa = sizex
            maxsizexb = sizex
        if not havemaxsizey:
            maxsizey = sizey
        if not havemingray:
            mingray = 0
        if not havemaxgray:
            maxgray = 255
        if not haveminheight:
            minheight = 0.0
        if not haveminheight and not havemaxheight:
            minheight = 0.0
            maxheight = 0.0
        elif not haveminheight:
            minheight = maxheight
        elif not havemaxheight:
            maxheight = minheight
        if not havecenterx:
            centerx = 0.0
        if not havecentery:
            centery = 0.0

        mingray = int(mingray)
        maxgray =  int(maxgray)
        minheight = float(minheight)
        maxheight = float(maxheight)
        centerx = float(centerx)
        centery = float(centery)

        # Derive cell data.
        def derive_cell_data (size, hmapsize, numtiles):
            tilesize = size / numtiles
            wquadsize = (size / hmapsize) / sqrt(celldensity)
            numtilequads = int(ceil(tilesize / wquadsize))
            numquads = numtiles * numtilequads
            return numquads, tilesize, numtilequads
        maxsizexr = (maxsizexa + maxsizexb) * 0.5
        hmapsizex = heightmap.num_x() * (sizex / maxsizexr)
        ret = derive_cell_data(sizex, hmapsizex, numtilesx)
        numquadsx, tilesizex, numtilequadsx = ret
        hmapsizey = heightmap.num_y() * (sizey / maxsizey)
        ret = derive_cell_data(sizey, hmapsizey, numtilesy)
        numquadsy, tilesizey, numtilequadsy = ret
# @cache-key-end: terrain-generation
        #print ("--terrain-construct-celldata  "
               #"nqx=%d  nqy=%d  ntx=%d  nty=%d  tszx=%.1f  tszy=%.1f  "
               #"estnp=%d  "
               #% (numquadsx, numquadsy, numtilesx, numtilesy,
                  #tilesizex, tilesizey,
                  #(numquadsx * numquadsy * 2)))
# @cache-key-start: terrain-generation

        # Load cut masks.
        cutmasks = []
        for cutmaskpath in cutmaskpaths:
            cutmask = UnitGrid2(cutmaskpath)
            cutmasks.append(cutmask)

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-collect-maps",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        cintdiv, cintlam, cintmu, cintiter = 2, 0.8, -0.2, 10
        ret = TerrainGeom._triangulate(
            heightmap, cutmasks, levints,
            maxsizexa, maxsizexb, maxsizey, centerx, centery,
            sizex, sizey, offsetx, offsety, numquadsx, numquadsy,
            mingray, maxgray, minheight, maxheight, flats,
            cintdiv, cintlam, cintmu, cintiter,
            periodic=periodic, timeit=timeit, memit=memit)
        verts, tris, quadmap = ret[:3]
# @cache-key-end: terrain-generation
        if timeit:
            t1 = ret[3]
# @cache-key-start: terrain-generation

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-categorize-polygons",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Construct vertex format for tile textures.
        gvformat = TerrainGeom._gvformat
        if gvformat is None:
            gvarray = GeomVertexArrayFormat()
            gvarray.addColumn(InternalName.getVertex(), 3,
                              Geom.NTFloat32, Geom.CPoint)
            gvarray.addColumn(InternalName.getNormal(), 3,
                              Geom.NTFloat32, Geom.CVector)
            gvarray.addColumn(InternalName.getTangent(), 3,
                              Geom.NTFloat32, Geom.CVector)
            gvarray.addColumn(InternalName.getBinormal(), 3,
                              Geom.NTFloat32, Geom.CVector)
            gvarray.addColumn(InternalName.getColor(), 4,
                              Geom.NTFloat32, Geom.CColor)
            gvarray.addColumn(InternalName.getTexcoord(), 2,
                              Geom.NTFloat32, Geom.CTexcoord)
            gvformat = GeomVertexFormat()
            gvformat.addArray(gvarray)
            gvformat = GeomVertexFormat.registerFormat(gvformat)
            TerrainGeom._gvformat = gvformat

        # Create tiles.
        tiles = []
        numcuts = len(cutmasks) + 1
        for cut in xrange(numcuts):
            tiles1 = TerrainGeom._make_tiles(
                offsetx, offsety, numquadsx, numquadsy,
                numtilesx, numtilesy, tilesizex, tilesizey,
                numtilequadsx, numtilequadsy,
                gvformat,
                verts, tris, quadmap, levints,
                cut)
            tiles.append(tiles1)

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-create-tiles",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Assemble tiles into final terrain.
        tileroot = NodePath("terrain")
        dummyoutvisradius = (0.5 * sqrt(tilesizex**2 + tilesizey**2)) * 4
        for it in xrange(numtilesx):
            for jt in xrange(numtilesy):
                ijtile = NodePath("tile-i%d-j%d" % (it, jt))
                for cut in xrange(numcuts):
                    ctile, x, y = tiles[cut][it][jt]
                    ctile.reparentTo(ijtile)
                ijtlod = LODNode("lod-visradius")
                ijtlnp = NodePath(ijtlod)
                ijtlnp.reparentTo(tileroot)
                ijtlnp.setPos(x, y, 0.0) # all cuts have same (x, y)
                ijtlod.addSwitch(dummyoutvisradius, 0.0)
                ijtile.reparentTo(ijtlnp)

        # Derive maximum heights for faster terrain collision check.
        maxz = -1e30
        maxqzs = array("d", [0.0] * (numquadsx * numquadsy))
        tri1s, tri2s, tri3s = tris[:3]
        qm1, qm2 = quadmap
        vertzs = verts[2]
        for i in xrange(numquadsx):
            for j in xrange(numquadsy):
                q = i * numquadsy + j
                ks = range(qm1[q], qm2[q])
                maxqz = -1e30
                for k in ks:
                    l1, l2, l3 = tri1s[k], tri2s[k], tri3s[k]
                    maxqz = max(maxqz, vertzs[l1], vertzs[l2], vertzs[l3])
                maxqzs[q] = maxqz
                maxz = max(maxz, maxqz)

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-cumulative",
                   (t2 - t0, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        celldata = (numquadsx, numquadsy, numtilesx, numtilesy,
                    tilesizex, tilesizey, numcuts,
                    centerx, centery,
                    maxsizexa, maxsizexb, maxsizey)
        elevdata = (verts, tris, quadmap, maxz, maxqzs)
        geomdata = (tileroot,)
        return celldata, elevdata, geomdata


    _cache_pdir = "terrain"

    @staticmethod
    def _cache_key_path (tname):

        return join_path(TerrainGeom._cache_pdir, tname, "terrain.key")


    @staticmethod
    def _cache_celldata_path (tname):

        return join_path(TerrainGeom._cache_pdir, tname, "celldata.pkl")


    @staticmethod
    def _cache_elevdata_path (tname):

        return join_path(TerrainGeom._cache_pdir, tname, "elevdata.pkl.gz")


    @staticmethod
    def _cache_geomdata_path (tname):

        return join_path(TerrainGeom._cache_pdir, tname, "geomdata.bam")

# @cache-key-end: terrain-generation

    @staticmethod
    def _load_from_cache (tname, keyhx):

        keypath = TerrainGeom._cache_key_path(tname)
        if not path_exists("cache", keypath):
            return None
        okeyhx = open(real_path("cache", keypath), "rb").read()
        if okeyhx != keyhx:
            return None

        celldatapath = TerrainGeom._cache_celldata_path(tname)
        if not path_exists("cache", celldatapath):
            return None
        fh = open(real_path("cache", celldatapath), "rb")
        celldata = pickle.load(fh)
        fh.close()

        #from time import sleep
        #print "--terrain235 start-sleep"
        #sleep(10)
        #print "--terrain236 end-sleep"
        elevdatapath = TerrainGeom._cache_elevdata_path(tname)
        if not path_exists("cache", elevdatapath):
            return None
        fh = GzipFile(real_path("cache", elevdatapath), "rb")
        elevdata = pickle.loads(fh.read())
        fh.close()
        del fh # prevent memory consumption peak
        #print "--terrain237 start-sleep"
        #sleep(10)
        #print "--terrain238 end-sleep"

        #print "--terrain245 start-sleep"
        #sleep(10)
        #print "--terrain246 end-sleep"
        geomdatapath = TerrainGeom._cache_geomdata_path(tname)
        if not path_exists("cache", geomdatapath):
            return None
        geomroot = base.load_model("cache", geomdatapath, cache=False)
        geomdata = geomroot.getChildren().getPaths()
        #print "--terrain247 start-sleep"
        #sleep(10)
        #print "--terrain248 end-sleep"

        return celldata, elevdata, geomdata

# @cache-key-start: terrain-generation

    @staticmethod
    def _write_to_cache (tname, keyhx, celldata, elevdata, geomdata):

        keypath = TerrainGeom._cache_key_path(tname)

        cdirpath = path_dirname(keypath)
        if path_exists("cache", cdirpath):
            rmtree(real_path("cache", cdirpath))
        os.makedirs(real_path("cache", cdirpath))

        geomdatapath = TerrainGeom._cache_geomdata_path(tname)
        geomroot = NodePath("root")
        for np in geomdata:
            np.reparentTo(geomroot)
        base.write_model_bam(geomroot, "cache", geomdatapath)

        elevdatapath = TerrainGeom._cache_elevdata_path(tname)
        fh = GzipFile(real_path("cache", elevdatapath), "wb", compresslevel=3)
        pickle.dump(elevdata, fh, -1)
        fh.close()

        celldatapath = TerrainGeom._cache_celldata_path(tname)
        fh = open(real_path("cache", celldatapath), "wb")
        pickle.dump(celldata, fh, -1)
        fh.close()

        fh = open(real_path("cache", keypath), "wb")
        fh.write(keyhx)
        fh.close()


    @staticmethod
    def _read_heightmap_data (fpath):

        mhdat = SafeConfigParser()
        mhdat.readfp(codecs.open(real_path("data", fpath), "r", "utf8"))
        extsec = "extents"
        if not mhdat.has_section(extsec):
            raise StandardError(
                "No '%s' section in heightmap data file '%s'." %
                (extsec, fpath))
        sxfld, sxafld, sxbfld = "sizex", "sizexs", "sizexn"
        xymult = 1000.0
        if (mhdat.has_option(extsec, sxafld) and
            mhdat.has_option(extsec, sxbfld)):
            sxa = mhdat.getfloat(extsec, sxafld) * xymult
            sxb = mhdat.getfloat(extsec, sxbfld) * xymult
        elif mhdat.has_option(extsec, sxfld):
            sxa = sxb = mhdat.getfloat(extsec, sxfld) * xymult
        else:
            raise StandardError(
                "No field '%s' nor fields '%s' and '%s' in section '%s' "
                "in file '%s'." % (sxfld, sxafld, sxbfld, extsec, fpath))
        vals = []
        for fld, typ, defval, mult in (
            ("sizey", float, None, xymult),
            ("minz", float, None, 1.0),
            ("maxz", float, None, 1.0),
            ("ming", int, 0, 1),
            ("maxg", int, 255, 1),
        ):
            val = TerrainGeom._getconfval(fpath, mhdat, extsec, fld, typ, defval)
            vals.append(val * mult)
        sy, mnz, mxz, mng, mxg = vals

        flats = []
        flatpref = "flat-"
        for flatsec in mhdat.sections():
            if flatsec.startswith(flatpref):
                def getf (field, defval=()):
                    return TerrainGeom._getconfval(fpath, mhdat, flatsec, field,
                                                   float, defval)
                name = flatsec[len(flatpref):]
                cx = getf("centerx") * xymult
                cy = getf("centery") * xymult
                cz = getf("centerz", ()) or None
                if mhdat.has_option(flatsec, "radius"):
                    rad = getf("radius") * xymult
                    radout = getf("radiusout", 0.0) * xymult
                    flat = TerrainGeom.FlatCircle(name, cx, cy, rad, cz, radout)
                else:
                    raise StandardError(
                        "Unknown flat section type '%s' in file '%s'." %
                        (flatsec, fpath))
                flats.append(flat)

        return sxa, sxb, sy, mnz, mxz, mng, mxg, flats


    @staticmethod
    def _getconfval (cfgpath, config, section, field, typ, defval=None):

        if config.has_option(section, field):
            strval = config.get(section, field)
            try:
                val = typ(strval)
            except:
                raise StandardError(
                    "Cannot convert field '%s' to type %s "
                    "in section '%s' file '%s'." %
                    (field, typ, cfgpath, section))
            return val
        elif defval is not None:
            return defval
        else:
            raise StandardError(
                "Missing field '%s' in section '%s' file '%s'." %
                (field, cfgpath, section))


    @staticmethod
    def _triangulate (heightmap, cutmasks, levints,
                      maxsizexa, maxsizexb, maxsizey, centerx, centery,
                      sizex, sizey, offsetx, offsety,
                      numquadsx, numquadsy,
                      mingray, maxgray, minheight, maxheight, flats,
                      cintdiv, cintlam, cintmu, cintiter,
                      periodic=False, timeit=False, memit=False):

# @cache-key-end: terrain-generation
        if timeit:
            t0 = time()
            t1 = t0
# @cache-key-start: terrain-generation

        quadsizex = sizex / numquadsx
        quadsizey = sizey / numquadsy

        # When converting coordinates to non-periodic unit square,
        # they may fall slightly out of range due to rounding.
        # This is the tolerance to accept that and move to nearest boundary.
        # The value should work for single precision too.
        usqtol = 1e-4

        # Assemble the cut map.
        cutmap = [array("l", [0] * (numquadsy + 1))
                  for x in xrange(numquadsx + 1)]
        for i, cutmask in enumerate(cutmasks):
            c = i + 1
            for i in xrange(numquadsx + 1):
                x = i * quadsizex + offsetx
                for j in xrange(numquadsy + 1):
                    y = j * quadsizey + offsety
                    xu, yu = TerrainGeom._to_unit_trap(
                        sizex, sizey, offsetx, offsety, maxsizexa, maxsizexb,
                        maxsizey, centerx, centery,
                        x, y)
                    cval = cutmask(xu, yu, usqtol, periodic)
                    if cval > 0.5:
                        cutmap[i][j] = c

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-assemble-cut-map",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Split cut interface quads into triangles.
        # NOTE: May modify the cut map, to repair problematic areas.
        ret = TerrainGeom._split_interface_quads(cutmap, quadsizex, quadsizey,
                                                 offsetx, offsety, cintdiv,
                                                 cintlam, cintmu, cintiter)
        intquadchains, intquadverts, intquadtris, intquadlinks, intcurves = ret

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-compute-cut-interfaces",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Compute quad vertices.
        iqvertxs, iqvertys, iqvertzs = intquadverts
        niqverts = len(iqvertxs)
        nverts = (numquadsx + 1) * (numquadsy + 1) + niqverts
        vertxs = array("d", [0.0] * nverts)
        vertys = array("d", [0.0] * nverts)
        vertzs = array("d", [0.0] * nverts)
        verts = (vertxs, vertys, vertzs)
        for i in xrange(numquadsx + 1):
            x = i * quadsizex + offsetx
            j0 = i * (numquadsy + 1)
            for j in xrange(numquadsy + 1):
                y = j * quadsizey + offsety
                vertxs[j0 + j] = x; vertys[j0 + j] = y

        # Add cut interface vertices.
        i0 = (numquadsx + 1) * (numquadsy + 1)
        for i in xrange(niqverts):
            vertxs[i0 + i] = iqvertxs[i]; vertys[i0 + i] = iqvertys[i]

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-compute-quad-vertices",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Add global links for cut interface triangles.
        nquads = numquadsx * numquadsy
        qm1 = array("l", [-1] * nquads)
        qm2 = array("l", [-1] * nquads)
        quadmap = (qm1, qm2)
        for (i, j), (itri1, itri2) in intquadlinks:
            q = i * numquadsy + j
            qm1[q] = itri1
            qm2[q] = itri2

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-add-quad-links",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Split non-interface quads into triangles and add global links.
        #tris = []
        iqtri1s, iqtri2s, iqtri3s, iqtrics = intquadtris
        niqtris = len(iqtri1s)
        ntris = 2 * (numquadsx * numquadsy - len(intquadlinks)) + niqtris
        tri1s = array("l", [0] * ntris)
        tri2s = array("l", [0] * ntris)
        tri3s = array("l", [0] * ntris)
        trics = array("l", [0] * ntris)
        tris = (tri1s, tri2s, tri3s, trics)
        k = 0
        for i in xrange(numquadsx):
            for j in xrange(numquadsy):
                q = i * numquadsy + j
                if qm1[q] >= 0: # interface quad
                    continue
                # Indices of vertices.
                k1 = i * (numquadsy + 1) + j
                k2 = (i + 1) * (numquadsy + 1) + j
                k3 = (i + 1) * (numquadsy + 1) + (j + 1)
                k4 = i * (numquadsy + 1) + (j + 1)
                # All four points from same cut (not interface quad).
                c = cutmap[i][j]
                # Whether to split this quad bottom-left top-right.
                bltr = (i % 2 + j) % 2
                if bltr:
                    #tris.append(((k1, k2, k3), c))
                    #tris.append(((k1, k3, k4), c))
                    tri1s[k] = k1; tri2s[k] = k2; tri3s[k] = k3; trics[k] = c
                    tri1s[k + 1] = k1; tri2s[k + 1] = k3; tri3s[k + 1] = k4; trics[k + 1] = c
                else:
                    #tris.append(((k2, k3, k4), c))
                    #tris.append(((k2, k4, k1), c))
                    tri1s[k] = k2; tri2s[k] = k3; tri3s[k] = k4; trics[k] = c
                    tri1s[k + 1] = k2; tri2s[k + 1] = k4; tri3s[k + 1] = k1; trics[k + 1] = c
                # Quad to triangle links.
                qm1[q] = k
                qm2[q] = k + 2
                k += 2

        # Add cut interface triangles.
        #tris.extend(intquadtris)
        k0 = ntris - niqtris
        for k in xrange(niqtris):
            tri1s[k0 + k] = iqtri1s[k]
            tri2s[k0 + k] = iqtri2s[k]
            tri3s[k0 + k] = iqtri3s[k]
            trics[k0 + k] = iqtrics[k]

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-assemble-triangulation",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Compute height at world (x, y).
        hpv = (maxheight - minheight) / ((maxgray - mingray) / 255.0)
        def getz (x, y):
            xu, yu = TerrainGeom._to_unit_trap(sizex, sizey, offsetx, offsety,
                                               maxsizexa, maxsizexb, maxsizey,
                                               centerx, centery,
                                               x, y)
            hval = heightmap(xu, yu, usqtol, periodic)
            z = minheight + (hval - mingray / 255.0) * hpv
            return z

        # Equip flats with heights.
        for flat in flats:
            if flat.refz() is None:
                flat.set_refz(getz(*flat.refxy()))

        # Equip vertices with heights.
        for i in xrange(nverts):
            x, y = vertxs[i], vertys[i]
            z = getz(x, y)
            for flat in flats:
                zc = flat.correct_z(x, y, z)
                if zc is not None:
                    z = zc
                    break
            vertzs[i] = z

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-compute-per-vertex-heights",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        # Level heights at interface vertices.
        l0 = nverts - niqverts
        for ic in xrange(len(intquadchains)):
            intcurve, closed = intcurves[ic]
            intquadchain, closed = intquadchains[ic]
            cl, cr = TerrainGeom._interface_cut_levels(cutmap, intquadchain)
            if levints[cl] or levints[cr]:
                l1 = l0 + len(intcurve)
                cvinds = range(l0, l1)
                TerrainGeom._level_curve_to_left(sizex, sizey, offsetx, offsety,
                                                 numquadsx, numquadsy,
                                                 verts, tris, quadmap,
                                                 cvinds, closed, cl)
            l0 += len(intcurve)

# @cache-key-end: terrain-generation
        if timeit:
            t2 = time()
            dbgval(1, "terrain-level-interface-vertices",
                   (t2 - t1, "%.3f", "time", "s"))
            t1 = t2
        if memit:
            os.system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`")
# @cache-key-start: terrain-generation

        ret = (verts, tris, quadmap)
# @cache-key-end: terrain-generation
        if timeit:
            ret += (t1,)
# @cache-key-start: terrain-generation
        return ret


    @staticmethod
    def _to_unit_trap (sizex, sizey, offsetx, offsety,
                       maxsizexa, maxsizexb, maxsizey, centerx, centery, x, y):

        x1 = (x - offsetx) + centerx
        y1 = (y - offsety) + centery
        y1u = y1 / maxsizey + 0.5 * (1.0 - sizey / maxsizey)
        maxsizex = maxsizexa + (maxsizexb - maxsizexa) * y1u
        x1u = x1 / maxsizex + 0.5 * (1.0 - sizex / maxsizex)
        return Vec2D(x1u, y1u)


    @staticmethod
    def _get_tri_verts (tri, verts):

        Pt = Point3D

        k1, k2, k3 = tri
        vertxs, vertys, vertzs = verts
        v1 = Pt(vertxs[k1], vertys[k1], vertzs[k1])
        v2 = Pt(vertxs[k2], vertys[k2], vertzs[k2])
        v3 = Pt(vertxs[k3], vertys[k3], vertzs[k3])
        return v1, v2, v3


    @staticmethod
    def _split_interface_quads (cutmap, quadsizex, quadsizey,
                                offsetx, offsety, subdiv,
                                tbslam, tbsmu, tbsiter):

        numquadsx = len(cutmap) - 1
        numquadsy = len(cutmap[0]) - 1

        # Correct thin diagonal cuts.
        anythin = True
        while anythin:
            anythin = False
            for i in xrange(numquadsx):
                for j in xrange(numquadsy):
                    c1 = cutmap[i][j]
                    c2 = cutmap[i + 1][j]
                    c3 = cutmap[i + 1][j + 1]
                    c4 = cutmap[i][j + 1]
                    if c1 == c3 and c2 == c4 and c1 != c2:
                        if c1 > c2:
                            cutmap[i][j + 1] = c1
                        else:
                            cutmap[i][j] = c2
                        anythin = True

        # Collect interface quad chains.
        freemap = [array("l", [1] * numquadsy) for x in xrange(numquadsx)]
        intquadchains = []
        for i in xrange(numquadsx):
            for j in xrange(numquadsy):
                if freemap[i][j]:
                    c1 = cutmap[i][j]
                    c2 = cutmap[i + 1][j]
                    c3 = cutmap[i + 1][j + 1]
                    c4 = cutmap[i][j + 1]
                    cset = set((c1, c2, c3, c4))
                    if len(cset) == 2:
                        cr, cl = sorted(cset)
                        # ...this order places the higher cut on the left of
                        # the oriented interface curve.
                        ret = TerrainGeom._extract_interface_quads(
                            cutmap, i, j, cl, cr, freemap)
                        intquadchain, closed = ret
                        intquadchains.append((intquadchain, closed))
                        #print "--chain", len(intquadchain), closed
                    elif len(cset) > 2:
                        raise StandardError(
                            "Neighboring points from more than two cuts "
                            "at (%d, %d)." % (i, j))

        # Construct interface curves.
        intcurves = []
        for q in range(len(intquadchains)):
            intquadchain, closed = intquadchains[q]
            intcurve = TerrainGeom._init_interface_curve(
                cutmap, intquadchain, closed,
                quadsizex, quadsizey, offsetx, offsety,
                subdiv)
            intcurve = TerrainGeom._smooth_interface_curve(
                intcurve, closed, subdiv, tbslam, tbsmu, tbsiter)
            intcurves.append((intcurve, closed))

        # Number of quad vertices and triangles in non-interface quads,
        # which are added in front of interface-related vertices and triangles.
        nverts0 = (numquadsx + 1) * (numquadsy + 1)
        ntris0 = 2 * (numquadsx * numquadsy -
                      sum(len(x[0]) for x in intquadchains))

        # Triangulate interface quads.
        #intquadverts = []
        vertxs = []; vertys = []; vertzs = []
        intquadverts = (vertxs, vertys, vertzs)
        #intquadtris = []
        tri1s = []; tri2s = []; tri3s = []; trics = []
        intquadtris = (tri1s, tri2s, tri3s, trics)
        intquadlinks = []
        for q in range(len(intquadchains)):
            intquadchain, closed = intquadchains[q]
            intcurve, closed = intcurves[q]
            ret = TerrainGeom._triangulate_interface_quads(
                cutmap, quadsizex, quadsizey, offsetx, offsety,
                intquadchain, intcurve, subdiv, nverts0, ntris0)
            cverts, ctris, clinks = ret
            #intquadverts.extend(cverts)
            vxs, vys, vzs = cverts
            vertxs.extend(vxs); vertys.extend(vys); vertzs.extend(vzs)
            #intquadtris.extend(ctris)
            t1s, t2s, t3s, tcs = ctris
            tri1s.extend(t1s); tri2s.extend(t2s); tri3s.extend(t3s); trics.extend(tcs)
            intquadlinks.extend(clinks)
            nverts0 += len(vxs)
            ntris0 += len(t1s)

        return intquadchains, intquadverts, intquadtris, intquadlinks, intcurves


    @staticmethod
    def _extract_interface_quads (cutmap, i0, j0, cl, cr, freemap):

        # Collect and join the two chain segments split by the given point.
        qcparts = []
        closed = True
        for i in range(2):
            ret = TerrainGeom._extract_interface_quads_1(
                cutmap, i0, j0, cl, cr, freemap)
            qcpart, cutbdry = ret
            closed = closed and not cutbdry
            qcparts.append(qcpart)
        intquadchain = list(reversed(qcparts[0])) + qcparts[1][1:]

        # Orient the chain so that it runs counter-clockwise around the cut.
        c0l, c0r = TerrainGeom._interface_cut_levels(cutmap, intquadchain)
        if c0l != cl:
            intquadchain = list(reversed(intquadchain))

        return intquadchain, closed


    @staticmethod
    def _extract_interface_quads_1 (cutmap, i0, j0, cl, cr, freemap):

        numquadsx = len(cutmap) - 1
        numquadsy = len(cutmap[0]) - 1

        intquadchain = []
        i, j = i0, j0
        while True:
            freemap[i][j] = 0
            selij = None
            cutbdry = False
            ncl = 0
            for (di, dj), (di1, dj1), (di2, dj2) in (
                ((1, 0), (1, 0), (1, 1)),
                ((0, 1), (1, 1), (0, 1)),
                ((-1, 0), (0, 1), (0, 0)),
                ((0, -1), (0, 0), (1, 0)),
            ):
                c1 = cutmap[i + di1][j + dj1]
                c2 = cutmap[i + di2][j + dj2]
                if c1 == cl:
                    ncl += 1
                    if (i + di1 == 0 or i + di1 == numquadsx or
                        j + dj1 == 0 or j + dj1 == numquadsy):
                        cutbdry = True
                if (selij is None and
                    0 <= i + di < numquadsx and
                    0 <= j + dj < numquadsy and
                    freemap[i + di][j + dj] and
                    (c1 == cl or c2 == cl) and
                    c1 != c2):
                    selij = (i + di, j + dj)
            intquadchain.append(((i, j), ncl))
            if selij is not None:
                i, j = selij
            else:
                break

        return intquadchain, cutbdry


    @staticmethod
    def _init_interface_curve (cutmap, intquadchain, closed,
                               quadsizex, quadsizey, offsetx, offsety, subdiv,
                               fromcut=0.5):

        Vt = Vec3D

        qsx = quadsizex; qsy = quadsizey
        subdivc = subdiv if subdiv % 2 == 0 else subdiv + 1
        subdivch = subdivc / 2
        dx = qsx / subdivc; dy = qsy / subdivc
        dxc = dx * 2; dyc = dy * 2
        ka = 1.0 - fromcut; kb = fromcut
        cl, cr = TerrainGeom._interface_cut_levels(cutmap, intquadchain)

        # NOTE: The assumption is that the chain is oriented counter-clockwise
        # around the higher cut, i.e. that the higher cut is always on the left.
        lenqc = len(intquadchain)
        intcurve = []
        for k in xrange(lenqc):
            (i, j), ncl = intquadchain[k]
            c1 = cutmap[i][j]
            c2 = cutmap[i + 1][j]
            c3 = cutmap[i + 1][j + 1]
            c4 = cutmap[i][j + 1]
            x0 = i * qsx + offsetx; y0 = j * qsy + offsety
            sf = 0 if (closed or k + 1 < lenqc) else 1
            if ncl == 1:
                for s in range(subdivch):
                    if c1 == cl:
                        pa = Vt(x0, y0, 0.0)
                        pb = Vt(x0 + qsx, y0 + dyc * s, 0.0)
                        gva = (0, 0)
                        gvb = (1, 0) if s == 0 else None
                    elif c2 == cl:
                        pa = Vt(x0 + qsx, y0, 0.0)
                        pb = Vt(x0 + qsx - dxc * s, y0 + qsy, 0.0)
                        gva = (1, 0)
                        gvb = (1, 1) if s == 0 else None
                    elif c3 == cl:
                        pa = Vt(x0 + qsx, y0 + qsy, 0.0)
                        pb = Vt(x0, y0 + qsy - dyc * s, 0.0)
                        gva = (1, 1)
                        gvb = (0, 1) if s == 0 else None
                    elif c4 == cl:
                        pa = Vt(x0, y0 + qsy, 0.0)
                        pb = Vt(x0 + dxc * s, y0, 0.0)
                        gva = (0, 1)
                        gvb = (0, 0) if s == 0 else None
                    intcurve.append((pa * ka + pb * kb, pa, pb, gva, gvb))
                for s in range(subdivch + sf):
                    if c1 == cl:
                        pa = Vt(x0, y0, 0.0)
                        pb = Vt(x0 + qsx - dxc * s, y0 + qsy, 0.0)
                        gva = (0, 0)
                        gvb = ((1, 1) if s == 0 else
                               (0, 1) if s == subdivch else
                               None)
                    elif c2 == cl:
                        pa = Vt(x0 + qsx, y0, 0.0)
                        pb = Vt(x0, y0 + qsy - dyc * s, 0.0)
                        gva = (1, 0)
                        gvb = ((0, 1) if s == 0 else
                               (0, 0) if s == subdivch else
                               None)
                    elif c3 == cl:
                        pa = Vt(x0 + qsx, y0 + qsy, 0.0)
                        pb = Vt(x0 + dxc * s, y0, 0.0)
                        gva = (1, 1)
                        gvb = ((0, 0) if s == 0 else
                               (1, 0) if s == subdivch else
                               None)
                    elif c4 == cl:
                        pa = Vt(x0, y0 + qsy, 0.0)
                        pb = Vt(x0 + qsx, y0 + dyc * s, 0.0)
                        gva = (0, 1)
                        gvb = ((1, 0) if s == 0 else
                               (1, 1) if s == subdivch else
                               None)
                    intcurve.append((pa * ka + pb * kb, pa, pb, gva, gvb))
            elif ncl == 2:
                for s in range(subdivc + sf):
                    if c1 == cl and c2 == cl:
                        pa = Vt(x0 + qsx - dx * s, y0, 0.0)
                        pb = Vt(x0 + qsx - dx * s, y0 + qsy, 0.0)
                        gva, gvb = (((1, 0), (1, 1)) if s == 0 else
                                    ((0, 0), (0, 1)) if s == subdivc else
                                    (None, None))
                    elif c2 == cl and c3 == cl:
                        pa = Vt(x0 + qsx, y0 + qsy - dy * s, 0.0)
                        pb = Vt(x0, y0 + qsy - dy * s, 0.0)
                        gva, gvb = (((1, 1), (0, 1)) if s == 0 else
                                    ((1, 0), (0, 0)) if s == subdivc else
                                    (None, None))
                    elif c3 == cl and c4 == cl:
                        pa = Vt(x0 + dx * s, y0 + qsy, 0.0)
                        pb = Vt(x0 + dx * s, y0, 0.0)
                        gva, gvb = (((0, 1), (0, 0)) if s == 0 else
                                    ((1, 1), (1, 0)) if s == subdivc else
                                    (None, None))
                    elif c4 == cl and c1 == cl:
                        pa = Vt(x0, y0 + dy * s, 0.0)
                        pb = Vt(x0 + qsx, y0 + dy * s, 0.0)
                        gva, gvb = (((0, 0), (1, 0)) if s == 0 else
                                    ((0, 1), (1, 1)) if s == subdivc else
                                    (None, None))
                    intcurve.append((pa * ka + pb * kb, pa, pb, gva, gvb))
            elif ncl == 3:
                for s in range(subdivc / 2):
                    if c1 == cr:
                        pa = Vt(x0 + dxc * s, y0 + qsy, 0.0)
                        pb = Vt(x0, y0, 0.0)
                        gva = (0, 1) if s == 0 else None
                        gvb = (0, 0)
                    elif c2 == cr:
                        pa = Vt(x0, y0 + dyc * s, 0.0)
                        pb = Vt(x0 + qsx, y0, 0.0)
                        gva = (0, 0) if s == 0 else None
                        gvb = (1, 0)
                    elif c3 == cr:
                        pa = Vt(x0 + qsx - dxc * s, y0, 0.0)
                        pb = Vt(x0 + qsx, y0 + qsy, 0.0)
                        gva = (1, 0) if s == 0 else None
                        gvb = (1, 1)
                    elif c4 == cr:
                        pa = Vt(x0 + qsx, y0 + qsy - dyc * s, 0.0)
                        pb = Vt(x0, y0 + qsy, 0.0)
                        gva = (1, 1) if s == 0 else None
                        gvb = (0, 1)
                    intcurve.append((pa * ka + pb * kb, pa, pb, gva, gvb))
                for s in range(subdivc / 2 + sf):
                    if c1 == cr:
                        pa = Vt(x0 + qsx, y0 + qsy - dyc * s, 0.0)
                        pb = Vt(x0, y0, 0.0)
                        gva = ((1, 1) if s == 0 else
                               (0, 1) if s == subdivch else
                               None)
                        gvb = (0, 0)
                    elif c2 == cr:
                        pa = Vt(x0 + dxc * s, y0 + qsy, 0.0)
                        pb = Vt(x0 + qsx, y0, 0.0)
                        gva = ((0, 1) if s == 0 else
                               (1, 1) if s == subdivch else
                               None)
                        gvb = (1, 0)
                    elif c3 == cr:
                        pa = Vt(x0, y0 + dyc * s, 0.0)
                        pb = Vt(x0 + qsx, y0 + qsy, 0.0)
                        gva = ((0, 0) if s == 0 else
                               (0, 1) if s == subdivch else
                               None)
                        gvb = (1, 1)
                    elif c4 == cr:
                        pa = Vt(x0 + qsx - dxc * s, y0, 0.0)
                        pb = Vt(x0, y0 + qsy, 0.0)
                        gva = ((1, 0) if s == 0 else
                               (0, 0) if s == subdivch else
                               None)
                        gvb = (0, 1)
                    intcurve.append((pa * ka + pb * kb, pa, pb, gva, gvb))

        return intcurve


    @staticmethod
    def _smooth_interface_curve (intcurve, closed, subdiv,
                                 tbslam, tbsmu, tbsiter):

        Pt = type(intcurve[0][0])

        mindf = 0.05 # minimum distance from segment start
        maxdf = 0.95 # maximum distance from segment start

        # NOTE: Taubin smoothing algorithm.
        for p in range(tbsiter):
            for scf in (tbslam, tbsmu):
                if scf == 0.0:
                    continue
                lenic = len(intcurve)

                ## Jacobi iteration.
                #intcurve1 = []
                #for k in xrange(lenic):
                    #pc, pa, pb = intcurve[k][:3]
                    #ptcs = []
                    #if 0 < k < lenic - 1 or closed:
                        #km = k - 1 if k > 0 else lenic - 1
                        #kp = k + 1 if k < lenic - 1 else 0
                        #pc1 = Pt(pc)
                        #ks = (km, kp)
                        #ws = (0.5, 0.5)
                        #for k1, w1 in zip(ks, ws):
                            #dp1 = intcurve[k1][0] - pc
                            #pc1 += dp1 * (w1 * scf)
                        #pc = pc1
                        ## Limit back to originating segment.
                        #ab = pb - pa
                        #mab = ab.length()
                        #abu = ab / mab
                        #ac = pc - pa
                        #acabu = ac.dot(abu)
                        #if acabu < mindf * mab:
                            #acabu = mindf * mab
                        #elif acabu > maxdf * mab:
                            #acabu = maxdf * mab
                        #pc = pa + abu * acabu
                    #intcurve1.append((pc, pa, pb) + intcurve[k][3:])
                #intcurve = intcurve1

                # Gauss iteration.
                for k in xrange(lenic):
                    pc, pa, pb = intcurve[k][:3]
                    ptcs = []
                    if 0 < k < lenic - 1 or closed:
                        km = k - 1 if k > 0 else lenic - 1
                        kp = k + 1 if k < lenic - 1 else 0
                        pc1 = Pt(pc)
                        ks = (km, kp)
                        ws = (0.5, 0.5)
                        for k1, w1 in zip(ks, ws):
                            dp1 = intcurve[k1][0] - pc
                            pc1 += dp1 * (w1 * scf)
                        # Limit back to originating segment.
                        ab = pb - pa
                        mab = ab.length()
                        abu = ab / mab
                        ac = pc1 - pa
                        acabu = ac.dot(abu)
                        if acabu < mindf * mab:
                            acabu = mindf * mab
                        elif acabu > maxdf * mab:
                            acabu = maxdf * mab
                        pc2 = pa + abu * acabu
                        pc.set(*pc2)

        #mind = 1e30
        #for p, pa, pb in intcurve:
            #mind = min(mind, (pc - pa).length(), (pc - pb).length())
        #print "--curve-mindist-ab", mind

        return intcurve


    @staticmethod
    def _level_curve_to_left (sizex, sizey, offsetx, offsety,
                              numquadsx, numquadsy,
                              verts, tris, quadmap,
                              cvinds, closed, lcut):

        Vt = Vec3D

        quadsizex = sizex / numquadsx
        quadsizey = sizey / numquadsy
        rhlen0 = 2 * sqrt(quadsizex**2 + quadsizey**2)
        dhrlen = 0.11 * rhlen0

        refpt = Vt(0.0, 0.0, 0.0)

        lenv = len(cvinds)
        vertxs, vertys, vertzs = verts
        for k in xrange(lenv):
            if not (0 < k < lenv - 1 or closed):
                continue
            km = k - 1 if k > 0 else lenv - 1
            kp = k + 1 if k < lenv - 1 else 0
            l = cvinds[k]; lm = cvinds[km]; lp = cvinds[kp]
            # Compute right-hand xy-projected normal at this vertex.
            v = Vt(vertxs[l], vertys[l], 0.0)
            vm = Vt(vertxs[lm], vertys[lm], 0.0)
            vp = Vt(vertxs[lp], vertys[lp], 0.0)
            dvm = v - vm; nm = Vt(-dvm[1], dvm[0], 0.0); lenm = dvm.length()
            dvp = vp - v; np = Vt(-dvp[1], dvp[0], 0.0); lenp = dvp.length()
            n = unitv((nm * lenp + np * lenm) / (lenm + lenp))
            # Take minimum height from a segment along the normal.
            rhlen = rhlen0
            zmin = None
            atvinds = []
            while rhlen > 0.0:
                ph = v + n * rhlen
                p, c, z, tvinds = TerrainGeom._interpolate_z(
                    sizex, sizey, offsetx, offsety, numquadsx, numquadsy,
                    verts, tris, quadmap, ph[0], ph[1], refpt,
                    wtvinds=True)
                if c == lcut:
                    atvinds.extend(tvinds)
                    if zmin is None or zmin > z:
                        zmin = z
                rhlen -= dhrlen
            if zmin is not None:
                vertzs[l] = zmin
                for la in atvinds:
                    vertzs[la] = zmin


    @staticmethod
    def _triangulate_interface_quads (cutmap,
                                      quadsizex, quadsizey, offsetx, offsety,
                                      intquadchain, intcurve, subdiv,
                                      nverts0, ntris0):

        numquadsx = len(cutmap) - 1
        numquadsy = len(cutmap[0]) - 1

        subdivc = subdiv if subdiv % 2 == 0 else subdiv + 1
        cl, cr = TerrainGeom._interface_cut_levels(cutmap, intquadchain)

        lenqc = len(intquadchain)
        lenic = len(intcurve)

        # Collect interface vertices, assign them indices.
        # Collect associated quad corner point coordinates.
        vertxs = []; vertys = []; vertzs = []
        verts = (vertxs, vertys, vertzs)
        vqvas = []
        vqvbs = []
        vinds = []
        nverts1 = nverts0
        kc = 0
        for kq in xrange(lenqc):
            (i, j), ncl = intquadchain[kq]
            sf = 0
            if kq == lenqc - 1 and kc + subdivc == lenic - 1: # open curve
                sf = 1
            for lc in range(subdivc + sf):
                kc1 = kc + lc
                p, a, b, qva, qvb = intcurve[kc1][:5]
                vertxs.append(p[0]); vertys.append(p[1]); vertzs.append(p[2])
                vqvas.append((i + qva[0], j + qva[1]) if qva else None)
                vqvbs.append((i + qvb[0], j + qvb[1]) if qvb else None)
                vinds.append(nverts1)
                nverts1 += 1
            kc += subdivc

        # Triangulate left and right of curve in each interface quad.
        tri1s = []; tri2s = []; tri3s = []; trics = []
        links = []
        ntris1 = ntris0
        kc = 0
        for kq in xrange(lenqc):
            (i, j), ncl = intquadchain[kq]

            # Collect interface vertex data in this quad.
            iqvdata1 = []
            for lc in range(subdivc + 1):
                kc1 = (kc + lc) % lenic
                xp = vertxs[kc1]
                yp = vertys[kc1]
                lp = vinds[kc1]
                iqvdata1.append((lp, xp, yp))

            # Order global offsets of quad corner points per side,
            # left-winding for left side, right-winding for right side.
            kc1 = kc
            kcm = kc + subdivc / 2
            kc2 = (kc + subdivc) % lenic
            if ncl == 1:
                gvels = [vqvas[kc1]]
                gvers = [vqvbs[kc2], vqvbs[kcm], vqvbs[kc1]]
            elif ncl == 2:
                gvels = [vqvas[kc2], vqvas[kc1]]
                gvers = [vqvbs[kc2], vqvbs[kc1]]
            elif ncl == 3:
                gvels = [vqvas[kc2], vqvas[kcm], vqvas[kc1]]
                gvers = [vqvbs[kc1]]
            else:
                raise StandardError("Impossible number of left cut points.")

            # Triangulate left and right.
            cntris = 0
            for side, gves, c in ((1, gvels, cl), (-1, gvers, cr)):
                # Collect quad corner vertex data on this side.
                iqvdata2 = []
                for ie, je in gves: # left winding for left side
                    xe = ie * quadsizex + offsetx
                    ye = je * quadsizey + offsety
                    le = ie * (numquadsy + 1) + je
                    iqvdata2.append((le, xe, ye))

                # Complete side polygon.
                iqvdata = iqvdata1 + iqvdata2
                if side == -1: # right polygon
                    iqvdata = list(reversed(iqvdata))

                # Triangulate the polygon and collect triangles.
                leniqvd = len(iqvdata)
                avgx = sum(iqvdata[lq][1] for lq in range(leniqvd)) / leniqvd
                avgy = sum(iqvdata[lq][2] for lq in range(leniqvd)) / leniqvd
                tgl = Triangulator()
                showdat = False
                for lq, (l, x, y) in enumerate(iqvdata):
                    #if l == 1061963:
                        #showdat = True
                    # Subtract average coordinates to have numbers
                    # as small as possible to avoid roundoff problems.
                    lqt = tgl.addVertex(x - avgx, y - avgy)
                    if lq != lqt:
                        raise StandardError(
                            "Unexpected behavior of the triangulator, "
                            "changed indices (quad %d, %d)." % (i, j))
                    tgl.addPolygonVertex(lqt) # Wtf?
                if not tgl.isLeftWinding():
                    raise StandardError(
                        "Unexpected behavior of the triangulator, "
                        "changed winding (quad %d, %d)." % (i, j))
                tgl.triangulate()
                nqstris = tgl.getNumTriangles()
                for t in range(nqstris):
                    lq1 = tgl.getTriangleV0(t)
                    lq2 = tgl.getTriangleV1(t)
                    lq3 = tgl.getTriangleV2(t)
                    tri1s.append(iqvdata[lq1][0])
                    tri2s.append(iqvdata[lq2][0])
                    tri3s.append(iqvdata[lq3][0])
                    trics.append(c)
                    #if showdat:
                        #print "--side-polygon-vertex", iqvdata[lq1][0], iqvdata[lq2][0], iqvdata[lq3][0]
                cntris += nqstris

            kc += subdivc
            links.append(((i, j), (ntris1, ntris1 + cntris)))
            ntris1 += cntris
        tris = (tri1s, tri2s, tri3s, trics)

        return verts, tris, links


    # Forward left point direction for quad-to-quad direction.
    _dij_ptfwlf = {
        (1, 0): (1, 1),
        (0, 1): (0, 1),
        (-1, 0): (0, 0),
        (0, -1): (1, 0),
    }

    # Forward right point direction for quad-to-quad direction.
    _dij_ptfwrg = {
        (1, 0): (1, 0),
        (0, 1): (1, 1),
        (-1, 0): (0, 1),
        (0, -1): (0, 0),
    }

    @staticmethod
    def _interface_cut_levels (cutmap, intquadchain):

        i1, j1 = intquadchain[0][0]
        if len(intquadchain) > 1:
            i2, j2 = intquadchain[1][0]
        else: # the single quad must be in corner
            if i1 == 0:
                if j1 == 0: # bottom left
                    i2 = i1 - 1; j2 = j1
                else: # top left
                    i2 = i1; j2 = j1 + 1
            else:
                if j1 == 0: # bottom right
                    i2 = i1; j2 = j1 - 1
                else: # top right
                    i2 = i1 + 1; j2 = j1
        dil, djl = TerrainGeom._dij_ptfwlf[(i2 - i1, j2 - j1)]
        cl = cutmap[i1 + dil][j1 + djl]
        dir, djr = TerrainGeom._dij_ptfwrg[(i2 - i1, j2 - j1)]
        cr = cutmap[i1 + dir][j1 + djr]

        return cl, cr


    @staticmethod
    def _make_tiles (offsetx, offsety, numquadsx, numquadsy,
                     numtilesx, numtilesy, tilesizex, tilesizey,
                     numtilequadsx, numtilequadsy,
                     gvformat,
                     verts, tris, quadmap, levints,
                     cut):

        Vt = Vec3D

        vertxs, vertys, vertzs = verts
        nverts = len(vertxs)

        # Compute vertex normals and tangents,
        # as area-weighted averages of adjoining triangles.
        # Loop over triangles, adding contributions to their vertices.
        tri1s, tri2s, tri3s, trics = tris
        vareas = array("d", [0.0] * nverts)
        vnormxs = array("d", [0.0] * nverts)
        vnormys = array("d", [0.0] * nverts)
        vnormzs = array("d", [0.0] * nverts)
        vnorms = (vnormxs, vnormys, vnormzs)
        vtangxs = array("d", [0.0] * nverts)
        vtangys = array("d", [0.0] * nverts)
        vtangzs = array("d", [0.0] * nverts)
        vtangs = (vtangxs, vtangys, vtangzs)
        #zdir = Vt(0.0, 0.0, 1.0)
        xdir = Vt(1.0, 0.0, 0.0)
        for k in xrange(len(tri1s)):
            c = trics[k]
            if c != cut and (levints[cut] or levints[c]):
                continue
            l1, l2, l3 = tri1s[k], tri2s[k], tri3s[k]
            v1 = Vt(vertxs[l1], vertys[l1], vertzs[l1])
            v2 = Vt(vertxs[l2], vertys[l2], vertzs[l2])
            v3 = Vt(vertxs[l3], vertys[l3], vertzs[l3])
            v12, v13 = v2 - v1, v3 - v1
            tnorm = v12.cross(v13)
            tarea = 0.5 * tnorm.length()
            tnorm.normalize()
            #ttang = tnorm.cross(zdir).cross(tnorm) # steepest ascent (gradient)
            ttang = tnorm.cross(xdir).cross(tnorm)
            ttang.normalize()
            for l in (l1, l2, l3):
                vareas[l] += tarea
                vn = tnorm * tarea
                vnormxs[l] += vn[0]; vnormys[l] += vn[1]; vnormzs[l] += vn[2]
                vt = ttang * tarea
                vtangxs[l] += vt[0]; vtangys[l] += vt[1]; vtangzs[l] += vt[2]
        for l in xrange(nverts):
            va = vareas[l]
            if va == 0.0:
                # May happen if the vertex does not belong to this cut,
                # or triangulation left some hanging vertices.
                #print "--zero-area-vertex", l, vertxs[l], vertys[l], vertzs[l]
                continue
            vn = Vt(vnormxs[l], vnormys[l], vnormzs[l])
            vn /= va
            vn.normalize()
            vnormxs[l] = vn[0]; vnormys[l] = vn[1]; vnormzs[l] = vn[2]
            vt = Vt(vtangxs[l], vtangys[l], vtangzs[l])
            vt /= va
            vt.normalize()
            vtangxs[l] = vt[0]; vtangys[l] = vt[1]; vtangzs[l] = vt[2]

        # Construct tiles.
        tiles = []
        tilevertmap = array("l", [0] * nverts) # for use inside _make_tile()
        for it in range(numtilesx):
            tiles1 = []
            xt = (it + 0.5) * tilesizex + offsetx
            for jt in range(numtilesy):
                yt = (jt + 0.5) * tilesizey + offsety
                tile = TerrainGeom._make_tile(
                    offsetx, offsety,
                    numtilesx, numtilesy, tilesizex, tilesizey,
                    numquadsx, numquadsy, numtilequadsx, numtilequadsy,
                    verts, vnorms, vtangs, tris, quadmap, tilevertmap,
                    gvformat,
                    cut, it, jt, xt, yt)
                tiles1.append((tile, xt, yt))
            tiles.append(tiles1)

        return tiles


    @staticmethod
    def _make_tile (offsetx, offsety,
                    numtilesx, numtilesy, tilesizex, tilesizey,
                    numquadsx, numquadsy, numtilequadsx, numtilequadsy,
                    verts, vnorms, vtangs, tris, quadmap, tilevertmap,
                    gvformat,
                    cut, it, jt, xt, yt):

        Vt = Vec3D

        i0 = it * numtilequadsx
        j0 = jt * numtilequadsy

        tname = "tile-i%d-j%d-c%d" % (it, jt, cut)

        # Link global vertex and triangle indices to indices for this tile.
        tilevinds = []
        tiletinds = []
        tri1s, tri2s, tri3s, trics = tris
        qm1, qm2 = quadmap
        for i in xrange(i0, i0 + numtilequadsx):
            for j in xrange(j0, j0 + numtilequadsy):
                q = i * numquadsy + j
                ks = range(qm1[q], qm2[q])
                for k in ks:
                    #tri, c = tris[k]
                    tri = (tri1s[k], tri2s[k], tri3s[k])
                    c = trics[k]
                    if c == cut:
                        tilevinds.extend(tri)
                        tiletinds.append(k)
        if not tilevinds:
            # There is nothing from this cut on this tile.
            return NodePath(tname)
        tilevinds = sorted(set(tilevinds))
        nvinds = len(tilevinds)
        ntinds = len(tiletinds)
        for lt, l in enumerate(tilevinds):
            tilevertmap[l] = lt

        # Compute texture coordinates.
        vertxs, vertys, vertzs = verts
        texcs = []
        x0 = offsetx
        y0 = offsety
        sx = tilesizex * numtilesx
        sy = tilesizey * numtilesy
        for l in tilevinds:
            x, y = vertxs[l], vertys[l]
            u = clamp((x - x0) / sx, 0.0, 1.0)
            v = clamp((y - y0) / sy, 0.0, 1.0)
            texcs.append((u, v))

        # Construct graphics vertices.
        gvdata = GeomVertexData("data", gvformat, Geom.UHStatic)
        gvdata.uncleanSetNumRows(nvinds)
        gvwvertex = GeomVertexWriter(gvdata, InternalName.getVertex())
        gvwnormal = GeomVertexWriter(gvdata, InternalName.getNormal())
        gvwtangent = GeomVertexWriter(gvdata, InternalName.getTangent())
        gvwbinormal = GeomVertexWriter(gvdata, InternalName.getBinormal())
        gvwcolor = GeomVertexWriter(gvdata, InternalName.getColor())
        gvwtexcoord = GeomVertexWriter(gvdata, InternalName.getTexcoord())
        vnormxs, vnormys, vnormzs = vnorms
        vtangxs, vtangys, vtangzs = vtangs
        for l in tilevinds:
            lt = tilevertmap[l]
            gvwvertex.addData3f(vertxs[l] - xt, vertys[l] - yt, vertzs[l])
            gvwnormal.addData3f(vnormxs[l], vnormys[l], vnormzs[l])
            gvwtangent.addData3f(vtangxs[l], vtangys[l], vtangzs[l])
            vn = Vt(vnormxs[l], vnormys[l], vnormzs[l])
            vt = Vt(vtangxs[l], vtangys[l], vtangzs[l])
            vb = vn.cross(vt)
            vb.normalize()
            gvwbinormal.addData3f(*vb)
            gvwcolor.addData4f(1.0, 1.0, 1.0, 1.0)
            u, v = texcs[lt]
            gvwtexcoord.addData2f(u, v)

        # Construct graphics triangles.
        gtris = GeomTriangles(Geom.UHStatic)
        # Default index column type is NTUint16, and add_vertices()
        # would change it automatically if needed. Since it is not used,
        # change manually.
        if nvinds >= 1 << 16:
            gtris.setIndexType(Geom.NTUint32)
        gvdtris = gtris.modifyVertices()
        gvdtris.uncleanSetNumRows(ntinds * 3)
        gvwtris = GeomVertexWriter(gvdtris, 0)
        tri1s, tri2s, tri3s = tris[:3]
        for k in tiletinds:
            l1, l2, l3 = (tri1s[k], tri2s[k], tri3s[k])
            lt1, lt2, lt3 = tilevertmap[l1], tilevertmap[l2], tilevertmap[l3]
            #gtris.addVertices(lt1, lt2, lt3)
            gvwtris.addData1i(lt1)
            gvwtris.addData1i(lt2)
            gvwtris.addData1i(lt3)
            #gtris.closePrimitive()

        # Construct tile skirt.
        if True:
            #print "------tile-skirt  it=%d  jt=%d  cut=%d" % (it, jt, cut)
            xb0 = it * tilesizex + offsetx
            yb0 = jt * tilesizey + offsety
            xb1 = (it + 1) * tilesizex + offsetx
            yb1 = (jt + 1) * tilesizey + offsety
            quadsizex = tilesizex / numtilequadsx
            quadsizey = tilesizey / numtilequadsy
            incang = radians(10.0)
            incrlen = 0.1
            incvz = Vec3D(0, 0, -((quadsizex + quadsizey) * 0.5) * incrlen)
            epsx = quadsizex * 1e-5
            epsy = quadsizey * 1e-5
            ltc = len(tilevinds)
            for ku, ue, epsu, ijs in (
                (0, xb0, epsx,
                 zip([i0] * numtilequadsy,
                     range(j0, j0 + numtilequadsy))),
                (0, xb1, epsx,
                 zip([i0 + numtilequadsx - 1] * numtilequadsy,
                     range(j0, j0 + numtilequadsy))),
                (1, yb0, epsy,
                 zip(range(i0, i0 + numtilequadsx),
                     [j0] * numtilequadsx)),
                (1, yb1, epsy,
                 zip(range(i0, i0 + numtilequadsx),
                     [j0 + numtilequadsy - 1] * numtilequadsx)),
            ):
                #print "----tile-skirt  ku=%d  ue=%.1f" % (ku, ue)
                rot = QuatD()
                vertus = verts[ku]
                ez = Vec3D(0.0, 0.0, 1.0)
                for i, j in ijs:
                    q = i * numquadsy + j
                    ks = range(qm1[q], qm2[q])
                    for k in ks:
                        c = trics[k]
                        if c == cut:
                            l1, l2, l3 = tri1s[k], tri2s[k], tri3s[k]
                            u1, u2, u3 = vertus[l1], vertus[l2], vertus[l3]
                            la, lb = None, None
                            if abs(u1 - ue) < epsu and abs(u2 - ue) < epsu:
                                la = l1; lb = l2
                            elif abs(u2 - ue) < epsu and abs(u3 - ue) < epsu:
                                la = l2; lb = l3
                            elif abs(u3 - ue) < epsu and abs(u1 - ue) < epsu:
                                la = l3; lb = l1
                            if la is not None:
                                # Compute lower skirt points.
                                xa, ya, za = vertxs[la], vertys[la], vertzs[la]
                                xb, yb, zb = vertxs[lb], vertys[lb], vertzs[lb]
                                #print ("--tile-skirt  "
                                       #"xa=%.1f  ya=%.1f  xb=%.1f  yb=%.1f" %
                                       #(xa, ya, xb, yb))
                                pa = Point3D(xa, ya, 0.0)
                                pb = Point3D(xb, yb, 0.0)
                                ra = unitv(pa - pb)
                                rot.setFromAxisAngleRad(incang, ra)
                                incv = Point3D(rot.xform(incvz))
                                pc = pa + incv
                                pd = pb + incv
                                pa[2] += za; pc[2] += za
                                pb[2] += zb; pd[2] += zb
                                xc, yc, zc = pc[0], pc[1], pc[2]
                                xd, yd, zd = pd[0], pd[1], pd[2]
                                lta, ltb = tilevertmap[la], tilevertmap[lb]
                                # Add vertices.
                                #vnc = unitv((pa - pb).cross(pc - pb))
                                #vnd = unitv((pc - pb).cross(pd - pb))
                                vnc = Vec3D(vnormxs[la], vnormys[la], vnormzs[la])
                                vnd = Vec3D(vnormxs[lb], vnormys[lb], vnormzs[lb])
                                for p, vn in ((pc, vnc), (pd, vnd)):
                                    vt = vn.cross(ez).cross(vt) # steepest ascent
                                    vb = vn.cross(vt)
                                    gvwvertex.addData3f(p[0] - xt, p[1] - yt, p[2])
                                    gvwnormal.addData3f(vn[0], vn[1], vn[2])
                                    gvwtangent.addData3f(vt[0], vt[1], vt[2])
                                    gvwbinormal.addData3f(vb[0], vb[1], vb[2])
                                    gvwcolor.addData4f(1.0, 1.0, 1.0, 1.0)
                                    x, y = p[0], p[1]
                                    u = clamp((x - x0) / sx, 0.0, 1.0)
                                    v = clamp((y - y0) / sy, 0.0, 1.0)
                                    gvwtexcoord.addData2f(u, v)
                                # Add triangles.
                                ltd = ltc + 1
                                #gtris.addVertices(ltb, lta, ltc)
                                gvwtris.addData1i(ltb)
                                gvwtris.addData1i(lta)
                                gvwtris.addData1i(ltc)
                                #gtris.closePrimitive()
                                #gtris.addVertices(ltb, ltc, ltd)
                                gvwtris.addData1i(ltb)
                                gvwtris.addData1i(ltc)
                                gvwtris.addData1i(ltd)
                                #gtris.closePrimitive()
                                ltc += 2

        # Construct the mesh.
        geom = Geom(gvdata)
        geom.addPrimitive(gtris)
        gnode = GeomNode(tname)
        gnode.addGeom(geom)
        node = NodePath(gnode)
        #node.flattenStrong()

        return node


    @staticmethod
    def _quad_index_for_xy (sizex, sizey, offsetx, offsety,
                            numquadsx, numquadsy, x, y):

        dx = sizex / numquadsx
        dy = sizey / numquadsy
        i = int((x - offsetx) / dx)
        j = int((y - offsety) / dy)
        if 0 <= i < numquadsx and 0 <= j < numquadsy:
            return i * numquadsy + j
        else:
            return None


    @staticmethod
    def _interpolate_z (sizex, sizey, offsetx, offsety,
                        numquadsx, numquadsy,
                        verts, tris, quadmap,
                        x1, y1, ref1, wnorm=False, wtvinds=False):

        xr1, yr1, zr1 = ref1[0], ref1[1], ref1[2]
        x, y = x1 - xr1, y1 - yr1

        q = TerrainGeom._quad_index_for_xy(sizex, sizey, offsetx, offsety,
                                           numquadsx, numquadsy,
                                           x, y)
        if q is None:
            ret = [1.0, -1, 0.0]
            if wnorm:
                ret.append(Vec3())
            if wtvinds:
                ret.append(())
            return ret
        qm1, qm2 = quadmap
        ks = range(qm1[q], qm2[q])
        trics = tris[3]
        pmin = None
        cpmin = None
        zpmin = None
        if wnorm:
            npmin = None
        if wtvinds:
            tvindspmin = None
        for k in ks:
            ret = TerrainGeom._interpolate_tri_z(verts, tris, k, x, y,
                                                 wnorm=wnorm, wtvinds=wtvinds)
            p, z = ret.pop(0), ret.pop(0)
            if wnorm:
                n = ret.pop(0)
            if wtvinds:
                tvinds = ret.pop(0)
            if pmin is None or pmin > p:
                pmin = p
                cpmin = trics[k]
                zpmin = z
                if wnorm:
                    npmin = n
                if wtvinds:
                    tvindspmin = tvinds
            if p == 0.0:
                break
        z1pmin = zpmin + zr1

        ret = [pmin, cpmin, z1pmin]
        if wnorm:
            ret.append(npmin)
        if wtvinds:
            ret.append(tvindspmin)
        return ret


    @staticmethod
    def _interpolate_tri_z (verts, tris, k, x, y,
                            wnorm=False, wtvinds=False):

        Pt2 = Point2D

        pf = Pt2(x, y)
        tri1s, tri2s, tri3s = tris[:3]
        tri = (tri1s[k], tri2s[k], tri3s[k])
        v1, v2, v3 = TerrainGeom._get_tri_verts(tri, verts)
        v1f, v2f, v3f = v1.getXy(), v2.getXy(), v3.getXy()

        v12f = v2f - v1f
        v13f = v3f - v1f
        v1pf = pf - v1f
        d1212 = v12f.dot(v12f)
        d1213 = v12f.dot(v13f)
        d1313 = v13f.dot(v13f)
        den = d1313 * d1212 - d1213 * d1213
        if den == 0.0: # can happen due to roundoff
            ret = [1.0, v1[2]]
            if wnorm:
                ret.append(Vec3D(0, 0, 1))
            if wtvinds:
                ret.append(tri)
            return ret
        d131p = v13f.dot(v1pf)
        d121p = v12f.dot(v1pf)
        b2 = (d1313 * d121p - d1213 * d131p) / den
        b3 = (d1212 * d131p - d1213 * d121p) / den
        b1 = 1.0 - (b2 + b3)

        p = 0.0 # outsideness penalty
        for b in (b1, b2, b3):
            if b < 0.0:
                p += b**2
            elif b > 1.0:
                p += (b - 1.0)**2

        z1, z2, z3 = v1[2], v2[2], v3[2]
        z = b1 * z1 + b2 * z2 + b3 * z3
        if wnorm:
            n = unitv((v2 - v1).cross(v3 - v1))

        ret = [p, z]
        if wnorm:
            ret.append(n)
        if wtvinds:
            ret.append(tri)
        return ret
# @cache-key-end: terrain-generation


    def heightmap_size (self):

        return Vec3D(self._maxsizexa, self._maxsizexb, self._maxsizey)


    def to_unit_trap (self, maxsizexa, maxsizexb, maxsizey, x, y):

        return TerrainGeom._to_unit_trap(
            self._sizex, self._sizey, self._offsetx, self._offsety,
            maxsizexa, maxsizexb, maxsizey,
            self._centerx, self._centery,
            x, y)


    def quad_index_for_xy (self, x, y):

        q = TerrainGeom._quad_index_for_xy(
            self._sizex, self._sizey, self._offsetx, self._offsety,
            self._numquadsx, self._numquadsy,
            x, y)
        if q is None:
            q = -1
        return q


    def interpolate_z (self, x1, y1, ref1,
                       pcz,
                       norm=None, wnorm=False,
                       tvinds=None, wtvinds=False):

        ret = TerrainGeom._interpolate_z(
            self._sizex, self._sizey, self._offsetx, self._offsety,
            self._numquadsx, self._numquadsy,
            self._verts, self._tris, self._quadmap,
            x1, y1, ref1, wnorm, wtvinds)
        pcz[0], pcz[1], pcz[2] = ret.pop(0), ret.pop(0), ret.pop(0)
        if wnorm:
            norm[0], norm[1], norm[2] = ret.pop(0)
        if wtvinds:
            tvinds[0], tvinds[1], tvinds[2] = ret.pop(0)


if USE_COMPILED:
    from terrain_c import *
