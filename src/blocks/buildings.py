# -*- coding: UTF-8 -*-

from pandac.PandaModules import Vec3, Point3
from pandac.PandaModules import TransparencyAttrib

from src.core.building import Building
from src.core.body import Body, HitboxData
from src.core.effect import fire_n_smoke_3
from src.core.misc import rgba, remove_subnodes, texture_subnodes
from src.core.misc import fx_uniform
from src.core.transl import *
from src.blocks.weapons import TurretL70


BUILDING_SMALL_LOD_DIST_FULL = 1000
BUILDING_MEDIUM_LOD_DIST_FULL = 2000
BUILDING_SMALL_LOD_DIST_3 = 3000
BUILDING_MEDIUM_LOD_DIST_3 = 6000


class Hangar1 (Building):

    species = "hangar-1"
    basesink = 0.0
    strength = 40000
    minhitdmg = None
    maxhitdmg = None
    rcs = 1.0
    hitboxdata = [
        HitboxData(name="hnrg",
                   colldata=[(Point3(  0.0,  0.0,  9.2), 16.0, 19.0,  4.0),
                             (Point3(  0.0, 17.9,  2.6), 16.0,  1.1,  2.6),
                             (Point3(-14.6,  0.0,  2.6),  1.3, 16.8,  2.6),
                             (Point3( 14.6,  0.0,  2.6),  1.3, 16.8,  2.6),
                             (Point3(-12.5,-17.9,  2.6),  3.5,  1.1,  2.6),
                             (Point3( 12.5,-17.9,  2.6),  3.5,  1.1,  2.6)],
                   longdes=_("hangar building"), shortdes=_("HNRG"),
                   selectable=True),
        HitboxData(name="mdoor",
                   colldata=[(Point3(  0.00, -17.30, 2.57), 9.00, 0.60, 2.57)],
                   longdes=_("hangar main door"), shortdes=_("MDOOR"),
                   selectable=False),
    ]
    modelpath = [("models/buildings/hangar/hangar_1.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/hangar/hangar_1-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/hangar/hangar_1_gw.png"
    glossmap = "models/buildings/hangar/hangar_1_gls.png"
    #destoffparts = []

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        self._hbx_hnrg.hitpoints = 300
        self._hbx_mdoor.hitpoints = 40

        self._hbx_hnrg.minhitdmg = 3
        self._hbx_mdoor.minhitdmg = 0

        self._hbx_hnrg.maxhitdmg = 140
        self._hbx_mdoor.maxhitdmg = 30

        self._hbx_hnrg.out = False
        self._hbx_mdoor.out = False

        self.mdoor_down = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hnrg.hitpoints <= 0 and not self._hbx_hnrg.out:
            self.explode(offset=self._hbx_hnrg.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Point3(0.0, 0.0, 2.0),
                           spos1=Point3(0.0, 0.0, 0.0),
                           sclfact=0.8,
                           emradfact=1.4,
                           flsfact=0.8,
                           slsfact=0.8,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 3.0),
                           fdelay3=fx_uniform(1.0, 3.0),
                           fdelay4=fx_uniform(1.0, 3.0))
            texture_subnodes(self.node, ["hng1_body", "hng1_roof", "hng1_misc",
                                         "hng1_door_main", "hng1_door_side",],
                             texture="models/buildings/hangar/hangar_1_burn.png",
                             glossmap="images/_glossmap_none.png")
            remove_subnodes(self.node, ["hng1_roof", "hng1_misc", "hng1_door_main",
                                        "hng1_door_side"])
            self._hbx_hnrg.out = True
            self._failure_full = True
        if self._hbx_mdoor.hitpoints <= 0 and not self._hbx_mdoor.out:
            self.explode_minor(offset=self._hbx_mdoor.center)
            texture_subnodes(self.node, ["hng1_door_main",],
                             texture="models/buildings/hangar/hangar_1_burn.png",
                             glossmap="images/_glossmap_none.png")
            remove_subnodes(self.node, ["hng1_door_main",])
            self.mdoor_down = True
            self._hbx_mdoor.out = True

        if self._failure_full:
            self.set_shotdown(3.0)

        return False


class HangarNato (Building):

    species = "hangar-nato"
    basesink = 0.0
    strength = 40000
    minhitdmg = None
    maxhitdmg = None
    rcs = 1.0
    hitboxdata = [
        HitboxData(name="hnrg",
                   colldata=[(Point3(  0.0,  0.3, 11.0), 18.2, 22.7,  3.7),
                             (Point3(  0.0,-20.1,  3.6), 13.1,  2.2,  3.6),
                             (Point3(-16.6,  0.3,  3.6),  3.5, 22.7,  3.6),
                             (Point3( 16.6,  0.3,  3.6),  3.5, 22.7,  3.6),
                             (Point3(-11.8, 20.9,  3.6),  1.3,  1.4,  3.6),
                             (Point3( 11.8, 20.9,  3.6),  1.3,  1.4,  3.6)],
                   longdes=_("hangar building"), shortdes=_("HNRG"),
                   selectable=True),
        HitboxData(name="mdoorl",
                   colldata=[(Point3( -5.22, 20.50, 3.60), 5.22, 0.50, 3.60)],
                   longdes=_("hangar main door left"), shortdes=_("MDOORL"),
                   selectable=False),
        HitboxData(name="mdoorr",
                   colldata=[(Point3(  5.22, 20.50, 3.60), 5.22, 0.50, 3.60)],
                   longdes=_("hangar main door right"), shortdes=_("MDOORR"),
                   selectable=False),
    ]
    modelpath = [("models/buildings/hangar/hangar_2.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/hangar/hangar_2-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/hangar/hangar_2_gw.png"
    glossmap = "models/buildings/hangar/hangar_2_gls.png"
    #destoffparts = []

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        self._hbx_hnrg.hitpoints = 500
        self._hbx_mdoorl.hitpoints = 30
        self._hbx_mdoorr.hitpoints = 30

        self._hbx_hnrg.minhitdmg = 10
        self._hbx_mdoorl.minhitdmg = 0
        self._hbx_mdoorr.minhitdmg = 0

        self._hbx_hnrg.maxhitdmg = 300
        self._hbx_mdoorl.maxhitdmg = 20
        self._hbx_mdoorr.maxhitdmg = 20

        self._hbx_hnrg.out = False
        self._hbx_mdoorl.out = False
        self._hbx_mdoorr.out = False

        self.mdoorl_down = False
        self.mdoorr_down = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hnrg.hitpoints <= 0 and not self._hbx_hnrg.out:
            self.explode(offset=self._hbx_hnrg.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Point3(0.0, 0.0, 1.0),
                           spos1=Point3(0.0, 0.0, 0.0),
                           sclfact=0.9,
                           emradfact=1.4,
                           flsfact=0.9,
                           slsfact=0.9,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 3.0),
                           fdelay3=fx_uniform(1.0, 3.0),
                           fdelay4=fx_uniform(1.0, 3.0))
            texture_subnodes(self.node, ["hng2_body", "hng2_body_int", "hng2_misc_1",
                                         "hng2_misc_2", "hng2_door_main_r",
                                         "hng2_door_main_l", "hng2_door_side",],
                             texture="models/buildings/hangar/hangar_2_burn.png",
                             glossmap="images/_glossmap_none.png")
            remove_subnodes(self.node, ["hng2_body", "hng2_misc_1", "hng2_misc_2",
                                        "hng2_door_main_r", "hng2_door_main_l",
                                        "hng2_door_side"])
            self._hbx_hnrg.out = True
            self._failure_full = True
        if self._hbx_mdoorl.hitpoints <= 0 and not self._hbx_mdoorl.out:
            self.explode_minor(offset=self._hbx_mdoorl.center)
            texture_subnodes(self.node, ["hng2_door_main_l",],
                             texture="models/buildings/hangar/hangar_2_burn.png",
                             glossmap="images/_glossmap_none.png")
            remove_subnodes(self.node, ["hng2_door_main_l",])
            self.mdoorl_down = True
            self._hbx_mdoorl.out = True
        if self._hbx_mdoorr.hitpoints <= 0 and not self._hbx_mdoorr.out:
            self.explode_minor(offset=self._hbx_mdoorr.center)
            texture_subnodes(self.node, ["hng2_door_main_r",],
                             texture="models/buildings/hangar/hangar_2_burn.png",
                             glossmap="images/_glossmap_none.png")
            remove_subnodes(self.node, ["hng2_door_main_r",])
            self.mdoorr_down = True
            self._hbx_mdoorr.out = True

        if self._failure_full:
            self.set_shotdown(3.0)

        return False


class RadarRussian1 (Building):

    species = "radar-russian-1"
    basesink = 0.0
    strength = 180
    minhitdmg = 0
    maxhitdmg = 110
    rcs = 1.0
    hitboxdata = [(Point3( 0.0,  0.0, 11.3), 11.0, 11.0, 11.3),
                  (Point3(16.3, 13.2,  2.6),  6.2,  9.6,  2.6)]
    modelpath = [("models/buildings/radarstation/sov_radarstation.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/radarstation/sov_radarstation-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/radarstation/sov_radarstation_gw.png"
    #glossmap = "models/buildings/radarstation/sov_radarstation_gls.png"
    destfirepos = Vec3(0.0, 0.0, 6.0)
    destoffparts = ["radar_sphere_part", "radar_roof", "radar_misc",
                    "glass", "door"]
    desttextures = ["models/buildings/radarstation/sov_radarstation_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class WarehouseRussian1 (Building):

    species = "warehouse-russian-1"
    basesink = 0.0
    strength = 260
    minhitdmg = 40
    maxhitdmg = 130
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.0, 6.2), 50.0, 25.1, 6.2)]
    modelpath = [("models/buildings/warehouse/sov_warehouse3x.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/warehouse/sov_warehouse3x-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/warehouse/sov_warehouse_gw.png"
    #glossmap = "models/buildings/warehouse/sov_warehouse_gls.png"
    destfirepos = Vec3(-4.0, 4.0, 0.0)
    destoffparts = ["wh_roof", "wh_door_rmain", "wh_door_lmain", "wh_door_side", "wh_misc",
                    "glass"]
    desttextures = ["models/buildings/warehouse/sov_warehouse_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class Warehouse1 (Building):

    species = "warehouse-1"
    basesink = 0.0
    strength = 610
    minhitdmg = 70
    maxhitdmg = 280
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.0, 5.0), 26.0, 26.3, 5.0)]
    modelpath = [("models/buildings/warehouse/warehouse_1.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/warehouse/warehouse_1-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/warehouse/warehouse_1_gw.png"
    #glossmap = "models/buildings/warehouse/warehouse_1_gls.png"
    destfirepos = Vec3(0.0, 0.0, 0.0)
    destoffparts = ["wh_roof", "wh_doors", "wh_door_main", "wh_misc"]
    desttextures = ["models/buildings/warehouse/warehouse_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class CampShed1 (Building):

    species = "camp-shed-1"
    basesink = 0.0
    strength = 80
    minhitdmg = 0
    maxhitdmg = 18
    rcs = 0.0
    hitboxdata = [(Point3(-20.0, 0.0, 5.3), 10.5, 21.2, 5.2),
                  (Point3( 20.0, 0.0, 5.3), 10.5, 21.2, 5.2)]
    modelpath = [("models/buildings/misc/camp_shed2x_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/misc/camp_shed2x_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/misc/camp_shed_1_gw.png"
    #glossmap = "models/buildings/misc/camp_shed_1_gls.png"
    destfirepos = None
    destoffparts = ["cs1_body", "cs1_front"]
    desttextures = ["models/buildings/misc/camp_shed_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class Bunker1 (Building):

    species = "bunker-1"
    basesink = 0.0
    strength = 845
    minhitdmg = 110
    maxhitdmg = 600
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.0, 8.0), 15.5, 15.5, 8.0)]
    modelpath = [("models/buildings/misc/bunker_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/misc/bunker_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/misc/bunker_1_gw.png"
    #glossmap = "models/buildings/misc/bunker_1_gls.png"
    destfirepos = None
    destoffparts = ["bu1_body_part"]
    desttextures = ["models/buildings/misc/bunker_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class Bunker2 (Building):

    species = "bunker-2"
    basesink = 0.0
    strength = 710
    minhitdmg = 90
    maxhitdmg = 430
    rcs = 0.0
    hitboxdata = [(Point3( 0.0,   0.0,  4.7), 21.5, 24.5, 4.7),
                  (Point3(-3.4, -19.4, 12.1),  3.8,  3.4, 2.6)]
    modelpath = [("models/buildings/misc/bunker_2.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/misc/bunker_2-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/misc/bunker_2_gw.png"
    #glossmap = "models/buildings/misc/bunker_2_gls.png"
    destfirepos = Vec3(13.0, -14.3, 0.3)
    destoffparts = ["bu2_misc_1", "bu2_misc_2", "bu2_doors", "bu2_roof", "glass"]
    desttextures = ["models/buildings/misc/bunker_2_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class BarrackRussian1 (Building):

    species = "barrack-russian-1"
    basesink = 0.0
    strength = 95
    minhitdmg = 0
    maxhitdmg = 60
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.0, 10.4), 13.2, 26.5, 10.4)]
    modelpath = [("models/buildings/barrack/sov_barrack_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/barrack/sov_barrack_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/barrack/sov_bunker_1_gw.png"
    #glossmap = "models/buildings/barrack/sov_bunker_1_gls.png"
    destfirepos = None
    destoffparts = ["brk_roof", "brk_misc", "brk_door", "glass"]
    desttextures = ["models/buildings/barrack/sov_barrack_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class BarrackRussian2 (Building):

    species = "barrack-russian-2"
    basesink = 0.0
    strength = 210
    minhitdmg = 1
    maxhitdmg = 140
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 15.0, 10.0), 18.0),
                  (Point3(0.0, -15.0, 10.0), 18.0)]
    modelpath = [("models/buildings/barrack/sov_barrack_2.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/barrack/sov_barrack_2-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/barrack/sov_bunker_2_gw.png"
    #glossmap = "models/buildings/barrack/sov_bunker_2_gls.png"
    destfirepos = None
    destoffparts = ["brk_roof", "brk_misc", "brk_door", "glass"]
    desttextures = ["models/buildings/barrack/sov_barrack_2_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class ComtowerRussian1 (Building):

    species = "comtower-russian-1"
    basesink = 0.0
    strength = 70
    minhitdmg = 0
    maxhitdmg = 25
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.6, 3.7), 4.6, 5.6, 3.6)]
    modelpath = [("models/buildings/comtower/sov_comtower_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/comtower/sov_comtower_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/comtower/sov_comtower_1_gw.png"
    #glossmap = "models/buildings/comtower/sov_comtower_1_gls.png"
    destfirepos = None
    destoffparts = ["ct_tower", "ct_roof", "ct_misc", "ct_door", "glass"]
    desttextures = ["models/buildings/comtower/sov_comtower_1_burn.png"]


    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class OutpostUs1 (Building):

    species = "outpost-us-1"
    basesink = 0.0
    strength = 400
    minhitdmg = 1
    maxhitdmg = 250
    rcs = 0.0
    hitboxdata = [(Point3(-1.2, 1.2, 2.0), 17.4, 9.4, 2.0)]
    modelpath = [("models/buildings/outpost/us_01.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/outpost/us_01-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/outpost/us_01_gw.png"
    #glossmap = "models/buildings/outpost/us_01_gls.png"
    destfirepos = None
    destoffparts = ["op_sandbags", "op_canvas", "op_canvas2", "op_crates",
                    "op_machineguns", "op_flag", "op_misc"]
    desttextures = ["models/buildings/warehouse/us_01_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class OutpostUs2 (Building):

    species = "outpost-us-2"
    basesink = 0.0
    strength = 900
    minhitdmg = 100
    maxhitdmg = 500
    rcs = 0.0
    hitboxdata=[(Point3(-20.0, -8.0, 4.0), 6.0),
                (Point3(-20.0, -23.2, 5.0), 9.0),
                (Point3(-34.0, -23.0, 5.0), 9.0),
                (Point3(-34.0, -8.0, 4.0), 9.0),

                (Point3(-32.0, 10.5, 6.0), 8.0),
                (Point3(-32.0, 22.5, 6.0), 8.0),

                (Point3(26.0, 12.0, 7.0), 8.0),
                (Point3(27.0, 11.8, 21.2), 3.0),

                (Point3(-19.7, -38.0, 2.6), 4.0),
                (Point3(-48.3, 4.0, 2.6), 4.0),
                (Point3(35.3, 34.6, 2.6), 4.0),

                (Point3(-13.1, 7.0, 8.0), 3.4),
                (Point3(-13.1, 7.0, 16.0), 3.4)]
    modelpath = [("models/buildings/outpost/us_02.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/outpost/us_02.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/outpost/us_02_gw.png"
    #glossmap = "models/buildings/outpost/us_02_gls.png"
    destfirepos=Vec3(-23.0, -18.0, 0.0),
    destoffparts=["command_tower_roof",
                  "command_tower_misc",
                  "com_tower_roof",
                  "com_dish",
                  "com_tower_misc",
                  "watch_tower_misc",
                  "fuel_barrels"],
    desttextures = ["models/buildings/outpost/us_02_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class OutpostUs3 (Building):

    species = "outpost-us-3"
    basesink = 0.0
    strength = 40000
    minhitdmg = None
    maxhitdmg = None
    rcs = 0.0

    hitboxdata = [
        HitboxData(name="commp",
                   colldata=[(Point3(-19.39,  16.88, 7.90), 18.00, 18.00, 7.90)],
                   longdes=_("command post"), shortdes=_("COMMP"),
                   selectable=True),
        HitboxData(name="barrp",
                   colldata=[(Point3( 14.19, -23.10, 6.42), 19.16, 14.87, 6.42)],
                   longdes=_("barrack post"), shortdes=_("BARRP"),
                   selectable=True),
        HitboxData(name="ulnkp",
                   colldata=[(Point3(-26.67, -28.11, 8.57), 10.88,  7.11, 8.57)],
                   longdes=_("uplink post"), shortdes=_("ULNKP"),
                   selectable=True),
        HitboxData(name="wallf",
                   colldata=[(Point3(-27.47, 57.79, 3.07), 25.75, 1.00, 3.22),
                             (Point3( 37.35, 57.79, 3.07),  8.30, 1.00, 3.22),
                             (Point3( 13.65, 57.71, 8.71), 28.33, 3.88, 2.40)],
                   longdes=_("wall front"), shortdes=_("WALLF"),
                   selectable=True),
        HitboxData(name="wallb",
                   colldata=[(Point3( -3.74, -52.21, 3.07), 49.25, 1.00, 3.22)],
                   longdes=_("wall back"), shortdes=_("WALLB"),
                   selectable=True),
        HitboxData(name="walll",
                   colldata=[(Point3(-51.75,  2.79, 3.07),  1.00, 56.08, 3.22)],
                   longdes=_("wall left"), shortdes=_("WALLL"),
                   selectable=True),
        HitboxData(name="wallr",
                   colldata=[(Point3( 44.27,  2.79, 3.07),  1.00, 56.08, 3.22)],
                   longdes=_("wall right"), shortdes=_("WALLR"),
                   selectable=True),
        HitboxData(name="heli",
                   colldata=[(Point3( 24.78, -20.88, 14.31), 2.0),
                             (Point3( 21.91, -23.19, 14.31), 2.0)],
                   longdes=_("apache"), shortdes=_("HELI"),
                   selectable=True),
    ]
    modelpath = [("models/buildings/outpost/us_03.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/outpost/us_03-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/outpost/us_03_gw.png"
    #glossmap = "models/buildings/outpost/us_03_gls.png"
    #destoffparts=[]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        texture_subnodes(self.node, ["wall_checkpoint", "wall_checkpoint_misc",],
                         texture="models/buildings/outpost/us_03omega_wall_tex.png",
                         normalmap="models/buildings/outpost/us_03_wall_nm.png",
                         glowmap=None, glossmap=None, clamp=False, alpha=False)
        texture_subnodes(self.node, ["fence",],
                         texture="models/buildings/outpost/us_03omega_wall_tex.png",
                         normalmap="models/buildings/outpost/us_03_wall_nm.png",
                         clamp=False, alpha=True)
        texture_subnodes(self.node, ["apache",],
                         texture="models/aircraft/ah64/ah64_tex.png",
                         normalmap="images/_normalmap_none.png",
                         glowmap=None,
                         glossmap="models/aircraft/ah64/ah64_gls.png",
                         clamp=True, alpha=False)
        texture_subnodes(self.node, ["abrams",],
                         texture="models/vehicles/abrams/abramsblackpanther_tex.png",
                         normalmap="models/vehicles/abrams/abrams_nm.png",
                         glowmap=None,
                         glossmap="models/vehicles/abrams/abrams_gls.png",
                         clamp=True, alpha=False)

        self._hbx_commp.hitpoints = 800
        self._hbx_barrp.hitpoints = 600
        self._hbx_ulnkp.hitpoints = 500
        self._hbx_wallf.hitpoints = 500
        self._hbx_wallb.hitpoints = 450
        self._hbx_walll.hitpoints = 450
        self._hbx_wallr.hitpoints = 450
        self._hbx_heli.hitpoints = 30

        self._hbx_commp.minhitdmg = 100
        self._hbx_barrp.minhitdmg = 100
        self._hbx_ulnkp.minhitdmg = 90
        self._hbx_wallf.minhitdmg = 90
        self._hbx_wallb.minhitdmg = 90
        self._hbx_walll.minhitdmg = 90
        self._hbx_wallr.minhitdmg = 90
        self._hbx_heli.minhitdmg = 0

        self._hbx_commp.maxhitdmg = 500
        self._hbx_barrp.maxhitdmg = 400
        self._hbx_ulnkp.maxhitdmg = 400
        self._hbx_wallf.maxhitdmg = 300
        self._hbx_wallb.maxhitdmg = 300
        self._hbx_walll.maxhitdmg = 300
        self._hbx_wallr.maxhitdmg = 300
        self._hbx_heli.maxhitdmg = 20

        self._hbx_commp.out = False
        self._hbx_barrp.out = False
        self._hbx_ulnkp.out = False
        self._hbx_wallf.out = False
        self._hbx_wallb.out = False
        self._hbx_walll.out = False
        self._hbx_wallr.out = False
        self._hbx_heli.out = False

        self.wall_down = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_commp.hitpoints <= 0 and not self._hbx_commp.out:
            self.explode(offset=self._hbx_commp.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Vec3(-19.4, 16.9, 0.0),
                           spos1=None,
                           sclfact=1.2,
                           emradfact=1.0,
                           forcefact=1.0,
                           flsfact=1.0,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 4.0),
                           fdelay3=fx_uniform(1.0, 4.0),
                           fdelay4=fx_uniform(1.0, 4.0))
            texture_subnodes(self.node, ["command_post", "command_post_roof", "command_post_misc", "glass"],
                             texture="models/buildings/outpost/us_03omega_burn.png",
                             normalmap="models/buildings/outpost/us_03_nm.png")
            remove_subnodes(self.node,
                            ["command_post_misc", "command_post_roof",])
            self._hbx_commp.out = True
        if self._hbx_barrp.hitpoints <= 0 and not self._hbx_barrp.out:
            self.explode(offset=self._hbx_barrp.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Vec3(9.9, -19.7, 0.0),
                           spos1=None,
                           sclfact=1.0,
                           emradfact=1.0,
                           forcefact=1.0,
                           flsfact=1.0,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 4.0),
                           fdelay3=fx_uniform(1.0, 4.0),
                           fdelay4=fx_uniform(1.0, 4.0))
            texture_subnodes(self.node, ["barrack_post", "barrack_post_misc", "fence", "glass"],
                             texture="models/buildings/outpost/us_03omega_burn.png",
                             normalmap="models/buildings/outpost/us_03_nm.png")
            remove_subnodes(self.node,
                            ["barrack_post_misc", "fence",])
            self._hbx_heli.hitpoints = 0
            self._hbx_barrp.out = True
        if self._hbx_ulnkp.hitpoints <= 0 and not self._hbx_ulnkp.out:
            self.explode(offset=self._hbx_ulnkp.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Vec3(-29.1, -33.8, 0.0),
                           spos1=None,
                           sclfact=1.1,
                           emradfact=1.0,
                           forcefact=1.0,
                           flsfact=1.1,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 4.0),
                           fdelay3=fx_uniform(1.0, 4.0),
                           fdelay4=fx_uniform(1.0, 4.0))
            texture_subnodes(self.node, ["uplink_post", "uplink_post_misc", "glass"],
                             texture="models/buildings/outpost/us_03omega_burn.png",
                             normalmap="models/buildings/outpost/us_03_nm.png")
            remove_subnodes(self.node,
                            ["uplink_post_misc",])
            self._hbx_ulnkp.out = True
        if ((self._hbx_wallf.hitpoints <= 0 and not self._hbx_wallf.out) or
            (self._hbx_wallb.hitpoints <= 0 and not self._hbx_wallb.out) or
            (self._hbx_walll.hitpoints <= 0 and not self._hbx_walll.out) or
            (self._hbx_wallr.hitpoints <= 0 and not self._hbx_wallr.out)):
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=None,
                           spos1=None,
                           sclfact=1.1,
                           emradfact=1.0,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 2.0),
                           fdelay3=fx_uniform(1.0, 2.0),
                           fdelay4=fx_uniform(1.0, 2.0))
            texture_subnodes(self.node, ["wall_checkpoint", "wall_checkpoint_misc",],
                             texture="models/buildings/outpost/us_03omega_wall_burn.png",
                             normalmap="models/buildings/outpost/us_03_wall_nm.png",
                             clamp=False)
            remove_subnodes(self.node, ["wall_checkpoint_misc",])
            self.wall_down = True
            self._hbx_wallf.out = True
            self._hbx_wallb.out = True
            self._hbx_walll.out = True
            self._hbx_wallr.out = True
        if self._hbx_heli.hitpoints <= 0 and not self._hbx_heli.out:
            self.explode_minor(offset=self._hbx_heli.center)
            remove_subnodes(self.node, ["apache",])
            self._hbx_heli.out = True

        if self._hbx_commp.out and self._hbx_barrp.out and self._hbx_ulnkp.out:
            texture_subnodes(self.node, ["wall_checkpoint", "wall_checkpoint_misc",],
                             texture="models/buildings/outpost/us_03omega_wall_burn.png",
                             normalmap="models/buildings/outpost/us_03_wall_nm.png",
                             clamp=False)
            remove_subnodes(self.node,
                            ["glass",])
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=None,
                           spos1=Vec3(0.0, 0.0, 0.0),
                           sclfact=1.8,
                           emradfact=1.1,
                           forcefact=1.0,
                           slsfact=1.0,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 4.0),
                           fdelay3=fx_uniform(1.0, 4.0),
                           fdelay4=fx_uniform(1.0, 4.0))
            self._failure_full = True

        if self._failure_full:
            self.set_shotdown(3.0)

        return False


class PowgeneratorRussian1 (Building):

    species = "powgenerator-russian-1"
    basesink = 0.0
    strength = 30
    minhitdmg = 0
    maxhitdmg = 5
    rcs = 0.0

    #glowmap = "models/buildings/powerplant/sov_powergenerator_1_gw.png"
    #glossmap = "models/buildings/powerplant/sov_powergenerator_1_gls.png"
    destfirepos = None
    destoffparts = ["pwg_misc"]
    desttextures = ["models/buildings/powerplant/sov_powergenerator_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None, type="two"):

        if type == "two":
            self.hitboxdata=[(Point3(0.0, 0.2, 2.5), 6.5, 7.7, 2.5)]
            self.modelpath=[("models/buildings/powerplant/sov_powergenerator2x_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                            ("models/buildings/powerplant/sov_powergenerator2x_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
        elif type == "four":
            self.hitboxdata=[(Point3(0.0, 0.2, 2.5), 14.5, 7.7, 2.5)]
            self.modelpath=[("models/buildings/powerplant/sov_powergenerator4x_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                            ("models/buildings/powerplant/sov_powergenerator4x_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class OilGasStorage1 (Building):

    species = "oil-gas-storage-1"
    basesink = 0.0
    strength = 640
    minhitdmg = 1
    maxhitdmg = 220
    rcs = 1.0
    hitboxdata = [(Point3(-12.3, -1.0, 11.1), 21.5, 21.5, 11.1),
                  (Point3( -1.4, 41.8,  5.4), 47.5, 14.6,  5.4),
                  (Point3(  9.7,-48.9,  5.4), 30.8, 14.6,  5.4),
                  (Point3( 36.0, -4.4,  8.5),  8.6, 17.5,  8.5),
                  (Point3(-30.9,-34.4,  5.3),  6.0, 11.3,  5.3),
                  (Point3( 44.8,-53.6,  6.5),  4.2, 10.8,  6.5),
                  (Point3( 17.5, 60.3,  5.3),  5.4,  2.7,  5.3),
                  (Point3( -3.8, 60.4,  3.9), 10.8,  4.0,  3.9),
                  (Point3( -3.7, 60.2, 37.4),  1.8,  1.8, 29.5),
                  (Point3(  3.2, 60.2, 37.4),  1.8,  1.8, 29.5)]
    modelpath = [("models/buildings/oil-gas/oil_gas_storage_1.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/oil-gas/oil_gas_storage_1-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/oil-gas/oil_gas_storage_1_gw.png"
    #glossmap = "models/buildings/oil-gas/oil_gas_storage_1_gls.png"
    destfirepos = Vec3(-12.3, -1.0, 2.0)
    destoffparts = ["ogs1_roofs", "ogs1_misc"]
    desttextures = ["models/buildings/oil-gas/oil_gas_storage_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class FuelTank1 (Building):

    species = "fueltank-1"
    basesink = 0.0
    strength = 15
    minhitdmg = 0
    maxhitdmg = 2
    rcs = 0.0
    hitboxdata = [(Point3(2.7, -0.4, 4.2), 14.1, 11.6, 4.2)]
    modelpath = [("models/buildings/oil-gas/fuel_tank_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/oil-gas/fuel_tank_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/oil-gas/fuel_tank_1_gw.png"
    #glossmap = "models/buildings/oil-gas/fuel_tank_1_gls.png"
    destfirepos = Vec3(0.0, 0.0, 4.2)
    destoffparts = ["flt_misc", "flt_body_part"]
    desttextures = ["models/buildings/oil-gas/fuel_tank_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)


class Banner1 (Building):

    species = "banner-1"
    basesink = 0.0
    strength = 5
    minhitdmg = 0
    maxhitdmg = 1
    rcs = 0.0
    hitboxdata = [(Point3(0.0, 0.0, 1.0), 21.0)]
    modelpath = [("models/buildings/flag/banner_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/flag/banner_1-3.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/flag/banner_1_gw.png"
    #glossmap = "models/buildings/flag/banner_1_gls.png"
    destoffparts = ["banner"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None, burns=False):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage, burns=burns)


class Fence1 (Building):

    species = "fence-1"
    basesink = 0.0
    strength = 0
    minhitdmg = 0
    maxhitdmg = 0
    rcs = 0.0
    hitboxdata = None
    modelpath = [("models/buildings/misc/fence_1.egg", BUILDING_SMALL_LOD_DIST_FULL),
                 ("models/buildings/misc/fence_1.egg", BUILDING_SMALL_LOD_DIST_3)]
    #glowmap = "models/buildings/misc/fence_1_gw.png"
    #glossmap = "models/buildings/misc/fence_1_gls.png"
    destoffparts = None

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  transp=TransparencyAttrib.MDual,
                  pos=None, hpr=None, sink=None,
                  damage=None, burns=False):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=False,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage, burns=burns)
        if transp is not None:
            self.node.setTransparency(transp)
            # self.node.setBin("opaque", 0)


class Mansion1 (Building):

    species = "mansion-1"
    basesink = 0.0
    strength = 410
    minhitdmg = 0
    maxhitdmg = 90
    rcs = 0.0
    hitboxdata = [#House
                  (Point3(  3.25,  12.35, 9.10), 11.16, 11.70, 9.10),
                  (Point3( -0.45,  15.64, 6.12), 31.00,  8.41, 6.12),
                  (Point3(-22.82,  -2.41, 3.91), 10.29, 11.56, 3.91),
                  #Wall
                  (Point3(-43.22,   5.33, 2.45),  1.05, 45.86, 2.45),
                  (Point3( 43.36,   5.33, 2.45),  1.05, 45.86, 2.45),
                  (Point3(  0.00, -39.34, 2.45), 44.20,  1.05, 2.45),
                  (Point3(  0.00,  50.10, 2.45), 44.20,  1.05, 2.45)]
    modelpath = [("models/buildings/house/mansion_1.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/house/mansion_1-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/mansion/mansion_1_gw.png"
    #glossmap = "models/buildings/mansion/mansion_1_gls.png"
    destfirepos = Vec3(1.0, 9.0, 7.5)
    destoffparts = ["h_roof", "h_misc_1", "h_misc_2", "glass"]
    desttextures = ["models/buildings/house/mansion_1_burn.png"]

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        texture_subnodes(self.node, ["h_wall",],
                         texture="models/buildings/house/mansion_1_wall_tex.png",
                         normalmap="models/buildings/house/mansion_1_wall_nm.png",
                         glowmap=None, glossmap=None, clamp=False, alpha=False)
        self._burn_set = False


    def collide (self, obody, chbx, cpos):

        inert = Building.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if not self._burn_set and self.damage >= self.strength:
            self._burn_set = True
            texture_subnodes(self.node, ["h_wall",],
                             texture="models/buildings/house/mansion_1_wall_burn.png",
                             normalmap="models/buildings/house/mansion_1_wall_nm.png",
                             glowmap=None, glossmap=None, clamp=False, alpha=False)

        return False


class PrisonEastern1 (Building):

    species = "prison-eastern-1"
    basesink = 0.0
    strength = 40000
    minhitdmg = None
    maxhitdmg = None
    rcs = 0.0

    hitboxdata = [
        HitboxData(name="prsn",
                   colldata=[(Point3(  0.00, 23.37, 8.31), 18.59,  5.97, 8.31),
                             (Point3(-15.72, 10.86, 8.10),  5.87, 18.59, 8.10),
                             (Point3( 15.72, 10.85, 8.10),  5.87, 18.59, 8.10)],
                   longdes=_("prison building"), shortdes=_("PRSN"),
                   selectable=True),
        HitboxData(name="wallf",
                   colldata=[(Point3(-21.00, -33.60, 3.01), 18.40, 1.00, 3.01),
                             (Point3( 21.00, -33.60, 3.01), 18.40, 1.00, 3.01)],
                   longdes=_("prison wall front"), shortdes=_("WALLF"),
                   selectable=True),
        HitboxData(name="wallb",
                   colldata=[(Point3(0.00, 29.81, 3.01), 39.50,  1.00, 3.01)],
                   longdes=_("prison wall back"), shortdes=_("WALLB"),
                   selectable=True),
        HitboxData(name="walll",
                   colldata=[(Point3(-39.21, -1.89, 3.01),  1.00, 32.00, 3.01)],
                   longdes=_("prison wall left"), shortdes=_("WALLL"),
                   selectable=True),
        HitboxData(name="wallr",
                   colldata=[(Point3( 39.21, -1.89, 3.01),  1.00, 32.00, 3.01)],
                   longdes=_("prison wall right"), shortdes=_("WALLR"),
                   selectable=True),
        HitboxData(name="wtow1",
                   colldata=[(Point3(-30.19, -27.92, 7.02), 3.66, 3.16, 6.98)],
                   longdes=_("watchtower 1"), shortdes=_("WTOW1"),
                   selectable=False),
        HitboxData(name="wtow2",
                   colldata=[(Point3( 29.97, -27.92, 7.02), 3.66, 3.16, 6.98)],
                   longdes=_("watchtower 2"), shortdes=_("WTOW2"),
                   selectable=False),
    ]
    modelpath = [("models/buildings/misc/prison_1.egg", BUILDING_MEDIUM_LOD_DIST_FULL),
                 ("models/buildings/misc/prison_1-3.egg", BUILDING_MEDIUM_LOD_DIST_3)]
    #glowmap = "models/buildings/misc/prison_1_gw.png"
    #glossmap = "models/buildings/misc/prison_1_gls.png"
    #destoffparts = []

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        texture_subnodes(self.node, ["prison_wall", "prison_wall_misc",],
                         texture="models/buildings/misc/prison_1_wall_tex.png",
                         normalmap="models/buildings/misc/prison_1_wall_nm.png",
                         glowmap=None, glossmap=None, clamp=False, alpha=False)
        texture_subnodes(self.node, ["prison_wire",],
                         texture="models/buildings/misc/prison_1_wall_tex.png",
                         clamp=False, alpha=True)

        self._hbx_prsn.hitpoints = 720
        self._hbx_wallf.hitpoints = 260
        self._hbx_wallb.hitpoints = 260
        self._hbx_walll.hitpoints = 260
        self._hbx_wallr.hitpoints = 260
        self._hbx_wtow1.hitpoints = 110
        self._hbx_wtow2.hitpoints = 110

        self._hbx_prsn.minhitdmg = 14
        self._hbx_wallf.minhitdmg = 2
        self._hbx_wallb.minhitdmg = 2
        self._hbx_walll.minhitdmg = 2
        self._hbx_wallr.minhitdmg = 2
        self._hbx_wtow1.minhitdmg = 0
        self._hbx_wtow2.minhitdmg = 0

        self._hbx_prsn.maxhitdmg = 440
        self._hbx_wallf.maxhitdmg = 180
        self._hbx_wallb.maxhitdmg = 180
        self._hbx_walll.maxhitdmg = 180
        self._hbx_wallr.maxhitdmg = 180
        self._hbx_wtow1.maxhitdmg = 45
        self._hbx_wtow2.maxhitdmg = 45

        self._hbx_prsn.out = False
        self._hbx_wallf.out = False
        self._hbx_wallb.out = False
        self._hbx_walll.out = False
        self._hbx_wallr.out = False
        self._hbx_wtow1.out = False
        self._hbx_wtow2.out = False

        self.wall_down = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_prsn.hitpoints <= 0 and not self._hbx_prsn.out:
            self.explode(offset=self._hbx_prsn.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=Vec3(4.0, 18.0, 8.0),
                           spos1=Vec3(0.0, 0.0, 0.0),
                           sclfact=0.8,
                           emradfact=0.7,
                           flsfact=0.8,
                           slsfact=0.8,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 4.0),
                           fdelay3=fx_uniform(1.0, 4.0),
                           fdelay4=fx_uniform(1.0, 4.0))
            texture_subnodes(self.node, ["prison", "prison_misc", "prison_doors", "prison_roof", "glass", "main_gate",
                                         "wt_base_1", "wt_floor_1", "wt_hut_1", "wt_door_1", "wt_base_2", "wt_floor_2",
                                         "wt_hut_2", "wt_door_2",],
                             texture="models/buildings/misc/prison_1_burn.png")
            texture_subnodes(self.node, ["prison_wall", "prison_wire", "prison_wall_misc",],
                             texture="models/buildings/misc/prison_1_wall_burn.png",
                             clamp=False)
            remove_subnodes(self.node,
                            ["prison_misc", "prison_doors", "prison_roof", "glass", "main_gate", "prison_wire",
                             "prison_wall_misc", "wt_hut1",])
            self._hbx_prsn.out = True
            self._failure_full = True
        if ((self._hbx_wallf.hitpoints <= 0 and not self._hbx_wallf.out) or
            (self._hbx_wallb.hitpoints <= 0 and not self._hbx_wallb.out) or
            (self._hbx_walll.hitpoints <= 0 and not self._hbx_walll.out) or
            (self._hbx_wallr.hitpoints <= 0 and not self._hbx_wallr.out)):
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=None,
                           spos1=None,
                           sclfact=0.7,
                           emradfact=0.6,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 2.0),
                           fdelay3=fx_uniform(1.0, 2.0),
                           fdelay4=fx_uniform(1.0, 2.0))
            texture_subnodes(self.node, ["prison_wall", "prison_wire", "prison_wall_misc",],
                             texture="models/buildings/misc/prison_1_wall_burn.png",
                             clamp=False)
            remove_subnodes(self.node, ["prison_wall_misc", "prison_wire", "main_gate", "glass",])
            self.wall_down = True
            self._hbx_wallf.out = True
            self._hbx_wallb.out = True
            self._hbx_walll.out = True
            self._hbx_wallr.out = True
        if self._hbx_wtow1.hitpoints <= 0 and not self._hbx_wtow1.out:
            self.explode_minor(offset=self._hbx_wtow1.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=None,
                           spos1=Vec3(-30.4, -28.0, 0.0),
                           sclfact=0.5,
                           emradfact=0.3,
                           flsfact=0.6,
                           slsfact=0.6,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 2.0),
                           fdelay3=fx_uniform(1.0, 2.0),
                           fdelay4=fx_uniform(1.0, 2.0))
            texture_subnodes(self.node, ["wt_base_1", "wt_floor_1", "wt_hut_1", "wt_door_1",],
                             texture="models/buildings/misc/prison_1_burn.png")
            remove_subnodes(self.node, ["wt_hut_1", "wt_door_1",])
            self._hbx_wtow1.out = True
        if self._hbx_wtow2.hitpoints <= 0 and not self._hbx_wtow2.out:
            self.explode_minor(offset=self._hbx_wtow2.center)
            fire_n_smoke_3(parent=self, store=self.damage_trails,
                           fpos1=None,
                           spos1=Vec3(30.0, -28.0, 0.0),
                           sclfact=0.5,
                           emradfact=0.3,
                           flsfact=0.6,
                           slsfact=0.6,
                           fdelay1=fx_uniform(0.0, 1.0),
                           fdelay2=fx_uniform(1.0, 3.0),
                           fdelay3=fx_uniform(1.0, 3.0),
                           fdelay4=fx_uniform(1.0, 3.0))
            texture_subnodes(self.node, ["wt_base_2", "wt_floor_2", "wt_hut_2", "wt_door_2",],
                             texture="models/buildings/misc/prison_1_burn.png")
            remove_subnodes(self.node, ["wt_hut_2", "wt_door_2", "wt_floor_2"])
            self._hbx_wtow2.out = True

        if self._failure_full:
            self.set_shotdown(3.0)

        return False


class FlakTowerL70 (Building):

    species = "flaktowerl70"
    basesink = 0.0
    strength = 150.0
    minhitdmg = 10.0
    maxhitdmg = 100.0
    rcs = 0.01
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 10.0)]
    modelpath = "sphere1280.egg"

    def __init__ (self, world, name, side, texture=None, normalmap=None,
                  pos=None, hpr=None, sink=None,
                  damage=None):

        Building.__init__(self, world=world, name=name, side=side,
                          texture=texture, normalmap=normalmap, clamp=True,
                          pos=pos, hpr=hpr, sink=sink,
                          damage=damage)

        turret1 = TurretL70(world=world, name="top", side=side,
                            hcenter=0, harc=360, pcenter=30, parc=80,
                            pos=Point3(0.0, 0.0, 10.0),
                            parent=self)
        self.turrets.append(turret1)


