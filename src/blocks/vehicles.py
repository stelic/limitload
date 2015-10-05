# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Vec3, Point3

from src.blocks.weapons import TurretPkm, N2a38m
from src.core.body import Body, HitboxData
from src.core.debris import GroundBreakupData
from src.core.effect import fire_n_smoke_2
from src.core.misc import rgba, remove_subnodes, texture_subnodes
from src.core.transl import *
from src.core.turret import CustomTurret
from src.core.vehicle import Vehicle


def breakup_small (handle, prob=0.5):
    return GroundBreakupData(handle=handle, breakprob=prob,
                             duration=(8, 10),
                             offdir=(-180, 180, 20, 70), offspeed=(8, 16),
                             tumbledir=(-180, 180, -90, 90), tumblespeeddeg=(-500, 500),
                             normrestfac=0.2, tangrestfac=0.7, tumblerestfac=0.2)


def breakup_large (handle, prob=0.5):
    return GroundBreakupData(handle=handle, breakprob=prob,
                             duration=None,
                             offdir=(-180, 180, 5, 15), offspeed=(7, 12),
                             tumbledir=(-180, 180, 0, 40), tumblespeeddeg=(-250, 250),
                             normrestfac=0.1, tangrestfac=0.3, tumblerestfac=0.1,
                             keeptogether=True,
                             traildurfac=1e6, traillifespan=0.45,
                             trailthickness=4.0, trailspacing=0.2,
                             trailtcol=0.5, trailfire=True)

def breakup_large_low (handle, prob=0.5, elev=0.0):
    return GroundBreakupData(handle=handle, breakprob=prob,
                             duration=None,
                             offdir=(-180, 180, 50, 70), offspeed=1.5,
                             tumbledir=(-180, 180, 70, 85), tumblespeeddeg=(-150, 150),
                             normrestfac=0.0, tangrestfac=0.0, tumblerestfac=0.0,
                             fixelev=elev, keeptogether=True)


class Ural375 (Vehicle):

    species = "ural375"
    longdes = _("Ural-375")
    shortdes = _("Ural-375")

    maxspeed = 30.0
    maxslope = radians(30.0)
    maxturnrate = radians(90.0)
    maxthracc = 2.0
    maxvdracc = 5.0
    strength = 16.0
    minhitdmg = 0.0
    maxhitdmg = 10.0
    rcs = 0.005
    # hitboxdata = [(Point3(0.0, 2.2, 1.5), 1.6),
                  # (Point3(0.0, -1.4, 1.7), 1.8)]
    hitboxdata = [(Point3(0.0, 0.3, 1.5), 1.4, 4.3, 1.5)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/ural375/ural375.egg"
    modelpath = ["models/vehicles/ural375/ural375-1.egg",
                 "models/vehicles/ural375/ural375-2.egg",
                 "models/vehicles/ural375/ural375-3.egg"]
    shdmodelpath = "models/vehicles/ural375/ural375-shadow.egg"
    normalmap = "models/vehicles/ural375/ural375_nm.png"
    glossmap = "models/vehicles/ural375/ural375_gls.png"
    engsoundname = "engine-truck-1"

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None,
                  noawning=False):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)

        if noawning:
            for model in self.models:
                remove_subnodes(model, ("awning",))
            if base.with_world_shadows:
                remove_subnodes(self.shadow_node, ("awning",))


class Uaz469 (Vehicle):

    species = "uaz469"
    longdes = _("UAZ-469")
    shortdes = _("UAZ-469")

    maxspeed = 35.0
    maxslope = radians(30.0)
    maxturnrate = radians(90.0)
    maxthracc = 6.0
    maxvdracc = 2.0
    strength = 16.0
    minhitdmg = 0.0
    maxhitdmg = 10.0
    rcs = 0.002
    # hitboxdata = [(Point3(0.0, -1.0, 1.0), 1.0),
                  # (Point3(0.0,  1.0, 1.0), 1.0)]
    hitboxdata = [(Point3(0.0, 0.0, 1.1), 1.0, 2.1, 1.15)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/uaz469/uaz469.egg"
    modelpath = ["models/vehicles/uaz469/uaz469-1.egg",
                 "models/vehicles/uaz469/uaz469-2.egg",
                 "models/vehicles/uaz469/uaz469-3.egg"]
    shdmodelpath = "models/vehicles/uaz469/uaz469-shadow.egg"
    normalmap = "models/vehicles/uaz469/uaz469_nm.png"
    glossmap = "models/vehicles/uaz469/uaz469_gls.png"
    engsoundname = ""

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None,
                  machinegun=False):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)

        if machinegun:
            # Turrets.
            turret1 = TurretPkm(world=world, name="machinegun", side=side,
                                hcenter=0, harc=360, pcenter=15, parc=(-15, 75),
                                pos=Point3(-0.004, -0.225, 2.244),
                                parent=self, cnammo=[200], cnreloads=[4],
                                cnrelrate=[10.0])
            self.turrets.append(turret1)


