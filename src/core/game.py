# -*- coding: UTF-8 -*-

import locale
import os
import pickle
from time import strftime

from pandac.PandaModules import Point2

from src import real_path, path_exists
from src.core.interface import MainMenu, CampaignMenu, SkirmishMenu, LoadMenu
from src.core.interface import PreCampaignMenu, MissionMenu, DialogMenu
from src.core.interface import DebriefingMenu, MISSION_DEBRIEFING
from src.core.interface import set_last_saved_game
from src.core.interface import LoadingScreen
from src.core.misc import AutoProps, node_fade_to
from src.core.misc import make_text, ui_font_path, rgba
from src.core.misc import report
from src.core.mission import Mission
from src.core.transl import *


class Game (object):

    def __init__ (self, gc=None):

        if gc is None:
            gc = AutoProps()
        self._game_context = gc

        self._game_context.game = self

        self._current_mission = None

        self._mmenu_first = False
        self._mmenu_jumpsub = None

        if gc.campaign is not None:
            self._game_stage = "load-campaign"
        elif gc.skirmish is not None:
            self._game_stage = "load-skirmish"
        elif gc.test is not None:
            self._game_stage = "load-test"
        else:
            self._game_stage = "game-start"

        self._next_missionf = None

        if gc.save_disabled:
            report(_("Saved games disabled."))

        self._loading_screen = LoadingScreen()

        self.alive = True
        base.taskMgr.add(self._post_loop, "game-post-loop", sort=16)
        # ...should come after mission's post loop.


    def destroy (self):

        if not self.alive:
            return

        # Main loop must request and wait for end of current mission.
        self._game_stage = "quit"


    def _cleanup (self):

        self._loading_screen.destroy()


    def _post_loop (self, task):

        if not self.alive:
            return task.done

        if self._game_stage == "mission-loop":
            # This condition should be first to avoid checking
            # all the stuff below throughout the mission.

            if not self._current_mission_skiploading:
                linfo = self._current_mission.take_loading_info()
                if linfo:
                    ltitle, lprog = linfo
                    self._loading_screen.set_title_text(ltitle)
                    self._loading_screen.set_progress_text(lprog)
                elif linfo is False:
                    self._loading_screen.clear()

            done = not self._current_mission.alive
            if done:
                sname, sargs = self._current_mission.end_state()
                if sname == "proceed":
                    mission_postcheck = self._current_mission_postcheck
                    if not mission_postcheck:
                        mission_postcheck = self._pack_mission_postcheck
                    if mission_postcheck:
                        ret = mission_postcheck(self._current_mission.context,
                                                self._game_context)
                        objcomp, gameover = ret
                    else:
                        objcomp = True
                        gameover = False
                    gameover_late = False
                    if isinstance(gameover, tuple):
                        gameover, gameover_late = gameover
                    if gameover is True:
                        gameover = gameover_loop_simple
                    self._current_mission_objcomp = objcomp
                    self._current_mission_gameover = gameover
                    self._current_mission_gameover_late = gameover_late
                    if self._current_mission_gameover and not gameover_late:
                        self._game_stage = "gameover-start"
                    elif self._current_mission_debriefing == MISSION_DEBRIEFING.EARLY:
                        self._game_stage = "debrief-start"
                    elif self._current_mission_debriefing in (MISSION_DEBRIEFING.LATE, MISSION_DEBRIEFING.SKIP):
                        self._game_stage = "outconv-start"
                    elif self._current_mission_gameover:
                        self._game_stage = "gameover-start"
                    else:
                        self._game_stage = "mission-end"
                else:
                    self._game_stage = "mission-end"
            else:
                # Short-circuit rest of the loop.
                return task.cont

        if self._game_stage == "game-start":
            self._game_stage = "mmenu-start"
            self._mmenu_first = True
            self._mmenu_jumpsub = None

        if self._game_stage == "mmenu-start":
            self._mmenu = MainMenu(
                first=self._mmenu_first,
                jumpsub=self._mmenu_jumpsub,
                parent=base.uiface_root)
            self._mmenu_first = False
            self._mmenu_jumpsub = None
            self._game_context.campaign = None
            self._game_context.skirmish = None
            self._game_context.test = None
            self._game_context.zone = None
            self._game_stage = "mmenu-loop"

        if self._game_stage == "mmenu-loop":
            done = not self._mmenu.alive
            if done:
                sname, sargs = self._mmenu.selection()
                if sname == "continue":
                    last_game = sargs[0]
                    gc = self.load_game(last_game)
                    self._game_context = gc
                    self._game_context.game = self
                    self._game_stage = "load-campaign"
                elif sname == "campaign":
                    cname = sargs[0]
                    self._game_context.campaign = cname
                    self._game_stage = "load-campaign"
                elif sname == "skirmish":
                    pname, mname = sargs
                    self._skirmish_selection = (pname, mname)
                    self._game_stage = "load-skirmish"
                elif sname == "quit":
                    self._game_stage = "quit"
                else:
                    assert False

        if self._game_stage == "load-campaign":

            if not self._game_context.campaign:
                raise StandardError("No campaign set in game context.")

            cname = self._game_context.campaign
            cmod = __import__(cname)
            report(_("Loading campaign: %s") % cname)

            nextmfn = "select_next_mission"
            self._next_missionf = getattr(cmod, nextmfn, None)
            if not self._next_missionf:
                raise StandardError(
                    "Campaign '%s' does not define function '%s'." %
                    (self._game_context.campaign, nextmfn))

            self._pack_mission_postcheck = getattr(cmod, "check_after_mission", None)

            initfn = "initialize"
            initf = getattr(cmod, initfn, None)
            if initf:
                initf(self._game_context)

            self._game_stage = "load-mission"

        if self._game_stage == "load-mission":
            if self._game_context.mission:
                mname = self._game_context.mission
                self._game_context.mission = None
                can_proceed = False
            elif self._next_missionf:
                mname = self._next_missionf(self._game_context)
                can_proceed = True
            else:
                assert False
            if mname is not None:
                cname = self._game_context.campaign
                report(_("Starting campaign mission: %(pack)s:%(name)s") %
                       dict(pack=cname, name=mname))
                mmod0 = __import__("%s.%s" % (cname, mname))
                mmod = getattr(mmod0, mname)
                getvo = lambda suffix, defval: (
                    getattr(mmod, "mission_" + suffix, defval)
                    if hasattr(mmod, "mission_" + suffix) else
                    getattr(mmod, mname + "_" + suffix, defval))
                startf = getvo("start", None) or getattr(mmod, "%s" % mname)
                setbgf = getvo("setbg", None)
                menuconvf = getvo("menuconv", None)
                drinkconvf = getvo("drinkconv", None)
                inconvf = getvo("inconv", None)
                outconvf = getvo("outconv", None)
                skipmenu = getvo("skipmenu", False)
                ondrink = getvo("ondrink", False)
                mustdrink = getvo("mustdrink", False)
                menumusic = getvo("menumusic", None)
                skipconfirm = getvo("skipconfirm", None)
                skiploading = getvo("skiploading", None)
                postcheck = getvo("postcheck", None)
                debriefing = getvo("debriefing", MISSION_DEBRIEFING.EARLY)
                self._current_mission_name = mname
                self._current_mission_setbgf = setbgf
                self._current_mission_startf = startf
                self._current_mission_menuconvf = menuconvf
                self._current_mission_drinkconvf = drinkconvf
                self._current_mission_inconvf = inconvf
                self._current_mission_outconvf = outconvf
                self._current_mission_skipmenu = skipmenu
                self._current_mission_ondrink = ondrink
                self._current_mission_mustdrink = mustdrink
                self._current_mission_menumusic = menumusic
                self._current_mission_skipconfirm = skipconfirm
                self._current_mission_skiploading = skiploading
                self._current_mission_postcheck = postcheck
                self._current_mission_debriefing = debriefing
                self._current_mission_insequence = True
                self._current_mission_ident = "campaign-%s-%s" % (cname, mname)
                if not self._game_context.save_disabled:
                    self.save_game("autosave_%s_%s" % (cname, mname))
                if can_proceed:
                    self._after_mission_proceed_stage = "load-mission"
                    self._after_mission_quit_stage = "imenu-start"
                else:
                    self._after_mission_proceed_stage = "quit"
                    self._after_mission_quit_stage = "quit"
                if self._game_context.zone is not None: # empty zone is default
                    self._game_stage = "mission-start"
                else:
                    self._game_stage = "imenu-start"
            else:
                self.destroy()

        if self._game_stage == "load-skirmish":
            if self._game_context.skirmish:
                pname = self._game_context.skirmish
                mname = self._game_context.mission
                self._game_context.skirmish = None
                self._game_context.mission = None
                can_proceed = False
            elif self._skirmish_selection:
                pname, mname = self._skirmish_selection
                can_proceed = True
            else:
                assert False
            report(_("Starting skirmish mission: %(pack)s:%(name)s") %
                   dict(pack=pname, name=mname))
            pmod = __import__(pname)
            pack_postcheck = getattr(pmod, "check_after_mission", None)
            self._pack_mission_postcheck = pack_postcheck
            mmod0 = __import__("%s.%s" % (pname, mname))
            mmod = getattr(mmod0, mname)
            getvm = lambda suffix: (
                getattr(mmod, "mission_" + suffix))
            getvo = lambda suffix, defval: (
                getattr(mmod, "mission_" + suffix, defval))
            startf = getvm("start")
            inconvf = getvo("inconv", None)
            outconvf = getvo("outconv", None)
            skipconfirm = getvo("skipconfirm", None)
            skiploading = getvo("skiploading", None)
            postcheck = getvo("postcheck", None)
            debriefing = getvo("debriefing", MISSION_DEBRIEFING.EARLY)
            self._current_mission_name = mname
            self._current_mission_setbgf = None
            self._current_mission_startf = startf
            self._current_mission_menuconvf = None
            self._current_mission_drinkconvf = None
            self._current_mission_inconvf = inconvf
            self._current_mission_outconvf = outconvf
            self._current_mission_skipmenu = True
            self._current_mission_ondrink = False
            self._current_mission_mustdrink = False
            self._current_mission_menumusic = None
            self._current_mission_skipconfirm = skipconfirm
            self._current_mission_skiploading = skiploading
            self._current_mission_postcheck = postcheck
            self._current_mission_debriefing = debriefing
            self._current_mission_insequence = False
            self._current_mission_ident = "skirmish-%s-%s" % (pname, mname)
            if can_proceed:
                self._after_mission_proceed_stage = "mmenu-start"
                self._after_mission_quit_stage = "mmenu-start"
                self._mmenu_jumpsub = "skirmish"
            else:
                self._after_mission_proceed_stage = "quit"
                self._after_mission_quit_stage = "quit"
            if self._game_context.zone is not None: # empty zone is default
                self._game_stage = "mission-start"
            else:
                self._game_stage = "imenu-start"

        if self._game_stage == "load-test":
            pname = self._game_context.test
            mname = self._game_context.mission
            report(_("Starting test mission: %(pack)s:%(name)s") %
                   dict(pack=pname, name=mname))
            pmod = __import__(pname)
            pack_postcheck = getattr(pmod, "check_after_mission", None)
            self._pack_mission_postcheck = pack_postcheck
            mmod0 = __import__("%s.%s" % (pname, mname))
            mmod = getattr(mmod0, mname)
            getvo = lambda suffix, defval: (
                getattr(mmod, "mission_" + suffix, defval))
            startf = getvo("start", None)
            if not startf:
                if self._game_context.loop:
                    lname = "zone_loop_%s" % self._game_context.loop
                    report(_("Entering zone loop: %s") %
                           self._game_context.loop)
                else:
                    lname = "zone_loop"
                loopf = getattr(mmod, lname)
                def startf (gc):
                    mission = Mission(gc)
                    mission.add_zone("zero", clat=0, clon=0, loopf=loopf)
                    return mission
                self._game_context.zone = ""
            inconvf = getvo("inconv", None)
            outconvf = getvo("outconv", None)
            skipconfirm = getvo("skipconfirm", None)
            skiploading = getvo("skiploading", None)
            postcheck = getvo("postcheck", None)
            debriefing = getvo("debriefing", MISSION_DEBRIEFING.SKIP)
            self._current_mission_name = mname
            self._current_mission_setbgf = None
            self._current_mission_startf = startf
            self._current_mission_inconvf = inconvf
            self._current_mission_menuconvf = None
            self._current_mission_outconvf = outconvf
            self._current_mission_skipmenu = True
            self._current_mission_ondrink = False
            self._current_mission_mustdrink = False
            self._current_mission_menumusic = None
            self._current_mission_skipconfirm = skipconfirm
            self._current_mission_skiploading = skiploading
            self._current_mission_postcheck = postcheck
            self._current_mission_debriefing = debriefing
            self._current_mission_insequence = False
            self._current_mission_ident = "test-%s-%s" % (pname, mname)
            self._after_mission_proceed_stage = "quit"
            self._after_mission_quit_stage = "quit"
            self._game_stage = "mission-start"

        if self._game_stage == "imenu-start":
            self._imenu = MissionMenu(
                gc=self._game_context,
                setbgf=self._current_mission_setbgf,
                music=self._current_mission_menumusic,
                preconvf=self._current_mission_menuconvf,
                inconvf=self._current_mission_inconvf,
                drinkconvf=self._current_mission_drinkconvf,
                mustdrink=self._current_mission_mustdrink,
                drinktostart=self._current_mission_ondrink,
                jumpinconv=self._current_mission_skipmenu,
                skipconfirm=self._current_mission_skipconfirm,
                parent=base.uiface_root)
            self._game_stage = "imenu-loop"

        if self._game_stage == "imenu-loop":
            done = not self._imenu.alive
            if done:
                sname, sargs = self._imenu.selection()
                if sname == "mission":
                    self._game_stage = "mission-start"
                elif sname == "main":
                    self._game_stage = "mmenu-start"
                else:
                    assert False

        if self._game_stage == "mission-start":
            self._prev_game_context = AutoProps()
            self._prev_game_context.set_from(self._game_context)
            if self._current_mission_startf:
                mission = self._current_mission_startf(self._game_context)
                mission.in_sequence = self._current_mission_insequence
                mission.ident = self._current_mission_ident
                if self._game_context.zone: # empty zone ignored
                    mission.switch_zone(self._game_context.zone)
                    self._game_context.zone = None
                self._current_mission = mission
                self._game_stage = "mission-loop"
            else:
                self._game_stage = "outconv-start"

        if self._game_stage == "mission-end":
            self._game_context.last_mission = self._current_mission_name
            self._pause_time = 0.0
            sname, sargs = self._current_mission.end_state()
            if sname == "proceed":
                report(_("Mission ended."))
                self._game_stage = "mission-proceed"
                self._pause_time = 3.0
                restore_gc = False
            elif sname == "restart":
                report(_("Restarting mission."))
                self._pause_frames = 5 # to clean up everything
                self._pause_time = 0.0
                self._game_stage = "mission-restart"
                restore_gc = True
            elif sname == "quit":
                report(_("Quitting mission."))
                self._game_stage = "mission-quit"
                self._pause_time = 1.0
                restore_gc = True
            elif sname == "quit-game":
                self._game_stage = "quit"
                restore_gc = True
            else:
                assert False
            if restore_gc:
                self._game_context.set_from(self._prev_game_context)
                # ...must not simply assign the previous context,
                # others may be holding the pointer to current context.

        if self._game_stage == "mission-proceed":
            if self._pause_time > 0.0:
                self._pause_time -= base.global_clock.getDt()
            else:
                self._current_mission = None
                self._game_stage = self._after_mission_proceed_stage

        if self._game_stage == "mission-restart":
            if self._pause_frames > 0 or self._pause_time > 0.0:
                self._pause_frames -= 1
                self._pause_time -= base.global_clock.getDt()
            else:
                self._game_stage = "mission-start"

        if self._game_stage == "mission-quit":
            if self._pause_time > 0.0:
                self._pause_time -= base.global_clock.getDt()
            else:
                self._current_mission = None
                self._game_stage = self._after_mission_quit_stage

        if self._game_stage == "debrief-start":
            self._dmenu = DebriefingMenu(
                objcomp=self._current_mission_objcomp,
                kills=self._current_mission.player_kills())
            self._game_stage = "debrief-loop"

        if self._game_stage == "debrief-loop":
            done = not self._dmenu.alive
            if done:
                if self._current_mission_debriefing == MISSION_DEBRIEFING.EARLY:
                    self._game_stage = "outconv-start"
                elif self._current_mission_gameover:
                    self._game_stage = "gameover-start"
                else:
                    self._game_stage = "mission-end"

        if self._game_stage == "gameover-start":
            gc = AutoProps()
            gc.set_from(self._game_context)
            mission = Mission(gc)
            mission.zone_switch_pause = 0.0
            mission.add_zone("zero", clat=0, clon=0,
                             loopf=self._current_mission_gameover)
            self._gameover_mission = mission
            self._game_stage = "gameover-loop"

        if self._game_stage == "gameover-loop":
            done = not self._gameover_mission.alive
            if done:
                self._current_mission.end(state="quit")
                self._game_stage = "mission-end"

        if self._game_stage == "outconv-start":
            if self._current_mission_outconvf:
                self._ocmenu = DialogMenu(
                    gc=self._game_context,
                    convf=self._current_mission_outconvf,
                    skipconfirm=self._current_mission_skipconfirm)
                self._game_stage = "outconv-loop"
            else:
                self._game_stage = "mission-end"

        if self._game_stage == "outconv-loop":
            done = not self._ocmenu.alive
            if done:
                if self._current_mission_debriefing == MISSION_DEBRIEFING.LATE:
                    self._game_stage = "debrief-start"
                elif self._current_mission_gameover:
                    self._game_stage = "gameover-start"
                else:
                    self._game_stage = "mission-end"

        if self._game_stage == "quit":
            self.alive = False
            report(_("Quitting game."))
            self._cleanup()
            exit(1)
            return task.done

        return task.cont


    _allowed_save_elements = frozenset([
        type(None),
        int,
        float,
        str,
        unicode,
        bool,
    ])
    _allowed_save_sequences = {
        tuple: (lambda x: x),
        list: (lambda x: tuple(x)),
        dict: (lambda x: sum(sorted(x.items()), ())),
    }

    def save_game (self, basename):

        payload = {}

        payload["context"] = {}
        for name, value in self._game_context.props():
            if value is self:
                continue
            if type(value) in self._allowed_save_sequences:
                for value_1 in self._allowed_save_sequences[type(value)](value):
                    if type(value_1) not in self._allowed_save_elements:
                        raise StandardError(
                            "A sequence element of game context attribute '%s' "
                            "has inadmissible type %s." %
                            (name, type(value)))
            else:
                if type(value) not in self._allowed_save_elements:
                    raise StandardError(
                        "Game context attribute '%s' "
                        "has inadmissible type %s." %
                        (name, type(value)))
            payload["context"][name] = value

        payload["time"] = strftime("%Y-%m-%d %H:%M:%S")

        file_path = basename + ".pkl"
        do_write = True
        if path_exists("save", file_path):
            try:
                with open(real_path("save", file_path), "rb") as fh:
                    old_payload = pickle.load(fh)
                do_write = (payload["context"] != old_payload["context"])
            except:
                pass
        if do_write:
            report(_("Saving game: %s") % basename)
            with open(real_path("save", file_path), "wb") as fh:
                pickle.dump(payload, fh, protocol=1)

        set_last_saved_game(basename)


    @staticmethod
    def load_game (basename):

        report(_("Loading game: %s") % basename)
        file_path = basename + ".pkl"
        with open(real_path("save", file_path), "rb") as fh:
            payload = pickle.load(fh)

        set_last_saved_game(basename)

        gc_props = payload["context"]
        gc = AutoProps(**gc_props)
        return gc


def gameover_loop_simple (zc, mc, gc):

    root_node = base.uiface_root.attachNewNode("gameover-root")

    make_text(
        _("GAME OVER"),
        width=2.0, pos=Point2(0.0, 0.0),
        font=ui_font_path, size=64, ppunit=100,
        color=rgba(255, 0, 0, 1.0),
        align="c", anchor="mc",
        parent=root_node)

    node_fade_to(root_node, startalpha=0.0, endalpha=1.0, duration=1.0)
    yield 1.0 + 2.0
    node_fade_to(root_node, startalpha=1.0, endalpha=0.0, duration=1.0)
    yield 1.0

    root_node.removeNode()
    mc.mission.end()


