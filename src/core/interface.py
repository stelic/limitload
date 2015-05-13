# -*- coding: UTF-8 -*-

import os
import pickle

from direct.gui.DirectGui import DGG
from direct.gui.DirectGui import DirectButton
from direct.gui.DirectGui import DirectScrolledFrame
from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import VBase2, Point2, Point3
from pandac.PandaModules import NodePath

from src import real_path, internal_path, join_path
from src import path_exists, path_isfile, list_dir_files, list_dir_subdirs
from src.core.misc import rgba, reading_time, ui_font_path
from src.core.misc import get_pointer
from src.core.misc import itertask, kill_tasks
from src.core.misc import node_fade_to, node_slide_to, node_scale_to, node_swipe
from src.core.misc import make_text, update_text, font_scale_for_ptsize
from src.core.misc import make_text_page, HorizRule
from src.core.misc import make_frame, make_image
from src.core.misc import SimpleProps, AutoProps
from src.core.sound import Sound2D
from src.core.transl import *


MISSION_DIFFICULTY = SimpleProps(
    EASY="easy",
    HARD="hard",
    EXTREME="extreme",
)

MISSION_TYPE = SimpleProps(
    DOGFIGHT="dogfight",
    ATTACK="attack",
)

MISSION_DEBRIEFING = SimpleProps(
    SKIP="skip",
    EARLY="early",
    LATE="late",
)


