# -*- coding: UTF-8 -*-

import cPickle as pickle
from hashlib import md5
import locale
from math import radians, degrees, sqrt
from math import pi, sin, cos, tan, asin, acos, atan, atan2
import os
import re
import sys
from time import time

from direct.directtools.DirectGeometry import LineNodePath
from direct.particles.Particles import Particles
from pandac.PandaModules import VBase2, VBase2D, VBase3, VBase3D, VBase4, VBase4D
from pandac.PandaModules import Vec3, Vec3D, Vec4, Point3, Point3D
from pandac.PandaModules import Quat, QuatD
from pandac.PandaModules import NodePath, TextNode, LODNode
from pandac.PandaModules import InternalName, GeomVertexData, GeomVertexWriter
from pandac.PandaModules import GeomVertexArrayFormat, GeomVertexFormat
from pandac.PandaModules import Geom, GeomNode, GeomTriangles
from pandac.PandaModules import Texture, TextureStage
from pandac.PandaModules import AudioManager, AudioSound
from pandac.PandaModules import TransparencyAttrib, RigidBodyCombiner

from src import path_exists, real_path, path_dirname
from src import UI_TEXT_ENC, pycv, USE_COMPILED
from src.core.transl import *


_vbase_cls = (VBase2, VBase2D, VBase3, VBase3D, VBase4, VBase4D)

_log_fh = None
_log_enc = "utf8"
_log_t0 = None
_log_num_prev = 9 # cannot be on base, as it is created after logs

def _init_log ():

    global _log_fh
    if _log_fh is not None:
        return

    log_path = rotate_logs("log", "txt")

    if not os.path.isdir(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path))
    _log_fh = open(log_path, "w")

    # Set initial time for timestamps.
    global _log_t0
    _log_t0 = time()


def _write_to_log (msg):

    _init_log()
    dt = time() - _log_t0
    lmsg = "[%8.2f] %s" % (dt, msg)
    _log_fh.write(lmsg.encode(_log_enc, "replace"))


def prev_logs_count ():

    return 


def rotate_logs (name, ext):

    maxprev = _log_num_prev
    zero_log_path = real_path("log", "%s.%s" % (name, ext))
    if maxprev > 0:
        for n in range(maxprev - 1, -1, -1):
            if n == 0:
                log_path = zero_log_path
            else:
                log_path = real_path("log", "%s.%s.%s" % (name, n, ext))
            prev_log_path = real_path("log", "%s.%s.%s" % (name, n + 1, ext))
            if os.path.exists(prev_log_path):
                os.remove(prev_log_path)
            if os.path.exists(log_path):
                os.rename(log_path, prev_log_path)
    else:
        log_path = zero_log_path
    return log_path


_std_streams_functional = None
_std_streams_enc = None

def _init_streams ():

    global _std_streams_functional
    if _std_streams_functional is not None:
        return
    try:
        sys.stdout.write(" \r")
        sys.stderr.write(" \r")
    except:
        _std_streams_functional = False
    else:
        _std_streams_functional = True
        global _std_streams_enc
        if os.name == "posix":
            _std_streams_enc = locale.getpreferredencoding()
        else:
            # On non-POSIX system, expect the standard output
            # to be to a UTF-8 terminal or redirected to a file.
            _std_streams_enc = "utf8"


def _write_to_stdout (msg):

    _init_streams()
    if _std_streams_functional:
        sys.stdout.write(msg.encode(_std_streams_enc, "replace"))


def _write_to_stderr (msg):

    _init_streams()
    if _std_streams_functional:
        sys.stderr.write(msg.encode(_std_streams_enc, "replace"))


def debug (lv, msg):

    if lv == 0 or lv <= base.gameconf.debug.output_level:
        fmsg = _("DBG: %s\n") % msg
        _write_to_stdout(fmsg)
        _write_to_log(fmsg)


def report (msg, noind=False):

    if noind:
        fmsg = _("%s\n") % msg
    else:
        fmsg = _("INFO: %s\n") % msg
    _write_to_stdout(fmsg)
    _write_to_log(fmsg)


def warning (msg):

    fmsg = _("WARN: %s\n") % msg
    _write_to_stderr(fmsg)
    _write_to_log(fmsg)


def error (msg):

    fmsg = _("ERROR: %s\n") % msg
    _write_to_stderr(fmsg)
    _write_to_log(fmsg)
    exit(1)


def dbgval (lv, hdr, *vspec):

    vfmts = []
    for vs in vspec:
        if not isinstance(vs, tuple):
            vs = (vs,)
        vs = list(vs)
        v = vs.pop(0)
        f = vs.pop(0) if vs else "%s"
        n = vs.pop(0) if vs else None
        u = vs.pop(0) if vs else None
        if not f.startswith("%"):
            f = "%" + f
        if isinstance(v, (tuple, list)) or isinstance(v, _vbase_cls):
            vfmt = "(%s)" % (", ".join(f % x for x in v))
        else:
            vfmt = f % v
        if n is not None:
            vfmt = "%s=%s" % (n, vfmt)
        if u is not None:
            vfmt = "%s[%s]" % (vfmt, u)
        vfmts.append(vfmt)
    msg = "%s:  %s" % (hdr, "  ".join(vfmts))
    debug(lv, msg)


def noop1 (x):

    return x


def rgb (r, g, b):

    return Vec3(r / 255.0, g / 255.0, b / 255.0)


def rgba (r, g, b, a):

    return Vec4(r / 255.0, g / 255.0, b / 255.0, a)


class _IterTaskState (object):
    pass


_itertask_store = {} # to avoid premature garbage collection of closure

def itertask (taskfunc):
    """
    Decorator for creating iterative task functions.

    Sometime it is convenient for a task function to be an iteration with
    points of explicit return and continuation of flow,
    instead of a callback that always executes from start and returns
    task.cont/task.done.
    This decorator allows writing such functions, where flow is returned
    and continued at yield statements.
    Yielding with no parameter (i.e. None) means to continue flow
    in the next frame, while yielding a number means to continue flow
    after that many seconds have passed.
    Task function must be defined to accept the task object as
    the last non-keyword parameter.

    For example, the following task function will print the given message
    at every given period (in seconds), for the given duration of time:

        @itertask
        def periodic_message (message, period, duration, task):
            while task.time < duration:
                report(message)
                yield period

        base.taskMgr.add(periodic_message, "knock-knock",
                         extraArgs=["Knock, knock!", 1.0, 10.0],
                         acceptTask=True)

    FIXME: Document two-parameter yield, with custom timer as first argument.
    """

    state = _IterTaskState()
    state.generator = None
    state.sleepfrom = None

    def taskfunc_mod (*args, **kwargs):

        task = args[-1]
        if state.generator is None:
            state.generator = taskfunc(*args, **kwargs)
            if state.generator is None:
                _itertask_store.pop(taskfunc_mod)
                return task.done

        if state.sleepfrom is None:
            try:
                ret = state.generator.next()
                if ret is None:
                    ret = (None, None, -1)
                elif isinstance(ret, (int, float)):
                    ret = (None, ret, 0)
                elif isinstance(ret, tuple) and len(ret) == 2:
                    ret = (ret[0], ret[1], 0)
                timer, duration, sleeptype = ret
                if timer is None:
                    timer = task
                state.sleeptype = sleeptype
                if state.sleeptype == -1:
                    pass
                elif state.sleeptype == 0:
                    state.sleepfrom = timer.time
                    state.sleeptime = duration
                elif state.sleeptype == 1:
                    state.sleepfrom = timer.frame
                    state.sleepframes = duration
                state.timer = timer
            except StopIteration:
                _itertask_store.pop(taskfunc_mod)
                return task.done
            return task.cont
        else:
            if state.sleeptype == 0:
                if state.timer.time - state.sleepfrom >= state.sleeptime:
                    state.sleepfrom = None
            elif state.sleeptype == 1:
                if state.timer.frame - state.sleepfrom >= state.sleepframes:
                    state.sleepfrom = None
            return task.cont

    _itertask_store[taskfunc_mod] = (taskfunc, state)
    return taskfunc_mod


_textfmts = {}

def texfmt_tangspace ():

    texfmt = _textfmts.get("tangspace")
    if texfmt is not None:
        return texfmt

    array = GeomVertexArrayFormat()
    array.addColumn(InternalName.getVertex(), 3,
                    Geom.NTFloat32, Geom.CPoint)
    array.addColumn(InternalName.getNormal(), 3,
                    Geom.NTFloat32, Geom.CVector)
    array.addColumn(InternalName.getTangent(), 3,
                    Geom.NTFloat32, Geom.CVector)
    array.addColumn(InternalName.getBinormal(), 3,
                    Geom.NTFloat32, Geom.CVector)
    array.addColumn(InternalName.getColor(), 4,
                    Geom.NTFloat32, Geom.CColor)
    array.addColumn(InternalName.getTexcoord(), 2,
                    Geom.NTFloat32, Geom.CTexcoord)
    texfmt = GeomVertexFormat()
    texfmt.addArray(array)
    texfmt = GeomVertexFormat.registerFormat(texfmt)

    _textfmts["tangspace"] = texfmt
    return texfmt


def texfmt_flatspace ():

    texfmt = _textfmts.get("flatspace")
    if texfmt is not None:
        return texfmt

    array = GeomVertexArrayFormat()
    array.addColumn(InternalName.getVertex(), 3,
                    Geom.NTFloat32, Geom.CPoint)
    array.addColumn(InternalName.getColor(), 4,
                    Geom.NTFloat32, Geom.CColor)
    array.addColumn(InternalName.getTexcoord(), 2,
                    Geom.NTFloat32, Geom.CTexcoord)
    texfmt = GeomVertexFormat()
    texfmt.addArray(array)
    texfmt = GeomVertexFormat.registerFormat(texfmt)

    _textfmts["flatspace"] = texfmt
    return texfmt


texstage_color = TextureStage("color")
#texstage_color.setMode(TextureStage.MReplace)
texstage_color.setMode(TextureStage.MModulate)

texstage_normal = TextureStage("normal")
texstage_normal.setMode(TextureStage.MNormal)

texstage_glow = TextureStage("glow")
texstage_glow.setMode(TextureStage.MGlow)

texstage_gloss = TextureStage("gloss")
texstage_gloss.setMode(TextureStage.MGloss)

texstage_shadow = TextureStage("shadow")
texstage_shadow.setMode(TextureStage.MSelector) # to put something


def set_texture (node, texture=None, normalmap=None, glowmap=None,
                 glossmap=None, shadowmap=None, extras=[],
                 clamp=True, filtr=True):

    if filtr:
        texfilter = Texture.FTLinearMipmapLinear
    else:
        texfilter = Texture.FTLinear

    if texture is not None:
        node.clearTexture(texstage_color)
        if texture != -1:
            if isinstance(texture, tuple):
                texture = base.load_texture("data", *texture)
            elif isinstance(texture, basestring):
                texture = base.load_texture("data", texture)
            texture.setMinfilter(texfilter)
            texture.setMagfilter(texfilter)
            if clamp:
                texture.setWrapU(Texture.WMClamp)
                texture.setWrapV(Texture.WMClamp)
            else:
                texture.setWrapU(Texture.WMRepeat)
                texture.setWrapV(Texture.WMRepeat)
            node.setTexture(texstage_color, texture)
    if normalmap is not None:
        node.clearTexture(texstage_normal)
        if normalmap != -1:
            if isinstance(normalmap, basestring):
                normalmap = base.load_texture("data", normalmap)
            normalmap.setMinfilter(texfilter)
            normalmap.setMagfilter(texfilter)
            node.setTexture(texstage_normal, normalmap)
    if glowmap is not None:
        node.clearTexture(texstage_glow)
        if glowmap != -1:
            if isinstance(glowmap, basestring):
                glowmap = base.load_texture("data", glowmap)
            glowmap.setMinfilter(texfilter)
            glowmap.setMagfilter(texfilter)
            node.setTexture(texstage_glow, glowmap)
    if glossmap is not None:
        node.clearTexture(texstage_gloss)
        if glossmap != -1:
            if isinstance(glossmap, basestring):
                glossmap = base.load_texture("data", glossmap)
            glossmap.setMinfilter(texfilter)
            glossmap.setMagfilter(texfilter)
            node.setTexture(texstage_gloss, glossmap)
    if shadowmap is not None:
        node.clearTexture(texstage_shadow)
        if shadowmap != -1:
            if isinstance(shadowmap, basestring):
                shadowmap = base.load_texture("data", shadowmap)
            # Do not set wrap, do not set filters.
            node.setTexture(texstage_shadow, shadowmap)
    for extra in extras:
        if len(extra) == 2:
            texstage1, texture1 = extra
            clamp1 = clamp
            texfilter1 = texfilter
        elif len(extra) == 3:
            texstage1, texture1, clamp1 = extra
            texfilter1 = texfilter
        else:
            texstage1, texture1, clamp1, texfilter1 = extra
        node.clearTexture(texstage1)
        if texture1 != -1:
            if isinstance(texture1, basestring):
                texture1 = base.load_texture("data", texture1)
            if texfilter1:
                texture1.setMinfilter(texfilter1)
                texture1.setMagfilter(texfilter1)
            if clamp1:
                texture1.setWrapU(Texture.WMClamp)
                texture1.setWrapV(Texture.WMClamp)
            node.setTexture(texstage1, texture1)


def set_hpr_vfu (node, vf, vu):

    pnode = node.getParent()
    pos = node.getPos()
    node.setPos(Point3())
    node.lookAt(pnode, Point3(vf), Vec3(vu))
    node.setPos(pos)


#ui_font_path = "fonts/red-october-regular.otf"
#ui_font_path = "fonts/DejaVuSans-Bold.ttf"
ui_font_path = "fonts/Russo.ttf"

_black_text = rgba(0, 0, 0, 1.0)

