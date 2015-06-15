# -*- coding: UTF-8 -*-

from math import sqrt

from pandac.PandaModules import Vec3, Point3, QuatD

from src import pycv
from src.core.body import Body
from src.core.fire import PolyExplosion
from src.core.misc import AutoProps, print_each, load_model_lod_chain, rgba
from src.core.misc import unitv, vtod, vtof, qtod, qtof
from src.core.shader import make_stores_shader
from src.core.sound import Sound3D
from src.core.transl import *


class Bomb (Body):

    family = "bomb"
    species = "generic"
    longdes = _("generic")
    shortdes = _("G/BMB")
    cpitdes = {}
    against = ["building", "vehicle", "ship"]
    mass = 500.0
    diameter = 0.400
    maxspeed = 400.0
    hitforce = 10.0
    expforce = 2000.0
    rcs = 0.00030
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 2.0)]
    modelpath = None
    texture = None
    normalmap = None
    glowmap = "models/weapons/_glowmap.png"
    glossmap = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    engsoundname = None

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None):

        # ====================

        if pos is None:
            pos = Vec3()
        if hpr is None:
            hpr = Vec3()
        if speed is None:
            maxspeed = Bomb.limspeeds_st(world, pos[2])
            speed = maxspeed

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

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, limnum="hum", volume=0.3, loop=True)
            self.engine_sound.play()

        self._prev_pos = pos
        self._flightdist = 0.0
        self._flighttime = 0.0

        self._armdist = 200.0 #!!!
        self._armed = False

        base.taskMgr.add(self._loop, "bomb-loop-%s" % self.name)


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        pos = self.pos()

        if self.world.below_surface(pos):
            vel = self.vel()
            posg = self.world.intersect_surface(pos - vel * dt, pos)
            self.explode(pos=posg)
            return task.done

        self._flighttime += dt
        ds = (pos - self._prev_pos).length()
        self._flightdist += ds

        if not self._armed and self._flightdist >= self._armdist:
            self.set_hitboxes(hitboxdata=self.hitboxdata)
            self._armed = True

        self._prev_pos = pos
        return task.cont


    def destroy (self):

        if not self.alive:
            return
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

        if self._armed:
            if pos is None:
                pos = self.pos()
            if self.world.otr_altitude(pos) < 20.0:
                debrispitch = (10, 80)
            else:
                debrispitch = (-90, 90)
            exp = PolyExplosion(world=self.world, pos=pos,
                                sizefac=4.0, timefac=0.8, amplfac=1.2,
                                smgray=pycv(py=(45,55), c=(220, 255)), smred=0,
                                debrispitch=debrispitch)
            snd = Sound3D("audio/sounds/%s.ogg" % "explosion-missile",
                          parent=exp, volume=0.8, fadetime=0.1)
            snd.play()

        self.destroy()

        if self._armed:
            self.world.explosion_damage(force=self.expforce, ref=self)


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
        angvel = vtod(self.angvel())

        # ====================
        # Translation.

        maxspeed = self.limspeeds(alt)

        gracc = vtod(self.world.gravacc)
        dracc = vdir * (-self.world.absgravacc * (speed**2 / maxspeed**2))
        acc = gracc + dracc
        pos1 = pos + vel * dt + acc * (0.5 * dt**2)
        vel1 = vel + acc * dt

        self.node.setPos(vtof(pos1))
        self._prev_vel = Vec3(self._vel) # needed in base class
        self._vel = vtof(vel1) # needed in base class
        self._acc = vtof(acc) # needed in base class

        # ====================
        # Rotation.

        vdir1 = unitv(vel1)
        paxis = vdir.cross(vdir1)
        if paxis.length() > 1e-5:
            paxis.normalize()
            dspitch = vdir.signedAngleRad(vdir1, paxis)
        else:
            paxis = quat.getRight()
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

        # print_each(105, 0.25, "--bmb1", pos, speed, self._flighttime)


    def limspeeds (self, alt=None):

        if alt is None:
            alt = self.pos()[2]

        return self.limspeeds_st(self, self.world, alt)


    @staticmethod
    def limspeeds_st (clss, world, alt):

        maxspeed0 = clss.maxspeed

        rfac = world.airdens_factor(alt)
        maxspeed = maxspeed0 / sqrt(rfac)

        return maxspeed


