# -*- coding: UTF-8 -*-

import codecs
from ConfigParser import SafeConfigParser
from math import degrees, radians
import os

from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import VBase2, Vec3, Point2, Point3, Quat
from pandac.PandaModules import NodePath

import pygame

from src import OUTSIDE_FOV, ANIMATION_FOV
from src.core.bomb import Dropper
from src.core.chaser import HeadChaser, ElasticChaser, TrackChaser
from src.core.cockpit import Cockpit, VirtualCockpit
from src.core.cockpit import select_des
from src.core.dialog import Dialog
from src.core.interface import SimpleText, BubbleText
from src.core.interface import KILL_STATS_FAMILIES
from src.core.misc import AutoProps, SimpleProps, rgba, update_towards
from src.core.misc import sign, clamp, unitv
from src.core.misc import intc01r, intl01v, intc01vr, intl01vr
from src.core.misc import hprtovec, hpr_to
from src.core.misc import make_image, make_text, update_text
from src.core.misc import uniform, randrange, choice, randvec
from src.core.misc import font_scale_for_ptsize
from src.core.misc import map_pos_to_screen
from src.core.planedyn import FLAPS
from src.core.podrocket import PodLauncher
from src.core.rocket import Launcher
from src.core.shader import make_shader, make_text_shader
from src.core.shell import Cannon
from src.core.transl import *