def make_text (text="", width=1.0, pos=Point3(), font=None, size=10,
               ppunit=30, lheight=None,
               color=(1.0, 1.0, 1.0, 1.0), shcolor=None,
               olcolor=None, olwidth=1.0, olfeather=0.0,
               align="l", anchor="mc", wrap=True,
               smallcaps=False, underscore=False,
               background=None, shader=None,
               parent=None):
    """
    Show a piece of 2D text on the screen.

    Parameters:
    - text (string): the text to show.
    - width (float): width of the text, relative to parent
    - pos (Point3|Point2): position of the text, relative to parent;
        if Point2, it is taken as x and z coordinate with y zero.
    - font (TextFont or string): font for the text
    - ppunit (flaot): pixels per point when rendering font.
    - lheight (float): font line height in units.
    - size (float): size of the font in points, relative to 120 dpi screen.
    - color ((float)*4): RGBA color of the text.
    - shcolor ((float)*4): RGBA color of the text shadow;
        shadow not displayed if not given.
    - olcolor ((float)*4): RGBA color of the text outline;
        no outline if not given.
    - olwidth (float): width of the text outline in points.
    - olfeather (float): softness of the outline, 0.0 sharp, 1.0 soft.
    - align (string): alignment of text; single character, l (left),
        c (center) or r (right).
    - anchor (string): the anchor point of text, to which the position
        is related; composed of two characters, one is t (top), m (middle),
        or b (bottom), the other l (left), c (center), or r (right).
    - wrap (bool): whether to wrap the text.
    - smallcaps (bool): whether to type set font in small caps.
    - underscore (bool): whether to underscore the text.
    - background ((string, float, Point3) or [(string, float, Point3)*]):
        the background image, or several of them.
        Each tuple is the image path, size, and its position relative
        to the anchor point.
    - shader (Shader): the shader to set on the text node.
    - parent (NodePath): where to attach the resulting node.
    Returns:
    - text node (NodePath)
    """

    if not font:
        font = ui_font_path
    if isinstance(font, basestring):
        if olcolor is not None and olcolor != _black_text:
            fgcolor = color
            color = None
        else:
            fgcolor = None
        font = base.load_font(category="data", font_path=font,
                              pixels_per_unit=ppunit,
                              line_height=lheight, fg_color=fgcolor,
                              outline_color=olcolor, outline_width=olwidth,
                              outline_feather=olfeather)

    if not parent:
        parent = NodePath("text")

    ndpath = parent.attachNewNode("text-node-parent")
    if isinstance(pos, VBase2):
        pos = Point3(pos[0], 0.0, pos[1])
    ndpath.setPos(pos)

    backgrounds = as_sequence(background)
    if backgrounds:
        imgnd = ndpath.attachNewNode("text-node-parent")
        for imgpath, imgsize, imgpos in reversed(backgrounds):
            img = make_image(imgpath, size=imgsize, pos=imgpos, parent=imgnd)
    else:
        imgnd = None

    nd = TextNode("text-node")
    nd.setFont(font)
    nd.setSmallCaps(smallcaps)
    nd.setUnderscore(underscore)
    subndpath = ndpath.attachNewNode(nd)
    if shader is not None:
        subndpath.setShader(shader)
    height, heightbase = _set_text_node(
        nd, subndpath, text, width, size, color, shcolor, align, anchor, wrap,
        None, None)

    ndpath.setPythonTag("nd", nd)
    ndpath.setPythonTag("ndpath", subndpath)
    ndpath.setPythonTag("imgndpath", imgnd)
    ndpath.setPythonTag("text", text)
    ndpath.setPythonTag("width", width)
    ndpath.setPythonTag("size", size)
    ndpath.setPythonTag("color", color)
    ndpath.setPythonTag("shcolor", shcolor)
    ndpath.setPythonTag("align", align)
    ndpath.setPythonTag("anchor", anchor)
    ndpath.setPythonTag("wrap", wrap)
    ndpath.setPythonTag("height", height)
    ndpath.setPythonTag("heightbase", heightbase)

    return ndpath


def _set_text_node (nd, ndpath,
                    text, width, size, color, shcolor, align, anchor, wrap,
                    height, heightbase):

    scale = font_scale_for_ptsize(size)
    if wrap:
        nd.setWordwrap(width / scale)

    if "c" in align:
        amode = TextNode.ACenter
    elif "r" in align:
        amode = TextNode.ARight
    else: # "l" in align
        amode = TextNode.ALeft
    nd.setAlign(amode)

    if text is not None:
        nd.setText("bq") # for full height above and below baseline
        heightbase = nd.getHeight() * scale * 0.75
        nd.setText(text.encode(UI_TEXT_ENC))
        height = nd.getHeight() * scale
        if not wrap:
            ewidth = nd.getWidth() * scale
            if ewidth > width:
                elipsis = "..."
                nd.setText(elipsis.encode(UI_TEXT_ENC))
                lwidth = width - nd.getWidth() * scale
                etext = text
                nd.setText(etext.encode(UI_TEXT_ENC))
                while True:
                    ewidth = nd.getWidth() * scale
                    if ewidth <= lwidth:
                        break
                    etext = text[:int((lwidth / ewidth) * len(etext) - 0.5)]
                    nd.setText(etext.encode(UI_TEXT_ENC))
                etext = etext.rstrip() + elipsis
                nd.setText(etext.encode(UI_TEXT_ENC))

    if "l" in anchor:
        if "c" in align:
            posx = 0.5 * width
        elif "r" in align:
            posx = width
        else: # "l" in align
            posx = 0.0
    elif "r" in anchor:
        if "c" in align:
            posx = -0.5 * width
        elif "r" in align:
            posx = 0.0
        else: # "l" in align
            posx = -width
    else: # "c" in anchor
        if "c" in align:
            posx = 0.0
        elif "r" in align:
            posx = 0.5 * width
        else: # "l" in align
            posx = -0.5 * width

    if "t" in anchor:
        posz = 0.0
    elif "b" in anchor:
        posz = height
    else: # "m" in anchor
        posz = 0.5 * height
    posz -= heightbase

    if color is not None:
        nd.setTextColor(*color)

    if shcolor is not None:
        nd.setShadow(0.1, 0.1)
        nd.setShadowColor(*shcolor)
    else:
        nd.clearShadow()

    ndpath.setPos(posx, 0.0, posz)
    ndpath.setScale(scale)

    return height, heightbase


def update_text (textnd, text=None, color=None, shcolor=None):
    """
    Update UI text object.

    Text elements corresponding to parameters left as None
    will not be touched.

    Parameters:
    - textnd (NodePath): the text node created by make_text

    Keyword parameters correspond to those in make_text.
    """

    text1 = None
    if text is not None and text != textnd.getPythonTag("text"):
        textnd.setPythonTag("text", text)
        text1 = text
    if color is not None:
        textnd.setPythonTag("color", color)
    if shcolor is not None:
        textnd.setPythonTag("shcolor", shcolor)

    text = textnd.getPythonTag("text")
    width = textnd.getPythonTag("width")
    size = textnd.getPythonTag("size")
    color = textnd.getPythonTag("color")
    shcolor = textnd.getPythonTag("shcolor")
    align = textnd.getPythonTag("align")
    anchor = textnd.getPythonTag("anchor")
    wrap = textnd.getPythonTag("wrap")
    height = textnd.getPythonTag("height")
    heightbase = textnd.getPythonTag("heightbase")

    nd = textnd.getPythonTag("nd")
    ndpath = textnd.getPythonTag("ndpath")
    #imgndpath = textnd.getPythonTag("imgndpath")
    height, heightbase = _set_text_node(
        nd, ndpath, text1, width, size, color, shcolor, align, anchor, wrap,
        height, heightbase)

    textnd.setPythonTag("height", height)
    textnd.setPythonTag("heightbase", heightbase)


def node_unfold_text (textnd, wpmspeed=150, time=None):

    text = textnd.getPythonTag("text")
    unfold_time = sys.float_info.max
    if wpmspeed is not None:
        read_time = reading_time(text, wpm=wpmspeed, raw=True)
        unfold_time = min(unfold_time, read_time)
    if time is not None:
        unfold_time = min(unfold_time, time)
    if not 0.0 < unfold_time < sys.float_info.max:
        return

    uc = SimpleProps()
    uc.text_length = len(text)
    uc.unfold_speed = uc.text_length / unfold_time
    uc.current_text = ""
    uc.current_pos = 0
    uc.current_float_pos = 0.0
    uc.previous_pos = 0

    update_text(textnd, text="")

    def taskf (task):

        if textnd.isEmpty():
            return task.done

        dt = base.global_clock.getDt()
        uc.current_float_pos += dt * uc.unfold_speed
        current_pos = int(uc.current_float_pos + 0.5)
        if uc.previous_pos < current_pos:
            #print "--unfold40", "==============", current_pos
            uc.current_pos = min(current_pos, uc.text_length)
            # The next word unfolded in full may cause new line,
            # in which case an immediate new line must be inserted.
            p1 = uc.previous_pos
            while p1 < uc.current_pos:
                if text[p1].isspace():
                    break
                p1 += 1
            if p1 < uc.current_pos:
                p2 = p1
                while p2 < uc.text_length and text[p2].isspace():
                    p2 += 1
                while p2 < uc.text_length and not text[p2].isspace():
                    p2 += 1
                #print "--unfold46 {%s}" % text[p1:p2]
                uc.current_text += text[uc.previous_pos:p1]
                test_current_text = uc.current_text + text[p1:p2]
                #print "--unfold48 {%s}" % test_current_text.replace("\n", "|")
                update_text(textnd, text=test_current_text)
                tn = textnd.getPythonTag("nd")
                test_wrapped_text = tn.getWordwrappedText()
                current_lines = uc.current_text.count("\n") + 1
                test_lines = test_wrapped_text.count("\n") + 1
                #print "--unfold49 {%s}" % test_wrapped_text.replace("\n", "|")
                if current_lines < test_lines:
                    uc.current_text += "\n"
                    uc.current_text += text[p2:uc.current_pos]
                else:
                    uc.current_text += text[p1:uc.current_pos]
            else:
                uc.current_text += text[uc.previous_pos:uc.current_pos]
            update_text(textnd, text=uc.current_text)
            uc.previous_pos = uc.current_pos
            #print "--unfold51 {%s}" % uc.current_text.replace("\n", "|")

        if uc.current_float_pos >= uc.text_length:
            return task.done

        return task.cont

    base.taskMgr.add(taskf, "unfold-text")


def font_scale_for_ptsize (ptsize):

    screen_dpi = 120
    screen_pxsize = 1024 # base.window_size_y
    # NOTE: We must not really try to set font size according to
    # physical screen size: that would ruin the relation of text size
    # to other graphical elements. This would be bad in a 3D game.
    # Therefore fixed values for screen DPI and pixel height.
    pxsize = (ptsize / 72.0) * screen_dpi
    font_scale = pxsize / (0.5 * screen_pxsize)
    return font_scale


def pixel_scale_for_size (size):

    screen_pxsize = base.window_size_y
    pxsize = size * (screen_pxsize / 2.0)
    return pxsize


class HorizRule (object):

    def __init__ (self):

        pass


def make_text_page (text, width, font, size, color,
                    ppunit=30, align="l", anchor="tl",
                    page_width=None, page_height=None,
                    para_spacing=1.0,
                    line_width=0.005, rule_length=0.5):

    if not isinstance(text, (tuple, list)):
        text = [text]

    # Split hard-coded paragraphs to real paragraphs.
    mod_text = []
    for text_1 in text:
        if isinstance(text_1, tuple):
            text_1, props_1 = text_1
        else:
            props_1 = None
        if isinstance(text_1, basestring):
            split_text = text_1.split("\n\n")
        else:
            split_text = [text_1]
        for mod_text_1 in split_text:
            if props_1 is not None:
                mod_text.append((mod_text_1, props_1))
            else:
                mod_text.append(mod_text_1)

    if page_width is None:
        page_width = width
    if page_height is None:
        page_height = 0.0
    accu_height = 0.0
    pnd = NodePath("text")
    tnds = []
    for i, text_1 in enumerate(mod_text):
        if isinstance(text_1, tuple):
            text_1, props_1 = text_1
        else:
            props_1 = None
        tnd = None
        if isinstance(text_1, basestring):
            font_1 = font
            ppunit_1 = ppunit
            size_1 = size
            color_1 = color
            align_1 = align
            smallcaps_1 = False
            underscore_1 = False
            para_spacing_1 = para_spacing
            block_indent_1 = 0.0
            if props_1 is not None:
                if props_1.font is not None:
                    font_1 = font_1.font
                if props_1.ppunit is not None:
                    ppunit_1 = props_1.ppunit
                if props_1.size is not None:
                    size_1 = props_1.size
                if props_1.size_factor is not None: # after .size
                    size_1 *= props_1.size_factor
                if props_1.color is not None:
                    color_1 = props_1.color
                if props_1.align is not None:
                    align_1 = props_1.align
                if props_1.smallcaps is not None:
                    smallcaps_1 = props_1.smallcaps
                if props_1.underscore is not None:
                    underscore_1 = props_1.underscore
                if props_1.para_spacing is not None:
                    para_spacing_1 = props_1.para_spacing
                if props_1.block_indent is not None:
                    block_indent_1 = props_1.block_indent
            base_height = font_scale_for_ptsize(size_1)
            if i >= 1:
                accu_height += base_height * para_spacing_1
            width_1 = width
            if align_1 in ("r", "l"):
                width -= block_indent_1
            if align_1 == "l":
                x_1 = block_indent_1
            elif align_1 == "r":
                x_1 = -block_indent_1
            else:
                x_1 = 0.0
            z_1 = -accu_height
            tnd = make_text(
                text=text_1, width=width_1, pos=Point3(x_1, 0.0, z_1),
                font=font_1, ppunit=ppunit_1, size=size_1, color=color_1,
                align=align_1, anchor=anchor,
                smallcaps=smallcaps_1, underscore=underscore_1,
                parent=pnd)
            ttnd = tnd.getPythonTag("nd")
            text_height = base_height * ttnd.getLineHeight() * ttnd.getNumRows()
            accu_height += text_height

        elif isinstance(text_1, HorizRule):
            size_1 = size
            para_spacing_1 = para_spacing
            line_width_1 = line_width
            length_1 = rule_length
            color_1 = color
            if props_1 is not None:
                if props_1.size is not None:
                    size_1 = props_1.size
                if props_1.size_factor is not None: # after .size
                    size_1 *= props_1.size_factor
                if props_1.para_spacing is not None:
                    para_spacing_1 = props_1.para_spacing
                if props_1.line_width is not None:
                    line_width_1 = props_1.line_width
                if props_1.length is not None:
                    length_1 = props_1.length
                if props_1.color is not None:
                    color_1 = props_1.color
            base_height = font_scale_for_ptsize(size_1)
            accu_height += base_height * para_spacing_1
            thickness_1 = pixel_scale_for_size(line_width_1)
            accu_height += 0.25 * base_height
            accu_height += 0.5 * line_width_1
            tnd = LineNodePath(
                thickness=thickness_1, colorVec=color_1,
                parent=pnd)
            if "l" in anchor:
                x_1 = 0.5 * page_width
            elif "r" in anchor:
                x_1 = -0.5 * page_width
            else: # "c" in anchor:
                x_1 = 0.0
            segs = [(Point3(x_1 - 0.5 * length_1, 0.0, -accu_height),
                     Point3(x_1 + 0.5 * length_1, 0.0, -accu_height))]
            tnd.drawLines(segs)
            tnd.create()
            accu_height += 0.5 * line_width_1
            accu_height += 0.25 * base_height

        if tnd is not None:
            tnds.append(tnd)

    # Offset nodes for page.
    for tnd in tnds:
        x, y, z = tnd.getPos()
        if "l" in anchor:
            x -= 0.5 * page_width
        elif "r" in anchor:
            x += 0.5 * page_width
        if "t" in anchor:
            z += 0.5 * page_height
        elif "b" in anchor:
            z -= 0.5 * page_height - accu_height
        else: # "m" in anchor
            z += 0.5 * accu_height
        tnd.setPos(x, y, z)

    pnd.setPythonTag("height", accu_height)
    return pnd


