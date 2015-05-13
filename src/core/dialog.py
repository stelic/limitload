# -*- coding: UTF-8 -*-

from math import degrees, atan2

from direct.gui.DirectGui import DirectButton
from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import Point2, VBase3, Vec3, Point3
from pandac.PandaModules import NodePath, TextNode
from pandac.PandaModules import TransparencyAttrib

from src.core.misc import rgba, SimpleProps, AutoProps, as_sequence
from src.core.misc import reading_time, make_text, font_scale_for_ptsize
from src.core.misc import map_pos_to_screen, get_pointer, node_swipe
from src.core.misc import node_fade_to, node_slide_to, kill_tasks
from src.core.misc import make_image, set_texture
from src.core.misc import unitv, intl01vr, segment_intersect_2d
from src.core.misc import choice as randchoice
from src.core.sound import Sound2D
from src.core.transl import *


FONT_ROC = "fonts/red-october-regular.otf"
FONT_DJV = "fonts/DejaVuSans-Bold.ttf"
FONT_VDD = "fonts/vps-dong-da-hoa.ttf"
FONT_TGA = "fonts/TeXGyreAdventor-Bold.otf"
FONT_RUS = "fonts/Russo.ttf"
FONT_DLG = FONT_DJV

class Dialog (DirectObject):

    _dialogs_in_progress = set()

    _dt_function = None
    _autoplace_offset_function = None

    # See set_defaults for possible parameters.
    # A value given here will override the default value,
    # except for:
    # - characters: when the value is actually a CharMod,
    #       it will be applied to the linked default character,
    #       and the resulting character will be taken instead.
    # - charmods: added to default items, overriding those with same keys.
    # - named*: added to default items, overriding those with same keys.
    # All parameter values will be available as attributes of the dialog.
    def __init__ (self, **kwargs):

        DirectObject.__init__(self)

        if self._top is None:
            self.set_defaults()
        for key, defval in self._top.iteritems():
            if key in kwargs:
                val = kwargs.pop(key)
                if key == "characters":
                    characters = {}
                    for name, char in val.iteritems():
                        if isinstance(char, CharMod):
                            char = char.supplement(defval[name])
                        characters[name] = char
                    val = characters
                elif key == "charmods" or key.startswith("named"):
                    combval = dict(defval)
                    combval.update(val)
                    val = combval
            else:
                val = defval
            self.__dict__[key] = val
        if kwargs:
            raise StandardError(
                "Unknown parameters passed to dialog constructor: %s."
                % (", ".join(sorted(kwargs.keys()))))

        self._in_progress = False
        self._swipe_duration = 0.2
        self._min_wait_time_read = 2.0

        self._speakers_on_stage = set()
        self._decos = {}
        self._silent_alpha = 0.5
        self._silent_fade_time = 0.1
        self._ref_line_voff = 1.2
        self._ref_num_lines = 5

        self._autoplace_margin = Point3(0.1, 0.0, 0.06)
        self._autoplace_skip = Point3(0.03, 0.0, 0.03)
        self._autoplace_slide_duration = 0.25
        self._autoplace_played_prio = 100
        self._autoplace_on_played_prio = 10
        self._autoplace_played_char_node = None
        for name, char in self.characters.items():
            if char.played:
                self._autoplace_played_char_node = char.node
                break

        self._showborders_color = rgba(255, 0, 0, 0.3)


    def start (self):

        if self._in_progress:
            self.stop()

        self._dialogs_in_progress.add(self)

        self._current_branch = self.branches["start"]
        self._next_item_index = 0
        self._item_contexts = []
        self._proceeded_items = set()

        self._node = self.pnode.attachNewNode("dialog")

        self._autoplace_node = self._node.attachNewNode("autoplace")
        hw = base.aspect_ratio
        self._autoplace_base_pos = Point3(-hw, 0.0, 1.0)
        self._autoplace_node.setPos(self._autoplace_base_pos)
        self._autoplace_charids = set()
        self._autoplace_just_added = set()
        self._autoplace_auto_entered_track = {}

        for name, char in self.characters.items():
            self._decos[name] = self._make_deco(name, char)

        self._last_base_screen_pos = dict((x, Point3())
                                          for x in self.characters.keys())

        self._skip_seq = "space"
        self.accept(self._skip_seq, self._handle_skip)
        base.set_priority("dialog", self._skip_seq, 20)
        self._end_seq = "escape"
        self.accept(self._end_seq, self._handle_end)
        base.set_priority("dialog", self._end_seq, 20)

        self._in_progress = True
        task = base.taskMgr.add(self._loop, "dialog")
        task.prev_time = 0.0


    def _make_deco (self, name, char):

        deco = SimpleProps()

        autoplace = self._res_autoplace(char.node, char.autoplace)
        pnode = self._autoplace_node if autoplace else self._node
        deco.node = pnode.attachNewNode("deco-%s" % name)
        deco.node.setSa(0.0)

        deco.talking_contexts = []
        deco.offset_node_fade_task = None
        deco.offset_node_to_alpha = 1.0
        deco.offset_node_slide_task = None

        deco.offset_node = None
        deco.offset_node_target_pos = None
        deco.outscr_arrow_node = None
        self._compose_deco_elements(char, deco)

        return deco


    def _compose_deco_elements (self, char, deco):

        if deco.offset_node is not None:
            deco.offset_node.removeNode()
        deco.offset_node = deco.node.attachNewNode("offset")
        deco.offset_node.setSa(deco.offset_node_to_alpha)

        autoplace = self._res_autoplace(char.node, char.autoplace)

        csize = self._res_size(char.size)
        cfscale = font_scale_for_ptsize(csize)
        cwidth = self._res_width(char.width) if not autoplace else self.aplwidth
        reftextw = cwidth
        reftexth = cfscale * self._ref_line_voff * self._ref_num_lines
        gapw = cfscale * 0.5
        gaph = cfscale * 0.2

        autoportrait = self.aplportrait if autoplace else None
        anchor = char.anchor if not autoplace else "tl"
        ignore_shortdes = (not char.shortdes or
                           (anchor == "mc" and not autoplace) or
                           (isinstance(char.node, NodePath) and not autoplace))
        ignore_portrait = (not self._res_portrait(char, autoportrait) or
                           (anchor == "mc" and not autoplace) or
                           (isinstance(char.node, NodePath) and not autoplace) or
                           self.cutportraits)
        only_text = ignore_shortdes and ignore_portrait

        if True: # text
            if self.showborders and not only_text:
                bbw = reftextw
                bbh = reftexth
                if "l" in anchor:
                    bbx = reftextw * 0.5
                elif "r" in anchor:
                    bbx = reftextw * -0.5
                else: # "c" in anchor:
                    bbx = 0.0
                if "t" in anchor:
                    bbz = reftexth * -0.5
                elif "b" in anchor:
                    bbz = reftexth * 0.5
                else: # "m" in anchor:
                    bbz = 0.0
                bbnode = make_image("images/ui/white.png",
                                    size=(bbw, bbh),
                                    pos=Point3(bbx, 0.0, bbz),
                                    parent=deco.offset_node)
                bbnode.setColor(self._showborders_color)

        if not ignore_portrait:
            cprtsize = (self._res_prtsize(char.prtsize)
                        if not autoplace else self.aplprtsize)
            prtw = cprtsize * char.prtaspect
            prth = cprtsize
            if "l" in anchor:
                prtx = prtw * -0.5 - gapw
                turn_side = 0
            elif "r" in anchor:
                prtx = prtw * 0.5 + gapw
                turn_side = 180
            else: # "c" in anchor:
                prtx = 0.0
                if "t" in anchor:
                    turn_side = 0
                else:
                    turn_side = 180
            if "t" in anchor:
                if "c" in anchor:
                    prtz = prth * 0.5 + gaph
                else:
                    prtz = prth * -0.5
            elif "b" in anchor:
                if "c" in anchor:
                    prtz = prth * -0.5 - gaph
                else:
                    prtz = prth * 0.5
            else: # "m" in anchor:
                prtz = 0.0
            portrait_path = self._res_portrait(char, autoportrait)
            pnode = make_image(texture=portrait_path,
                               size=cprtsize,
                               pos=Point3(prtx, 0.0, prtz),
                               hpr=Vec3(turn_side, 0.0, 0.0),
                               twosided=True,
                               parent=deco.offset_node)
            if self.showborders:
                pbw = prtw
                pbh = prth
                pbx = prtx
                pbz = prtz
                pbnode = make_image("images/ui/white.png",
                                    size=(pbw, pbh),
                                    pos=Point3(pbx, 0.0, pbz),
                                    parent=deco.offset_node)
                pbnode.setColor(self._showborders_color)
                pnode.reparentTo(pnode.getParent()) # move to front
        else:
            deco.portrait_node = None

        if not ignore_shortdes:
            dtext = char.shortdes
            #dtext = _("%s:") % char.shortdes
            #dtext = _("[%s]") % char.shortdes
            dfont = char.font or self.font
            dsize = csize
            if not ignore_portrait:
                extw = prtw + gapw
                exth = prth + gaph
            else:
                extw = 0.0
                exth = 0.0
            gaptlh = cfscale * (self._ref_line_voff - 1.0)
            dfscale = font_scale_for_ptsize(dsize)
            danchor = ""
            if "l" in anchor:
                if "m" in anchor:
                    danch = "r"
                    dalign = "r"
                    descx = -gapw
                else:
                    danch = "l"
                    dalign = "l"
                    descx = -extw
            elif "r" in anchor:
                if "m" in anchor:
                    danch = "l"
                    dalign = "l"
                    descx = gapw
                else:
                    danch = "r"
                    dalign = "r"
                    descx = extw
            else: # "c" in anchor:
                danch = "c"
                dalign = "c"
                descx = 0.0
            if "t" in anchor:
                dancv = "b"
                if "c" in anchor:
                    descz = exth + gaph
                else:
                    descz = gaph
            elif "b" in anchor:
                dancv = "t"
                if "c" in anchor:
                    descz = -exth - gaph
                else:
                    descz = -gaph
            else: # "m" in anchor:
                if not ignore_portrait:
                    dancv = "b"
                    descz = exth * 0.5 + gaph * 0.5
                else:
                    dancv = "c"
                    descz = 0.0
            danchor = dancv + danch
            dnode = make_text(text=dtext, width=cwidth,
                              font=dfont, size=dsize,
                              color=char.color, shcolor=char.shcolor,
                              olcolor=char.olcolor, olwidth=char.olwidth,
                              olfeather=char.olfeather,
                              align=dalign, anchor=danchor,
                              smallcaps=True, underscore=ignore_portrait,
                              pos=Point3(descx, 0.0, descz),
                              parent=deco.offset_node)
            dnode.setTransparency(TransparencyAttrib.MAlpha)
            # ...or else underscore will not react to alpha.
            if self.showborders:
                dbw = cwidth * 1.0
                dbh = cfscale #* self._ref_line_voff
                if "l" in danchor:
                    if "l" in anchor:
                        dbw += extw
                    dbx = descx + dbw * 0.5
                elif "r" in danchor:
                    if "r" in anchor:
                        dbw += extw
                    dbx = descx + dbw * -0.5
                else: # "c" in danchor:
                    dbx = descx
                if "t" in danchor:
                    dbz = descz + dbh * -0.5
                elif "b" in danchor:
                    dbz = descz + dbh * 0.5
                else: # "m" in danchor:
                    dbz = descz
                dbnode = make_image("images/ui/white.png",
                                    size=(dbw, dbh),
                                    pos=Point3(dbx, 0.0, dbz),
                                    parent=deco.offset_node)
                dbnode.setColor(self._showborders_color)
                dnode.reparentTo(dnode.getParent()) # move to front

        if self.showborders and not only_text:
            opnode = make_image("images/ui/white.png",
                                parent=deco.offset_node)
            opnode.setColor(rgba(255, 255, 255, 1.0))
            opnode.setScale(0.01)
            if not ignore_shortdes:
                dpnode = make_image("images/ui/white.png",
                                    pos=Point3(descx, 0.0, descz),
                                    parent=deco.offset_node)
                dpnode.setColor(rgba(255, 255, 0, 1.0))
                dpnode.setScale(0.01)

        if isinstance(char.node, NodePath):
            if deco.outscr_arrow_node is not None:
                deco.outscr_arrow_node.removeNode()
            deco.outscr_arrow_size = 0.08
            deco.outscr_arrow_node = deco.node.attachNewNode("outscr-arrow")
            deco.outscr_arrow_node.hide()
            deco.outscr_arrow_bg_node = make_image(
                "images/ui/outside_screen_arrow.png",
                size=(deco.outscr_arrow_size * 0.8),
                parent=deco.outscr_arrow_node)
            deco.outscr_arrow_fg_node = deco.outscr_arrow_bg_node.copyTo(
                deco.outscr_arrow_node)
            color = char.color
            deco.outscr_arrow_fg_node.setColor(color)
            #shcolor = char.shcolor
            shcolor = rgba(0, 0, 0, 1.0)
            deco.outscr_arrow_bg_node.setColor(shcolor)
            shadow_off = deco.outscr_arrow_size * 0.05
            deco.outscr_arrow_bg_node.setPos(shadow_off, 0.0, -shadow_off)

        # Delay bounds evaluation because expensive and not always needed.
        deco.offset_node_bounds = None
        deco.char_node_bounds = None # used in self._res_pos

        if not autoplace:
            cpos = self._res_pos(deco, char.node, char.offset,
                                 char.pos, char.posx, char.posz)
        else:
            if deco.offset_node_target_pos is None:
                deco.offset_node_target_pos = Point3()
            cpos = deco.offset_node_target_pos
        deco.offset_node.setPos(cpos)


    def stop (self):

        if not self._in_progress:
            return

        self._dialogs_in_progress.remove(self)

        self._node.removeNode()
        self.ignoreAll()
        base.remove_priority("dialog")
        self._in_progress = False


    def in_progress (self):

        return self._in_progress


    _top = None

    @classmethod
    def set_defaults (cls,
                      pnode=None, camnode=None,
                      characters={}, charmods={}, branches={},
                      wpmspeed=100, font=FONT_DLG,
                      choicepos=(None, -0.85), choicebox=(None, 0.05),
                      choicesize=10, choicecolor=rgba(128, 128, 128, 1.0),
                      unfoldfac=0.0,
                      autoplace=False, aplportrait=None, aplprtsize=0.2,
                      aplwidth=0.8,
                      canskip=False, canend=False,
                      cutportraits=False,
                      namedpos={}, namedsizes={}, namedwidths={},
                      namedprtsizes={}, namedctimes={},
                      showborders=False, testlongtext=False):

        if cls._top is None:
            cls._top = SimpleProps()
        cls._top.pnode = pnode
        cls._top.camnode = camnode
        cls._top.characters = characters
        cls._top.charmods = charmods
        cls._top.branches = branches
        cls._top.wpmspeed = wpmspeed
        cls._top.font = font
        cls._top.choicepos = choicepos
        cls._top.choicebox = choicebox
        cls._top.choicesize = choicesize
        cls._top.choicecolor = choicecolor
        cls._top.unfoldfac = unfoldfac
        cls._top.autoplace = autoplace
        cls._top.aplportrait = aplportrait
        cls._top.aplprtsize = aplprtsize
        cls._top.aplwidth = aplwidth
        cls._top.canend = canend
        cls._top.canskip = canskip
        cls._top.cutportraits = cutportraits
        cls._top.namedpos = namedpos
        cls._top.namedsizes = namedsizes
        cls._top.namedwidths = namedwidths
        cls._top.namedprtsizes = namedprtsizes
        cls._top.namedctimes = namedctimes
        cls._top.showborders = showborders
        cls._top.testlongtext = testlongtext


    @classmethod
    def stop_all_dialogs (cls):

        for d in list(cls._dialogs_in_progress): # .stop() modifies the set
            d.stop()


    def _loop (self, task):

        if self.pnode.isEmpty():
            self.stop()
            return task.done

        if not self._in_progress:
            return task.done

        if Dialog._dt_function:
            dt = Dialog._dt_function()
        else:
            dt = task.time - task.prev_time
        task.prev_time = task.time

        new_item_contexts = []
        proceed = True
        tobranch = None
        for i, item_context in enumerate(self._item_contexts):

            finished, proceed1, tobranch1 = item_context.updatef(dt)

            if not finished:
                new_item_contexts.append(item_context)
                if proceed1:
                    self._proceeded_items.add(item_context)
            elif item_context in self._proceeded_items:
                self._proceeded_items.remove(item_context)

            if (not finished and not proceed1 and
                item_context not in self._proceeded_items):
                proceed = False

            if tobranch1 is not None and self._next_item_index > 0:
                tobranch = tobranch1
                if tobranch not in self.branches:
                    raise StandardError(
                        "Trying to jump to unknown branch '%s' in dialog."
                        % tobranch)
                self._current_branch = self.branches[tobranch]
                self._next_item_index = 0

        self._item_contexts = new_item_contexts

        if proceed:
            item_context = None
            while (self._next_item_index < len(self._current_branch) and
                   item_context is None):
                item = self._current_branch[self._next_item_index]

                if isinstance(item, Speech):
                    if item.speaker in self._speakers_on_stage:
                        item_context = self._start_speech(item)
                        self._next_item_index += 1
                    else:
                        self._speakers_on_stage.add(item.speaker)
                        entry = Entry(speaker=item.speaker, ctime=0.0)
                        item_context = self._start_entry_or_exit(entry)
                        char = self.characters[item.speaker]
                        autoplace = self._res_autoplace(char.node, char.autoplace)
                        if autoplace:
                            self._autoplace_auto_entered_track[item.speaker] = [True]

                elif isinstance(item, Pause):
                    item_context = self._start_pause(item)
                    self._next_item_index += 1

                elif isinstance(item, Entry):
                    if item.speaker is True:
                        test_speakers = self.characters.keys()
                    else:
                        test_speakers = as_sequence(item.speaker)
                    add_speakers = []
                    for speaker in test_speakers:
                        if speaker not in self._speakers_on_stage:
                            self._speakers_on_stage.add(speaker)
                            add_speakers.append(speaker)
                    item.speaker = add_speakers
                    item_context = self._start_entry_or_exit(item)
                    self._next_item_index += 1

                elif isinstance(item, Exit):
                    if item.speaker is True:
                        test_speakers = self.characters.keys()
                    else:
                        test_speakers = as_sequence(item.speaker)
                    rem_speakers = []
                    for speaker in test_speakers:
                        if speaker in self._speakers_on_stage:
                            self._speakers_on_stage.remove(speaker)
                            rem_speakers.append(speaker)
                        if speaker in self._autoplace_auto_entered_track:
                            self._autoplace_auto_entered_track.pop(speaker)
                    item.speaker = rem_speakers
                    item_context = self._start_entry_or_exit(item)
                    self._next_item_index += 1

                elif isinstance(item, UpdateChar):
                    item_context = self._start_char_update(item)
                    self._next_item_index += 1

                else:
                    raise StandardError("Unknown branch item in dialog.")

                if item_context is not None:
                    finished, proceed1, tobranch1 = item_context.updatef(0.0)
                    if not finished or tobranch1:
                        self._item_contexts.append(item_context)
                    else:
                        item_context = None

            if item_context is None:
                self.stop()
                return task.done

        auto_exit_speakers = []
        for speaker, pack in self._autoplace_auto_entered_track.items():
            active, = pack
            if not active:
                auto_exit_speakers.append(speaker)
        if auto_exit_speakers:
            exit = Exit(speaker=auto_exit_speakers, ctime=0.0)
            for speaker in auto_exit_speakers:
                self._speakers_on_stage.remove(speaker)
                self._autoplace_auto_entered_track.pop(speaker)
            item_context = self._start_entry_or_exit(exit)
            finished, proceed1, tobranch1 = item_context.updatef(0.0)
            if not finished:
                self._item_contexts.append(item_context)

        self._update_autoplace()
        # ...at this point, all deco bounds have been updated.

        return task.cont


    def _update_decos (self):

        talking_charids = set()
        for charid, deco in self._decos.iteritems():
            if deco.talking_contexts:
                talking_charids.add(charid)
        for charid, deco in self._decos.iteritems():
            #if talking_charids and charid not in talking_charids:
            if charid not in talking_charids:
                from_alpha, to_alpha = 1.0, self._silent_alpha
            else:
                from_alpha, to_alpha = self._silent_alpha, 1.0
            if deco.offset_node_to_alpha != to_alpha:
                kill_tasks(deco.offset_node_fade_task)
                current_alpha = deco.offset_node.getSa()
                duration = intl01vr(current_alpha, from_alpha, to_alpha,
                                    0.0, self._silent_fade_time)
                if duration > 0.0:
                    task = node_fade_to(deco.offset_node,
                                        endalpha=to_alpha, duration=duration)
                else:
                    task = None
                    deco.offset_node.setSa(to_alpha)
                deco.offset_node_fade_task = task
                deco.offset_node_to_alpha = to_alpha


    def _update_autoplace (self):

        prio_charid = []
        for charid in self._autoplace_charids:
            char = self.characters[charid]
            if char.aplprio is None:
                if char.played:
                    prio = self._autoplace_played_prio
                elif (char.node is not None and
                      char.node is self._autoplace_played_char_node):
                    prio = self._autoplace_on_played_prio
                else:
                    prio = 0
            else:
                prio = char.aplprio
            prio_charid.append((prio, charid))
        prio_charid.sort(key=lambda x: -x[0]) # do not sort by ID

        sum_width = self._autoplace_margin[0]
        sum_height = self._autoplace_margin[2]
        for prio, charid in prio_charid:
            deco = self._decos[charid]
            if deco.offset_node_bounds is None:
                tmp_pos = deco.offset_node.getPos()
                deco.offset_node.setPos(0.0, 0.0, 0.0)
                deco.offset_node_bounds = deco.offset_node.getTightBounds()
                deco.offset_node.setPos(tmp_pos)
            bmin, bmax = deco.offset_node_bounds
            pos = Point3(sum_width - bmin[0], 0.0, -(sum_height + bmax[2]))
            sum_height += bmax[2] - bmin[2] + self._autoplace_skip[2]
            if (pos - deco.offset_node_target_pos).length() > 1e-3:
                deco.offset_node_target_pos = pos
                kill_tasks(deco.offset_node_slide_task)
                if charid in self._autoplace_just_added:
                    self._autoplace_just_added.remove(charid)
                    deco.offset_node.setPos(pos)
                    deco.offset_node_slide_task = None
                else:
                    task = node_slide_to(node=deco.offset_node, endpos=pos,
                                         duration=self._autoplace_slide_duration)
                    deco.offset_node_slide_task = task

        if Dialog._autoplace_offset_function:
            off = Dialog._autoplace_offset_function()
            self._autoplace_node.setPos(self._autoplace_base_pos + off)


    def _start_speech (self, item):

        if isinstance(item.line, Line): # single line
            item_context = self._start_line(item.line, item.speaker, item.charmod)
        else: # choice of lines
            item_context = self._start_choice(item.line, item.speaker, item.charmod)
        return item_context


    def _start_line (self, line, charid, cmod):

        if not self._is_line_active(line):
            return None

        char = self._res_character(charid, cmod)
        deco = self._decos[charid]

        autoplace = self._res_autoplace(char.node, char.autoplace)
        anchor = char.anchor if not autoplace else "tl"
        align = char.align if not autoplace else "l"

        font = line.font or char.font or self.font
        text = line.text
        if self.testlongtext:
            tail = lorem_ipsum(int(len(text) * 0.25 + 0.5))
            text += " " + tail
        if not autoplace:
            cpos = self._res_pos(deco, char.node, char.offset,
                                 char.pos, char.posx, char.posz)
            deco.offset_node.setPos(cpos)
        csize = self._res_size(char.size)
        cwidth = self._res_width(char.width) if not autoplace else self.aplwidth
        make_text_node = lambda atext, pnode: make_text(
            text=atext, width=cwidth,
            font=font, size=csize,
            smallcaps=char.smallcaps, underscore=char.underscore,
            color=char.color, shcolor=char.shcolor,
            olcolor=char.olcolor, olwidth=char.olwidth,
            olfeather=char.olfeather,
            align=align, anchor=anchor,
            parent=pnode)
        textnode = make_text_node(text, deco.offset_node)
        textnode.hide()

        # Make short one-line texts close to anchor.
        if align != anchor[1]:
            bmin, bmax = textnode.getTightBounds()
            bbox = bmax - bmin
            twidth, theight = bbox[0], bbox[2]
            cfscale = font_scale_for_ptsize(csize)
            if twidth < cwidth - cfscale * 0.5 and theight < cfscale * 1.5:
                hdi = {"l": 0, "c": 1, "r": 2}
                dxfac = 0.5 * (hdi[anchor[1]] - hdi[align])
                textnode.setX((cwidth - twidth) * dxfac)

        # Bounds calculation must take place after text has been prepared.
        # Position must be temporarily reset, for proper bounds.
        if isinstance(char.node, NodePath) or autoplace:
            tmp_pos = deco.offset_node.getPos()
            deco.offset_node.setPos(0.0, 0.0, 0.0)
            deco.offset_node_bounds = deco.offset_node.getTightBounds()
            deco.offset_node.setPos(tmp_pos)

        # Out-of-screen constants.
        if isinstance(char.node, NodePath) and not autoplace:
            (bxbl, d1, bzbl), (bxtr, d2, bztr) = deco.offset_node_bounds
            outscrsize = deco.outscr_arrow_size
            margindxl = bxbl - outscrsize
            margindxr = bxtr + outscrsize
            margindzb = bzbl - outscrsize
            margindzt = bztr + outscrsize
            hw = base.aspect_ratio
            if Dialog._screen_size_function:
                minx, maxx, minz, maxz = Dialog._screen_size_function()
            else:
                minx, maxx, minz, maxz = -hw, hw, -1.0, 1.0
            mc1t = Point2(minx - margindxl, minz - margindzb)
            mc2t = Point2(maxx - margindxr, minz - margindzb)
            mc3t = Point2(maxx - margindxr, maxz - margindzt)
            mc4t = Point2(minx - margindxl, maxz - margindzt)
            margin_edges_text = ((mc1t, mc2t), (mc2t, mc3t),
                                 (mc3t, mc4t), (mc4t, mc1t))
            mc1o = Point2(minx + 0.5 * outscrsize, minz + 0.5 * outscrsize)
            mc2o = Point2(maxx - 0.5 * outscrsize, minz + 0.5 * outscrsize)
            mc3o = Point2(maxx - 0.5 * outscrsize, maxz - 0.5 * outscrsize)
            mc4o = Point2(minx + 0.5 * outscrsize, maxz - 0.5 * outscrsize)
            margin_edges_outscr = ((mc1o, mc2o), (mc2o, mc3o),
                                   (mc3o, mc4o), (mc4o, mc1o))
            boff = Point3(0.5 * (bxbl + bxtr), 0.0, 0.5 * (bzbl + bztr))

        uc = AutoProps()

        if line.voice:
            path = line.voice
            if "/" not in path:
                path = "audio/voices/%s" % path
            volume = line.volume if line.volume is not None else 1.0
            uc.sound = Sound2D(path=path, pnode=textnode, volume=volume)

        if uc.sound:
            uc.wait_time_read = uc.sound.length()
            if line.time:
                uc.wait_time_read = max(uc.wait_time_read, line.time)
        elif line.time:
            uc.wait_time_read = line.time
        else:
            cwpmspeed = char.wpmspeed or self.wpmspeed
            uc.wait_time_read = reading_time(text, wpm=cwpmspeed)
            if uc.wait_time_read < self._min_wait_time_read:
                uc.wait_time_read = self._min_wait_time_read
        if line.timefac:
            uc.wait_time_read *= line.timefac

        if line.ctimefac is not None:
            ctimefac = line.ctimefac
            if ctimefac > 0.0:
                uc.wait_time_cont = uc.wait_time_read * ctimefac
            else:
                uc.wait_time_cont = uc.wait_time_read * (1.0 + ctimefac)
        elif line.ctime is not None:
            ctime = self._res_ctime(line.ctime)
            if ctime >= 0.0:
                uc.wait_time_cont = ctime
            else:
                uc.wait_time_cont = uc.wait_time_read + ctime
        else:
            uc.wait_time_cont = None

        clinesound = char.linesound
        if clinesound:
            clinesndvol = char.linesndvol
            clinesndloop = char.linesndloop
            path = "audio/sounds/%s" % clinesound
            uc.line_sound = Sound2D(path=path, pnode=textnode,
                                    volume=clinesndvol, loop=clinesndloop)
            uc.line_sound.play()

        cunfoldfac = None
        if not isinstance(char.node, NodePath):
            cunfoldfac = char.unfoldfac
            if cunfoldfac is None:
                cunfoldfac = self.unfoldfac
            cunfoldsound = char.unfoldsound
            cunfoldsndvol = char.unfoldsndvol
        if cunfoldfac:
            cwpmspeed = char.wpmspeed or self.wpmspeed
            base_read_time = reading_time(text, wpm=cwpmspeed, raw=True)
            unfold_read_time = min(base_read_time, uc.wait_time_read)
            if unfold_read_time > 0.0:
                uc.unfolding_text_node = NodePath("dummy")
                uc.full_text_node = textnode
                textnode = deco.offset_node.attachNewNode("unfolding")
                textnode.setPos(uc.full_text_node.getPos())
                uc.full_text_node.reparentTo(textnode)
                uc.full_text_node.setPos(0.0, 0.0, 0.0)
                uc.full_text_node.hide()
                uc.text_length = len(text)
                uc.unfold_speed = uc.text_length / unfold_read_time
                uc.unfold_speed /= cunfoldfac
                uc.current_text = ""
                uc.current_pos = 0
                uc.current_float_pos = 0.0
                uc.previous_pos = 0
                if cunfoldsound:
                    path = "audio/sounds/%s" % cunfoldsound
                    uc.unfold_sound = Sound2D(path=path, pnode=textnode,
                                              volume=cunfoldsndvol, loop=True)
                    uc.unfold_sound.play()
            else:
                cunfoldfac = None

        uc.wait_time_end = None

        uc.canskip = (line.time is not None or line.ctime is not None)

        uc.stage = "wait"

        def updatef (dt):

            finished, proceed, tobranch = False, False, line.branch

            if uc.skip:
                uc.stage = "end1"

            if uc.stage == "wait":
                if not deco.talking_contexts:
                    uc.stage = "start"

            if uc.stage == "start":
                textnode.show()
                if char.swipe is not None:
                    node_swipe(textnode,
                               angledeg=char.swipe,
                               duration=self._swipe_duration)
                else:
                    pass
                for startf in as_sequence(line.startf):
                    startf()
                if uc.sound:
                    uc.sound.play()
                deco.talking_contexts.append(uc)
                self._update_decos()
                if charid in self._autoplace_auto_entered_track:
                    pack = self._autoplace_auto_entered_track[charid]
                    pack[0] = True
                uc.stage = "loop"

            if uc.stage == "loop":
                # Update line position.
                if autoplace:
                    pass

                elif isinstance(char.node, NodePath):
                    scrnode = base.uiface_root
                    if self.camnode is not None:
                        camnode = self.camnode
                    else:
                        camnode = base.stack_camera
                    if not char.node.isEmpty():
                        bpos, back = map_pos_to_screen(
                            camnode, char.node, reloff=char.offset,
                            scrnode=scrnode)
                        if back:
                            # Move out of screen if in the back.
                            bpos = unitv(bpos) * (2 * hw)
                        self._last_base_screen_pos[charid] = bpos
                    else:
                        bpos = self._last_base_screen_pos[charid]
                    cpos = self._res_pos(deco, char.node, char.offset,
                                         char.pos, char.posx, char.posz)
                    pos = bpos + cpos

                    # Fix out of screen position.
                    deco.outscr_arrow_node.hide()
                    if (pos[0] + margindxl < minx or pos[0] + margindxr > maxx or
                        pos[2] + margindzb < minz or pos[2] + margindzt > maxz):
                        a1 = Point2()
                        a2 = pos.getXz()
                        for i, (b1, b2) in enumerate(margin_edges_text):
                            c = segment_intersect_2d(a1, a2, b1, b2)
                            if c is not None:
                                pos = Point3(c[0], 0.0, c[1])
                                break
                        if not (minx < bpos[0] < maxx) or not (minz < bpos[2] < maxz):
                            a1 = (pos + boff).getXz()
                            a2 = unitv(pos.getXz()) * (2 * hw)
                            for b1, b2 in margin_edges_outscr:
                                c = segment_intersect_2d(a1, a2, b1, b2)
                                if c is not None:
                                    opos = Point3(c[0], 0.0, c[1])
                                    break
                            deco.outscr_arrow_node.setPos(opos)
                            oang = -atan2(opos[2], opos[0])
                            deco.outscr_arrow_fg_node.setR(degrees(oang))
                            deco.outscr_arrow_bg_node.setR(degrees(oang))
                            deco.outscr_arrow_node.show()

                    rpos = deco.node.getRelativePoint(scrnode, pos)
                    deco.offset_node.setPos(rpos)

                # Update unfolding.
                if cunfoldfac and uc.current_float_pos < uc.text_length:
                    uc.current_float_pos += dt * uc.unfold_speed
                    current_pos = int(uc.current_float_pos + 0.5)
                    if uc.previous_pos < current_pos:
                        #print "--unfold40", "==============", current_pos
                        uc.current_pos = min(current_pos, uc.text_length)
                        uc.unfolding_text_node.removeNode()
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
                            test_text_node = make_text_node(test_current_text, textnode)
                            tn = test_text_node.getPythonTag("nd")
                            test_wrapped_text = tn.getWordwrappedText()
                            current_lines = uc.current_text.count("\n") + 1
                            test_lines = test_wrapped_text.count("\n") + 1
                            #print "--unfold49 {%s}" % test_wrapped_text.replace("\n", "|")
                            if current_lines < test_lines:
                                uc.current_text += "\n"
                                uc.current_text += text[p2:uc.current_pos]
                            else:
                                uc.current_text += text[p1:uc.current_pos]
                            test_text_node.removeNode()
                        else:
                            uc.current_text += text[uc.previous_pos:uc.current_pos]
                        uc.unfolding_text_node = make_text_node(uc.current_text, textnode)
                        uc.previous_pos = uc.current_pos
                        #print "--unfold51 {%s}" % uc.current_text.replace("\n", "|")
                elif uc.unfold_sound:
                    uc.unfold_sound.stop()

                if uc.wait_time_read > 0.0 and not (line.isendf and line.isendf()):
                    uc.wait_time_read -= dt
                else:
                    uc.stage = "end1"

            if uc.stage == "end1":
                uc.wait_time_read = 0.0 # in case isendf terminated
                if char.swipe is not None and not uc.skip:
                    node_swipe(textnode, cover=True,
                               angledeg=char.swipe,
                               duration=self._swipe_duration,
                               endf=textnode.removeNode)
                    uc.wait_time_end = self._swipe_duration
                else:
                    textnode.removeNode()
                    uc.wait_time_end = 0.0
                uc.stage = "end2"

            if uc.stage == "end2":
                if uc.wait_time_end > 0.0:
                    uc.wait_time_end -= dt
                else:
                    for endf in as_sequence(line.endf):
                        endf()
                if uc in deco.talking_contexts:
                    deco.talking_contexts.remove(uc)
                if isinstance(char.node, NodePath):
                    deco.outscr_arrow_node.hide()
                self._update_decos()
                if uc.wait_time_cont is None or uc.wait_time_cont <= 0.0:
                    finished = True
                if charid in self._autoplace_auto_entered_track:
                    pack = self._autoplace_auto_entered_track[charid]
                    pack[0] = False
                if uc.line_sound:
                    uc.line_sound.stop()
                if uc.unfold_sound:
                    uc.unfold_sound.stop()
                uc.stage = "none"

            if uc.wait_time_cont is not None:
                uc.wait_time_cont -= dt
                if uc.wait_time_cont <= 0.0:
                    proceed = True
                    if uc.wait_time_end is not None and uc.wait_time_end <= 0.0:
                        finished = True

            return finished, proceed, tobranch

        uc.updatef = updatef

        return uc


    def _start_choice (self, lines, charid, cmod):

        lines = filter(self._is_line_active, lines)
        if not lines:
            return None

        char = self._res_character(charid, cmod)
        #deco = self._decos[charid]

        if char.played:
            # Create line menu.
            choicenode = self._node.attachNewNode("dialog-choice")
            uc = AutoProps()
            def set_choice (index, bseq=None):
                def setf ():
                    if not bseq or base.challenge_priority("dialog-choice", bseq):
                        uc.selected_line = lines[index]
                return setf
            hw = base.aspect_ratio
            margh, margv = 0.05 * hw, 0.05
            posh, posv = self.choicepos
            boxh, boxv = self.choicebox
            if boxh is None:
                boxh = hw - margh * 2
            if posh is None:
                posh = -hw + margh + boxh * 0.5
            # posx = posh # for center-aligned text
            posx = posh - boxh * 0.5 # for left-aligned text
            btheight = boxv * 1.05
            posz = posv + len(lines) * btheight / 2
            pointer = get_pointer("images/ui/mouse_pointer.png",
                                  pos=Point3(posx + boxh * 0.5, 0.0,
                                             posz + btheight * 2.0))
            bseqs = []
            for i in range(len(lines)):
                bseq = "%d" % (i + 1)
                bseqs.append(bseq)
                text = _("%(key)s. %(line)s") % dict(key=bseq, line=lines[i].text)
                make_dlg_button(text,
                                pos=(posx, posz),
                                width=boxh,
                                height=boxv,
                                font=FONT_DLG,
                                size=self.choicesize,
                                color=self.choicecolor,
                                clickf=set_choice(i),
                                parent=choicenode)
                posz -= btheight
                self.accept(bseq, set_choice(i, bseq))
                base.set_priority("dialog-choice", bseq, 20)
            pointer.show()

            uc.stage = "toselect"

            def updatef (dt):

                finished, proceed, tobranch = False, False, None

                if uc.stage == "start":
                    uc.stage = "toselect"

                if uc.stage == "toselect":
                    if uc.selected_line is not None:
                        uc.line_context = self._start_line(uc.selected_line,
                                                           charid, cmod)
                        for bseq in bseqs:
                            self.ignore(bseq)
                            base.remove_priority("dialog-choice", bseq)
                        choicenode.removeNode()
                        pointer.hide()
                        uc.stage = "selected"

                if uc.stage == "selected":
                    finished, proceed, tobranch = uc.line_context.updatef(dt)

                return finished, proceed, tobranch

            uc.updatef = updatef

            return uc

        else:
            line = randchoice(lines)
            return self._start_line(line, charid, cmod)


    def _start_pause (self, pause):

        uc = AutoProps()
        uc.stage = "start"
        uc.wait_time = pause.time

        def updatef (dt):

            finished, proceed, tobranch = False, False, pause.branch

            if uc.skip:
                uc.stage = "end"

            if uc.stage == "start":
                for startf in as_sequence(pause.startf):
                    startf()
                uc.stage = "loop"

            if uc.stage == "loop":
                done = pause.isendf() if pause.isendf else False
                if uc.wait_time > 0.0 and not done:
                    uc.wait_time -= dt
                else:
                    uc.stage = "end"

            if uc.stage == "end":
                for endf in as_sequence(pause.endf):
                    endf()
                finished = True

            return finished, proceed, tobranch

        uc.updatef = updatef

        return uc


    def _start_entry_or_exit (self, item):

        uc = AutoProps()
        uc.stage = "start"
        uc.wait_time_cont = self._res_ctime(item.ctime)

        if item.speaker is True:
            speakers = self.characters.keys()
        else:
            speakers = as_sequence(item.speaker)

        def updatef (dt):

            finished, proceed, tobranch = False, False, None

            if uc.skip:
                uc.stage = "end"

            if uc.stage == "start":
                uc.wait_time = 0.0
                for speaker in speakers:
                    deco = self._decos[speaker]
                    ret = item.effect(deco.node)
                    task, duration = ret
                    uc.wait_time = max(uc.wait_time, duration)
                if isinstance(item, Entry):
                    for speaker in speakers:
                        char = self.characters[speaker]
                        autoplace = self._res_autoplace(char.node, char.autoplace)
                        if autoplace and speaker not in self._autoplace_charids:
                            self._autoplace_charids.add(speaker)
                            self._autoplace_just_added.add(speaker)
                for startf in as_sequence(item.startf):
                    startf()
                self._update_decos()
                uc.stage = "loop"

            if uc.stage == "loop":
                if uc.wait_time > 0.0:
                    uc.wait_time -= dt
                else:
                    uc.stage = "end"

            if uc.stage == "end":
                if isinstance(item, Exit):
                    for speaker in speakers:
                        if speaker in self._autoplace_charids:
                            self._autoplace_charids.remove(speaker)
                for endf in as_sequence(item.endf):
                    endf()
                finished = True

            if uc.wait_time_cont is not None:
                uc.wait_time_cont -= dt
                if uc.wait_time_cont <= 0.0:
                    proceed = True

            return finished, proceed, tobranch

        uc.updatef = updatef

        return uc


    def _start_char_update (self, update):

        char = self.characters[update.speaker]
        upd_char = update.charmod.supplement(char)
        self.characters[update.speaker] = upd_char

        deco = self._decos[update.speaker]
        self._compose_deco_elements(upd_char, deco)

        uc = AutoProps()
        uc.updatef = lambda dt: (True, True, None)

        return uc


    def _is_line_active (self, line):

        if callable(line.cond):
            return bool(line.cond())
        else:
            return bool(line.cond)


    def _res_character (self, charid, cmod=None):

        char = self.characters.get(charid)
        if cmod is not None:
            autoplace = self._res_autoplace(char.node, char.autoplace)
            if not autoplace:
                charmod = cmod
                if isinstance(charmod, basestring):
                    charmod = self.charmods.get(cmod)
                char = charmod.supplement(char)
        return char


    def _res_named (self, val, valmap, errtext):

        if not isinstance(val, basestring):
            return val

        name = val
        val = valmap.get(name)
        if val is None:
            raise StandardError(errtext % name)
        return val


    def _res_pos (self, deco, node, offset, pos, posx=None, posz=None):

        # deprecated-start
        if posx is not None and posz is not None:
            pos = Point2(posx, posz)
        # deprecated-end

        if isinstance(pos, basestring):
            pos = self._res_named(pos, self.namedpos,
                                  "Named position '%s' not defined.")

        if pos is None and isinstance(node, NodePath):
            if deco.char_node_bounds is None:
                deco.char_node_bounds = node.getTightBounds()
            bmin, bmax = deco.char_node_bounds
            bcen = (bmin + bmax) * 0.5
            pos = Point3(0.0, 0.0, bmax[2] - bcen[2])

        if isinstance(pos, VBase3):
            if isinstance(node, NodePath):
                if self.camnode is not None:
                    camnode = self.camnode
                else:
                    camnode = base.stack_camera
                scrnode = base.uiface_root
                scr_pos_1, back = map_pos_to_screen(
                    camnode, node, reloff=offset, scrnode=scrnode)
                if offset is None:
                    offset = Point3()
                scr_pos_2, back = map_pos_to_screen(
                    camnode, node, reloff=(offset + pos), scrnode=scrnode)
                res_pos = scr_pos_2 - scr_pos_1
            else:
                res_pos = Point3(pos[0], 0.0, pos[2])
        else:
            res_pos = Point3(pos[0], 0.0, pos[1])

        return res_pos


    def _res_size (self, size):

        return self._res_named(size, self.namedsizes,
                               "Named size '%s' not defined.")


    def _res_width (self, width):

        return self._res_named(width, self.namedwidths,
                               "Named width '%s' not defined.")


    def _res_portrait (self, char, autoportrait=None):

        portrait_path = None
        if char.portrait:
            portrait_path = char.portrait
            if "." not in portrait_path:
                if portrait_path not in char.prtsel:
                    raise StandardError(
                        "Named portrait '%s' not defined." % portrait_path)
                portrait_path = char.prtsel.get(portrait_path)
        elif autoportrait:
            portrait_path = autoportrait
        if portrait_path and "/" not in portrait_path:
            portrait_path = "images/portraits/%s" % portrait_path
        return portrait_path


    def _res_prtsize (self, prtsize):

        return self._res_named(prtsize, self.namedprtsizes,
                               "Named portrait size '%s' not defined.")


    def _res_ctime (self, ctime):

        return self._res_named(ctime, self.namedctimes,
                               "Named continuation time '%s' not defined.")


    def _res_autoplace (self, node, autoplace):

        if autoplace is None:
            if isinstance(node, NodePath):
                autoplace = self.autoplace
            else:
                autoplace = False
        return autoplace


    def _handle_skip (self):

        if not base.challenge_priority("dialog", self._skip_seq):
            return
        if self.canskip:
            doskip = True
        else:
            doskip = all(x.canskip for x in self._item_contexts)
        if doskip:
            for item_context in self._item_contexts:
                item_context.skip = True


    def _handle_end (self):

        if not base.challenge_priority("dialog", self._end_seq):
            return
        if self.canend:
            self.stop()


    @staticmethod
    def set_dt_function (func):

        Dialog._dt_function = staticmethod(func)


    @staticmethod
    def set_screen_size_function (func):

        Dialog._screen_size_function = staticmethod(func)


    @staticmethod
    def set_autoplace_offset_function (func):

        Dialog._autoplace_offset_function = staticmethod(func)


