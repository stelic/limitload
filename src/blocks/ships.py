# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Vec3, Point3

from src.core.body import Body, HitboxData
from src.core.effect import fire_n_smoke
from src.core.misc import rgba, remove_subnodes
from src.core.misc import fx_uniform
from src.core.ship import Ship
from src.core.trail import PolyTrail
from src.core.transl import *


class Ticonderoga (Ship):

    species = "ticonderoga"
    longdes = _("Ticonderoga")
    shortdes = _("Ticonderoga")

    maxspeed = 15.0
    maxturnrate = radians(4.0)
    maxthracc = 1.0
    maxvdracc = 10.0
    strength = 5000.0
    minhitdmg = 100.0
    maxhitdmg = 2000.0
    rcs = 10
    hitboxdata = []
    basesink = 6.5
    modelpath = [("models/ships/ticonderoga/ticonderoga.egg", 25000)]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None, damage=None):

        Ship.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, sink=sink,
                      damage=damage)

        #sumsink = self.basesink + (sink or 0.0)
        #wake1 = PolyTrail(parent=self,
                          #pos=Point3(0.0, -80.0, sumsink + 0.5),
                          #radius0=20.0, radius1=60.0, lifespan=40.0,
                          #color=rgba(250, 250, 250, 0.6),
                          #texture="images/particles/exhaust06.png", flat=True)
        #self.wake_trails.append(wake1)


class Atlantis (Ship):

    species = "atlantis"
    longdes = _("Atlantis")
    shortdes = _("Atlantis")

    maxspeed = 8.0
    maxturnrate = radians(2.0)
    maxthracc = 0.3
    maxvdracc = 30.0
    strength = 10000.0
    minhitdmg = 100.0
    maxhitdmg = 3000.0
    rcs = 30
    hitboxdata = []
    basesink = 15.0
    modelpath = [("models/ships/atlantis/atlantis.egg", 30000)]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None, damage=None):

        Ship.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, sink=sink,
                      damage=damage)

        #sumsink = self.basesink + (sink or 0.0)
        #wake1 = PolyTrail(parent=self,
                          #pos=Point3(0.0, -80.0, sumsink + 0.5),
                          #radius0=20.0, radius1=60.0, lifespan=40.0,
                          #color=rgba(250, 250, 250, 0.6),
                          #texture="images/particles/exhaust06.png", flat=True)
        #self.wake_trails.append(wake1)


class GunBoat1 (Ship):

    species = "gunboat1"
    longdes = _("Gun Boat")
    shortdes = _("Gun Boat")

    maxspeed = 20.0
    maxturnrate = radians(12.0)
    maxthracc = 3.0
    maxvdracc = 6.0
    strength = 110.0
    minhitdmg = 0.0
    maxhitdmg = 60.0
    rcs = 0.0195
    hitboxdata = [(Point3(0.0, 0.2, 5.1), 6.0, 26.3, 5.1)]
    basesink = 2.9
    fmodelpath = "models/ships/gunboat1/gunboat1.egg"
    modelpath = [("models/ships/gunboat1/gunboat1-1.egg", 800),
                 ("models/ships/gunboat1/gunboat1-2.egg", 4000),
                 ("models/ships/gunboat1/gunboat1-3.egg", 12000)]
    shdmodelpath = "models/ships/gunboat1/gunboat1-shadow.egg"
    normalmap = "models/ships/gunboat1/gunboat1_nm.png"
    glossmap = "models/ships/gunboat1/gunboat1_gls.png"

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None, damage=None):

        Ship.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, sink=sink,
                      damage=damage)