class Player (DirectObject):

    def __init__ (self, ac, headpos, dimpos, rvpos,
                  cpitpos, cpitmfspec, cpitdownto,
                  arenaedge=(3000.0, 1000.0),
                  mission=None, mzexitf=None):

        self._lang = "ru"
        #self._font = "fonts/DejaVuSans-Bold.ttf"
        self._font = "fonts/red-october-regular.otf"
        #self._font = "fonts/DidactGothic.ttf"

        DirectObject.__init__(self)

        self.world = ac.world
        self.ac = ac
        self.mission = mission
        self.mzexitf = mzexitf

        ac.sensorpack.update(scanperiod=0.5, relspfluct=0.1, maxtracked=1)
        ac.sensorpack.start_scanning()

        self.headchaser = HeadChaser(
            world=self.world, parent=ac,
            fov=OUTSIDE_FOV,
            angspeed=radians(180.0), angacc=radians(720.0),
            fovspeed=40.0, fovacc=160.0,
            pos=headpos, hpr=Vec3())
        if dimpos is not None:
            self._dimchaser_point = dimpos
            self._dimchaser_fov = ANIMATION_FOV
            self.dimchaser = ElasticChaser(
                world=self.world, point=dimpos,
                relto=ac, rotrel=False,
                atref=ac, upref=Vec3(0.0, 0.0, 1.0),
                distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10)
            #self.dimchaser = ElasticChaser(
                #world=self.world, point=Point3(0, 0, 40),
                #relto=ac, rotrel=False,
                #atref=ac, upref=Vec3(-1, 0, 0),
                #distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10)
            #self.dimchaser = ElasticChaser(
                #world=self.world, point=Point3(0, 0, 20000),
                #relto=ac, rotrel=False,
                #atref=Vec3(0, 0, -1), upref=Vec3(0, 1, 0),
                #distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10)
        else:
            self.dimchaser = None
        if rvpos is not None:
            self.rvchaser = ElasticChaser(
                world=self.world, point=rvpos,
                relto=ac, rotrel=True,
                atref=ac, upref=ac,
                distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10)
        else:
            self.rvchaser = None
        self.targchaser = None

        #for cannon in self.ac.cannons:
            #cannon.reloads = -1 # means infinite

        self.throttle_maxab = 1.1

        if isinstance(arenaedge, tuple):
            arenaedge_warn, arenaedge_turn = arenaedge
        else:
            arenaedge_warn = arenaedge
            arenaedge_turn = arenaedge * 0.33

        self.notifier = PlayerNotifier(self)
        self.cockpit = Cockpit(self, pos=cpitpos, mfspec=cpitmfspec,
                               headpos=headpos, downto=cpitdownto,
                               arenaedge=arenaedge_warn)
        self.virtcpit = VirtualCockpit(self)
        self._virtcpit_available = True

        self._wait_time_slow_loop = 0.0

        #self._prev_input_elevator = 0.0
        self._prev_input_elevator = []

        self._prev_player_control_level = None
        self._targchaser_prev_target = None

        self._arenaedge_warn = arenaedge_warn
        self._arenaedge_turn = arenaedge_turn
        self._turn_back_warning = None
        self._turn_back_forced = False
        self._prev_aedist = 1e30

        self._missile_chasef = None
        self._bomb_chasef = None

        # Collect possible weapons.
        self.weapons = []
        #againstf = lambda cannon: (lambda: cannon.against)
        # TODO: Add another cannon mode for ground attack, when enabled.
        cannon_against_air = ["plane", "heli"]
        againstf = lambda cannon: (lambda: cannon_against_air)
        availablef = lambda cannon: (lambda: cannon.ammo > 0)
        resetf = lambda cannon: (lambda: cannon.fire(rounds=0))
        for cannon in self.ac.cannons:
            wp = AutoProps()
            wp.set_silent(False)
            wp.handle = cannon
            wp.onpylons = False
            wp.against = againstf(cannon)
            wp.available = availablef(cannon)
            wp.reset = resetf(cannon)
            self.weapons.append(wp)
        againstf = lambda launcher: (lambda: launcher.mtype.against)
        availablef = lambda launcher: (lambda: len(launcher.points) > 0)
        resetf = lambda launcher: (lambda: launcher.ready(target=None))
        for launcher in self.ac.launchers:
            wp = AutoProps()
            wp.set_silent(False)
            wp.handle = launcher
            wp.onpylons = True
            wp.against = againstf(launcher)
            wp.available = availablef(launcher)
            wp.reset = resetf(launcher)
            self.weapons.append(wp)
        againstf = lambda dropper: (lambda: dropper.btype.against)
        availablef = lambda dropper: (lambda: len(dropper.points) > 0)
        resetf = lambda dropper: (lambda: None)
        for dropper in self.ac.droppers:
            wp = AutoProps()
            wp.set_silent(False)
            wp.handle = dropper
            wp.onpylons = True
            wp.against = againstf(dropper)
            wp.available = availablef(dropper)
            wp.reset = resetf(dropper)
            self.weapons.append(wp)
        rocket_against_ground = ["vehicle", "ship", "building"]
        againstf = lambda podlauncher: (lambda: rocket_against_ground)
        availablef = lambda podlauncher: (lambda: len(podlauncher.rounds) > 0)
        resetf = lambda podlauncher: (lambda: None)
        for podlauncher in self.ac.podlaunchers:
            wp = AutoProps()
            wp.set_silent(False)
            wp.handle = podlauncher
            wp.onpylons = True
            wp.against = againstf(podlauncher)
            wp.available = availablef(podlauncher)
            wp.reset = resetf(podlauncher)
            self.weapons.append(wp)

        self._set_bindings() # set player input bindings

        self._zero_inputs() # initialize input variables

        self.ac.evade_missile_decoy = False

        self._lost_inited = False

        self._chaser_sens_rot = 0.2
        self._chaser_min_fov = 5
        self._chaser_max_fov = 85

        # Notifications.
        self.node2d = self.world.overlay_root.attachNewNode("player-indicators")
        self._text_shader = make_text_shader(glow=rgba(255, 255, 255, 0.4),
                                             shadow=True)

        # Targeting.
        self.target_contact = None
        self.target_body = None
        self.target_offset = None
        self.target_hitbox = None
        self._prev_cycle_contact_set = {}
        self._cycle_target_time_pressed = None
        self._cycle_target_deselect_delay = 0.2
        self._cycle_target_immediate_deselect = False
        self._cycle_tag_contact_set = set()
        self._wait_cycle_tag = 0.0
        self._cycle_tag_period = 1.13
        self._target_section_index = 0

        # View tracking.
        self.view_contact = None
        self.view_body = None

        # Waypoints.
        self._waypoints = {}
        self._waypoint_keys = []
        self._current_waypoint_name = None
        self._waypoint_wait_check = 0.0
        self._waypoint_check_period = 0.53

        # Navpoints.
        self._navpoints = {}
        self._navpoint_anon_counter = 0

        # Active navpoints.
        self._wait_actnav = 0.0
        self._actnav_period = 0.51
        self._actnav_names = set()
        self._actnav_text = None
        self._actnav_text_size = 10.0
        self._actnav_text_color = rgba(255, 0, 0, 1.0)
        self._actnav_text_shcolor = rgba(0, 0, 0, 1.0)
        self._actnav_text_sel_color = rgba(255, 255, 255, 1.0)
        self._actnav_seldelay = 0.5
        self._actnav_clrdelay = 5.0
        self._actnav_selnp = AutoProps()
        self.jump_navpoint = None

        # Families which prevent player from jumping through a navpoint
        # when they target him or his allies.
        self._no_navjump_when_target_families = (
            "plane",
            "rocket",
        )
        self._no_navjump_when_attacked_families = (
            "plane",
        )
        self._navjump_clear_delay = 10.0
        self._navjump_wait_clear = 5.0 # min wait at zone start

        # Aerotow.
        self._aerotow_max_dist = 300.0
        self._aerotow_max_offbore = radians(15.0)
        self._aerotow_max_speed_diff = 20.0


        c = base.gameconf.cheat
        if (c.adamantium_bath or c.flying_dutchman or c.guards_tanksman or
            c.chernobyl_liquidator):
            ac.strength = 1e10
            ac.maxhitdmg = 1e10

        self.alive = True
        base.taskMgr.add(self._loop, "player-loop", sort=-6)
        base.taskMgr.add(self._slow_loop, "player-slow-loop", sort=-6)
        # ...should come before cockpit loop.


    def destroy (self):

        if self.alive == False:
            return
        self.alive = False
        for jsdev in self._jsdevs.values():
            jsdev.dev.quit()
        self.notifier.destroy()
        self.cockpit.destroy()
        self.virtcpit.destroy()
        self.headchaser.destroy()
        if self.dimchaser:
            self.dimchaser.destroy()
        if self.rvchaser:
            self.rvchaser.destroy()
        if self.targchaser:
            self.targchaser.destroy()
        self.ignoreAll()
        self.node2d.removeNode()
        base.remove_priority("control")


    def _loop (self, task):

        if not self._lost_inited and (self.ac.controlout or self.ac.shotdown):
            self._lost_init()

        if not self.alive:
            return task.done
        if not self.ac.alive:
            self.destroy()
            return task.done

        pclev = self.world.player_control_level
        world = self.world

        self.cockpit.active = world.chaser is self.headchaser

        outchs = (self.dimchaser, self.rvchaser, self.targchaser)
        self.virtcpit.active = (self._virtcpit_available and
                                (world.chaser in outchs or
                                 world.chaser in world.action_chasers))

        if self._prev_player_control_level != pclev:
            self._prev_player_control_level = pclev
            self.cockpit.set_physio_effects(pclev < 2 or self.cockpit.active)
            self._zero_inputs(keepthr=True, keepwpsel=True)
            if pclev == 0:
                self.node2d.show()
                self.headchaser.move_to(atref=Vec3(0.0, 1.0, 0.0))
                self.ac.zero_ap()
            else:
                self.node2d.hide()

        if True:
            self._update_targeting(self.world.dt)
            self._update_cycle_tag(self.world.dt)
            self._update_waypoints(self.world.dt)

        if pclev == 0:
            self._update_navjumps(self.world.dt)

        if pclev == 0 and self._jsdevs:
            self._set_control_joy()

        if pclev == 0 and base.mouse_watcher.node().hasMouse():
            self._set_control_mouse()

        if pclev == 0:
            self._set_ac_inputs()

        if pclev == 0 and self.fire_chasers_on:
            self.fire_chasers_on = False
            if self._missile_chasef is None:
                # chf = lambda p: FixedChaser(parent=p, pos=Point3(0, -32, 8))
                def chf(p):
                    chaserchoice = randrange(3)
                    if chaserchoice == 0:
                        # ch = ElasticChaser(
                            # world=p.world, point=Point3(0, -30, -10),
                            # relto=self.ac, rotrel=True,
                            # atref=p, upref=self.ac,
                            # distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                            # remdelay=3.0)
                        ch = TrackChaser(
                            world=p.world, point=Point3(0, -30, -8),
                            relto=self.ac, rotrel=True,
                            atref=p, upref=self.ac,
                            fov=20)
                    elif chaserchoice == 1:
                        # sidex = choice([15, -15])
                        # ch = ElasticChaser(
                            # world=p.world, point=Point3(sidex, 30, -8),
                            # relto=self.ac, rotrel=True,
                            # atref=p, upref=self.ac,
                            # distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                            # remdelay=3.0)
                        sidex = choice([20, -20])
                        ch = TrackChaser(
                            world=p.world, point=Point3(sidex, 30, -8),
                            relto=self.ac, rotrel=True,
                            atref=p, upref=self.ac,
                            fov=20)
                    elif chaserchoice == 2:
                        # ch = ElasticChaser(
                            # world=p.world, point=Point3(0, 30, 4),
                            # relto=self.ac, rotrel=True,
                            # atref=p, upref=self.ac,
                            # distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                            # remdelay=3.0)
                        ch = TrackChaser(
                            world=p.world, point=Point3(0, 60, 8),
                            relto=self.ac, rotrel=True,
                            atref=p, upref=self.ac,
                            fov=20)
                    # elif chaserchoice == 3:
                        # ch = ElasticChaser(
                            # world=p.world, point=Point3(0, -30, 5),
                            # relto=p, rotrel=True,
                            # atref=p, upref=p,
                            # distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                            # remdelay=3.0,
                            # pos=self.ac.pos(offset=Point3(
                                # 0, randrange(-40,-30), randrange(-20,-10))))
                    def camf (task):
                        if self.ac.alive and ch.alive and p and p.target.alive:
                            if chaserchoice == 0:
                                # ch.move_to(point=Point3(0, -10, 2), relto=p, rotrel=True,
                                           # atref=p, upref=p, fov=90,
                                           # distlag=1.60, atlag=0.60, uplag=0.60, fovlag=1.20)
                                ch.move_to(point=Point3(0, -30, 2), relto=p, rotrel=True,
                                           atref=p, upref=p, fov=90, speed=10.0, acc=5.0,
                                           fovspeed=10.0, fovacc=4.0)
                            elif chaserchoice == 1:
                                # ch.move_to(point=Point3(0, -20, 2), relto=p, rotrel=True,
                                           # atref=p, upref=p, fov=90,
                                           # distlag=1.40, atlag=1.20, uplag=1.20, fovlag=1.80)
                                ch.move_to(point=Point3(0, -20, 2), relto=p, rotrel=True,
                                           atref=p, upref=p, fov=90,
                                           speed=15.0, acc=5.0,
                                           fovspeed=10.0, fovacc=4.0)
                            elif chaserchoice == 2:
                                # ch.move_to(point=Point3(0, -60, -4), relto=p, rotrel=False,
                                           # atref=p, upref=p, fov=90,
                                           # distlag=0.80, atlag=0.30, uplag=0.30, fovlag=1.00)
                                ch.move_to(point=Point3(0, -60, 2), relto=p, rotrel=True,
                                           atref=p, upref=p, fov=90,
                                           speed=100.0, acc=50.0,
                                           fovspeed=10, fovacc=4.0)
                            # elif chaserchoice == 3:
                                # ch.move_to(fov=90, fovlag=2.0)
                    taskMgr.doMethodLater(1.0, camf, "actionmissile")
                    return ch
                self._missile_chasef = chf
                chf = lambda p: ElasticChaser(
                    world=p.world, point=Point3(-35, 35, 60),
                    relto=p, rotrel=True,
                    atref=p, upref=Vec3(0, 0, 1),
                    distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                    remdelay=3.0,
                    pos=self.ac.pos(offset=Point3(
                        0, randrange(-40,-30), randrange(-20,-10))))
                self._bomb_chasef = chf
                #self.notifier.show_message("state", "small",
                                           #_("Action camera enabled"))
                self.notifier.set_on_off_indicator("actchaser", True)
            else:
                self._missile_chasef = None
                self._bomb_chasef = None
                #self.notifier.show_message("state", "small",
                                           #_("Action camera disabled"))
                self.notifier.set_on_off_indicator("actchaser", False)

        if self.targchaser and not self.targchaser.alive:
            self.chaser = self.headchaser
            self.targchaser = None

        if self.input_flaps_switch:
            self.input_flaps_switch = False
            if not self.input_landing_gear:
                self.input_flaps = FLAPS.RETRACTED
            elif not self.ac.onground:
                self.input_flaps = FLAPS.LANDING
            else:
                self.input_flaps = FLAPS.TAKEOFF
        elif (self.ac.onground and self.input_flaps != FLAPS.TAKEOFF and
              self.ac.speed() < 15.0):
            self.input_flaps = FLAPS.TAKEOFF

        self._last_ac_pos = self.ac.pos()

        return task.cont


    def _slow_loop (self, task):

        if not self.alive:
            return task.done
        if not self.ac.alive:
            self.destroy()
            return task.done

        if self._wait_time_slow_loop > 0.0:
            self._wait_time_slow_loop -= self.world.dt
            return task.cont
        self._wait_time_slow_loop = uniform(1.0, 1.5)
        pclev = self.world.player_control_level
        world = self.world

        if pclev == 0:
            aedist = world.arena_edge_dist(self.ac.pos())
            if aedist < self._arenaedge_turn:
                self.world.player_control_level = 2
                dq = self.ac.dynstate
                mass, alt = dq.m, dq.h
                point = Point3(0.0, 0.0, alt)
                speed = self.ac.dyn.tab_voptrf[0](mass, alt)
                self.ac.set_ap(point=point, speed=speed, maxg=5.0, useab=True)
                self._turn_back_forced = True
                self._turn_back_warning = None
                self.notifier.show_message("state", "poke", "", duration=0.0)
            elif aedist < self._arenaedge_warn:
                if not self._turn_back_warning and self._prev_aedist > aedist:
                    self._turn_back_warning = choice(Player._turn_back_warnings)
                elif self._turn_back_warning and self._prev_aedist < aedist:
                    self._turn_back_warning = None
            if self._turn_back_warning:
                self.notifier.show_message("state", "poke", self._turn_back_warning,
                                           duration=5.0, blink=True)
            self._prev_aedist = aedist
        if self._turn_back_forced:
            aedist = world.arena_edge_dist(self.ac.pos())
            if aedist > self._arenaedge_turn * 1.2:
                self.world.player_control_level = 0
                self._turn_back_forced = False

        return task.cont


    def _lost_init (self):

        if self._lost_inited:
            return
        self._lost_inited = True

        self.world.player_control_level = 2
        self.ac.must_eject_time = -1 # no ejection
        Dialog.stop_all_dialogs()
        if self.mission:
            self.mission.set_zone_frozen(True)

        self._eject_cam_type = None

        minotralt = 5.0
        if self.ac.alive:
            modx = choice([-1, 1])
            # mody = choice([-1, 1])
            if not self.ac.ejection_triggered:
                # Lost by out of control.
                ch = TrackChaser(world=self.world,
                                 point=Point3(10 * modx, -25, -5),
                                 relto=self.ac, rotrel=True,
                                 atref=self.ac, upref=Vec3(0, 0, 1),
                                 minotralt=minotralt)
                def camf (task):
                    if self.ac.alive and ch.alive:
                        ch.move_to(point=Point3(10 * modx, -50, -10),
                                   relto=self.ac, rotrel=True,
                                   atref=self.ac, upref=Vec3(0, 0, 1),
                                   speed=5.0, acc=1e6)
                taskMgr.doMethodLater(0.1, camf, "player-lost-zoom-out")
            else:
                # Lost by ejection.
                self._eject_cam_type = 2
                if self._eject_cam_type == 0:
                    point = Point3(0.0,
                                   self.ac.bboxcenter[1] - self.ac.bbox[1] * 0.5,
                                   self.ac.bboxcenter[2] + self.ac.bbox[2] * 1.0)
                    ch = TrackChaser(world=self.world,
                                     point=point, relto=self.ac, rotrel=True,
                                     atref=Vec3(0, 1, 0), upref=Vec3(0, 0, 1),
                                     lookrel=True, minotralt=minotralt)
                elif self._eject_cam_type == 1:
                    point = Point3(0.0,
                                   self.ac.bboxcenter[1] + self.ac.bbox[1],
                                   self.ac.bboxcenter[2] + self.ac.bbox[2] * 0.0)
                    ch = TrackChaser(world=self.world,
                                     point=point,
                                     relto=self.ac, rotrel=True,
                                     atref=Vec3(0, -1, 0), upref=Vec3(0, 0, 1),
                                     lookrel=True, minotralt=minotralt)
                elif self._eject_cam_type == 2:
                    point = Point3(self.ac.bboxcenter[0] + self.ac.bbox[0] * 0.5,
                                   self.ac.bboxcenter[1] + self.ac.bbox[1] * 1.0,
                                   self.ac.bboxcenter[2] + self.ac.bbox[2] * 0.6)
                    ch = TrackChaser(world=self.world,
                                     point=point,
                                     relto=self.ac, rotrel=True,
                                     atref=self.ac, upref=self.ac,
                                     lookrel=True, minotralt=minotralt)
                else:
                    assert False
        else:
            off_dir = randvec(minh=-180, maxh=180, minp=0, maxp=0)
            off_dist = 2.0
            point = self._last_ac_pos + off_dir * off_dist
            atref = self._last_ac_pos
            ch = TrackChaser(world=self.world,
                             point=point, atref=atref,
                             upref=Vec3(0, 0, 1),
                             minotralt=minotralt)
        self._lost_chaser = ch
        self._lost_chaser_move_far = False
        self.world.chaser = self._lost_chaser

        self.cockpit.set_physio_effects(False)

        self.world.pause.set_player_shotdown(True)

        self._lost_wait_pause = 3.0

        taskMgr.add(self._lost_loop, "player-lost-loop", sort=-5)


    def _lost_loop (self, task):

        if not self.world.alive:
            return task.done

        if not self._lost_chaser_move_far:
            if (self._eject_cam_type is not None and
                self.ac.ejection and self.ac.ejection.ref_body() is not None):
                if self._eject_cam_type == 0:
                    move_time = 0.5
                    pilot_point = Point3(1.0, -2.0, -3.0)
                    rbody = self.ac.ejection.ref_body()
                    rdist = rbody.dist(self._lost_chaser)
                    speed = rdist / move_time
                    self._lost_chaser.move_to(point=pilot_point,
                                              relto=rbody, rotrel=True,
                                              atref=self.ac, upref=Vec3(0, 0, 1),
                                              lookrel=True,
                                              speed=speed, acc=1e6)
                    self._lost_wait_pause = 5.0
                elif self._eject_cam_type == 1:
                    rbody = self.ac.ejection.ref_body()
                    self._lost_chaser.move_to(atref=rbody)
                    self._lost_wait_pause = 5.0
                elif self._eject_cam_type == 2:
                    rbody = self.ac.ejection.ref_body()
                    point = Point3(self.ac.bboxcenter[0] + self.ac.bbox[0] * 1.0,
                                   self.ac.bboxcenter[1] + self.ac.bbox[1] * 2.0,
                                   self.ac.bboxcenter[2] + self.ac.bbox[2] * 1.0)
                    self._lost_chaser.move_to(point=point, atref=rbody,
                                              speed=2.0, acc=1e6)
                    self._lost_wait_pause = 5.0
                else:
                    assert False
                self._lost_chaser_move_far = True
            elif not self.ac.alive:
                off_dist = 200.0
                move_time = 0.25
                rel_z_off = 0.10
                min_off_pitch = 0.0
                max_off_pitch = 0.0
                off_dir = randvec(minh=-180, maxh=180,
                                  minp=min_off_pitch, maxp=max_off_pitch)
                point = self._last_ac_pos + off_dir * off_dist
                atref = Point3(self._last_ac_pos +
                               Point3(0.0, 0.0, off_dist * rel_z_off))
                speed = off_dist / move_time
                self._lost_chaser.move_to(point=point, atref=atref,
                                          upref=Vec3(0, 0, 1),
                                          speed=speed, acc=1e6)
                self._lost_chaser_move_far = True
                self._lost_wait_pause = 2.0

        self._lost_wait_pause -= self.world.dt
        if self._lost_wait_pause <= 0.0:
            self.world.pause.set_active(active=True,
                                        canresume=False, desat=1.0)
            return task.done

        return task.cont


    def _zero_inputs (self, keepthr=False, keepwpsel=False):

        self.input_elevator = 0.0
        self.input_ailerons = 0.0
        if not keepthr or not hasattr(self, "input_throttle"):
            self.input_throttle = 0.8 if not self.ac.onground else 0.0
        self.input_inc_throttle = False
        self.input_dec_throttle = False
        self.input_air_brake = False
        self.input_landing_gear = self.ac.onground
        self.input_flaps = FLAPS.TAKEOFF if self.ac.onground else FLAPS.RETRACTED
        self.input_flaps_switch = False
        self.input_steer = 0.0
        self.input_wheel_brake = False
        self.input_fire_weapon = False
        self.fire_chasers_on = False
        self.notifier.set_on_off_indicator("actchaser", self.fire_chasers_on)
        self.view_lock_on = True
        self.cockpit.view_lock_on_off(self.view_lock_on)
        self.notifier.set_on_off_indicator("viewlock", self.view_lock_on)
        self.chaser = self.headchaser
        if not keepwpsel or not hasattr(self, "input_select_weapon"):
            self.input_select_weapon = -1


    def _set_bindings (self):

        # Setup configurable bindings.
        bindings = base.inputconf.bindings
        jsdevs = base.inputconf.jsdevs
        self.bindings = dict((b.name, b) for b in bindings)
        self._jsdevs = dict((j.num, j) for j in jsdevs)

        # Add choice bindings (in dialog, autopilot, etc).
        self._max_choices = 9
        for i in range(self._max_choices):
            name = "choice-%d" % (i + 1)
            self.bindings[name] = (
                AutoProps(name=name, seqs=["%d" % (i + 1)], internal=True))

        # Initialize devices.
        # Remove devices that are not found.
        for jsnum, jsdev in list(self._jsdevs.items()):
            if 1 <= jsnum <= pygame.joystick.get_count():
                pgdev = pygame.joystick.Joystick(jsnum - 1)
                pgdev.init()
                jsdev.dev = pgdev
            else:
                self._jsdevs.pop(jsnum)
        self._js_accept = {}

        # Link bindings to actions.
        self._bind_cmd("pitch", self._setc1("input_elevator"))
        self._bind_cmd("pitch-up", self._setc0("input_elevator", -1.0))
        self._bind_cmd("pitch-up", self._setc0("input_elevator", 0.0), up=True)
        self._bind_cmd("pitch-down", self._setc0("input_elevator", 1.0))
        self._bind_cmd("pitch-down", self._setc0("input_elevator", 0.0), up=True)
        self._bind_cmd("roll", self._setc1(["input_ailerons", "input_steer"]))
        self._bind_cmd("roll-left", self._setc0(["input_ailerons", "input_steer"], -1.0))
        self._bind_cmd("roll-left", self._setc0(["input_ailerons", "input_steer"], 0.0), up=True)
        self._bind_cmd("roll-right", self._setc0(["input_ailerons", "input_steer"], 1.0))
        self._bind_cmd("roll-right", self._setc0(["input_ailerons", "input_steer"], 0.0), up=True)
        self._bind_cmd("throttle", self._setc1t("input_throttle", 0.0, self.throttle_maxab, -1.0))
        self._bind_cmd("throttle-up", self._setc0("input_inc_throttle", True))
        self._bind_cmd("throttle-up", self._setc0("input_inc_throttle", False), up=True)
        self._bind_cmd("throttle-down", self._setc0("input_dec_throttle", True))
        self._bind_cmd("throttle-down", self._setc0("input_dec_throttle", False), up=True)
        self._bind_cmd("air-brake", self._setbinv(["input_air_brake", "input_wheel_brake"]))
        self._bind_cmd("landing-gear", self._setbinv(["input_landing_gear", "input_flaps_switch"]))
        self._bind_cmd("next-target", self.cycle_focus_init)
        self._bind_cmd("next-target", self.cycle_focus, up=True)
        self._bind_cmd("deselect-target", self.deselect_target)
        self._bind_cmd("fire-weapon", self._setc0("input_fire_weapon", True))
        self._bind_cmd("fire-weapon", self._setc0("input_fire_weapon", False), up=True)
        self._bind_cmd("next-target-section", self.cycle_target_section)
        self._bind_cmd("next-weapon", self.cycle_weapon, [1])
        self._bind_cmd("previous-weapon", self.cycle_weapon, [-1])
        self._bind_cmd("radar-on-off", self.radar_on_off)
        self._bind_cmd("radar-scale-up", self.cockpit.cycle_radar_scale, [True])
        self._bind_cmd("radar-scale-down", self.cockpit.cycle_radar_scale, [False])
        self._bind_cmd("next-mfd-mode", self.cockpit.cycle_mfd_mode, [1])
        self._bind_cmd("previous-mfd-mode", self.cockpit.cycle_mfd_mode, [-1])
        self._bind_cmd("fire-decoy", self.ac.fire_decoy)
        self._bind_cmd("cockpit-light-on-off", self.cockpit.light_on_off)
        self._bind_cmd("eject", self.ac.eject)
        self._bind_cmd("view-lock-on-off", self._view_lock_on_off)
        self._bind_cmd("cockpit-view", self._setc0("chaser", self.headchaser))
        if self.dimchaser:
            self._bind_cmd("external-view", self._setc0("chaser", self.dimchaser))
        if self.rvchaser:
            self._bind_cmd("rear-view", self._setc0("chaser", self.rvchaser))
        self._bind_cmd("target-view", self._set_targchaser)
        self._bind_cmd("fire-chaser-on-off", self._setbinv("fire_chasers_on"))
        self._bind_cmd("head-look", self.cockpit.set_view_look)
        self._bind_cmd("head-turn", self.cockpit.set_view_horiz)
        self._bind_cmd("head-turn-left", self.cockpit.set_view_horiz, [-1.0])
        self._bind_cmd("head-turn-left", self.cockpit.set_view_horiz, [0.0], up=True)
        self._bind_cmd("head-turn-right", self.cockpit.set_view_horiz, [1.0])
        self._bind_cmd("head-turn-right", self.cockpit.set_view_horiz, [0.0], up=True)
        self._bind_cmd("head-pitch", self.cockpit.set_view_vert)
        self._bind_cmd("head-pitch-down", self.cockpit.set_view_vert, [-1.0])
        self._bind_cmd("head-pitch-down", self.cockpit.set_view_vert, [0.0], up=True)
        self._bind_cmd("head-pitch-up", self.cockpit.set_view_vert, [1.0])
        self._bind_cmd("head-pitch-up", self.cockpit.set_view_vert, [0.0], up=True)
        self._bind_cmd("zoom-view-in", self._zoom_view, [-5])
        self._bind_cmd("zoom-view-out", self._zoom_view, [+5])
        self._bind_cmd("virtual-cockpit-on-off", self._setbinv("_virtcpit_available"))
        for i in range(self._max_choices):
            self._bind_cmd("choice-%d" % (i + 1), self._make_choice, [i])

        # Map binding names to sequences.
        # Must come after linking to actions, as during linking additional
        # internal bindings may be added (on up= and repeat= parameters).
        self._bindnames_by_seq = {}
        for bindg in self.bindings.values():
            self._bindnames_by_seq.update((x, bindg.name) for x in bindg.seqs)

        # Active choices.
        self._choices = []


    def _bind_cmd (self, bname, cmdf, args=[], up=False, repeat=False):

        bindg = self.bindings.get(bname)
        if bindg is None:
            raise StandardError("Trying to bind unknown action '%s'." % bname)
        ext = ("-up" if up else "") + ("-repeat" if repeat else "")
        bname1 = bname + ext
        if bname1 != bname:
            bindg1 = AutoProps(**dict(bindg.props()))
            bindg1.name = bname1
            bindg1.seqs = []
            bindg1.internal = True
            self.bindings[bname1] = bindg1
        def wcmdf_kb (bseq):
            def wcmdf (*args):
                if (self.world.player_control_level == 0 and
                    not self.world.pause.active and
                    base.challenge_priority("control", bseq)):
                    cmdf(*args)
            return wcmdf
        def wcmdf_js ():
            def wcmdf (*args):
                if (self.world.player_control_level == 0 and
                    not self.world.pause.active):
                    cmdf(*args)
            return wcmdf
        for bseq in bindg.seqs:
            bseq1 = bseq + ext
            self.accept(bseq1, wcmdf_kb(bseq1), args)
            self._js_accept[bname1] = (wcmdf_js(), args)
            base.set_priority("control", bseq1, 10)
            if bname1 != bname:
                self.bindings[bname1].seqs.append(bseq1)
        return bindg.seqs


    def _unbind_cmd (self, bname):

        self.ignore(bname)


    def _setc0 (self, cmdkey, value):

        if isinstance(cmdkey, (tuple, list)):
            def setf ():
                for cmdkey1 in cmdkey:
                    self.__dict__[cmdkey1] = value
        else:
            def setf ():
                self.__dict__[cmdkey] = value

        return setf


    def _setc1 (self, cmdkey):

        if isinstance(cmdkey, (tuple, list)):
            def setf (value):
                for cmdkey1 in cmdkey:
                    self.__dict__[cmdkey1] = value
        else:
            def setf (value):
                self.__dict__[cmdkey] = value

        return setf


    def _setc1t (self, cmdkey, vmin, vmax, vfac=1.0):

        def setf (value):
            tvalue = vmin + (vmax - vmin) * (0.5 + 0.5 * value * vfac)
            self.__dict__[cmdkey] = tvalue

        return setf


    def _setbinv (self, cmdkey):

        if isinstance(cmdkey, (tuple, list)):
            def setf ():
                for cmdkey1 in cmdkey:
                    value = not self.__dict__[cmdkey1]
                    self.__dict__[cmdkey1] = value
        else:
            def setf ():
                value = not self.__dict__[cmdkey]
                self.__dict__[cmdkey] = value

        return setf


    def _set_targchaser (self):

        target = self.target_body
        if self._targchaser_prev_target is not target:
            self._targchaser_prev_target = target
            if self.targchaser:
                self.targchaser.destroy()
                self.targchaser = None
            if target:
                point = Point3(80, -80, 40)
                fov = ANIMATION_FOV
                self.targchaser = ElasticChaser(
                    world=target.world, point=point,
                    relto=target, rotrel=False,
                    atref=target, upref=Vec3(0.0, 0.0, 1.0), fov=fov,
                    distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10)
                self._targchaser_point = point
                self._targchaser_fov = fov
        if self.targchaser:
            self.chaser = self.targchaser


    _usable_joy_events = (
        pygame.JOYAXISMOTION,
        pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
        pygame.JOYHATMOTION,
    )

    def _set_control_joy (self):

        anymod = False
        for e in pygame.event.get(Player._usable_joy_events):
            jnum = e.joy + 1
            jsdev = self._jsdevs.get(jnum)
            if jsdev is not None:
                if e.type == pygame.JOYAXISMOTION:
                    bseq = "axis%d%s" % ((e.axis + 1), jsdev.ext)
                    bname = self._bindnames_by_seq.get(bseq)
                    cmdpack = self._js_accept.get(bname)
                    if cmdpack:
                        cmdf, args = cmdpack
                        bindg = self.bindings[bname]
                        aexp = bindg.exponent
                        adzn = bindg.deadzone
                        amin = bindg.minval
                        amax = bindg.maxval
                        ainv = bindg.inverted
                        aval = e.value
                        aval = clamp(aval, -1.0, 1.0)
                        if abs(aval) <= adzn:
                            aval = 0.0
                        else:
                            absaval1 = (abs(aval) - adzn) / (1.0 - adzn)
                            aval = absaval1**aexp * sign(aval)
                        if ainv:
                            aval *= -1
                        aval = amin + (amax - amin) * ((aval + 1.0) / 2.0)
                        cmdf(aval)
                elif e.type is pygame.JOYBUTTONDOWN:
                    bseq = "joy%d%s" % ((e.button + 1), jsdev.ext)
                    bname = self._bindnames_by_seq.get(bseq)
                    cmdpack = self._js_accept.get(bname)
                    if cmdpack:
                        cmdf, args = cmdpack
                        cmdf(*args)
                elif e.type is pygame.JOYBUTTONUP:
                    bseq = "joy%d%s-up" % ((e.button + 1), jsdev.ext)
                    bname = self._bindnames_by_seq.get(bseq)
                    cmdpack = self._js_accept.get(bname)
                    if cmdpack:
                        cmdf, args = cmdpack
                        cmdf(*args)
                elif e.type == pygame.JOYHATMOTION:
                    bseq = "hat%d%s" % ((e.hat + 1), jsdev.ext)
                    bname = self._bindnames_by_seq.get(bseq)
                    cmdpack = self._js_accept.get(bname)
                    if cmdpack:
                        cmdf, args = cmdpack
                        hval = e.value
                        cmdf(hval)


    def _set_control_mouse (self):

        if self.world.pause.active:
            return

        mouse_delta = base.mouse_watcher.node().getMouse()
        base.center_mouse_pointer()

        if mouse_delta.length() > 1e-4:
            target = self.target_body
            chaser = None
            if self.chaser is self.targchaser and self.targchaser.alive and target.alive:
                chaser = self.targchaser
                point = self._targchaser_point
            elif self.chaser is self.dimchaser and self.dimchaser.alive:
                chaser = self.dimchaser
                point = self._dimchaser_point
            if chaser:
                cam_quat = chaser.quat(refbody=target)
                cam_up = cam_quat.getUp()
                point_fw = unitv(-point)
                point_rt = unitv(point_fw.cross(cam_up))
                point_up = unitv(point_rt.cross(point_fw))
                dang_rt, dang_up = mouse_delta * self._chaser_sens_rot
                rot_up = Quat()
                rot_up.setFromAxisAngleRad(-dang_up, point_rt)
                rot_rt = Quat()
                rot_rt.setFromAxisAngleRad(dang_rt, point_up)
                rot = rot_up * rot_rt
                point_1 = Point3(rot.xform(point))
                chaser.move_to(point=point_1)
                if chaser is self.targchaser:
                    self._targchaser_point = point_1
                elif chaser is self.dimchaser:
                    self._dimchaser_point = point_1


    def _zoom_view (self, dfov=0.0):

        if self.chaser is self.headchaser:
            self.cockpit.zoom_view(dfov)
        else:
            chaser = None
            if self.chaser is self.targchaser:
                target = self.target_body
                if self.targchaser.alive and target.alive:
                    chaser = self.targchaser
                    fov = self._targchaser_fov
            elif self.chaser is self.dimchaser:
                if self.dimchaser.alive:
                    chaser = self.dimchaser
                    fov = self._dimchaser_fov
            if chaser:
                fov_1 = clamp(fov + dfov,
                              self._chaser_min_fov, self._chaser_max_fov)
                chaser.move_to(fov=fov_1)
                if chaser is self.targchaser:
                    self._targchaser_fov = fov_1
                elif chaser is self.dimchaser:
                    self._dimchaser_fov = fov_1


    def cycle_focus_init (self):

        if self.world.player_control_level > 0:
            return

        if self.cockpit.hud_mode in ("atk", "gnd"):
            self._cycle_target_time_pressed = self.world.time


    def cycle_focus (self):

        if self.world.player_control_level > 0:
            return

        if self.world.action_chasers:
            self.world.clear_action_chasers()
            self._cycle_target_time_pressed = None
        elif self.cockpit.hud_mode == "nav":
            self.cycle_waypoint()
            self._cycle_target_time_pressed = None
        elif self.cockpit.hud_mode in ("atk", "gnd"):
            if self._cycle_target_time_pressed is not None:
                time_pressed = self._cycle_target_time_pressed
                self._cycle_target_time_pressed = None
                if (self.world.time - time_pressed >
                    self._cycle_target_deselect_delay):
                    return
            self.cycle_target()


    def deselect_target (self):

        if self.world.player_control_level > 0:
            return

        if self.cockpit.hud_mode in ("atk", "gnd"):
            self._cycle_target_immediate_deselect = True


    def cycle_target (self):

        if self.world.player_control_level > 0:
            return

        if self.input_select_weapon < 0:
            return
        wp = self.weapons[self.input_select_weapon]

        cycle_contact_set = {}
        all_plock = True
        for con in self.ac.sensorpack.contacts():
            if not (con.trackable() or con.firsthand) or con.body.shotdown:
                continue
            if con.body.family in wp.against():
                ret = map_pos_to_screen(self.world.camera, con.body.node,
                                        scrnode=self.world.overlay_root)
                tpos, back = ret
                hw = base.aspect_ratio
                if (not con.trackable() and
                    (back or abs(tpos[0]) > hw or abs(tpos[2]) > 1.0) and
                    con not in self._cycle_tag_contact_set):
                    continue
                if not back:
                    cdist = tpos.length()
                else:
                    cdist = 2 * hw + self.ac.dist(con.body)
                prev_con_spec = self._prev_cycle_contact_set.get(con)
                plock = prev_con_spec[1] if prev_con_spec else False
                track = con.trackable()
                cycle_contact_set[con] = [cdist, plock, track]
                if not plock:
                    all_plock = False
        if all_plock:
            for con, con_spec in cycle_contact_set.iteritems():
                con_spec[1] = False

        if cycle_contact_set:
            cycle = sorted(cycle_contact_set.items(), key=lambda x: x[1][0])
            skip_con = None
            if len(cycle_contact_set) > 1:
                #skip_con = self.target_contact
                skip_con = self.view_contact
            sel_con = None
            for con, (cdist, plock, track) in cycle:
                if not plock and con is not skip_con:
                    sel_con = con
                    sel_con_track = track
                    break
            if sel_con:
                if sel_con_track:
                    self.target_contact = sel_con
                    self.target_body = sel_con.body
                    self.cycle_target_section(reset=True)
                    self.cockpit.update_target_track(sel_con)
                else:
                    self.target_contact = None
                    self.target_body = None
                self.view_contact = sel_con
                self.view_body = sel_con.body
                cycle_contact_set[sel_con][1] = True
                self._cycle_tag_contact_set.add(sel_con)
            else:
                self.target_contact = None
                self.target_body = None
                self.view_contact = None
                self.view_body = None
                cycle_contact_set = {}

        self._prev_cycle_contact_set = cycle_contact_set


    def cycle_target_section (self, reset=False):

        if self.world.player_control_level > 0:
            return

        if not self.target_contact:
            return

        target = self.target_contact.body
        self.target_offset = None
        self.target_hitbox = None
        selhitboxes = [x for x in target.hitboxes if x.selectable]
        if selhitboxes:
            if not reset:
                self._target_section_index += 1
                if self._target_section_index >= len(selhitboxes):
                    self._target_section_index = 0 #-1
            else:
                self._target_section_index = 0 #-1
            secname = None
            if self._target_section_index >= 0:
                hbx = selhitboxes[self._target_section_index]
                self.target_offset = hbx.center
                self.target_hitbox = hbx
                secname = hbx.name
            #print "--cycle-target-section", target.species, secname


    def _update_targeting (self, dt):

        input_deselect = (
            (self._cycle_target_time_pressed is not None and
             self.world.time - self._cycle_target_time_pressed >
                 self._cycle_target_deselect_delay) or
            self._cycle_target_immediate_deselect)
        if self._cycle_target_immediate_deselect:
            self._cycle_target_time_pressed = None
            self._cycle_target_immediate_deselect = False

        if (not self.target_contact or
            not self.target_contact.body.alive or
            self.target_contact not in self.ac.sensorpack.contacts() or
            not self.target_contact.trackable() or
            self.target_contact.body.shotdown or
            input_deselect):
            self.target_contact = None
            self.target_body = None

        if (not self.view_contact or
            not self.view_contact.body.alive or
            self.view_contact not in self.ac.sensorpack.contacts() or
            not self.view_contact.firsthand or
            input_deselect):
            self.view_contact = None
            self.view_body = None

        if (self.view_contact and
            self.view_contact.trackable() and
            not self.target_contact):
            self.target_contact = self.view_contact
            self.target_body = self.view_body

        if not self.target_contact and not self.view_contact:
            self._prev_cycle_contact_set = {}

        weapon_class = None
        weapon_state = None
        if self.target_contact:
            self.ac.target = self.target_contact.body

            if self.input_select_weapon >= 0:
                wp = self.weapons[self.input_select_weapon]
                if isinstance(wp.handle, Launcher) and wp.handle.mtype.seeker:
                    weapon_class = Launcher
                    launcher = wp.handle
                    weapon_state = launcher.ready(target=self.target_contact.body)[0]
                #elif isinstance(wp.handle, Dropper):
        else:
            self.ac.target = None

        self.cockpit.update_target_track(self.target_contact, self.target_offset,
                                         weapon_class, weapon_state)

        view_is_target = self.view_contact is self.target_contact
        self.cockpit.update_view_track(self.view_contact, self.target_offset,
                                       view_is_target)


    def _update_cycle_tag (self, dt):

        self._wait_cycle_tag -= dt
        if self._wait_cycle_tag <= 0.0:
            self._wait_cycle_tag += self._cycle_tag_period
            new_cycle_tag_contact_set = set()
            for con in self._cycle_tag_contact_set:
                if con in self.ac.sensorpack.contacts():
                    new_cycle_tag_contact_set.add(con)
            self._cycle_tag_contact_set = new_cycle_tag_contact_set


    def cycle_weapon (self, skip=1):

        wpind0 = self.input_select_weapon
        wpind = wpind0
        while True:
            wpind += skip
            if wpind >= len(self.weapons):
                wpind = -1
            elif wpind < -1:
                wpind = len(self.weapons) - 1
            if self.target_body:
                wp = self.weapons[wpind] if wpind >= 0 else None
                if wp and self.target_body.family in wp.against():
                    break
            else:
                break
            if wpind == wpind0:
                break
            #if ...:
                #wp = self.weapons[wpind]
                #if wp.available():
                    #break
        if wpind != wpind0:
            wp = self.weapons[wpind] if wpind >= 0 else None
            if (self.target_body and
                (not wp or self.target_body.family not in wp.against())):
                self.target_contact = None
                self.target_body = None
            if (self.view_body and
                (not wp or self.view_body.family not in wp.against())):
                self.view_contact = None
                self.view_body = None
            if wpind0 >= 0:
                wp0 = self.weapons[wpind0]
                wp0.reset()
            if wpind >= 0:
                wp.reset()
            self.input_select_weapon = wpind

        if self.input_select_weapon >= 0:
            return self.weapons[self.input_select_weapon]


    def _set_ac_inputs (self):

        if not self.ac.dynstate:
            return

        dt = self.world.dt

        dq = self.ac.dynstate
        mass, alt, speed = dq.m, dq.h, dq.v
        pos, aoa, throttle, airbrake = dq.p, dq.a, dq.tl, dq.brd
        minaoa, zliftaoa, maxaoa, groundaoa = dq.amin, dq.a0, dq.amax, dq.ag
        nminaoa, nmaxaoa = dq.anmin, dq.anmax
        tmaxaoa = dq.atmaxab
        noneaoa = dq.anone
        maxpitchrate, maxrollrate = dq.pomax, dq.romax
        rollrate, maxrollacc = dq.ro, dq.rsmax
        if self.ac.onground:
            steerrate = dq.gso
        airbrakerate = dq.brdvmax

        # Flight.

        # - throttle
        throttle_speed = 0.5
        if self.input_inc_throttle:
            self.input_throttle += throttle_speed * dt
        elif self.input_dec_throttle:
            self.input_throttle -= throttle_speed * dt
        self.input_throttle = clamp(self.input_throttle, 0.0, self.throttle_maxab)
        if self.ac.fuel == 0.0:
            self.input_throttle = 0.0
        if self.input_throttle <= 1.0:
            throttle1 = self.input_throttle
        else:
            throttle1 = 1.0 + (self.input_throttle - 1.0) / (self.throttle_maxab - 1.0)
            throttle1 = clamp(throttle1, 0.0, 2.0)
        dthrottle = throttle1 - throttle

        # - pitch
        useab = self.ac.dyn.hasab #throttle > 1.0
        minspeed = self.ac.dyn.tab_vmin[0](mass, alt)
        optspeedts = self.ac.dyn.tab_voptts[useab](mass, alt)
        aoaspan = maxaoa - minaoa
        if not self.ac.onground:
            #neutraoa = zliftaoa - 0.1 * (zliftaoa - minaoa)
            if noneaoa is not None:
                neutraoa = noneaoa # - 0.02 * aoaspan
            else:
                neutraoa = zliftaoa
        else:
            neutraoa = groundaoa
        limlwbaoa = minaoa + aoaspan * 0.02
        limupbaoa = maxaoa - aoaspan * 0.04
        limlwcaoa = minaoa - aoaspan * 0.1
        limupcaoa = maxaoa + aoaspan * 0.2
        limspeed = 1.5 * minspeed
        ifac = intc01r(speed, minspeed, limspeed)
        limlwaoa = limlwcaoa + (limlwbaoa - limlwcaoa) * ifac
        limupaoa = limupcaoa + (limupbaoa - limupcaoa) * ifac
        #if tmaxaoa is not None:
            #limspeedt = minspeed + (optspeedts - minspeed) * 0.7
            #limupaoa = intc01vr(speed, minspeed, limspeedt, limupaoa, tmaxaoa)
        if nminaoa is not None and limlwaoa < nminaoa:
            limlwaoa = nminaoa
        if nmaxaoa is not None and limupaoa > nmaxaoa:
            limupaoa = nmaxaoa
        #self._prev_input_elevator.append(self.input_elevator)
        #nelinmax = 10
        #nelin = len(self._prev_input_elevator)
        #while nelin > nelinmax:
            #self._prev_input_elevator.pop(0)
            #nelin -= 1
        #smooth_elevator = sum(self._prev_input_elevator) / nelin
        smooth_elevator = self.input_elevator
        if smooth_elevator > 0.0:
            aoa1 = neutraoa + (limupcaoa - neutraoa) * smooth_elevator
        else:
            aoa1 = neutraoa - (limlwcaoa - neutraoa) * smooth_elevator
        aoa1 = clamp(aoa1, limlwaoa, limupaoa)
        tdaoa = aoa1 - aoa
        if not self.ac.onground or tdaoa > 0.0:
            pitchrate = maxpitchrate * clamp(abs(tdaoa) * 1.2, 0.0, 1.0)
        else:
            pitchrate = maxpitchrate * clamp(abs(tdaoa) * 2.0, 0.4, 1.0)
        daoa = update_towards(tdaoa, 0.0, pitchrate, dt)
        #print "--ac-inputs-51", degrees(dq.pomax), degrees(dq.po)

        # - roll
        smooth_ailerons = self.input_ailerons
        sfac = abs(smooth_ailerons)**0.5
        maxrollacc *= 0.6 #!!!
        rollrate1 = clamp(smooth_ailerons * sfac * maxrollrate,
                          rollrate - maxrollacc * dt,
                          rollrate + maxrollacc * dt)
        droll = rollrate1 * dt
        #print "--ac-inputs-61", degrees(maxrollrate), degrees(rollrate)

        # - air brake
        airbrake1 = self.input_air_brake
        tdairbrake = airbrake1 - airbrake
        dairbrake = update_towards(tdairbrake, 0.0, airbrakerate, dt)

        # - wheel steering
        if self.ac.onground:
            smooth_steer = self.input_steer
            # TODO: Proper input from dynamics.
            minsteerrad0 = self.ac.size * 1.0
            limsteerspeed0 = 0.0
            minsteerrad1 = self.ac.size * 0.5
            limsteerspeed1 = 2.0
            minsteerrad2 = self.ac.size * 2.0
            limsteerspeed2 = 10.0
            minsteerrad3 = self.ac.size * 100.0
            limsteerspeed3 = minspeed * 1.5
            if speed > limsteerspeed2:
                minsteerrad = intl01vr(speed, limsteerspeed2, limsteerspeed3,
                                       minsteerrad2, minsteerrad3)
            elif speed > limsteerspeed1:
                minsteerrad = intl01vr(speed, limsteerspeed1, limsteerspeed2,
                                       minsteerrad1, minsteerrad2)
            else:
                minsteerrad = intl01vr(speed, limsteerspeed0, limsteerspeed1,
                                       minsteerrad0, minsteerrad1)
            maxsteerrate = speed / minsteerrad
            maxsteeracc = maxsteerrate * 1.0
            sfac = 1.0
            steerrate1 = smooth_steer * sfac * maxsteerrate
            dsteer = steerrate1 - steerrate
        else:
            dsteer = 0.0

        # - extensions
        flaps = self.input_flaps
        landgear = self.input_landing_gear
        wheelbrake = self.input_wheel_brake

        # - input
        self.ac.set_cntl(daoa=daoa, droll=droll, dthrottle=dthrottle,
                         dairbrake=dairbrake, flaps=flaps,
                         landgear=landgear, dsteer=dsteer,
                         wheelbrake=wheelbrake)

        # Firing.
        if self.input_select_weapon >= 0:
            wp = self.weapons[self.input_select_weapon]
            if isinstance(wp.handle, Cannon):
                cannon = wp.handle
                rounds = cannon.burstlen if self.input_fire_weapon else 0
                cannon.fire(rounds=rounds)
            elif isinstance(wp.handle, Launcher):
                launcher = wp.handle
                if launcher.mtype.seeker:
                    target = None
                    offset = None
                    if self.target_body:
                        target = self.target_body
                        offset = self.target_offset
                    elif self.cockpit.has_boresight and self.cockpit.boresight_target:
                        target = self.cockpit.boresight_target
                    if self.input_fire_weapon and target:
                        launcher.fire(target=target,
                                      offset=offset,
                                      addchf=self._missile_chasef)
                else:
                    if self.input_fire_weapon:
                        launcher.fire(addchf=self._missile_chasef)
            elif isinstance(wp.handle, Dropper):
                dropper = wp.handle
                if self.input_fire_weapon:
                    dropper.fire(addchf=self._bomb_chasef)
            elif isinstance(wp.handle, PodLauncher):
                podlauncher = wp.handle
                if self.input_fire_weapon:
                    podlauncher.fire()
            #if not wp.available():
                #self.cycle_weapon()


    def set_choice (self, name, num, actf=None, priority=0):

        i = 0
        for i, ch in enumerate(self._choices):
            if ch.name == name:
                break
        if i == len(self._choices):
            if num > 0 and actf is not None:
                # Adding new choice.
                ch = AutoProps()
                ch.name = name
                ch.num = num
                ch.actf = actf
                ch.priority = priority
                self._choices.append(ch)
                self._choices.sort(key=lambda ch: ch.priority)
        else:
            if num > 0 and actf is not None:
                # Updating a choice.
                ch.name = name
                ch.num = num
                ch.actf = actf
                ch.priority = priority
                self._choices.sort(key=lambda ch: ch.priority)
            else:
                # Removing a choice.
                self._choices.pop(i)


    def _view_lock_on_off (self):

        self.view_lock_on = not self.view_lock_on
        self.cockpit.view_lock_on_off(self.view_lock_on)
        self.notifier.set_on_off_indicator("viewlock", self.view_lock_on)


    def _make_choice (self, i):

        if self._choices:
            ch = self._choices[-1]
            if i < ch.num:
                ch.actf(i)


    def show_message (self, *args, **kwargs):

        self.notifier.show_message(*args, **kwargs)


    def add_reported_target (self, *args, **kwargs):

        self.cockpit.add_reported_target(*args, **kwargs)


    def remove_reported_target (self, *args, **kwargs):

        self.cockpit.remove_reported_target(*args, **kwargs)


    def record_kill (self, body):

        if self.mission and body.family in KILL_STATS_FAMILIES:
            kill = SimpleProps(
                family=body.family, species=body.species,
                longdes=body.longdes, shortdes=body.shortdes,
                time=self.world.time)
            self.mission.record_player_kill(kill)


    def record_release (self, body):

        if self.mission:
            release = SimpleProps(
                family=body.family, species=body.species,
                longdes=body.longdes, shortdes=body.shortdes,
                time=self.world.time)
            self.mission.record_player_release(release)


    _turn_back_warnings = [
        _("Running away from the fight? Turn back!"),
        _("The enemy is in the other direction!"),
        _("Navigation system defunct? Check the compass!"),
    ]


    def add_waypoint (self, name, longdes, shortdes,
                      pos, radius, height=None,
                      tozone=None, active=True, exitf=None):

        if name in self._waypoints:
            raise StandardError(
                "Trying to add already existing waypoint '%s'." % name)

        wp = AutoProps()
        wp.name = name
        wp.longdes = longdes
        wp.shortdes = shortdes
        wp.pos = pos
        wp.radius = radius
        wp.height = height
        wp.elev = self.world.elevation(pos)
        self._waypoints[name] = wp
        self._waypoint_keys.append(name)

        if tozone:
            self.add_navpoint(name, longdes, shortdes, tozone,
                              pos, radius, height, active, exitf=exitf)

        self.cockpit.add_waypoint(name, longdes, shortdes, pos, height)

        if self._current_waypoint_name is None:
            self._select_waypoint(name)


    def _select_waypoint (self, name):

        self._current_waypoint_name = name
        self._waypoint_wait_check = 0.0
        self._update_waypoints(0.0)


    def cycle_waypoint (self):

        if not self._current_waypoint_name:
            if self._waypoint_keys:
                self._select_waypoint(self._waypoint_keys[0])
        else:
            i = self._waypoint_keys.index(self._current_waypoint_name)
            i1 = i + 1
            if i1 >= len(self._waypoint_keys):
                i1 = 0
            self._select_waypoint(self._waypoint_keys[i1])


    def at_waypoint (self, name):

        return self._to_marker(self._waypoints[name])[0]


    def waypoint_dist (self, key):

        wp = self._waypoints[key]
        if isinstance(wp.pos, VBase2):
            dpos = wp.pos - self.ac.pos().getXy()
        else:
            dpos = wp.pos - self.ac.pos()
        return dpos.length()


    def _update_waypoints (self, dt):

        self._waypoint_wait_check -= dt
        if self._waypoint_wait_check <= 0.0:
            self._waypoint_wait_check = self._waypoint_check_period
            if self._current_waypoint_name:
                wp = self._waypoints[self._current_waypoint_name]
                ret = self._to_marker(wp)
                there, dist, dalt, dhead = ret
                self.cockpit.update_waypoint_track(self._current_waypoint_name,
                                                   dist, dalt, dhead, there)


    def add_navpoint (self, name, longdes, shortdes, tozone,
                      pos=None, radius=None, height=None,
                      active=True, onbody=None, aerotow=False, exitf=None):

        if not name:
            name = "!anon-%d" % self._navpoint_anon_counter
            self._navpoint_anon_counter += 1
        if name in self._navpoints:
            raise StandardError(
                "Trying to add already existing navpoint '%s'." % name)

        np = AutoProps()
        np.name = name
        np.longdes = longdes
        np.shortdes = shortdes
        np.pos = pos
        np.radius = radius
        np.height = height
        np.tozone = tozone
        np.active = active
        np.onbody = onbody
        np.aerotow = aerotow
        np.exitf = exitf

        if not np.onbody and isinstance(np.pos, VBase2):
            np.elev = self.world.elevation(np.pos)

        self._navpoints[name] = np

        return name


    def update_navpoint (self, name, tozone=False,
                         pos=False, radius=False, height=False,
                         active=None, onbody=False, aerotow=False, exitf=False):

        if name not in self._navpoints:
            raise StandardError("Trying to update non-existing navpoint '%s'." % name)

        np = self._navpoints[name]
        if tozone is not False:
            np.tozone = tozone
        if pos is not False:
            np.pos = pos
        if radius is not False:
            np.radius = radius
        if height is not False:
            np.height = height
        if active is not None:
            np.active = active
        if onbody is not False:
            np.onbody = onbody
        if aerotow is not False:
            np.aerotow = aerotow
        if exitf is not False:
            np.exitf = exitf

        if not np.onbody and isinstance(np.pos, VBase2):
            np.elev = self.world.elevation(np.pos)


    def _update_navjumps (self, dt):

        if self.ac.onground: # outside, to react on runway hops
            self._navjump_wait_clear = self._navjump_clear_delay

        self._wait_actnav -= dt
        self._navjump_wait_clear -= dt
        if self._wait_actnav <= 0.0:
            self._wait_actnav += self._actnav_period
            if not self._navjump_allowed() or self.world.player_control_level > 1:
                self._navjump_wait_clear = self._navjump_clear_delay
            if self._navjump_wait_clear <= 0.0:
                actnps = self.active_navpoints()
            else:
                actnps = []
            actnp_names = set(np.name for np in actnps)
            if self._actnav_names != actnp_names:
                actnps.sort(key=lambda np: np.longdes)
                self._actnav_textnds = []
                self._actnav_selnp = AutoProps()
                def actf (ci):
                    if ci != self._actnav_selnp.index:
                        if self._actnav_selnp.index is not None:
                            textnd = self._actnav_textnds[self._actnav_selnp.index]
                            update_text(textnd, color=self._actnav_text_color)
                        self._actnav_selnp.index = ci
                        self._actnav_selnp.time0 = self.world.wall_time
                        textnd = self._actnav_textnds[self._actnav_selnp.index]
                        update_text(textnd, color=self._actnav_text_sel_color)
                    elif self._actnav_selnp.time0 + self._actnav_seldelay <= self.world.wall_time:
                        self.jump_navpoint = actnps[ci]
                        self._jump_to_zone(actnps[ci].tozone, actnps[ci].exitf)
                self.set_choice("nav", len(actnps), actf, priority=10)
                if self._actnav_text is not None:
                    self._actnav_text.removeNode()
                    self._actnav_text = None
                if actnp_names:
                    text = select_des(_("Autopilot:"), {"ru": u"Автопилот:"},
                                      self._lang)
                    self._actnav_text = make_text(
                        text=text,
                        width=1.0, pos=Point3(-0.80, 0.0, -0.10),
                        font=self._font, size=self._actnav_text_size,
                        color=self._actnav_text_color,
                        shcolor=self._actnav_text_shcolor,
                        align="t", anchor="tl",
                        shader=self._text_shader,
                        parent=self.node2d)
                    dz = font_scale_for_ptsize(self._actnav_text_size) * 1.5
                    for i, np in enumerate(actnps):
                        keys = self.bindings["choice-%d" % (i + 1)].seqs
                        keyfmt = ", ".join(keys)
                        text = (_("[%(key)s] %(navpoint)s") %
                                dict(key=keyfmt, navpoint=np.longdes))
                        textnd = make_text(
                            text=text,
                            width=1.0, pos=Point3(0.0, 0.0, -dz * (i + 1)),
                            font=self._font, size=self._actnav_text_size,
                            color=self._actnav_text_color,
                            shcolor=self._actnav_text_shcolor,
                            align="t", anchor="tl",
                            shader=self._text_shader,
                            parent=self._actnav_text)
                        self._actnav_textnds.append(textnd)
                self._actnav_names = actnp_names
            elif self._actnav_selnp.index is not None:
                if self._actnav_selnp.time0 + self._actnav_clrdelay <= self.world.wall_time:
                    textnd = self._actnav_textnds[self._actnav_selnp.index]
                    update_text(textnd, color=self._actnav_text_color)
                    self._actnav_selnp = AutoProps()


    def _jump_to_zone (self, zoneid, exitf=None):

        if zoneid:
            # Configure plane for jump.
            self.input_air_brake = False
            self.input_flaps = False
            self.input_landing_gear = False
            self.input_wheel_brake = False

            m = self.world.mission
            if m and not m.switching_zones():
                m.switch_zone(zoneid, exitf=exitf)


    def _navjump_allowed (self):

        acp = self.ac
        friendlies = self.world.get_friendlies(
            self._no_navjump_when_attacked_families, acp.side)
        for family in self._no_navjump_when_target_families:
            for body in self.world.iter_bodies(family):
                if not body.alive:
                    continue
                if body.target in friendlies and body is not acp:
                    return False

        return True


    def active_navpoints (self):

        actnps = []
        for npname, np in self._navpoints.items():
            if np.onbody and (not np.onbody.alive or np.onbody.shotdown):
                self._navpoints.pop(npname)
            elif (np.active() if callable(np.active) else np.active):
                if np.aerotow:
                    if self._aerotow_active(np.onbody):
                        actnps.append(np)
                elif self._to_marker(np)[0]:
                    actnps.append(np)
        return actnps


    def _aerotow_active (self, tac):

        active = False
        # FIXME: Temporary, until in-game hook implemented.
        if not tac.shotdown:
            bdist = self.ac.dist(tac)
            if bdist < self._aerotow_max_dist:
                spdiff = abs(self.ac.speed() - tac.speed())
                offb = self.ac.offbore(tac)
                offbinv = tac.offbore(self.ac)
                if (spdiff < self._aerotow_max_speed_diff and
                    offb < self._aerotow_max_offbore and
                    offbinv > pi - self._aerotow_max_offbore):
                    active = True
        return active


    def _to_marker (self, md):

        ppos = self.ac.pos()
        bmpos = md.pos
        if bmpos is None:
            bmpos = Point3()
        if not md.onbody:
            mpos = bmpos
            onground = isinstance(bmpos, VBase2)
        else:
            mpos = md.onbody.pos() + bmpos
            onground = False
        if md.height is not None and md.height < 0.0:
            mpos = Point3(mpos[0], mpos[1], ppos[2])
        elif onground:
            mpos = Point3(mpos[0], mpos[1], md.elev)
        dalt = ppos.getZ() - mpos.getZ()
        dist = (ppos - mpos).length()
        dhead = hpr_to(ppos, mpos)[0]
        there = (md.radius is not None and dist < md.radius and
                 (md.height is None or md.height < 0.0 or
                  (onground and 0.0 < dalt < md.height) or
                  (not onground and -0.5 * md.height < dalt < 0.5 * md.height)))
        return there, dist, dalt, dhead


    def radar_on_off (self):

        if self.ac.sensorpack.emissive:
            self.ac.sensorpack.set_emissive(active=False)
        else:
            self.ac.sensorpack.set_emissive(active=True)


