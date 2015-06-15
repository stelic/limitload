# -*- coding: UTF-8 -*-

from math import pi, floor

from pandac.PandaModules import Vec3, Vec4, Point3
from pandac.PandaModules import NodePath, TransparencyAttrib, AmbientLight

from src.core.body import Body, EnhancedVisual
from src.core.fire import Splash
from src.core.misc import AutoProps, load_model_lod_chain
from src.core.misc import make_quad_lattice, set_texture
from src.core.shader import make_stores_shader, make_shader
from src.core.sound import Sound3D
from src.core.transl import *


class PodRocket (Body):

    family = "podrocket"
    species = "generic"
    longdes = _("generic")
    shortdes = _("G/PRCK")
    cpitdes = {}
    mass = 15.0
    diameter = 0.080
    maxspeed = 600.0
    maxthracc = 400.0
    maxvdracc = 4.0
    maxflighttime = 6.0
    minlaunchdist = 200.0
    hitforce = 1.0
    expforce = 20.0
    rcs = 0.00005
    hitboxdata = []
    modelpath = None
    texture = None
    normalmap = None
    glowmap = None
    glossmap = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None,
                  extvis=False, basictrail=True):

        if pos is None:
            pos = Vec3()
        if hpr is None:
            hpr = Vec3()
        if speed is None:
            speed = self.maxspeed

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
            pos=pos, hpr=hpr, vel=speed)

        if basictrail:
            radius = 0.5 * self.diameter
            length = radius * 2000.0
            radius0 = radius * 5.0
            radius1 = radius * 1.0
            numquads = 4
            texture = "images/particles/smoke6-1.png"
            alpha = 0.2
            ret = self._make_tail(length, radius0, radius1, numquads,
                                  texture, alpha)
            (self._tail_node, self._tail_uvscr, self._tail_uvoff,
             self._tail_uvspdfac) = ret
        else:
            self._tail_node = None

        if True:
            lnchsnd = Sound3D(
                "audio/sounds/%s.ogg" % "missile-launch4",
                parent=self, volume=0.5, fadetime=0.1)
            lnchsnd.play()

        self._armdist = self.minlaunchdist
        self._armed = False

        self.exhaust_trails = []

        self._pos = pos

        self._flightdist = 0.0
        self._flighttime = 0.0

        if extvis:
            bx, by, bz = self.bbox
            bbox = Vec3(bx, by * 50.0, bz)
            EnhancedVisual(parent=self, bbox=bbox)

        base.taskMgr.add(self._loop, "podrocket-loop-%s" % self.name)


    _cache_tail_geom = {}

    def _make_tail (self, length, radius0, radius1, numquads, texture, alpha):

        umax = length / (2 * radius0)

        tkey = (length, radius0, radius1, numquads)
        base_tail_node = self._cache_tail_geom.get(tkey)
        if base_tail_node is None:
            uvext = (0.0, 0.0, umax, 1.0)
            alext = (alpha, 0.0, 0.0, alpha)
            base_tail_node = make_quad_lattice(length=-length,
                                               radius0=radius0, radius1=radius1,
                                               numquads=numquads,
                                               uvext=uvext, alext=alext)
            self._cache_tail_geom[tkey] = base_tail_node
        tail_node = self.world.node.attachNewNode("tail_off")
        tail_node.setQuat(self.quat())
        off_tail_node = base_tail_node.copyTo(tail_node)
        off_tail_node.setY(-0.5 * self.bbox[1])

        tail_node.setTwoSided(True)
        tail_node.setTransparency(TransparencyAttrib.MAlpha)
        tail_node.setDepthWrite(False)
        self.world.add_altbin_node(tail_node)

        uvscrn = "INuvscr"
        shader = make_shader(ambln=self.world.shdinp.ambsmln,
                             modcol=True, uvscrn=uvscrn)
        tail_node.setShader(shader)
        set_texture(tail_node, texture, clamp=False)
        tail_uvscr = AmbientLight(name="uvscr-tail")
        tail_node.setShaderInput(uvscrn, NodePath(tail_uvscr))
        tail_uvoff = Vec4(0.0, 0.0, umax, 1.0)
        tail_uvscr.setColor(tail_uvoff)
        tail_uvspdfac = umax / length

        return tail_node, tail_uvscr, tail_uvoff, tail_uvspdfac


    def _loop (self, task):

        if not self.alive:
            return task.done

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

        if not self._armed and self._flightdist >= self._armdist:
            self.set_hitboxes(hitboxdata=self.hitboxdata)
            self._armed = True

        if self._tail_node is not None:
            self._tail_uvoff[0] -= (vel.length() * self._tail_uvspdfac) * dt
            self._tail_uvscr.setColor(self._tail_uvoff)

        return task.cont


    def destroy (self):

        if not self.alive:
            return
        if self._tail_node is not None:
            self._tail_node.removeNode()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos, silent=True)
        if inert:
            return True

        self.explode()

        return False


    def explode (self, pos=None):

        if not self.alive:
            return

        if pos is None:
            pos = self.pos()
        exp = Splash(world=self.world, pos=pos, size=8.0, relsink=0.5,
                     numquads=1,
                     texture="images/particles/effects-rocket-exp-3.png",
                     glowmap="images/particles/effects-rocket-exp-3_gw.png",
                     texsplit=8, fps=24, numframes=28)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion-missile",
            parent=exp, volume=0.8, fadetime=0.1)
        snd.play()

        self.shotdown = True
        self.destroy()

        self.world.explosion_damage(force=self.expforce, ref=self)


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        if dt == 0.0:
            return

        pos = self._pos
        vel = self._vel
        speed = vel.length()
        fdir = vel / speed

        dspeed = self.maxspeed - speed
        maxacc = self.maxthracc
        minacc = -self.maxvdracc
        if dspeed >= 0.0:
            acc = fdir * min(dspeed * 1.0, maxacc)
        else:
            acc = fdir * max(dspeed * 1.0, minacc)
        dpos = vel * dt + acc * (0.5 * dt**2)
        pos1 = pos + dpos
        dvel = acc * dt
        vel1 = vel + dvel

        self.node.setPos(pos1)
        self._prev_vel = self._vel # needed in base class
        self._vel = vel1 # needed in base class
        self._acc = acc # needed in base class

        self._pos = pos1

        self._flighttime += dt
        self._flightdist += dpos.length()

        if self._tail_node is not None:
            self._tail_node.setPos(pos1)