# :also-compiled:
def clamp (val, val0, val1):
    """
    Clamp a scalar value to an interval.

    If the value is inside the interval, it is returned as-is.
    If it is outside, the nearest boundary value is returned instead.
    Boundary values do not have to be in particular order.
    """

    if val0 < val1:
        valmin, valmax = val0, val1
    else:
        valmax, valmin = val0, val1

    if val < valmin:
        return valmin
    elif val > valmax:
        return valmax
    else:
        return val


def absclamp (val, dval, val0=0.0):
    """
    Clamp a scalar value to a symetric interval.

    If the value is inside the interval, it is returned as-is.
    If it is outside, the nearest boundary value is returned instead.
    """

    return clamp(val, val0 - dval, val0 + dval)


def clampn (valn, valn0, valn1):
    """
    Clamp the multi-component value to an interval.

    Multi-component version of clamp(): clamp() is applied to every component,
    and resulting multi-component value (of the same type as input value)
    is returned.
    """

    return type(valn)(*[clamp(*x) for x in zip(valn, valn0, valn1)])


def pclamp (val, val0, val1, per0=None, per1=None, mirror=False):
    """
    Clamp a periodical scalar value to an interval.

    Like clamp, except that values have a basic period (e.g. angles).
    Basic period is defined by lower (inclusive) and upper (exclusive)
    limit value.
    Interval limits do not have to be given within the basic period.
    If the value is outside the interval, it is reduced to nearer
    of the two limits, considering periodicity.
    If the value is within the interval, but not within the basic period,
    it will be reduced to basic period.
    If lower (upper) period limit is not given, it is taken as equal to
    lower (upper) interval limit.
    """

    skipf = _pclamp_skipf_mirror if mirror else _pclamp_skipf_direct

    if per0 is None:
        per0 = val0
    if per1 is None:
        per1 = val1

    if per1 < per0:
        per0, per1 = per1, per0

    while val1 < val0:
        val1 = skipf(val1, per0, per1, +1)
    val0t = skipf(val0, per0, per1, +1)
    while val0t < val1:
        val0 = skipf(val0, per0, per1, +1)

    if val < val0:
        valp = val
        while val < val0:
            valp = val
            val = skipf(val, per0, per1, +1)
        if val > val1:
            if val0 - valp < val - val1:
                val = val0
            else:
                val = val1
    elif val > val1:
        valp = val
        while val > val1:
            valp = val
            val = skipf(val, per0, per1, -1)
        if val < val0:
            if val1 - valp < val0 - val:
                val = val1
            else:
                val = val0

    while val < per0:
        val = skipf(val, per0, per1, +1)
    while val >= per1:
        valp = val
        val = skipf(val, per0, per1, -1)
        if valp == val: # may happen on mirror
            break

    return val


def _pclamp_skipf_direct (val, per0, per1, side):

    return val + side * (per1 - per0)


def _pclamp_skipf_mirror (val, per0, per1, side):

    if val != per0:
        nints = int((val - per0) / (per1 - per0))
        if side > 0:
            nints += 1
        return val - 2 * (val - (per0 + nints * (per1 - per0)))
    else:
        return val + side * (per1 - per0)


def next_pos (pos, vel, acc, dt):

    pos1 = pos + (vel + acc * (0.5 * dt)) * dt
    return pos1


def next_quat (quat, angvel, angacc, dt):

    daxis = (angvel + angacc * (0.5 * dt)) * dt
    dang = daxis.length()
    if daxis.normalize():
        dquat = Quat()
        dquat.setFromAxisAngleRad(dang, daxis)
        quat1 = quat * dquat
    else:
        quat1 = quat
    return quat1


def update_towards (tvalue, value, speed, dt):
    """
    Compute the new value updated towards the target value.

    The value is updated using given absolute speed and time step
    (both must be positive).
    If speed or dt are None, the copy of target value is returned.
    Values can be float or VecBase.
    """

    if isinstance(tvalue, float):
        if speed is not None and dt is not None:
            if abs(tvalue - value) < speed * dt:
                return tvalue
            else:
                tdir = 1 if value < tvalue else -1
                return value + tdir * speed * dt
        else:
            return tvalue
    else:
        if speed is not None and dt is not None:
            if (tvalue - value).length() < speed * dt:
                return type(tvalue)(tvalue)
            else:
                tdir = tvalue - value
                tdir.normalize()
                return value + tdir * speed * dt
        else:
            return type(tvalue)(tvalue)


def update_bounded (tvalue, tspeed, value, speed, maxspeed, minaccel, dt,
                    mon=False):
    """
    Compute the new value updated towards the target value and target speed,
    never overshooting the target value.

    The value and speed is updated using given maximum absolute speed,
    minimum absolute acceleration, and the time step.
    Value is not allowed to overshoot the target value, and acceleration
    is varied as necessary to achieve this; it is attempted
    to keep it above and near to the given minimum absolute acceleration.
    If maximum absolute speed is not greater than zero,
    there is no limit on speed.
    If minimum absolute accceleration is not greater than zero,
    there is no limit on acceleration.
    If neither maximum absolute speed nor minimum absolute acceleration
    are greater than zero, target value and target speed
    are immediately reached.

    Updated value and speed for given time step are returned.
    If speed or time step is None, target value and target speed are returned.

    With respect to roundoff errors, it is guaranteed that in the end
    value and speed will be exactly equal to tvalue and tspeed.
    """

    if speed is None or dt is None or value == tvalue:
        value_up = tvalue
        speed_up = tspeed

    elif dt == 0.0:
        value_up = value
        speed_up = speed

    elif maxspeed > 0.0 and minaccel > 0.0:
        assert abs(tspeed) <= maxspeed

        at_targets = False
        at_max_speed = False
        if tspeed != speed:
            assert tvalue != value
            accel = minaccel * sign(tspeed - speed)
            # Select time to maximum value or to target speed.
            time_ts = (tspeed - speed) / accel
            time_zs = -speed / accel
            time_ch = time_zs if 0.0 < time_zs < time_ts else time_ts
            value_ch = value + speed * time_ch + accel * (0.5 * time_ch**2)
            if mon:
                dbgval(1, "uptwac-120", value, value_ch, tvalue, time_ts, time_zs)
            if (tvalue - value) * (tvalue - value_ch) <= 0.0:
                # The minimum acceleration would cause the value to overshoot
                # the target value during the time target speed is reached.
                # Use acceleration that will reach both targets
                # at the same time.
                accel = 0.5 * (tspeed - speed) * (tspeed + speed) / (tvalue - value)
                time_tvs = (tvalue - value) / (0.5 * (tspeed + speed))
                at_targets = (time_tvs <= dt)
                if mon:
                    dbgval(1, "uptwac-122", accel, time_tvs, dt, at_targets)
            else:
                # The minimum acceleration would cause the speed to reach
                # the target speed before the value reaches the target value.
                # Increase the speed by minimum acceleration in the direction
                # of target value.
                # Do not overshoot the maximum speed or the target value.
                maxspeed_sg = maxspeed * sign(tvalue - value)
                accel = (maxspeed_sg - speed) / dt
                if abs(accel) > minaccel:
                    accel = minaccel * sign(accel)
                else:
                    at_max_speed = True
                value_n = value + speed * dt + accel * (0.5 * dt**2)
                at_targets = ((tvalue - value) * (tvalue - value_n) <= 0.0)
                if mon:
                    dbgval(1, "uptwac-124",
                           accel, speed, maxspeed_sg, at_max_speed, at_targets)
        else:
            accel = minaccel * sign(tvalue - value)
            time_tv = sqrt((tvalue - value) / (0.5 * accel))
            if abs(speed) != maxspeed:
                speed_n = speed + accel * dt
                if abs(speed_n) > maxspeed:
                    accel = (maxspeed * sign(speed_n) - speed) / dt
                    time_tv = sqrt((tvalue - value) / (0.5 * accel))
                at_targets = (time_tv <= dt)
                if mon:
                    dbgval(1, "uptwac-130",
                           accel, speed_n, time_tv, dt, at_targets)
            else:
                accel = 0.0
                time_tv = (tvalue - value) / speed
                at_targets = (0.0 <= time_tv <= dt)
                if mon:
                    dbgval(1, "uptwac-132", time_tv, dt, at_targets)

        if not at_targets:
            value_up = value + speed * dt + accel * (0.5 * dt**2)
            if not at_max_speed:
                speed_up = speed + accel * dt
            else:
                speed_up = maxspeed_sg
            if mon:
                dbgval(1, "uptwac-152",
                       value, speed, accel, dt, value_up, speed_up)
        else:
            value_up = tvalue
            speed_up = tspeed
            if mon:
                dbgval(1, "uptwac-154", value_up, speed_up)

    elif minaccel > 0.0:
        at_targets = False
        if tspeed != speed:
            assert tvalue != value
            accel = minaccel * sign(tspeed - speed)
            # Select time to maximum value or to target speed.
            time_ts = (tspeed - speed) / accel
            time_zs = -speed / accel
            time_ch = time_zs if 0.0 < time_zs < time_ts else time_ts
            value_ch = value + speed * time_ch + accel * (0.5 * time_ch**2)
            if mon:
                dbgval(1, "uptwac-220",
                       value, value_ch, tvalue, time_ts, time_zs)
            if (tvalue - value) * (tvalue - value_ch) <= 0.0:
                # The minimum acceleration would cause the value to overshoot
                # the target value during the time target speed is reached.
                # Use acceleration that will reach both targets
                # at the same time.
                accel = 0.5 * (tspeed - speed) * (tspeed + speed) / (tvalue - value)
                time_tvs = (tvalue - value) / (0.5 * (tspeed + speed))
                at_targets = (time_tvs <= dt)
                if mon:
                    dbgval(1, "uptwac-222", accel, time_tvs, dt, at_targets)
            else:
                # The minimum acceleration would cause the speed to reach
                # the target speed before the value reaches the target value.
                # Increase the speed by minimum acceleration in the direction
                # of target value.
                # Do not overshoot the target value.
                accel = minaccel * sign(tvalue - value)
                value_n = value + speed * dt + accel * (0.5 * dt**2)
                at_targets = ((tvalue - value) * (tvalue - value_n) <= 0.0)
                if mon:
                    dbgval(1, "uptwac-224", accel, speed, at_targets)
        else:
            accel = minaccel * sign(tvalue - value)
            time_tv = sqrt((tvalue - value) / (0.5 * accel))
            at_targets = (time_tv <= dt)
            if mon:
                dbgval(1, "uptwac-230", accel, time_tv, dt, at_targets)

        if not at_targets:
            value_up = value + speed * dt + accel * (0.5 * dt**2)
            speed_up = speed + accel * dt
            if mon:
                dbgval(1, "uptwac-252",
                       value, speed, accel, dt, value_up, speed_up)
        else:
            value_up = tvalue
            speed_up = tspeed
            if mon:
                dbgval(1, "uptwac-254", value_up, speed_up)

    elif maxspeed > 0.0:
        assert abs(tspeed) <= maxspeed

        speed = maxspeed * sign(tvalue - value)
        value_n = value + speed * dt
        if (tvalue - value) * (tvalue - value_n) <= 0.0:
            value_up = tvalue
            speed_up = tspeed
        else:
            value_up = value_n
            speed_up = speed

    else:
        value_up = tvalue
        speed_up = tspeed

    return value_up, speed_up


def solve_quad (a, b, c):
    """
    Solve quadratic equation.

    The equation is in the form
        a * x**2 + b * x + c = 0.

    If real roots exist, the first returned root is smaller than the second.
    Otherwise (None, None) is returned.
    """

    x = VBase2D()
    if solve_quad_s(a, b, c, x):
        return x[0], x[1]
    else:
        return None, None


# :also-compiled:
def solve_quad_s (a, b, c, x):

    exist = False
    if a != 0.0:
        d = b**2 - 4 * a * c
        if d >= 0.0:
            exist = True
            rd = sqrt(d)
            x1 = (-b - rd) / (2 * a)
            x2 = (-b + rd) / (2 * a)
            if x1 > x2:
                x1, x2 = x2, x1
            x[0] = x1; x[1] = x2
    elif b != 0.0:
        exist = True
        x1 = - c / b
        x[0] = x[1] = x1
    return exist


def solve_quad_minpos (a, b, c):
    """
    Get smallest positive root of quadratic equation.

    Like solve_quad, but returns only the smallest positive root,
    if it exists. Otherwise returns None.
    """

    x = VBase2D()
    if solve_quad_minpos_s(a, b, c, x):
        return x[0]
    else:
        return None


# :also-compiled:
def solve_quad_minpos_s (a, b, c, x):

    exist = False
    if solve_quad_s(a, b, c, x):
        # Guaranteed order x[0] <= x[1].
        if x[0] > 0.0:
            exist = True
        elif x[1] > 0.0:
            exist = True
            x[0] = x[1]
    return exist


def solve_quad_minabs (a, b, c):
    """
    Get smallest root by absolute value of quadratic equation.

    Like solve_quad, but returns only the smallest root by absolute value,
    if it exists. Otherwise returns None.
    """

    x1, x2 = solve_quad(a, b, c)
    if x1 is None:
        x = None
    elif abs(x1) < abs(x2):
        x = x1
    else:
        x = x2
    return x


def solve_quad_maxabs (a, b, c):
    """
    Get greatest root by absolute value of quadratic equation.

    Like solve_quad, but returns only the greatest root by absolute value,
    if it exists. Otherwise returns None.
    """

    x1, x2 = solve_quad(a, b, c)
    if x1 is None:
        x = None
    elif abs(x1) > abs(x2):
        x = x1
    else:
        x = x2
    return x


def solve_linsys_2 (a11, a12, a21, a22, b1, b2, epsz=1e-10):
    """
    Solve 2x2 linear system.

    The linear system is in the form
        |a11 a12| |x1|   |b1|
        |a21 a22| |x2| = |b2|.

    If the absolute value of the system determinant is greater then epsz,
    x1, x2 are returned; otherwise, None is returned.
    """

    det = a11 * a22 - a12 * a21
    if abs(det) <= epsz:
        return None
    det1 = b1 * a22 - b2 * a12
    det2 = b2 * a11 - b1 * a21
    x1 = det1 / det
    x2 = det2 / det
    return x1, x2