class PlayerNotifier (object):

    def __init__ (self, player):

        self.player = player
        self.world = player.ac.world

        self.node = self.world.overlay_root.attachNewNode("player-notifier")
        shader = make_shader(glow=rgba(255, 255, 255, 0.8))
        self.node.setShader(shader)
        self._text_shader = make_text_shader(glow=rgba(255, 255, 255, 0.4))
        #self.node = self.world.uiface_root.attachNewNode("player-notifier")
        #self._text_shader = None

        self._only_head_node = self.node.attachNewNode("only-head")
        self._only_head_node.hide()

        self._setup_messages()
        self._setup_indicators_on_off()

        self.alive = True
        base.taskMgr.add(self._loop, "notifier-loop", sort=-1)
        # ...should come before mission loops.


    def _setup_messages (self):

        hw = base.aspect_ratio
        self._message = {}

        font = None # default

        self._message["state"] = {}
        self._message["state"]["small"] = SimpleText(
            width=1.25, pos=Point3(-hw + 0.10, 0.0, 0.90),
            font=font, size=14, color=rgba(255, 255, 255, 1.0),
            align="l", anchor="tl",
            textshader=self._text_shader, parent=self.node)
        self._message["state"]["big"] = SimpleText(
            width=1.65, pos=Point3(-hw + 0.10, 0.0, 0.90),
            font=font, size=26, color=rgba(255, 255, 255, 1.0),
            align="l", anchor="tl",
            textshader=self._text_shader, parent=self.node)
        self._message["state"]["poke"] = SimpleText(
            width=2.5, pos=Point3(0.0, 0.0, 0.60),
            size=26, color=rgba(255, 255, 255, 1.0),
            align="c", anchor="mc",
            textshader=self._text_shader, parent=self.node)

        self._message["info"] = {}
        self._message["info"]["small"] = SimpleText(
            width=1.25, pos=Point3(0.0, 0.0, 0.40),
            font=font, size=14, color=rgba(255, 255, 255, 1.0),
            align="c",
            textshader=self._text_shader, parent=self.node)
        self._message["info"]["big"] = SimpleText(
            width=1.65, pos=Point3(0, 0.0, 0.10),
            font=font, size=26, color=rgba(255, 255, 255, 1.0),
            align="c",
            textshader=self._text_shader, parent=self.node)

        self._message["narrator"] = {}
        self._message["narrator"]["big"] = SimpleText(
            width=1.65, pos=Point3(0.0, 0.0, 0.10),
            font=font, size=26, color=rgba(255, 255, 255, 1.0),
            align="c",
            textshader=self._text_shader, parent=self.node)

        self._message["notification"] = {}
        self._message["notification"]["left"] = BubbleText(
            width=0.6, height=0.4, pos=Point3(-hw + 0.8, 0.0, -0.2),
            font=font, size=10, color=rgba(255, 255, 255, 1.0),
            framebase="images/ui/textfloat01", framesize=0.02,
            textshader=self._text_shader, parent=self.node)

        for mgrp in self._message.values():
            for msg in mgrp.values():
                if isinstance(msg, NodePath):
                    msg.hide()
        self._prev_message_text = dict([(x, None) for x in self._message.keys()])
        self._prev_message_task = dict([(x, None) for x in self._message.keys()])


    def _setup_indicators_on_off (self):

        size = 0.10
        alpha_on = 0.70
        alpha_off = 0.20
        margin_horiz = 0.05
        margin_vert = 0.05
        skip_horiz = 0.05
        skip_vert = 0.05

        self._indicator_alpha_on = alpha_on
        self._indicator_alpha_off = alpha_off

        hw = base.aspect_ratio
        parent = self._only_head_node

        self._indicator_nodes = {}

        def grid_pos_br (i_horiz, i_vert):
            return Point3(
                hw - margin_horiz - (size + skip_horiz) * i_horiz - size * 0.5,
                0.0,
                -1.0 + margin_vert + (size + skip_vert) * i_vert + size * 0.5)

        self._indicator_nodes["actchaser"] = make_image(
            texture="images/cockpit/cockpit_mig29_action_chaser_tex.png",
            size=size, pos=grid_pos_br(0, 0), twosided=True, parent=parent)

        self._indicator_nodes["viewlock"] = make_image(
            texture="images/cockpit/cockpit_mig29_view_lock_tex.png",
            size=size, pos=grid_pos_br(1, 0), twosided=True, parent=parent)

        for node in self._indicator_nodes.values():
            node.setSa(alpha_off)


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        for msgs in self._message.values():
            for msg in msgs.values():
                msg.destroy()
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.player.alive or not self.player.ac.alive:
            self.destroy()
            return task.done

        dt = self.world.dt

        if self.player.cockpit.active:
            self._only_head_node.show()
        else:
            self._only_head_node.hide()

        return task.cont


    def show_message (self, mgroup, mtype, text, duration=None, blink=0.0):

        tobj = self._message[mgroup][mtype]
        if isinstance(tobj, BubbleText):
            tobj.add(text, duration)
        elif isinstance(tobj, SimpleText):
            tobj.show(text, duration, blink)


    def set_on_off_indicator (self, name, on):

        ind_node = self._indicator_nodes[name]
        if on:
            ind_node.setSa(self._indicator_alpha_on)
        else:
            ind_node.setSa(self._indicator_alpha_off)