class Dropper (object):
    """
    Generic bomb dropper.
    """

    def __init__ (self, btype, parent, points, rate,
                  reloads=0, relrate=0):
        """
        Parameters:
        - btype (<Bomb>): type of bombs being dropped
        - parent (Body): the body which mounts the dropper
        - points ([int*]): indices of loaded parent pylons
        - rate (double): rate of dropping in seconds
        - reloads(int): number of reloads to full bomb pack;
            if less then zero, then infinite
        - relrate (double): rate of reloading in seconds
        """

        self.btype = btype
        self.parent = parent
        self.world = parent.world
        self._pnode = parent.node
        self._full_points = points
        self.rate = rate
        self._relrate = relrate
        self.reloads = reloads

        self.alive = True
        self._wait_prep_time = 0.0
        self._wait_reload_time = 0.0
        self._create_chaser = None
        self._drop = False

        self._store_model_report_addition = None
        self._store_model_report_removal = None
        self.points = []
        self.store_models = []
        self._create_stores()

        task = base.taskMgr.add(self._loop, "bomb-dropper-loop")


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
                self.parent.mass -= self.btype.mass
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
        assert not self.store_models
        self.points = []
        self.rounds = 0


    def _create_stores (self):

        self._remove_stores()

        shader = make_stores_shader(self.world,
                                    normal=bool(self.btype.normalmap),
                                    glow=bool(self.btype.glowmap),
                                    gloss=bool(self.btype.glossmap))
        self.points = list(self._full_points)
        self.store_models = []
        for pind in self.points:
            ppos, phpr = self.parent.pylons[pind][:2]
            ret = load_model_lod_chain(
                self.world.vfov, self.btype.modelpath,
                texture=self.btype.texture, normalmap=self.btype.normalmap,
                glowmap=self.btype.glowmap, glossmap=self.btype.glossmap,
                shadowmap=self.world.shadow_texture,
                scale=self.btype.modelscale)
            lnode = ret[0]
            lnode.reparentTo(self.parent.node)
            ppos1 = ppos + Point3(0.0, 0.0, -0.5 * self.btype.diameter)
            lnode.setPos(ppos1 + self.btype.modeloffset)
            lnode.setHpr(phpr + self.btype.modelrot)
            lnode.setShader(shader)
            self.store_models.append(lnode)
            if self._store_model_report_addition:
                self._store_model_report_addition(lnode)
            if self.parent.mass is not None:
                self.parent.mass += self.btype.mass
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
                self.points = list(self._full_points)
                self.rounds = len(self.points)
                self._create_stores()
                if self.reloads > 0:
                    self.reloads -= 1
                if self.parent.mass is not None:
                    self.parent.mass += self.rounds * self.btype.mass

        if self._wait_prep_time > 0.0:
            self._wait_prep_time -= dt

        if self._drop:
            rst, pinds = self.ready()
            if rst == "ready":
                for pind in pinds:
                    #print "--bdrop"
                    rind = self.points.index(pind)
                    self.points.pop(rind)
                    smodel = self.store_models.pop(rind)
                    wpos = smodel.getPos(self.world.node)
                    whpr = smodel.getHpr(self.world.node)
                    smodel.removeNode()
                    if self._store_model_report_removal:
                        self._store_model_report_removal(smodel)
                    bomb = self.btype(world=self.world,
                                    name=("from-%s" % self.parent.name),
                                    side=self.parent.side,
                                    pos=wpos, hpr=whpr,
                                    speed=self.parent.speed())
                    bomb.initiator = self.parent
                    if self.world.player and self.parent is self.world.player.ac:
                        self.world.player.record_release(bomb)
                    if self._create_chaser:
                        ch = self._create_chaser(bomb)
                        self.parent.world.add_action_chaser(ch)
                    self._create_chaser = None
                    self._wait_prep_time = self.rate
                    self.rounds -= 1
                    if self.rounds == 0:
                        self._wait_reload_time = self._relrate
                    self._drop = False
                    if self.parent.mass is not None:
                        self.parent.mass -= self.btype.mass

        return task.cont


    def ready (self):
        """
        Check the readiness state of next bombs to be dropped.

        Returns:
        - state [string]: "norounds" if the dropper is empty,
            "readying" if a bomb is being readied,
            "ready" if a bomb is ready to drop.
        - points [[int*]]: pylon indices of rounds to be dropped
        """

        pinds = [self.points[-1]] if self.points else []

        if self.rounds == 0:
            return "norounds", pinds
        elif self._wait_prep_time > 0.0:
            return "readying", pinds
        else:
            return "ready", pinds


    def fire (self, addchf=False):
        """
        Drop one bomb once ready.

        Parameters:
        - addchf [(Body)->*Chaser]: function to construct action chaser
        """

        rst, pinds = self.ready()
        if rst == "ready":
            #print "--bdrop-drop-accepted"
            self._drop = True
            self._create_chaser = addchf
        else:
            self._drop = False