def solve_linsys_3 (a11, a12, a13, a21, a22, a23, a31, a32, a33, b1, b2, b3,
                    epsz=1e-10):
    """
    Solve 3x3 linear system.

    The linear system is in the form
        |a11 a12 a13| |x1|   |b1|
        |a21 a22 a23| |x2| = |b2|.
        |a31 a32 a33| |x3|   |b3|

    If the absolute value of the system determinant is greater then epsz,
    x1, x2, x3 are returned; otherwise, None is returned.
    """

    det = (  a11 * a22 * a33 + a12 * a23 * a31 + a13 * a21 * a32
           - a13 * a22 * a31 - a12 * a21 * a33 - a11 * a23 * a32)
    if abs(det) <= epsz:
        return None
    det1 = (  b1 * (a22 * a33 - a23 * a32)
            + b2 * (a13 * a32 - a12 * a33)
            + b3 * (a12 * a23 - a13 * a22))
    det2 = (  b1 * (a23 * a31 - a21 * a33)
            + b2 * (a11 * a33 - a13 * a31)
            + b3 * (a13 * a21 - a11 * a23))
    det3 = (  b1 * (a21 * a32 - a22 * a31)
            + b2 * (a12 * a31 - a11 * a32)
            + b3 * (a11 * a22 - a12 * a21))
    x1 = det1 / det
    x2 = det2 / det
    x3 = det3 / det
    return x1, x2, x3


def sign (x):

    return cmp(x, 0)


# :also-compiled:
def unitv (v):

    lv = v.length()
    return v / lv if lv != 0.0 else v


def norm_ang_delta (fromang, toang, indeg=False):

    if indeg:
        fromang = radians(fromang)
        toang = radians(toang)

    while fromang <= -pi:
        fromang += 2 * pi
    while fromang > pi:
        fromang -= 2 * pi
    while toang <= -pi:
        toang += 2 * pi
    while toang > pi:
        toang -= 2 * pi

    dang = toang - fromang
    if dang > pi:
        dang = dang - 2 * pi
    if dang < -pi:
        dang = dang + 2 * pi

    if indeg:
        dang = degrees(dang)

    return dang


def norm_ang (ang, indeg=False):

    if indeg:
        ang = radians(ang)

    angn = ang
    while angn <= -pi:
        angn += 2 * pi
    while angn > pi:
        angn -= 2 * pi

    if indeg:
        angn = degrees(angn)

    return angn


def vtod (v):

    return Vec3D(v[0], v[1], v[2])


def vtof (v):

    return Vec3(v[0], v[1], v[2])


def vtop (v):

    if isinstance(v, VBase3D):
        return Point3D(v[0], v[1], v[2])
    else:
        return Point3(v[0], v[1], v[2])


def ptod (v):

    return Point3D(v[0], v[1], v[2])


def ptof (v):

    return Point3(v[0], v[1], v[2])


def ptov (v):

    if isinstance(v, VBase3D):
        return Vec3D(v[0], v[1], v[2])
    else:
        return Vec3(v[0], v[1], v[2])


def qtod (q):

    return QuatD(q[0], q[1], q[2], q[3])


def qtof (q):

    return Quat(q[0], q[1], q[2], q[3])


def as_sequence (value):
    """
    View a value as a sequence.

    The value is returned as-is if it implements __iter__.
    If the value is None, empty sequence is returned.
    Otherwise, the value is wrapped as a sequence of single element.

    Useful when input parameter to a function can be None,
    a single non-None value, or a sequence of values, to avoid always
    writing code for conditionally promoting such input parameter
    to a sequence which can be iterated over.
    """

    if value is None:
        return ()
    elif isinstance(value, _vbase_cls) or getattr(value, "__iter__", False):
        return value
    else:
        return (value,)


def node_fade_to (node, endalpha, duration, startalpha=None, startf=None,
                  endf=None, taskname=None, frozen=False, timer=None):
    """
    Task dispatcher for fading in/out a node using alpha scale.

    Parameters:
    - node (NodePath, or list of): node to fade
    - endalpha (float): final alpha scale for the node (0.0 to 1.0)
    - duration (float): time in seconds to go from initial to final alpha
    - startalpha (float): start from this alpha instead from node alpha
    - startf (()->?, or list of): function to execute at start of fading
    - endf (()->?, or list of): function to execute at end of fading
    - taskname (string): name for the task
    - frozen (bool): return the thunk which adds the task when called
    - timer (has .time attribute): object to use as timer instead of task
    """

    nodes = as_sequence(node)

    if startalpha is None:
        alpha0s = []
        for nd in nodes:
            if isinstance(nd, (AudioSound, AudioManager)):
                alpha0s.append(nd.getVolume())
            else:
                alpha0s.append(nd.getSa())
    else:
        alpha0s = [startalpha] * len(nodes)
        for nd in nodes:
            if isinstance(nd, (AudioSound, AudioManager)):
                nd.setVolume(startalpha)
            else:
                nd.setSa(startalpha)

    def taskf (task):

        ctimer = timer if timer is not None else task
        if task.first:
            for func in as_sequence(startf):
                func()
            task.time0 = ctimer.time
            task.first = False
        dtime = clamp(ctimer.time - task.time0, 0.0, duration)
        #print "--nft10", task, node, endalpha, duration, dtime

        anyremaining = False
        for nd, alpha0 in zip(nodes, alpha0s):
            if duration > 0:
                alpha = alpha0 + (endalpha - alpha0) * dtime / duration
            else:
                alpha = endalpha
            alpha = clamp(alpha, alpha0, endalpha)
            if isinstance(nd, (AudioSound, AudioManager)):
                nd.setVolume(alpha)
                anyremaining = True
            else:
                if not nd.isEmpty():
                    nd.setSa(alpha)
                    anyremaining = True

        if dtime >= duration or not anyremaining:
            for func in as_sequence(endf):
                func()
            #print "--nft20", task, node, endalpha, "done"
            return task.done
        else:
            #print "--nft30", task, node, endalpha, "cont"
            return task.cont

    if not taskname:
        taskname = "node-fade-to"
    def thunk ():
        task = base.taskMgr.add(taskf, taskname)
        task.first = True
        return task
    return thunk() if not frozen else thunk


def node_slide_to (node, endpos, duration, taskname=None,
                   lookat=None, endup=None, frozen=False, timer=None):
    """
    Task dispatcher for sliding a node to new position.

    Parameters:
    - node (NodePath, or list of): node to slide
    - endpos (Point3): final position of the node
    - duration (float): time in seconds to go from initial to final position
    - taskname (string): name for the task
    - lookat (NodePath): keep forward direction of the node towards
        this node during sliding
    - endup (Vec3): adjust up vector of the node during sliding such
        that at the end it lies in the plane of this vector and forward
    - frozen (bool): return the thunk which adds the task when called
    - timer (has .time attribute): object to use as timer instead of task
    """

    nodes = as_sequence(node)
    pos0s = [nd.getPos() for nd in nodes]
    up0s = [nd.getQuat().getUp() for nd in nodes]

    def taskf (task):
        ctimer = timer if timer is not None else task
        if task.first:
            task.time0 = ctimer.time
            task.first = False
        dtime = ctimer.time - task.time0
        if duration > 0.0:
            tfac = clamp(dtime / duration, 0.0, 1.0)
        else:
            tfac = 1.0
        anyremaining = False
        for nd, pos0, up0 in zip(nodes, pos0s, up0s):
            if not nd.isEmpty():
                cpos = pos0 + (endpos - pos0) * tfac
                nd.setPos(cpos)
                if lookat is not None: # before endup
                    nd.lookAt(lookat)
                if endup is not None:
                    fw = nd.getQuat().getForward()
                    up = up0 + (endup - up0) * tfac
                    set_hpr_vfu(nd, fw, up)
                anyremaining = True
        return task.cont if (dtime < duration and anyremaining) else task.done

    if not taskname:
        ndstr = "|".join([x.getName() for x in nodes])
        taskname = "node-slide-to-%s" % ndstr
    def thunk ():
        task = base.taskMgr.add(taskf, taskname)
        task.first = True
        return task
    return thunk() if not frozen else thunk


def node_scale_to (node, endscale, duration, startscale=None,
                   startf=None, endf=None, taskname=None, frozen=False,
                   timer=None):
    """
    Task dispatcher for scaling a node to a new scale.

    Parameters:
    - node (NodePath, or list of): node to scale
    - endscale (float or Vec3): final scale of the node
    - duration (float): time in seconds to go from initial to final scale
    - startscale (float or Vec3): initial scale of the node
    - startf (()->?, or list of): function to execute at start of scaling
    - endf (()->?, or list of): function to execute at end of scaling
    - taskname (string): name for the task
    - frozen (bool): return the thunk which adds the task when called
    - timer (has .time attribute): object to use as timer instead of task
    """

    if isinstance(startscale, (int, float)):
        startscale = Vec3(startscale, startscale, startscale)
    if isinstance(endscale, (int, float)):
        endscale = Vec3(endscale, endscale, endscale)

    nodes = as_sequence(node)
    if startscale is None:
        scale0s = [nd.getScale() for nd in nodes]
    else:
        scale0s = [startscale] * len(nodes)

    def taskf (task):

        ctimer = timer if timer is not None else task
        if task.first:
            for func in as_sequence(startf):
                func()
            task.time0 = ctimer.time
            task.first = False
        dtime = clamp(ctimer.time - task.time0, 0.0, duration)

        anyremaining = False
        for nd, scale0 in zip(nodes, scale0s):
            if duration > 0:
                scale = scale0 + (endscale - scale0) * (dtime / duration)
            else:
                scale = endscale
            scale = clampn(scale, scale0, endscale)
            if not nd.isEmpty():
                nd.setScale(scale)
                anyremaining = True

        if dtime >= duration or not anyremaining:
            for func in as_sequence(endf):
                func()
            return task.done
        else:
            return task.cont

    if not taskname:
        taskname = "node-scale-to"
    def thunk ():
        task = base.taskMgr.add(taskf, taskname)
        task.first = True
        return task
    return thunk() if not frozen else thunk


def node_rothprloc_to (node, dhpr, duration,
                       center=None,
                       taskname=None, frozen=False, timer=None):
    """
    Task dispatcher for rotating a node by delta HPR angle
    in node's coordinate system.

    Parameters:
    - node (NodePath, or list of): node to rotate
    - dhpr (Point3): delta HPR for rotation
    - duration (float): time in seconds for rotation
    - center (Point3): point to rotate around instead of the node center,
        in local coordinate system
    - taskname (string): name for the task
    - frozen (bool): return the thunk which adds the task when called
    - timer (has .time attribute): object to use as timer instead of task
    """

    nodes = as_sequence(node)
    pos0s = [nd.getPos() for nd in nodes]
    hpr0s = [nd.getHpr() for nd in nodes]

    def taskf (task):
        ctimer = timer if timer is not None else task
        if task.first:
            task.time0 = ctimer.time
            task.first = False
        dtime = ctimer.time - task.time0
        if duration > 0.0:
            tfac = clamp(dtime / duration, 0.0, 1.0)
        else:
            tfac = 1.0
        anyremaining = False
        for nd, pos0, hpr0 in zip(nodes, pos0s, hpr0s):
            if not nd.isEmpty():
                dhpr1 = dhpr * tfac
                nd.setPos(pos0)
                nd.setHpr(hpr0)
                move_node_rothprloc(nd, center, dhpr1)
                anyremaining = True
        return task.cont if (dtime < duration and anyremaining) else task.done

    if not taskname:
        ndstr = "|".join([x.getName() for x in nodes])
        taskname = "node-rothprloc-to-%s" % ndstr
    def thunk ():
        task = base.taskMgr.add(taskf, taskname)
        task.first = True
        return task
    return thunk() if not frozen else thunk


def move_node_rothprloc (node, center, dhpr):
    """
    Set new node position and orientation by rotating around
    the given center point in node's coordinate system
    for given delta HPR angle.
    """

    if center is None:
        node.setHpr(node.getHpr() + dhpr)
        return

    ref = NodePath("ref")
    arm = ref.attachNewNode("arm")
    parent = node.getParent()
    ref.reparentTo(node)
    ref.setPos(center)
    ref.wrtReparentTo(parent)
    node.wrtReparentTo(arm)
    arm.setHpr(dhpr)
    node.wrtReparentTo(parent)
    arm.removeNode()
    ref.removeNode()


def node_swipe (node, angledeg=0.0, duration=1.0, cover=False,
                startf=None, endf=None):

    angle = radians(angledeg)
    udir = Vec3(cos(angle), 0.0, sin(angle))
    udir.normalize()
    vdir = Vec3(-udir[2], 0.0, udir[0]) # 90 degree rotated

    pos = node.getPos()
    c1, c3 = node.getTightBounds()
    c2 = Point3(c3[0], c3[1], c1[2])
    c4 = Point3(c1[0], c1[1], c3[2])
    sizex = c3[0] - c1[0]
    sizez = c3[2] - c1[2]
    off = (c3 + c1) * 0.5 - pos

    umin, umax = 1e30, -1e30
    vmin, vmax = 1e30, -1e30
    for c in (c1, c2, c3, c4):
        u = c.dot(udir)
        umin = min(umin, u)
        umax = max(umax, u)
        v = c.dot(vdir)
        vmin = min(vmin, v)
        vmax = max(vmax, v)
    sizeu = umax - umin
    sizev = vmax - vmin

    rttbuffer = base.window.makeTextureBuffer("swipe-buffer", 1024, 1024)
    rttbuffer.setSort(-100)
    rttscene = NodePath("swipe-scene")
    rttcamera = base.make_camera_2d(window=rttbuffer,
                                    coords=(-0.5 * sizeu, 0.5 * sizeu,
                                            -0.5 * sizev, 0.5 * sizev))
    rttcamera.node().setScene(rttscene)

    pnode = node.getParent()
    slider = pnode.attachNewNode("swipe-slider")
    slider.setPos(pos + off)
    slider.setHpr(0.0, 0.0, -angledeg)
    curtain = make_quad(parent=slider, size=(sizeu, sizev))
    curtain.setTransparency(TransparencyAttrib.MAlpha)
    rtttexture = rttbuffer.getTexture()
    #rtttexture.setMinfilter(Texture.FTLinear)
    #rtttexture.setMagfilter(Texture.FTLinear)
    curtain.setTexture(rtttexture)
    #set_texture(curtain, "images/ui/white.png")

    rttslider = rttscene.attachNewNode("swipe-slider-rtt")
    rttslider.setPos(-off.dot(udir), 0.0, -off.dot(vdir))
    rttnode = node.copyTo(rttslider)
    #rttnode = rttslider.attachNewNode("test-image")
    #rttimg = make_image("images/ui/red.png", size=(sizex, sizez),
                        #pos=off, parent=rttnode)
    rttnode.setBin("fixed", 10)
    rttnode.setDepthWrite(False)
    rttnode.setDepthTest(False)
    rttnode.setPos(0.0, 0.0, 0.0)
    rttnode.setHpr(0.0, 0.0, angledeg)
    rttnode.show()

    speed = sizeu / duration
    cx0 = 0.0 if cover else -sizeu
    rttcx0 = 0.0 if cover else sizeu

    def finalize ():

        if not cover and not node.isEmpty():
            node.show()
        if not pnode.isEmpty():
            slider.removeNode()
        rttscene.removeNode()
        rttcamera.removeNode()
        base.graphics_engine.removeWindow(rttbuffer)
        for func in as_sequence(endf):
            func()

    def taskf (task):

        if node.isEmpty() or pnode.isEmpty():
            finalize()
            return task.done

        slider.setPos(node.getPos() + off) # in case the node moves

        if task.first:
            for func in as_sequence(startf):
                func()
            dt = 0.0
            task.first = False
        else:
            dt = base.global_clock.getDt()
        task.cdist += dt * speed
        if task.cdist > sizeu:
            task.cdist = sizeu
        curtain.setX(cx0 + task.cdist)
        rttnode.setX(rttcx0 - task.cdist)

        if task.cdist < sizeu:
            return task.cont
        else:
            finalize()
            return task.done

    node.hide()
    #node.show()
    task = base.taskMgr.add(taskf, "node-swipe")
    task.first = True
    task.cdist = 0.0

    return task


