# -*- coding: UTF-8 -*-

import codecs
from ConfigParser import SafeConfigParser
from math import degrees, radians
import os

from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import Point2, Vec3, Point3, Quat
from pandac.PandaModules import NodePath

import pygame

from src import OUTSIDE_FOV, ANIMATION_FOV
from src.core.bomb import Dropper
from src.core.chaser import HeadChaser, ElasticChaser, TrackChaser
from src.core.cockpit import Cockpit, VirtualCockpit, Helmet
from src.core.dialog import Dialog
from src.core.interface import SimpleText, BubbleText
from src.core.interface import KILL_STATS_FAMILIES
from src.core.misc import AutoProps, SimpleProps, rgba, update_towards
from src.core.misc import sign, clamp, unitv
from src.core.misc import intc01r, intl01v, intc01vr, intl01vr, hprtovec
from src.core.misc import make_image
from src.core.misc import uniform, randrange, choice, randvec
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
        self.helmet = Helmet(self)
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

        c = base.gameconf.cheat
        if (c.adamantium_bath or c.flying_dutchman or c.guards_tanksman or
            c.chernobyl_liquidator):
            ac.strength = 1e10
            ac.maxhitdmg = 1e10

        self.alive = True
        base.taskMgr.add(self._loop, "player-loop", sort=-5)
        base.taskMgr.add(self._slow_loop, "player-slow-loop", sort=-5)
        # ...should come after helmet and cockpit loops.


    def destroy (self):

        if self.alive == False:
            return
        self.alive = False
        for jsdev in self._jsdevs.values():
            jsdev.dev.quit()
        self.notifier.destroy()
        self.helmet.destroy()
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
        self.helmet.active = world.chaser is self.headchaser

        outchs = (self.dimchaser, self.rvchaser, self.targchaser)
        self.virtcpit.active = (self._virtcpit_available and
                                (world.chaser in outchs or
                                 world.chaser in world.action_chasers))

        if self._prev_player_control_level != pclev:
            self._prev_player_control_level = pclev
            self.helmet.active = (pclev < 2)
            self._zero_inputs(keepthr=True, keepwpsel=True)
            if pclev == 0:
                self.headchaser.move_to(atref=Vec3(0.0, 1.0, 0.0))
                self.ac.zero_ap()

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

        self.helmet.set_physio_effects(False)

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
        self._bind_cmd("next-waypoint-target", self.helmet.cycle_waypoint_target_init)
        self._bind_cmd("next-waypoint-target", self.helmet.cycle_waypoint_target, up=True)
        self._bind_cmd("deselect-target", self.helmet.deselect_target)
        self._bind_cmd("fire-weapon", self._setc0("input_fire_weapon", True))
        self._bind_cmd("fire-weapon", self._setc0("input_fire_weapon", False), up=True)
        self._bind_cmd("next-target-section", self.helmet.cycle_target_section)
        self._bind_cmd("next-weapon", self.cycle_weapon, [1])
        self._bind_cmd("previous-weapon", self.cycle_weapon, [-1])
        self._bind_cmd("radar-on-off", self.cockpit.radar_on_off)
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

        target = self.helmet.target_body
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
            target = self.helmet.target_body
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
                target = self.helmet.target_body
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


    def cycle_weapon (self, skip=1):

        wpind0 = self.input_select_weapon
        wpind = wpind0
        while True:
            wpind += skip
            if wpind >= len(self.weapons):
                wpind = -1
            elif wpind < -1:
                wpind = len(self.weapons) - 1
            if self.helmet.target_body:
                wp = self.weapons[wpind] if wpind >= 0 else None
                if wp and self.helmet.target_body.family in wp.against():
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
            if (self.helmet.target_body and
                (not wp or self.helmet.target_body.family not in wp.against())):
                self.helmet.target_contact = None
                self.helmet.target_body = None
            if (self.helmet.view_body and
                (not wp or self.helmet.view_body.family not in wp.against())):
                self.helmet.view_contact = None
                self.helmet.view_body = None
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
                    if self.helmet.target_body:
                        target = self.helmet.target_body
                        offset = self.helmet.target_offset
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


    def add_waypoint (self, *args, **kwargs):

        return self.cockpit.add_waypoint(*args, **kwargs)


    def at_waypoint (self, *args, **kwargs):

        return self.cockpit.at_waypoint(*args, **kwargs)


    def waypoint_dist (self, *args, **kwargs):

        return self.cockpit.waypoint_dist(*args, **kwargs)


    def add_navpoint (self, *args, **kwargs):

        return self.cockpit.add_navpoint(*args, **kwargs)


    def update_navpoint (self, *args, **kwargs):

        return self.cockpit.update_navpoint(*args, **kwargs)


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

        if self.player.helmet.active:
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