class Character (object):

    def __init__ (self, longdes=None, shortdes=None,
                  portrait=None, prtsize=0.3, prtaspect=0.75, prtsel={},
                  width=1.0, pos=(0.0, 0.0),
                  posx=None, posz=None, # deprecated
                  font=FONT_DLG, size=12,
                  smallcaps=False, underscore=False,
                  color=rgba(1.0, 1.0, 1.0, 1.0),
                  shcolor=None,
                  olcolor=rgba(0, 0, 0, 1.0), olwidth=1.0, olfeather=0.1,
                  align="l", anchor="mc", swipe=None,
                  wpmspeed=None,
                  unfoldfac=None, unfoldsound=None, unfoldsndvol=1.0,
                  linesound=None, linesndvol=1.0, linesndloop=False,
                  autoplace=None, aplprio=None,
                  node=None, offset=None, played=False):

        self.longdes = longdes
        self.shortdes = shortdes
        self.portrait = portrait
        self.prtsize = prtsize
        self.prtaspect = prtaspect
        self.prtsel = prtsel
        self.width = width
        # deprecated-start
        self.posx = posx
        self.posz = posz
        # deprecated-end
        self.pos = pos
        self.font = font
        self.size = size
        self.smallcaps = smallcaps
        self.underscore = underscore
        self.color = color
        self.shcolor = shcolor
        self.olcolor = olcolor
        self.olwidth = olwidth
        self.olfeather = olfeather
        self.align = align
        self.anchor = anchor
        self.swipe = swipe
        self.wpmspeed = wpmspeed
        self.unfoldfac = unfoldfac
        self.unfoldsound = unfoldsound
        self.unfoldsndvol = unfoldsndvol
        self.linesound = linesound
        self.linesndvol = linesndvol
        self.linesndloop = linesndloop
        self.autoplace = autoplace
        self.aplprio = aplprio
        self.node = node
        self.offset = offset
        self.played = played

        # Normalize anchor to first vertical second horizontal.
        if self.anchor[0:1] in "lrc":
            self.anchor = self.anchor[1:] + self.anchor[0]

        # Sanity.
        if self.align not in "lrc":
            raise StandardError("Unknown alignment type '%s'." % self.align)
        if self.anchor[0:1] not in "tmb" or self.anchor[1:2] not in "lrc":
            raise StandardError("Unknown anchor type '%s'." % self.anchor)