# For backward compatibility.
# Note different default value in make_quad for transp.
def make_image (texture, size=(1.0, 1.0), pos=Point3(), hpr=Vec3(),
                parent=None, filtr=True, twosided=False, clamp=True,
                transp=True):

    node = make_quad(parent=parent, pos=pos, hpr=hpr, size=size,
                     texture=texture,
                     twosided=twosided, filtr=filtr, clamp=clamp,
                     transp=transp)
    return node


def make_frame (imgbase, imgsize, width, height, name="frame", parent=None,
                offset=(0.0, 0.0), filtr=True):

    if parent is not None:
        framend = parent.attachNewNode(name)
    else:
        framend = NodePath(name)

    w = width; h = height; s = imgsize
    ox, oz = offset
    for ext, ppos, sx, sy in (
        ("ctl", Point3(ox - 0.5 * w - 0.5 * s, 0.0, oz + 0.5 * h + 0.5 * s), s, s),
        ("ctr", Point3(ox + 0.5 * w + 0.5 * s, 0.0, oz + 0.5 * h + 0.5 * s), s, s),
        ("cbl", Point3(ox - 0.5 * w - 0.5 * s, 0.0, oz - 0.5 * h - 0.5 * s), s, s),
        ("cbr", Point3(ox + 0.5 * w + 0.5 * s, 0.0, oz - 0.5 * h - 0.5 * s), s, s),
        ("et", Point3(ox + 0.0, 0.0, oz + 0.5 * h + 0.5 * s), w, s),
        ("er", Point3(ox + 0.5 * w + 0.5 * s, 0.0, oz + 0.0), s, h),
        ("eb", Point3(ox + 0.0, 0.0, oz - 0.5 * h - 0.5 * s), w, s),
        ("el", Point3(ox - 0.5 * w - 0.5 * s, 0.0, oz + 0.0), s, h),
        ("b", Point3(ox + 0.0, 0.0, oz + 0.0), w, h)
    ):
        imgpath = "%s-%s.png" % (imgbase, ext)
        make_image(imgpath, size=(sx, sy), pos=ppos, parent=framend, filtr=filtr)

    framend.flattenStrong()
    framend.setTransparency(TransparencyAttrib.MAlpha)

    return framend


_pointer_cache = {}
_pointer_prev = [None]

def get_pointer (imgpath, size=0.1, offset=Point3(), pos=None):

    pnode = _pointer_cache.get(imgpath)
    if pnode is None or pnode.isEmpty():
        pimg = make_image(imgpath, size=size)
        pimg.setBin("gui-popup", 50)
        pnode = base.square_root.attachNewNode("mouse-pointer")
        pimg.setPos(offset)
        pimg.reparentTo(pnode)
        pimg.setScale(1.0 / base.aspect_ratio, 1.0, 1.0)
        _pointer_cache[imgpath] = pnode

    if _pointer_prev[0]:
        _pointer_prev[0].detachNode()

    pnode.reparentTo(base.square_root)
    base.mouse_watcher.node().setGeometry(pnode.node())

    if pos is not None:
        hw = base.aspect_ratio
        sx = int(base.window.getXSize() * (1.0 - (hw - pos[0]) / (hw * 2)))
        sy = int(base.window.getYSize() * ((1.0 - pos[2]) / (1.0 * 2)))
        base.window.movePointer(0, sx, sy)

    _pointer_prev[0] = pnode

    return pnode


def kill_tasks (tasks):

    for task in as_sequence(tasks):
        if task:
            taskf = task.getFunction()
            if taskf in _itertask_store:
                _itertask_store.pop(taskf)
            #task.setFunction(lambda t: t.done)
            task.remove()


def map_pos_to_screen (camera, node, reloff=None, scrnode=None):

    if reloff is None:
        reloff = Point3()
    pt_cam = camera.getRelativePoint(node, reloff)
    pt_scr_2d = Point3()
    camera.node().getLens().project(pt_cam, pt_scr_2d)
    back = pt_scr_2d[2] > 1.0
    pt_scr = Point3(pt_scr_2d[0], 0.0, pt_scr_2d[1])
    if scrnode is None:
        scrnode = base.overlay_root
    pt_scr_asp = scrnode.getRelativePoint(base.square_root, pt_scr)

    return pt_scr_asp, back


def is_on_screen (camera, node):

   nodeb = node.getBounds()
   nodeb.xform(node.getParent().getMat(camera))
   lensb = camera.node().getLens().makeBounds()
   onscreen = bool(lensb.contains(nodeb))
   return onscreen


def make_raw_quad (szext=(-0.5, -0.5, 0.5, 0.5),
                   uvext=(0.0, 0.0, 1.0, 1.0),
                   alext=(1.0, 1.0, 1.0, 1.0),
                   name="quad"):

    #gvformat = GeomVertexFormat.getV3n3c4t2()
    gvformat = texfmt_tangspace()
    gvdata = GeomVertexData("data", gvformat, Geom.UHStatic)
    gvwvertex = GeomVertexWriter(gvdata, InternalName.getVertex())
    gvwnormal = GeomVertexWriter(gvdata, InternalName.getNormal())
    gvwtangent = GeomVertexWriter(gvdata, InternalName.getTangent())
    gvwbinormal = GeomVertexWriter(gvdata, InternalName.getBinormal())
    gvwcolor = GeomVertexWriter(gvdata, InternalName.getColor())
    gvwtexcoord = GeomVertexWriter(gvdata, InternalName.getTexcoord())
    gtris = GeomTriangles(Geom.UHStatic)

    ## The unrolled version below ~15% faster on one machine.
    #if isinstance(szext[0], float):
        #sz1 = (szext[0], szext[2], szext[2], szext[0])
        #sz2 = (szext[1], szext[1], szext[3], szext[3])
    #else:
        #sz1 = (szext[0][0], szext[1][0], szext[2][0], szext[3][0])
        #sz2 = (szext[0][1], szext[1][1], szext[2][1], szext[3][1])
    #if isinstance(uvext[0], float):
        #uv1 = (uvext[0], uvext[2], uvext[2], uvext[0])
        #uv2 = (uvext[1], uvext[1], uvext[3], uvext[3])
    #else:
        #uv1 = (uvext[0][0], uvext[1][0], uvext[2][0], uvext[3][0])
        #uv2 = (uvext[0][1], uvext[1][1], uvext[2][1], uvext[3][1])
    #for i in xrange(4):
        #gvwvertex.addData3f(sz1[i], 0.0, sz2[i])
        #gvwnormal.addData3f(0.0, 1.0, 0.0)
        #gvwtangent.addData3f(1.0, 0.0, 0.0)
        #gvwbinormal.addData3f(0.0, 0.0, 1.0)
        #gvwcolor.addData4f(1.0, 1.0, 1.0, 1.0)
        #gvwtexcoord.addData2f(uv1[i], uv2[i])

    if isinstance(szext[0], float):
        gvwvertex.addData3f(szext[0], 0.0, szext[1])
        gvwvertex.addData3f(szext[2], 0.0, szext[1])
        gvwvertex.addData3f(szext[2], 0.0, szext[3])
        gvwvertex.addData3f(szext[0], 0.0, szext[3])
    else:
        gvwvertex.addData3f(szext[0][0], 0.0, szext[0][1])
        gvwvertex.addData3f(szext[1][0], 0.0, szext[1][1])
        gvwvertex.addData3f(szext[2][0], 0.0, szext[2][1])
        gvwvertex.addData3f(szext[3][0], 0.0, szext[3][1])
    gvwnormal.addData3f(0.0, 1.0, 0.0)
    gvwnormal.addData3f(0.0, 1.0, 0.0)
    gvwnormal.addData3f(0.0, 1.0, 0.0)
    gvwnormal.addData3f(0.0, 1.0, 0.0)
    gvwtangent.addData3f(1.0, 0.0, 0.0)
    gvwtangent.addData3f(1.0, 0.0, 0.0)
    gvwtangent.addData3f(1.0, 0.0, 0.0)
    gvwtangent.addData3f(1.0, 0.0, 0.0)
    gvwbinormal.addData3f(0.0, 0.0, 1.0)
    gvwbinormal.addData3f(0.0, 0.0, 1.0)
    gvwbinormal.addData3f(0.0, 0.0, 1.0)
    gvwbinormal.addData3f(0.0, 0.0, 1.0)
    gvwcolor.addData4f(1.0, 1.0, 1.0, alext[0])
    gvwcolor.addData4f(1.0, 1.0, 1.0, alext[1])
    gvwcolor.addData4f(1.0, 1.0, 1.0, alext[2])
    gvwcolor.addData4f(1.0, 1.0, 1.0, alext[3])
    if isinstance(uvext[0], float):
        gvwtexcoord.addData2f(uvext[0], uvext[1])
        gvwtexcoord.addData2f(uvext[2], uvext[1])
        gvwtexcoord.addData2f(uvext[2], uvext[3])
        gvwtexcoord.addData2f(uvext[0], uvext[3])
    else:
        gvwtexcoord.addData2f(uvext[0][0], uvext[0][1])
        gvwtexcoord.addData2f(uvext[1][0], uvext[1][1])
        gvwtexcoord.addData2f(uvext[2][0], uvext[2][1])
        gvwtexcoord.addData2f(uvext[3][0], uvext[3][1])

    gtris.addVertices(0, 1, 2)
    gtris.closePrimitive()
    gtris.addVertices(0, 2, 3)
    gtris.closePrimitive()

    geom = Geom(gvdata)
    geom.addPrimitive(gtris)
    gnode = GeomNode(name)
    gnode.addGeom(geom)

    return gnode


def make_quad (parent=None, pos=Point3(), hpr=Vec3(), size=(1.0, 1.0),
               texture=None, normalmap=None, glowmap=None, glossmap=None,
               shadowmap=None,
               twosided=False, clamp=True, filtr=True, transp=False):

    if isinstance(size, tuple):
        sizex, sizez = size
    else:
        sizex = sizez = size

    gnode = make_raw_quad(
        szext=(-0.5 * sizex, -0.5 * sizez, 0.5 * sizex, 0.5 *sizez))

    if parent is not None:
        node = parent.attachNewNode(gnode)
    else:
        node = NodePath(gnode)
    set_texture(node, texture=texture, normalmap=normalmap, glowmap=glowmap,
                glossmap=glossmap, shadowmap=shadowmap,
                clamp=clamp, filtr=filtr)
    node.setTwoSided(twosided)
    if transp:
        node.setTransparency(TransparencyAttrib.MAlpha)
    if isinstance(pos, VBase2):
        pos = Point3(pos[0], 0.0, pos[1])
    node.setPos(pos)
    node.setHpr(hpr)

    return node


_particles_cache = []

def fill_particles_cache (n):

    for i in range(n - len(_particles_cache)):
        p = Particles("particles")
        p.setPoolSize(1)
        _particles_cache.append(p)
    return len(_particles_cache)


def make_particles ():

    if not _particles_cache:
        fill_particles_cache(1)
    return _particles_cache.pop()


def make_quad_lattice (length, radius0, radius1, numquads,
                       slant=0.0,
                       uvext=(0.0, 0.0, 1.0, 1.0),
                       alext=(1.0, 1.0, 1.0, 1.0),
                       name="paddle"):

    #gvformat = GeomVertexFormat.getV3n3c4t2()
    gvformat = texfmt_tangspace()
    gvdata = GeomVertexData("data", gvformat, Geom.UHStatic)
    gvwvertex = GeomVertexWriter(gvdata, InternalName.getVertex())
    gvwnormal = GeomVertexWriter(gvdata, InternalName.getNormal())
    gvwtangent = GeomVertexWriter(gvdata, InternalName.getTangent())
    gvwbinormal = GeomVertexWriter(gvdata, InternalName.getBinormal())
    gvwcolor = GeomVertexWriter(gvdata, InternalName.getColor())
    gvwtexcoord = GeomVertexWriter(gvdata, InternalName.getTexcoord())
    gtris = GeomTriangles(Geom.UHStatic)

    if isinstance(uvext[0], float):
        uv1 = (uvext[0], uvext[2], uvext[2], uvext[0])
        uv2 = (uvext[1], uvext[1], uvext[3], uvext[3])
    else:
        uv1 = (uvext[0][0], uvext[1][0], uvext[2][0], uvext[3][0])
        uv2 = (uvext[0][1], uvext[1][1], uvext[2][1], uvext[3][1])

    rot_step = pi / numquads
    vind_off = 0
    for k in xrange(numquads):
        rot = rot_step * k
        srot = sin(rot)
        crot = cos(rot)
        ext = (0.5 * length) * sin(slant)
        extx = ext * -srot
        extz = ext * crot
        gvwvertex.addData3f(radius0 * crot - extx, 0.0, radius0 * srot - extz)
        gvwvertex.addData3f(radius1 * crot + extx, length, radius1 * srot + extz)
        gvwvertex.addData3f(radius1 * -crot + extx, length, radius1 * -srot + extz)
        gvwvertex.addData3f(radius0 * -crot - extx, 0.0, radius0 * -srot - extz)
        for i in xrange(4):
            gvwnormal.addData3f(-srot, 0.0, crot)
            gvwtangent.addData3f(0.0, 1.0, 0.0)
            gvwbinormal.addData3f(crot, 0.0, srot)
            gvwcolor.addData4f(1.0, 1.0, 1.0, alext[i])
            gvwtexcoord.addData2f(uv1[i], uv2[i])
        gtris.addVertices(vind_off + 0, vind_off + 1, vind_off + 2)
        gtris.closePrimitive()
        gtris.addVertices(vind_off + 0, vind_off + 2, vind_off + 3)
        gtris.closePrimitive()
        vind_off += 4

    geom = Geom(gvdata)
    geom.addPrimitive(gtris)
    gnode = GeomNode(name)
    gnode.addGeom(geom)

    node = NodePath(gnode)

    return node


