# -*- coding: UTF-8 -*-

from sys import float_info
from math import degrees, radians, pi, exp, atan

from pandac.PandaModules import Vec3, Point3
from pandac.PandaModules import ColorBlendAttrib

from src import internal_path, join_path
from src.core.body import Body, EnhancedVisual
from src.core.fire import MuzzleFlash, Splash
from src.core.misc import AutoProps, SimpleProps, rgba, unitv, vtod
from src.core.misc import hprtovec, vectohpr
from src.core.misc import get_cache_key_section
from src.core.misc import read_cache_object, write_cache_object
from src.core.misc import solve_linsys_3
from src.core.misc import intl01v
from src.core.misc import uniform, randunit
from src.core.misc import dbgval
from src.core.sound import Sound3D, Sound2D
from src.core.transl import *


class Shell (Body):

    family = "shell"
    species = "Gmm"
    caliber = 0.030
    dragcoeff = 0.30
    mass = 0.80
    pmassfac = 0.4
    hitforce = 1.4

    _hbxlen = 10.0
    _hbxrad = 0.5
    #_hitboxdata = [(Point3(0.0, 0.0, 0.0), _hbxrad)]
    #_hitboxdata = [(Point3(0.0, -0.5 * _hbxlen, 0.0), Point3(0.0, 0.5 * _hbxlen, 0.0))]
    _hitboxdata = [(Point3(_hbxrad, -0.5 * _hbxlen, -_hbxrad), Point3(_hbxrad, 0.5 * _hbxlen, _hbxrad)),
                   (Point3(-_hbxrad, -0.5 * _hbxlen, _hbxrad), Point3(-_hbxrad, 0.5 * _hbxlen, -_hbxrad))]
    #_hitboxdata = [(Point3(_hbxrad, -0.5 * _hbxlen, 0.0), Point3(_hbxrad, 0.5 * _hbxlen, 0.0)),
                   #(Point3(-_hbxrad, -0.5 * _hbxlen, 0.0), Point3(-_hbxrad, 0.5 * _hbxlen, 0.0)),
                   #(Point3(0.0, -0.5 * _hbxlen, _hbxrad), Point3(0.0, 0.5 * _hbxlen, _hbxrad)),
                   #(Point3(0.0, -0.5 * _hbxlen, -_hbxrad), Point3(0.0, 0.5 * _hbxlen, -_hbxrad))]
    #_hitboxdata = [(Point3(0.0, 0.0, 0.0), _hbxrad, 0.5 * _hbxlen, _hbxrad)]
    _refcaliber = 0.030
    #_refvscale = Vec3(0.05, 10.0, 0.05) #OLD
    _refvscale = Vec3(0.12, 7.0, 0.12)
    _refvzoomfac = 10.0

    _monpath = False

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=None):

        self.world = world

        self._visible = visible
        if visible:
            scale = self._refvscale * (self.caliber / self._refcaliber)
            modeldata = AutoProps(
                path="models/weapons/fx_shell.egg",
                texture="models/weapons/fx_shell_tex.png",
                # glowmap="models/weapons/fx_shell_gw.png",
                scale=scale,
                nobbox=True)
        else:
            modeldata = None
        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=self.hitforce,
            name="", side="",
            mass=self.mass, passhitfx=True,
            modeldata=modeldata,
            hitboxdata=self._hitboxdata, hitinto=False,
            amblit=False, dirlit=False, pntlit=0, fogblend=False,
            ltrefl=False,
            pos=pos, hpr=hpr, vel=vel)
        if visible:
            self.modelnode.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))

        self._pos = pos
        self._vel = vel
        self._acc = acc

        self._effrange = effrange
        self._visrange = effrange * 1.5 # should be > 1.0

        self._dist = 0.0

        assert len(self.hitboxes) == 1
        self._hbx = self.hitboxes[0]
        #self._hbx.cnode.show()
        self._hbx.set_active(False)
        self._armed = False

        if vzoomed:
            zoomfac = self._refvzoomfac * (self.caliber / self._refcaliber)
            bbox = self._refvscale * zoomfac
            EnhancedVisual(parent=self, bbox=bbox)

        self._vpuff = vpuff

        self._target = target # for debugging

        if self._monpath:
            self._pos0 = pos
            self._gravdrop = Point3()
            self._gravvel = Vec3()
            self._muzzledir = hprtovec(hpr)

        if self._target:
            self._target_min_dist = float_info.max
            self._target_preint_y = float_info.max
            self._target_preint_r = float_info.max
            self._target_pstint_y = -float_info.max
            self._target_pstint_r = -float_info.max
            self._target_hit = False

        if initdt != 0.0:
            self.move(initdt)

        self.hits_critical = True

        base.taskMgr.add(self._loop, "shell-loop")


    def destroy (self):

        if not self.alive:
            return
        if self._target:
            cf = lambda x: (x if abs(x) < float_info.max else 0.0)
            dbgval(1, "shell-target",
                   (self._target_hit, "%s", "hit"),
                   (self._target_min_dist, "%.1f", "mindist", "m"),
                   ((cf(self._target_preint_y), cf(self._target_pstint_y)), "%.1f", "ppinty", "m"),
                   ((cf(self._target_preint_r), cf(self._target_pstint_r)), "%.1f", "ppintr", "m"))
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done

        #if False:
        if self._vpuff and self.world.below_surface(self._pos):
            posg = self.world.intersect_surface(self._pos - self._vel * self.world.dt, self._pos)
            size = 10.0 * (self.caliber / 0.030)
            Splash(world=self.world, pos=posg, size=3.0, relsink=0.5,
                   numquads=1, texture="images/particles/effects-rocket-exp-3.png",
                   texsplit=8, fps=24, numframes=28,
                   glowmap="images/particles/effects-rocket-exp-3_gw.png")
            self.destroy()
            return task.done

        if self._dist >= self._visrange:
            self.destroy()
            return task.done

        if self._dist >= self._effrange:
            if self._armed:
                self._hbx.set_active(False)
                self._armed = False
                if not self._visible:
                    self.destroy()
                    return task.done
        elif not self._armed:
            if self._dist > self._hbxlen:
                self._hbx.set_active(True)
                self._armed = True

        if self._target:
            tdist = self.dist(self._target)
            self._target_min_dist = min(tdist, self._target_min_dist)
            dpos = self._target.pos() - self._pos
            vdir = unitv(self._vel)
            y = dpos.dot(vdir)
            r = (dpos - vdir * y).length()
            if y > 0.0:
                if self._target_preint_y > y:
                    self._target_preint_y = y
                    self._target_preint_r = r
            else:
                if self._target_pstint_y < y:
                    self._target_pstint_y = y
                    self._target_pstint_r = r

        return task.cont


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos, silent=True)
        if inert:
            return True

        if self.world.player and obody is self.world.player.ac:
            snd = Sound3D(
                "audio/sounds/cockpit-hit.ogg",
                parent=obody, singleat=True,
                volume=0.8, loop=0.2, fadetime=0.01)
        else:
            snd = Sound3D(
                "audio/sounds/flight-hit.ogg",
                parent=obody, singleat=True,
                volume=0.8, loop=0.2, fadetime=0.01)
        snd.play()

        if not self._visible:
            self.destroy()
        else:
            self._hbx.set_active(False)
            self._armed = False
            min_exttime = 0.05
            max_exttime = 0.10
            calfac = (self.caliber / 0.030)**2
            exttime = intl01v(randunit()**(1.0 / calfac), min_exttime, max_exttime)
            self._acc = Vec3()
            self._visrange = self._dist + self._vel.length() * exttime

        if self._target:
            self._target_hit = (obody is self._target)

        return False


    def move (self, dt):

        pos = self._pos
        vel = self._vel
        acc = self._acc

        dpos = vel * dt + acc * (0.5 * dt**2)
        pos1 = pos + dpos
        vel1 = vel + acc * dt
        #print "--here25", pos1

        self._dist += dpos.length()

        # Needed in base class:
        self._prev_vel = vel
        self._pos = pos1
        self._vel = vel1
        self._acc = acc

        self.node.setPos(pos1)
        #self.node.setHpr(vectohpr(vel1))
        #if self._visible:
            ##self.node.setHpr(vectohpr(vel1))
            #self.node.setHpr(vectohpr(vel1 - self.world.chaser.vel()))

        if self._monpath:
            dist = self._dist + vel.length() * dt # use old vel
            speed = vel1.length()
            mdir = self._muzzledir
            ppvel = vel1 - mdir * vel1.dot(mdir)
            ppspeed = ppvel.length()
            spacc = acc.dot(unitv(vel1))
            ppspacc = acc.dot(unitv(ppvel))
            gravacc = self.world.gravacc
            self._gravdrop += self._gravvel * dt + gravacc * (0.5 * dt**2)
            self._gravvel += gravacc * dt
            gravdrop = self._gravdrop.length()
            pos0 = self._pos0
            dpos = pos1 - pos0
            offmuzzle = (dpos - mdir * dpos.dot(mdir)).length()
            dbgval(1, "shell-move",
                   (dist, "%5.0f", "dist", "m"),
                   (speed, "%6.1f", "speed", "m/s"),
                   (ppspeed, "%6.1f", "ppspeed", "m/s"),
                   (spacc, "%7.1f", "spacc", "m/s^2"),
                   (ppspacc, "%6.2f", "ppspacc", "m/s^2"),
                   (gravdrop, "%5.1f", "gravdrop", "m"),
                   (offmuzzle, "%6.1f", "offmuzzle", "m"))