class Uaz469mod (Vehicle):

    species = "uaz469mod"
    longdes = _("UAZ-469 modified")
    shortdes = _("UAZ-469(m)")

    maxspeed = 40.0
    maxslope = radians(35.0)
    maxturnrate = radians(100.0)
    maxthracc = 7.0
    maxvdracc = 2.0
    strength = 12.0
    minhitdmg = 0.0
    maxhitdmg = 8.0
    rcs = 0.002
    # hitboxdata = [(Point3(0.0, -1.0, 1.0), 1.0),
                  # (Point3(0.0,  1.0, 1.0), 1.0)]
    hitboxdata = [(Point3(0.0, 0.0, 1.1), 1.0, 2.1, 1.15)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/uaz469/uaz469.egg"
    modelpath = ["models/vehicles/uaz469/uaz469mod-1.egg",
                 "models/vehicles/uaz469/uaz469mod-2.egg",
                 "models/vehicles/uaz469/uaz469-3.egg"]
    shdmodelpath = "models/vehicles/uaz469/uaz469mod-shadow.egg"
    normalmap = "models/vehicles/uaz469/uaz469_nm.png"
    glossmap = "models/vehicles/uaz469/uaz469_gls.png"
    engsoundname = ""

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None,
                  turret=True):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)

        # Turrets.
        if turret:
            turret1 = TurretPkm(world=world, name="machinegun", side=side,
                                hcenter=0, harc=360, pcenter=15, parc=(-15, 75),
                                pos=Point3(-0.004, -0.225, 2.244),
                                hpr=Vec3(0,0,0),
                                parent=self, cnammo=[200],
                                cnreloads=[4], cnrelrate=[10.0])
            self.turrets.append(turret1)