_print_each_timers = {}

def print_each (handle, period, *args):

    tmspec = _print_each_timers.get(handle)
    if tmspec is None:
        tmspec = [0.0, period, 0.0]
        _print_each_timers[handle] = tmspec
    else:
        tmspec[1] = period
    time1 = base.global_clock.getLongTime()
    dt = time1 - tmspec[2]
    tmspec[2] = time1
    tmspec[0] -= dt
    if tmspec[0] <= 0:
        debug(1, (" ".join(["%s"] * len(args))) % tuple(args))
        tmspec[0] = tmspec[1]


def pos_from (body, pos):

    if isinstance(pos, VBase2):
        pos = Point3(pos[0], pos[1], 0.0)
    wpos = body.world.node.getRelativePoint(body.node, pos)
    return wpos


def vec_from (body, vec):

    if isinstance(vec, VBase2):
        vec = Vec3(vec[0], vec[1], 0.0)
    wpos = body.world.node.getRelativeVector(body.node, vec)
    return wpos


_relhpr_platform = NodePath("relhpr-platform")

def hpr_from (body, hpr):

    _relhpr_platform.reparentTo(body.node)
    _relhpr_platform.setHpr(hpr)
    whpr = _relhpr_platform.getHpr(body.world.node)
    _relhpr_platform.detachNode()
    return whpr


def hpr_from_to (body, pos):

    bpos = body.pos()
    wpos = pos_from(body, pos)
    dpos = bpos - wpos
    h = atan2(-dpos.getX(), dpos.getY())
    p = atan2(dpos.getZ(), dpos.getXy().length())
    r = 0.0
    return Vec3(degrees(h), degrees(p), degrees(r))


_relposhrz_platform = NodePath("relposhrz-platform")

def pos_from_horiz (body, pos, absz=False):

    twod = isinstance(pos, VBase2)
    bpos = body.pos()
    bhpr = body.hpr()
    _relposhrz_platform.reparentTo(body.world.node)
    _relposhrz_platform.setHpr(Vec3(bhpr[0], 0, 0))
    _relposhrz_platform.setPos(bpos)
    if twod:
        pos = Point3(pos[0], pos[1], 0.0)
    wpos = body.world.node.getRelativePoint(_relposhrz_platform, pos)
    _relposhrz_platform.detachNode()
    if absz:
        wpos[2] -= bpos[2]
    if twod:
        wpos = wpos.getXy()
    return wpos


def pos_from_point (pos, hpr, offset, absz=False):

    if isinstance(pos, VBase2):
        pos = Point3(pos[0], pos[1], 0.0)
    q = Quat()
    q.setHpr(hpr)
    if isinstance(offset, VBase2):
        offset = Point3(offset[0], offset[1], 0.0)
    opos = pos + Point3(q.xform(offset))
    if absz:
        opos[2] = offset[2]
    return opos


def hpr_from_hpr (hpr, offset):

    offvec = hprtovec(offset)
    q = Quat()
    q.setHpr(hpr)
    aoffvec = Vec3(q.xform(offvec))
    ahpr = vectohpr(aoffvec)
    return ahpr


def vec_from_horiz (body, vec):

    if isinstance(vec, VBase2):
        vec = Vec3(vec[0], vec[1], 0.0)
    bpos = body.pos()
    bhpr = body.hpr()
    _relposhrz_platform.reparentTo(body.world.node)
    _relposhrz_platform.setHpr(Vec3(bhpr[0], 0, 0))
    _relposhrz_platform.setPos(bpos)
    wpos = body.world.node.getRelativeVector(_relposhrz_platform, vec)
    _relposhrz_platform.detachNode()
    return wpos


def hpr_from_horiz (body, hpr):

    bhpr = body.hpr()
    wh = norm_ang(bhpr[0] + hpr[0], indeg=True)
    whpr = Vec3(wh, hpr[1], hpr[2])
    return whpr


def hpr_from_to_horiz (body, pos):

    bpos = body.pos()
    wpos = pos_from_horiz(body, pos)
    dpos = bpos - wpos
    h = atan2(-dpos.getX(), dpos.getY())
    p = atan2(dpos.getZ(), dpos.getXy().length())
    r = 0.0
    return Vec3(degrees(h), degrees(p), degrees(r))


def hpr_to (pos0, pos1):

    dpos = pos1 - pos0
    h = atan2(-dpos.getX(), dpos.getY())
    p = atan2(dpos.getZ(), dpos.getXy().length())
    r = 0.0
    return Vec3(degrees(h), degrees(p), degrees(r))


def pos_hpr_offcoord_towards_point (point, offx, offy, alt, offhdg=0.0):

    pos = Point3(point[0] + offx, point[1] + offy, alt)
    brng = degrees(atan2(-offx, offy))
    hdg = norm_ang(brng + 180 + offhdg, indeg=True)
    hpr = Vec3(hdg, 0.0, 0.0)
    return pos, hpr


def to_navhead (zhead):

    nhead = 360 - zhead
    while nhead < 0:
        nhead += 360
    while nhead >= 360:
        nhead -= 360
    return nhead


def to_navhead_rad (zhead):

    tau = 2 * pi
    nhead = tau - zhead
    while nhead < 0:
        nhead += tau
    while nhead >= tau:
        nhead -= tau
    return nhead


def intercept_time (tpos, tvel, tacc, ipos, ifvel, idvelp, ifacc, idaccp,
                    finetime=0.0, epstime=1e-3, maxiter=10):
    """
    Compute time to intercept.
    Object T is initially at tpos, has velocity tvel,
    and accelerates at constant rate tacc.
    Object I starts from ipos to intercept T, with initial velocity which is
    the sum of the fixed component ifvel and the component of magnitude idvelp
    in the unknown direction idir, and with constant acceleration which is
    the sum of the fixed component ifacc and the component of magnitude idaccp
    in the same unknown direction idir.
    First an approximate time to intercept is computed, such that
    higher order terms are neglected, but no iterative solving is needed.
    If the approximate time itime is smaller than finetime, iterative solving
    is performed to get a more accurate answer, either to within epstime
    or until maxiter iterations have been performed, whichever happens first.
    If I can intercept T according to approximate time computation,
    the time to intercept itime, the collision point cpos, and the unknown
    initial velocity/acceleration component direction idir are returned.
    If I cannot intercept T, None is returned.
    """

    itime = VBase2D(); cpos = Point3D(); idir = Vec3D()
    if intercept_time_s(tpos, tvel, tacc, ipos, ifvel, idvelp, ifacc, idaccp,
                        finetime, epstime, maxiter,
                        itime, cpos, idir):
        return itime[0], cpos, idir
    else:
        return None


# :also-compiled:
def intercept_time_s (tpos, tvel, tacc, ipos, ifvel, idvelp, ifacc, idaccp,
                      finetime, epstime, maxiter,
                      itime_, cpos_, idir_):

    # Approximate computation.
    dpos = tpos - ipos
    dvel = tvel - ifvel
    dacc = tacc - ifacc
    k0 = dpos.lengthSquared()
    k1 = 2 * dpos.dot(dvel)
    k2 = dvel.lengthSquared() - idvelp**2 + dpos.dot(dacc)
    if not solve_quad_minpos_s(k2, k1, k0, itime_):
        return False
    itime = itime_[0]

    # Accurate computation.
    if itime < finetime:
        k3 = dvel.dot(dacc) - idvelp * idaccp
        k4 = 0.25 * (dacc.lengthSquared() - idaccp**2)
        niter = 0
        it = itime
        # Fix-point with higher-order terms lumped into k0.
        dit = itime * 1e3
        ditp = itime * 2e3 # to detect divergence
        while dit > epstime and dit < ditp and niter < maxiter:
            niter += 1
            itp = it
            ditp = dit
            k0u = k0 + it**3 * (k3 + k4 * it)
            it = solve_quad_minpos(k2, k1, k0u)
            dit = abs(it - itp)
        if dit > ditp: # diverged
            it = itime
        #print ("--intercept-time  itime0=%.3f[s]  niter=%d  dctime=%.3f[s]"
               #% (itime, niter, (itime - it)))
        itime = it

    itimehsq = 0.5 * itime**2
    cpos = tpos + tvel * itime + tacc * itimehsq
    dcipos = cpos - ipos
    idir = ((dcipos - ifvel * itime - ifacc * itimehsq) /
            (idvelp * itime + idaccp * itimehsq))
    idir = ptov(unitv(idir))

    itime_[0] = itime
    cpos_.assign(cpos)
    idir_.assign(idir)
    return True


def max_intercept_range (tpos, tvel, ipos, idvelp, itime):
    """
    Compute maximum range at which the intercept is possible.
    Object T is initially at a range along the direction
    from ipos to tpos and travels with constant velocity tvel.
    Object I starts from ipos and travels at constant velocity
    of magnitude idvelp to intercept T.
    If there is no range of T at which I can intercept it within given time,
    None is returned.
    """

    tdir0 = tpos - ipos
    tdir0.normalize()
    a = -1.0; bu = 0.0; cu = 0.0
    for d in range(3):
        a += (tvel[d] / idvelp)**2
        bu += 2 * tdir0[d] * tvel[d] / idvelp**2
        cu += (tdir0[d] / idvelp)**2
    du = bu**2 - 4 * a * cu
    if du < 0.0:
        return None
    du2 = sqrt(du)
    rs = []
    if -bu - du2 != 0.0:
        r1 = itime * (2 * a) / (-bu - du2)
        rs.append(r1)
    if -bu + du2 != 0.0:
        r2 = itime * (2 * a) / (-bu + du2)
        rs.append(r2)
    rs = [r for r in rs if r >= 0.0]
    if not rs:
        return None
    return max(rs)


_non_alpha_rx = re.compile(r"\W", re.U)

def count_norm_words (text):

    words = [_non_alpha_rx.sub("", x) for x in text.split()]
    normtext = "".join(words)
    nwords = len(normtext) / 5.0
    return nwords


def reading_time (text, wpm=100, raw=False):

    nwords = count_norm_words(text)
    rtime = nwords / (wpm / 60.0)
    if not raw:
        rtime += 1.0 # in-out extra time
    return rtime


class SimpleProps (object):

    def __init__ (self, **kwargs):

        self.__dict__.update(kwargs)


    def __getitem__ (self, key):

        return self.__dict__[key]


    def __setitem__ (self, key, val):

        self.__dict__[key] = val


    def __contains__ (self, key):

        return key in self.__dict__


    def values (self):

        return self.__dict__.values()


    def get (self, key, defval=None):

        return self.__dict__.get(key, defval)


    def keys (self):

        return self.__dict__.keys()


    def items (self):

        return self.__dict__.items()


    def itervalues (self):

        for val in self.__dict__.itervalues():
            yield val


    def iterkeys (self):

        for key in self.__dict__.iterkeys():
            yield key


    def iteritems (self):

        for item in self.__dict__.iteritems():
            yield item


class AutoProps (object):

    reserved_attribs = frozenset(("__frozen", "__silent"))

    def __init__ (self, **kwargs):

        self.__dict__["__frozen"] = {}
        self.__dict__["__silent"] = True

        self.__dict__.update(kwargs)


    def set_silent (self, silent):

        self.__dict__["__silent"] = bool(silent)


    def __getattr__ (self, att):

        frozen = self.__dict__["__frozen"]
        ret = frozen.pop(att, None)
        if ret:
            if isinstance(ret, tuple):
                att2 = att
                valf, att = ret
                val = valf()
                for att1, val1 in zip(att, val):
                    self.__dict__[att1] = val1
                    if att2 == att1:
                        val2 = val1
                    else:
                        frozen.pop(att1)
                return val2
            else:
                valf = ret
                val = valf()
                self.__dict__[att] = val
                return val
        elif self.__dict__["__silent"]:
            return self.__dict__.get(att, None)
        else:
            return self.__dict__[att]


    def __setattr__ (self, att, val):

        frozen = self.__dict__["__frozen"]
        frozen.pop(att, None)
        self.__dict__[att] = val


    def update (self, props):

        if props is not None:
            for att, val in props:
                self.__setattr__(att, val)


    def set_from (self, other):

        for att in self.attribs():
            self.__setattr__(att, None)
        self.update(other.props())


    def freeze (self, att, valf):

        frozen = self.__dict__["__frozen"]
        if isinstance(att, tuple):
            for att1 in att:
                frozen[att1] = (valf, att)
                self.__dict__.pop(att1, None)
        else:
            frozen[att] = valf
            self.__dict__.pop(att, None)


    def __getitem__ (self, att):

        return self.__getattr__(att)


    def __setitem__ (self, att, val):

        return self.__setattr__(att, val)


    def __contains__ (self, att):

        return att in self.__dict__ or att in self.__frozen


    def attribs (self):

        frozen = self.__dict__["__frozen"]
        atts = set(self.__dict__.keys() + frozen.keys())
        atts.difference_update(AutoProps.reserved_attribs)
        return list(atts)


    def values (self):

        values = []
        for att in self.attribs():
            values.append(self.__getattr__(att))
        return values


    def props (self):

        props = []
        for att in self.attribs():
            props.append((att, self.__getattr__(att)))
        return props


    def __getstate__ (self):

        frozen = self.__dict__["__frozen"]
        if frozen:
            raise StandardError(
                "Cannot pickle when there are frozen properties.")

        return self.__dict__


    def __setstate__ (self, state):

        self.__dict__.update(state)


def segment_intersect_2d (a1, a2, b1, b2):

    # Intersect is at c = a1 + (a2 - a1) * ta = b1 + (b2 - b1) * tb,
    # where a1, a2, b1, b2 in R^2; ta, tb in [0, 1].
    xa1, ya1 = a1
    xa2, ya2 = a2
    xb1, yb1 = b1
    xb2, yb2 = b2
    d = (yb2 - yb1) * (xa2 - xa1) - (xb2 - xb1) * (ya2 - ya1)
    if d != 0.0:
        ta = ((xb2 - xb1) * (ya1 - yb1) - (yb2 - yb1) * (xa1 - xb1)) / d
        tb = ((xa2 - xa1) * (ya1 - yb1) - (ya2 - ya1) * (xa1 - xb1)) / d
        if 0.0 <= ta <= 1.0 and 0.0 <= tb <= 1.0:
            c = a1 + (a2 - a1) * ta
            #c = b1 + (b2 - b1) * tb
            return c
    return None


