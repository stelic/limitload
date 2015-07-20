# -*- coding: UTF-8 -*-

from math import radians, degrees, pi, sqrt, sin, cos, tan, asin, acos, atan

from direct.directtools.DirectGeometry import LineNodePath
from pandac.PandaModules import VBase2, Vec3, Vec3D, Point3, QuatD

from src import pycv
from src.core.body import Body, EnhancedVisual
from src.core.curve import Segment, Arc
from src.core.fire import PolyExplosion
from src.core.misc import AutoProps, rgba, print_each, load_model_lod_chain
from src.core.misc import hprtovec, hpr_to
from src.core.misc import unitv, clamp, vtod, vtof, ptod, qtod, qtof, intl01v
from src.core.misc import intercept_time, explosion_reach
from src.core.misc import uniform, randunit
from src.core.misc import max_intercept_range
from src.core.misc import dbgval
from src.core.shader import make_stores_shader
from src.core.sound import Sound3D
from src.core.transl import *


class Rocket (Body):

    family = "rocket"
    species = "generic"
    longdes = _("generic")
    shortdes = _("G/RCK")
    cpitdes = {}
    against = []
    mass = 150.0
    diameter = 0.140
    maxg = 20.0
    vmaxalt = 12000.0
    minspeed = 470.0
    minspeed1 = 470.0
    maxspeed = 650.0
    maxspeed1 = 850.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 20.0
    minlaunchdist = 1000.0
    hitforce = 5.0
    expforce = 50.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 2.0
    decoyresist = 0.7
    rcs = 0.00010
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = None
    texture = None
    normalmap = None
    glowmap = "models/weapons/_glowmap.png"
    glossmap = "models/weapons/_glossmap.png"
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    engsoundname = None
    engvol = 0.3
    launchvol = 0.5
    expvol = 0.8

    _seekers_local = set(("ir", "tv", "intv", "arh"))
    _seekers_remote = set(("sarh", "salh", "radio", "wire"))
    _seekers_none = set((None,))
    _seekers_all = _seekers_local.union(_seekers_remote).union(_seekers_none)

    _flightmodes_all = set(("transfer", "intercept", "inertial"))

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None,
                  extvis=True):

        if pos is None:
            pos = Vec3()
        if hpr is None:
            hpr = Vec3()
        if speed is None:
            d1, maxspeed = self.limspeeds(pos[2])
            speed = maxspeed

        if False: # no point checking in every instance...
            if self.seeker not in Rocket._seekers_all:
                raise StandardError(
                    "Unknown seeker type '%s' for '%s'." %
                    (self.seeker, self.species))
            unknown = set(self.flightmodes).difference(Rocket._flightmodes_all)
            if unknown:
                raise StandardError(
                    "Unknown flight mode '%s' for '%s'." %
                    (unknown.pop(), self.species))

        if dropvel is not None:
            vel = hprtovec(hpr) * speed + dropvel
        else:
            vel = speed

        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=self.hitforce,
            modeldata=AutoProps(
                path=self.modelpath,
                texture=self.texture, normalmap=self.normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            amblit=True, dirlit=True, pntlit=1, fogblend=True,
            ltrefl=(self.glossmap is not None),
            name=name, side=side,
            pos=pos, hpr=hpr, vel=vel)

        self.ming = -self.maxg

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, limnum="hum", volume=self.engvol, loop=True)
            self.engine_sound.play()
        if 1:
            lnchsnd = Sound3D(
                "audio/sounds/%s.ogg" % "missile-launch",
                parent=self, volume=self.launchvol, fadetime=0.1)
            lnchsnd.play()

        self.target = target
        self.offset = offset
        self.must_hit_expforce = 0.0
        self.proximity_fuze_active = True
        self._last_target = target

        self.path = None
        self.pspeed = None

        self._targeted_offset = (self.offset or
                                 (self.target and self.target.center) or
                                 Point3())
        self._effective_offset = self._targeted_offset

        self._actdist = min(0.5 * self.minlaunchdist, 1000.0)
        self._active = False
        self._armdist = self.minlaunchdist
        self._armed = False

        self._state_info_text = None
        self._wait_time_state_info = 0.0

        self._prev_path = None
        self._path_pos = 0.0

        self.exhaust_trails = []

        if side == "bstar":
            trcol = rgba(127, 0, 0, 1)
        elif side == "nato":
            trcol = rgba(0, 0, 127, 1)
        else:
            trcol = rgba(0, 127, 0, 1)
        self._trace = None
        if world.show_traces:
            self._trace = LineNodePath(parent=self.world.node,
                                       thickness=1.0, colorVec=trcol)
            self._trace_segs = []
            self._trace_lens = []
            self._trace_len = 0.0
            self._trace_maxlen = 5000.0
            self._trace_prevpos = pos
            self._trace_frameskip = 5
            self._trace_accuframe = 0

        self._flightdist = 0.0
        self._flighttime = 0.0

        self._updperiod_decoy = 0.053
        self._updwait_decoy = 0.0
        self._dtime_decoy_process = 0.0
        self._eliminated_decoys = set()
        self._tracked_decoy = None

        self._no_target_selfdest_time = 1.0
        self._no_target_time = 0.0

        test_expforce = max(self.expforce * 0.9, self.expforce - 1.0)
        self._prox_dist = explosion_reach(test_expforce)
        self.proximity_fuzed = False # debug
        self.target_hit = False # debug

        if extvis:
            bx, by, bz = self.bbox
            bbox = Vec3(bx, by * 500.0, bz)
            EnhancedVisual(parent=self, bbox=bbox)

        self._fudge_player_manoeuver = True
        if self._fudge_player_manoeuver:
            self._plmanv_done_1 = False
            self._plmanv_done_2 = False

        base.taskMgr.add(self._loop, "rocket-loop-%s" % self.name)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if self.target and not self.target.alive:
            self.target = None

        # Keep track of last known and alive target.
        # Needed e.g. to apply force explosion damage.
        if self.target and self.target.alive:
            self._last_target = self.target
        elif self._last_target and not self._last_target.alive:
            self._last_target = None

        dt = self.world.dt
        pos = self.pos()
        vel = self.vel()

        if self.world.below_surface(pos):
            posg = self.world.intersect_surface(pos - vel * dt, pos)
            self.explode(pos=posg)
            return task.done

        if self._flighttime >= self.maxflighttime:
            self.explode()
            return task.done

        if not self._active and (self._flightdist >= self._actdist or
                                 self.must_hit_expforce > 0.0):
            self._active = True
            # Initial autopilot state.
            self._ap_currctl = None
            self._ap_pause = 0.0

        if not self._armed and self._flightdist >= self._armdist:
            self.set_hitboxes(hitboxdata=self.hitboxdata)
            self._armed = True

        # Update offset for decoys.
        if self.target:
            self._updwait_decoy -= dt
            self._dtime_decoy_process += dt
            if self._updwait_decoy <= 0.0:
                self._updwait_decoy += self._updperiod_decoy
                ret = self._process_decoys(self.target, self._targeted_offset,
                                           self._dtime_decoy_process)
                self._effective_offset = ret
                self._dtime_decoy_process = 0.0

        # Activate proximity fuze if near miss.
        if (self._armed and self.proximity_fuze_active and self.target and
            not self.world.in_collision(self)):
            tdir = self.target.pos(refbody=self, offset=self._targeted_offset)
            # ...not self._effective_offset.
            tdist = tdir.length()
            #print_each(1350, 1.0, "--rck-prox-check tdist=%.0f[m]" % tdist)
            if tdist < self._prox_dist or self.must_hit_expforce > 0.0:
                tdir.normalize()
                offbore = acos(clamp(tdir[1], -1.0, 1.0))
                if offbore > self.maxoffbore:
                    #print "--rck-proxfuze", tdist, degrees(offbore)
                    self.explode()
                    self.proximity_fuzed = True # debug
                    return task.done

        # Apply autopilot.
        if self._active:
            if not self.target:
                # TODO: Look for another target?
                if self.seeker not in Rocket._seekers_none:
                    self._no_target_time += dt
                    if self._no_target_time >= self._no_target_selfdest_time:
                        self.explode()
                        return task.done
            else:
                self._no_target_time = 0.0
            self._ap_pause -= dt
            if self._ap_pause <= 0.0:
                self._ap_pause = self._ap_input(dt)
                if self._ap_pause is None:
                    self.target = None
                    self._ap_pause = 2.0

        #for trail in self.exhaust_trails:
            #pass

        # Update trace (debugging).
        if self._trace is not None:
            self._trace_accuframe += 1
            if self._trace_accuframe >= self._trace_frameskip:
                self._trace_accuframe = 0
                while self._trace_len >= self._trace_maxlen and self._trace_segs:
                    tseg = self._trace_segs.pop(0)
                    tlen = self._trace_lens.pop(0)
                    self._trace_len -= tlen
                self._trace_segs.append((self._trace_prevpos, pos))
                self._trace_lens.append((pos - self._trace_prevpos).length())
                self._trace_len += self._trace_lens[-1]
                self._trace.reset()
                self._trace.drawLines(self._trace_segs)
                #self._trace.drawTo(pos)
                self._trace.create()
                self._trace_prevpos = pos

        return task.cont


    def destroy (self):

        if not self.alive:
            return

        if self._trace is not None:
            self._trace.removeNode()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos, silent=True)
        if inert:
            return True

        self.target_hit = (obody is self.target) # debug

        self.explode()

        return False


    def explode (self, pos=None):

        if not self.alive:
            return

        if pos is None:
            pos = self.pos()
        if self.world.otr_altitude(pos) < 20.0:
            debrispitch = (10, 80)
        else:
            debrispitch = (-90, 90)
        exp = PolyExplosion(
            world=self.world, pos=pos,
            sizefac=1.4, timefac=0.4, amplfac=0.8,
            smgray=pycv(py=(115, 150), c=(220, 255)), smred=0, firepeak=(0.5, 0.8),
            debrispart=(3, 6),
            debrispitch=debrispitch)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion-missile",
            parent=exp, volume=self.expvol, fadetime=0.1)
        snd.play()

        self.shotdown = True
        self.destroy()

        touch = []
        if self.must_hit_expforce > 0.0 and self._last_target:
            touch = [(self._last_target, self.must_hit_expforce)]
        self.world.explosion_damage(force=self.expforce, ref=self, touch=touch)


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        if dt == 0.0:
            return

        pos = vtod(self.pos())
        alt = pos[2]
        vel = vtod(self.vel())
        vdir = unitv(vel)
        speed = vel.length()
        quat = qtod(self.quat())
        udir = quat.getUp()
        fdir = quat.getForward()
        rdir = quat.getRight()
        angvel = vtod(self.angvel())

        if self._prev_path is not self.path: # must come before next check
            self._prev_path = self.path
            self._path_pos = 0.0
        if self.path is None or self.path.length() < self._path_pos:
            tdir = vdir
            ndir = udir
            if self.path is not None:
                tdir = self.path.tangent(self.path.length())
                ndir = self.path.normal(self.path.length())
            self.path = Segment(Vec3D(), tdir * 1e5, ndir)
            self._prev_path = self.path
            self._path_pos = 0.0

        # ====================
        # Translation.

        minspeed, maxspeed = self.limspeeds(alt)
        if self.pspeed is None:
            self.pspeed = maxspeed
        self.pspeed = clamp(self.pspeed, minspeed, maxspeed)
        minacc, maxacc = self.limaccs(alt=alt, speed=speed)
        dspeed = self.pspeed - speed
        if dspeed >= 0.0:
            tacc = min(dspeed * 1.0, maxacc)
        else:
            tacc = max(dspeed * 1.0, minacc)

        s = self._path_pos
        dp = self.path.point(s)
        t = self.path.tangent(s)
        tvel = vel.dot(t)
        s1 = s + tvel * dt + tacc * (0.5 * dt**2)
        dp1 = self.path.point(s1)
        tvel1 = tvel + tacc * dt
        t1 = self.path.tangent(s1)
        vel1 = t1 * tvel1
        dpos = dp1 - dp
        #acc = (dpos - vel * dt) / (0.5 * dt**2)
        n1 = self.path.normal(s1)
        r1 = self.path.radius(s1)
        acc = t1 * tacc + n1 * (tvel1**2 / r1)
        self._path_pos = s1

        self.node.setPos(vtof(pos + dpos))
        self._prev_vel = Vec3(self._vel) # needed in base class
        self._vel = vtof(vel1) # needed in base class
        self._acc = vtof(acc) # needed in base class

        # ====================
        # Rotation.

        fdir1 = t1
        paxis = fdir.cross(fdir1)
        if paxis.length() > 1e-5:
            paxis.normalize()
            dspitch = fdir.signedAngleRad(fdir1, paxis)
        else:
            paxis = rdir
            dspitch = 0.0
        pdang = dspitch
        pdquat = QuatD()
        pdquat.setFromAxisAngleRad(pdang, paxis)

        dquat = pdquat
        quat1 = quat * dquat

        angvel1 = (paxis * pdang) / dt
        angacc = (angvel1 - angvel) / dt

        self.node.setQuat(qtof(quat1))
        self._angvel = vtof(angvel1) # needed in base class
        self._angacc = vtof(angacc) # needed in base class

        self._flighttime += dt
        self._flightdist += dpos.length()

        # print_each(105, 0.25, "--rck1", pos, speed, self._flighttime)


    def limspeeds (self, alt=None):

        if alt is None:
            alt = self.pos()[2]

        return self.limspeeds_st(self, alt)


    @staticmethod
    def limspeeds_st (clss, alt):

        minspeed0, minspeed0b = clss.minspeed, clss.minspeed1
        maxspeed0, maxspeed0b = clss.maxspeed, clss.maxspeed1

        alt0b = clss.vmaxalt
        if alt < alt0b:
            ifac = alt / alt0b
            minspeed = minspeed0 + (minspeed0b - minspeed0) * ifac
            maxspeed = maxspeed0 + (maxspeed0b - maxspeed0) * ifac
        else:
            minspeed = minspeed0b
            maxspeed = maxspeed0b

        return minspeed, maxspeed


    def limaccs (self, alt=None, speed=None):

        if alt is None:
            alt = self.pos()[2]
        if speed is None:
            speed = self.speed()

        return self.limaccs_st(self, alt, speed)


    @staticmethod
    def limaccs_st (clss, alt, speed):

        maxthracc0, maxthracc0b = clss.maxthracc, clss.maxthracc1
        maxvdracc0, maxvdracc0b = clss.maxvdracc, clss.maxvdracc1

        # Altitude influence.
        alt0b = clss.vmaxalt
        if alt < alt0b:
            afac = alt / alt0b
            maxthracc = maxthracc0 + afac * (maxthracc0b - maxthracc0)
            maxvdracc = maxvdracc0 + afac * (maxvdracc0b - maxvdracc0)
        else:
            maxthracc = maxthracc0b
            maxvdracc = maxvdracc0b

        # Speed influence.
        minspeed, maxspeed = clss.limspeeds_st(clss, alt)
        sfac = speed / maxspeed
        minacc0 = maxvdracc * -sfac
        maxacc0 = maxthracc * (1.0 - sfac)
        minacc = minacc0
        maxacc = maxacc0

        return minacc, maxacc


    def _ap_input (self, dt):

        w = self.world
        t = self.target

        #print "========== rck-ap-start (world-time=%.2f)" % (w.time)

        # Choose initial control and flight mode.
        if self._ap_currctl is None:
            if self.seeker in Rocket._seekers_local:
                self._ap_currctl = "local"
            elif self.seeker in Rocket._seekers_remote:
                self._ap_currctl = "remote"
            else: # self.seeker in Rocket._seekers_none
                self._ap_currctl = "continue"
            if "transfer" in self.flightmodes:
                self._ap_currflt = "transfer"
            elif "intercept" in self.flightmodes:
                self._ap_currflt = "intercept"
            else: # "inertial" in self.flightmodes
                self._ap_currflt = "inertial"

        pos = ptod(self.pos())
        alt = pos[2]
        vel = vtod(self.vel())
        vdir = unitv(vel)
        speed = vel.length()
        if t and t.alive:
            tpos = ptod(t.pos(offset=self._effective_offset))
            tvel = vtod(t.vel())
            tspeed = tvel.length()
            tacc = vtod(t.acc())
            tabsacc = tacc.length()
        ppitch = self.ppitch()

        minspeed, maxspeed = self.limspeeds(alt)
        maxlfac = self.maxg
        minlfac = self.ming

        if t and t.alive:
            dpos = tpos - pos
            tdist = dpos.length()
            tdir = unitv(dpos)

        # Check if still tracking and return if not.
        havectl = False
        while not havectl: # control may switch
            if t and t.alive:
                if self._ap_currctl == "local":
                    # Check if the target is still within seeker FOV.
                    cosoffbore = tdir.dot(vdir)
                    tracking = (cosoffbore > cos(self.maxoffbore) or
                                self.must_hit_expforce > 0.0)
                    if tracking:
                        havectl = True
                    else:
                        if self.seeker in Rocket._seekers_remote:
                            self._ap_currctl = "remote"
                            # FIXME: What if no transfer mode?
                            self._ap_currflt = "transfer"
                        else:
                            havectl = True
                elif self._ap_currctl == "remote":
                    # TODO: Check if parent still tracks the target.
                    tracking = True
                    havectl = True
                elif self._ap_currctl == "continue":
                    tracking = False
                    havectl = True
            else:
                self._ap_currctl == "continue"
                tracking = False
                havectl = True

        if self._fudge_player_manoeuver:
            # Check special player manoeuvring to throw off the missile.
            player = self.world.player
            if tracking and player and t is player.ac:
                outer_time = 4.0 # as for outer pip on missile tracker
                inner_time = 2.0 # as for inner pip on missile tracker
                rel_reset_time = 1.2
                lim_pitch_ang = radians(-20)
                rel_max_load = 0.8
                lim_aspect_ang = radians(45)
                assert inner_time < outer_time
                assert rel_reset_time > 1.0
                assert pi * -0.5 < lim_pitch_ang < 0.0
                assert 0.0 < rel_max_load < 1.0
                assert 0.0 < lim_aspect_ang < pi * 0.5
                intc_time = tdist / speed
                pdq = player.ac.dynstate
                if intc_time > outer_time * rel_reset_time:
                    self._plmanv_done_1 = False
                    self._plmanv_done_2 = False
                if not self._plmanv_done_1:
                    if intc_time < outer_time:
                        udir = vtof(pdq.xit)
                        pitch_ang = 0.5 * pi - acos(clamp(udir[2], -1.0, 1.0))
                        if pitch_ang < lim_pitch_ang:
                            self._plmanv_done_1 = True
                if not self._plmanv_done_2:
                    if intc_time < inner_time:
                        ndir = pdq.xin
                        aspect_ang = acos(clamp(ndir.dot(-tdir), -1.0, 1.0))
                        if aspect_ang < lim_aspect_ang:
                            nmaxv = pdq.nmaxvab if pdq.hasab else pdq.nmaxv
                            nmaxc = min(pdq.nmax, nmaxv)
                            if pdq.n > nmaxc * rel_max_load:
                                self._plmanv_done_2 = True
                if self._plmanv_done_1 and self._plmanv_done_2:
                    tracking = False
                    dbgval(1, "missile-avoid",
                           (w.time, "%.2f", "time", "s"),
                           (self.name, "%s", "name"))

        if tracking:
            # Compute location of the target at interception,
            # assuming that its acceleration is constant,
            # and that parent points in the exact direction.
            # Compute with higher precision when near enough.
            sfvel = Vec3D()
            sdvelp = speed
            sfacc = Vec3D() # or self.acc()?
            sdaccp = 0.0
            ret = intercept_time(tpos, tvel, tacc,
                                 pos, sfvel, sdvelp, sfacc, sdaccp,
                                 finetime=2.0, epstime=(dt * 0.5), maxiter=5)
            if not ret:
                ret = 0.0, tpos, vdir
            inttime, tpos1, idir = ret

            # Modify intercept according to current state and mode.
            havemod = False
            while not havemod: # mode may switch
                if self._ap_currflt == "intercept":
                    havemod = True
                    adt = dt
                    # Modify intercept to keep sufficiently within boresight.
                    if self._ap_currctl == "local":
                        safeoffbore = self.maxoffbore * 0.8
                        offbore1 = acos(clamp(idir.dot(tdir), -1.0, 1.0))
                        if offbore1 > safeoffbore:
                            a1u = unitv(tpos1 - tpos)
                            ang1 = acos(clamp(a1u.dot(-tdir), -1.0, 1.0))
                            ang2 = pi - ang1 - safeoffbore
                            tdist1c = tdist * (sin(ang1) / sin(ang2))
                            anu = unitv(tdir.cross(idir))
                            q = QuatD()
                            q.setFromAxisAngleRad(safeoffbore, anu)
                            idirc = Vec3D(q.xform(tdir))
                            tpos1c = pos + idirc * tdist1c
                            tpos1 = tpos1c
                elif self._ap_currflt == "transfer":
                    tointtime = 15.0 #!!!
                    if inttime < tointtime:
                        offbore1 = acos(clamp(unitv(tpos - pos).dot(vdir), -1.0, 1.0))
                        safeoffbore = self.maxoffbore * 0.8
                        if offbore1 < safeoffbore:
                            # FIXME: What if no intercept mode?
                            self._ap_currflt = "intercept"
                            if self.seeker in Rocket._seekers_local:
                                self._ap_currctl = "local"
                    if self._ap_currflt == "transfer": # mode not switched
                        havemod = True
                        maxadt = 1.0
                        if inttime < tointtime:
                            adt = clamp((tointtime - inttime) * 0.1, dt, maxadt)
                            # Direct towards intercept.
                            tpos1 = tpos
                        else:
                            # Climb to best altitude, in direction of intercept.
                            adt = maxadt
                            dpos1 = tpos1 - pos
                            tdir1 = unitv(dpos1)
                            #maxlfac = max(maxlfac * 0.2, min(maxlfac, 6.0))
                            maxlfac = min(maxlfac, 12.0)
                            mintrad = speed**2 / (maxlfac * w.absgravacc)
                            tralt = max(self.vmaxalt, tpos[2])
                            daltopt = tralt - alt
                            cpitch = (1.0 - (alt / tralt)**2) * (0.5 * pi)
                            if self._ap_currctl == "local":
                                # If local control in transfer, must keep in bore.
                                safeoffbore = self.maxoffbore * 0.8
                                tpitch = atan(tdir1[2] / tdir1.getXy().length())
                                cpitch = clamp(cpitch,
                                               tpitch - safeoffbore,
                                               tpitch + safeoffbore)
                            tdir1xy = unitv(Vec3D(tdir1[0], tdir1[1], 0.0))
                            dpos1mxy = tdir1xy * (daltopt / tan(cpitch))
                            dpos1m = dpos1mxy + Vec3D(0.0, 0.0, daltopt)
                            tpos1 = pos + unitv(dpos1m) * (mintrad * 10.0)
                elif self._ap_currflt == "inertial":
                    pass
            #print("--rck-ap-state  ctl=%s  flt=%s  tdist=%.0f[m]  alt=%.0f[m]  ppitch=%.1f[deg]  adt=%.3f[s]" %
                #(self._ap_currctl, self._ap_currflt, tdist, alt, degrees(ppitch), adt))
        else:
            tpos1 = pos + vdir * (speed * 1.0)
            adt = None

        # Input path.
        dpos1 = tpos1 - pos
        tdist1 = dpos1.length()
        tdir1 = unitv(dpos1)
        ndir = vdir.cross(tdir1).cross(vdir)
        if ndir.length() > 1e-5:
            ndir.normalize()
            dpos1n = dpos1.dot(ndir) or 1e-10
            maxturntime = 5.0 #!!!
            turndist = min(tdist1, maxspeed * maxturntime)
            trad = turndist**2 / (2 * dpos1n)
            lfac = (speed**2 / trad) / w.absgravacc
            if lfac > maxlfac:
                lfac = maxlfac
                trad = speed**2 / (lfac * w.absgravacc)
        else:
            ndir = vtod(self.quat().getUp())
            trad = 1e6
        if trad < 1e6:
            tang = 2 * asin(clamp(dpos1n / tdist1, -1.0, 1.0))
            path = Arc(trad, tang, Vec3D(), vdir, ndir)
            #print "--hmap1  tdist=%.1f[m]  speed=%.1f[m/s]  trad=%.1f[m]  tang=%.1f[deg]  lfac=%.1f" % (tdist, speed, trad, degrees(tang), lfac)
        else:
            path = Segment(Vec3D(), vdir * 1e5, ndir)
            # print "--hmap2"
        self.path = path

        # # Input path.
        # vdir = unitv(vel)
        # dpos = tpos - pos
        # tdist = dpos.length()
        # tdir = unitv(dpos)
        # ndir = unitv(vdir.cross(tdir).cross(vdir))
        # dposn = dpos.dot(ndir) or 1e-5
        # dpost = dpos.dot(vdir) or 1e-5
        # maxtrad = tdist**2 / (2 * dposn)
        # mrlfac = (speed**2 / maxtrad) / w.absgravacc
        # if mrlfac < maxlfac:
            # lfac1 = clamp((maxlfac * 1e3) / tdist, 2.0, maxlfac)
            # trad = speed**2 / (lfac1 * w.absgravacc)
            # tang = atan(dposn / dpost)
            # tang_p = 2 * tang
            # niter = 0
            # maxiter = 10
            # while abs(tang_p - tang) > 1e-4 and niter < maxiter:
                # tang_p = tang
                # k1 = tan(tang)
                # k2 = sqrt(1.0 + k1**2)
                # tang = atan(((dposn - trad) * k2 + trad) / (dpost * k2 - trad * k1))
                # niter += 1
            # path = Arc(trad, tang, Vec3D(), vdir, ndir)
            # print "--hmap1  maxiter=%d  iter=%d  tdist=%.1f  speed=%.1f  trad=%.1f  tang=%.1f" % (maxiter, niter, tdist, speed, trad, degrees(tang))
        # else:
            # path = Segment(Vec3D(), vdir * 1e5, ndir)
            # print "--hmap2"
        # self.path = path

        # Input speed.
        self.pspeed = maxspeed

        #print "========== rck-ap-end"
        return adt


    @staticmethod
    def check_launch_free (launcher=None):

        return True


    def exec_post_launch (self, launcher=None):

        pass


    def _process_decoys (self, target, toffset, dtime):


        target_dir = unitv(target.pos(refbody=self))
        target_offbore = acos(clamp(target_dir[1], -1.0, 1.0))
        if target_offbore < self.maxoffbore:
            target_fwd = target.quat(refbody=self).getForward()
            target_aspect = acos(clamp(target_dir.dot(target_fwd), -1.0, 1.0))
            target_weight = intl01v((target_aspect / pi)**0.5, 1.0, 0.2)
            resist_mod = target_weight**((1.0 - self.decoyresist)**0.5)
            offset = toffset
        else:
            target_weight = 0.0
            resist_mod = 1.0
            offset = self._effective_offset # last offset

        while True:
            if not self._tracked_decoy:
                num_tested = 0
                for decoy in target.decoys:
                    if decoy.alive and decoy not in self._eliminated_decoys:
                        tracked = False
                        decoy_offbore = self.offbore(decoy)
                        if decoy_offbore < self.maxoffbore:
                            num_tested += 1
                            if randunit() > self.decoyresist * resist_mod:
                                tracked = True
                        if tracked:
                            self._tracked_decoy = decoy
                            break
                        else:
                            self._eliminated_decoys.add(decoy)
            else:
                num_tested = 1

            decoy_reloffb = 0.0
            decoy_effect = 0.0
            if self._tracked_decoy:
                decoy = self._tracked_decoy
                tracked = False
                if decoy.alive:
                    decoy_offbore = self.offbore(decoy)
                    if decoy_offbore < self.maxoffbore:
                        if target_weight and decoy_offbore > target_offbore:
                            decoy_reloffb = (target_offbore / decoy_offbore)**0.5
                        else:
                            decoy_reloffb = 1.0
                        decoy_effect = (1.0 - decoy.decay()) * decoy_reloffb
                        if decoy_effect > self.decoyresist * resist_mod:
                            offset = decoy.pos(refbody=target)
                            tracked = True
                if not tracked:
                    self._tracked_decoy = None
                    self._eliminated_decoys.add(decoy)

            if self._tracked_decoy or num_tested == 0:
                break

        #vf = lambda v, d=3: "(%s)" % ", ".join(("%% .%df" % d) % e for e in v)
        #num_seen = len(self._eliminated_decoys) + int(bool(self._tracked_decoy))
        #num_tracked = int(bool(self._tracked_decoy))
        #target_dist = self.pos(refbody=target, offset=toffset).length()
        #doffset = offset - toffset
        #print ("--procdec  num_seen=%d  target_weight=%.2f  "
               #"decoy_reloffb=%.2f  decoy_effect=%.2f  "
               #"target_dist=%.0f  doffset=%s"
               #% (num_seen, target_weight, decoy_reloffb, decoy_effect,
                  #target_dist, vf(doffset)))

        return offset


    @classmethod
    def launch_limits (cls, attacker, target, offset=None):

        weapon = cls

        apos = attacker.pos()
        pdir = attacker.quat().getForward()
        tpos = target.pos(offset=offset)
        tvel = target.vel()
        tspd = tvel.length()

        # Maximum range for non-manouevring target.
        malt = 0.5 * (apos[2] + tpos[2])
        spds = weapon.limspeeds_st(weapon, malt)
        accs = weapon.limaccs_st(weapon, malt, 0.0)
        fltime = weapon.maxflighttime - 0.5 * (spds[1] / accs[1])
        tvel1 = tvel
        fltime1 = fltime * 0.90 # safety
        rmax = max_intercept_range(tpos, tvel1, apos, spds[1], fltime1)
        # - correct once for bore-keeping (overcorrection)
        tpos1 = tpos + tvel1 * fltime1
        tdir1 = unitv(tpos1 - apos)
        offbore1 = acos(clamp(tdir1.dot(pdir), -1.0, 1.0))
        if offbore1 > weapon.maxoffbore:
            tdist1 = (tpos1 - apos).length()
            dbore1 = offbore1 - weapon.maxoffbore
            tarc1 = (tdist1 / sin(dbore1)) * dbore1
            fltime2 = fltime1 * (tdist1 / tarc1)
            rmax = max_intercept_range(tpos, tvel1, apos, spds[1], fltime2)

        # Maximum range for manouevring target.
        if hasattr(target, "mass"):
            #tminmass = getattr(target, "minmass", target.mass)
            ##tspds = target.limspeeds(mass=tminmass, alt=tpos[2], withab=True)
            #taccs = target.limaccs(mass=tminmass, alt=tpos[2], speed=tspd,
                                   #climbrate=0.0, turnrate=0.0,
                                   #ppitch=radians(-30.0), withab=True)
            tdpos = tpos - apos
            tdist = tdpos.length()
            #fltime1 = min(fltime, tdist / spds[1])
            tspd1 = tspd #+ 0.5 * fltime1 * taccs[1]
            tvel1 = unitv(tdpos) * tspd1
            fltime1 = fltime * 0.75 # safety inc. manoeuvring
            rman = max_intercept_range(tpos, tvel1, apos, spds[1], fltime1)
            # - correct once for bore-keeping (overcorrection)
            tpos1 = tpos + tvel1 * fltime1
            tdir1 = unitv(tpos1 - apos)
            offbore1 = acos(clamp(tdir1.dot(pdir), -1.0, 1.0))
            if offbore1 > weapon.maxoffbore:
                tdist1 = (tpos1 - apos).length()
                dbore1 = offbore1 - weapon.maxoffbore
                tarc1 = (tdist1 / sin(dbore1)) * dbore1
                fltime2 = fltime1 * (tdist1 / tarc1)
                rman1 = max_intercept_range(tpos, tvel1, apos, spds[1], fltime2)
                rman = rman1
        else:
            rman = rmax

        # Minimum range.
        rmin = weapon.minlaunchdist

        return rmin, rman, rmax


