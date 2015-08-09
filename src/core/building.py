# -*- coding: UTF-8 -*-

from pandac.PandaModules import VBase2, VBase2D, Vec3, Point2, Point3
from pandac.PandaModules import NodePath

from src import pycv
from src.core.body import Body
from src.core.effect import fire_n_smoke_3
from src.core.fire import PolyExplosion
from src.core.misc import rgba, AutoProps, remove_subnodes, set_texture
from src.core.misc import fx_uniform, fx_choice
from src.core.sound import Sound3D
from src.core.table import Table1


class Building (Body):

    family = "building"
    species = "generic"
    longdes = None
    shortdes = None

    basesink = 0.0
    strength = 300.0
    minhitdmg = 20.0
    maxhitdmg = 200.0
    rcs = 0.01
    hitboxdata = []
    hitdebris = None
    # hitdebris = AutoProps(
        # #firetex="images/particles/explosion1.png",
        # #smoketex="images/particles/smoke1-1.png",
        # debristex=[
            # "images/particles/airplanedebris_1.png",
            # "images/particles/airplanedebris_2.png",
            # "images/particles/airplanedebris_3-1.png",
            # "images/particles/airplanedebris_3-2.png",
            # "images/particles/airplanedebris_3-3.png"])
    hitflash = AutoProps()
    modelpath = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    castshadow = True
    shdmodelpath = None
    glowmap = rgba(0,0,0, 0.1)
    glossmap = None
    destfirepos = None
    destoffparts = []
    desttextures = []
    distraise = []

    def __init__ (self, world, name, side,
                  texture=None, normalmap=None, clamp=True,
                  pos=None, hpr=None, sink=None, damage=None,
                  burns=True):

        # ====================

        if pos is None:
            pos = Point2()
        if hpr is None:
            hpr = Vec3()
        if sink is None:
            sink = 0.0

        self._burns = burns

        if isinstance(pos, (VBase2, VBase2D)):
            z1 = world.elevation(pos) - self.basesink - sink
        else:
            z1 = pos[2]
        pos1 = Point3(pos[0], pos[1], z1)

        if self.castshadow:
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
        else:
            self.shdmodelpath = None
            shdmodind = None

        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=(self.strength * 0.1),
            name=name, side=side,
            modeldata=AutoProps(
                path=self.modelpath, shadowpath=self.shdmodelpath,
                texture=texture, normalmap=normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                clamp=clamp,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            hitboxdata=self.hitboxdata,
            hitlight=AutoProps(),
            hitdebris=self.hitdebris, hitflash=self.hitflash,
            amblit=True, dirlit=True, pntlit=4, fogblend=True,
            obright=True, ltrefl=(self.glossmap is not None),
            shdshow=True, shdmodind=shdmodind,
            pos=pos1, hpr=hpr)

        width, length, height = self.bbox
        self._size_xy = min(width, length)
        self.size = max(width, length, height)

        self.damage = damage or 0.0

        self.damage_trails = []
        self.turrets = []
        self.decoys = []

        if self.distraise:
            self._distraise_table = Table1(*zip(*self.distraise))
            self._distraise_updperiod = 0.219
            self._distraise_updwait = 0.0
            self._distraise_basepos = pos1

        base.taskMgr.add(self._loop, "building-loop-%s" % self.name)


    def _loop (self, task):

        if not self.alive:
            return task.done

        if self.distraise:
            dt = self.world.dt
            self._distraise_updwait -= dt
            if self._distraise_updwait <= 0.0:
                self._distraise_updwait += self._distraise_updperiod
                cvdist = self.world.camera.getDistance(self.node)
                dz = self._distraise_table(cvdist)
                pos = self._distraise_basepos + Point3(0.0, 0.0, dz)
                self.node.setPos(pos)

        return task.cont


    def destroy (self):

        if not self.alive:
            return
        for turret in self.turrets:
            turret.destroy()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > self.minhitdmg:
            self.damage += obody.hitforce
        if obody.hitforce > self.maxhitdmg and self.damage < self.strength:
            self.damage = self.strength

        if self.damage >= self.strength:
            self.set_shotdown(5.0)

            self.explode_minor()

            if "_all_" in self.destoffparts:
                self.modelnode.removeNode()
                self.models = []
            else:
                remove_subnodes(self.node, self.destoffparts)
            if self.desttextures:
                desttexture = fx_choice(self.desttextures)
                for model in self.models:
                    set_texture(model, texture=desttexture)

            if self._burns:
                fire_n_smoke_3(
                    parent=self, store=self.damage_trails,
                    fpos1=self.destfirepos,
                    spos1=Vec3(0.0, 0.0, 0.0),
                    fdelay1=fx_uniform(0.0, 1.0),
                    fdelay2=fx_uniform(1.0, 4.0),
                    fdelay3=fx_uniform(1.0, 4.0),
                    fdelay4=fx_uniform(1.0, 4.0))

            for turret in self.turrets:
                turret.destroy()

        return False


    def explode (self, destroy=True, offset=None):

        if not self.alive:
            return

        exp = PolyExplosion(world=self.world, pos=self.pos(offset=offset),
                            firepart=3, smokepart=3,
                            sizefac=6.0, timefac=1.4, amplfac=1.8,
                            smgray=pycv(py=(30,60), c=(220, 255)), smred=0, firepeak=(0.3, 0.6))
        snd = Sound3D("audio/sounds/%s.ogg" % "explosion01",
                      parent=exp, volume=1.0, fadetime=0.1)
        snd.play()
        # if destroy:
            # self.shotdown = True
            # self.destroy()
        # self.world.explosion_damage(self.hitforce * 0.2, self)


    def explode_minor (self, offset=None):

        exp = PolyExplosion(world=self.world, pos=self.pos(offset=offset),
                            sizefac=1.2, timefac=0.4, amplfac=0.6,
                            smgray=pycv(py=(60,90), c=(220, 255)), smred=0, firepeak=(0.3, 0.6))
        snd = Sound3D("audio/sounds/%s.ogg" % "explosion01",
                      parent=exp, volume=1.0, fadetime=0.1)
        snd.play()


class CustomBuilding (Building):

    species = "common"
    basesink = 0.0

    def __init__ (self, world, name, side,
                  strength, minhitdmg, maxhitdmg, rcs,
                  hitboxdata, modelpath,
                  texture=None, normalmap=None, glowmap=rgba(0,0,0, 0.1),
                  glossmap=None, transp=None, clamp=True,
                  pos=None, hpr=None, sink=None,
                  damage=None, burns=True,
                  destfirepos=None, destoffparts=[], desttexture=None,
                  distraise=[], castshadow=True, shdmodelpath=None,
                  longdes=None, shortdes=None):

        self.strength = strength
        self.minhitdmg = minhitdmg
        self.maxhitdmg = maxhitdmg
        self.rcs = rcs
        self.hitboxdata = hitboxdata
        self.modelpath = modelpath
        self.glowmap = glowmap
        self.glossmap = glossmap
        self.destfirepos = destfirepos
        self.destoffparts = destoffparts
        self.distraise = distraise
        self.castshadow = castshadow
        self.shdmodelpath = shdmodelpath
        self.longdes = longdes
        self.shortdes = shortdes
        if desttexture:
            self.desttextures = [desttexture]
        Building.__init__(self,
            world=world, name=name, side=side,
            texture=texture, normalmap=normalmap, clamp=clamp,
            pos=pos, hpr=hpr, sink=sink,
            damage=damage, burns=burns)
        if transp is not None:
            self.node.setTransparency(transp)