def line_intersect_2d (a0, da, b0, db, mults=False):

    # Intersect is at c = a0 + da * ta = b0 + db * tb,
    # where a0, b0, da, db in R^2; ta, tb in R.
    dxa, dya = da
    dxb, dyb = db
    d = dyb * dxa - dxb * dya
    if d != 0.0:
        xa0, ya0 = a0
        xb0, yb0 = b0
        ta = (dxb * (ya0 - yb0) - dyb * (xa0 - xb0)) / d
        if mults:
            tb = (dxa * (ya0 - yb0) - dya * (xa0 - xb0)) / d
        c = a0 + da * ta # = b0 + db * tb
        if not mults:
            return c
        else:
            return c, ta, tb
    return None


def vectohpr (vec):

    if isinstance(vec, VBase2):
        x, y = unitv(vec)
        z = 0.0
    else:
        x, y, z = unitv(vec)
    h = atan2(-x, y)
    p = asin(z)
    r = 0.0
    hpr = Vec3(*map(degrees, (h, p, r)))
    return hpr


# :also-compiled:
def hprtovec (hpr):

    q = Quat()
    q.setHpr(hpr)
    vec = Vec3(q.xform(Vec3(0, 1, 0)))
    vec.normalize()
    return vec


def randnormvec (vec):

    vec_u = unitv(vec)
    vec_t1 = type(vec)(1, 0, 0)
    vec_t2 = type(vec)(0, 1, 0)
    vec_t = vec_t1 if abs(vec_u.dot(vec_t1)) < abs(vec_u.dot(vec_t2)) else vec_t2
    vec_b = unitv(vec_u.cross(vec_t))
    ang = uniform(-pi, pi)
    vec_n = vec_b * cos(ang) + vec_u.cross(vec_b) * sin(ang)
    return vec_n


def randswivel (vec, minang, maxang):

    ang = uniform(minang, maxang)
    assert 0.0 <= ang < pi
    vec_t1 = type(vec)(0, 1, 0)
    vec_t2 = type(vec)(0, 0, 1)
    vec_t = vec_t1 if abs(vec_t1.dot(vec)) < abs(vec_t2.dot(vec)) else vec_t2
    vec_n = unitv(vec.cross(vec_t))
    ang_n = uniform(-pi, pi)
    vec_u = unitv(vec)
    vec_nr = vec_n * cos(ang_n) + vec_u.cross(vec_n) * sin(ang_n)
    vec_b = unitv(vec_u.cross(vec_nr))
    vec_r = vec * cos(ang) + vec_b.cross(vec) * sin(ang)
    return vec_r


def remove_subnodes (node, handles):

    for handle in handles:
        for geom in node.findAllMatches("**/%s" % handle):
            geom.removeNode()


def texture_subnodes (node, handles, texture,
                      normalmap=-1, glowmap=None, glossmap=None, shadowmap=None,
                      clamp=True, filtr=True, alpha=False):

    for handle in handles:
        for geom in node.findAllMatches("**/%s" % handle):
            if not geom.isEmpty():
                if alpha:
                    geom.setTransparency(TransparencyAttrib.MAlpha)
                set_texture(geom,
                            texture=texture, normalmap=normalmap,
                            glowmap=glowmap, glossmap=glossmap,
                            shadowmap=shadowmap,
                            clamp=clamp, filtr=filtr)


def radial_point_horiz (radius, heading, elevation):

    h = radians(heading)
    x = radius * -sin(h)
    y = radius * cos(h)
    z = elevation
    return Point3(x, y, z)


_lod_pexp_pvfovs = {
    1: (1.0, (0.0066, )),
    2: (0.8, (0.0500, 0.0040)),
    3: (0.5, (0.0200, 0.0066, 0.0013)),
    4: (0.5, (0.0200, 0.0066, 0.0013, 0.0002)),
    # (1.0, [0.1000, 0.0333, 0.0066, 0.0001])
    # (0.8, [0.0500, 0.0200, 0.0040, 0.0008])
    # (0.6, [0.0250, 0.0100, 0.0020, 0.0003])
    # (0.5, [0.0200, 0.0066, 0.0013, 0.0002])
}

def load_model_lod_chain (vfov, modelchain,
                          texture=None, normalmap=None,
                          glowmap=None, glossmap=None,
                          shadowmap=False,
                          clamp=True, filtr=True,
                          scale=None, pos=None, hpr=None,
                          rbcomb=False):

    lod = LODNode("lod-models")
    lodnd = NodePath(lod)
    models = []
    fardists = []
    neardist = 0.0
    modelchain = as_sequence(modelchain)
    pexp, pvfovs = _lod_pexp_pvfovs[len(modelchain)]
    for lv, modelspec in enumerate(modelchain):
        if isinstance(modelspec, tuple):
            modelpath, fardist = modelspec
        else:
            modelpath, fardist = modelspec, None
        model = load_model(modelpath,
                           texture, normalmap, glowmap, glossmap, shadowmap,
                           clamp, filtr,
                           scale, pos, hpr, rbcomb)
        models.append(model)
        if lv == 0:
            bmin, bmax = model.getTightBounds()
            bbox = bmax - bmin
            bcen = (bmin + bmax) * 0.5
        if fardist is None:
            if lv == 0:
                bbdiag = bbox.length()
                hrbbdiag = bbdiag**pexp * 0.5
            fardist = hrbbdiag / tan(0.5 * vfov * pvfovs[lv])
            #print ("--load-model-lod-chain  level=%d  diag=%.1f  fardist=%.0f"
                   #% (lv, bbdiag, fardist))
        #else:
            #print ("--load-model-lod-chain  level=%d  fardist=%.0f"
                   #% (lv, fardist))
        lod.addSwitch(fardist, neardist)
        model.reparentTo(lodnd)
        fardists.append(fardist)
        neardist = fardist

    return lodnd, models, fardists, bbox, bcen


def load_model (path,
                texture=None, normalmap=None,
                glowmap=None, glossmap=None,
                shadowmap=None,
                clamp=True, filtr=True,
                scale=None, pos=None, hpr=None,
                rbcomb=False):

    model = base.load_model("data", path)
    #model = model.getChild(0) # remove ModelRoot
    if rbcomb:
        rbc = RigidBodyCombiner("rbcombiner")
        rbcnp = NodePath(rbc)
        model.reparentTo(rbcnp)
        rbc.collect()
        model = rbcnp
    set_texture(model,
                texture=texture, normalmap=normalmap,
                glowmap=glowmap, glossmap=glossmap,
                shadowmap=shadowmap,
                clamp=clamp, filtr=filtr)
    if scale is not None:
        model.setScale(scale)
    if pos is not None:
        model.setPos(pos)
    if hpr is not None:
        model.setHpr(hpr)
    return model


def extract_model_lod_chain (topnode, subname,
                             texture=None, normalmap=None,
                             glowmap=None, glossmap=None,
                             shadowmap=None,
                             clamp=True, filtr=True):

    toplodnd = topnode.find("**/+LODNode")
    if not toplodnd.isEmpty():
        toplod = toplodnd.node()
        lod = LODNode("lod-models")
        lodnd = NodePath(lod)
        models = []
        fardists = []
        lv = 0
        toppos = Point3()
        tophpr = Vec3()
        bbox = Vec3()
        bcen = Point3()
        for toplv, topnd1 in enumerate(toplodnd.getChildren()):
            subnds = topnd1.findAllMatches("**/%s" % subname)
            if len(subnds) == 0:
                continue
            elif len(subnds) > 1:
                raise StandardError(
                    "More than one subnode with name '%s'." % subname)
            model = subnds[0]
            neardist = toplod.getOut(toplv)
            fardist = toplod.getIn(toplv)
            lod.addSwitch(fardist, neardist)
            models.append(model)
            fardists.append(fardist)
            if lv == 0:
                toppos = model.getPos(topnode)
                tophpr = model.getHpr(topnode)
                bmin, bmax = model.getTightBounds()
                bbox = bmax - bmin
                bcen = (bmin + bmax) * 0.5
            model.reparentTo(lodnd)
            set_texture(model,
                        texture=texture, normalmap=normalmap,
                        glowmap=glowmap, glossmap=glossmap,
                        shadowmap=shadowmap,
                        clamp=clamp, filtr=filtr)
            lv += 1
    else:
        raise StandardError(
            "Extracting model LOD chain from non-LOD node not implemented yet.")

    return lodnd, models, fardists, bbox, bcen, toppos, tophpr


# grad = planet_radius[m]
# gposN = (latitude_north[rad], longitude_east[rad], elevation_over_surface[m])
def great_circle_dist (grad, gpos1, gpos2):

    n1, e1, z1 = gpos1
    n2, e2, z2 = gpos2
    ca = (sin(n1) * sin(n2) + cos(n1) * cos(n2) * cos(e2 - e1))
    dist0 = acos(ca) * grad
    dist = sqrt(dist0**2 + (z2 - z1)**2)
    return dist


def hrmin_to_sec (hours, minutes):

    return hours * 3600.0 + minutes * 60.0


# f(0) = 0, f(1) = 1, f'(0..1) = 1, f(-inf..0) = 0, f(1..+inf) = 1
def intl01 (x):

    if 0.0 < x < 1.0:
        return x
    elif x <= 0.0:
        return 0.0
    else:
        return 1.0


def intl01r (x, x0, x1):

    return intl01((x - x0) / (x1 - x0))


#def intl01r (x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return u
    #elif u <= 0.0:
        #return 0.0
    #else:
        #return 1.0


def intl01v (x, y0, y1):

    return y0 + (y1 - y0) * x


def intl01vr (x, x0, x1, y0, y1):

    return intl01v(intl01r(x, x0, x1), y0, y1)


#def intl01vr (x, x0, x1, y0, y1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return y0 + (y1 - y0) * u
    #elif u < 1.0:
        #return y0
    #else:
        #return y1


def extl01vr (x, x0, x1, y0, y1):

    u = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * u


# f(0) = 1, f(1) = 0, f'(0..1) = -1, f(-inf..0) = 1, f(1..+inf) = 0
def intl10 (x):

    if 0.0 < x < 1.0:
        return 1.0 - x
    elif x <= 0.0:
        return 1.0
    else:
        return 0.0


def intl10r (x, x0, x1):

    return intl10((x - x0) / (x1 - x0))


#def intl10r (x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return 1.0 - u
    #elif u <= 0.0:
        #return 1.0
    #else:
        #return 0.0


# f(0) = 0, f(1) = 1, f'(0) = 0, f'(1) = 0, f'(0..1) >= 0,
# f(-inf..0) = 0, f(1..+inf) = 1
def intc01 (x):

    if 0.0 < x < 1.0:
        return 0.5 * (1.0 - cos(x * pi))
    elif x <= 0.0:
        return 0.0
    else:
        return 1.0


def intc01r (x, x0, x1):

    return intc01((x - x0) / (x1 - x0))


#def intc01r (x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return 0.5 * (1.0 - cos(u * pi))
    #elif u <= 0.0:
        #return 0.0
    #else:
        #return 1.0


def intc01v (x, y0, y1):

    return y0 + (y1 - y0) * x


def intc01vr (x, x0, x1, y0, y1):

    return intc01v(intc01r(x, x0, x1), y0, y1)


#def intc01vr (x, x0, x1, y0, y1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return y0 + (y1 - y0) * (0.5 * (1.0 - cos(u * pi)))
    #elif u < 1.0:
        #return y0
    #else:
        #return y1


# f(0) = 1, f(1) = 0, f'(0) = 0, f'(1) = 0, f'(0..1) <= 0,
# f(-inf..0) = 1, f(1..+inf) = 0
def intc10 (x):

    if 0.0 < x < 1.0:
        return 0.5 * (1.0 + cos(x * pi))
    elif x <= 0.0:
        return 1.0
    else:
        return 0.0


def intc10r (x, x0, x1):

    return intc10((x - x0) / (x1 - x0))


#def intc10r (x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #if 0.0 < u < 1.0:
        #return 0.5 * (1.0 + cos(u * pi))
    #elif u <= 0.0:
        #return 1.0
    #else:
        #return 0.0


# 0 < r < 1, f(0) = 0, f(1) = r, f(+inf) = 1, f'(0..+inf) > 0, f''(0..+inf) < 0
def int0r1 (r, x):

    return 1.0 - 1.0 / (1.0 + (r / (1.0 - r)) * x)


def int0r1r (r, x, x0, x1):

    return int0r1(r, (x - x0) / (x1 - x0))


#def int0r1r (r, x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #return 1.0 - 1.0 / (1.0 + (r / (1.0 - r)) * u)


def int0r1vr (r, x, x0, x1, y0, y1):

    return y0 + (y1 - y0) * int0r1(r, (x - x0) / (x1 - x0))


#def int0r1vr (r, x, x0, x1, y0, y1):

    #u = (x - x0) / (x1 - x0)
    #return y0 + (y1 - y0) * (1.0 - 1.0 / (1.0 + (r / (1.0 - r)) * u))


# 0 < r < 1, f(0) = 1, f(1) = r, f(+inf) = 0, f'(0..+inf) < 0, f''(0..+inf) > 0
def int1r0 (r, x):

    return 1.0 / (1.0 + ((1.0 - r) / r) * x)


def int1r0r (r, x, x0, x1):

    return int1r0(r, (x - x0) / (x1 - x0))


#def int1r0r (r, x, x0, x1):

    #u = (x - x0) / (x1 - x0)
    #return 1.0 / (1.0 + ((1.0 - r) / r) * u)


def get_cache_key_section (filepath, segmark):

    headst = "@cache-key-start:"
    headen = "@cache-key-end:"

    lines = open(real_path("data", filepath)).readlines()
    cklines = []
    inck = False
    for i, line in enumerate(lines):
        lno = i + 1
        if not inck:
            p = line.find(headst)
            if p >= 0 and line[p + len(headst):].strip() == segmark:
                inck = True
                #print "--cksec-10", "in", filepath, lno
        else:
            p = line.find(headen)
            if p >= 0 and line[p + len(headen):].strip() == segmark:
                inck = False
                #print "--cksec-20", "out", filepath, lno
            else:
                cklines.append(line)
    return "".join(cklines)


def key_to_hex (key, fckey=None):

    return md5("".join(map(repr, key)) +
               "".join(open(real_path("data", f), "rb").read()
                       for f in sorted(fckey or []))).hexdigest()


def read_cache_object (filepath, key, fckey=None):

    if not path_exists("cache", filepath):
        return None

    kfilepath = filepath + ".key"
    if not path_exists("cache", kfilepath):
        return None
    fh = open(real_path("cache", kfilepath), "rb")
    okeyhx = fh.read()
    fh.close()

    keyhx = key_to_hex(key, fckey)
    if keyhx != okeyhx:
        return None

    fh = open(real_path("cache", filepath), "rb")
    obj = pickle.load(fh)
    fh.close()
    return obj