class RocketPod (Body):

    rtype = PodRocket
    mass = 150.0 # empty
    diameter = 0.500
    rate = 0.20
    rounds = 10
    modelpath = None
    texture = None
    normalmap = None
    glowmap = None
    glossmap = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    #soundname = None

    def __init__ (self):

        raise StandardError("Rocket pods cannot be created as bodies.")


class PodLauncher (object):
    """
    Generic podded rocket launcher.
    """

    def __init__ (self, ptype, parent, points,
                  reloads=0, relrate=0):
        """
        Parameters:
        - ptype (<RocketPod>): type of rocket pods being launched from
        - parent (Body): the body which mounts the podded launcher
        - points ([int*]): indices of parent pylons with rocket pods
        - reloads (int): number of reloads to full rocket pods;
            if less then zero, then infinite
        - relrate (double): rate of reloading in seconds
        """

        self.parent = parent
        self.world = parent.world

        self.ptype = ptype
        self._full_points = points
        self.relrate = relrate
        self.reloads = reloads

        self._pnode = parent.node

        self._wait_prep_time = 0.0
        self._wait_reload_time = 0.0
        self._launch = False
        self._launch_next_pod = 0

        self._extvis_period = 1.0
        self._wait_extvis_time = 0.0

        self._store_model_report_addition = None
        self._store_model_report_removal = None
        self.points = []
        self.store_models = []
        self._pod_rounds = []
        self._create_stores()

        self.alive = True
        base.taskMgr.add(self._loop, "podlauncher-loop")


    def destroy (self):

        if not self.alive:
            return
        self._remove_stores()
        self.alive = False


    def _remove_stores (self):

        for rind in xrange(len(self.points)):
            smodel = self.store_models.pop()
            smodel.removeNode()
            pod_rounds = self._pod_rounds.pop()
            if self.parent.mass is not None:
                self.parent.mass -= self.ptype.mass
                self.parent.mass -= pod_rounds * self.ptype.rtype.mass
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
        assert not self.store_models
        assert not self._pod_rounds
        self.points = []
        self.rounds = 0


    def _create_stores (self):

        self._remove_stores()

        shader = make_stores_shader(self.world,
                                    normal=bool(self.ptype.normalmap),
                                    glow=bool(self.ptype.glowmap),
                                    gloss=bool(self.ptype.glossmap))
        self.points = list(self._full_points)
        self.store_models = []
        self._pod_rounds = []
        for pind in self.points:
            ppos, phpr = self.parent.pylons[pind][:2]
            ret = load_model_lod_chain(
                self.world.vfov, self.ptype.modelpath,
                texture=self.ptype.texture, normalmap=self.ptype.normalmap,
                glowmap=self.ptype.glowmap, glossmap=self.ptype.glossmap,
                shadowmap=self.world.shadow_texture,
                scale=self.ptype.modelscale)
            lnode = ret[0]
            lnode.reparentTo(self.parent.node)
            ppos1 = ppos + Point3(0.0, 0.0, -0.5 * self.ptype.diameter)
            lnode.setPos(ppos1 + self.ptype.modeloffset)
            lnode.setHpr(phpr + self.ptype.modelrot)
            lnode.setShader(shader)
            self.store_models.append(lnode)
            if self._store_model_report_addition:
                self._store_model_report_addition(lnode)
            pod_rounds = self.ptype.rounds
            self._pod_rounds.append(pod_rounds)
            self.rounds += pod_rounds
            if self.parent.mass is not None:
                self.parent.mass += self.ptype.mass
                self.parent.mass += pod_rounds * self.ptype.rtype.mass


    def set_store_model_report_functions (self, add_func, rem_func):

        self._store_model_report_addition = add_func
        self._store_model_report_removal = rem_func


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        if self.rounds == 0 and self.reloads != 0:
            if self._wait_reload_time > 0.0:
                self._wait_reload_time -= dt
            else:
                self._create_stores()
                if self.reloads > 0:
                    self.reloads -= 1

        if self._wait_prep_time > 0.0:
            self._wait_prep_time -= dt

        if self._wait_extvis_time > 0.0:
            self._wait_extvis_time -= dt

        if self._launch:
            rst, fpoints = self.ready()
            if rst == "ready":
                rind = self._launch_next_pod
                assert self._pod_rounds[rind] > 0
                while True:
                    self._launch_next_pod += 1
                    self._launch_next_pod %= len(self.points)
                    if self._pod_rounds[self._launch_next_pod] > 0:
                        break
                    assert self._launch_next_pod != rind
                smodel = self.store_models[rind]
                wpos = smodel.getPos(self.world.node)
                whpr = smodel.getHpr(self.world.node)
                rtype = self.ptype.rtype
                extvis = (self._wait_extvis_time <= 0.0)
                speed = max(self.parent.speed(), rtype.maxspeed * 0.8)
                rocket = rtype(world=self.world,
                               name=("from-%s" % self.parent.name),
                               side=self.parent.side,
                               pos=wpos, hpr=whpr,
                               speed=speed,
                               extvis=extvis)
                rocket.initiator = self.parent
                if self.world.player and self.parent is self.world.player.ac:
                    self.world.player.record_release(rocket)
                self._pod_rounds[rind] -= 1
                self.rounds -= 1
                if self.rounds == 0:
                    self._wait_reload_time = self.relrate
                self._wait_prep_time = self.ptype.rate
                if extvis:
                    self._wait_extvis_time = self._extvis_period
                self._launch = False
                if self.parent.mass is not None:
                    self.parent.mass -= self.ptype.rtype.mass
                #if self.ptype.soundname:
                    #snd = Sound3D("audio/sounds/%s.ogg" % self.ptype.soundname,
                                  #parent=self.parent, singleat=True,
                                  #volume=1.0, loop=self.ptype.rate,
                                  #fadetime=(self.ptype.rate * 0.1))
                    #snd.play()

        return task.cont


    def ready (self):
        """
        Check the readiness state of next rocket.

        Returns:
        - state [string]: "norounds" if the launcher is empty,
            "loading" if next rocket is being prepared for firing,
            "ready" if a rocket is ready for launch.
        - points [[int*]]: pylon indices of rounds to be launched
        """

        fpoints = [self._launch_next_pod] if self.rounds else []

        if self.rounds == 0:
            return "norounds", fpoints
        elif self._wait_prep_time > 0.0:
            return "loading", fpoints
        else:
            return "ready", fpoints


    def fire (self):
        """
        Launch one rocket once ready.

        Parameters:
        """

        rst, pinds = self.ready()
        if rst == "ready":
            self._launch = True
        else:
            self._launch = False