class CharMod (object):

    # See Character.__init__ for possible parameters.
    def __init__ (self, **kwargs):

        Character(**kwargs) # validation
        self._mods = kwargs


    def supplement (self, char):

        mod_char = Character()
        for key, val in char.__dict__.items():
            if key in self._mods:
                mod_val = self._mods[key]
            else:
                mod_val = val
            mod_char.__dict__[key] = mod_val
        return mod_char


class Speech (object):

    def __init__ (self, speaker, line, charmod=None):

        self.speaker = speaker
        self.line = line
        self.charmod = charmod


class Line (object):

    def __init__ (self, text, cond=True, startf=None, endf=None, branch=None,
                  time=None, timefac=None, ctime=None, ctimefac=None,
                  isendf=None, font=None, voice=None, volume=None):

        self.text = text
        self.cond = cond
        self.startf = startf
        self.endf = endf
        self.branch = branch
        self.time = time
        self.timefac = timefac
        self.ctime = ctime
        self.ctimefac = ctimefac
        self.isendf = isendf
        self.font = font
        self.voice = voice
        self.volume = volume

        # Sanity.
        if self.time is not None and self.timefac is not None:
            raise StandardError(
                "Cannot set both time (%s) and "
                "time factor (%s)." % ("time", "timefac"))
        if self.ctime is not None and self.ctimefac is not None:
            raise StandardError(
                "Cannot set both continuation time (%s) and "
                "continuation time factor (%s)." % ("ctime", "ctimefac"))