def write_cache_object (obj, filepath, key, fckey=None):

    cdir = path_dirname(filepath)
    if not path_exists("cache", cdir):
        os.makedirs(real_path("cache", cdir))

    keyhx = key_to_hex(key, fckey)

    fh = open(real_path("cache", filepath), "wb")
    pickle.dump(obj, fh, -1)
    fh.close()

    kfilepath = filepath + ".key"
    fh = open(real_path("cache", kfilepath), "wb")
    fh.write(keyhx)
    fh.close()


def bin_view_b2f (node, camera):

    binval = -int(node.getPos(camera).getY())
    return binval


def show_raw_perf (start, duration, end=False, frames=False):

    wtyp = 1 if frames else 0

    @itertask
    def func (task):
        yield None, start, wtyp
        fs0 = base.global_clock.getFrameCount()
        ft0 = base.global_clock.getLongTime()
        yield None, duration, wtyp
        fs = base.global_clock.getFrameCount() - fs0 - 1
        ft = base.global_clock.getLongTime() - ft0
        dbgval(0, "perf",
               (fs, "%d", "frames"),
               (ft, "%5.1f", "time", "s"),
               (fs / ft, "%5.1f", "avg-rate", "1/s"),
               (ft / fs * 1000, "%5.2f", "avg-duration", "ms"))
        if end:
            exit(1)

    base.taskMgr.add(func, "raw-perf-loop")


def show_perf (world, start, duration, end=False, frames=False, fadeout=1.0):

    wtyp = 1 if frames else 0

    @itertask
    def func (task):
        yield world, start, wtyp
        fs0 = world.frame
        ft0 = world.wall_time
        yield world, duration, wtyp
        fs = world.frame - fs0 - 1
        ft = world.wall_time - ft0
        dbgval(0, "perf",
               (fs, "%d", "frames"),
               (ft, "%5.1f", "time", "s"),
               (fs / ft, "%5.1f", "avg-rate", "1/s"),
               (ft / fs * 1000, "%5.2f", "avg-duration", "ms"))
        if end:
            world.fade_out(fadeout)
            yield world, fadeout
            world.destroy()
            if world.mission:
                world.mission.end()
            else:
                exit(1)

    base.taskMgr.add(func, "perf-loop")


def v3t4 (v3, w=1.0):

    return Vec4(v3[0], v3[1], v3[2], w)


def set_particle_texture_noext (renderer, texpath, add=False):

    fulltexpath = texpath + ".png"
    file_found = False
    has_card = False
    if path_exists("data", fulltexpath):
        texture = base.load_texture("data", fulltexpath)
        if add:
            renderer.addTexture(texture)
        else:
            renderer.setTexture(texture)
        file_found = True
    else:
        for ext in ("bam", "egg", "egg.pz"):
            fulltexpath = texpath + "." + ext
            if path_exists("data", fulltexpath):
                texcard = base.load_model("data", fulltexpath)
                if add:
                    renderer.addFromNode(texcard)
                else:
                    renderer.setFromNode(texcard)
                file_found = True
                has_card = True
                break
    if texpath is None:
        raise StandardError(
            "No file found for requested texture '%s'." % texpath)
    return has_card


# Check if both 2D points b1 and b2 are on the same side
# of line through 2D points a1 and a2.
def _on_same_side (a1, a2, b1, b2):

    p1 = (b1[0] - a1[0]) * (a1[1] - a2[1]) + (b1[1] - a1[1]) * (a2[0] - a1[0])
    p2 = (b2[0] - a1[0]) * (a1[1] - a2[1]) + (b2[1] - a1[1]) * (a2[0] - a1[0])
    return p1 * p2 > 0


# Check if 2D segments (a1, a2) and (b1, b2) intersect.
def have_segment_intersect (a1, a2, b1, b2):

    return (not _on_same_side(a1, a2, b1, b2) and
            not _on_same_side(b1, b2, a1, a2))


# Check if 2D point a is inside 2D polygon p.
def is_inside_poly (p, a):

    # Select a point that is certainly outside of the polygon.
    c1 = min(p)
    c2 = max(p)
    ao = c1 + (c1 - c2)

    # Count intersections.
    num_point = len(p)
    num_isec = 0
    for i1 in xrange(num_point):
        i2 = (i1 + 1) % num_point
        if have_segment_intersect(a, ao, p[i1], p[i2]):
            num_isec += 1

    # If number of intersections is odd, the point is inside.
    inside = (num_isec % 2 == 1)

    return inside


# Check if 2D point a is inside 2D convex polygon p.
def is_inside_convex_poly (p, a):

    # The point is inside if it is on the same side of each segment.
    inside = True
    num_point = len(p)
    k = 0.0
    for i1 in xrange(num_point):
        i2 = (i1 + 1) % num_point
        dp12 = p[i2] - p[i1]
        dp1a = a - p[i1]
        k12 = dp12[0] * dp1a[1] - dp1a[0] * dp12[1]
        if k == 0.0:
            k = k12
        if k * k12 < 0.0:
            inside = False
            break

    return inside


def rotation_forward_up (fwdir0, updir0, fwdir1, updir1, neg=False):

    #updir0 = unitv(fwdir0.cross(updir0).cross(fwdir0))
    #updir1 = unitv(fwdir1.cross(updir1).cross(fwdir1))
    #fwdir0 = unitv(fwdir0)
    #fwdir1 = unitv(fwdir1)

    dfwdir = unitv(fwdir1 - fwdir0)
    dupdir = unitv(updir1 - updir0)
    axis = unitv(dfwdir.cross(dupdir))
    if axis.lengthSquared() < 0.5: # i.e. was zero on normalization
        axis = unitv(fwdir0 + updir0)
    afwdir0 = unitv(fwdir0 - axis * fwdir0.dot(axis))
    afwdir1 = unitv(fwdir1 - axis * fwdir1.dot(axis))
    fwang = afwdir0.signedAngleRad(afwdir1, axis)
    aupdir0 = unitv(updir0 - axis * updir0.dot(axis))
    aupdir1 = unitv(updir1 - axis * updir1.dot(axis))
    upang = aupdir0.signedAngleRad(aupdir1, axis)
    #angle = (fwang + upang) * 0.5
    angle = fwang if abs(fwang) < abs(upang) else upang

    if (angle >= 0.0 and neg) or (angle < 0.0 and not neg):
        angle *= -1
        axis *= -1

    return angle, axis


class TimeAveraged (object):

    def __init__ (self, period, zero):

        self._period = period
        self._zero = zero
        self.reset()


    def update (self, value, step):

        self._integral_step += step
        self._integral_sum += value * step
        self._average_value = self._integral_sum / self._integral_step
        # ...computed here, so that if the period is smaller than
        # the step, the average value is equal to the current value.
        self._value_track.append((value, step))
        while self._integral_step >= self._period and self._value_track:
            old_value, old_step = self._value_track.pop(0)
            self._integral_sum -= old_value * old_step
            self._integral_step -= old_step
        return self._average_value


    def current (self):

        return self._average_value


    def reset (self):

        self._value_track = []
        self._integral_sum = self._zero * 2.0 # to make a copy
        self._integral_step = 0.0
        self._average_value = self._zero * 2.0



_exp_drop_fac = 0.35

def explosion_dropoff (force, dist):

    damage = force - _exp_drop_fac * dist**2 # eq-exp
    damage = max(damage, 0.0)
    return damage


def explosion_reach (force):

    reach = sqrt(force / _exp_drop_fac) # from eq-exp == 0
    return reach


def vert_to_horiz_fov (vfov, ar):

    hfov = degrees(2 * atan(tan(radians(vfov) * 0.5) * ar))
    return hfov


# :also-compiled:
def texture_frame (texsplit, frind):
    """
    Compute texture frame data (u_offset, v_offset, u_span, v_span)
    for texsplit x texsplit grid of frames and given frame index frind.
    Frame indexing is row-wise, starting from top left corner.
    """

    dcoord = 1.0 / texsplit
    uind = frind % texsplit
    vind = frind // texsplit
    uoff = uind * dcoord
    voff = 1.0 - (vind + 1) * dcoord
    frame = Vec4(uoff, voff, dcoord, dcoord)
    return frame


# As WichmannHill in Python standard library,
# flattened and without bells and whistles.
# Here any negative number is used to request internal seed,
# instead of None, for compatibility with compiled version.
# :also-compiled:
class RandomBase (object):

    def __init__ (self, seed=-1):

        # long type needed due to multiplication of a.
        a = long(seed)
        if a < 0:
            from time import time
            a = long(time())
        a *= 256

        a, x = divmod(a, 30268)
        a, y = divmod(a, 30306)
        a, z = divmod(a, 30322)
        # long type removed because not needed for x, y, z,
        # and would slow down random() by about factor 2.
        self._xyz = (int(x) + 1, int(y) + 1, int(z) + 1)


    def random (self):

        x, y, z = self._xyz
        x = (171 * x) % 30269
        y = (172 * y) % 30307
        z = (170 * z) % 30323
        self._xyz = (x, y, z)

        r = (x / 30269.0 + y / 30307.0 + z / 30323.0) % 1.0
        return r


_global_rb = None

# :also-compiled:
def reset_random (seed=-1):

    global _global_rb
    if seed >= 0:
        _global_rb = RandomBase(seed)
    else:
        _global_rb = RandomBase()


_fx_global_rb = None

# :also-compiled:
def fx_reset_random (seed=-1):

    global _fx_global_rb
    if seed >= 0:
        _fx_global_rb = RandomBase(seed)
    else:
        _fx_global_rb = RandomBase()


# :also-compiled:
def randunit ():

    if _global_rb is None:
        raise StandardError("Random number generator not initialized.")
    r = _global_rb.random()
    return r


# :also-compiled:
def fx_randunit ():

    if _fx_global_rb is None:
        raise StandardError(
            "Random number generator for effects not initialized.")
    r = _fx_global_rb.random()
    return r


def _uniform_w (randunit, a, b):

    u = randunit()
    r = a + (b - a) * u
    return r


def _randrange_w (randunit, start, stop=None):

    u = randunit()
    if stop is None:
        r = int(u * start)
    else:
        r = int(start + u * (stop - start))
    return r


def _choice_w (randunit, seq):

    u = randunit()
    el = seq[int(u * len(seq))]
    return el


def _shuffle_w (randunit, seq):

    for i in reversed(xrange(1, len(seq))):
        u = randunit()
        j = int(u * (i + 1))
        seq[i], seq[j] = seq[j], seq[i]


def _randvec_w (uniform, minh, maxh, minp, maxp):

    h = uniform(minh, maxh)
    minz = sin(radians(minp))
    maxz = sin(radians(maxp))
    z = uniform(minz, maxz)
    p = degrees(asin(z))
    vec = hprtovec(Vec3(h, p, 0.0))
    return vec


def uniform (a, b):
    return _uniform_w(randunit, a, b)
def fx_uniform (a, b):
    return _uniform_w(fx_randunit, a, b)

def randrange (start, stop=None):
    return _randrange_w(randunit, start, stop)
def fx_randrange (start, stop=None):
    return _randrange_w(fx_randunit, start, stop)

def choice (seq):
    return _choice_w(randunit, seq)
def fx_choice (seq):
    return _choice_w(fx_randunit, seq)

def shuffle (seq):
    return _shuffle_w(randunit, seq)
def fx_shuffle (seq):
    return _shuffle_w(fx_randunit, seq)

# :also-compiled:
def randvec (minh=-180.0, maxh=180.0, minp=-90.0, maxp=90.0):
    return _randvec_w(uniform, minh, maxh, minp, maxp)
# :also-compiled:
def fx_randvec (minh=-180.0, maxh=180.0, minp=-90.0, maxp=90.0):
    return _randvec_w(fx_uniform, minh, maxh, minp, maxp)


class Random (object):

    def __init__ (self, seed=-1):

        self._rb = RandomBase(seed)


    def randunit (self):

        r = self._rb.random()
        return r


    def uniform (self, a, b):
        return _uniform_w(self.randunit, a, b)

    def randrange (self, start, stop=None):
        return _randrange_w(self.randunit, start, stop)

    def choice (self, seq):
        return _choice_w(self.randunit, seq)

    def shuffle (self, seq):
        return _shuffle_w(self.randunit, seq)

    def randvec (self, minh=-180.0, maxh=180.0, minp=-90.0, maxp=90.0):
        return _randvec_w(self.uniform, minh, maxh, minp, maxp)


# :also-compiled:
class NumRandom (object):

    def __init__ (self, seed=-1):

        self._rb = RandomBase(seed)


    def randunit (self):

        r = self._rb.random()
        return r


    def uniform (self, a, b):
        return _uniform_w(self.randunit, a, b)

    def randrange (self, start, stop=None):
        return _randrange_w(self.randunit, start, stop)

    def randvec (self, minh=-180.0, maxh=180.0, minp=-90.0, maxp=90.0):
        return _randvec_w(self.uniform, minh, maxh, minp, maxp)


# :also-compiled:
class HaltonDistrib (object):

    def __init__ (self, startind):

        self._index = startind


    @staticmethod
    def _get_r (base, i):

        r = 0.0
        f = 1.0 / base
        while i > 0:
            r += f * (i % base)
            i //= base
            f /= base
        return r


    def next1 (self):

        r1 = self._get_r(2, self._index)
        self._index += 1
        return r1


    def next2 (self):

        r1 = self._get_r(2, self._index)
        r2 = self._get_r(3, self._index)
        self._index += 1
        return VBase2(r1, r2)


    def next3 (self):

        r1 = self._get_r(2, self._index)
        r2 = self._get_r(3, self._index)
        r3 = self._get_r(5, self._index)
        self._index += 1
        return VBase3(r1, r2, r3)


from pandac.PandaModules import PTAInt
def enc_lst_int (lst):
    enc_lst = PTAInt()
    for el in lst:
        enc_lst.pushBack(el)
    return enc_lst
def dec_lst_int (enc_lst):
    lst = list(enc_lst)
    return lst

from pandac.PandaModules import PTAInt
def enc_lst_bool (lst):
    enc_lst = PTAInt()
    for el in lst:
        enc_lst.pushBack(el)
    return enc_lst
def dec_lst_bool (enc_lst):
    lst = map(bool, enc_lst)
    return lst

def enc_lst_string (lst):
    if lst:
        enc_lst = "\x04".join(lst) + "\x04"
    else:
        enc_lst = ""
    return enc_lst
def dec_lst_string (enc_lst):
    if enc_lst:
        return enc_lst[:-1].split("\x04")
    else:
        return []


if USE_COMPILED:
    from misc_c import *