class SimpleText (object):

    def __init__ (self, width=1.0, pos=Point2(),
                  font=None, size=10,
                  color=rgba(255, 255, 255, 1.0),
                  blcolor=rgba(255, 0, 0, 1.0),
                  align="l", anchor="tl", parent=None,
                  text="", duration=None, blink=0.0,
                  wpmspeed=100, textshader=None):

        if parent is not None:
            self.node = parent.attachNewNode("text-simple")
        else:
            self.node = NodePath("text-simple")
        self.node.hide()

        self._textnd = make_text(text=text, width=width,
                                 font=font, size=size, color=color,
                                 align=align, anchor=anchor,
                                 shader=textshader, parent=self.node)
        if isinstance(pos, VBase2):
            pos = Point3(pos[0], 0.0, pos[1])
        self._textnd.setPos(pos)

        self._color = color
        self._blcolors = [color, blcolor]

        if duration is None:
            duration = reading_time(text=text, wpm=wpmspeed)
        self._duration = duration
        self._blink = blink
        self._wpmspeed = wpmspeed

        if text:
            self._currtime = 0.0
        else:
            self._currtime = self._duration
        self._fadetime = 0.2
        self._blinktime = 0.0
        self._blcolind = 0

        self.alive = True
        base.taskMgr.add(self._loop, "textsimple-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = base.global_clock.getDt()

        if self._currtime < self._duration:

            if self._currtime < self._fadetime:
                alpha = self._currtime / self._fadetime
            elif self._currtime < self._duration - self._fadetime:
                alpha = 1.0
            else:
                alpha = (self._duration - self._currtime) / self._fadetime
            self._currtime += dt

            if self._blink:
                if self._blinktime >= self._blink:
                    self._blcolind = (self._blcolind + 1) % len(self._blcolors)
                    update_text(self._textnd,
                                color=self._blcolors[self._blcolind])
                    self._blinktime = self._blinktime - self._blink
                self._blinktime += dt

        else:
            alpha = 0.0

        if alpha > 0.0:
            if self.node.isHidden():
                self.node.show()
            self.node.setSa(alpha)
        else:
            if not self.node.isHidden():
                self.node.hide()

        return task.cont


    def show (self, text, duration=None, blink=0.0):

        update_text(self._textnd, text=text)
        if duration is None:
            duration = reading_time(text=text, wpm=self._wpmspeed)
        if self.node.isHidden():
            self._duration = duration
            self._currtime = 0.0
        else:
            self._duration = self._currtime + duration
        self._blink = blink


class BubbleText (object):

    def __init__ (self, width=1.0, height=None, pos=Point2(),
                  font=None, size=10, color=rgba(255, 255, 255, 1.0),
                  framebase=None, framesize=0.05,
                  parent=None,
                  text="", duration=None, wpmspeed=100, textshader=None):

        if parent is not None:
            self.node = parent.attachNewNode("text-float")
        else:
            self.node = NodePath("text-float")
        if isinstance(pos, VBase2):
            pos = Point3(pos[0], 0.0, pos[1])
        self.node.setPos(pos)

        self._textnd = make_text(text=text, width=width,
                                 font=font, size=size, color=color,
                                 align="l", anchor="tc",
                                 shader=textshader, parent=self.node)
        self._textnd.hide()
        if height is None:
            bmin, bmax = self._textnd.getTightBounds()
            height = bmax[2] - bmin[2]

        if framebase:
            self._framend = make_frame(framebase, framesize, width, height,
                                       filtr=False,
                                       name="text-frame", parent=self.node)
            self._framend.setPos(0.0, 0.0, -0.5 * height)
            self._framend.setScale(1e-5) # not zero, would be singular
            self._textnd.reparentTo(self.node) # to come in front
        else:
            self._framend = None

        self._scale = 1e-5 # not zero, would be singular
        self._scaling_time = 0.3

        self._ctext = ""
        self._cduration = 0.0
        self._cwpmspeed = wpmspeed
        self._nexttexts = []
        if text:
            self._nexttexts.append((text, duration))

        self.alive = True
        base.taskMgr.add(self._loop, "textfloat-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = base.global_clock.getDt()

        if self._cduration > 0.0 or self._nexttexts:
            if self._scale == 1.0:
                self._cduration -= dt
            if self._cduration <= 0.0:
                if self._nexttexts:
                    text, duration = self._nexttexts.pop(0)
                    if duration is None:
                        duration = reading_time(text=text, wpm=self._cwpmspeed)
                    if self._ctext:
                        self._ctext += "\n"
                    self._ctext += text
                    self._cduration = duration
                    update_text(self._textnd, text=self._ctext)
                else:
                    self._ctext = ""
                    self._cduration = 0.0

        if self._ctext and self._scale < 1.0:
            self._scale += (1.0 / self._scaling_time) * dt
            if self._scale > 1.0:
                self._scale = 1.0
        elif not self._ctext and self._scale > 0.0:
            self._scale -= (1.0 / self._scaling_time) * dt
            if self._scale < 0.0:
                self._scale = 1e-5 # not zero, would be singular
        if self._framend is not None:
            self._framend.setScale(self._scale)

        if self._scale < 1.0:
            self._textnd.hide()
        else:
            self._textnd.show()

        return task.cont


    def add (self, text, duration=None):

        self._nexttexts.append((text, duration))


class Button (object):

    def __init__ (self,
                  basetext=None, clicktext=None, overtext=None, disbtext=None,
                  baseframe=None, clickframe=None, overframe=None, disbframe=None,
                  textfont=ui_font_path, textcolor=rgba(255, 255, 255, 1.0),
                  textsize=10, textpos=Point2(),
                  clicksound=None, oversound=None,
                  clickf=None,
                  parent=None, pos=Point2()):

        if not baseframe and not basetext:
            raise StandardError(
                "Requested button with no text and no frame.")

        if parent is None:
            parent = NodePath("button")

        blanktext = ""
        text = (
            basetext or blanktext,
            clicktext or basetext or blanktext,
            overtext or basetext or blanktext,
            disbtext or basetext or blanktext,
        )

        if baseframe:
            make_frame_1 = lambda *args: make_frame(*args, filtr=False)
            basegeom = make_frame_1(*baseframe)
            geom = (
                basegeom,
                make_frame_1(*clickframe) if clickframe else basegeom,
                make_frame_1(*overframe) if overframe else basegeom,
                make_frame_1(*disbframe) if disbframe else basegeom,
            )
        else:
            geom = None

        if isinstance(textfont, basestring):
            textfont = base.load_font("data", textfont)
        textscale = font_scale_for_ptsize(textsize)
        if isinstance(textpos, VBase2):
            textpos = Point3(textpos[0], 0.0, textpos[1])
        textpos = (textpos[0], textpos[2])

        if isinstance(clicksound, basestring):
            clicksound = base.load_sound("data", clicksound)
        if isinstance(oversound, basestring):
            oversound = base.load_sound("data", oversound)
        if isinstance(pos, VBase2):
            pos = Point3(pos[0], 0.0, pos[1])

        self._button = DirectButton(
            text=text, text_font=textfont, text_fg=textcolor,
            text_scale=textscale, text_pos=textpos,
            geom=geom,
            clickSound=clicksound, rolloverSound=oversound,
            pos=pos,
            relief=None, pressEffect=0,
            parent=parent,
            command=clickf)


    def disable (self):

        self._button["state"] = DGG.DISABLED
        self._button.setSa(0.3)


    def enable (self):

        self._button["state"] = DGG.NORMAL
        self._button.setSa(1.0)



class MainLargeButton (Button):

    def __init__ (self, basetext, clicktext=None, overtext=None, disbtext=None,
                  clickf=None, parent=None, pos=Point2()):

        fs = 0.04; fw = 0.52; fh = 0.08
        Button.__init__(self,
            basetext=basetext, clicktext=clicktext,
            overtext=overtext, disbtext=disbtext,
            baseframe=("images/ui/textfloat02", fs, fw, fh),
            clickframe=None,
            overframe=("images/ui/textfloat02",
                       fs * 1.4, fw - 0.4 * fs, fh - 0.4 * fs),
            disbframe=None,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=22,
            textpos=Point2(0.0, -0.017),
            clicksound="audio/sounds/button-click.ogg",
            oversound=None,
            clickf=clickf,
            parent=parent,
            pos=pos)


class MainSmallButton (Button):

    def __init__ (self, basetext, clicktext=None, overtext=None, disbtext=None,
                  clickf=None, parent=None, pos=Point2()):

        fs = 0.04; fw = 0.40; fh = 0.04
        Button.__init__(self,
            basetext=basetext, clicktext=clicktext,
            overtext=overtext, disbtext=disbtext,
            baseframe=("images/ui/textfloat02", fs, fw, fh),
            clickframe=None,
            overframe=("images/ui/textfloat02",
                       fs * 1.4, fw - 0.4 * fs, fh - 0.4 * fs),
            disbframe=None,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=16,
            textpos=Point2(0.0, -0.013),
            clicksound="audio/sounds/button-click.ogg",
            oversound=None,
            clickf=clickf,
            parent=parent,
            pos=pos)


class MissionButton (Button):

    def __init__ (self, basetext, clicktext=None, overtext=None, disbtext=None,
                  clickf=None, parent=None, pos=Point2()):

        fs = 0.02; fw = 0.4; fh = 0.04
        Button.__init__(self,
            basetext=basetext, clicktext=clicktext,
            overtext=overtext, disbtext=disbtext,
            baseframe=("images/ui/textfloat02", fs, fw, fh),
            clickframe=None,
            overframe=("images/ui/textfloat02",
                       fs * 1.4, fw - 0.4 * fs, fh - 0.4 * fs),
            disbframe=None,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=14,
            textpos=Point2(0.0, -0.013),
            clicksound="audio/sounds/button-click.ogg",
            oversound=None,
            clickf=clickf,
            parent=parent,
            pos=pos)


class SequenceButton (Button):

    def __init__ (self, basetext, clicktext=None, overtext=None, disbtext=None,
                  clickf=None, parent=None, pos=Point2()):

        fs = 0.04; fw = 0.4; fh = 0.03
        Button.__init__(self,
            basetext=basetext, clicktext=clicktext,
            overtext=overtext, disbtext=disbtext,
            baseframe=("images/ui/textfloat02", fs, fw, fh),
            clickframe=None,
            overframe=("images/ui/textfloat02",
                       fs * 1.4, fw - 0.4 * fs, fh - 0.4 * fs),
            disbframe=None,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=14,
            textpos=Point2(0.0, -0.013),
            clicksound="audio/sounds/button-click.ogg",
            oversound=None,
            clickf=clickf,
            parent=parent,
            pos=pos)


class ScrollText (object):

    def __init__ (self, size,
                  text="",
                  textfont=ui_font_path, textcolor=rgba(255, 255, 255, 1.0),
                  textsize=10,
                  caption=None, para_spacing=0.5,
                  line_width=0.005, rule_length=0.5,
                  parent=None, pos=Point2()):

        top = NodePath("scroll-text")
        if parent is not None:
            top.reparentTo(parent)

        frame_width, frame_height = size
        line_height = font_scale_for_ptsize(textsize) * 1.2

        scbar_width = 0.04
        border_size = 0.04
        scbar_outer_width = scbar_width * 2.0

        if caption is not None:
            ctextsize = textsize * 1.5
            make_text(
                caption,
                width=frame_width,
                pos=Point2(pos[0] - 0.5 * frame_width,
                           pos[1] + 0.5 * frame_height + 1.0 * border_size),
                size=ctextsize, font=textfont,
                color=textcolor,
                align="l", anchor="bl", wrap=False,
                smallcaps=True,
                parent=top)

        frame_base_geom = make_frame(
            imgbase="images/ui/textfloat03", imgsize=border_size,
            width=frame_width, height=frame_height, filtr=False)
        frame_geom = (frame_base_geom,) * 4

        scbt_size = scbar_width * 2
        scbtinc_base_geom = make_image("images/ui/scroll_button_inc.png",
                                       size=scbt_size, filtr=False)
        scbtinc_geom = (scbtinc_base_geom,) * 4
        scbtdec_base_geom = make_image("images/ui/scroll_button_dec.png",
                                       size=scbt_size, filtr=False)
        scbtdec_geom = (scbtdec_base_geom,) * 4
        thumb_base_geom = make_image("images/ui/scroll_thumb.png",
                                     size=scbt_size, filtr=False)
        thumb_geom = (thumb_base_geom,) * 4

        text_width = frame_width - border_size - scbar_width
        text_height = frame_height

        frame_size = (-0.5 * frame_width, 0.5 * frame_width + scbar_outer_width,
                      -0.5 * frame_height, 0.5 * frame_height)
        bg_color = rgba(0, 0, 0, 0.0)
        canvas_size = (-0.5 * frame_width, -0.5 * frame_width + text_width,
                       0.5 * frame_height - text_height, 0.5 * frame_height)
        self._frame = DirectScrolledFrame(
            frameSize=frame_size,
            canvasSize=canvas_size,
            manageScrollBars=True,
            autoHideScrollBars=True,
            scrollBarWidth=scbar_width,
            frameColor=bg_color,
            geom=frame_geom,
            verticalScroll_scrollSize=line_height,
            verticalScroll_relief=None,
            verticalScroll_incButton_geom=scbtinc_geom,
            verticalScroll_incButton_relief=None,
            verticalScroll_decButton_geom=scbtdec_geom,
            verticalScroll_decButton_relief=None,
            verticalScroll_resizeThumb=False,
            verticalScroll_thumb_relief=None,
            verticalScroll_thumb_geom=thumb_geom,
            verticalScroll_frameColor=rgba(255, 0, 0, 1.0),
            pos=Point3(pos[0], 0.0, pos[1]),
            parent=top)
        cnode = self._frame.getCanvas()

        self._no_desc_node = make_text(
            text=_("NO DATA"),
            width=text_width,
            pos=pos,
            size=(textsize * 1.5), font=ui_font_path,
            color=rgba(255, 0, 0, 1.0),
            align="c", anchor="mc",
            parent=top)

        self._frame_width = frame_width
        self._frame_height = frame_height
        self._text_width = text_width
        self._text_size = textsize
        self._text_color = textcolor
        self._font_path = ui_font_path

        self._text_node = None
        self._cached_text_nodes = {}
        self._text_node_cached = False

        self._para_spacing = para_spacing
        self._line_width = line_width
        self._rule_length = rule_length

        self.cache_texts([""])
        self.set_text(text)


    def set_text (self, text):

        if text is None:
            text = ""
        elif isinstance(text, list):
            text = tuple(text)
        if self._text_node is not None:
            if self._text_node_cached:
                self._text_node.detachNode()
            else:
                self._text_node.removeNode()
        cached_text_node = self._cached_text_nodes.get(text)
        if cached_text_node is None:
            self._text_node = self._make_text_node(text)
            self._text_node_cached = False
        else:
            self._text_node = cached_text_node
            self._text_node_cached = True
        self._text_node.reparentTo(self._frame.getCanvas())
        text_height = self._text_node.getPythonTag("height")
        canvas_size = (-0.5 * self._frame_width,
                       -0.5 * self._frame_width + self._text_width,
                       0.5 * self._frame_height - text_height,
                       0.5 * self._frame_height)
        self._frame["canvasSize"] = canvas_size
        if text:
            self._no_desc_node.hide()
        else:
            self._no_desc_node.show()


    def cache_texts (self, texts):

        for text in texts:
            if isinstance(text, list):
                text = tuple(text)
            if text not in self._cached_text_nodes:
                text_node = self._make_text_node(text)
                self._cached_text_nodes[text] = text_node


    def _make_text_node (self, text):

        text_node = make_text_page(text,
            width=self._text_width, font=self._font_path,
            size=self._text_size, color=self._text_color,
            page_width=self._frame_width,
            page_height=self._frame_height,
            para_spacing=self._para_spacing,
            line_width=self._line_width,
            rule_length=self._rule_length)
        return text_node


class ScrollTable (object):

    def __init__ (self, colspec, rowdata, size,
                  textfont=ui_font_path, textcolor=rgba(255, 255, 255, 1.0),
                  textsize=10, notetextsize=8,
                  caption=None, sortcol=0, noclicksort=False, switchf=None,
                  noheader=False, multitable=False,
                  parent=None, pos=Point2()):

        top = NodePath("scroll-frame")
        if parent is not None:
            top.reparentTo(parent)

        self._multitable = multitable
        self._switchf = switchf

        tnode = NodePath("scroll-table")
        twidth, theight = size
        base_height = font_scale_for_ptsize(textsize)
        row_height = base_height * 1.2
        self._size = size
        self._row_height = row_height

        num_col = len(colspec)

        scbar_width = 0.04
        border_size = 0.04
        scbar_outer_width = scbar_width * 2.0
        cwpad = 0.02

        if caption is not None:
            ctextsize = textsize * 1.5
            make_text(
                text=caption,
                width=twidth,
                pos=Point2(pos[0] - 0.5 * twidth,
                           pos[1] + 0.5 * theight + 1.0 * border_size),
                size=ctextsize, font=textfont,
                color=textcolor,
                align="l", anchor="bl", wrap=False,
                smallcaps=True,
                parent=top)

        if isinstance(pos, VBase2):
            pos = Point3(pos[0], 0.0, pos[1])

        if not noheader:
            header_height = row_height
        else:
            header_height = 0.0

        self._textcolor = textcolor

        dimcolor = textcolor * 0.5
        dimcolor[3] = textcolor[3]
        self._dimcolor = dimcolor

        bt_geom_base = make_image("images/ui/white.png", size=base_height)
        bt_geom_base.setSa(0.0)
        bt_geom = (bt_geom_base,) * 4

        self._tables = []

        def make_entry_bt (k, i, z, mldh=0.0):
            table = self._tables[k]
            return DirectButton(
                frameSize=(-0.5 * twidth, 0.5 * twidth,
                           -0.5 * base_height - mldh, 0.5 * base_height),
                geom=bt_geom,
                clickSound=None,
                rolloverSound=None,
                pos=Point3(0.0, 0.0, z),
                relief=None,
                pressEffect=0,
                command=self._make_row_command(k, i),
                parent=table.top_node)

        if multitable:
            multi_row_data = rowdata
        else:
            multi_row_data = [rowdata]
        for k, row_data_1 in enumerate(multi_row_data):
            table = SimpleProps(
                rows=[],
                top_node=None,
                accu_cheight=0.0,
                accu_cwidth=0.0,
                prev_hlt_index=None,
            )
            self._tables.append(table)
            table.top_node = tnode.attachNewNode("table-%d" % k)
            table.top_node.hide()
            num_row_1 = len(row_data_1)
            for i in xrange(num_row_1):
                row = SimpleProps(
                    node=None,
                    button=None,
                    text_nodes=[],
                    z_position=None,
                    text_data=[],
                    sort_data=[],
                    note_data=[],
                )
                table.rows.append(row)
                for j in xrange(num_col):
                    datum = row_data_1[i][j]
                    if isinstance(datum, tuple):
                        if len(datum) == 3:
                            text_datum, sort_datum, note_datum = datum
                        elif len(datum) == 2:
                            text_datum, sort_datum = datum
                            note_datum = None
                        else:
                            text_datum = sort_datum = datum
                            note_datum = None
                    else:
                        text_datum = sort_datum = datum
                        note_datum = None
                    row.text_data.append(text_datum)
                    row.sort_data.append(sort_datum)
                    row.note_data.append(note_datum)

            table.accu_cheight = header_height
            table.accu_cwidth = twidth
            textscale = font_scale_for_ptsize(textsize)
            for i in xrange(num_row_1):
                row = table.rows[i]
                tnds = []
                maxmldh = 0.0
                for j in xrange(num_col):
                    cwidth = colspec[j][1] * twidth
                    cwrap = colspec[j][2] if len(colspec[j]) > 2 else False
                    tnd = make_text(
                        text=row.text_data[j],
                        width=(cwidth - cwpad),
                        size=textsize, font=textfont,
                        color=dimcolor,
                        align="l", anchor="tl", wrap=cwrap)
                    tnds.append(tnd)
                    tbh = tnd.getPythonTag("heightbase")
                    th = tnd.getPythonTag("height")
                    mldh = th - tbh
                    if row.note_data[j] is not None:
                        indw = textscale * 1.0
                        nnd = make_text(
                            text=row.note_data[j],
                            width=(cwidth - cwpad - indw),
                            size=notetextsize, font=textfont,
                            color=dimcolor,
                            align="l", anchor="tl", wrap=cwrap)
                        nh = nnd.getPythonTag("height")
                        nnd.reparentTo(tnd)
                        nnd.setPos(indw, 0.0, -th)
                        mldh += nh
                    maxmldh = max(maxmldh, mldh)
                bt_z = 0.5 * theight - table.accu_cheight - 0.5 * base_height
                row.z_position = bt_z
                row.button = make_entry_bt(k, i, bt_z, maxmldh)
                row.node = row.button
                table.accu_cwidth = 0.0
                for j, tnd in enumerate(tnds):
                    cwidth = colspec[j][1] * twidth
                    tnd.reparentTo(row.node)
                    tnd.setPos(-0.5 * twidth + table.accu_cwidth, 0.0,
                               0.5 * base_height)
                    row.text_nodes.append(tnd)
                    table.accu_cwidth += cwidth
                table.accu_cheight += row_height + maxmldh

        frame_base_geom = make_frame(
            imgbase="images/ui/textfloat03", imgsize=border_size,
            width=twidth, height=theight, filtr=False)
        frame_geom = (frame_base_geom,) * 4

        scbt_size = scbar_width * 2
        scbtinc_base_geom = make_image("images/ui/scroll_button_inc.png",
                                       size=scbt_size, filtr=False)
        scbtinc_geom = (scbtinc_base_geom,) * 4
        scbtdec_base_geom = make_image("images/ui/scroll_button_dec.png",
                                       size=scbt_size, filtr=False)
        scbtdec_geom = (scbtdec_base_geom,) * 4
        thumb_base_geom = make_image("images/ui/scroll_thumb.png",
                                     size=scbt_size, filtr=False)
        thumb_geom = (thumb_base_geom,) * 4

        frame_size = (-0.5 * twidth, 0.5 * twidth + scbar_outer_width,
                      -0.5 * theight, 0.5 * theight)
        bg_color = rgba(0, 0, 0, 0.0)
        canvas_size = (-0.5 * twidth, 0.5 * twidth,
                       -0.5 * theight, 0.5 * theight)
        self._frame = DirectScrolledFrame(
            frameSize=frame_size,
            canvasSize=canvas_size,
            manageScrollBars=True,
            autoHideScrollBars=True,
            scrollBarWidth=scbar_width,
            frameColor=bg_color,
            geom=frame_geom,
            verticalScroll_scrollSize=row_height,
            verticalScroll_relief=None,
            verticalScroll_incButton_geom=scbtinc_geom,
            verticalScroll_incButton_relief=None,
            verticalScroll_decButton_geom=scbtdec_geom,
            verticalScroll_decButton_relief=None,
            verticalScroll_resizeThumb=False,
            verticalScroll_thumb_relief=None,
            verticalScroll_thumb_geom=thumb_geom,
            verticalScroll_frameColor=rgba(255, 0, 0, 1.0),
            pos=pos,
            parent=top)
        cnode = self._frame.getCanvas()
        tnode.reparentTo(cnode)

        if not noheader:
            def make_header_bt (i, width, pos):
                if not noclicksort:
                    def cmdf ():
                        if self._sort_column == i:
                            self._sort_descending[i] = not self._sort_descending[i]
                        else:
                            self._sort_descending[i] = False
                        self._sort_column = i
                        self._sort_by_column(i, self._sort_descending[i])
                else:
                    cmdf = None
                return DirectButton(
                    frameSize=(0.0, cwidth, -base_height, 0.0),
                    geom=bt_geom,
                    clickSound=None,
                    rolloverSound=None,
                    pos=Point3(pos[0], 0.0, pos[1]),
                    relief=None,
                    pressEffect=0,
                    command=cmdf,
                    parent=top)

            img = make_image(
                "images/ui/white.png",
                size=(twidth, 1.2 * row_height),
                pos=Point2(pos[0], pos[2] + 0.5 * theight - 0.4 * row_height),
                filtr=False, parent=top)
            img.setColor(rgba(0, 0, 0, 1.0))
            accu_cwidth = 0.0
            for i in xrange(num_col):
                cname, rcwidth = colspec[i][:2]
                cwidth = rcwidth * twidth
                hdr_pos = Point2(pos[0] - 0.5 * twidth + accu_cwidth,
                                 pos[2] + 0.5 * theight)
                make_header_bt(i, cwidth, hdr_pos)
                make_text(
                    text=cname,
                    width=(cwidth - cwpad),
                    pos=hdr_pos,
                    size=textsize, font=textfont,
                    color=textcolor,
                    align="l", anchor="tl", wrap=False,
                    smallcaps=True, underscore=True,
                    parent=top)
                accu_cwidth += cwidth

        self._sort_column = sortcol
        self._sort_descending = [False] * num_col
        self._sort_by_column(sortcol, self._sort_descending[sortcol])

        self._current_table_index = -1
        self.switch_table(0)


    def _highlight_row (self, k, i):

        table = self._tables[k]
        if table.prev_hlt_index is not None:
            for tnd in table.rows[table.prev_hlt_index].text_nodes:
                update_text(tnd, color=self._dimcolor)
        for tnd in table.rows[i].text_nodes:
            update_text(tnd, color=self._textcolor)
        table.prev_hlt_index = i


    def _make_row_command (self, k, i):

        if self._switchf is not None:
            cmd = lambda: (self._highlight_row(k, i),
                           (self._switchf(k, i) if self._multitable
                            else self._switchf(i)))
        else:
            cmd = lambda: (self._highlight_row(k, i), None)
        return cmd


    def _sort_by_column (self, sortcol, descending=False, k=None):

        if sortcol < 0:
            return
        if k is not None:
            tables = [self._tables[k]]
        else:
            tables = self._tables
        for table in tables:
            i_sc = sortcol
            sort_map = [ir[0] for ir in sorted(
                enumerate(row.sort_data for row in table.rows),
                key=lambda e: [e[1][i_sc]] + e[1][:i_sc] + e[1][i_sc + 1:])]
            if descending:
                sort_map = reversed(sort_map)
            for i_sorted, i_base in enumerate(sort_map):
                z = table.rows[i_sorted].z_position
                table.rows[i_base].node.setPos(0.0, 0.0, z)


    def delete_row (self, i):

        k = self._current_table_index
        table = self._tables[k]
        if table.prev_hlt_index == i:
            table.prev_hlt_index = None
        for i_n in xrange(i + 1, len(table.rows)):
            if table.prev_hlt_index == i_n:
                table.prev_hlt_index -= 1
            row = table.rows[i_n]
            row.node.setPos(row.node.getPos() +
                            Point3(0.0, 0.0, self._row_height))
            row.z_position += self._row_height
            row.button["command"] = self._make_row_command(k, i_n - 1)
        table.rows[i].node.removeNode()
        table.rows.pop(i)

        self._sort_by_column(self._sort_column,
                             self._sort_descending[self._sort_column],
                             k)

        self._update_canvas(k)


    def switch_table (self, k):

        if k == self._current_table_index:
            return

        k_prev = self._current_table_index
        if 0 <= k_prev < len(self._tables):
            table = self._tables[k_prev]
            table.top_node.hide()
            if table.prev_hlt_index is not None:
                for tnd in table.rows[table.prev_hlt_index].text_nodes:
                    update_text(tnd, color=self._dimcolor)
                table.prev_hlt_index = None

        self._update_canvas(k)

        self._current_table_index = k


    def _update_canvas (self, k):

        twidth, theight = self._size
        if 0 <= k < len(self._tables):
            table = self._tables[k]
            table.top_node.show()
            canvas_size = (-0.5 * twidth, -0.5 * twidth + table.accu_cwidth,
                           0.5 * theight - table.accu_cheight, 0.5 * theight)
        else:
            canvas_size = (-0.5 * twidth, 0.5 * twidth,
                           -0.5 * theight, 0.5 * theight)
        self._frame["canvasSize"] = canvas_size


class PageItem (object):

    def __init__ (self, items, size,
                  textfont=ui_font_path, textcolor=rgba(255, 255, 255, 1.0),
                  textsize=14, caption=None, switchf=None,
                  parent=None, pos=Point2()):

        top = NodePath("page-item")
        if parent is not None:
            top.reparentTo(parent)

        frame_width, frame_height = size

        border_size = 0.04

        frame_node = make_frame(
            imgbase="images/ui/textfloat03", imgsize=border_size,
            width=frame_width, height=frame_height, filtr=False,
            parent=top)
        frame_node.setPos(pos[0], 0.0, pos[1])

        item_nodes = []
        item_size = max(frame_width, frame_height)
        for item in items:
            if path_isfile("data", item):
                item_node = make_image(texture=item, size=item_size,
                                       filtr=False, parent=frame_node)
            else:
                item_node = make_text(text=item,
                                      width=frame_width,
                                      size=textsize, font=textfont,
                                      color=textcolor,
                                      align="c", anchor="mc", wrap=False,
                                      parent=frame_node)
            item_node.hide()
            item_nodes.append(item_node)

        self._current_item_index = 0
        num_items = len(items)
        def pagef (di):
            if num_items == 0:
                return
            item_nodes[self._current_item_index].hide()
            self._current_item_index -= di
            while self._current_item_index < 0:
                self._current_item_index += num_items
            while self._current_item_index >= num_items:
                self._current_item_index -= num_items
            item_nodes[self._current_item_index].show()
            switchf(self._current_item_index)
        pagef(0)

        bt_size = 0.15
        bt_click_sound = base.load_sound("data", "audio/sounds/button-click.ogg")
        bt_left_base_geom = make_image(
            texture="images/ui/page_button_left.png",
            size=bt_size, filtr=False)
        bt_off_x = 0.5 * frame_width + (0.5 - 0.20) * bt_size + border_size
        bt_left_geom = (bt_left_base_geom,) * 4
        self._bt_left = DirectButton(
            geom=bt_left_geom,
            clickSound=bt_click_sound,
            rolloverSound=None,
            pos=Point3(pos[0] - bt_off_x, 0.0, pos[1]),
            relief=None,
            pressEffect=0,
            parent=top,
            command=lambda: pagef(-1))
        bt_right_base_geom = make_image(
            texture="images/ui/page_button_right.png",
            size=bt_size, filtr=False)
        bt_right_geom = (bt_right_base_geom,) * 4
        self._bt_right = DirectButton(
            geom=bt_right_geom,
            clickSound=bt_click_sound,
            rolloverSound=None,
            pos=Point3(pos[0] + bt_off_x, 0.0, pos[1]),
            relief=None,
            pressEffect=0,
            parent=top,
            command=lambda: pagef(+1))


class Menu (DirectObject):

    def __init__ (self, name, pointer=None, music=None, fadetime=0.0,
                  delaytime=0.0, quickexit=None, parent=None):

        DirectObject.__init__(self)

        self.name = name

        if parent is None:
            pnode = base.uiface_root
        elif isinstance(parent, Menu):
            pnode = parent.pnode
        elif isinstance(parent, NodePath):
            pnode = parent
            parent = None
        else:
            raise StandardError(
                "Parent must be another menu, node path, or none.")
        self.parent = parent
        self.pnode = pnode
        self.bgnode = pnode.attachNewNode(name + "-background")
        self.node = pnode.attachNewNode(name)
        self.fgnode = pnode.attachNewNode(name + "-foreground")
        self.node.hide()

        if parent:
            music = None
            fadetime = 0.0

        if pointer is None:
            pointer = "images/ui/mouse_pointer.png"
        self._pointer = get_pointer(pointer)
        self._pointer.hide()

        if music is not None:
            music = Sound2D(music, pnode=self.node,
                            volume=0.0, loop=True, play=False)
        self._music = music

        self._selection = None
        self._stage = "delay"
        self._delaytime = delaytime
        self._fadetasks = []
        if isinstance(fadetime, tuple):
            self._fadetime = fadetime
        else:
            self._fadetime = (fadetime, fadetime)
        if self._fadetime[0] > 0.0:
            self.node.setSa(0.0)

        self._keyseq_exit = "escape"
        self.accept(self._keyseq_exit, self._quick_exit)
        if not self.parent:
            base.set_priority("menu", self._keyseq_exit, 15)
        self._quick_exit_func = quickexit

        self._submenu = None

        self.alive = True
        base.taskMgr.add(self._loop, "%s-loop" % name)


    def destroy (self):

        if not self.alive:
            return

        self.alive = False

        kill_tasks(self._fadetasks)
        if self._music is not None:
            self._music.stop()
        if not self.parent:
            self._pointer.detachNode()
        self.node.removeNode()
        self.bgnode.removeNode()
        self.fgnode.removeNode()
        self.ignoreAll()
        if not self.parent:
            base.remove_priority("menu")


    def _loop (self, task):

        if not self.alive:
            return task.done

        if self._stage == "delay":
            if callable(self._delaytime):
                done = self._delaytime()
            else:
                self._delaytime -= base.global_clock.getDt()
                done = (self._delaytime <= 0.0)
            if done:
                # ._delaytime() might call .end(), and then do not start.
                if self._stage != "end":
                    self._stage = "start"

        if self._stage == "start":
            kill_tasks(self._fadetasks)
            self._fadetasks = []
            if self._fadetime[0] > 0.0:
                t = node_fade_to(self.node, startalpha=0.0, endalpha=1.0,
                                 duration=self._fadetime[0],
                                 startf=self.node.show)
                self._fadetasks.append(t)
            else:
                self.node.setSa(1.0)
                self.node.show()
            if self._music is not None:
                self._music.play()
                self._music.set_volume(1.0, fadetime=self._fadetime[0])
            self._stage = "start2"

        if self._stage == "start2":
            if not any(x.isAlive() for x in self._fadetasks):
                self._stage = "loop"
                self._pointer.show()

        if self._stage == "loop":
            pass

        if self._stage == "submenu":
            if not self._submenu.alive:
                sname, sargs = self._submenu.selection()
                self._submenu = None
                if sname:
                    self.end(sname, sargs)
                else:
                    self.node.show()
                    if self._music is not None and self._submenu_mutemusic:
                        self._music.play()
                    self._pointer.show()
                    self._stage = self._submenu_after_stage
                if self._submenu_endf:
                    self._submenu_endf()

        if self._stage == "dialog":
            if not self._dialog.in_progress():
                self.node.show()
                if self._music is not None and self._dialog_mutemusic:
                    self._music.play()
                self._pointer.show()
                self._stage = self._dialog_after_stage
                if self._dialog_endf:
                    self._dialog_endf()

        if self._stage == "end":
            kill_tasks(self._fadetasks)
            self._fadetasks = []
            if self._fadetime[1] > 0.0:
                t = node_fade_to(self.node,
                                 startalpha=1.0, endalpha=0.0,
                                 duration=self._fadetime[1],
                                 endf=self.node.hide)
                self._fadetasks.append(t)
            if self._music is not None:
                self._music.stop(fadetime=self._fadetime[1])
            self._pointer.hide()
            self._stage = "end2"

        if self._stage == "end2":
            if not any(x.isAlive() for x in self._fadetasks):
                self.destroy()
                return task.done

        return task.cont


    def end (self, name=None, args=()):

        if self._stage.startswith("end"):
            return

        self._selection = (name, args)
        self._stage = "end"


    def _quick_exit (self):

        if (not self._quick_exit_func or
            not base.challenge_priority("menu", self._keyseq_exit) or
            self._submenu):
            return

        self._quick_exit_func()


    def selection (self):

        return self._selection


    def wait_submenu (self, menu, startf=None, endf=None, mutemusic=False):

        self._submenu = menu
        self.node.hide()
        # No hide on fgnode and bgnode.
        if startf:
            startf()
        if self._music is not None and mutemusic:
            self._music.stop()
        self._submenu_endf = endf
        self._submenu_mutemusic = mutemusic
        self._submenu_after_stage = self._stage
        self._stage = "submenu"


    def wait_dialog (self, dialog, startf=None, endf=None, mutemusic=False):

        self._dialog = dialog
        self._dialog.start()
        self.node.hide()
        self._pointer.hide()
        # No hide on fgnode and bgnode.
        if startf:
            startf()
        if self._music is not None and mutemusic:
            self._music.stop()
        self._dialog_endf = endf
        self._dialog_mutemusic = mutemusic
        self._dialog_after_stage = self._stage
        self._stage = "dialog"


    def create_dialog_context (self):

        dc = AutoProps()
        dc.bgnode = self.bgnode.attachNewNode("dialog-background")
        dc.node = self.fgnode.attachNewNode("dialog")
        dc.fgnode = self.fgnode.attachNewNode("dialog-foreground")
        return dc


    def cleanup_dialog_context (self, dc):

        dc.fgnode.removeNode()
        dc.bgnode.removeNode()
        dc.node.removeNode()


class MainMenu (Menu):

    def __init__ (self, first=False, jumpsub=None, parent=None):

        fade_time = 0.5
        anim_type = 2

        time_delay_menu = 0.0
        if first:
            if anim_type == 0:
                pass
            elif anim_type == 1:
                time_before_title = 1.0
                time_title = 2.0
                time_move_title = fade_time
                time_delay_menu = time_before_title + time_title + time_move_title
            elif anim_type == 2:
                time_move_title = fade_time
            else:
                assert False

        Menu.__init__(self,
            name="main-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            fadetime=(fade_time, 0.0),
            delaytime=time_delay_menu,
            parent=parent)

        hw = base.aspect_ratio

        img_node = make_image("images/ui/main_menu.png",
                              size=(2 * hw), pos=Point2(0.0, 0.0),
                              filtr=False, parent=self.node)

        split_type = p_("title splitting type: horiz, vert",
        # TRNOTE: This determines how the game name in the main menu
        # title will be split into two pieces, which will be moved
        # into their final position by an animation.
        # Translate this *exactly* as one of:
        # - horiz: title is one line, split into left and right part
        # - vert: title is two lines, split into upper and lower part
                        "horiz")
        if split_type == "horiz":
            game_name_p1 = p_("game name as main menu title, left part "
                              "(used when 'horiz' splitting)",
            # TRNOTE: If the name is split at a space character, include it
            # either at end of left part or at start of right part.
                              "LIMIT")
            game_name_p2 = p_("game name as main menu title, right part "
                              "(used when 'horiz' splitting)",
            # TRNOTE: If the name is split at a space character, include it
            # either at end of left part or at start of right part.
                              " LOAD")
        elif split_type == "vert":
            game_name_p1 = p_("game name as main menu title, upper part "
                              "(used when 'vert' splitting)",
            # TRNOTE: Do not include any trailing or leading space characters.
                              "LIMIT")
            game_name_p2 = p_("game name as main menu title, lower part "
                              "(used when 'vert' splitting)",
            # TRNOTE: Do not include any trailing or leading space characters.
                              "LOAD")
        else:
            raise StandardError(
                "Unknown main manu title splitting type '%s'." %
                split_type)

        if split_type == "horiz":
            gn_size = 64
            align_1 = "r"
            align_2 = "l"
            anchor_1 = "rc"
            anchor_2 = "lc"
        elif split_type == "vert":
            gn_size = 48
            align_1 = "c"
            align_2 = "c"
            anchor_1 = "mc"
            anchor_2 = "mc"
        else:
            assert False
        gn_scale = font_scale_for_ptsize(gn_size)
        gn_off_x_1 = 0.0
        gn_off_x_2 = 0.0
        if split_type in ("horiz",):
            space_rel_size = 0.33
            if game_name_p1.endswith(" "):
                gn_off_x_1 = -gn_scale * space_rel_size
            if game_name_p2.startswith(" "):
                gn_off_x_2 = gn_scale * space_rel_size
        game_name_p1 = game_name_p1.strip()
        game_name_p2 = game_name_p2.strip()
        name_pnode = self.fgnode if first else self.node
        name_node = name_pnode.attachNewNode("title")
        name_node_1 = make_text(
            game_name_p1,
            width=2.0,
            font=ui_font_path, size=gn_size, ppunit=100,
            color=rgba(255, 0, 0, 1.0),
            align=align_1, anchor=anchor_1,
            parent=name_node)
        name_node_2 = make_text(
            game_name_p2,
            width=2.0,
            font=ui_font_path, size=gn_size, ppunit=100,
            color=rgba(255, 0, 0, 1.0),
            align=align_2, anchor=anchor_2,
            parent=name_node)
        bmin_1, bmax_1 = name_node_1.getTightBounds()
        name_width_1 = (bmax_1[0] - bmin_1[0]) + abs(gn_off_x_1)
        bmin_2, bmax_2 = name_node_2.getTightBounds()
        name_width_2 = (bmax_2[0] - bmin_2[0]) + abs(gn_off_x_2)
        if split_type == "horiz":
            gn_pos_z = 0.80
            gn_pos_z_1 = 0.0
            gn_pos_z_2 = 0.0
            gn_pos_x = 0.0
            width_off = (name_width_1 - name_width_2) * 0.5
            gn_pos_x_1 = width_off
            gn_pos_x_2 = width_off
        elif split_type == "vert":
            gn_pos_z = 0.75
            gn_pos_z_1 = 0.08
            gn_pos_z_2 = -0.08
            gn_pos_x = 0.0
            gn_pos_x_1 = 0.0
            gn_pos_x_2 = 0.0
        else:
            assert False
        name_node.setPos(gn_pos_x, 0.0, gn_pos_z)
        name_node_1.setPos(gn_pos_x_1 + gn_off_x_1, 0.0, gn_pos_z_1)
        name_node_2.setPos(gn_pos_x_2 + gn_off_x_2, 0.0, gn_pos_z_2)

        bt_campaign = MainLargeButton(
            basetext=p_("main menu: play a campaign",
                        "Campaign"),
            pos=Point2(0.0, 0.15),
            clickf=self._click_campaign,
            parent=self.node)

        bt_skirmish = MainLargeButton(
            basetext=p_("main menu: play a skirmish",
                        "Skirmish"),
            pos=Point2(0.0, -0.05),
            clickf=self._click_skirmish,
            parent=self.node)

        # bt_options = MainSmallButton(
            # basetext=p_("main menu: show game options",
                        # "Options"),
            # pos=Point2(-0.26, -0.32),
            # clickf=self._click_options,
            # parent=self.node)
        # bt_options.disable()

        # bt_manual = MainSmallButton(
            # basetext=p_("main menu: show player manual",
                        # "Manual"),
            # pos=Point2(0.26, -0.32),
            # clickf=self._click_manual,
            # parent=self.node)
        # bt_manual.disable()

        # bt_extras = MainSmallButton(
            # basetext=p_("main menu: show extras (funny stuff, etc.)",
                        # "Extras"),
            # pos=Point2(-0.26, -0.48),
            # clickf=self._click_extras,
            # parent=self.node)
        # bt_extras.disable()

        # bt_credits = MainSmallButton(
            # basetext=p_("main menu: show game credits (people names, etc.)",
                        # "Credits"),
            # pos=Point2(0.26, -0.48),
            # clickf=self._click_credits,
            # parent=self.node)
        # bt_credits.disable()

        bt_quit = MainSmallButton(
            basetext=p_("main menu: quit the game",
                        "Quit Game"),
            pos=Point2(0.0, -0.64),
            clickf=self._click_quit,
            parent=self.node)

        if first:
            if anim_type == 0:
                name_node.reparentTo(self.node)
            elif anim_type == 1:
                self._init_anim_1(name_node, name_node_1, name_node_2,
                                  time_before_title, time_title,
                                  time_move_title)
            elif anim_type == 2:
                self._init_anim_2(name_node, name_node_1, name_node_2,
                                  time_move_title)
            else:
                assert False

        if jumpsub == "skirmish":
            self._click_skirmish()


    def _init_anim_1 (self, name_node, name_node_1, name_node_2,
                      time_before_title, time_title, time_move_title):

        name_node.hide()
        name_end_pos = name_node.getPos()
        name_node.setPos(0.0, 0.0, 0.0)
        name_node.setScale(1.2)
        @itertask
        def taskf (task):
            yield time_before_title
            node_swipe(name_node, duration=0.4, cover=False)
            #node_fade_to(name_node,
                         #startalpha=0.0, endalpha=1.0, duration=0.4)
            yield time_title
            node_slide_to(name_node,
                          endpos=name_end_pos, duration=time_move_title)
            node_scale_to(name_node,
                          endscale=1.0, duration=time_move_title)
            yield time_move_title
            yield time_move_title # to not get caught into fade
            name_node.reparentTo(self.node)
        base.taskMgr.add(taskf, "main-menu-setup-background")


    def _init_anim_2 (self, name_node, name_node_1, name_node_2,
                      time_move_title):

        name_end_pos_1 = name_node_1.getPos()
        name_end_pos_2 = name_node_2.getPos()
        hw = base.aspect_ratio
        bmin_1, bmax_1 = name_node_1.getTightBounds()
        bmin_2, bmax_2 = name_node_2.getTightBounds()
        name_node_1.setPos(name_end_pos_1 + Point3(-hw - bmax_1[0], 0.0, 0.0))
        name_node_2.setPos(name_end_pos_2 + Point3(hw - bmin_2[0], 0.0, 0.0))
        @itertask
        def taskf (task):
            node_slide_to(name_node_1,
                          endpos=name_end_pos_1, duration=time_move_title)
            node_slide_to(name_node_2,
                          endpos=name_end_pos_2, duration=time_move_title)
            yield time_move_title
            yield time_move_title # to not get caught into fade
            if not self.node.isEmpty():
                name_node.reparentTo(self.node)
        base.taskMgr.add(taskf, "main-menu-setup-background")


    def _click_campaign (self):

        pre_campaign_menu = PreCampaignMenu(parent=self)
        self.wait_submenu(pre_campaign_menu)


    def _click_skirmish (self):

        skirmish_menu = SkirmishMenu(parent=self)
        self.wait_submenu(skirmish_menu)


    def _click_options (self):

        raise NotImplementedError
        options_menu = OptionsMenu(parent=self)
        self.wait_submenu(options_menu)


    def _click_manual (self):

        raise NotImplementedError
        manual_menu = ManualMenu(parent=self)
        self.wait_submenu(manual_menu)


    def _click_extras (self):

        raise NotImplementedError
        extras_menu = ExtrasMenu(parent=self)
        self.wait_submenu(extras_menu)


    def _click_credits (self):

        raise NotImplementedError
        credits_menu = CreditsMenu(parent=self)
        self.wait_submenu(credits_menu)


    def _click_quit (self):

        self.end("quit")


class CampaignMenu (Menu):

    def __init__ (self, parent=None):

        Menu.__init__(self,
            name="campaign-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_exit,
            parent=parent)

        hw = base.aspect_ratio

        make_image("images/ui/campaign_menu.png",
                   size=(2 * hw), pos=Point2(0.0, 0.0),
                   parent=self.node)

        make_text(_("CAMPAIGN"),
                  width=2.0, pos=Point2(0.0, 0.85),
                  font=ui_font_path, size=48, ppunit=100,
                  color=rgba(255, 0, 0, 1.0),
                  align="c", anchor="mc",
                  parent=self.node)

        bt_start = MainSmallButton(
            basetext=p_("campaign menu: start the campaign",
                        "Start"),
            pos=Point2(0.85, -0.62),
            clickf=self._click_start,
            parent=self.node)
        bt_start.disable()

        bt_exit = MainSmallButton(
            basetext=p_("campaign menu: go to the previous menu",
                        "Go Back"),
            pos=Point2(0.85, -0.78),
            clickf=self._click_exit,
            parent=self.node)

        campaign_spec = CampaignMenu._collect_campaigns()
        scroll_campaign_texts = []
        page_emblem_items = []
        for name, shortdes, longdes, cshortdes, emblem, avail in campaign_spec:
            text = []
            text.append((shortdes,
                         AutoProps(align="c", size_factor=1.5, underscore=True)))
            if not avail:
                text.append((p_("campaign not available", "(unavailable)"),
                             AutoProps(align="c", size_factor=0.8)))
            text.append("")
            text.append(longdes)
            scroll_campaign_texts.append(text)
            if emblem:
                page_emblem_items.append(emblem)
            else:
                page_emblem_items.append(cshortdes or shortdes)

        fr_desc = ScrollText(
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=16,
            size=(2.2, 1.1),
            pos=Point2(0.0, 0.15),
            parent=self.node)
        fr_desc.cache_texts(scroll_campaign_texts)

        self._selected_campaign = None
        def page_emblem_switchf (i):
            name = campaign_spec[i][0]
            fr_desc.set_text(scroll_campaign_texts[i])
            avail = campaign_spec[i][5]
            self._selected_campaign = name
            if name and avail:
                bt_start.enable()
            else:
                bt_start.disable()

        fr_emblem = PageItem(
            items=page_emblem_items,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=16,
            size=(0.4, 0.4),
            pos=Point2(-0.80, -0.70),
            parent=self.node,
            switchf=page_emblem_switchf)

        if campaign_spec:
            page_emblem_switchf(0)


    def _click_start (self):

        self.end("campaign", (self._selected_campaign,))


    def _click_exit (self):

        self.end()


    @staticmethod
    def _collect_campaigns ():

        campaign_spec = []
        campaign_dir = "src/campaigns"
        for item in list_dir_subdirs("data", campaign_dir):
            item_path = join_path(campaign_dir, item)
            init_path = join_path(item_path, "__init__.py")
            name = item
            mod = __import__(name)
            shortdes = getattr(mod, "campaign_shortdes")
            longdes = getattr(mod, "campaign_longdes", "")
            cshortdes = getattr(mod, "campaign_shortdes_compact", "")
            emblem = join_path(item_path, "__emblem.png")
            if not path_exists("data", emblem):
                emblem = None
            avail = hasattr(mod, "select_next_mission")
            #dif = getattr(mod, "campaign_difficulty", None)
            campaign_spec.append((name, shortdes, longdes, cshortdes, emblem,
                                  avail))
        campaign_spec.sort()
        return campaign_spec


class LoadMenu (Menu):

    def __init__ (self, parent=None):

        Menu.__init__(self,
            name="load-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_exit,
            parent=parent)

        hw = base.aspect_ratio

        make_image("images/ui/load_menu.png",
                   size=(2 * hw), pos=Point2(0.0, 0.0),
                   parent=self.node)

        make_text(_("LOAD GAME"),
                  width=2.0, pos=Point2(0.0, 0.85),
                  font=ui_font_path, size=48, ppunit=100,
                  color=rgba(255, 0, 0, 1.0),
                  align="c", anchor="mc",
                  parent=self.node)

        bt_exit = MainSmallButton(
            basetext=p_("load game menu: go to the previous menu",
                        "Go Back"),
            pos=Point2(-0.08, -0.90),
            clickf=self._click_exit,
            parent=self.node)

        bt_delete = MainSmallButton(
            basetext=p_("load game menu: delete a saved game",
                        "Delete"),
            pos=Point2(0.44, -0.90),
            clickf=self._click_delete,
            parent=self.node)
        bt_delete.disable()
        self._bt_delete = bt_delete

        bt_load = MainSmallButton(
            basetext=p_("load game menu: load a saved game",
                        "Load"),
            pos=Point2(0.96, -0.90),
            clickf=self._click_load,
            parent=self.node)
        bt_load.disable()
        self._bt_load = bt_load

        saved_game_spec = LoadMenu._collect_saved_games()
        table_campaigns_spec = []
        table_saved_games_spec = []
        for saved_game_spec_1 in saved_game_spec:
            (campaign_name, campaign_saved_game_spec,
             campaign_shortdes) = saved_game_spec_1[:3]
            table_campaigns_spec.append((campaign_shortdes,))
            table_saved_games_spec.append([])
            for campaign_saved_game_spec_1 in campaign_saved_game_spec:
                saved_game_name, = campaign_saved_game_spec_1[:1]
                table_saved_games_spec[-1].append((saved_game_name,))
        self._saved_game_spec = saved_game_spec

        self._selected_campaign_index = None
        def table_campaigns_switchf (k):
            if self._selected_campaign_index != k:
                self._selected_campaign_index = k
                fr_games.switch_table(k)
                self._selected_game = None
                bt_load.disable()
                bt_delete.disable()

        fr_campaigns = ScrollTable(
            caption=_("Campaigns:"),
            colspec=[
                (p_("column name", "Name"), 1.0),
            ],
            rowdata=table_campaigns_spec,
            sortcol=0,
            switchf=table_campaigns_switchf,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=12,
            size=(0.94, 1.34),
            noheader=True,
            pos=Point2(-0.70, -0.07),
            parent=self.node)

        self._selected_game_index = None
        def table_saved_games_switchf (k, i):
            if self._selected_game_index != (k, i):
                self._selected_game_index = (k, i)
                saved_game_name = saved_game_spec[k][1][i][0]
                self._selected_game = saved_game_name
                saved_game_path = saved_game_spec[k][1][i][1]
                if saved_game_path:
                    bt_load.enable()
                    bt_delete.enable()
                else:
                    bt_load.disable()
                    bt_delete.disable()

        fr_games = ScrollTable(
            caption=_("Saved games:"),
            colspec=[
                (p_("column name", "Name"), 1.0),
            ],
            multitable=True,
            rowdata=table_saved_games_spec,
            sortcol=0,
            switchf=table_saved_games_switchf,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=12,
            size=(1.20, 1.34),
            noheader=True,
            pos=Point2(0.52, -0.07),
            parent=self.node)
        fr_games.switch_table(-1)
        self._fr_games = fr_games

        self._selected_game = None


    def _click_exit (self):

        self.end()


    def _click_delete (self):

        if self._selected_game_index:
            k, i = self._selected_game_index
            saved_game_path = self._saved_game_spec[k][1][i][1]
            self._fr_games.delete_row(i)
            self._saved_game_spec[k][1].pop(i)
            self._selected_game_index = None
            self._selected_game = None
            os.remove(saved_game_path)
            self._bt_load.disable()
            self._bt_delete.disable()


    def _click_load (self):

        self.end("continue", (self._selected_game,))


    @staticmethod
    def _collect_saved_games ():

        games_by_campaign = {}
        for item in list_dir_files("save", "."):
            if not item.endswith(".pkl"):
                continue
            saved_game_name = item[:-len(".pkl")]
            saved_game_path = item
            with open(real_path("save", saved_game_path), "rb") as fh:
                payload = pickle.load(fh)
            gcd = payload["context"]
            campaign_name = gcd["campaign"]
            if campaign_name not in games_by_campaign:
                games_by_campaign[campaign_name] = []
            campaign_saved_game_spec_1 = (saved_game_name, saved_game_path)
            games_by_campaign[campaign_name].append(campaign_saved_game_spec_1)
        if 0:
            from dialog import lorem_ipsum
            for i in range(40):
                campaign_name = "zc%03d" % (i + 1)
                games_by_campaign[campaign_name] = []
                for j in range(20 + i):
                    saved_game_name = "%s_g%03d" % (campaign_name, j + 1)
                    campaign_saved_game_spec_1 = (saved_game_name, "")
                    games_by_campaign[campaign_name].append(
                        campaign_saved_game_spec_1)
        saved_game_spec = []
        for campaign_name, campaign_saved_game_spec in games_by_campaign.items():
            try:
                mod = __import__(campaign_name)
            except:
                campaign_shortdes = campaign_name
                is_dummy_campaign = True
            else:
                campaign_shortdes = getattr(mod, "campaign_shortdes")
                is_dummy_campaign = False
            campaign_saved_game_spec.sort(key=lambda x: x[0])
            saved_game_spec.append(
                (campaign_name, campaign_saved_game_spec, campaign_shortdes,
                 is_dummy_campaign))
        saved_game_spec.sort(key=lambda x: x[2])
        return saved_game_spec


_last_game_filename = "last_game"

def set_last_saved_game (basename):

    last_path = _last_game_filename
    with open(real_path("save", last_path), "wb") as fh:
        fh.write("%s\n" % basename.encode("utf8"))


def get_last_saved_game ():

    basename = None
    last_path = _last_game_filename
    if path_exists("save", last_path):
        with open(real_path("save", last_path), "rb") as fh:
            basename = fh.read().decode("utf8").strip()
        if not path_exists("save", basename + ".pkl"):
            basename = None
    return basename


class PreCampaignMenu (Menu):

    def __init__ (self, parent=None):

        Menu.__init__(self,
            name="pre-campaign-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_exit,
            parent=parent)

        hw = base.aspect_ratio

        make_image("images/ui/main_menu.png",
                   size=(2 * hw), pos=Point2(0.0, 0.0),
                   parent=self.node)

        self._last_game = get_last_saved_game()

        bt_continue = MainSmallButton(
            basetext=p_("pre-campaign menu: continue the current campaign",
                        "Continue"),
            pos=Point2(0.0, 0.24),
            clickf=self._click_continue,
            parent=self.node)
        if not self._last_game:
            bt_continue.disable()

        bt_load = MainSmallButton(
            basetext=p_("pre-campaign menu: load a saved game",
                        "Load Game"),
            pos=Point2(0.0, 0.08),
            clickf=self._click_load,
            parent=self.node)
        bt_load.disable()

        bt_start = MainSmallButton(
            basetext=p_("pre-campaign menu: start a new campaign",
                        "Start New"),
            pos=Point2(0.0, -0.08),
            clickf=self._click_start,
            parent=self.node)

        bt_exit = MainSmallButton(
            basetext=p_("pre-campaign menu: go to the previous menu",
                        "Go Back"),
            pos=Point2(0.0, -0.24),
            clickf=self._click_exit,
            parent=self.node)

        bt_load.enable()


    def _click_continue (self):

        self.end("continue", (self._last_game,))


    def _click_load (self):

        load_menu = LoadMenu(parent=self)
        self.wait_submenu(load_menu)


    def _click_start (self):

        campaign_menu = CampaignMenu(parent=self)
        self.wait_submenu(campaign_menu)


    def _click_exit (self):

        self.end()


class SkirmishMenu (Menu):

    def __init__ (self, parent=None):

        Menu.__init__(self,
            name="skirmish-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_exit,
            parent=parent)

        hw = base.aspect_ratio

        make_image("images/ui/skirmish_menu.png",
                   size=(2 * hw), pos=Point2(0.0, 0.0),
                   parent=self.node)

        make_text(_("SKIRMISH"),
                  width=2.0, pos=Point2(0.0, 0.85),
                  font=ui_font_path, size=48, ppunit=100,
                  color=rgba(255, 0, 0, 1.0),
                  align="c", anchor="mc",
                  parent=self.node)

        bt_start = MainSmallButton(
            basetext=p_("skirmish menu: start the skirmish mission",
                        "Start"),
            pos=Point2(0.65, -0.60),
            clickf=self._click_start,
            parent=self.node)
        bt_start.disable()

        bt_exit = MainSmallButton(
            basetext=p_("skirmish menu: go to the previous menu",
                        "Go Back"),
            pos=Point2(0.65, -0.76),
            clickf=self._click_exit,
            parent=self.node)

        mission_spec = SkirmishMenu._collect_missions()
        table_mission_spec = []
        D = MISSION_DIFFICULTY
        T = MISSION_TYPE
        for dname, name, shortdes, longdes, dif, typ in mission_spec:
            dif_vis = (
                p_("skirmish difficulty", "easy") if dif == D.EASY else
                p_("skirmish difficulty", "hard") if dif == D.HARD else
                p_("skirmish difficulty", "extreme") if dif == D.EXTREME else
                p_("skirmish difficulty", "unknown"))
            typ_vis = (
                p_("skirmish type", "dogfight") if typ == T.DOGFIGHT else
                p_("skirmish type", "ground attack") if typ == T.ATTACK else
                p_("skirmish type", "unknown"))
            table_mission_spec.append((shortdes, typ_vis, (dif_vis, dif)))

        fr_desc = ScrollText(
            caption=_("Description:"),
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=12,
            size=(1.00, 1.00),
            pos=Point2(0.65, 0.10),
            parent=self.node)
        fr_desc.cache_texts([s[3] for s in mission_spec])

        self._selected_skirmish = None
        self._selected_mission = None
        def table_entry_switchf (i):
            dname, name, shortdes, longdes, dif, typ = mission_spec[i]
            fr_desc.set_text(longdes)
            self._selected_skirmish = dname
            self._selected_mission = name
            if name:
                bt_start.enable()
            else:
                bt_start.disable()

        fr_missions = ScrollTable(
            caption=_("Scenarios:"),
            colspec=[
                (p_("column name", "Name"), 0.55),
                (p_("column name", "Type"), 0.25),
                (p_("column name", "Difficulty"), 0.20),
                #(p_("column name", "Name"), 0.75),
                #(p_("column name", "Difficulty"), 0.25),
            ],
            rowdata=table_mission_spec,
            sortcol=0,
            switchf=table_entry_switchf,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=12,
            size=(1.15, 1.50),
            pos=Point2(-0.58, -0.15),
            parent=self.node)


    def _click_start (self):

        self.end("skirmish", (self._selected_skirmish, self._selected_mission))


    def _click_exit (self):

        self.end()


    @staticmethod
    def _collect_missions ():

        mission_spec = []
        skirmish_dir = "src/skirmish"
        for dname in list_dir_subdirs("data", skirmish_dir):
            skirmish_subdir = join_path(skirmish_dir, dname)
            for fname in list_dir_files("data", skirmish_subdir):
                if not fname.endswith(".py"):
                    continue
                name = fname[:-len(".py")]
                if name == "__init__":
                    continue
                mod0 = __import__("%s.%s" % (dname, name))
                mod = getattr(mod0, name)
                shortdes = getattr(mod, "mission_shortdes")
                longdes = getattr(mod, "mission_longdes", None)
                dif = getattr(mod, "mission_difficulty", None)
                typ = getattr(mod, "mission_type", None)
                mission_spec.append((dname, name, shortdes, longdes, dif, typ))
        mission_spec.sort()
        if 0:
            from dialog import lorem_ipsum
            for i in range(40):
                name = ""
                shortdes = ("z%03d|" % (i + 1)) + lorem_ipsum(40)
                longdes = ("z%03d|" % (i + 1)) + lorem_ipsum()
                dif = MISSION_DIFFICULTY.EASY
                typ = MISSION_TYPE.DOGFIGHT
                mission_spec.append((name, shortdes, longdes, dif, typ))
        return mission_spec


class MissionMenu (Menu):

    def __init__ (self, gc=None, setbgf=None, music=None,
                  preconvf=None, inconvf=None, drinkconvf=None,
                  mustdrink=False, drinktostart=False, jumpinconv=False,
                  skipconfirm=False,
                  parent=None):

        self._game_context = gc

        mc = AutoProps()
        self._menu_context = mc

        init_fade_duration = 0.25

        Menu.__init__(self,
            name="mission-menu",
            music=music,
            pointer="images/ui/mouse_pointer.png",
            fadetime=init_fade_duration,
            parent=parent)
        mc.node = self.node
        mc.bgnode = self.bgnode
        mc.fgnode = self.fgnode

        if setbgf:
            setbgf(mc, gc)
            self.bgnode.setSa(0.0)
            def fadebg ():
                node_fade_to(self.bgnode,
                            startalpha=0.0, endalpha=1.0,
                            duration=init_fade_duration)
        if preconvf:
            self.bgnode.hide()
            dc = self.create_dialog_context()
            preconv = preconvf(dc, mc, gc)
            preconv.canskip = True
            preconv.canend = True
            def endf ():
                self.cleanup_dialog_context(dc)
                self.bgnode.show()
                if not jumpinconv:
                    if setbgf:
                        fadebg()
                else:
                    self._click_mission()
            self.wait_dialog(preconv, endf=endf, mutemusic=True)
        elif setbgf:
            fadebg()

        self._inconvf = inconvf
        self._drinkconvf = drinkconvf
        self._mustdrink = mustdrink
        self._drinktostart = drinktostart
        self._skipconfirm = skipconfirm

        self._background_alpha_conv = 0.5
        self._background_fade_duration = 0.25

        if not jumpinconv:
            wmission = not mustdrink and not drinktostart
            wdrink = drinkconvf is not None
            wsave = False # not implemented
            self._add_buttons(wmission, wdrink, wsave)
        elif not preconvf:
            self._click_mission()


    def _add_buttons (self, wmission, wdrink, wsave):

        hw = base.aspect_ratio

        bt_mission = MissionButton(
            basetext=p_("mission menu: start playing the mission",
                        "Mission"),
            pos=Point2(-hw + 0.40, -0.40),
            clickf=self._click_mission,
            parent=self.node)
        if not wmission:
            bt_mission.disable()
        self._bt_mission = bt_mission

        bt_drink = MissionButton(
            basetext=p_("mission menu: go have some relaxation",
                        "Vodka!"),
            pos=Point2(-hw + 0.44, -0.55),
            clickf=self._click_drink,
            parent=self.node)
        if not wdrink:
            bt_drink.disable()

        bt_save = MissionButton(
            basetext=p_("mission menu: manage saved games",
                        "Archive"),
            pos=Point2(-hw + 0.48, -0.70),
            clickf=self._click_save,
            parent=self.node)
        if not wsave:
            bt_save.disable()

        bt_main = MissionButton(
            basetext=p_("mission menu: go to the main menu",
                        "Main Menu"),
            pos=Point2(-hw + 0.52, -0.85),
            clickf=self._click_main,
            parent=self.node)


    def _click_mission (self):

        if self._inconvf is not None:
            dmenu = DialogMenu(gc=self._game_context, mc=self._menu_context,
                               convf=self._inconvf,
                               skipconfirm=self._skipconfirm,
                               exitstate="mission",
                               parent=self)
            self.wait_submenu(menu=dmenu,
                              startf=self._on_dialog_start(),
                              mutemusic=True)
        else:
            self.end("mission")


    def _click_drink (self):

        if not self._drinktostart:
            skipconfirm = True
            exitstate = None
            endf = self._on_dialog_end()
        else:
            skipconfirm = False
            exitstate = "mission"
            def endf1 ():
                if self._mustdrink:
                    self._bt_mission.enable()
            endf = self._on_dialog_end(execf=endf1)
        dmenu = DialogMenu(gc=self._game_context, mc=self._menu_context,
                           convf=self._drinkconvf,
                           skipconfirm=skipconfirm,
                           exitstate=exitstate,
                           parent=self)
        self.wait_submenu(menu=dmenu,
                          startf=self._on_dialog_start(),
                          endf=endf,
                          mutemusic=True)


    def _click_save (self):

        raise NotImplementedError
        save_menu = SaveMenu(parent=self)
        self.wait_submenu(save_menu)


    def _click_main (self):

        self.end("main")


    def _on_dialog_start (self):

        def startf ():
            node_fade_to(self.bgnode,
                         endalpha=self._background_alpha_conv,
                         duration=self._background_fade_duration)
        return startf


    def _on_dialog_end (self, execf=None):

        def endf ():
            node_fade_to(self.bgnode,
                         endalpha=1.0,
                         duration=self._background_fade_duration,
                         endf=execf)
        return endf


class DialogMenu (Menu):

    def __init__ (self, convf, gc=None, mc=None,
                  skipconfirm=False, exitstate=None, parent=None):

        Menu.__init__(self,
            name="dialog-menu",
            pointer="images/ui/mouse_pointer.png",
            fadetime=0.0,
            parent=parent)

        self._game_context = gc

        if mc is None:
            mc = AutoProps()
            mc.node = self.node
            mc.bgnode = self.bgnode
            mc.fgnode = self.fgnode
        self._menu_context = mc

        self._convf = convf
        self._skipconfirm = skipconfirm
        self._exitstate = exitstate

        self._dialog_context = None

        self._click_repeat()

        if not skipconfirm:
            self._add_buttons()


    def _add_buttons (self):

        hw = base.aspect_ratio

        bt_proceed = SequenceButton(
            basetext=p_("dialog menu: go to action after the dialog",
                        "Proceed"),
            pos=Point2(hw - 0.70, -0.80),
            clickf=self._click_proceed,
            parent=self.node)

        bt_repeat = SequenceButton(
            basetext=p_("dialog menu: repeat the dialog",
                        "Repeat"),
            pos=Point2(hw - 1.20, -0.80),
            clickf=self._click_repeat,
            parent=self.node)


    def _click_proceed (self):

        if self._dialog_context is not None:
            self.cleanup_dialog_context(self._dialog_context)
        self.end(self._exitstate)


    def _click_repeat (self):

        if self._dialog_context is not None:
            self.cleanup_dialog_context(self._dialog_context)
        self._dialog_context = self.create_dialog_context()
        dc = self._dialog_context
        mc = self._menu_context
        gc = self._game_context
        dialog = self._convf(dc, mc, gc)
        dialog.canskip = True
        dialog.canend = True
        def endf ():
            if self._skipconfirm:
                self._click_proceed()
        self.wait_dialog(dialog, endf=endf)


class PauseMenu (Menu):

    def __init__ (self, wresume=True, wrestart=True, wcontrols=True,
                  wquit=True, wquitgame=True,
                  music=None, parent=None):

        Menu.__init__(self,
            name="pause-menu",
            music=music,
            fadetime=0.0,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_resume,
            parent=parent)

        hw = base.aspect_ratio

        bt_dx = 0.00 #0.04
        bt_dz = -0.15
        bt_x = 0.40
        bt_z = -0.40

        bt_resume = MissionButton(
            basetext=p_("pause menu: resume play",
                        "Resume"),
            pos=Point2(-hw + bt_x, bt_z),
            clickf=self._click_resume,
            parent=self.node)
        if not wresume:
            bt_resume.disable()
        bt_x += bt_dx; bt_z += bt_dz

        bt_restart = MissionButton(
            basetext=p_("pause menu: restart the mission",
                        "Restart"),
            pos=Point2(-hw + bt_x, bt_z),
            clickf=self._click_restart,
            parent=self.node)
        if not wrestart:
            bt_restart.disable()
        bt_x += bt_dx; bt_z += bt_dz

        bt_controls = MissionButton(
            basetext=p_("pause menu: show player controls",
                        "Controls"),
            pos=Point2(-hw + bt_x, bt_z),
            clickf=self._click_controls,
            parent=self.node)
        if not wcontrols:
            bt_controls.disable()
        bt_x += bt_dx; bt_z += bt_dz

        bt_quit = MissionButton(
            basetext=p_("pause menu: quit the mission",
                        "Quit"),
            pos=Point2(-hw + bt_x, bt_z),
            clickf=self._click_quit,
            parent=self.node)
        if not wquit:
            bt_quit.disable()
        bt_x += bt_dx; bt_z += bt_dz


    def _click_resume (self):

        self.end()


    def _click_restart (self):

        self.end("restart")


    def _click_controls (self):

        controls_menu = ControlsMenu(parent=self)
        self.wait_submenu(controls_menu)


    def _click_quit (self):

        self.end("quit")


class ShotdownInseqMenu (Menu):

    def __init__ (self, wrestart=True, wquit=True, wproceed=True,
                  music=None, parent=None):

        Menu.__init__(self,
            name="shotdown-menu",
            music=music,
            fadetime=0.0,
            pointer="images/ui/mouse_pointer.png",
            parent=parent)

        hw = base.aspect_ratio

        bt_restart = MissionButton(
            basetext=p_("pause menu: restart the mission",
                        "Restart"),
            pos=Point2(0.0, 0.15),
            clickf=self._click_restart,
            parent=self.node)
        if not wrestart:
            bt_restart.disable()

        bt_quit = MissionButton(
            basetext=p_("pause menu: quit the mission",
                        "Quit"),
            pos=Point2(-0.40, -0.15),
            clickf=self._click_quit,
            parent=self.node)
        if not wquit:
            bt_quit.disable()

        bt_proceed = MissionButton(
            basetext=p_("pause menu: go to action after the mission",
                        "Proceed"),
            pos=Point2(0.40, -0.15),
            clickf=self._click_proceed,
            parent=self.node)
        if not wproceed:
            bt_proceed.disable()


    def _click_restart (self):

        self.end("restart")


    def _click_quit (self):

        self.end("quit")


    def _click_proceed (self):

        self.end("proceed")


class ShotdownNoseqMenu (Menu):

    def __init__ (self, wrestart=True, wquit=True,
                  music=None, parent=None):

        Menu.__init__(self,
            name="shotdown-menu",
            music=music,
            fadetime=0.0,
            pointer="images/ui/mouse_pointer.png",
            parent=parent)

        hw = base.aspect_ratio

        bt_restart = MissionButton(
            basetext=p_("pause menu: restart the mission",
                        "Restart"),
            pos=Point2(0.0, 0.12),
            clickf=self._click_restart,
            parent=self.node)
        if not wrestart:
            bt_restart.disable()

        bt_quit = MissionButton(
            basetext=p_("pause menu: quit the mission",
                        "Quit"),
            pos=Point2(0.0, -0.12),
            clickf=self._click_quit,
            parent=self.node)
        if not wquit:
            bt_quit.disable()


    def _click_restart (self):

        self.end("restart")


    def _click_quit (self):

        self.end("quit")


class ControlsMenu (Menu):

    def __init__ (self, parent=None):

        Menu.__init__(self,
            name="controls-menu",
            music=None,
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_exit,
            parent=parent)

        hw = base.aspect_ratio

        bg = make_image("images/ui/black.png",
                        size=(2 * hw), pos=Point2(0.0, 0.0),
                        parent=self.node)
        bg.setSa(0.85)

        make_text(_("CONTROLS"),
                  width=2.0, pos=Point2(0.0, 0.92),
                  font=ui_font_path, size=32, ppunit=100,
                  color=rgba(255, 0, 0, 1.0),
                  align="c", anchor="mc",
                  parent=self.node)

        bt_exit = MainSmallButton(
            basetext=p_("controls menu: go to the previous menu",
                        "Go Back"),
            pos=Point2(0.0, -0.90),
            clickf=self._click_exit,
            parent=self.node)

        bindings = base.inputconf.bindings
        table_bindings_spec = []
        for bindg in bindings:
            fmtseq = base.inputconf.format_binding_sequence(bindg.seqs)
            desc = bindg.desc
            if bindg.note is not None:
                note = "[%s] %s" % (bindg.name, bindg.note)
            else:
                note = "[%s]" % bindg.name
            spec = (fmtseq, (desc, desc, note))
            table_bindings_spec.append(spec)

        fr_missions = ScrollTable(
            colspec=[
                (p_("column name", "Binding"), 0.30),
                (p_("column name", "Description"), 0.70, True),
            ],
            rowdata=table_bindings_spec,
            sortcol=-1,
            noclicksort=True,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=12, notetextsize=10,
            size=(1.90, 1.60),
            pos=Point2(0.0, 0.02),
            parent=self.node)


    def destroy (self):

        Menu.destroy(self)


    def _click_exit (self):

        self.end()


KILL_STATS_FAMILIES = [ # ordered by appearance
    "plane",
    "heli",
    "vehicle",
    "ship",
    "building",
]

class DebriefingMenu (Menu):

    def __init__ (self, objcomp=None, kills=None, parent=None):

        Menu.__init__(self,
            name="debriefing-menu",
            fadetime=(0.25, 0.25),
            pointer="images/ui/mouse_pointer.png",
            quickexit=self._click_proceed,
            parent=parent)

        make_text(_("DEBRIEFING"),
                  width=2.0, pos=Point2(0.0, 0.65),
                  font=ui_font_path, size=48, ppunit=100,
                  color=rgba(255, 0, 0, 1.0),
                  align="c", anchor="mc",
                  parent=self.node)

        text_props_sub = AutoProps(size_factor=0.8,
                                   para_spacing=0.0, block_indent=0.05)

        st = []
        if objcomp is True:
            objcomp = [_("Mission objectives completed.")]
        elif not objcomp:
            objcomp = [_("Mission failed.")]
        if isinstance(objcomp, basestring):
            objcomp = [objcomp]
        for objcomp_1 in objcomp:
            if isinstance(objcomp_1, tuple):
                objcomp_1, sub_1 = objcomp_1
            else:
                sub_1 = False
            if sub_1:
                st.append((objcomp_1, text_props_sub))
            else:
                st.append(objcomp_1)
        if objcomp:
            st.append(HorizRule())
        kills_by_family = {}
        for kill in kills or []:
            if kill.family in KILL_STATS_FAMILIES:
                kill_list_fam = kills_by_family.get(kill.family)
                if kill_list_fam is None:
                    kill_list_fam = []
                    kills_by_family[kill.family] = kill_list_fam
                kill_list_fam.append(kill)
        for family in KILL_STATS_FAMILIES: # in this order
            kill_list_fam = kills_by_family.get(family)
            if not kill_list_fam:
                continue
            if family == "plane":
                head = _("Airplanes shot down:")
                otherdes = p_("other airplane types", "(other)")
            elif family == "heli":
                head = _("Helicopters shot down:")
                otherdes = p_("other helicopter types", "(other)")
            elif family == "vehicle":
                head = _("Vehicles knocked out:")
                otherdes = p_("other vehicle types", "(other)")
            elif family == "ship":
                head = _("Ships sunk:")
                otherdes = p_("other ship types", "(other)")
            elif family == "building":
                head = _("Buildings destroyed:")
                otherdes = p_("other building types", "(other)")
            else:
                assert False
            st.append("%s  %d" % (head, len(kill_list_fam)))
            kills_by_des = {}
            for kill in kill_list_fam:
                des = (kill.shortdes or otherdes)
                kill_list_des = kills_by_des.get(des)
                if kill_list_des is None:
                    kill_list_des = []
                    kills_by_des[des] = kill_list_des
                kill_list_des.append(kill)
            kill_list_des_other = kills_by_des.get(otherdes)
            if kill_list_des_other is not None:
                kills_by_des.pop(otherdes)
            srt_kills_by_des = sorted(kills_by_des.items())
            if kill_list_des_other is not None:
                srt_kills_by_des.append((otherdes, kill_list_des_other))
            style = 1
            if style == 1:
                for des, kill_list_des in srt_kills_by_des:
                    st.append((u"%s — %d" % (des, len(kill_list_des)),
                              text_props_sub))
            elif style == 2:
                els = []
                for des, kill_list_des in srt_kills_by_des:
                    nk = len(kill_list_des)
                    if nk == 1:
                        els.append(des)
                    else:
                        els.append(p_("vehicle type and number",
                                      "%(type)s (%(num)d)") %
                                   dict(type=des, num=nk))
                jstr = p_("string for joining list elements", ", ")
                st.append((jstr.join(els), text_props_sub))
            else:
                assert False
        ScrollText(
            text=st,
            textfont=ui_font_path,
            textcolor=rgba(255, 0, 0, 1.0),
            textsize=16,
            size=(1.2, 1.0),
            pos=Point2(0.0, 0.0),
            para_spacing=0.25,
            line_width=0.005,
            rule_length=0.5,
            parent=self.node)

        bt_proceed = MissionButton(
            basetext=p_("debriefing menu: go to action after the debriefing",
                        "Proceed"),
            pos=Point2(0.0, -0.65),
            clickf=self._click_proceed,
            parent=self.node)


    def destroy (self):

        Menu.destroy(self)


    def _click_proceed (self):

        self.end("proceed")


class LoadingScreen (object):

    def __init__ (self):

        self.node = base.uiface_root.attachNewNode("loading-screen")

        self._title_text = None
        self._title_text_node = None
        self._progress_text = None
        self._progress_text_node = None

        self.alive = True


    def set_title_text (self, text):

        if self._title_text != text:
            self._title_text = text
            if self._title_text_node is not None:
                self._title_text_node.removeNode()
            self._title_text_node = make_text(
                text=text,
                width=2.0, pos=Point2(0.0, -0.54),
                font=ui_font_path, size=24, ppunit=100,
                color=rgba(255, 0, 0, 1.0),
                align="c", anchor="bc",
                parent=self.node)


    def set_progress_text (self, text):

        if self._progress_text != text:
            self._progress_text = text
            if self._progress_text_node is not None:
                self._progress_text_node.removeNode()
            self._progress_text_node = make_text(
                text=text,
                width=2.0, pos=Point2(0.0, -0.56),
                font=ui_font_path, size=12,
                color=rgba(255, 0, 0, 1.0),
                align="c", anchor="tc",
                parent=self.node)


    def clear (self):

        if self._title_text_node is not None:
            self._title_text = None
            self._title_text_node.removeNode()
            self._title_text_node = None
        if self._progress_text_node is not None:
            self._progress_text = None
            self._progress_text_node.removeNode()
            self._progress_text_node = None


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


class NarrowAspect (DirectObject):

    def __init__ (self, narrowasc=1.25):

        DirectObject.__init__(self)

        realasc = base.aspect_ratio
        if narrowasc > realasc:
            narrowasc = realasc

        self._node = NodePath("narrow-aspect")
        self._active = False
        sidew = realasc - narrowasc
        img = make_image(
            texture="images/ui/white.png",
            size=(sidew, 2.0),
            pos=Point2(-realasc + sidew * 0.5, 0.0),
            parent=self._node)
        img.setColor(rgba(32, 32, 32, 1.0))
        img = make_image(
            texture="images/ui/white.png",
            size=(sidew, 2.0),
            pos=Point2(+realasc - sidew * 0.5, 0.0),
            parent=self._node)
        img.setColor(rgba(32, 32, 32, 1.0))

        self.accept("shift-control-n", self._toggle_aspect)

        self.alive = True


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.ignoreAll()
        self._node.removeNode()


    def _toggle_aspect (self):

        if self._active:
            self._node.detachNode()
            self._active = False
        else:
            self._node.reparentTo(base.front_root)
            self._active = True