class Launcher (object):
    """
    Generic missile launcher.
    """

    def __init__ (self, mtype, parent, points, rate,
                  reloads=0, relrate=0):
        """
        Parameters:
        - mtype (<Rocket>): type of missiles being launched
        - parent (Body): the body which mounts the launcher
        - points ([int*]): indices of loaded parent pylons
        - rate (double): rate of launching in seconds
        - reloads (int): number of reloads to full missile pack;
            if less then zero, then infinite
        - relrate (double): rate of reloading in seconds
        """

        self.mtype = mtype
        self.parent = parent
        self.world = parent.world
        self._pnode = parent.node
        self._full_points = points
        self.rate = rate
        self._relrate = relrate
        self.reloads = reloads

        self.alive = True
        self._wait_prep_time = 0.0
        self._wait_lock_time = 0.0
        self._wait_reload_time = 0.0
        self._target = None
        self._in_boresight = False

        self._store_model_report_addition = None
        self._store_model_report_removal = None
        self.points = []
        self.store_models = []
        self._create_stores()

        need_sens = []
        if mtype.seeker == "sarh":
            need_sens = ["radar"]
        elif mtype.seeker == "tv":
            need_sens = ["tv"]
        elif mtype.seeker == "intv":
            need_sens = ["tv", "radar", "datalink"]
        self._track_need_sens = frozenset(need_sens)

        base.taskMgr.add(self._loop, "launcher-loop")


    def destroy (self):

        if not self.alive:
            return
        self._remove_stores()
        self.alive = False


    def _remove_stores (self):

        for rind in xrange(len(self.points)):
            smodel = self.store_models.pop()
            smodel.removeNode()
            if self.parent.mass is not None:
                self.parent.mass -= self.mtype.mass
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
        assert not self.store_models
        self.points = []
        self.rounds = 0


    def _create_stores (self):

        self._remove_stores()

        shader = make_stores_shader(self.world,
                                    normal=bool(self.mtype.normalmap),
                                    glow=bool(self.mtype.glowmap),
                                    gloss=bool(self.mtype.glossmap))
        self.points = list(self._full_points)
        self.store_models = []
        for pind in self.points:
            ppos, phpr = self.parent.pylons[pind][:2]
            ret = load_model_lod_chain(
                self.world.vfov, self.mtype.modelpath,
                texture=self.mtype.texture, normalmap=self.mtype.normalmap,
                glowmap=self.mtype.glowmap, glossmap=self.mtype.glossmap,
                shadowmap=self.world.shadow_texture,
                scale=self.mtype.modelscale)
            lnode = ret[0]
            lnode.reparentTo(self.parent.node)
            ppos1 = ppos + Point3(0.0, 0.0, -0.5 * self.mtype.diameter)
            lnode.setPos(ppos1 + self.mtype.modeloffset)
            lnode.setHpr(phpr + self.mtype.modelrot)
            lnode.setShader(shader)
            self.store_models.append(lnode)
            if self._store_model_report_addition:
                self._store_model_report_addition(lnode)
            if self.parent.mass is not None:
                self.parent.mass += self.mtype.mass
        self.rounds = len(self.points)


    def set_store_model_report_functions (self, add_func, rem_func):

        self._store_model_report_addition = add_func
        self._store_model_report_removal = rem_func


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        if self.rounds == 0 and self.reloads != 0:
            if self._wait_reload_time > 0:
                self._wait_reload_time -= dt
            else:
                self._create_stores()
                if self.reloads > 0:
                    self.reloads -= 1

        if self._wait_prep_time > 0.0:
            self._wait_prep_time -= dt

        if self._target and not self._target.alive:
            self._target = None

        if self._target and self.mtype.seeker is not None:
            offbore = self.parent.offbore(self._target)
            if offbore > self.mtype.maxoffbore:
                self._in_boresight = False
                self._wait_lock_time = self.mtype.locktime
            else:
                self._in_boresight = True
            if self._wait_lock_time > 0.0:
                self._wait_lock_time -= dt
        else:
            self._in_boresight = True

        return task.cont


    def _execute_launch (self, pinds, target, offset, addchf):

        #print "--mlaunch", target
        missiles = []
        for pind in pinds:
            rind = self.points.index(pind)
            self.points.pop(rind)
            smodel = self.store_models.pop(rind)
            wpos = smodel.getPos(self.world.node)
            whpr = smodel.getHpr(self.world.node)
            smodel.removeNode()
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
            dropvel = None
            missile = self.mtype(world=self.world,
                                 name=("from-%s" % self.parent.name),
                                 side=self.parent.side,
                                 pos=wpos, hpr=whpr,
                                 speed=self.parent.speed(),
                                 dropvel=dropvel,
                                 target=target,
                                 offset=offset)
            missile.initiator = self.parent
            missile.exec_post_launch(self)
            missiles.append(missile)
            if self.world.player and self.parent is self.world.player.ac:
                self.world.player.record_release(missile)
            if addchf:
                ch = addchf(missile)
                self.parent.world.add_action_chaser(ch)
            self._wait_prep_time = self.rate
            self.rounds -= 1
            if self.rounds == 0:
                self._wait_reload_time = self._relrate
            if self.parent.mass is not None:
                self.parent.mass -= self.mtype.mass
        return missiles


    def ready (self, target=None, locktimefac=1.0):
        """
        Check the readiness state of next missile.

        When this function is called for the first time on a new target,
        some time must pass for the missile to obtain the lock.
        After that some more time may need to pass to launch the missile.
        The target must be within the missile boresight the whole time.

        Parameters:
        - target [Body]: a body in the world
        - locktimefac [float]: relative increase in locking time

        Returns:
        - state [string]: "notarget" if there is no target set,
            "norounds" if the launcher is empty,
            "notrack" if the target is not tracked with an appropriate sensor,
            "offbore" if the target is out of boresight,
            "locking" if the target is being locked,
            "locked" if the target is locked,
            "ready" if a missile is ready for launch.
        - points [[int*]]: pylon indices of rounds to be launched
        """

        if target is not self._target:
            self._target = target
            if self.mtype.seeker is not None:
                self._in_boresight = False
                self._wait_lock_time = self.mtype.locktime * locktimefac
            else:
                self._in_boresight = True
                self._wait_lock_time = 0.0

        pinds = [self.points[-1]] if self.points else []

        if not self.mtype.check_launch_free(self):
            return "notfree", pinds
        elif self._target is None and self.mtype.seeker is not None:
            return "notarget", pinds
        elif self.rounds == 0:
            return "norounds", pinds
        elif not self._has_track(target):
            return "notrack", pinds
        elif not self._in_boresight:
            return "offbore", pinds
        elif self._wait_lock_time > 0.0:
            return "locking", pinds
        elif self._wait_prep_time > 0.0:
            return "locked", pinds
        else:
            return "ready", pinds


    def fire (self, target=None, offset=None, addchf=False):
        """
        Launch one missile once ready.

        Parameters:
        - target [Body]: a body in the world
        - offset [Point3]: relative point the missile should hit
        - addchf [(Body)->*Chaser]: function to construct action chaser

        Returns:
        - missiles [[Rocket*]]: the list of fired missiles, if any
        """

        rst, pinds = self.ready(target)
        if rst == "ready":
            #print "--mlaunch-launch-accepted", target
            missiles = self._execute_launch(pinds, target, offset, addchf)
        else:
            missiles = []
        return missiles


    def is_locking (self, body):

        return (self.mtype.seeker is not None and
                body is self._target and
                self._in_boresight and
                self._has_track(self._target))


    def _has_track (self, target):

        if not self._track_need_sens:
            return True

        con_by_body = self.parent.sensorpack.contacts_by_body()
        sens_by_con = self.parent.sensorpack.sensors_by_contact()
        sens = sens_by_con.get(con_by_body.get(target), []) or []
        return bool(self._track_need_sens.intersection(sens))


