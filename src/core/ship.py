# -*- coding: UTF-8 -*-

from math import radians, degrees, sin, cos, atan2

from pandac.PandaModules import Vec3, Vec3D, Point3, Point3D

from src import pycv
from src.core.body import Body
from src.core.curve import Segment, Arc
from src.core.effect import fire_n_smoke_2
from src.core.fire import PolyExplosion
from src.core.misc import AutoProps, rgba, norm_ang_delta, to_navhead
from src.core.misc import sign, clamp, vtod, vtof, ptod, ptof
from src.core.misc import make_text, update_text
from src.core.misc import uniform, randrange
from src.core.misc import fx_uniform
from src.core.sound import Sound3D


class Ship (Body):

    family = "ship"
    species = "generic"
    longdes = None
    shortdes = None

    maxspeed = 15.0
    maxturnrate = radians(2.0)
    maxthracc = 1.0
    maxvdracc = 10.0
    strength = 5000.0
    minhitdmg = 100.0
    maxhitdmg = 2000.0
    rcs = 2.0
    hitboxdata = []
    hitdebris = None
    # hitdebris = AutoProps(
        # #firetex="images/particles/explosion5-1.png",
        # #smoketex="images/particles/smoke1-1.png",
        # debristex=[
            # "images/particles/airplanedebris_1.png",
            # "images/particles/airplanedebris_2.png",
            # "images/particles/airplanedebris_3-1.png",
            # "images/particles/airplanedebris_3-2.png",
            # "images/particles/airplanedebris_3-3.png"])
    hitflash = AutoProps()
    basesink = 0.0
    modelpath = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    shdmodelpath = None
    normalmap = None
    glowmap = rgba(0,0,0, 0.1)
    glossmap = None
    engsoundname = None
    engminvol = 0.0
    engmaxvol = 0.4

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None, damage=None):

        if pos is None:
            pos = Point3()
        if hpr is None:
            hpr = Vec3()
        if sink is None:
            sink = 0.0

        z1 = world.elevation(pos) - self.basesink - sink
        pos1 = Point3(pos[0], pos[1], z1)
        hpr1 = Vec3(hpr[0], 0.0, 0.0)

        if isinstance(self.modelpath, basestring):
            shdmodind = 0
        elif self.modelpath:
            shdmodind = min(len(self.modelpath) - 1, 1)
        else:
            shdmodind = None

        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=(self.strength * 0.1),
            name=name, side=side,
            modeldata=AutoProps(
                path=self.modelpath, shadowpath=self.shdmodelpath,
                texture=texture, normalmap=self.normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            hitboxdata=self.hitboxdata,
            hitlight=AutoProps(),
            hitdebris=self.hitdebris, hitflash=self.hitflash,
            amblit=True, dirlit=True, pntlit=4, fogblend=True,
            obright=True, shdshow=True, shdmodind=shdmodind,
            ltrefl=(self.glossmap is not None),
            pos=pos1, hpr=hpr1)

        self.maxbracc = self.maxspeed * 0.1
        self.sink = sink

        width, length, height = self.bbox
        self.size = (length + width + height) / 3
        self._length = length
        self._size_xy = min(width, length)

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, maxdist=3000, limnum="hum",
                volume=self.engmaxvol, loop=True, fadetime=2.5)
            self.engine_sound.play()
        else:
            self.engine_sound = None

        self.damage = damage or 0.0

        self.wake_trails = []
        self.damage_trails = []

        self.turrets = []
        self.decoys = []

        self._prev_path = None
        self._path_pos = 0.0
        self._throttle = 0.0

        # Control inputs.
        self.zero_inputs()

        # Autopilot constants.
        self._ap_adjperiod = 1.97
        self._ap_adjpfloat = 0.4

        # Autopilot state.
        self.zero_ap()

        # Route settings.
        self._route_current_point = None
        self._route_points = []
        self._route_point_inc = 1
        self._route_patrol = False
        self._route_circle = False

        self._state_info_text = None
        self._wait_time_state_info = 0.0

        base.taskMgr.add(self._loop, "ship-loop-%s" % self.name)


    def destroy (self):

        if not self.alive:
            return
        if self.engine_sound is not None:
            self.engine_sound.stop()
        for turret in self.turrets:
            turret.destroy()
        if self._state_info_text is not None:
            self._state_info_text.removeNode()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return

        if obody.hitforce > self.minhitdmg:
            self.damage += obody.hitforce
        if obody.hitforce > self.maxhitdmg and self.damage < self.strength:
            self.damage = self.strength

        if self.damage >= self.strength:
            self.set_shotdown(10.0)

            self.node.setColor(rgba(32, 32, 32, 1.0))

            d100 = randrange(100)
            if d100 < 66:
                self.explode_minor()

            firescale = fx_uniform(1.0, 1.3)
            fire_n_smoke_2(
                parent=self, store=None,
                sclfact = fx_uniform(0.5, 0.7) * self._size_xy,
                emradtype="fat-y",
                emradfact = fx_uniform(0.7, 0.9) * self._size_xy,
                zvelfact = 20.0,
                fcolor = rgba(255, 255, 255, 1.0),
                fcolorend = rgba(246, 112, 27, 1.0),
                ftcol = 0.5,
                fspacing=0.1,
                flifespan = 0.8,
                fpos = Vec3(0.0, 0.0, 2.0),
                fdelay = fx_uniform(0.1, 3.0),
                spos = Vec3(0.0, 0.0, 2.0),
                stcol = 0.4,
                slifespan = 4.0)

            self._ap_active = True
            self._ap_pause = 0.0


    def explode (self, destroy=True, offset=None):

        if not self.alive:
            return

        exp = PolyExplosion(
            world=self.world, pos=self.pos(offset=offset),
            firepart=3, smokepart=3,
            sizefac=6.0, timefac=1.0, amplfac=1.6,
            smgray=pycv(py=(35,50), c=(220, 255)))
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()


    def explode_minor (self, offset=None):

        exp = PolyExplosion(
            world=self.world, pos=self.pos(offset=offset),
            sizefac=1.2, timefac=0.4, amplfac=0.6,
            smgray=pycv(py=(60,90), c=(220, 255)), smred=0)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()


    def zero_inputs (self):

        self.path = None
        self.pspeed = None


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        # Set engine sound volume based on throttle.
        if self.engine_sound is not None:
            sfac = self._throttle
            engvol = self.engminvol + sfac * (self.engmaxvol - self.engminvol)
            self.engine_sound.set_volume(engvol)

        # Apply autopilot.
        self._ap_pause -= dt
        if self._ap_active and self._ap_pause <= 0.0:
            if not self.controlout:
                minwait = self._ap_adjperiod - self._ap_adjpfloat
                maxwait = self._ap_adjperiod + self._ap_adjpfloat
                adjperiod1 = uniform(minwait, maxwait)
                if self._ap_target:
                    if self._ap_target.alive and not self._ap_target.shotdown:
                        pass
                        #self._ap_input_attack(self._ap_pause)
                    else:
                        self.set_ap(speed=0.0, turnrate=0.0)
                else:
                    self._ap_pause = adjperiod1
                    self._ap_input_nav(self._ap_pause)
            else:
                self._ap_pause = 0.0
                self._ap_input_shotdown(dt)

        if self._state_info_text is not None:
            self._update_state_info(dt)

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        if dt == 0.0:
            return

        # FIXME: Mostly taken from vehicle, removing slope and friction.
        # Certainly can be further simplified.

        pos = ptod(self.pos())
        hpr = vtod(self.hpr())

        zdir = Vec3D(0, 0, 1)
        head = radians(hpr[0])
        hdir = Vec3D(-sin(head), cos(head), 0.0)

        if self._prev_path is not self.path: # must come before next check
            self._prev_path = self.path
            self._path_pos = 0.0
        if self.path is None or self.path.length() < self._path_pos:
            if self.path is not None:
                ptdir = self.path.tangent(self.path.length())
            else:
                ptdir = hdir
            self.path = Segment(Vec3D(), ptdir * 1e5, zdir)
            self._prev_path = self.path
            self._path_pos = 0.0

        speed = self.speed()
        turnrate = self.turnrate()

        if self.pspeed is None:
            self.pspeed = speed

        optspeed, maxspeed = self.limspeeds()
        self.pspeed = clamp(self.pspeed, 0.0, maxspeed)
        ret = self.limaccs(speed=speed, turnrate=turnrate)
        minacc, maxacc, maxaccv0 = ret
        dspeed = self.pspeed - speed
        if dspeed >= 0.0:
            tacc = min(dspeed * 0.5, maxacc)
        else:
            tacc = max(dspeed * 20.0, minacc)

        s = self._path_pos
        dpg = self.path.point(s)
        tvelg = speed
        taccg = tacc
        s1 = s + tvelg * dt + taccg * (0.5 * dt**2)
        dp1g = self.path.point(s1)
        tvel1g = tvelg + taccg * dt
        t1g = self.path.tangent(s1)
        vel1g = t1g * tvel1g
        dposg = dp1g - dpg
        dpos = dposg
        self._path_pos = s1

        head1 = atan2(-t1g[0], t1g[1])
        hdir1 = Vec3D(-sin(head1), cos(head1), 0.0)
        dhpr = Vec3D(degrees(head1 - head), 0, 0)

        pos1 = pos + dpos
        hpr1 = hpr + dhpr

        # Force to surface.
        if dpos.lengthSquared() > 0.0:
            z1 = self.world.elevation(pos1) - self.basesink - self.sink
            pos1 = Point3D(pos1[0], pos1[1], z1)
        else:
            pos1 = pos

        self.node.setPos(ptof(pos1))
        self.node.setHpr(vtof(hpr1))

        vel = hdir1 * tvel1g
        n1g = self.path.normal(s1)
        r1g = self.path.radius(s1)
        acc = hdir1 * taccg + n1g * (tvel1g**2 / r1g)
        self._prev_vel = Vec3(self._vel) # needed in base class
        self._vel = vtof(vel) # needed in base class
        self._acc = vtof(acc) # needed in base class

        # Derive throttle level, needed for effects.
        self._throttle = 1.0 - maxacc / (maxaccv0 or 1e-5)
        self._throttle = clamp(self._throttle, 0.0, 1.0)


    def limspeeds (self):

        maxspeed = self.maxspeed

        optspeed = 0.7 * maxspeed #!!!

        return optspeed, maxspeed


    def limturnrates (self, speed=None):

        if speed is None:
            speed = self.speed()

        # FIXME: Mostly taken from vehicle, analyze better.
        optspeed, maxspeed = self.limspeeds()
        maxturnspeed = maxspeed * 0.2
        zeroturnspeed = max(1.2 * maxspeed, 2 * maxturnspeed)
        if speed <= zeroturnspeed:
            if speed < maxturnspeed:
                sfac = speed / maxturnspeed
            else:
                sfac = 1.0 - (speed - maxturnspeed) / (zeroturnspeed - maxturnspeed)
            maxturnrate = self.maxturnrate * sfac
        else:
            maxturnrate = 0.0

        return maxturnrate


    def limaccs (self, speed=None, turnrate=None):

        if speed is None:
            speed = self.speed()
        if turnrate is None:
            turnrate = self.turnrate()

        maxthracc = self.maxthracc
        maxvdracc = self.maxvdracc

        # Speed influence.
        optspeed, maxspeed = self.limspeeds()
        if speed < maxspeed and maxspeed > 0.0:
            sfac = speed / maxspeed
            maxacc = maxthracc * (1.0 - sfac)
        else:
            maxacc = 0.0
        minacc = -self.maxbracc
        maxaccv0 = maxthracc

        # Turn rate influence.
        maxturnrate = self.limturnrates(speed=speed)
        if maxacc > 0.0:
            maxturnrate_mod = maxturnrate
            # Bound max turn rate from below,
            # so that the following correction does not explode.
            minmaxturnrate = radians(0.2)
            if maxturnrate_mod < minmaxturnrate:
                maxturnrate_mod = minmaxturnrate
            # Reduce maxacc to zero when max turn rate reached.
            tdacc = -maxacc * (abs(turnrate) / maxturnrate_mod)
        else:
            # Add some more arbitrary reduction to acceleration.
            trfac = 2.0
            tdacc = -maxvdracc * abs(turnrate) * trfac
        minacc += tdacc
        maxacc += tdacc

        return minacc, maxacc, maxaccv0


    def set_route (self, points, patrol=False, circle=False):

        self._route_points = points
        self._route_patrol = patrol
        self._route_circle = circle
        self._route_current_point = 0
        self._route_point_inc = 1


    def set_ap (self,
                speed=None, turnrate=None, heading=None, point=None,
                enroute=False, target=None):

        if self.controlout:
            return

        self._ap_speed = speed
        self._ap_turnrate = turnrate
        self._ap_heading = heading
        self._ap_point = point
        self._ap_target = target
        self._ap_enroute = enroute

        self._ap_active = True
        self._ap_pause = 0.0


    def zero_ap (self):

        if self.controlout:
            return

        self.set_ap()

        self._ap_active = False


    def _ap_input_nav (self, adt):

        w = self.world

        #print "========== ap-ship-nav-start (world-time=%.2f)" % (w.time)

        # FIXME: Mostly taken from vehicle, removing slope and friction.
        # Probably can be further simplified.

        tspeed = self._ap_speed
        tturnrate = self._ap_turnrate
        thead = self._ap_heading
        tpoint = self._ap_point
        tenroute = self._ap_enroute

        if tturnrate is not None:
            tturnrate = radians(tturnrate)
        if thead is not None:
            thead = radians(thead)

        pos = self.pos()
        posg = Point3D(pos[0], pos[1], 0.0)
        zdir = Point3D(0, 0, 1)
        hpr = self.hpr()
        head = radians(hpr[0])
        hdir = Vec3D(-sin(head), cos(head), 0.0)
        vel = vtod(self.vel())
        speed = vel.length()
        turnrate = self.turnrate()
        optspeed, maxspeed = self.limspeeds()
        maxturnrate = self.limturnrates(speed=speed)

        # Correct targets for route target.
        break_on_tpoint = True
        if tenroute:
            if self._route_current_point is not None:
                rpos = self._route_points[self._route_current_point]
                rposg = Point3D(rpos[0], rpos[1], 0.0)
                rptdist = (rposg - posg).length()
                if rptdist < 2.0 * self._length:
                    # Select next point.
                    np = self._route_current_point + self._route_point_inc
                    npts = len(self._route_points)
                    if not (0 <= np < npts):
                        if self._route_patrol:
                            if self._route_circle:
                                if np < 0:
                                    np = npts - 1
                                else:
                                    np = 0
                            else:
                                self._route_point_inc *= -1
                                np += 2 * self._route_point_inc
                        else:
                            np = None
                    # If next point is not final, cancel breaking at it.
                    if np is not None:
                        npp = np + self._route_point_inc
                        if self._route_patrol or 0 <= npp < npts:
                            break_on_tpoint = False
                    self._route_current_point = np
                    #print "--ship-route-next-point", self.name, np, self._route_points[np]
                else:
                    tpoint = rpos
                    thead = None
            else:
                # No route, stop.
                tpoint = None
                tspeed = 0.0
                tturnrate = 0.0
                thead = head

        # Correct targets for point target.
        if tpoint is not None:
            tpointg = Point3D(tpoint[0], tpoint[1], 0.0)
            # Set target heading based on given point, ignoring any given.
            dpos = vtod(tpointg) - posg
            thead = atan2(-dpos.getX(), dpos.getY())
            tturnrate = None
            ptdist = dpos.length()
            if break_on_tpoint and ptdist < 1.0 * self._length:
                # Arrived, stop.
                tpoint = None
                tspeed = 0.0
                tturnrate = 0.0
                thead = head

        # Determine updated speed.
        if tpoint is not None:
            speed1 = None
            if break_on_tpoint:
                # Compute stopping distance with a bit smaller deceleration
                # than actual; don't break like mad.
                ret = self.limaccs(speed=speed, turnrate=turnrate)
                minacc, maxacc, maxaccv0 = ret
                bracc = minacc * 0.5
                brtime = speed / -bracc
                brdist = speed * brtime + bracc * (0.5 * brtime**2)
                if brdist > ptdist:
                    dcacc = bracc * 1.2
                    speed1 = speed + dcacc * adt
            if speed1 is None:
                if tspeed is not None:
                    speed1 = tspeed
                else:
                    speed1 = optspeed
        elif tspeed is not None:
            speed1 = tspeed
        else:
            speed1 = speed

        # Determine updated turn rate.
        if tturnrate is not None:
            turnrate1 = tturnrate
        elif thead is not None:
            atime = 2.0 # !!!
            dhead = norm_ang_delta(head, thead)
            cmturnrate = maxturnrate
            if speed < speed1 and speed1 > 0.5 * optspeed:
                 cmturnrate *= (speed / speed1)
            turnrate1 = clamp(dhead / atime, -cmturnrate, cmturnrate)
        else:
            turnrate1 = 0.0

        # Input path.
        head1 = thead if thead is not None else head
        rad01 = abs(speed / turnrate1) if abs(turnrate1) > 1e-5 else 1e30
        dhead = norm_ang_delta(head, head1)
        if abs(dhead) > 1e-6:
            etime = adt + 0.5
            rad01b = abs(speed * etime / dhead)
            rad01 = max(rad01, rad01b)
        infrad = 1e6
        indhead = (rad01 < infrad and abs(dhead) > 1e-6)
        if indhead:
            rdir = zdir.cross(hdir) * sign(dhead)
            path1 = Arc(rad01, abs(dhead), Vec3D(), hdir, rdir)
        else:
            path1 = Segment(Vec3D(), hdir * 1e5, zdir)
        self.path = path1

        # Input speed.
        self.pspeed = speed1

        # Unused inputs.
        pass


    def _ap_input_shotdown (self, adt):

        self.pspeed = 0.0


    def show_state_info (self, pos, align="l", anchor="tl"):

        if self._state_info_text is None:
            self._state_info_text = make_text(
                text="", width=1.0, size=10, align=align, anchor=anchor,
                shcolor=rgba(0, 0, 0, 1), parent=self.world.node2d)
        self._state_info_text.setPos(pos)
        self._state_info_text.show()


    def hide_state_info (self):

        if self._state_info_text is not None:
            self._state_info_text.hide()


    def _update_state_info (self, dt):

        if self._state_info_text.isHidden():
            return
        if self._wait_time_state_info > 0.0:
            self._wait_time_state_info -= dt
            return
        self._wait_time_state_info = fx_uniform(1.0, 2.0)

        d = degrees

        ls = []
        ls.append("name: %s" % self.name)
        pos = self.pos()
        ls.append("position: x=%.1f y=%.1f z=%.1f [m]" % tuple(pos))
        hpr = self.hpr()
        ls.append("heading: % .1f [deg]" % to_navhead(hpr[0]))
        speed = self.speed()
        optspeed, maxspeed = self.limspeeds()
        ls.append("speed: %.1f (%.1f/%.1f) [m/s]" %
                  (speed, optspeed, maxspeed))
        turnrate = self.turnrate()
        maxturnrate = self.limturnrates()
        ls.append("turn-rate: % .1f (% .1f) [deg/s]"
                  % (d(turnrate), d(maxturnrate)))
        facc = self.acc(self)[1]
        minacc, maxacc, maxaccv0 = self.limaccs()
        ls.append("path-acceleration: % .1f (% .1f/% .1f) [m/s^2]"
                  % (facc, minacc, maxacc))
        text = "\n".join(ls)

        update_text(self._state_info_text, text=text)