class T80 (Vehicle):

    species = "t80"
    longdes = _("T-80")
    shortdes = _("T-80")

    maxspeed = 20.0
    maxslope = radians(40.0)
    maxturnrate = radians(90.0)
    maxthracc = 2.0
    maxvdracc = 5.0
    strength = 50.0
    minhitdmg = 15.0
    maxhitdmg = 40.0
    rcs = 0.005
    # hitboxdata = [(Point3(0.0, 1.4, 1.2), 1.8),
                  # (Point3(0.0, -2.0, 1.2), 1.8)]
    hitboxdata = [(Point3(0.0, -0.2, 1.4), 2.2, 3.8, 1.4)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/t80/t80.egg"
    modelpath = ["models/vehicles/t80/t80-1.egg",
                 "models/vehicles/t80/t80-2.egg",
                 "models/vehicles/t80/t80-3.egg"]
    shdmodelpath = "models/vehicles/t80/t80-shadow.egg"
    #normalmap = "models/vehicles/t80/t80_nm.png"
    #glossmap = "models/vehicles/t80/t80_gls.png"
    trkspdfac = [0.090]
    engsoundname = ""

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class Tunguska (Vehicle):

    species = "tunguska"
    longdes = _("9K22 Tunguska")
    shortdes = _("9K22")

    maxspeed = 20.0
    maxslope = radians(40.0)
    maxturnrate = radians(90.0)
    maxthracc = 2.0
    maxvdracc = 5.0
    strength = 15.0
    minhitdmg = 1.0
    maxhitdmg = 6.0
    rcs = 0.005
    # hitboxdata = [(Point3(0.0, 1.4, 1.2), 1.8),
                  # (Point3(0.0, -2.0, 1.2), 1.8)]
    hitboxdata = [(Point3(0.0, 0.0, 2.0), 2.0, 4.1, 2.0)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/tunguska/tunguska.egg"
    modelpath = ["models/vehicles/tunguska/tunguska-1.egg",
                 "models/vehicles/tunguska/tunguska-2.egg",
                 "models/vehicles/tunguska/tunguska-3.egg"]
    sdmodelpath = "models/vehicles/tunguska/tunguska-shotdown.egg"
    shdmodelpath = "models/vehicles/tunguska/tunguska-shadow.egg"
    normalmap = "models/vehicles/tunguska/tunguska_nm.png"
    glossmap = "models/vehicles/tunguska/tunguska_gls.png"
    trkspdfac = [0.090]
    engsoundname = ""
    breakupdata = [
        breakup_small("turret_radar", prob=0.8),
        breakup_small("turret_elev_left", prob=0.3),
        breakup_small("turret_elev_right", prob=0.3),
        breakup_large_low("turret_azim", prob=0.7, elev=2.3),
        breakup_large("turret_azim", prob=0.3),
        breakup_small("axle2_left", prob=0.5),
        breakup_small("axle4_left", prob=0.5),
        breakup_small("axle4_right", prob=0.5),
        breakup_small("axle5_left", prob=0.5),
        breakup_small("axle6_left", prob=0.5),
        breakup_small("axle6_right", prob=0.5),
        breakup_small("axle7_right", prob=0.5),
        breakup_small("hatch", prob=0.6),
    ]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None,
                  cnammo=[2000, 2000]):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)

        turret = CustomTurret(parent=self,
                              world=world, name=("%s-turret" % name), side=side,
                              turnrate=radians(90.0), elevrate=radians(90.0),
                              hcenter=0, harc=360, pcenter=0, parc=(-10, 80),
                              modelpath=(self.node, "turret"),
                              texture=texture, normalmap=self.normalmap,
                              glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(turret)

        cannon1 = N2a38m(parent=turret,
                         mpos=Point3(1.00, 2.35, 2.73),
                         mhpr=Vec3(0.0, 0.0, 0.0),
                         mltpos=Point3(1.90, 5.74, 1.0),
                         ammo=cnammo[0], viseach=(10, 0))
        turret.add_cannon(cannon1)

        cannon2 = N2a38m(parent=turret,
                         mpos=Point3(-1.00, 2.35, 2.73),
                         mhpr=Vec3(0.0, 0.0, 0.0),
                         mltpos=Point3(-1.90, 5.74, 1.0),
                         ammo=cnammo[1], viseach=(10, 5))
        turret.add_cannon(cannon2)


class Btr80 (Vehicle):

    species = "btr80"
    longdes = _("BTR-80")
    shortdes = _("BTR-80")

    maxspeed = 25.0
    maxslope = radians(30.0)
    maxturnrate = radians(90.0)
    maxthracc = 3.0
    maxvdracc = 4.0
    strength = 20.0
    minhitdmg = 2.0
    maxhitdmg = 12.0
    rcs = 0.004
    # hitboxdata = [(Point3(0.0, 1.4, 1.2), 1.8),
                  # (Point3(0.0, -2.0, 1.2), 1.8)]
    hitboxdata = [(Point3(0.0, 0.0, 1.2), 1.6, 3.9, 1.2)]
    groundcontact = [Point3(0.0, 2.11, 0.0),
                     Point3(-1.21, -2.41, 0.0),
                     Point3(+1.21, -2.41, 0.0)]
    fmodelpath = "models/vehicles/btr80/btr80.egg"
    modelpath = ["models/vehicles/btr80/btr80-1.egg",
                 "models/vehicles/btr80/btr80-2.egg",
                 "models/vehicles/btr80/btr80-3.egg"]
    shdmodelpath = "models/vehicles/btr80/btr80-shadow.egg"
    normalmap = "models/vehicles/btr80/btr80_nm.png"
    glossmap = "models/vehicles/btr80/btr80_gls.png"
    engsoundname = "engine-transporter-1"

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class Abrams (Vehicle):

    species = "abrams"
    longdes = _("M1 Abrams")
    shortdes = _("M1")

    maxspeed = 20.0
    maxslope = radians(30.0)
    maxturnrate = radians(70.0)
    maxthracc = 1.5
    maxvdracc = 7.0
    strength = 70.0
    minhitdmg = 15.0
    maxhitdmg = 50.0
    rcs = 0.008
    # hitboxdata = [(Point3(0.0, 1.4, 1.2), 1.8),
                  # (Point3(0.0, -2.0, 1.2), 1.8)]
    hitboxdata = [(Point3(0.0, -0.1, 1.3), 2.8, 4.0, 1.3)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/abrams/abrams.egg"
    modelpath = ["models/vehicles/abrams/abrams-1.egg",
                 "models/vehicles/abrams/abrams-2.egg",
                 "models/vehicles/abrams/abrams-3.egg"]
    sdmodelpath = "models/vehicles/abrams/abrams-shotdown.egg"
    shdmodelpath = "models/vehicles/abrams/abrams-shadow.egg"
    normalmap = "models/vehicles/abrams/abrams_nm.png"
    glossmap = "models/vehicles/abrams/abrams_gls.png"
    trkspdfac = [0.040]
    engsoundname = ""
    breakupdata = [
        breakup_small("turret_elev", prob=0.3),
        breakup_large_low("turret_azim", prob=0.7, elev=1.9),
        breakup_large("turret_azim", prob=0.3),
        breakup_small("axle3_left", prob=0.5),
        breakup_small("axle4_right", prob=0.5),
        breakup_small("axle6_left", prob=0.5),
        breakup_small("axle6_right", prob=0.5),
        breakup_small("axle7_left", prob=0.5),
        breakup_small("axle8_left", prob=0.5),
        breakup_small("axle8_right", prob=0.5),
    ]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class Bradley (Vehicle):

    species = "bradley"
    longdes = _("M2 Bradley")
    shortdes = _("M2")

    maxspeed = 20.0
    maxslope = radians(40.0)
    maxturnrate = radians(90.0)
    maxthracc = 2.0
    maxvdracc = 5.0
    strength = 30.0
    minhitdmg = 2.0
    maxhitdmg = 20.0
    rcs = 0.005
    hitboxdata = [(Point3(0.0, 0.1, 1.8), 1.8, 3.8, 1.8)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/bradley/bradley.egg"
    modelpath = ["models/vehicles/bradley/bradley-1.egg",
                 "models/vehicles/bradley/bradley-2.egg",
                 "models/vehicles/bradley/bradley-3.egg"]
    sdmodelpath = "models/vehicles/bradley/bradley-shotdown.egg"
    shdmodelpath = "models/vehicles/bradley/bradley-shadow.egg"
    normalmap = "models/vehicles/bradley/bradley_nm.png"
    glossmap = "models/vehicles/bradley/bradley_gls.png"
    trkspdfac = [0.040]
    engsoundname = ""
    breakupdata = [
        breakup_small("turret_elev", prob=0.4),
        breakup_large_low("turret_azim", prob=0.6, elev=2.5),
        breakup_large("turret_azim", prob=0.4),
        breakup_small("axle4_left", prob=0.5),
        breakup_small("axle4_right", prob=0.5),
        breakup_small("axle5_left", prob=0.5),
        breakup_small("axle5_right", prob=0.5),
        breakup_small("axle7_left", prob=0.5),
        breakup_small("axle7_right", prob=0.5),
        breakup_small("door", prob=0.7),
    ]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class Bradleyaa (Vehicle):

    species = "bradleyaa"
    longdes = _("M2(AA)")
    shortdes = _("M2 Bradley Anti-Aircraft")

    maxspeed = 20.0
    maxslope = radians(40.0)
    maxturnrate = radians(90.0)
    maxthracc = 2.0
    maxvdracc = 5.0
    strength = 30.0
    minhitdmg = 2.0
    maxhitdmg = 20.0
    rcs = 0.005
    hitboxdata = [(Point3(0.0, 0.1, 1.8), 1.8, 3.8, 1.8)]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    fmodelpath = "models/vehicles/bradley/bradleyaa.egg"
    modelpath = ["models/vehicles/bradley/bradleyaa-1.egg",
                 "models/vehicles/bradley/bradleyaa-2.egg",
                 "models/vehicles/bradley/bradley-3.egg"]
    shdmodelpath = "models/vehicles/bradley/bradleyaa-shadow.egg"
    normalmap = "models/vehicles/bradley/bradley_nm.png"
    glossmap = "models/vehicles/bradley/bradley_gls.png"
    trkspdfac = [0.040]
    engsoundname = ""

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class Stryker (Vehicle):

    species = "stryker"
    longdes = _("M1126 Stryker")
    shortdes = _("M1126")

    maxspeed = 27.0
    maxslope = radians(30.0)
    maxturnrate = radians(90.0)
    maxthracc = 3.0
    maxvdracc = 4.0
    strength = 20.0
    minhitdmg = 2.0
    maxhitdmg = 12.0
    rcs = 0.004
    hitboxdata = [(Point3(0.0, 0.4, 1.4), 1.4, 3.6, 1.4)]
    groundcontact = [Point3(0.0, 2.11, 0.0),
                     Point3(-1.21, -2.41, 0.0),
                     Point3(+1.21, -2.41, 0.0)]
    fmodelpath = "models/vehicles/stryker/stryker.egg"
    modelpath = ["models/vehicles/stryker/stryker-1.egg",
                 "models/vehicles/stryker/stryker-2.egg",
                 "models/vehicles/stryker/stryker-3.egg"]
    shdmodelpath = "models/vehicles/stryker/stryker-shadow.egg"
    normalmap = "models/vehicles/stryker/stryker_nm.png"
    glossmap = "models/vehicles/stryker/stryker_gls.png"
    engsoundname = "engine-transporter-1"

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)


class TankCruiser (Vehicle):

    species = "tankcruiser"
    longdes = _("TK-1")
    shortdes = _("TK-1")

    maxspeed = 3.0
    maxslope = radians(10.0)
    maxturnrate = radians(20.0)
    maxthracc = 0.5
    maxvdracc = 4.0
    strength = 100000
    minhitdmg = None
    maxhitdmg = None
    rcs = 0.005
    hitboxdata = [
        #HULL
        HitboxData(name="hull",
                   colldata=[#Front/middle/back armor
                             (Point3(0.00,   1.67,  9.05), 15.41, 46.34,  9.05),
                             (Point3(0.00,  17.55, 10.79),  7.34, 27.46, 10.79),
                             (Point3(0.00, -26.61, 11.82),  9.98, 16.67, 11.82),
                             #Left & right side armor
                             (Point3(-21.01, 3.21, 10.61), 5.58, 40.09, 1.80),
                             (Point3(+21.01, 3.21, 10.61), 5.58, 40.09, 1.80),
                             #Left wheel armor (lhull)
                             (Point3(-22.20, 3.17, 4.39), 5.10, 40.86, 4.36)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="rhull",
                   colldata=[(Point3(-22.20, 3.17, 4.39), 5.10, 40.86, 4.36)],
                   longdes=_("rhull"), shortdes=_("RHULL"),
                   selectable=False),
        #TURRETS
        HitboxData(name="turm",
                   colldata=[(Point3(0.00, 18.86, 26.82), 8.23, 13.13, 5.09)],
                   longdes=_("turret main"), shortdes=_("TURM"),
                   selectable=False),
        HitboxData(name="tursl",
                   colldata=[(Point3(-11.56, 33.27, 20.12), 4.33, 5.36, 2.03)],
                   longdes=_("turret side left"), shortdes=_("TURSL"),
                   selectable=False),
        HitboxData(name="tursr",
                   colldata=[(Point3(+11.56, 33.27, 20.12), 4.33, 5.36, 2.03)],
                   longdes=_("turret side right"), shortdes=_("TURSR"),
                   selectable=False),
        HitboxData(name="turaa1",
                   colldata=[(Point3(0.0, -32.8, 23.2), 2.6)],
                   longdes=_("turret anti air 1"), shortdes=_("TURAA1"),
                   selectable=False),
        HitboxData(name="turaa5",
                   colldata=[(Point3(17.3, 3.1, 14.2), 2.6)],
                   longdes=_("turret anti air 5"), shortdes=_("TURAA5"),
                   selectable=False),
        HitboxData(name="turaa6",
                   colldata=[(Point3(-17.3, 3.1, 14.2), 2.6)],
                   longdes=_("turret anti air 6"), shortdes=_("TURAA6"),
                   selectable=False),
        #WHEELS
        HitboxData(name="wheel1",
                   colldata=[(Point3(22.18, 39.03, 3.89), 4.0)],
                   longdes=_("wheel 1"), shortdes=_("WHEEL1"),
                   selectable=False),
        HitboxData(name="wheel2",
                   colldata=[(Point3(22.18, 30.34, 3.89), 4.0)],
                   longdes=_("wheel 2"), shortdes=_("WHEEL2"),
                   selectable=False),
        HitboxData(name="wheel3",
                   colldata=[(Point3(22.18, 21.14, 3.89), 4.0)],
                   longdes=_("wheel 3"), shortdes=_("WHEEL3"),
                   selectable=False),
        HitboxData(name="wheel4",
                   colldata=[(Point3(22.18, 12.45, 3.89), 4.0)],
                   longdes=_("wheel 4"), shortdes=_("WHEEL4"),
                   selectable=False),
        HitboxData(name="wheel5",
                   colldata=[(Point3(22.18, -6.28, 3.89), 4.0)],
                   longdes=_("wheel 5"), shortdes=_("WHEEL5"),
                   selectable=False),
        HitboxData(name="wheel6",
                   colldata=[(Point3(22.18, -14.97, 3.89), 4.0)],
                   longdes=_("wheel 6"), shortdes=_("WHEEL6"),
                   selectable=False),
        HitboxData(name="wheel7",
                   colldata=[(Point3(22.18, -24.16, 3.89), 4.0)],
                   longdes=_("wheel 7"), shortdes=_("WHEEL7"),
                   selectable=False),
        HitboxData(name="wheel8",
                   colldata=[(Point3(22.18, -32.85, 3.89), 4.0)],
                   longdes=_("wheel 8"), shortdes=_("WHEEL8"),
                   selectable=False),
    ]
    groundcontact = [Point3(0.0, 2.75, 0.0),
                     Point3(-0.95, -1.35, 0.0),
                     Point3(+0.95, -1.35, 0.0)]
    modelpath = ["models/vehicles/tank-cruiser/tankcruiser.egg",
                 "models/vehicles/tank-cruiser/tankcruiser.egg",
                 "models/vehicles/tank-cruiser/tankcruiser.egg"]
    #normalmap = "models/vehicles/tank-cruiser/tankcruiser_nm.png"
    #glossmap = "models/vehicles/tank-cruiser/tankcruiser_gls.png"
    trkspdfac = [0.010, 0.010, 0.010]
    engsoundname = ""

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None,
                  nohullright=False, nohullleft=False):

        Vehicle.__init__(self, world=world, name=name, side=side,
                         texture=texture,
                         pos=pos, hpr=hpr, speed=speed, sink=sink,
                         damage=damage)

        self._hbx_hull.hitpoints = 3600
        self._hbx_rhull.hitpoints = 2400
        self._hbx_turm.hitpoints = 1300
        self._hbx_tursl.hitpoints = 700
        self._hbx_tursr.hitpoints = 700
        self._hbx_turaa1.hitpoints = 100
        self._hbx_turaa5.hitpoints = 100
        self._hbx_turaa6.hitpoints = 100
        self._hbx_wheel1.hitpoints = 120
        self._hbx_wheel2.hitpoints = 120
        self._hbx_wheel3.hitpoints = 120
        self._hbx_wheel4.hitpoints = 120
        self._hbx_wheel5.hitpoints = 120
        self._hbx_wheel6.hitpoints = 120
        self._hbx_wheel7.hitpoints = 120
        self._hbx_wheel8.hitpoints = 120

        self._hbx_hull.minhitdmg = 800
        self._hbx_rhull.minhitdmg = 600
        self._hbx_turm.minhitdmg = 200
        self._hbx_tursl.minhitdmg = 90
        self._hbx_tursr.minhitdmg = 90
        self._hbx_turaa1.minhitdmg = 1
        self._hbx_turaa5.minhitdmg = 1
        self._hbx_turaa6.minhitdmg = 1
        self._hbx_wheel1.minhitdmg = 20
        self._hbx_wheel2.minhitdmg = 20
        self._hbx_wheel3.minhitdmg = 20
        self._hbx_wheel4.minhitdmg = 20
        self._hbx_wheel5.minhitdmg = 20
        self._hbx_wheel6.minhitdmg = 20
        self._hbx_wheel7.minhitdmg = 20
        self._hbx_wheel8.minhitdmg = 20

        self._hbx_hull.maxhitdmg = 2400
        self._hbx_rhull.maxhitdmg = 1600
        self._hbx_turm.maxhitdmg = 850
        self._hbx_tursl.maxhitdmg = 300
        self._hbx_tursr.maxhitdmg = 300
        self._hbx_turaa1.maxhitdmg = 60
        self._hbx_turaa5.maxhitdmg = 60
        self._hbx_turaa6.maxhitdmg = 60
        self._hbx_wheel1.maxhitdmg = 110
        self._hbx_wheel2.maxhitdmg = 110
        self._hbx_wheel3.maxhitdmg = 110
        self._hbx_wheel4.maxhitdmg = 110
        self._hbx_wheel5.maxhitdmg = 110
        self._hbx_wheel6.maxhitdmg = 110
        self._hbx_wheel7.maxhitdmg = 110
        self._hbx_wheel8.maxhitdmg = 110

        self._hbx_hull.out = False
        self._hbx_rhull.out = False
        self._hbx_turm.out = False
        self._hbx_tursl.out = False
        self._hbx_tursr.out = False
        self._hbx_turaa1.out = False
        self._hbx_turaa5.out = False
        self._hbx_turaa6.out = False
        self._hbx_wheel1.out = False
        self._hbx_wheel2.out = False
        self._hbx_wheel3.out = False
        self._hbx_wheel4.out = False
        self._hbx_wheel5.out = False
        self._hbx_wheel6.out = False
        self._hbx_wheel7.out = False
        self._hbx_wheel8.out = False

        self._hbx_wheel1.set_active(False)
        self._hbx_wheel2.set_active(False)
        self._hbx_wheel3.set_active(False)
        self._hbx_wheel4.set_active(False)
        self._hbx_wheel5.set_active(False)
        self._hbx_wheel6.set_active(False)
        self._hbx_wheel7.set_active(False)
        self._hbx_wheel8.set_active(False)
        self._wheelrow1 = False
        self._wheelrow2 = False

        if nohullright:
            #remove_subnodes(self.node, ["hull_rightwheels",])
            texture_subnodes(self.node, ["hull_rightwheels",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png",
                             alpha=True)
            self._hbx_wheel1.set_active(True)
            self._hbx_wheel2.set_active(True)
            self._hbx_wheel3.set_active(True)
            self._hbx_wheel4.set_active(True)
            self._hbx_wheel5.set_active(True)
            self._hbx_wheel6.set_active(True)
            self._hbx_wheel7.set_active(True)
            self._hbx_wheel8.set_active(True)
            self._hbx_rhull.set_active(False)
            self._hbx_rhull.hitpoints = 0
            self._hbx_rhull.out = True

        self._failure_full = False

        self._turretaa1 = CustomTurret(parent=self,
                                       world=world, name=("%s-aa1-turret" % name), side=side,
                                       turnrate=radians(80.0), elevrate=radians(80.0),
                                       hcenter=0, harc=360, pcenter=0, parc=(-10, 70),
                                       modelpath=(self.node, "aa1_turret"),
                                       texture=texture, normalmap=self.normalmap,
                                       glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(self._turretaa1)
        self._turretaa5 = CustomTurret(parent=self,
                                       world=world, name=("%s-aa5-turret" % name), side=side,
                                       turnrate=radians(80.0), elevrate=radians(80.0),
                                       hcenter=-90, harc=180, pcenter=0, parc=(-10, 70),
                                       modelpath=(self.node, "aa5_turret"),
                                       texture=texture, normalmap=self.normalmap,
                                       glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(self._turretaa5)
        self._turretaa6 = CustomTurret(parent=self,
                                       world=world, name=("%s-aa6-turret" % name), side=side,
                                       turnrate=radians(80.0), elevrate=radians(80.0),
                                       hcenter=90, harc=180, pcenter=0, parc=(-10, 70),
                                       modelpath=(self.node, "aa6_turret"),
                                       texture=texture, normalmap=self.normalmap,
                                       glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(self._turretaa6)

        cannonaa1 = N2a38m(parent=self._turretaa1,
                           mpos=Point3(0.00, -29.81, 24.11),
                           mhpr=Vec3(0.0, 0.0, 0.0),
                           mltpos=Point3(0.00, -26.41, 24.11),
                           ammo=10000, viseach=(10, 0))
        self._turretaa1.add_cannon(cannonaa1)
        cannonaa5 = N2a38m(parent=self._turretaa5,
                           mpos=Point3(17.39, 6.20, 15.38),
                           mhpr=Vec3(0.0, 0.0, 0.0),
                           mltpos=Point3(-23.86, 9.60, 15.38),
                           ammo=10000, viseach=(10, 5))
        self._turretaa5.add_cannon(cannonaa5)
        cannonaa6 = N2a38m(parent=self._turretaa6,
                           mpos=Point3(-17.39, 6.20, 15.38),
                           mhpr=Vec3(0.0, 0.0, 0.0),
                           mltpos=Point3(23.86, 9.60, 15.38),
                           ammo=10000, viseach=(10, 5))
        self._turretaa6.add_cannon(cannonaa6)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if self.shotdown:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        # HULL
        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode(offset=self._hbx_hull.center)
            # fire'n'smoke
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rhull.hitpoints <= 0 and not self._hbx_rhull.out:
            #remove_subnodes(self.node, ["hull_rightwheels",])
            texture_subnodes(self.node, ["hull_rightwheels",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png",
                             alpha=True)
            self._hbx_wheel1.set_active(True)
            self._hbx_wheel2.set_active(True)
            self._hbx_wheel3.set_active(True)
            self._hbx_wheel4.set_active(True)
            self._hbx_wheel5.set_active(True)
            self._hbx_wheel6.set_active(True)
            self._hbx_wheel7.set_active(True)
            self._hbx_wheel8.set_active(True)
            self._hbx_rhull.set_active(False)
            self._hbx_rhull.out = True

        # WHEELS
        if self._hbx_wheel1.hitpoints <= 0 and not self._hbx_wheel1.out:
            self.explode_minor(offset=self._hbx_wheel1.center)
            for model in self.models:
                handle = model.find("**/axle1")
                if not handle.isEmpty():
                    handle.setR(15)
            texture_subnodes(self.node, ["axle1",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel1.out = True
        if self._hbx_wheel2.hitpoints <= 0 and not self._hbx_wheel2.out:
            self.explode_minor(offset=self._hbx_wheel2.center)
            for model in self.models:
                handle = model.find("**/axle2")
                if not handle.isEmpty():
                    handle.setR(350)
            texture_subnodes(self.node, ["axle2",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel2.out = True
        if self._hbx_wheel3.hitpoints <= 0 and not self._hbx_wheel3.out:
            self.explode_minor(offset=self._hbx_wheel3.center)
            for model in self.models:
                handle = model.find("**/axle3")
                if not handle.isEmpty():
                    handle.setR(5)
            texture_subnodes(self.node, ["axle3",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel3.out = True
        if self._hbx_wheel4.hitpoints <= 0 and not self._hbx_wheel4.out:
            self.explode_minor(offset=self._hbx_wheel4.center)
            for model in self.models:
                handle = model.find("**/axle4")
                if not handle.isEmpty():
                    handle.setR(20)
            texture_subnodes(self.node, ["axle4",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel4.out = True
        if self._hbx_wheel5.hitpoints <= 0 and not self._hbx_wheel5.out:
            self.explode_minor(offset=self._hbx_wheel5.center)
            for model in self.models:
                handle = model.find("**/axle5")
                if not handle.isEmpty():
                    handle.setR(355)
            texture_subnodes(self.node, ["axle5",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel5.out = True
        if self._hbx_wheel6.hitpoints <= 0 and not self._hbx_wheel6.out:
            self.explode_minor(offset=self._hbx_wheel6.center)
            for model in self.models:
                handle = model.find("**/axle6")
                if not handle.isEmpty():
                    handle.setR(345)
            texture_subnodes(self.node, ["axle6",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel6.out = True
        if self._hbx_wheel7.hitpoints <= 0 and not self._hbx_wheel7.out:
            self.explode_minor(offset=self._hbx_wheel7.center)
            for model in self.models:
                handle = model.find("**/axle7")
                if not handle.isEmpty():
                    handle.setR(10)
            texture_subnodes(self.node, ["axle7",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel7.out = True
        if self._hbx_wheel8.hitpoints <= 0 and not self._hbx_wheel8.out:
            self.explode_minor(offset=self._hbx_wheel8.center)
            for model in self.models:
                handle = model.find("**/axle8")
                if not handle.isEmpty():
                    handle.setR(350)
            texture_subnodes(self.node, ["axle8",],
                             texture="models/vehicles/tank-cruiser/tankcruiser_burn.png")
            self._hbx_wheel8.out = True
        if not self._wheelrow1 and self._hbx_wheel1.hitpoints <= 0 and self._hbx_wheel2.hitpoints <= 0 and self._hbx_wheel3.hitpoints <= 0 and self._hbx_wheel4.hitpoints <= 0:
            remove_subnodes(self.node, ["axle1", "axle2", "axle3", "axle4", "track2"])
            self._wheelrow1 = True
        if not self._wheelrow2 and self._hbx_wheel5.hitpoints <= 0 and self._hbx_wheel6.hitpoints <= 0 and self._hbx_wheel7.hitpoints <= 0 and self._hbx_wheel8.hitpoints <= 0:
            remove_subnodes(self.node, ["axle5", "axle6", "axle7", "axle8", "track3"])
            self._wheelrow2 = True

        # TURRETS
        if self._hbx_turm.hitpoints <= 0 and not self._hbx_turm.out:
            self.explode(offset=self._hbx_turm.center)
            remove_subnodes(self.node, ["main_turret",])
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 4.2,
                emradfact = 6.0,
                zvelfact = 9.0,
                fcolor = rgba(255, 255, 255, 1.0),
                fcolorend = rgba(246, 112, 27, 1.0),
                ftcol = 0.6,
                flifespan = 2.2,
                fpos = self._hbx_turm.center + Point3(0,0,-8),
                fdelay = 2.0,
                spos = self._hbx_turm.center + Point3(0,0,-7),
                stcol = 0.4,
                slifespan = 5.0)
            self._hbx_turm.out = True
            self._failure_full = True
        if self._hbx_tursl.hitpoints <= 0 and not self._hbx_tursl.out:
            remove_subnodes(self.node, ["sideleft_turret_elev","sideleft_turret_azim",])
            self.explode_minor(offset=self._hbx_tursl.center)
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 2.8,
                emradfact = 1.1,
                zvelfact = 8.0,
                fcolor = None,
                fcolorend = None,
                ftcol = None,
                flifespan = None,
                fpos = None,
                fdelay = None,
                spos = self._hbx_tursl.center + Point3(0,0,-2),
                stcol = 0.4,
                slifespan = 5.0)
            self._hbx_tursl.out = True
        if self._hbx_tursr.hitpoints <= 0 and not self._hbx_tursr.out:
            remove_subnodes(self.node, ["sideright_turret_elev","sideright_turret_azim",])
            self.explode_minor(offset=self._hbx_tursr.center)
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 2.8,
                emradfact = 1.1,
                zvelfact = 8.0,
                fcolor = None,
                fcolorend = None,
                ftcol = None,
                flifespan = None,
                fpos = None,
                fdelay = None,
                spos = self._hbx_tursr.center + Point3(0,0,-2),
                stcol = 0.4,
                slifespan = 5.0)
            self._hbx_tursr.out = True
        if self._hbx_turaa1.hitpoints <= 0 and not self._hbx_turaa1.out:
            self.explode_minor(offset=self._hbx_turaa1.center)
            remove_subnodes(self.node, ["aa1_turret_elev",])
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 1.4,
                emradfact = 1.1,
                zvelfact = 7.0,
                fcolor = None,
                fcolorend = None,
                ftcol = None,
                flifespan = None,
                fpos = None,
                fdelay = None,
                spos = self._hbx_turaa1.center,
                stcol = 0.5,
                slifespan = 4.0)
            self._turretaa1.destroy()
            self.turrets.remove(self._turretaa1)
            self._hbx_turaa1.out = True
        if self._hbx_turaa5.hitpoints <= 0 and not self._hbx_turaa5.out:
            self.explode_minor(offset=self._hbx_turaa5.center)
            remove_subnodes(self.node, ["aa5_turret_elev",])
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 1.4,
                emradfact = 1.1,
                zvelfact = 7.0,
                fcolor = None,
                fcolorend = None,
                ftcol = None,
                flifespan = None,
                fpos = None,
                fdelay = None,
                spos = self._hbx_turaa5.center,
                stcol = 0.5,
                slifespan = 4.0)
            self._turretaa5.destroy()
            self.turrets.remove(self._turretaa5)
            self._hbx_turaa5.out = True
        if self._hbx_turaa6.hitpoints <= 0 and not self._hbx_turaa6.out:
            self.explode_minor(offset=self._hbx_turaa6.center)
            remove_subnodes(self.node, ["aa6_turret_elev",])
            fire_n_smoke_2(
                parent=self, store=self.damage_trails,
                sclfact = 1.4,
                emradfact = 1.1,
                zvelfact = 7.0,
                fcolor = None,
                fcolorend = None,
                ftcol = None,
                flifespan = None,
                fpos = None,
                fdelay = None,
                spos = self._hbx_turaa6.center,
                stcol = 0.5,
                slifespan = 4.0)
            self._turretaa6.destroy()
            self.turrets.remove(self._turretaa6)
            self._hbx_turaa6.out = True

        # FAILURE CONDITIONS
        if self._wheelrow1 and self._wheelrow2:
            self._failure_full = True

        if self._failure_full:
            self.set_shotdown(5.0)

            for turret in self.turrets:
                turret.set_ap()

        return False


# class TankCruiser (Vehicle):

    # species = "tankcruiser"
    # maxspeed = 8.0
    # maxslope = radians(40.0)
    # maxturnrate = radians(90.0)
    # maxthracc = 2.0
    # maxvdracc = 5.0
    # strength = 3600.0
    # minhitdmg = 800.0
    # maxhitdmg = 2400.0
    # rcs = 0.005
    # hitboxdata = [#Front/middle/back armor
                  # (Point3(0.00, -32.00, 13.00), 12.6),
                  # (Point3(0.00, -7.14, 14.00), 12.8),
                  # (Point3(0.00, 37.00, 12.60), 12.0),
                  # #Side armor
                  # (Point3( 20.0, -33.0, 8.0), 5.0),
                  # (Point3(-20.0, -33.0, 8.0), 5.0),
                  # (Point3( 19.0, -22.0, 8.6), 7.0),
                  # (Point3(-19.0, -22.0, 8.6), 7.0),
                  # (Point3( 19.0, -10.0, 9.0), 7.0),
                  # (Point3(-19.0, -10.0, 9.0), 7.0),
                  # (Point3( 19.0, 3.0, 9.8), 7.5),
                  # (Point3(-19.0, 3.0, 9.8), 7.5),
                  # (Point3( 19.0, 14.0, 10.0), 7.0),
                  # (Point3(-19.0, 14.0, 10.0), 7.0),
                  # (Point3( 19.0, 26.0, 9.6), 7.0),
                  # (Point3(-19.0, 26.0, 9.6), 7.0),
                  # (Point3( 20.0, 37.0, 8.0), 5.0),
                  # (Point3(-20.0, 37.0, 8.0), 5.0),
                  # #Turrets
                  # (Point3(0.00, 18.17, 22.26), 13.0),
                  # #Wheels
                  # (Point3(-11.54, 33.14, 18.43), 5.0),
                  # (Point3(11.54, 33.14, 18.43), 5.0),
                  # (Point3(22.18, 39.03, 3.89), 4.0),
                  # (Point3(22.18, 30.34, 3.89), 4.0),
                  # (Point3(22.18, 21.14, 3.89), 4.0),
                  # (Point3(22.18, 12.45, 3.89), 4.0),
                  # (Point3(22.18, -6.28, 3.89), 4.0),
                  # (Point3(22.18, -14.97, 3.89), 4.0),
                  # (Point3(22.18, -24.16, 3.89), 4.0),
                  # (Point3(22.18, -32.85, 3.89), 4.0)]

    # groundcontact = [Point3(0.0, 2.75, 0.0),
                     # Point3(-0.95, -1.35, 0.0),
                     # Point3(+0.95, -1.35, 0.0)]
    # modelpath = "models/vehicles/tank-cruiser/tankcruiser.egg"
    # trkspdfac = [0.090]

    # def __init__ (self, world, name, side, texture=None,
                  # pos=None, hpr=None, speed=None, sink=None, damage=None):

        # Vehicle.__init__(self, world=world, name=name, side=side,
                         # texture=texture,
                         # pos=pos, hpr=hpr, speed=speed, sink=sink,
                         # damage=damage)