class Pause (object):

    def __init__ (self, time, isendf=None, startf=None, endf=None, branch=None):

        self.time = time
        self.isendf = isendf
        self.startf = startf
        self.endf = endf
        self.branch = branch


def _store (store, name):
    def decf (func):
        if name in store:
            raise StandardError("Name '%s' already in store." % name)
        store[name] = func
        return func
    return decf


class Entry (object):

    _effects = {}
    _default = "instant"

    def __init__ (self, speaker=True, ctime=None, effect=None,
                  startf=None, endf=None):

        self.speaker = speaker
        self.ctime = ctime
        if effect is None:
            self.effect = self._effects[self._default]
        elif isinstance(effect, basestring):
            self.effect = self._effects.get(effect, self._effects[self._default])
        else:
            self.effect = effect
        self.startf = startf
        self.endf = endf


    @_store(_effects, "instant")
    def _instant (node):

        duration = 0.0
        node.setSa(1.0)
        task = None
        return task, duration


    @_store(_effects, "fade")
    def _fade (node):

        duration = 0.1
        task = node_fade_to(node=node, endalpha=1.0, duration=duration)
        return task, duration


class Exit (object):

    _effects = {}
    _default = "instant"

    def __init__ (self, speaker=True, ctime=None, effect=None,
                  startf=None, endf=None):

        self.speaker = speaker
        self.ctime = ctime
        if effect is None:
            self.effect = self._effects[self._default]
        elif isinstance(effect, basestring):
            self.effect = self._effects.get(effect, self._effects[self._default])
        else:
            self.effect = effect
        self.startf = startf
        self.endf = endf


    @_store(_effects, "instant")
    def _instant (node):

        duration = 0.0
        node.setSa(0.0)
        task = None
        return task, duration


    @_store(_effects, "fade")
    def _fade (node):

        duration = 0.1
        task = node_fade_to(node=node, endalpha=0.0, duration=duration)
        return task, duration


