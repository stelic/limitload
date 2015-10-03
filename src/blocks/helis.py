# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Vec3, Point3

from src.blocks.weapons import M230
from src.core.debris import AirBreakupData
from src.core.heli import Heli
from src.core.transl import *
from src.core.turret import CustomTurret


def breakup_small_front (handle):
    return AirBreakupData(handle=handle, limdamage=200,
                          duration=(5, 10), termspeed=(200, 300),
                          offdir=(-30, 30, -30, 30), offspeed=(10, 20),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.3), traillifespan=(0.7, 1.0),
                          trailthickness=(0.4, 0.8))

def breakup_medium_left (handle):
    return AirBreakupData(handle=handle, limdamage=160,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(60, 120, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2))

def breakup_medium_right (handle):
    return AirBreakupData(handle=handle, limdamage=160,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-120, -60, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2))

def breakup_engine_left (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(60, 120, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2))

def breakup_engine_right (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-120, -60, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2))

def breakup_engine_down (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-180, 180, -90, -45), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2))

def breakup_small_left (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(5, 10), termspeed=(50, 100),
                          offdir=(30, 150, -60, 60), offspeed=(15, 25),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.2), traillifespan=(0.3, 0.7),
                          trailthickness=(0.3, 0.5))

def breakup_small_right (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(5, 10), termspeed=(50, 100),
                          offdir=(-150, -30, -60, 60), offspeed=(15, 25),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.2), traillifespan=(0.3, 0.7),
                          trailthickness=(0.3, 0.5))

def breakup_small_up (handle):
    return AirBreakupData(handle=handle, limdamage=120,
                          duration=(10, 15), termspeed=(100, 150),
                          offdir=(-180, 180, 45, 90), offspeed=(10, 20),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.3), traillifespan=(0.4, 0.9),
                          trailthickness=(0.4, 0.8))


class Ah64 (Heli):

    species = "ah64"
    longdes = _("Hughes AH-64 Apache")
    shortdes = _("AH-64")

    minmass = 5200.0
    maxmass = 8000.0
    maxspeed = 80.0
    strength = 10.0
    minhitdmg = 1.0
    maxhitdmg = 8.0
    dmgtime = 4.0
    rcs = 0.8
    mainrpm = 400.0
    tailrpm = 1400.0

    # hitboxdata = [(Point3(0.0, 1.0, 0.0), 2.0),
                  # (Point3(0.0, -3.0, 0.0), 1.0)]
    hitboxdata = [(Point3(0.0, -2.8, -0.2), 3.0, 8.8, 2.7)]
    fmodelpath = "models/aircraft/ah64/ah64.egg"
    modelpath = ["models/aircraft/ah64/ah64-1.egg",
                 "models/aircraft/ah64/ah64-2.egg",
                 "models/aircraft/ah64/ah64-3.egg"]
    sdmodelpath = "models/aircraft/ah64/ah64-shotdown.egg"
    shdmodelpath = "models/aircraft/ah64/ah64-shadow.egg"
    glossmap = "models/aircraft/ah64/ah64_gls.png"
    engsoundname = "engine-ah64"
    breakupdata = [
        breakup_small_front("rotor"),
        breakup_small_left("wing_left"),
        breakup_small_right("wing_right"),
        breakup_small_up("tail"),
        breakup_small_up("radar"),
        breakup_small_up("rotor_tail"),
        breakup_engine_left("engine_left"),
        breakup_engine_right("engine_right"),
    ]

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None,
                  cnammo=[], lnammo=[], trammo=[1200]):

        Heli.__init__(self, world=world, name=name, side=side,
                      texture=texture,
                      pos=pos, hpr=hpr, speed=speed,
                      damage=damage, faillvl=faillvl)

        # Turrets.
        turret = CustomTurret(parent=self,
                              world=world, name=("%s-turret" % name), side=side,
                              turnrate=radians(90.0), elevrate=radians(90.0),
                              hcenter=0, harc=270, pcenter=0, parc=(-70, 5),
                              modelpath=(self.node, "turret"),
                              texture=texture, normalmap=self.normalmap,
                              glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(turret)

        cannon = M230(parent=turret,
                      mpos=Point3(0.002, 4.211, -1.780),
                      mhpr=Vec3(0.0, 0.0, 0.0),
                      mltpos=Point3(0.002, 4.611, -1.780),
                      ammo=trammo[0], viseach=5)
        turret.add_cannon(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-2.40,  0.20, -0.05), Vec3()),
                       (Point3( 2.40,  0.20, -0.05), Vec3())]
        self._init_pylon_handlers(lnammo)