class OilPlatform1 (Ship):

    species = "oilplatform1"
    longdes = _("Oil Platform")
    shortdes = _("Oil Platform")

    maxspeed = 3.0
    maxturnrate = radians(6.0)
    maxthracc = 0.5
    maxvdracc = 28.0
    strength = 300.0
    minhitdmg = 0.0
    maxhitdmg = 100.0
    rcs = 0.312
    hitboxdata = [
        HitboxData(name="plat",
                   colldata=[(Point3(-7.42, 2.05, 42.01), 42.84, 42.84, 10.31),
                             (Point3(-7.42, 2.05, 16.15), 34.44, 34.44, 16.15),
                             (Point3(58.76, 2.05, 17.10),  5.51,  5.51, 17.01)],
                   longdes=_("platform"), shortdes=_("PLAT"),
                   selectable=True),
        HitboxData(name="hpad",
                   colldata=[(Point3(-39.07, -32.79, 55.17), 15.17, 15.02, 2.86)],
                   longdes=_("helipad"), shortdes=_("HPAD"),
                   selectable=False),
        HitboxData(name="cns1",
                   colldata=[(Point3(59.54,   2.06, 45.58), 1.56,  1.56, 11.43),
                             (Point3(59.54, -13.02, 54.85), 1.69, 36.79,  1.59)],
                   longdes=_("construction1"), shortdes=_("CNS1"),
                   selectable=True),
        HitboxData(name="ins1",
                   colldata=[(Point3(-8.81, -11.09, 59.29), 14.67, 14.12, 6.97)],
                   longdes=_("installation1"), shortdes=_("INS1"),
                   selectable=True),
        HitboxData(name="ins2",
                   colldata=[(Point3(20.08, -25.32, 55.29), 12.22, 9.49, 2.97)],
                   longdes=_("installation2"), shortdes=_("INS2"),
                   selectable=True),
        HitboxData(name="ins3",
                   colldata=[(Point3(19.88, 1.01, 57.46), 6.99, 13.57, 6.95)],
                   longdes=_("installation3"), shortdes=_("INS3"),
                   selectable=True),
        HitboxData(name="ins4",
                   colldata=[(Point3(17.78, 29.35, 53.32), 8.70, 10.68, 1.00)],
                   longdes=_("installation4"), shortdes=_("INS4"),
                   selectable=False),
        HitboxData(name="ins5",
                   colldata=[(Point3(-12.40, 20.30, 60.73), 21.71, 16.78, 7.32),
                             (Point3(-21.14, 11.22, 69.02), 12.40,  7.12, 2.24)],
                   longdes=_("installation5"), shortdes=_("INS5"),
                   selectable=True),
    ]
    basesink = 0.0
    #fmodelpath = "models/ships/oil-platform/oil_platform_01.egg"
    modelpath = [("models/ships/oil-platform/oil_platform_01.egg", 5000),
                 ("models/ships/oil-platform/oil_platform_01-2.egg", 10000),
                 ("models/ships/oil-platform/oil_platform_01-3.egg", 25000)]


    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None,
                  damage=None, defsam1on=False, defsam2on=False):

        self._defsam1on = defsam1on
        self._defsam2on = defsam2on
        self._defsam1handles = ["def1_plat", "def1_crank", "def1_tubes",
                                "def1_missile1", "def1_missile2",
                                "def1_missile3", "def1_missile4"]
        self._defsam2handles = ["def2_plat", "def2_crank", "def2_tubes",
                                "def2_missile1", "def2_missile2",
                                "def2_missile3", "def2_missile4"]

        self.hitboxdata = OilPlatform1.hitboxdata[:]
        if self._defsam1on:
            hbx = HitboxData(name="def1",
                             colldata=[(Point3(-19.5, 11.0, 75.5), 4.2)],
                             longdes=_("sam1"), shortdes=_("SAM1"),
                             selectable=True)
            self.hitboxdata.append(hbx)
        if self._defsam2on:
            hbx = HitboxData(name="def2",
                             colldata=[(Point3(22.0, -24.5, 61.5), 4.2)],
                             longdes=_("sam2"), shortdes=_("SAM2"),
                             selectable=True)
            self.hitboxdata.append(hbx)

        Ship.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, sink=sink,
                      damage=damage)

        remove_subnodes(self.node, ["oilplat_constr2", "oilplat_constr3",
                                    "oilplat_chopper"])

        if self._defsam1on:
            self._hbx_def1.hitpoints = 80 # Defense
            self._hbx_def1.minhitdmg = 0 # Defense
            self._hbx_def1.maxhitdmg = 30 # Defense
            self._hbx_def1.out = False # Defense
            self.defense1_destroyed = False # Defense
        else:
            remove_subnodes(self.node, self._defsam1handles)
            self.defense1_destroyed = True # Defense

        if self._defsam2on:
            self._hbx_def2.hitpoints = 80 # Defense
            self._hbx_def2.minhitdmg = 0 # Defense
            self._hbx_def2.maxhitdmg = 30 # Defense
            self._hbx_def2.out = False # Defense
            self.defense2_destroyed = False # Defense
        else:
            remove_subnodes(self.node, self._defsam2handles)
            self.defense2_destroyed = True # Defense

        self._hbx_plat.hitpoints = 5000
        self._hbx_hpad.hitpoints = 210
        self._hbx_cns1.hitpoints = 160
        self._hbx_ins1.hitpoints = 200
        self._hbx_ins2.hitpoints = 200
        self._hbx_ins3.hitpoints = 200
        self._hbx_ins4.hitpoints = 240
        self._hbx_ins5.hitpoints = 260

        self._hbx_plat.minhitdmg = 500
        self._hbx_hpad.minhitdmg = 1
        self._hbx_cns1.minhitdmg = 0
        self._hbx_ins1.minhitdmg = 0
        self._hbx_ins2.minhitdmg = 0
        self._hbx_ins3.minhitdmg = 0
        self._hbx_ins4.minhitdmg = 5
        self._hbx_ins5.minhitdmg = 5

        self._hbx_plat.maxhitdmg = 2500
        self._hbx_hpad.maxhitdmg = 140
        self._hbx_cns1.maxhitdmg = 80
        self._hbx_ins1.maxhitdmg = 140
        self._hbx_ins2.maxhitdmg = 140
        self._hbx_ins3.maxhitdmg = 140
        self._hbx_ins4.maxhitdmg = 160
        self._hbx_ins5.maxhitdmg = 180

        self._hbx_plat.out = False
        self._hbx_hpad.out = False
        self._hbx_cns1.out = False
        self._hbx_ins1.out = False
        self._hbx_ins2.out = False
        self._hbx_ins3.out = False
        self._hbx_ins4.out = False
        self._hbx_ins5.out = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        Body.collide(self, obody, chbx, cpos)

        if self.shotdown:
            return

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_plat.hitpoints <= 0 and not self._hbx_plat.out:
            self.explode(offset=self._hbx_plat.center)
            self._hbx_plat.out = True
        if self._hbx_hpad.hitpoints <= 0 and not self._hbx_hpad.out:
            self.explode_minor(offset=self._hbx_hpad.center)
            self._hbx_hpad.out = True
        if self._hbx_cns1.hitpoints <= 0 and not self._hbx_cns1.out:
            self.explode_minor(offset=self._hbx_cns1.center)
            self._hbx_cns1.out = True
        if self._hbx_ins1.hitpoints <= 0 and not self._hbx_ins1.out:
            self.explode(offset=self._hbx_ins1.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(236, 112, 27, 1.0),
                         fpos=Vec3(-9.0, -11.0, 51.0),
                         spos=Vec3(-9.0, -11.0, 54.0),
                         spos2=None,
                         ftcol=0.6,
                         stcol=0.6,
                         fforce=10.0,
                         sforce=10.0,
                         flifespan=1.2,
                         slifespan=3.2,
                         sclfact=2.4,
                         psfact=0.8,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.04, 0.08) * self._size_xy,
                         emampfact=1.1,
                         absolute=True,
                         fdelay=fx_uniform(1.0, 4.0))
            self._hbx_ins1.out = True
        if self._hbx_ins2.hitpoints <= 0 and not self._hbx_ins2.out:
            self.explode_minor(offset=self._hbx_ins2.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(231, 132, 47, 1.0),
                         fpos=Vec3(18.0, -25.0, 51.0),
                         spos=Vec3(18.0, -25.0, 54.0),
                         spos2=None,
                         ftcol=0.6,
                         stcol=0.6,
                         fforce=8.0,
                         sforce=8.0,
                         flifespan=1.2,
                         slifespan=2.8,
                         sclfact=2.3,
                         psfact=0.6,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.02, 0.04) * self._size_xy,
                         emampfact=1.2,
                         absolute=True,
                         fdelay=fx_uniform(0.1, 4.0))
            if self._defsam2on:
                self._hbx_def2.hitpoints = 0 # Defense
            self._hbx_ins2.out = True
        if self._hbx_ins3.hitpoints <= 0 and not self._hbx_ins3.out:
            self.explode_minor(offset=self._hbx_ins3.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(241, 132, 87, 1.0),
                         fpos=Vec3(20.0, 1.0, 51.0),
                         spos=Vec3(20.0, 1.0, 54.0),
                         spos2=None,
                         ftcol=0.8,
                         stcol=0.6,
                         fforce=8.0,
                         sforce=8.0,
                         flifespan=1.3,
                         slifespan=2.9,
                         sclfact=2.2,
                         psfact=0.6,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.02, 0.04) * self._size_xy,
                         emampfact=1.2,
                         absolute=True,
                         fdelay=fx_uniform(0.1, 4.0))
            self._hbx_ins3.out = True
        if self._hbx_ins4.hitpoints <= 0 and not self._hbx_ins4.out:
            self.explode_minor(offset=self._hbx_ins4.center)
            self._hbx_ins4.out = True
        if self._hbx_ins5.hitpoints <= 0 and not self._hbx_ins5.out:
            self.explode(offset=self._hbx_ins5.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(241, 96, 53, 1.0),
                         fpos=Vec3(-20.0, 20.0, 51.0),
                         spos=Vec3(-20.0, 20.0, 54.0),
                         spos2=None,
                         ftcol=0.6,
                         stcol=0.6,
                         fforce=12.0,
                         sforce=12.0,
                         flifespan=1.4,
                         slifespan=3.4,
                         sclfact=2.5,
                         psfact=0.8,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.04, 0.08) * self._size_xy,
                         emampfact=1.3,
                         absolute=True,
                         fdelay=fx_uniform(1.0, 4.0))
            if self._defsam1on:
                self._hbx_def1.hitpoints = 0 # Defense
            self._hbx_ins5.out = True

        ##### Defense
        if self._defsam1on:
            if self._hbx_def1.hitpoints <= 0 and not self._hbx_def1.out:
                self.explode(offset=self._hbx_def1.center)
                self.defense1_destroyed = True
                self._hbx_def1.out = True
                remove_subnodes(self.node, self._defsam1handles)
        if self._defsam2on:
            if self._hbx_def2.hitpoints <= 0 and not self._hbx_def2.out:
                self.explode(offset=self._hbx_def2.center)
                self.defense2_destroyed = True
                self._hbx_def2.out = True
                remove_subnodes(self.node, self._defsam2handles)
        ##### Defense END

        if (self._hbx_cns1.hitpoints <= 0 and self._hbx_ins1.hitpoints <= 0 and self._hbx_ins2.hitpoints <= 0 and self._hbx_ins3.hitpoints <= 0 and self._hbx_ins5.hitpoints <= 0) or (self._hbx_plat.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            self.node.setColor(rgba(22, 22, 22, 1.0))
            self.set_shotdown(10.0)


class OilPlatform2 (Ship):

    species = "oilplatform2"
    longdes = _("Oil Platform")
    shortdes = _("Oil Platform")

    maxspeed = 3.0
    maxturnrate = radians(6.0)
    maxthracc = 0.5
    maxvdracc = 28.0
    strength = 300.0
    minhitdmg = 0.0
    maxhitdmg = 100.0
    rcs = 0.271
    hitboxdata = [
        HitboxData(name="plat",
                   colldata=[(Point3( -3.63, 1.24, 36.57), 45.05, 27.77, 5.41),
                             (Point3(-30.25, 1.32, 49.12),  7.26, 26.90, 7.15)],
                   longdes=_("platform"), shortdes=_("PLAT"),
                   selectable=True),
        HitboxData(name="leg1",
                   colldata=[(Point3(-40.78, +20.79, 23.31), 3.79, 3.79, 23.31)],
                   longdes=_("leg1"), shortdes=_("LEG1"),
                   selectable=False),
        HitboxData(name="leg2",
                   colldata=[(Point3(+33.47, +20.36, 23.31), 3.79, 3.79, 23.31)],
                   longdes=_("leg2"), shortdes=_("LEG2"),
                   selectable=False),
        HitboxData(name="leg3",
                   colldata=[(Point3(-40.60, -18.00, 23.31), 3.79, 3.79, 23.31)],
                   longdes=_("leg3"), shortdes=_("LEG3"),
                   selectable=False),
        HitboxData(name="leg4",
                   colldata=[(Point3(+33.47, -17.91, 23.31), 3.79, 3.79, 23.31)],
                   longdes=_("leg4"), shortdes=_("LEG4"),
                   selectable=False),
        HitboxData(name="hpad",
                   colldata=[(Point3(-57.73, -25.09, 52.22), 17.00, 17.00, 3.93)],
                   longdes=_("helipad"), shortdes=_("HPAD"),
                   selectable=False),
        HitboxData(name="cns1",
                   colldata=[(Point3(34.74,  -7.37, 62.93), 2.00,  2.00, 20.96),
                             (Point3(34.85, -28.34, 81.59), 2.20, 51.20,  2.20)],
                   longdes=_("construction1"), shortdes=_("CNS1"),
                   selectable=True),
        HitboxData(name="cns2",
                   colldata=[(Point3(-31.69, 22.43,  85.65),  2.40, 2.40, 29.39),
                             (Point3(-10.50, 22.40, 112.01), 51.12, 2.40,  1.40)],
                   longdes=_("construction2"), shortdes=_("CNS2"),
                   selectable=True),
        HitboxData(name="ins1",
                   colldata=[(Point3( -1.19,  1.53, 49.79), 16.43, 23.07,  7.82),
                             (Point3(-17.17, 10.04, 54.76),  8.98, 14.05, 12.79)],
                   longdes=_("installation1"), shortdes=_("INS1"),
                   selectable=True),
        HitboxData(name="ins2",
                   colldata=[(Point3(22.89, 1.32, 49.12),  7.26, 26.90, 7.15)],
                   longdes=_("installation2"), shortdes=_("INS2"),
                   selectable=True),
        HitboxData(name="ins3",
                   colldata=[(Point3(2.84, 5.70, 65.48), 7.50, 15.00, 7.88)],
                   longdes=_("installation3"), shortdes=_("INS3"),
                   selectable=True),
    ]
    basesink = 0.0
    # fmodelpath = "models/ships/oil-platform/oil_platform_02.egg"
    modelpath = [("models/ships/oil-platform/oil_platform_02.egg", 5000),
                 ("models/ships/oil-platform/oil_platform_02-2.egg", 10000),
                 ("models/ships/oil-platform/oil_platform_02-3.egg", 25000)]


    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, sink=None,
                  damage=None, defsam1on=False, defsam2on=False):

        Ship.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, sink=sink,
                      damage=damage)

        # remove_subnodes(self.node, ["oilplat_constr2", "oilplat_constr3", "oilplat_chopper"])

        self._hbx_plat.hitpoints = 3800
        self._hbx_leg1.hitpoints = 450
        self._hbx_leg2.hitpoints = 450
        self._hbx_leg3.hitpoints = 450
        self._hbx_leg4.hitpoints = 450
        self._hbx_hpad.hitpoints = 180
        self._hbx_cns1.hitpoints = 160
        self._hbx_cns2.hitpoints = 160
        self._hbx_ins1.hitpoints = 400
        self._hbx_ins2.hitpoints = 400
        self._hbx_ins3.hitpoints = 200

        self._hbx_plat.minhitdmg = 500
        self._hbx_leg1.minhitdmg = 1
        self._hbx_leg2.minhitdmg = 1
        self._hbx_leg3.minhitdmg = 1
        self._hbx_leg4.minhitdmg = 1
        self._hbx_hpad.minhitdmg = 1
        self._hbx_cns1.minhitdmg = 0
        self._hbx_cns2.minhitdmg = 0
        self._hbx_ins1.minhitdmg = 0
        self._hbx_ins2.minhitdmg = 0
        self._hbx_ins3.minhitdmg = 0

        self._hbx_plat.maxhitdmg = 2000
        self._hbx_leg1.maxhitdmg = 210
        self._hbx_leg2.maxhitdmg = 210
        self._hbx_leg3.maxhitdmg = 210
        self._hbx_leg4.maxhitdmg = 210
        self._hbx_hpad.maxhitdmg = 90
        self._hbx_cns1.maxhitdmg = 80
        self._hbx_cns2.maxhitdmg = 80
        self._hbx_ins1.maxhitdmg = 200
        self._hbx_ins2.maxhitdmg = 200
        self._hbx_ins3.maxhitdmg = 140

        self._hbx_plat.out = False
        self._hbx_leg1.out = False
        self._hbx_leg2.out = False
        self._hbx_leg3.out = False
        self._hbx_leg4.out = False
        self._hbx_hpad.out = False
        self._hbx_cns1.out = False
        self._hbx_cns2.out = False
        self._hbx_ins1.out = False
        self._hbx_ins2.out = False
        self._hbx_ins3.out = False

        self._failure_full = False
        self._leghbxs = [self._hbx_leg1, self._hbx_leg2, self._hbx_leg3, self._hbx_leg4]


    def collide (self, obody, chbx, cpos):

        Body.collide(self, obody, chbx, cpos)

        if self.shotdown:
            return

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_plat.hitpoints <= 0 and not self._hbx_plat.out:
            self.explode(offset=self._hbx_plat.center)
            self._hbx_plat.out = True
        if self._hbx_leg1.hitpoints <= 0 and not self._hbx_leg1.out:
            self.explode_minor(offset=self._hbx_leg1.center)
            self._hbx_leg1.out = True
        if self._hbx_leg2.hitpoints <= 0 and not self._hbx_leg2.out:
            self.explode_minor(offset=self._hbx_leg2.center)
            self._hbx_leg2.out = True
        if self._hbx_leg3.hitpoints <= 0 and not self._hbx_leg3.out:
            self.explode_minor(offset=self._hbx_leg3.center)
            self._hbx_leg3.out = True
        if self._hbx_hpad.hitpoints <= 0 and not self._hbx_hpad.out:
            self.explode_minor(offset=self._hbx_hpad.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=None,
                         fcolorend=None,
                         fpos=None,
                         spos=Vec3(-48.0, -18.0, 40.0),
                         spos2=None,
                         ftcol=None,
                         stcol=0.6,
                         fforce=None,
                         sforce=10.0,
                         flifespan=None,
                         slifespan=2.6,
                         sclfact=2.2,
                         psfact=0.4,
                         pdir=Vec3(0, 0, 1),
                         fphpr=None,
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.01, 0.02) * self._size_xy,
                         emampfact=1.0,
                         absolute=True,
                         fdelay=None)
            self._hbx_hpad.out = True
        if self._hbx_cns1.hitpoints <= 0 and not self._hbx_cns1.out:
            self.explode_minor(offset=self._hbx_cns1.center)
            self._hbx_cns1.out = True
        if self._hbx_cns2.hitpoints <= 0 and not self._hbx_cns1.out:
            self.explode_minor(offset=self._hbx_cns1.center)
            self._hbx_cns2.out = True
        if self._hbx_ins1.hitpoints <= 0 and not self._hbx_ins1.out:
            self.explode(offset=self._hbx_ins1.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(242, 137, 29, 1.0),
                         fpos=Vec3(-5.0, 3.0, 41.0),
                         spos=Vec3(-5.0, 3.0, 45.0),
                         spos2=None,
                         ftcol=0.5,
                         stcol=0.6,
                         fforce=12.0,
                         sforce=12.0,
                         flifespan=1.2,
                         slifespan=3.2,
                         sclfact=2.6,
                         psfact=1.0,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.04, 0.08) * self._size_xy,
                         emampfact=1.2,
                         absolute=True,
                         fdelay=fx_uniform(1.0, 6.0))
            self._hbx_ins1.out = True
            self._hbx_ins3.hitpoints = 0
        if self._hbx_ins2.hitpoints <= 0 and not self._hbx_ins2.out:
            self.explode(offset=self._hbx_ins2.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(247, 141, 96, 1.0),
                         fpos=Vec3(23.0, 1.0, 48.0),
                         spos=Vec3(23.0, 1.0, 52.0),
                         spos2=None,
                         ftcol=0.5,
                         stcol=0.6,
                         fforce=12.0,
                         sforce=12.0,
                         flifespan=1.4,
                         slifespan=3.0,
                         sclfact=2.3,
                         psfact=0.8,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.015, 0.03) * self._size_xy,
                         emampfact=1.1,
                         absolute=True,
                         fdelay=fx_uniform(1.0, 4.0))
            self._hbx_ins2.out = True
        if self._hbx_ins3.hitpoints <= 0 and not self._hbx_ins3.out:
            self.explode_minor(offset=self._hbx_ins3.center)
            fire_n_smoke(parent=self, store=self.damage_trails,
                         fcolor=rgba(255, 255, 255, 1.0),
                         fcolorend=rgba(239, 121, 85, 1.0),
                         fpos=Vec3(3.0, 6.0, 58.0),
                         spos=Vec3(3.0, 6.0, 62.0),
                         spos2=None,
                         ftcol=0.6,
                         stcol=0.6,
                         fforce=14.0,
                         sforce=14.0,
                         flifespan=1.2,
                         slifespan=3.2,
                         sclfact=2.4,
                         psfact=0.6,
                         pdir=Vec3(0, 0, 1),
                         fphpr=Vec3(0,0,0),
                         sphpr=Vec3(0,0,0),
                         emradfact=fx_uniform(0.02, 0.04) * self._size_xy,
                         emampfact=1.1,
                         absolute=True,
                         fdelay=fx_uniform(1.0, 4.0))
            self._hbx_ins3.out = True

        if ((self._hbx_ins1.hitpoints <= 0 and self._hbx_ins2.hitpoints <= 0 and self._hbx_ins3.hitpoints <= 0) or
            self._hbx_plat.hitpoints <= 0 or
            sum(leg.hitpoints <= 0 for leg in self._leghbxs) >= 2):
            self._failure_full = True

        if self._failure_full:
            self.node.setColor(rgba(22, 22, 22, 1.0))
            self.set_shotdown(10.0)


