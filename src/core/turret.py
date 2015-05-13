# -*- coding: UTF-8 -*-

from math import radians, degrees, tan, acos, atan2

from pandac.PandaModules import Vec3, Vec3D, Point3, Point3D, Quat
from pandac.PandaModules import NodePath

from src.core.body import Body
from src.core.misc import AutoProps, intercept_time, norm_ang_delta
from src.core.misc import sign, unitv, clamp, pclamp, hprtovec, intl01vr
from src.core.misc import vtod, ptod, vtof
from src.core.sensor import SIZEREF, TransportVisual, Radar, Comm


class Turret (Body):
    """
    Generic cannon turret.
    """

    family = "turret"
    species = "G/TUR"
    turnrate = radians(90.0)
    elevrate = radians(60.0)
    radarrange = 5000.0
    radarangle = (radians(75.0), radians(75.0), radians(180.0))
    shellspread = None # ((offbore0, spread0), (offbore1, spread1))
    modelpath = None
    modelscale = None
    modeloffset = None
    modelrot = None
    shdmodelpath = None
    texture = None
    normalmap = None
    glowmap = None
    glossmap = None

    def __init__ (self, world, name, side,
                  parent, pos, hpr,
                  hcenter, harc, pcenter, parc,
                  storepos=None, storespeed=1.0, storedecof=None):

        self.hitforce = 0.0

        # NOTE: Must not set initial pos and hpr here,
        # in order not to mess up model repositioning below.

        if (len(self.modelpath) == 2 and
            isinstance(self.modelpath[0], NodePath) and
            isinstance(self.modelpath[1], basestring)):
            shdmodind = 0
        elif isinstance(self.modelpath, basestring):
            shdmodind = 0
        elif self.modelpath:
            shdmodind = min(len(self.modelpath) - 1, 1)
        else:
            shdmodind = None

        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=self.hitforce,
            modeldata=AutoProps(
                path=self.modelpath, shadowpath=self.shdmodelpath,
                texture=self.texture, normalmap=self.normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            sensordata=AutoProps(
                scanperiod=2.0,
                relspfluct=0.1,
                maxtracked=1),
            amblit=True, dirlit=True, pntlit=2, fogblend=True,
            ltrefl=(self.glossmap is not None),
            shdshow=True, shdmodind=shdmodind,
            name=name, side=side,
            pos=pos, hpr=hpr, vel=Vec3(),
            parent=parent)

        # Get azimuth- and elevation-moving parts.
        self._rotparts = []
        for model in self.models:
            azimnd = model.find("**/*turret_azim")
            elevnd = model.find("**/*turret_elev")
            if not azimnd.isEmpty() and not elevnd.isEmpty():
                self._rotparts.append((azimnd, elevnd))

        # Position virtual referent aiming node model within the parent
        # such that its center is a point at z-axis of azimut part's center
        # nearest to elevation part's center.
        # Needed for accurate aiming.
        if self._rotparts:
            azimnd, elevnd = self._rotparts[0] # referent parts
            azim_elev_pos = elevnd.getPos(azimnd)
            ez = Vec3(0.0, 0.0, 1.0)
            azim_znear_pos = ez * azim_elev_pos.dot(ez)
            apos = self.node.getRelativePoint(azimnd, azim_znear_pos)
            self._cannon_node = elevnd
        else:
            apos = Point3()
            self._cannon_node = self.node
        self._aimref_base = self.node.attachNewNode("aim-base")
        self._aimref_base.setPos(apos)
        self._aimref_sviw = self._aimref_base.attachNewNode("aim-swivel")

        self._pos = self.node.getPos()
        if storepos is None:
            self._stored = False
            self._storepos = None
            pos0 = self._pos
        else:
            self._stored = True
            self._storepos = storepos
            self._storespeed = storespeed
            self._storedecof = storedecof
            pos0 = self._storepos
        hpr0 = self.node.getHpr()
        if hcenter is None:
            hcenter = hpr0[0]
        if pcenter is None:
            pcenter = hpr0[1]
        hpr0 = Vec3(hcenter, pcenter, 0.0)
        self._update_pos_hpr(pos0, hpr0)

        self.parent = parent
        self.hcenter = hcenter
        self.harc = harc
        self.pcenter = pcenter
        self.parc = parc

        self.cannons = []
        self._stop_firing = False

        self.launchers = []

        self.decoys = []

        self.target = None
        self._prev_target = None
        self._targsel_wait = 0.0
        self._targsel_period = 0.63

        self._ap_target = None
        self._ap_targprio = 0

        self._aa_families = []
        self._aa_target = None
        self._aa_targprio = 0
        self._aa_wait = 0.0
        self._aa_period = 1.11

        self.mass = 0.0

        self._wait_burst = 0.0
        self._target_intdir = None
        self._target_intpos_rp = None
        self._prev_mass = self.mass

        self._trksmpl_period = 0.8

        # Sensors.
        if True:
            self.visualangle = (radians(90.0), radians(90.0), radians(180.0))
            da, ua, ta = self.visualangle
            airvis = TransportVisual(parent=self, subnode=self._aimref_sviw,
                                     dfamilies=["plane", "heli"],
                                     downangle=da, upangle=ua, topangle=ta,
                                     refsizetype=SIZEREF.PROJAREA,
                                     relsight=1.0, considersun=True)
            self.sensorpack.add(airvis, "visual-air")
        if self.radarrange:
            da, ua, ta = self.radarangle
            radar = Radar(parent=self, subnode=self._aimref_sviw,
                          dfamilies=["plane", "heli"],
                          refrange=self.radarrange,
                          downangle=da, upangle=ua, topangle=ta)
            self.sensorpack.add(radar, "radar")
        if True:
            comm = Comm(parent=self,
                        dfamilies=["plane", "heli", "vehicle", "ship"])
            self.sensorpack.add(comm, "comm")
        self.sensorpack.start_scanning()

        # Jamming constants and state.
        self.jammed = False

        self.shell_spread_angle = 0.0

        self.alive = True
        base.taskMgr.add(self._loop, "turret-loop-%s" % self.name)


    def destroy (self):

        if not self.alive:
            return
        for cannon in self.cannons:
            cannon.destroy()
        Body.destroy(self)


    def add_cannon (self, cannon):

        cnpos = self._cannon_node.getPos(self.node)
        mpos = cannon.mpos - cnpos
        if cannon.mltpos is not None:
            mltpos = cannon.mltpos - cnpos
        else:
            mltpos = None
        cannon.update(mpos=mpos, mltpos=mltpos, subnode=self._cannon_node)
        self.cannons.append(cannon)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos, silent=True)
        if inert:
            return True

        #self.destroy()

        return False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done

        dt = self.world.dt

        if self._wait_burst > 0.0:
            self._wait_burst -= dt

        self._target_intdir = None

        if self._storepos is not None:
            ready = (self.node.getPos() - self._pos).length() < 0.1
        else:
            ready = True

        # Update shell spread.
        if self.shellspread:
            (offb0, spda0), (offb1, spda1) = self.shellspread
            fdir = self._aimref_sviw.getQuat().getForward()
            rdir = hprtovec(Vec3(self.hcenter, self.pcenter, 0.0))
            offb = degrees(acos(clamp(fdir.dot(rdir), -1.0, 1.0)))
            spda = intl01vr(offb, offb0, offb1, spda0, spda1)
            self.shell_spread_angle = spda

        # Cancel stale targets.
        if self._ap_target:
            if not self._ap_target.alive or self._ap_target.shotdown:
                self._ap_target = None
        if self._aa_target:
            if not self._aa_target.alive or self._aa_target.shotdown:
                self._aa_target = None

        refcannon = self.cannons[0]

        # Choose target for auto attack.
        self._aa_wait -= dt
        if self._aa_wait <= 0.0:
            self._aa_wait = self._aa_period
            self._choose_auto_attack_target()

        # Select between autopilot and autoattack targets.
        if self._ap_target and self._aa_target:
            self._targsel_wait -= dt
            if self._targsel_wait <= 0.0 or not self.target:
                self._targsel_wait = self._targsel_period
                tdist_ap = self.dist(self._ap_target)
                tdist_aa = self.dist(self._aa_target)
                if (tdist_aa < refcannon.effrange and
                    (tdist_ap > refcannon.effrange or
                     self._aa_targprio > self._ap_targprio)):
                    self.target = self._aa_target
                else:
                    self.target = self._ap_target
        elif self._ap_target:
            self.target = self._ap_target
        elif self._aa_target:
            self.target = self._aa_target
        else:
            self.target = None
        if self.target is not self._prev_target:
            self._prev_target = self.target
            self._stop_firing = True
            self._trksmpl_time = 0.0
            self._trksmpl_pos = None
            self._trksmpl_vel = None
            self._trksmpl_acc = None

        # Track target.
        if (ready and self.target and self.target.alive and
            not self.target.shotdown):
            tdist = self.dist(self.target)
            if tdist <= refcannon.effrange * 1.5:
                # Compute position of target at intercept.
                vel = self.vel()
                spos = self._aimref_sviw.getPos(self.world.node)
                targoff = None
                if self.target is self._ap_target:
                    targoff = self._ap_targoff
                self._trksmpl_time += dt
                if self._trksmpl_time >= self._trksmpl_period:
                    cdt = self._trksmpl_time
                    self._trksmpl_time -= self._trksmpl_period
                    opos = self.target.pos(offset=targoff)
                    ovel = self.target.vel()
                    if self._trksmpl_pos is not None:
                        self._trksmpl_acc = (ovel - self._trksmpl_vel) / cdt
                    self._trksmpl_pos = opos
                    self._trksmpl_vel = ovel
                if self._trksmpl_pos is not None:
                    cdt = self._trksmpl_time
                    ovel = self._trksmpl_vel
                    opos = self._trksmpl_pos + ovel * cdt
                    if self._trksmpl_acc is not None:
                        opos += self._trksmpl_acc * (0.5 * cdt**2)
                        oacc = self._trksmpl_acc
                    else:
                        oacc = Vec3()
                    sfvel, sdvelp, sfacc, sdaccp, setime = refcannon.launch_dynamics()
                    ret = intercept_time(ptod(opos), vtod(ovel), vtod(oacc),
                                         ptod(spos), vtod(sfvel), sdvelp,
                                         vtod(sfacc), sdaccp,
                                         finetime=setime, epstime=dt,
                                         maxiter=10)
                    if ret is not None:
                        odir1 = vtof(ret[2])
                        check_fire = True
                    else:
                        odir1 = unitv(opos - spos)
                        check_fire = False
                else:
                    odir1 = None
                    check_fire = False
                self._target_intdir = odir1

                # Fire on target if possible.
                if check_fire and self._wait_burst <= 0.0 and tdist < refcannon.effrange:
                    sdir = self._aimref_sviw.getQuat(self.world.node).getForward()
                    offbore = acos(clamp(sdir.dot(odir1), -1.0, 1.0))
                    if abs(tdist * tan(offbore)) < 4.0:
                        ftime = 0.0
                        for cannon in self.cannons:
                            ftime1 = cannon.fire(rounds=-2)
                            ftime = max(ftime, ftime1)
                        self._wait_burst = ftime + 1.0
            else:
                self._stop_firing = True

        if self._stop_firing:
            for cannon in self.cannons:
                cannon.fire(rounds=0)
            self._stop_firing = False

        if self._prev_mass != self.mass:
            if self.parent.mass is not None:
                dmass = self.mass - self._prev_mass
                self.parent.mass += dmass
            self._prev_mass = self.mass

        return task.cont


    def set_ap (self, stored=True, target=None, targoff=None, targprio=0):

        self._stored = stored
        self._ap_target = target
        self._ap_targoff = targoff
        self._ap_targprio = targprio

        # This would be automatically assigned later,
        # but do it here in order to be able to check for
        # "ac.target is something" right after this call.
        self.target = self._ap_target

        # Override storage.
        if self.target:
            self._stored = False


    def set_auto_attack (self, families=[]):

        self._aa_families = []
        for i, family in enumerate(families):
            if isinstance(family, tuple):
                family, prio = family
            else:
                prio = -(i + 1) # less then default targprio in set_ap()
            self._aa_families.append((family, prio))

        # Override storage.
        if self._aa_families:
            self._stored = False


    def _choose_auto_attack_target (self):

        if self._aa_families:
            refcannon = self.cannons[0]
            allied_sides = self.world.get_allied_sides(self.side)
            tbody, prio = None, 0
            for family, prio in self._aa_families:
                bodysel = []
                for body in self.world.iter_bodies(family):
                    if body.side not in allied_sides and not body.shotdown:
                        bdist = self.dist(body)
                        if bdist < refcannon.effrange * 1.5:
                            bodysel.append((body, bdist))
                if bodysel:
                    tbody = sorted(bodysel, key=lambda x: x[1])[0][0]
                    break
            self._aa_target = tbody
            self._aa_targprio = prio
        else:
            self._aa_target = None
            self._aa_targprio = 0


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        # Store or pop the turret.
        pos = self.node.getPos()
        pos1 = pos
        vel = Vec3()
        if self._storepos is not None:
            speed = self._storespeed
            tpos = self._storepos if self._stored else self._pos
            dpos = tpos - pos
            tdist = dpos.length()
            if tdist > 1e-3:
                if speed * dt > tdist:
                    speed = tdist / dt
                tdir = unitv(dpos)
                vel = tdir * speed
                pos1 = pos + vel * dt
                stfac = ((pos1 - self._storepos).length() /
                         (self._pos - self._storepos).length())
                stfac = clamp(stfac, 0.0, 1.0)
                if self._storedecof:
                    self._storedecof(stfac)

        # Rotate towards the target intercept direction.
        idir = self._target_intdir
        quat = self._aimref_sviw.getQuat() # to self._aimref_base
        if idir is not None:
            tdir = self._aimref_base.getRelativeVector(self.world.node, idir)
        else:
            tdir = hprtovec(Vec3(self.hcenter, self.pcenter, 0.0))
        fdir = quat.getForward()
        zdir = Vec3(0, 0, 1)
        rdir = unitv(fdir.cross(zdir))

        cturn = atan2(tdir[1], -tdir[0])
        tturn = atan2(fdir[1], -fdir[0])
        dturn = norm_ang_delta(cturn, tturn)

        celev = atan2(fdir[2], fdir.getXy().length())
        telev = atan2(tdir[2], tdir.getXy().length())
        delev = norm_ang_delta(celev, telev)

        turnrate = self.turnrate
        if turnrate * dt > abs(dturn):
            turnrate = abs(dturn) / dt
        turnrate *= sign(dturn)

        elevrate = self.elevrate
        if elevrate * dt > abs(delev):
            elevrate = abs(delev) / dt
        elevrate *= sign(delev)

        angvel = zdir * turnrate + rdir * elevrate

        # Compute new rotation unconstrained.
        angspeed = angvel.length()
        if angspeed > 1e-5:
            adir = unitv(angvel)
            dquat = Quat()
            dquat.setFromAxisAngleRad(angspeed * dt, adir)
            quat1 = quat * dquat
            # Limit to movement arc.
            h, p, r = quat1.getHpr()
            if isinstance(self.harc, tuple):
                harc1, harc2 = self.harc
            else:
                harc1 = self.hcenter - 0.5 * self.harc
                harc2 = self.hcenter + 0.5 * self.harc
            h = pclamp(h, harc1, harc2, -180, 180)
            if isinstance(self.parc, tuple):
                parc1, parc2 = self.parc
            else:
                parc1 = self.pcenter - 0.5 * self.parc
                parc2 = self.pcenter + 0.5 * self.parc
            p = pclamp(p, parc1, parc2, -90, 90, mirror=True)
            hpr1 = Vec3(h, p, r)
        else:
            hpr1 = quat.getHpr()

        self._update_pos_hpr(pos1, hpr1)

        # Needed in base class.
        self._prev_vel = self._vel
        self._vel = vel
        self._acc = (self._vel - self._prev_vel) / dt
        self._prev_angvel = self._angvel
        self._angvel = angvel
        self._angacc = (self._angvel - self._prev_angvel) / dt


    def _update_pos_hpr (self, pos, hpr):

        self.node.setPos(pos)

        self._aimref_sviw.setHpr(hpr)
        for azimnd, elevnd in self._rotparts:
            azimnd.setHpr(hpr[0], 0.0, 0.0)
            elevnd.setHpr(0.0, hpr[1], 0.0)


class CustomTurret (Turret):

    species = "custom"

    def __init__ (self, world, name, side,
                  turnrate, elevrate,
                  parent, hcenter, harc, pcenter, parc,
                  pos=None, hpr=None,
                  storepos=None, storespeed=1.0, storedecof=None,
                  shellspread=None,
                  modelpath=None, modelscale=None, modeloffset=None, modelrot=None,
                  texture=None, normalmap=None, glowmap=None, glossmap=None):

        self.turnrate = turnrate
        self.elevrate = elevrate
        self.shellspread = shellspread
        self.modelpath = modelpath
        self.modelscale = modelscale
        self.modeloffset = modeloffset
        self.modelrot = modelrot
        self.texture = texture
        self.normalmap = normalmap
        self.glowmap = glowmap
        self.glossmap = glossmap

        Turret.__init__(self,
            world=world, name=name, side=side,
            parent=parent, pos=pos, hpr=hpr,
            storepos=storepos, storespeed=storespeed, storedecof=storedecof,
            hcenter=hcenter, harc=harc, pcenter=pcenter, parc=parc)