class Cannon (object):
    """
    Generic cannon.
    """

    longdes = _("generic")
    shortdes = _("G/CN")
    cpitdes = {}
    against = ["plane", "heli", "vehicle", "ship", "building"]
    stype = Shell
    ftype = ("square", 1.0)
    mzvel = 850.0
    effrange = 1200.0
    rate = 0.04
    burstlen = 10
    soundname = None

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0,
                  subnode=None):
        """
        Parameters:
        - parent (Body): the body which mounts the cannon
        - mpos (Point3): position of muzzle relative to parent
        - mhpr (Vec3): rotation of muzzle relative to parent
        - mltpos (Point3): position of muzzle flash light relative to parent
        - ammo (int): number of rounds in full ammo pack
        - viseach (int or (int, int)): visible each N-th shell (0 means none),
            or each N-th shell with M-th shift.
        - reloads(int): number of reloads to ammo pack;
            if less then zero, then infinite
        - relrate (double): rate of reloading in seconds
        - subnode (NodePath): subnode to which positions and orientations
            are relative to, instead of parent's main node
        """

        self.__class__.derive_dynamics()

        self.world = parent.world
        self.parent = parent
        self._full_ammo = ammo
        if isinstance(viseach, (tuple, list)):
            self._viseach, self._visstart = viseach
        else:
            self._viseach, self._visstart = viseach, viseach // 2
        self.mpos = mpos
        self.mhpr = mhpr
        self.mltpos = mltpos

        self.alive = True
        self.ammo = ammo
        self.reloads = reloads
        self.relrate = relrate
        self.mpos_override = None

        self._fire_rounds = 0
        self._wait_next_round = 0.0
        self._wait_reload_time = 0.0

        max_vpf_rate = 0.10
        self._vpfeach = int(max_vpf_rate / self.rate + 0.5)

        self._target = None # for debugging

        pnode = subnode if subnode is not None else parent.node
        self._platform = pnode.attachNewNode("cannon-platform")
        self._platform.setPos(mpos)
        self._platform.setHpr(mhpr)

        self.mflashes = []
        if self.ftype is not None:
            ltpos = None
            if mltpos is not None:
                ltpos = mltpos - mpos
            mshape, mscale = self.ftype
            mflash = MuzzleFlash(parent=self.parent, subnode=self._platform,
                                 pos=Point3(), hpr=Vec3(),
                                 ltpos=ltpos, rate=self.rate,
                                 shape=mshape, scale=mscale)
            self.mflashes.append(mflash)

        if self.parent.mass is not None:
            self.parent.mass += self.ammo * self.stype.mass

        base.taskMgr.add(self._loop, "cannon-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        for mflash in self.mflashes:
            mflash.destroy()
        self._platform.removeNode()


    _dyn = None

    @classmethod
    def derive_dynamics (cls, rep=False):

        if cls._dyn is not None:
            return cls._dyn

        htrop = 11000.0
        hstrat = 20000.0
        rhoz = 1.225
        rhoefac = -1.10e-4

        d = cls.stype.caliber
        cd = cls.stype.dragcoeff
        m = cls.stype.mass * cls.stype.pmassfac
        vmz = cls.mzvel
        reff = cls.effrange

# @cache-key-start: cannon-dynamics
        carg = AutoProps(
            htrop=htrop, hstrat=hstrat, rhoz=rhoz, rhoefac=rhoefac,
            d=d, cd=cd, m=m, vmz=vmz, reff=reff,
        )
        this_path = internal_path("data", __file__)
        ckey = (sorted(carg.props()),
                get_cache_key_section(this_path.replace(".pyc", ".py"),
                                      "cannon-dynamics"))
        cname = cls.__name__.lower()
        cpath = join_path("cndyn", cname, "basedat.pkl")
        dyn = read_cache_object(cpath, ckey)
        if dyn is None:
            dyn = cls._derive(rep=rep, **dict(carg.props()))
            write_cache_object(dyn, cpath, ckey)
# @cache-key-end: cannon-dynamics

        cls._dyn = dyn
        return dyn


# @cache-key-start: cannon-dynamics
    @classmethod
    def _derive (cls, htrop, hstrat, rhoz, rhoefac, d, cd, m, vmz, reff,
                 rep=False):

        dt = 50e-3
        rtrk = reff * 0.70
        rhos = []
        rbfacs = []
        fcrhosqv = -0.5 * (0.25 * pi * d**2) * cd / m
        for h in (0.0, 0.5 * htrop, htrop):
            rhofac = exp(rhoefac * h)
            rho = rhoz * rhofac
            fcsqv = fcrhosqv * rho
            t = 0.0
            r = 0.0
            v = vmz
            c0 = None
            sum_rbfac_dt = 0.0
            while r < rtrk:
                c = fcsqv * v**2
                t += dt
                r += v * dt + c * (0.5 * dt**2)
                v += c * dt
                if c0 is None:
                    c0 = c
                rbfac = c / c0
                sum_rbfac_dt += rbfac * dt
            rbfac = sum_rbfac_dt / t
            rhos.append(rho)
            rbfacs.append(rbfac)
            if rep:
                dbgval(1, "cannon-derive-at-alt",
                       (h, "%.0f", "h", "m"),
                       (rho, "%.3f", "rho", "kg/m^3"),
                       (rbfac, "%.3f", "rbfac"))
        assert len(rhos) == 3
        ret = solve_linsys_3(rhos[0]**2, rhos[0], 1.0,
                             rhos[1]**2, rhos[1], 1.0,
                             rhos[2]**2, rhos[2], 1.0,
                             rbfacs[0], rbfacs[1], rbfacs[2])
        crbf2, crbf1, crbf0 = ret
        if rep:
            dbgval(1, "cannon-derive-rho-fit",
                   (crbf2, "%.5f", "crbf2"),
                   (crbf1, "%.5f", "crbf1"),
                   (crbf0, "%.5f", "crbf0"))

        spda = degrees(atan(0.5 / reff))
        if rep:
            dbgval(1, "cannon-derive-spread",
                   (spda, "%.3f", "spda", "deg"))

        dyn = SimpleProps(crbf2=crbf2, crbf1=crbf1, crbf0=crbf0,
                          fcrhosqv=fcrhosqv, spda=spda)
        return dyn
# @cache-key-end: cannon-dynamics


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done

        dt = self.world.dt
        if dt == 0.0:
            return task.cont

        if self.ammo == 0 and self.reloads != 0:
            if self._wait_reload_time > 0:
                self._wait_reload_time -= dt
            else:
                self.ammo = self._full_ammo
                if self.parent.mass is not None:
                    self.parent.mass += self.ammo * self.stype.mass
                if self.reloads > 0:
                    self.reloads -= 1

        ltime = 0.0
        dtw = self._wait_next_round
        first = True
        while self.ammo != 0 and self._fire_rounds != 0 and ltime < dt:
            if self._wait_next_round <= 0.0:
                if self.soundname:
                    snd = Sound3D("audio/sounds/%s.ogg" % self.soundname,
                                  parent=self.parent, singleat=True,
                                  volume=0.4, loop=0.2, fadetime=0.01)
                    snd.play()
                if first:
                    first = False
                    quat = self._platform.getQuat(self.world.node)
                    if self.mpos_override is not None:
                        mpos = self.mpos_override - self.mpos
                        pos = self.world.node.getRelativePoint(self._platform, mpos)
                    else:
                        pos = self._platform.getPos(self.world.node)
                    hpr = quat.getHpr()
                    gacc = self.world.gravacc
                    adens = self.world.airdens(pos[2])
                    mzvel = self.mzvel
                    pvel = self.parent.vel()
                    effrange = self.effrange
                    ret = self.launch_dynamics_st(gacc, adens, mzvel, effrange, pvel)
                    fvel, dvelp, facc, daccp = ret[:4]
                    spda = self._dyn.spda
                    dspda = getattr(self.parent, "shell_spread_angle", 0.0)
                    spda += dspda
                spos = pos - pvel * ltime
                # ...remove firing platform component from forwarded position.
                shpr = hpr + Vec3(uniform(-spda, spda), uniform(-spda, spda), 0.0)
                #shpr = hpr
                mzdir = hprtovec(shpr)
                vel = fvel + mzdir * dvelp
                acc = facc + mzdir * daccp
                if self._viseach > 0:
                    isvis = ((self.ammo + self._visstart) % self._viseach == 0)
                    isvzmd = (self.ammo % self.burstlen == 0)
                else:
                    isvis = False
                    isvzmd = False
                isvpf = (self.ammo % self._vpfeach == 0)
                shell = self.stype(self.world, spos, shpr, vel, acc, effrange,
                                   initdt=ltime, visible=isvis, vzoomed=isvzmd,
                                   vpuff=isvpf, target=self._target)
                shell.initiator = self.parent
                #if self.world.player and self.parent is self.world.player.ac:
                    #self.world.player.record_release(shell)
                if self._fire_rounds > 0:
                    self._fire_rounds -= 1
                self.ammo -= 1
                if self.parent.mass is not None:
                    self.parent.mass -= self.stype.mass
                if self.ammo == 0:
                    self._wait_reload_time = self.relrate
                for mflash in self.mflashes:
                    mflash.active = True
                self._wait_next_round = self.rate
            else:
                dtc = min(dt, dtw, dt - ltime)
                ltime += dtc
                self._wait_next_round -= dtc
                dtw = self.rate
        if self.ammo == 0 or self._fire_rounds == 0:
            for mflash in self.mflashes:
                mflash.active = False

        return task.cont


    def ready (self):
        """
        Returns:
        - [bool]: True if the cannon is ready to fire next round.
        """

        return (    self.ammo > 0
                and self._wait_next_round <= 0.0)


    def fire (self, rounds=-1, target=None):
        """
        Fire a number of rounds once ready.

        rounds given as -1 means to fire without stopping.
        rounds given as -2 means to fire a nominal burst.
        rounds given as 0 means to stop firing.

        Returns:
        - [float]: estimated time of firing
        """

        if rounds == -2:
            self._fire_rounds = self.burstlen
        else:
            self._fire_rounds = rounds
        if self._fire_rounds > 0:
            ftime = self._fire_rounds * self.rate
        else:
            ftime = self.ammo * self.rate
        self._target = target
        return ftime


    def update (self, mpos=None, mhpr=None, mltpos=None, subnode=None):
        """
        Update cannon parameters.

        Parameters same as in constructor.
        """

        if subnode is -1:
            subnode = self.parent.node
        if subnode is not None:
            self._platform.reparentTo(subnode)

        if mpos is not None:
            self.mpos = mpos
            self._platform.setPos(mpos)
        if mhpr is not None:
            self._platform.setHpr(mhpr)

        if mltpos is not None:
            mltpos = mltpos - self.mpos
        for mflash in self.mflashes:
            mflash.update(ltpos=mltpos)


    @classmethod
    def launch_dynamics_st (cls, gacc, adens, mzvel, effrange, pvel):

        fvel = pvel
        dvelp = mzvel

        dq = cls._dyn
        rbfac = dq.crbf0 + dq.crbf1 * adens + dq.crbf2 * adens**2
        faccv = dq.fcrhosqv * adens * mzvel * rbfac
        facc = pvel * faccv + gacc
        #facc = type(pvel)(0.0, 0.0, 0.0)
        daccp = mzvel * faccv
        #daccp = 0.0

        etime = effrange / mzvel

        return fvel, dvelp, facc, daccp, etime


    def launch_dynamics (self, dbl=False):

        gacc = self.world.gravacc
        ppos = self.parent.pos()
        adens = self.world.airdens(ppos[2])
        pvel = self.parent.vel()
        if dbl:
            gacc = vtod(gacc)
            pvel = vtod(pvel)
        return self.launch_dynamics_st(gacc, adens, self.mzvel, self.effrange,
                                       pvel)