class UpdateChar (object):

    def __init__ (self, speaker, charmod):

        self.speaker = speaker
        self.charmod = charmod


def make_dlg_button (text, pos, width, height, font, size, color,
                     clickf=None, parent=None):

    if parent is None:
        parent = base.uiface_root
    if isinstance(font, basestring):
        font = base.load_font("data", font)

    #geom = [_ui_imgs.find("**/%s" % x) for x in frames]
    texts = [text]
    scale = font_scale_for_ptsize(size)
    offset = (0.0, 0.0)
    bt = DirectButton(
        text=texts,
        text_font=font,
        text_fg=color,
        text_scale=scale,
        text_pos=offset,
        text_align=TextNode.ALeft,
        #geom=geom,
        clickSound=None,
        rolloverSound=None,
        pos=(pos[0], 0.0, pos[1]),
        relief=None,
        pressEffect=0,
        parent=parent,
        command=clickf)
    bt._DirectGuiBase__componentInfo["text2"][0].setColorScale(1.5)
    return bt


_LOREM = (
"Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do "
"eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim "
"ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut "
"aliquip ex ea commodo consequat. Duis aute irure dolor in "
"reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
"pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
"culpa qui officia deserunt mollit anim id est laborum."
)

def lorem_ipsum (length=-1, start=0):

    end = start + length if length >= 0 else len(_LOREM)
    text = _LOREM[start:end]
    text = text.strip(" ,.") + "."
    text = text.capitalize()
    return text