class SamCarpet (object):

    def __init__ (self, world, mtype, mside, targsides, avgfiretime,
                  skiptime=None, maxrad=None, maxalt=None, rounds=None,
                  carpetpos=None, carpetradius=None):

        self.world = world
        self._mtype = mtype
        self._mside = mside
        self._skiptime = skiptime
        self._maxrad = maxrad
        self._maxalt = maxalt
        self.rounds = rounds
        self._carpetpos = carpetpos
        self._carpetradius = carpetradius

        self._targspecs = {}
        for tsspec in targsides:
            if isinstance(tsspec, tuple):
                side, redprob = tsspec
            else:
                side, redprob = tsspec, 1.0
            self._targspecs[side] = (redprob,)

        self._fireprob = 1.0 / avgfiretime

        if self._maxrad is None:
            maxrange = mtype.maxspeed * mtype.maxflighttime
            self._maxrad = 0.50 * maxrange
        if self._maxalt is None:
            maxrange = mtype.maxspeed * mtype.maxflighttime
            self._maxalt = 0.33 * maxrange

        self._waittime = 0.0

        self.alive = True
        base.taskMgr.add(self._loop, "sam-carpet-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        dt = self.world.dt
        if self._skiptime:
            self._waittime += dt
            if self._waittime < self._skiptime:
                return task.cont
        else:
            self._waittime = dt

        absprob = self._fireprob * self._waittime
        for body in self.world.iter_bodies(family=["plane"]):
            targspec = self._targspecs.get(body.side)
            if targspec is not None:
                bpos = body.pos()
                btalt = self.world.otr_altitude(bpos)
                if (btalt <= self._maxalt and
                    (self._carpetpos is None or self._carpetradius is None or
                     body.dist(self._carpetpos) < self._carpetradius + self._maxrad)):
                    redprob, = targspec
                    absprob1 = absprob * redprob
                    if randunit() < absprob1:
                        if self._carpetpos is None or self._carpetradius is None:
                            brad = uniform(0.5 * self._maxrad, 1.0 * self._maxrad)
                            lpos = bpos
                        else:
                            brad = uniform(0.0, self._carpetradius)
                            lpos = self._carpetpos
                            if isinstance(lpos, VBase2):
                                lpos = Point3(lpos[0], lpos[1], 0.0)
                        bdir = Vec3(uniform(-180.0, 180.0), 0, 0)
                        pos = lpos + hprtovec(bdir) * brad
                        pos[2] = self.world.elevation(pos) + 10.0
                        hpr = hpr_to(pos, bpos)
                        speed = self._mtype.minspeed
                        m = self._mtype(world=self.world,
                                        name="carpetsam",
                                        side=self._mside,
                                        pos=pos, hpr=hpr, speed=speed,
                                        target=body)
                        #print "--carpet-sam  launch-time=%.1f[sec]  target=%s  target-dist=%.0f[m]" % (self.world.time, body.name, (bpos - pos).length())
                        if self.rounds:
                            self.rounds -= 1
                            if self.rounds == 0:
                                self.destroy()
                                return task.done

        if self._skiptime:
            self._waittime -= self._skiptime
        else:
            self._waittime = 0.0

        return task.cont


