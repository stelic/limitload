# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Point2, Vec3, Point3

from src.blocks.weapons import Gsh23, Gsh301, Gsh623, M3, M39, M61, Nr23, Gau8, Defa554
from src.blocks.weapons import TurretM61
from src.core.body import Body, HitboxData
from src.core.debris import AirBreakupData, AirBreakup
from src.core.droptank import DropTank
from src.core.effect import fire_n_smoke_1
from src.core.misc import rgba, hprtovec, remove_subnodes, set_texture, intl01vr
from src.core.misc import randrange
from src.core.misc import fx_uniform
from src.core.plane import Plane, VISTYPE
from src.core.trail import PolyExhaust
from src.core.transl import *
from src.core.turret import CustomTurret


exhaustcolor = rgba(240, 188, 102, 0.5) #rgba(255, 160, 51, 0.5)
exhaustcolorend = rgba(222, 198, 240, 0.6) #rgba(113, 101, 122, 0.6) #rgba(113, 51, 12, 0.6) #rgba(113, 101, 154, 0.6) #rgba(159, 108, 127, 1.0)
exhaustcolorlight = rgba(255, 200, 109, 0.5)
exhaustglowmap = rgba(255, 255, 255, 1.0)
exhaustltradius = 3.0
exhaustlthalfat = 0.33

def breakup_large_up (handle):
    return AirBreakupData(handle=handle, limdamage=220,
                          duration=(25, 30), termspeed=(150, 250),
                          offdir=(-180, 180, 60, 90), offspeed=(3, 6),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=0.0, traillifespan=0.0,
                          trailthickness=0.0)

def breakup_large_left (handle):
    return AirBreakupData(handle=handle, limdamage=220,
                          duration=(25, 30), termspeed=(150, 250),
                          offdir=(75, 105, -15, 15), offspeed=(3, 6),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=0.0, traillifespan=0.0,
                          trailthickness=0.0)

def breakup_large_right (handle):
    return AirBreakupData(handle=handle, limdamage=220,
                          duration=(25, 30), termspeed=(150, 250),
                          offdir=(-105, -75, -15, 15), offspeed=(3, 6),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=0.0, traillifespan=0.0,
                          trailthickness=0.0)

def breakup_medium_up (handle):
    return AirBreakupData(handle=handle, limdamage=160,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-180, 180, 45, 90), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_medium_left (handle):
    return AirBreakupData(handle=handle, limdamage=160,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(60, 120, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_medium_right (handle):
    return AirBreakupData(handle=handle, limdamage=160,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-120, -60, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_engine_left (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(60, 120, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_engine_right (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-120, -60, -30, 30), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_engine_down (handle):
    return AirBreakupData(handle=handle, limdamage=100,
                          duration=(15, 20), termspeed=(100, 200),
                          offdir=(-180, 180, -90, -45), offspeed=(5, 10),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.2, 0.4), traillifespan=(1.0, 1.5),
                          trailthickness=(0.7, 1.2), trailtcol=0.2)

def breakup_small_front (handle):
    return AirBreakupData(handle=handle, limdamage=200,
                          duration=(5, 10), termspeed=(200, 300),
                          offdir=(-30, 30, -30, 30), offspeed=(10, 20),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.3), traillifespan=(0.7, 1.0),
                          trailthickness=(0.4, 0.8))

def breakup_small_back (handle):
    return AirBreakupData(handle=handle, limdamage=200,
                          duration=(5, 10), termspeed=(200, 300),
                          offdir=(150, 210, -30, 30), offspeed=(10, 20),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.3), traillifespan=(0.7, 1.0),
                          trailthickness=(0.4, 0.8))

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

def breakup_small_down (handle):
    return AirBreakupData(handle=handle, limdamage=120,
                          duration=(10, 15), termspeed=(100, 150),
                          offdir=(-180, 180, -90, -45), offspeed=(10, 20),
                          rollspeeddeg=(-720, 720), rollrad=(-1.0, 1.0),
                          traildurfac=(0.1, 0.3), traillifespan=(0.4, 0.9),
                          trailthickness=(0.4, 0.8))


class Mig29 (Plane):

    species = "mig29"
    longdes = _("Mikoyan-Gurevich MiG-29")
    shortdes = _("MiG-29")

    minmass = 11000.0
    maxmass = 20000.0
    wingarea = 38.0
    wingaspect = 3.5
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(28.0)
    maxthrust = 50e3 * 2
    maxthrustab = 80e3 * 2
    thrustincab = 1.4
    maxload = 9.0
    refmass = 14000.0
    maxspeedz = 320.0
    maxspeedabz = 430.0
    maxclimbratez = 280.0
    cloptspeedz = 300.0
    maxspeedh = 310.0
    maxspeedabh = 650.0
    maxrollratez = radians(360.0)
    maxpitchratez = radians(60.0)
    maxfuel = 3500.0
    refsfcz = 0.80 / 3.6e4
    refsfcabz = 2.00 / 3.6e4
    sfcincab = 1.1
    reldragbrake = 2.0
    maxflapdeflect = radians(30.0)
    maxflapdeltzlaoa = radians(-10.0)
    maxflapdeltmaxaoa = radians(-5.0)
    maxflapdeltreldrag = 2.0
    midflapdeflect = radians(10.0)
    midflapdeltzlaoa = radians(-5.0)
    midflapdeltmaxaoa = radians(-2.0)
    midflapdeltreldrag = 0.5
    maxlandspeed = 140.0
    maxlandsinkrate = 8.0
    maxlandrotangle = radians(20.0)
    minlandrotangle = radians(-2.0)
    maxlandrollangle = radians(20.0)
    reldragwheelbrake = 20.0
    reldragwheel = 1.0
    groundcontact = [Point3(0.0, 3.0, -1.7),
                     Point3(1.5, -0.5, -1.7),
                     Point3(-1.5, -0.5, -1.7)]

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 12.0), radians(90 - 15.0), radians(180 - 25.0))
    radarrange = 60000.0
    radarangle = (radians(30.0), radians(30.0), radians(30.0))
    irstrange = 20000.0
    irstangle = (radians(30.0), radians(30.0), radians(30.0))
    tvrange = 5000.0
    tvangle = (radians(-70.0), radians(5.0), radians(50.0))
    rwrwash = 0.5
    datalinkrecv = True
    datalinksend = False
    rcs = 5.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.1, 0.6), 1.2),
                  # (Point3(0.0, 2.7, 0.2), 1.4),
                  # (Point3(0.0, 0.0, 0.0), 1.4),
                  # (Point3(0.0, -2.8, 0.0), 1.4),
                  # #Left wing
                  # (Point3(-2.0, -1.2, 0.2), 1.0),
                  # (Point3(-3.7, -1.8, 0.2), 0.8),
                  # #Right wing
                  # (Point3(+2.0, -1.2, 0.2), 1.0),
                  # (Point3(+3.7, -1.8, 0.2), 0.8)]
    hitboxdata = [(Point3(0.0,  4.9, 0.4), 1.2, 4.3, 1.2),
                  (Point3(0.0, -0.1, 0.0), 1.7, 3.9, 0.9),
                  (Point3(-1.9, -4.5, 1.3), 0.2, 1.0, 1.1),
                  (Point3(+1.9, -4.5, 1.3), 0.2, 1.0, 1.1),
                  #Left wing
                  (Point3(-3.7, -0.9, 0.1), 2.0, 2.4, 0.2),
                  #Right wing
                  (Point3(+3.7, -0.9, 0.1), 2.0, 2.4, 0.2)]
    hitboxcritdata = [(Point3(-0.95, -4.6, -0.2), 0.7),
                      (Point3(+0.95, -4.6, -0.2), 0.7)]
    fmodelpath = "models/aircraft/mig29/mig29.egg"
    modelpath = ["models/aircraft/mig29/mig29-1.egg",
                 "models/aircraft/mig29/mig29-2.egg",
                 "models/aircraft/mig29/mig29-3.egg"]
    sdmodelpath = "models/aircraft/mig29/mig29-shotdown.egg"
    shdmodelpath = "models/aircraft/mig29/mig29-shadow.egg"
    vortexdata = [Point3(-5.7, -2.6, 0.1), Point3(5.7, -2.6, 0.1)]
    glossmap = "models/aircraft/mig29/mig29_gls.png"
    engsoundname = "engine-mig29"
    cpengsoundname = "cockpit-mig29-engine"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None, onground=False,
                  damage=None, faillvl=None, cnammo=[250], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       onground=onground,
                       damage=damage, faillvl=faillvl)

        cannon = Gsh301(parent=self,
                        mpos=Point3(-0.7, 5.0, 0.1),
                        mhpr=Vec3(0.0, 0.0, 0.0),
                        mltpos=Point3(-0.8, 5.0, 0.2),
                        ammo=cnammo[0], viseach=5,
                        reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-2.41, -0.27, -0.07), Vec3()),
                       (Point3( 2.41, -0.27, -0.07), Vec3()),
                       (Point3(-3.30, -0.85, -0.07), Vec3()),
                       (Point3( 3.30, -0.85, -0.07), Vec3()),
                       (Point3(-4.00, -1.35, -0.07), Vec3()),
                       (Point3( 4.00, -1.35, -0.07), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.95, -5.30, -0.18),
                               radius0=0.45, radius1=0.40, length=6.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -5.8, -0.18),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.95, -5.30, -0.18),
                               radius0=0.45, radius1=0.40, length=6.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Mig29fd (Mig29):

    species = "mig29fd"
    longdes = _("Mikoyan-Gurevich MiG-29FD")
    shortdes = _("MiG-29FD")

    refsfcz = 0.70 / 3.6e4
    refsfcabz = 1.80 / 3.6e4

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None, onground=False,
                  damage=None, faillvl=None, cnammo=[250], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       onground=onground,
                       damage=damage, faillvl=faillvl)

        cannon = Gsh301(parent=self,
                        mpos=Point3(-0.7, 5.0, 0.1),
                        mhpr=Vec3(0.0, 0.0, 0.0),
                        mltpos=Point3(-0.8, 5.0, 0.2),
                        ammo=cnammo[0], viseach=5,
                        reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.

        self.pylons = [(Point3( 0.00, -1.24, -0.34), Vec3(), DropTank),

                       (Point3(-2.35, -0.27, -0.05), Vec3()),
                       (Point3( 2.35, -0.27, -0.05), Vec3()),

                       (Point3(-2.48, -0.27, -0.07), Vec3()),
                       (Point3( 2.48, -0.27, -0.07), Vec3()),
                       (Point3(-3.30, -0.85, -0.07), Vec3()),
                       (Point3( 3.30, -0.85, -0.07), Vec3()),
                       (Point3(-4.00, -1.35, -0.07), Vec3()),
                       (Point3( 4.00, -1.35, -0.07), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.95, -5.30, -0.18),
                               radius0=0.45, radius1=0.40, length=6.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -5.8, -0.18),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.95, -5.30, -0.18),
                               radius0=0.45, radius1=0.40, length=6.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Mig25 (Plane):

    species = "mig25"
    longdes = _("Mikoyan-Gurevich MiG-25")
    shortdes = _("MiG-25")

    minmass = 20000.0
    maxmass = 37000.0
    wingarea = 61.0
    wingaspect = 3.1
    wingspeff = 0.70
    zlaoa = radians(-2.0)
    maxaoa = radians(18.0)
    maxthrust = 74e3 * 2
    maxthrustab = 110e3 * 2
    thrustincab = 3.0
    maxload = 4.5
    refmass = 24000.0
    maxspeedz = 320.0
    maxspeedabz = 440.0
    maxclimbratez = 240.0
    cloptspeedz = 280.0
    maxspeedh = 360.0
    maxspeedabh = 920.0
    maxrollratez = radians(160.0)
    maxpitchratez = radians(30.0)
    maxfuel = 14000.0
    refsfcz = 1.20 / 3.6e4
    refsfcabz = 2.80 / 3.6e4
    sfcincab = 0.8
    reldragbrake = 2.0

    strength = 9.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 30.0), radians(180 - 35.0))
    radarrange = 100000.0
    radarangle = (radians(30.0), radians(30.0), radians(45.0))
    irstrange = 15000.0
    irstangle = (radians(20.0), radians(20.0), radians(30.0))
    tvrange = None
    tvangle = None
    rwrwash = 0.8
    datalinkrecv = True
    datalinksend = False
    rcs = 8.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.4, 0.6), 1.4),
                  # (Point3(0.0, 2.0, 0.8), 1.8),
                  # (Point3(0.0, -1.8, 0.8), 2.0),
                  # (Point3(0.0, -5.8, 1.0), 1.9),
                  # #Left wing
                  # (Point3(-2.6, -3.4, 1.3), 1.1),
                  # (Point3(-4.6, -4.6, 1.0), 1.1),
                  # #Right wing
                  # (Point3(+2.6, -3.4, 1.3), 1.1),
                  # (Point3(+4.6, -4.6, 1.0), 1.1)]
    hitboxdata = [(Point3(0.0,  7.7, 0.7), 0.6, 2.7, 1.1),
                  (Point3(0.0, -1.2, 0.8), 1.8, 6.2, 1.1),
                  (Point3(-1.5, -8.0, 3.0), 0.3, 1.0, 1.0),
                  (Point3( 1.5, -8.0, 3.0), 0.3, 1.0, 1.0),
                  #Left wing
                  (Point3(-4.3, -3.7, 1.1), 2.5, 2.8, 0.35),
                  #Right wing
                  (Point3(+4.3, -3.7, 1.1), 2.5, 2.8, 0.35)]
    hitboxcritdata = [(Point3(-0.74, -8.1, 0.77), 0.9),
                      (Point3(+0.74, -8.1, 0.77), 0.9)]
    vortexdata = [Point3(-6.7, -5.0, 0.9), Point3(6.7, -5.0, 0.9)]
    fmodelpath = "models/aircraft/mig25/mig25.egg"
    modelpath = ["models/aircraft/mig25/mig25-1.egg",
                 "models/aircraft/mig25/mig25-2.egg",
                 "models/aircraft/mig25/mig25-3.egg"]
    sdmodelpath = "models/aircraft/mig25/mig25-shotdown.egg"
    shdmodelpath = "models/aircraft/mig25/mig25-shadow.egg"
    glossmap = "models/aircraft/mig25/mig25_gls.png"
    engsoundname = "engine-mig29"
    cpengsoundname = "cockpit-mig29-engine"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_small_front("nose"),
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[260], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-3.44, -2.60,  0.62), Vec3()),
                       (Point3( 3.44, -2.60,  0.62), Vec3()),
                       (Point3(-4.73, -3.24,  0.50), Vec3()),
                       (Point3( 4.73, -3.24,  0.50), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.74, -8.38, 0.77),
                               radius0=0.80, radius1=0.75, length=7.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -8.38, 0.77),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.74, -8.38, 0.77),
                               radius0=0.80, radius1=0.75, length=7.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Mig31 (Plane):

    species = "mig31"
    longdes = _("Mikoyan-Gurevich MiG-31")
    shortdes = _("MiG-31")

    minmass = 22000.0
    maxmass = 46000.0
    wingarea = 62.0
    wingaspect = 2.9
    wingspeff = 0.70
    zlaoa = radians(-2.0)
    maxaoa = radians(20.0)
    maxthrust = 90e3 * 2
    maxthrustab = 150e3 * 2
    thrustincab = 3.0
    maxload = 5.0
    refmass = 34000.0
    maxspeedz = 330.0
    maxspeedabz = 470.0
    maxclimbratez = 240.0
    cloptspeedz = 280.0
    maxspeedh = 380.0
    maxspeedabh = 940.0
    maxrollratez = radians(180.0)
    maxpitchratez = radians(30.0)
    maxfuel = 16500.0
    refsfcz = 0.80 / 3.6e4
    refsfcabz = 2.00 / 3.6e4
    sfcincab = 0.8
    reldragbrake = 2.0

    strength = 10.0
    minhitdmg = 0.0
    maxhitdmg = 8.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 25.0), radians(180 - 35.0))
    radarrange = 180000.0
    radarangle = (radians(40.0), radians(40.0), radians(50.0))
    irstrange = 20000.0
    irstangle = (radians(30.0), radians(30.0), radians(30.0))
    tvrange = None
    tvangle = None
    rwrwash = 0.5
    datalinkrecv = True
    datalinksend = True
    rcs = 8.5
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 6.4, 0.5), 1.6),
                  # (Point3(0.0, 3.0, 0.5), 1.8),
                  # (Point3(0.0, -1.0, 0.5), 2.0),
                  # (Point3(0.0, -5.4, 0.8), 2.2),
                  # #Left wing
                  # (Point3(-2.6, -2.4, 0.5), 1.2),
                  # (Point3(-4.6, -3.6, 0.5), 1.0),
                  # #Right wing
                  # (Point3(+2.6, -2.4, 0.5), 1.2),
                  # (Point3(+4.6, -3.6, 0.5), 1.0)]
    hitboxdata = [(Point3(0.0,  9.4, 0.5), 0.8, 2.6, 1.2),
                  (Point3(0.0, -0.4, 0.4), 2.3, 7.2, 1.4),
                  #Left wing
                  (Point3(-4.7, -3.2, 0.4), 2.4, 3.2, 0.5),
                  #Right wing
                  (Point3(+4.7, -3.2, 0.4), 2.4, 3.2, 0.5)]
    hitboxcritdata = [(Point3(-0.88, -8.6, 0.34), 1.0),
                      (Point3(+0.88, -8.6, 0.34), 1.0)]
    vortexdata = [Point3(-7.1, -5.0, 0.0), Point3(7.1, -5.0, 0.0)]
    fmodelpath = "models/aircraft/mig31/mig31.egg"
    modelpath = ["models/aircraft/mig31/mig31-1.egg",
                 "models/aircraft/mig31/mig31-2.egg",
                 "models/aircraft/mig31/mig31-3.egg"]
    sdmodelpath = "models/aircraft/mig31/mig31-shotdown.egg"
    shdmodelpath = "models/aircraft/mig31/mig31-shadow.egg"
    # normalmap = "models/aircraft/mig31/mig31_nm.png"
    glossmap = "models/aircraft/mig31/mig31_gls.png"
    engsoundname = "engine-mig29"
    cpengsoundname = "cockpit-mig29-engine"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[260], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = Gsh623(parent=self,
                        mpos=Point3(0.1, 3.0, -0.7),
                        mhpr=Vec3(0.0, 0.0, 0.0),
                        mltpos=Point3(0.2, 3.0, -0.8),
                        ammo=cnammo[0], viseach=5,
                        reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-3.51, -2.55,  0.00), Vec3()),
                       (Point3( 3.51, -2.55,  0.00), Vec3()),
                       (Point3(-4.81, -3.15, -0.17), Vec3()),
                       (Point3( 4.81, -3.15, -0.17), Vec3()),
                       (Point3(-7.10, -5.00,  0.02), Vec3()),
                       (Point3( 7.10, -5.00,  0.02), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.88, -8.40, 0.33),
                               radius0=0.80, radius1=0.75, length=7.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -8.90, 0.33),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.88, -8.40, 0.33),
                               radius0=0.80, radius1=0.75, length=7.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Mig21 (Plane):

    species = "mig21"
    longdes = _("Mikoyan-Gurevich MiG-21")
    shortdes = _("MiG-21")

    minmass = 5400.0
    maxmass = 8800.0
    wingarea = 23.0
    wingaspect = 2.2
    wingspeff = 0.60
    zlaoa = radians(-2.0)
    maxaoa = radians(20.0)
    maxthrust = 40e3
    maxthrustab = 70e3
    thrustincab = 1.4
    maxload = 8.5
    refmass = 6500.0
    maxspeedz = 310.0
    maxspeedabz = 400.0
    maxclimbratez = 210.0
    cloptspeedz = 270.0
    maxspeedh = 290.0
    maxspeedabh = 610.0
    maxrollratez = radians(360.0)
    maxpitchratez = radians(60.0)
    maxfuel = 2400.0
    refsfcz = 0.95 / 3.6e4
    refsfcabz = 2.30 / 3.6e4
    sfcincab = 1.2
    reldragbrake = 2.0

    strength = 6.0
    minhitdmg = 0.0
    maxhitdmg = 4.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 25.0), radians(180 - 30.0))
    radarrange = 30000.0
    radarangle = (radians(20.0), radians(20.0), radians(30.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = 0.8
    datalinkrecv = False
    datalinksend = False
    rcs = 3.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 3.8, 0.5), 1.1),
                  # (Point3(0.0, 1.6, 0.5), 1.2),
                  # (Point3(0.0, -0.8, 0.5), 1.2),
                  # (Point3(0.0, -3.3, 0.6), 1.3),
                  # (Point3(0.0, -5.2, 1.8), 0.8),
                  # #Left wing
                  # (Point3(-2.0, -1.2, 0.0), 0.8),
                  # #Right wing
                  # (Point3(+2.0, -1.2, 0.0), 0.8)]
    hitboxdata = [(Point3(0.0,  1.5, 0.5), 0.7, 6.4, 1.0),
                  (Point3(0.0, -5.3, 1.9), 0.1, 1.4, 0.9),
                  #Left wing
                  (Point3(-2.2, -0.4, 0.1), 1.5, 2.4, 0.15),
                  #Right wing
                  (Point3(+2.2, -0.4, 0.1), 1.5, 2.4, 0.15)]
    hitboxcritdata = [(Point3(0.00, -5.5, 0.2), 0.7)]
    vortexdata = [Point3(-3.7, -2.5, 0.0), Point3(3.7, -2.5, 0.0)]
    fmodelpath = "models/aircraft/mig21/mig21.egg"
    modelpath = ["models/aircraft/mig21/mig21-1.egg",
                 "models/aircraft/mig21/mig21-2.egg",
                 "models/aircraft/mig21/mig21-3.egg"]
    sdmodelpath = "models/aircraft/mig21/mig21-shotdown.egg"
    shdmodelpath = "models/aircraft/mig21/mig21-shadow.egg"
    glossmap = "models/aircraft/mig21/mig21_gls.png"
    engsoundname = "engine-mig29"
    flybysoundname = "flight-mig21flyby"
    breakupdata = [
        breakup_small_front("nose"),
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[250], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = Gsh23(parent=self,
                       mpos=Point3(0.46, 3.62, -0.27),
                       mhpr=Vec3(0.0, 0.0, 0.0),
                       mltpos=Point3(0.56, 3.62, -0.17),
                       ammo=cnammo[0], viseach=5,
                       reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3( 0.00, -0.02, -0.60), Vec3()), #Fuel Tank

                       (Point3(-2.11, -0.28, -0.12), Vec3()),
                       (Point3( 2.11, -0.28, -0.12), Vec3()),
                       (Point3(-2.73, -1.19, -0.16), Vec3()),
                       (Point3( 2.73, -1.19, -0.16), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.00, -5.75, 0.19),
                               radius0=0.60, radius1=0.55, length=7.0,
                               speed=20.0, poolsize=15,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.00, -6.25, 0.19),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)


class Su27 (Plane):

    species = "su27"
    longdes = _("Sukhoi Su-27")
    shortdes = _("Su-27")

    minmass = 16500.0
    maxmass = 30500.0
    wingarea = 62.0
    wingaspect = 3.5
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(28.0)
    maxthrust = 75e3 * 2
    maxthrustab = 122e3 * 2
    thrustincab = 1.5
    maxload = 9.0
    refmass = 21500.0
    maxspeedz = 320.0
    maxspeedabz = 440.0
    maxclimbratez = 280.0
    cloptspeedz = 300.0
    maxspeedh = 340.0
    maxspeedabh = 680.0
    maxrollratez = radians(360.0)
    maxpitchratez = radians(60.0)
    maxfuel = 9400.0
    refsfcz = 0.80 / 3.6e4
    refsfcabz = 2.00 / 3.6e4
    sfcincab = 1.0
    reldragbrake = 2.0

    strength = 10.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 13.0), radians(90 - 13.0), radians(180 - 25.0))
    radarrange = 100000.0
    radarangle = (radians(30.0), radians(30.0), radians(40.0))
    irstrange = 20000.0
    irstangle = (radians(30.0), radians(30.0), radians(30.0))
    tvrange = 5000.0
    tvangle = (radians(-70.0), radians(5.0), radians(50.0))
    rwrwash = 0.5
    datalinkrecv = True
    datalinksend = False
    rcs = 7.5
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 6.0, 0.8), 1.4),
                  # (Point3(0.0, 2.8, 0.6), 1.6),
                  # (Point3(0.0, -0.4, 0.3), 1.7),
                  # (Point3(0.0, -4.0, 0.5), 1.8),
                  # #Left wing
                  # (Point3(-3.1, -1.6, 0.3), 1.2),
                  # (Point3(-5.1, -3.0, 0.3), 1.2),
                  # #Right wing
                  # (Point3(+3.1, -1.6, 0.3), 1.2),
                  # (Point3(+5.1, -3.0, 0.3), 1.2)]
    hitboxdata = [(Point3(0.0,  5.1, 0.7), 1.0, 6.4, 1.0),
                  (Point3(0.0, -1.2, 0.1), 1.8, 4.7, 0.9),
                  (Point3(-1.9, -4.5, 2.3), 0.1, 1.4, 1.8),
                  (Point3( 1.9, -4.5, 2.3), 0.1, 1.4, 1.8),
                  #Left wing
                  (Point3(-4.3, -1.6, 0.5), 2.5, 2.6, 0.15),
                  #Right wing
                  (Point3(+4.3, -1.6, 0.5), 2.5, 2.6, 0.15)]
    hitboxcritdata = [(Point3(-1.10, -6.6, 0.04), 0.8),
                      (Point3(+1.10, -6.6, 0.04), 0.8)]
    vortexdata = [Point3(-6.7, -3.8, 0.5), Point3(6.7, -3.8, 0.5)]
    fmodelpath = "models/aircraft/su27/su27.egg"
    modelpath = ["models/aircraft/su27/su27-1.egg",
                 "models/aircraft/su27/su27-2.egg",
                 "models/aircraft/su27/su27-3.egg"]
    sdmodelpath = "models/aircraft/su27/su27-shotdown.egg"
    shdmodelpath = "models/aircraft/su27/su27-shadow.egg"
    glossmap = "models/aircraft/su27/su27_gls.png"
    engsoundname = "engine-su27"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_small_front("nose"),
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[250], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = Gsh301(parent=self,
                        mpos=Point3(0.65, 4.70, 0.7),
                        mhpr=Vec3(0.0, 0.0, 0.0),
                        mltpos=Point3(0.75, 4.70, 0.8),
                        ammo=cnammo[0], viseach=5,
                        reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(0.01,  0.84, -0.09), Vec3()),
                       (Point3(0.01,  -2.93, -0.10), Vec3()),
                       (Point3(-1.07, 0.52, -0.94), Vec3()),
                       (Point3( 1.07, 0.52, -0.94), Vec3()),
                       (Point3(-2.40, -1.15, 0.10), Vec3()),
                       (Point3( 2.40, -1.15, 0.10), Vec3()),
                       (Point3(-2.85, -1.15, 0.10), Vec3()),
                       (Point3( 2.85, -1.15, 0.10), Vec3()),
                       (Point3(-4.30, -2.00, 0.20), Vec3()),
                       (Point3( 4.30, -2.00, 0.20), Vec3()),
                       (Point3(-5.39, -3.04, 0.20), Vec3()),
                       (Point3( 5.39, -3.04, 0.20), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(1.10, -7.50, -0.05),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -8.00, -0.05),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-1.10, -7.50, -0.05),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F16 (Plane):

    species = "f16"
    longdes = _("General Dynamics F-16 Fighting Falcon")
    shortdes = _("F-16")

    minmass = 10000.0
    maxmass = 18000.0
    wingarea = 27.9
    wingaspect = 3.2
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(25.0)
    maxthrust = 76e3
    maxthrustab = 127e3
    thrustincab = 1.2
    maxload = 9.0
    refmass = 13000.0
    maxspeedz = 310.0
    maxspeedabz = 400.0
    maxclimbratez = 260.0
    cloptspeedz = 290.0
    maxspeedh = 320.0
    maxspeedabh = 540.0
    maxrollratez = radians(420.0)
    maxpitchratez = radians(50.0)
    maxfuel = 3200.0
    refsfcz = 0.75 / 3.6e4
    refsfcabz = 1.90 / 3.6e4
    sfcincab = 1.3
    reldragbrake = 2.0
    maxflapdeflect = radians(30.0)
    maxflapdeltzlaoa = radians(-10.0)
    maxflapdeltmaxaoa = radians(-5.0)
    maxflapdeltreldrag = 2.0
    midflapdeflect = radians(10.0)
    midflapdeltzlaoa = radians(-5.0)
    midflapdeltmaxaoa = radians(-2.0)
    midflapdeltreldrag = 0.5
    maxlandspeed = 140.0
    maxlandsinkrate = 8.0
    maxlandrotangle = radians(20.0)
    minlandrotangle = radians(-2.0)
    maxlandrollangle = radians(20.0)
    reldragwheelbrake = 20.0
    reldragwheel = 1.0
    groundcontact = [Point3(0.0, 3.0, -1.5),
                     Point3(1.5, -0.5, -1.5),
                     Point3(-1.5, -0.5, -1.5)]

    strength = 6.0
    minhitdmg = 0.0
    maxhitdmg = 4.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 15.0), radians(90 - 5.0), radians(180 - 20.0))
    radarrange = 40000.0
    radarangle = (radians(30.0), radians(30.0), radians(40.0))
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 4.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 3.8, 0.4), 1.0),
                  # (Point3(0.0, 1.6, 0.0), 1.3),
                  # (Point3(0.0, -0.7, 0.0), 1.2),
                  # (Point3(0.0, -3.0, 0.4), 1.2),
                  # (Point3(0.0, -4.4, 1.6), 0.6),
                  # #Left wing
                  # (Point3(-2.2, -1.2, 0.1), 1.0),
                  # #Right wing
                  # (Point3(+2.2, -1.2, 0.1), 1.0)]
    hitboxdata = [(Point3(0.0,  4.2, 0.4), 0.9, 2.9, 0.8),
                  (Point3(0.0, -0.3, 0.0), 1.2, 3.9, 0.9),
                  (Point3(0.0, -4.5, 1.8), 0.2, 1.2, 0.9),
                  #Left wing
                  (Point3(-3.0, -0.8, 0.1), 1.8, 1.6, 0.15),
                  #Right wing
                  (Point3(+3.0, -0.8, 0.1), 1.8, 1.6, 0.15)]
    hitboxcritdata = [(Point3(0.0, -4.9, 0.0), 0.8)]
    vortexdata = [Point3(-4.8, -1.7, 0.0), Point3(4.8, -1.7, 0.0)]
    fmodelpath = "models/aircraft/f16/f16.egg"
    modelpath = ["models/aircraft/f16/f16-1.egg",
                 "models/aircraft/f16/f16-2.egg",
                 "models/aircraft/f16/f16-3.egg"]
    sdmodelpath = "models/aircraft/f16/f16-shotdown.egg"
    shdmodelpath = "models/aircraft/f16/f16-shadow.egg"
    # normalmap = "models/aircraft/f16/f16_nm.png"
    glossmap = "models/aircraft/f16/f16_gls.png"
    engsoundname = "engine-f16"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_small_front("nose"),
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[600], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(-0.6, 3.0, 0.2),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(-0.6, 4.0, 0.2),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-1.61,  -0.235, -0.356), Vec3()),
                       (Point3( 1.61,  -0.235, -0.356), Vec3()),
                       (Point3(-2.87,  -0.835, -0.356), Vec3()),
                       (Point3( 2.87,  -0.835, -0.356), Vec3()),
                       (Point3(-4.13,  -1.435, -0.15), Vec3()),
                       (Point3( 4.13,  -1.435, -0.15), Vec3()),
                       (Point3(-4.86,  -1.44, 0.015), Vec3()),
                       (Point3( 4.86,  -1.44, 0.015), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -5.2, 0.0),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -6.0, 0.0),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)


class F15 (Plane):

    species = "f15"
    longdes = _("McDonnell-Douglas F-15 Eagle")
    shortdes = _("F-15")

    minmass = 15000.0
    maxmass = 30000.0
    wingarea = 56.0
    wingaspect = 3.0
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(24.0)
    maxthrust = 77e3 * 2
    maxthrustab = 112e3 * 2
    thrustincab = 1.6
    maxload = 9.0
    refmass = 20000.0
    maxspeedz = 310.0
    maxspeedabz = 420.0
    maxclimbratez = 260.0
    cloptspeedz = 280.0
    maxspeedh = 330.0
    maxspeedabh = 670.0
    maxrollratez = radians(320.0)
    maxpitchratez = radians(50.0)
    maxfuel = 6100.0
    refsfcz = 0.70 / 3.6e4
    refsfcabz = 1.80 / 3.6e4
    sfcincab = 1.0
    reldragbrake = 2.0

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 14.0), radians(90 - 10.0), radians(180 - 25.0))
    radarrange = 80000.0
    radarangle = (radians(35.0), radians(35.0), radians(50.0))
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 7.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.2, 0.7), 1.4),
                  # (Point3(0.0, 2.2, 0.4), 1.6),
                  # (Point3(0.0, -1.0, 0.2), 1.7),
                  # (Point3(0.0, -4.6, 0.3), 1.7),
                  # (Point3(-1.7, -6.8, 1.8), 0.7),
                  # (Point3(+1.7, -6.8, 1.8), 0.7),
                  # #Left wing
                  # (Point3(-2.8, -2.2, 0.4), 1.2),
                  # #Right wing
                  # (Point3(+2.8, -2.2, 0.4), 1.2)]
    hitboxdata = [(Point3(0.0,  5.7, 0.7), 0.8, 4.3, 1.2),
                  (Point3(0.0, -0.6, 0.2), 2.0, 5.6, 1.0),
                  (Point3(-1.7, -7.0, 2.0), 0.2, 1.0, 1.8),
                  (Point3(+1.7, -7.0, 2.0), 0.2, 1.0, 1.8),
                  #Left wing
                  (Point3(-4.2, -2.5, 0.4), 2.3, 2.5, 0.2),
                  #Right wing
                  (Point3(+4.2, -2.5, 0.4), 2.3, 2.5, 0.2)]
    hitboxcritdata = [(Point3(-0.72, -7.0, 0.09), 0.75),
                      (Point3(+0.72, -7.0, 0.09), 0.75)]
    vortexdata = [Point3(-6.4, -3.5, 0.3), Point3(6.4, -3.5, 0.3)]
    fmodelpath = "models/aircraft/f15/f15.egg"
    modelpath = ["models/aircraft/f15/f15-1.egg",
                 "models/aircraft/f15/f15-2.egg",
                 "models/aircraft/f15/f15-3.egg"]
    sdmodelpath = "models/aircraft/f15/f15-shotdown.egg"
    shdmodelpath = "models/aircraft/f15/f15-shadow.egg"
    # normalmap = "models/aircraft/f15/f15_nm.png"
    glossmap = "models/aircraft/f15/f15_gls.png"
    engsoundname = "engine-f15"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("intake_left"),
        breakup_small_right("intake_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(1.75, 2.78, 0.665),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(1.85, 2.78, 0.775),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-2.49, -1.67, 0.07), Vec3()),
                       (Point3( 2.49, -1.67, 0.07), Vec3()),
                       (Point3(-2.83, -1.39, 0.00), Vec3()),
                       (Point3( 2.83, -1.39, 0.00), Vec3()),
                       (Point3(-3.17, -1.39, 0.07), Vec3()),
                       (Point3( 3.17, -1.39, 0.07), Vec3()),
                       (Point3(-1.54,  1.17, -0.42), Vec3()),
                       (Point3( 1.54,  1.17, -0.42), Vec3()),
                       (Point3(-1.54, -0.80, -0.42), Vec3()),
                       (Point3( 1.54, -0.80, -0.42), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.72, -7.20, 0.09),
                               radius0=0.40, radius1=0.35, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -7.70, 0.09),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.72, -7.20, 0.09),
                               radius0=0.40, radius1=0.35, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F18 (Plane):

    species = "f18"
    longdes = _("McDonnell-Douglas F/A-18 Hornet")
    shortdes = _("F/A-18")

    minmass = 11000.0
    maxmass = 23000.0
    wingarea = 38.0
    wingaspect = 3.5
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(22.0)
    maxthrust = 49e3 * 2
    maxthrustab = 79e3 * 2
    thrustincab = 1.3
    maxload = 9.0
    refmass = 14000.0
    maxspeedz = 320.0
    maxspeedabz = 410.0
    maxclimbratez = 260.0
    cloptspeedz = 290.0
    maxspeedh = 300.0
    maxspeedabh = 540.0
    maxrollratez = radians(360.0)
    maxpitchratez = radians(60.0)
    maxfuel = 4800.0
    refsfcz = 0.75 / 3.6e4
    refsfcabz = 1.90 / 3.6e4
    sfcincab = 1.3
    reldragbrake = 2.0

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 15.0), radians(90 - 8.0), radians(180 - 25.0))
    radarrange = 60000.0
    radarangle = (radians(30.0), radians(30.0), radians(40.0))
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 5.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.4, 0.5), 1.4),
                  # (Point3(0.0, 2.5, 0.4), 1.5),
                  # (Point3(0.0, -0.4, 0.4), 1.5),
                  # (Point3(0.0, -3.5, 0.5), 1.6),
                  # #Left wing
                  # (Point3(-2.4, -0.7, 0.6), 1.0),
                  # (Point3(-4.2, -1.0, 0.6), 0.8),
                  # #Right wing
                  # (Point3(+2.4, -0.7, 0.6), 1.0),
                  # (Point3(+4.2, -1.0, 0.6), 0.8)]
    hitboxdata = [(Point3( 0.0, 3.1, 0.6), 0.6, 7.0, 1.1),
                  (Point3( 0.0, 0.6, 0.1), 1.6, 5.7, 0.7),
                  (Point3(-2.5, -5.6, 0.0), 1.0, 1.0, 0.1),
                  (Point3( 2.5, -5.6, 0.0), 1.0, 1.0, 0.1),
                  #Left wing
                  (Point3(-3.8, -0.4, 0.6), 2.4, 2.1, 0.2),
                  #Right wing
                  (Point3(+3.8, -0.4, 0.6), 2.4, 2.1, 0.2)]
    hitboxcritdata = [(Point3(-0.58, -5.8, 0.09), 0.75),
                      (Point3(+0.58, -5.8, 0.09), 0.75)]
    vortexdata = [Point3(-6.1, -1.0, 0.6), Point3(6.1, -1.0, 0.6)]
    fmodelpath = "models/aircraft/f18/f18.egg"
    modelpath = ["models/aircraft/f18/f18-1.egg",
                 "models/aircraft/f18/f18-2.egg",
                 "models/aircraft/f18/f18-3.egg"]
    sdmodelpath = "models/aircraft/f18/f18-shotdown.egg"
    shdmodelpath = "models/aircraft/f18/f18-shadow.egg"
    glossmap = "models/aircraft/f18/f18_gls.png"
    engsoundname = "engine-f18"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(0.030, 9.0, 0.4),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.030, 9.1, 0.5),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-2.344,  -0.097, -0.01), Vec3()),
                       (Point3( 2.344,  -0.097, -0.01), Vec3()),
                       (Point3(-3.024,  -0.097, -0.01), Vec3()),
                       (Point3( 3.024,  -0.097, -0.01), Vec3()),
                       (Point3(-6.21,  -0.62, 0.58), Vec3()),
                       (Point3( 6.21,  -0.62, 0.58), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.63, -6.27, 0.09),
                               radius0=0.50, radius1=0.45, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -7.27, -0.085),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.58, -6.27, 0.09),
                               radius0=0.50, radius1=0.45, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.8,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F22 (Plane):

    species = "f22"
    longdes = _("Lockheed-Martin F-22 Raptor")
    shortdes = _("F-22")

    minmass = 18000.0
    maxmass = 36000.0
    wingarea = 78.0
    wingaspect = 2.4
    wingspeff = 0.90
    zlaoa = radians(-2.0)
    maxaoa = radians(36.0)
    maxthrust = 104e3 * 2
    maxthrustab = 156e3 * 2
    thrustincab = 1.6
    maxload = 9.0
    refmass = 24000.0
    maxspeedz = 360.0
    maxspeedabz = 460.0
    maxclimbratez = 310.0
    cloptspeedz = 320.0
    maxspeedh = 410.0
    maxspeedabh = 660.0
    maxrollratez = radians(400.0)
    maxpitchratez = radians(60.0)
    maxfuel = 8200.0
    refsfcz = 0.65 / 3.6e4
    refsfcabz = 1.60 / 3.6e4
    sfcincab = 1.0
    reldragbrake = 2.0

    strength = 10.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 15.0), radians(90 - 5.0), radians(180 - 20.0))
    radarrange = 120000.0
    radarangle = (radians(40.0), radians(40.0), radians(60.0))
    irstrange = 24000.0
    irstangle = (radians(30.0), radians(30.0), radians(40.0))
    tvrange = 7000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.2
    datalinkrecv = True
    datalinksend = True
    rcs = 0.0025
    irmuffle = 0.2
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 7.0, 0.4), 1.4),
                  # (Point3(0.0, 4.2, 0.2), 1.6),
                  # (Point3(0.0, 1.1, 0.1), 1.6),
                  # (Point3(0.0, -2.2, 0.4), 1.8),
                  # (Point3(-2.8, -6.2, 0.1), 0.8),
                  # (Point3(+2.8, -6.2, 0.1), 0.8),
                  # #Left wing
                  # (Point3(-3.2, -1.5, 0.1), 1.4),
                  # #Right wing
                  # (Point3(+3.2, -1.5, 0.1), 1.4)]
    hitboxdata = [(Point3(0.0, 7.9, 0.3), 1.0, 3.0, 1.1),
                  (Point3(0.0, 1.1, 0.2), 2.2, 5.0, 1.1),
                  (Point3(-3.0, -6.0, 0.1), 1.1, 2.0, 0.1),
                  (Point3(+3.0, -6.0, 0.1), 1.1, 2.0, 0.1),
                  #Left wing
                  (Point3(-4.5, -1.2, 0.1), 2.3, 2.8, 0.25),
                  #Right wing
                  (Point3(+4.5, -1.2, 0.1), 2.3, 2.8, 0.25)]
    hitboxcritdata = [(Point3(-0.70, -4.5, 0.17), 0.75),
                      (Point3(+0.70, -4.5, 0.17), 0.75)]
    vortexdata = [Point3(-6.7, -2.4, -0.1), Point3(6.7, -2.4, -0.1)]
    fmodelpath = "models/aircraft/f22/f22.egg"
    modelpath = ["models/aircraft/f22/f22-1.egg",
                 "models/aircraft/f22/f22-2.egg",
                 "models/aircraft/f22/f22-3.egg"]
    sdmodelpath = "models/aircraft/f22/f22-shotdown.egg"
    shdmodelpath = "models/aircraft/f22/f22-shadow.egg"
    glossmap = "models/aircraft/f22/f22_gls.png"
    engsoundname = "engine-f22"
    flybysoundname = "flyby-f35"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(1.07, 5.9, 0.43),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(1.07, 5.9, 0.53),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [# INTERNAL PYLONS MISSING!
                      ]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.7, -5.2, 0.12),
                               radius0=0.70, radius1=0.65, length=6.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust04.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -6.1, -0.132),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.7, -5.2, 0.12),
                               radius0=0.70, radius1=0.65, length=6.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust04.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F35b (Plane):

    species = "f35b"
    longdes = _("Lockheed-Martin F-35 Lightning II")
    shortdes = _("F-35B")

    minmass = 14700.0
    maxmass = 27300.0
    wingarea = 42.7
    wingaspect = 2.7
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(30.0)
    maxthrust = 125e3
    maxthrustab = 191e3
    thrustincab = 1.6
    maxload = 8.0
    refmass = 19000.0
    maxspeedz = 330.0
    maxspeedabz = 420.0
    maxclimbratez = 220.0
    cloptspeedz = 300.0
    maxspeedh = 340.0
    maxspeedabh = 470.0
    maxrollratez = radians(340.0)
    maxpitchratez = radians(50.0)
    maxfuel = 6000.0
    refsfcz = 0.65 / 3.6e4
    refsfcabz = 1.60 / 3.6e4
    sfcincab = 1.0
    reldragbrake = 2.0

    strength = 7.0
    minhitdmg = 0.0
    maxhitdmg = 5.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 15.0), radians(90 - 5.0), radians(180 - 20.0))
    radarrange = 80000.0
    radarangle = (radians(40.0), radians(40.0), radians(60.0))
    irstrange = 20000.0
    irstangle = (radians(30.0), radians(30.0), radians(40.0))
    tvrange = 8000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.2
    datalinkrecv = True
    datalinksend = True
    rcs = 0.0100
    irmuffle = 0.2
    iraspect = 0.5

    hitboxdata = [(Point3(0.0, 6.3, 0.2), 1.1, 2.6, 1.2),
                  (Point3(0.0, 0.1, 0.1), 1.9, 3.7, 1.2),
                  (Point3(-2.2, -5.4, 0.3), 1.3, 1.2, 0.2),
                  (Point3(+2.2, -5.4, 0.3), 1.3, 1.2, 0.2),
                  #Left wing
                  (Point3(-3.7, -0.9, 0.3), 1.8, 2.1, 0.2),
                  #Right wing
                  (Point3(+3.7, -0.9, 0.3), 1.8, 2.1, 0.2)]
    hitboxcritdata = [(Point3(0.00, -4.48, 0.02), 0.9)]
    vortexdata = [Point3(-5.5, -1.7, 0.3), Point3(5.5, -1.7, 0.3)]
    fmodelpath = "models/aircraft/f35/f35b.egg"
    modelpath = ["models/aircraft/f35/f35b-1.egg",
                 "models/aircraft/f35/f35b-2.egg",
                 "models/aircraft/f35/f35b-3.egg"]
    sdmodelpath = "models/aircraft/f35/f35b-shotdown.egg"
    shdmodelpath = "models/aircraft/f35/f35b-shadow.egg"
    glossmap = "models/aircraft/f35/f35b_gls.png"
    pilottexture = "models/aircraft/pilots/pilot_adv_tex.png"
    pilotglossmap = "models/aircraft/pilots/pilot_adv_gls.png"
    engsoundname = "engine-f22"
    flybysoundname = "flyby-f35"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(1.57, 3.78, 0.46),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(1.57, 3.78, 0.56),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [#INTERNAL PYLONS MISSING!
                       (Point3(-3.25, -0.35, -0.20), Vec3()),
                       (Point3( 3.25, -0.35, -0.20), Vec3()),
                       (Point3(-4.28, -0.98, -0.20), Vec3()),
                       (Point3( 4.28, -0.98, -0.20), Vec3()),
                       (Point3(-4.96, -1.19, -0.07), Vec3()),
                       (Point3( 4.96, -1.19, -0.07), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -4.30, 0.02),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -5.20, -0.02),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)


class F14 (Plane):

    species = "f14"
    longdes = _("Grumman F-14 Tomcat")
    shortdes = _("F-14")

    minmass = 15000.0
    maxmass = 30000.0
    wingarea = 56.0
    wingaspect = 3.0
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(24.0)
    maxthrust = 77e3 * 2
    maxthrustab = 112e3 * 2
    thrustincab = 1.6
    maxload = 9.0
    refmass = 20000.0
    maxspeedz = 310.0
    maxspeedabz = 420.0
    maxclimbratez = 260.0
    cloptspeedz = 280.0
    maxspeedh = 330.0
    maxspeedabh = 670.0
    maxrollratez = radians(320.0)
    maxpitchratez = radians(50.0)
    maxfuel = 6100.0
    refsfcz = 0.70 / 3.6e4
    refsfcabz = 1.80 / 3.6e4
    sfcincab = 1.0
    reldragbrake = 2.0
    varsweepmach = (0.45, 0.90)

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 14.0), radians(90 - 10.0), radians(180 - 25.0))
    radarrange = 80000.0
    radarangle = (radians(35.0), radians(35.0), radians(50.0))
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 7.0
    irmuffle = 1.0
    iraspect = 0.5

    hitboxdata = [
        HitboxData(name="hull",
                   colldata=[(Point3(0.0,  6.6, 0.5), 1.0, 4.7, 1.3),
                             (Point3(0.0, -0.1, 0.0), 2.9, 5.2, 1.1)]),
        HitboxData(name="rwng",
                   colldata=[(Point3( 6.2, -1.1, 0.4), 3.3, 1.5, 0.2)]),
        HitboxData(name="lwng",
                   colldata=[(Point3(-6.2, -1.1, 0.4), 3.3, 1.5, 0.2)]),
    ]
    hitboxcritdata = [(Point3(-1.5, -6.2, -0.2), 0.9),
                      (Point3( 1.5, -6.2, -0.2), 0.9)]
    vortexdata = [Point3(-9.5, -2.3, 0.3), Point3(9.5, -2.3, 0.3)]
    fmodelpath = "models/aircraft/f14/f14.egg"
    modelpath = ["models/aircraft/f14/f14-1.egg",
                 "models/aircraft/f14/f14-2.egg",
                 "models/aircraft/f14/f14-3.egg"]
    sdmodelpath = "models/aircraft/f14/f14-shotdown.egg"
    shdmodelpath = "models/aircraft/f14/f14-shadow.egg"
    glossmap = "models/aircraft/f14/f14_gls.png"
    engsoundname = "engine-f18"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_front("nose"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail_left"),
        breakup_small_up("tail_right"),
    ]
    varsweeprange = (radians(20.0), radians(68.0))
    varsweeppivot = (Point2(-2.82, 0.25), Point2(2.82, 0.25))
    varsweepspeed = radians(8.0)
    varsweephitbox = ("lwng", "rwng")
    varsweepmodelmin = True

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(-0.59, 8.6, -0.18),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(-0.59, 8.7, -0.18),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3( 0.00, -1.88, -0.43), Vec3()),
                       (Point3( 0.00,  1.52, -0.43), Vec3()),
                       (Point3( 0.54,  3.64, -0.38), Vec3()),
                       (Point3( 0.54,  3.64, -0.38), Vec3()),
                       (Point3(-3.28,  0.77, -0.50), Vec3()),
                       (Point3( 3.28,  0.77, -0.50), Vec3()),
                       (Point3(-3.60,  0.82, -0.06), Vec3()),
                       (Point3( 3.60,  0.82, -0.06), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(1.48, -5.20, -0.25),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -6.00, -0.25),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-1.48, -5.20, -0.25),
                               radius0=0.55, radius1=0.50, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.8,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F4 (Plane):

    species = "f4"
    longdes = _("McDonnell-Douglas F-4 Phantom II")
    shortdes = _("F-4")

    minmass = 14000.0
    maxmass = 28000.0
    wingarea = 49.2
    wingaspect = 2.8
    wingspeff = 0.70
    zlaoa = radians(-2.0)
    maxaoa = radians(22.0)
    maxthrust = 53e3 * 2
    maxthrustab = 79e3 * 2
    thrustincab = 1.4
    maxload = 7.0
    refmass = 17000.0
    maxspeedz = 320.0
    maxspeedabz = 400.0
    maxclimbratez = 210.0
    cloptspeedz = 270.0
    maxspeedh = 290.0
    maxspeedabh = 620.0
    maxrollratez = radians(240.0)
    maxpitchratez = radians(50.0)
    maxfuel = 6200.0
    refsfcz = 0.85 / 3.6e4
    refsfcabz = 2.20 / 3.6e4
    sfcincab = 1.2
    reldragbrake = 2.0

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 25.0), radians(180 - 30.0))
    radarrange = 50000.0
    radarangle = (radians(30.0), radians(30.0), radians(40.0))
    irstrange = None
    irstangle = None
    tvrange = 5000.0
    tvangle = (radians(-70.0), radians(5.0), radians(30.0))
    rwrwash = 0.7
    datalinkrecv = False
    datalinksend = False
    rcs = 7.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.4, 0.7), 1.6),
                  # (Point3(0.0, 2.2, 0.7), 1.8),
                  # (Point3(0.0, -1.0, 0.7), 1.8),
                  # (Point3(0.0, -6.2, 2.0), 1.4),
                  # #Left wing
                  # (Point3(-3.0, -0.6, 0.0), 1.2),
                  # #Right wing
                  # (Point3(+3.0, -0.6, 0.0), 1.2)]
    hitboxdata = [(Point3(0.0,  3.9, 0.7), 1.5, 6.5, 1.3),
                  (Point3(0.0, -6.2, 2.5), 0.15, 2.0, 1.0),
                  #Left wing
                  (Point3(-3.9, 0.0, 0.2), 2.4, 3.0, 0.3),
                  #Right wing
                  (Point3(+3.9, 0.0, 0.2), 2.4, 3.0, 0.3),]
    hitboxcritdata = [(Point3(0.0, -3.8, 0.6), 1.4)]
    vortexdata = [Point3(-6.2, -2.7, 0.4), Point3(6.2, -2.7, 0.4)]
    fmodelpath = "models/aircraft/f4/f4.egg"
    modelpath = ["models/aircraft/f4/f4-1.egg",
                 "models/aircraft/f4/f4-2.egg",
                 "models/aircraft/f4/f4-3.egg"]
    sdmodelpath = "models/aircraft/f4/f4-shotdown.egg"
    glossmap = "models/aircraft/f4/f4_gls.png"
    engsoundname = "engine-f16"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[600], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = M61(parent=self,
                     mpos=Point3(0.0, 9.2, -0.4),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.0, 10.2, -0.4),
                     ammo=cnammo[0], viseach=5,
                     reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-1.86, 2.26, -0.41), Vec3()),
                       (Point3( 1.86, 2.26, -0.41), Vec3()),
                       (Point3(-2.24, 2.26, -0.41), Vec3()),
                       (Point3( 2.24, 2.26, -0.41), Vec3()),
                       (Point3(-3.32, -0.40, -0.48), Vec3()),
                       (Point3( 3.32, -0.40, -0.48), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.63, -4.05, 0.11),
                               radius0=0.50, radius1=0.45, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -4.85, 0.11),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.63, -4.05, 0.11),
                               radius0=0.50, radius1=0.45, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class F5 (Plane):

    species = "f5e"
    longdes = _("Northrop F-5E")
    shortdes = _("F-5E")

    minmass = 4400.0
    maxmass = 9700.0
    wingarea = 17.3
    wingaspect = 3.8
    wingspeff = 0.70
    zlaoa = radians(-2.0)
    maxaoa = radians(18.0)
    maxthrust = 15e3 * 2
    maxthrustab = 23e3 * 2
    thrustincab = 1.2
    maxload = 8.0
    refmass = 6000.0
    maxspeedz = 300.0
    maxspeedabz = 360.0
    maxclimbratez = 150.0
    cloptspeedz = 250.0
    maxspeedh = 280.0
    maxspeedabh = 430.0
    maxrollratez = radians(360.0)
    maxpitchratez = radians(60.0)
    maxfuel = 2000.0
    refsfcz = 1.00 / 3.6e4
    refsfcabz = 2.00 / 3.6e4
    sfcincab = 1.3
    reldragbrake = 2.0

    strength = 5.0
    minhitdmg = 0.0
    maxhitdmg = 3.0
    dmgtime = 6.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 12.0), radians(90 - 20.0), radians(180 - 25.0))
    radarrange = 30000.0
    radarangle = (radians(25.0), radians(25.0), radians(30.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = 0.7
    datalinkrecv = False
    datalinksend = False
    rcs = 3.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 5.0, 0.3), 1.0),
                  # (Point3(0.0, 3.0, 0.4), 1.2),
                  # (Point3(0.0, 0.8, 0.4), 1.2),
                  # (Point3(0.0, -1.4, 0.4), 1.2),
                  # (Point3(0.0, -3.8, 0.7), 1.2),
                  # #Left wing
                  # (Point3(-2.2, -0.8, 0.0), 1.0),
                  # #Right wing
                  # (Point3(+2.2, -0.8, 0.0), 1.0)]
    hitboxdata = [(Point3(0.0, 3.5, 0.5), 0.6, 5.1, 0.9),
                  (Point3(0.0, -1.0, 0.2), 1.1, 3.8, 0.8),
                  (Point3(0.0, -4.3, 2.0), 0.1, 1.0, 1.0),
                  #Left wing
                  (Point3(-2.7, -0.4, 0.0), 1.6, 1.6, 0.15),
                  #Right wing
                  (Point3(+2.7, -0.4, 0.0), 1.6, 1.6, 0.15)]
    hitboxcritdata = [(Point3(0.0, -5.5, 0.3), 0.7)]
    vortexdata = [Point3(-4.2, -1.3, 0.0), Point3(4.2, -1.3, 0.0)]
    fmodelpath = "models/aircraft/f5/f5.egg"
    modelpath = ["models/aircraft/f5/f5-1.egg",
                 "models/aircraft/f5/f5-2.egg",
                 "models/aircraft/f5/f5-3.egg"]
    sdmodelpath = "models/aircraft/f5/f5-shotdown.egg"
    shdmodelpath = "models/aircraft/f5/f5-shadow.egg"
    glossmap = "models/aircraft/f5/f5_gls.png"
    engsoundname = "engine-f16"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_small_front("nose"),
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_left("stabilator_left"),
        breakup_small_right("stabilator_right"),
        breakup_small_up("tail"),
        breakup_engine_down("nozzle_p2"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[280, 280], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon1 = M39(parent=self,
                      mpos=Point3(0.225, 6.718, 0.453),
                      mhpr=Vec3(0.0, 0.0, 0.0),
                      mltpos=Point3(0.0, 7.718, 0.453),
                      ammo=cnammo[0], viseach=5,
                      reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon1)
        cannon2 = M39(parent=self,
                      mpos=Point3(-0.225, 6.718, 0.453),
                      mhpr=Vec3(0.0, 0.0, 0.0),
                      mltpos=None,
                      ammo=cnammo[1], viseach=5,
                      reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon2)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-2.65, -0.70, -0.27), Vec3()),
                       (Point3( 2.65, -0.70, -0.27), Vec3()),
                       (Point3(-3.25, -0.90, -0.27), Vec3()),
                       (Point3( 3.25, -0.90, -0.27), Vec3()),
                       (Point3(-4.23, -0.65, -0.05), Vec3()),
                       (Point3( 4.23, -0.65, -0.05), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.31, -5.95, 0.30),
                               radius0=0.30, radius1=0.25, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -6.75, 0.11),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.31, -5.95, 0.30),
                               radius0=0.30, radius1=0.25, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class A10 (Plane):

    species = "a10"
    longdes = _("Fairchild-Republic A-10 Thunderbolt II")
    shortdes = _("A-10")

    minmass = 11500.0
    maxmass = 23000.0
    wingarea = 47.0
    wingaspect = 6.5
    wingspeff = 0.80
    zlaoa = radians(-4.0)
    maxaoa = radians(10.0)
    maxthrust = 40e3 * 2
    maxthrustab = None
    thrustincab = None
    maxload = 4.5
    refmass = 16000.0
    maxspeedz = 210.0
    maxspeedabz = None
    maxclimbratez = 40.0
    cloptspeedz = 190.0
    maxspeedh = 190.0
    maxspeedabh = None
    maxrollratez = radians(120.0)
    maxpitchratez = radians(25.0)
    maxfuel = 6500.0
    refsfcz = 0.55 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 2.0

    strength = 16.0
    minhitdmg = 0.5
    maxhitdmg = 12.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 12.0), radians(90 - 15.0), radians(180 - 30.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 6.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3( 0.0,  4.5, 0.6), 1.6),
                  # (Point3( 0.0,  1.5, 0.5), 1.6),
                  # (Point3( 0.0, -1.5, 0.5), 1.3),
                  # (Point3( 0.0, -6.0, 0.6), 1.1),
                  # #Left wing
                  # (Point3(-2.5, -0.5, 0.2), 1.2),
                  # (Point3(-5.3, -0.5, 0.2), 1.2),
                  # #Right wing
                  # (Point3(+2.5, -0.5, 0.2), 1.2),
                  # (Point3(+5.3, -0.5, 0.2), 1.2)]
    # hitboxcritdata = [(Point3( 0.0, -3.6, 0.5), 0.8),
                      # (Point3(-1.5, -3.2, 1.2), 1.0),
                      # (Point3( 1.5, -3.2, 1.2), 1.0)]
    hitboxdata = [(Point3( 0.0,  4.75, 0.7), 0.8, 3.45, 1.25),
                  (Point3( 0.0,  -3.4, 0.6), 0.7,  4.7,  0.9),
                  (Point3( 0.0,  -6.9, 0.4), 3.1,  1.0,  0.2),
                  #Left wing
                  (Point3(-4.8, -0.3, 0.2), 4.1, 1.6, 0.6),
                  #Right wing
                  (Point3(+4.8, -0.3, 0.2), 4.1, 1.6, 0.6)]
    hitboxcritdata = [(Point3(-1.5, -3.2, 1.2), 0.8, 1.8, 0.85),
                      (Point3( 1.5, -3.2, 1.2), 0.8, 1.8, 0.85)]
    vortexdata = [Point3(-8.9, -0.6, 0.4), Point3(8.9, -0.6, 0.4)]
    fmodelpath = "models/aircraft/a10/a10.egg"
    modelpath = ["models/aircraft/a10/a10-1.egg",
                 "models/aircraft/a10/a10-2.egg",
                 "models/aircraft/a10/a10-3.egg"]
    sdmodelpath = "models/aircraft/a10/a10-shotdown.egg"
    shdmodelpath = "models/aircraft/a10/a10-shadow.egg"
    glossmap = "models/aircraft/a10/a10_gls.png"
    engsoundname = "engine-f18"
    flybysoundname = "flight-a10flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_engine_left("engine_left"),
        breakup_engine_right("engine_right"),
        breakup_small_left("tail_left"),
        breakup_small_right("tail_right"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[1200], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon = Gau8(parent=self,
                      mpos=Point3(-0.05, 8.2, -0.2),
                      mhpr=Vec3(0.0, 3.12, 0.0),
                      mltpos=Point3(-0.05, 9.2, -0.2),
                      ammo=cnammo[0], viseach=5,
                      reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-0.00, 0.40, -0.50), Vec3()),
                       (Point3(-0.56, 0.50, -0.50), Vec3()),
                       (Point3( 0.56, 0.50, -0.50), Vec3()),
                       (Point3(-1.68, 0.55, -0.50), Vec3()),
                       (Point3( 1.68, 0.55, -0.50), Vec3()),
                       (Point3(-3.62, 0.45, -0.38), Vec3()),
                       (Point3( 3.62, 0.45, -0.38), Vec3()),
                       (Point3(-4.84, 0.36, -0.23), Vec3()),
                       (Point3( 4.84, 0.36, -0.23), Vec3()),
                       (Point3(-5.90, 0.07, -0.04), Vec3()),
                       (Point3( 5.90, 0.07, -0.04), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(1.46, -4.5, 1.13),
                               radius0=0.30, radius1=0.25, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -5.25, 1.13),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-1.46, -4.5, 1.13),
                               radius0=0.30, radius1=0.25, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Mirage2000 (Plane):

    species = "mirage2000"
    longdes = _("Dassault Mirage 2000")
    shortdes = _("Mirage 2000")

    minmass = 8000.0
    maxmass = 17000.0
    wingarea = 41.0
    wingaspect = 2.0
    wingspeff = 0.60
    zlaoa = radians(-1.0)
    maxaoa = radians(24.0)
    maxthrust = 68e3
    maxthrustab = 102e3
    thrustincab = 1.4
    maxload = 9.0
    refmass = 10000.0
    maxspeedz = 310.0
    maxspeedabz = 420.0
    maxclimbratez = 260.0
    cloptspeedz = 290.0
    maxspeedh = 300.0
    maxspeedabh = 630.0
    maxrollratez = radians(420.0)
    maxpitchratez = radians(50.0)
    maxfuel = 3200.0
    refsfcz = 0.75 / 3.6e4
    refsfcabz = 1.90 / 3.6e4
    sfcincab = 1.1
    reldragbrake = 2.0

    strength = 6.0
    minhitdmg = 0.0
    maxhitdmg = 4.0
    dmgtime = 8.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 12.0), radians(90 - 15.0), radians(180 - 25.0))
    radarrange = 60000.0
    radarangle = (radians(30.0), radians(30.0), radians(35.0))
    irstrange = None
    irstangle = None
    tvrange = 5000.0
    tvangle = (radians(-70.0), radians(5.0), radians(30.0))
    rwrwash = 0.4
    datalinkrecv = True
    datalinksend = False
    rcs = 3.6
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 4.5, 0.2), 1.1),
                  # (Point3(0.0, 2.2, 0.2), 1.2),
                  # (Point3(0.0, -0.4, 0.2), 1.4),
                  # (Point3(0.0, -3.2, 0.7), 1.5),
                  # #Left wing
                  # (Point3(-2.4, -2.0, -0.4), 1.0),
                  # #Right wing
                  # (Point3(+2.4, -2.0, -0.4), 1.0)]
    hitboxdata = [(Point3(0.0,  5.2, 0.1), 0.5, 2.8, 0.9),
                  (Point3(0.0, -0.6, 0.1), 1.0, 4.0, 0.8),
                  (Point3(0.0, -4.3, 2.1), 0.1, 1.4, 1.2),
                  #Left wing
                  (Point3(-2.3, -0.9, -0.3), 1.4, 2.8, 0.4),
                  #Right wing
                  (Point3(+2.3, -0.9, -0.3), 1.4, 2.8, 0.4),]
    hitboxcritdata = [(Point3(0.0, -5.2, 0.2), 0.8)]
    vortexdata = [Point3(-4.6, -3.4, -0.6), Point3(4.6, -3.4, -0.6)]
    fmodelpath = "models/aircraft/mirage2000/mirage2000.egg"
    modelpath = ["models/aircraft/mirage2000/mirage2000-1.egg",
                 "models/aircraft/mirage2000/mirage2000-2.egg",
                 "models/aircraft/mirage2000/mirage2000-3.egg"]
    sdmodelpath = "models/aircraft/mirage2000/mirage2000-shotdown.egg"
    shdmodelpath = "models/aircraft/mirage2000/mirage2000-shadow.egg"
    glossmap = "models/aircraft/mirage2000/mirage2000_gls.png"
    engsoundname = "engine-f16"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_up("tail"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[125, 125], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        cannon1 = Defa554(parent=self,
                          mpos=Point3(0.31, 2.46, -0.49),
                          mhpr=Vec3(0.0, 0.0, 0.0),
                          mltpos=Point3(0.0, 2.46, -0.39),
                          ammo=cnammo[0], viseach=5,
                          reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon1)
        cannon2 = Defa554(parent=self,
                          mpos=Point3(-0.31, 2.46, -0.49),
                          mhpr=Vec3(0.0, 0.0, 0.0),
                          mltpos=None,
                          ammo=cnammo[1], viseach=5,
                          reloads=cnrnum, relrate=cnrrate)
        self.cannons.append(cannon2)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3( 0.0, 0.17, -0.92), Vec3()),

                       (Point3( 0.83,  2.31, -0.64), Vec3()),
                       (Point3(-0.83,  2.31, -0.64), Vec3()),

                       (Point3( 0.93, -2.02, -0.63), Vec3()),
                       (Point3(-0.93, -2.02, -0.63), Vec3()),

                       (Point3( 2.38,  0.01, -0.77), Vec3()),
                       (Point3(-2.38,  0.01, -0.77), Vec3()),

                       (Point3( 3.31, -1.83, -0.77), Vec3()),
                       (Point3(-3.31, -1.83, -0.77), Vec3())]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.00, -5.0, 0.17),
                               radius0=0.65, radius1=0.55, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.00, -5.50, 0.17),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)


class F117 (Plane):

    species = "f117"
    longdes = _("Lockheed F-117 Nighthawk")
    shortdes = _("F-117")

    minmass = 14000.0
    maxmass = 24000.0
    wingarea = 73.0
    wingaspect = 2.4
    wingspeff = 0.50
    zlaoa = radians(-2.0)
    maxaoa = radians(14.0)
    maxthrust = 48e3 * 2
    maxthrustab = None
    thrustincab = None
    maxload = 5.0
    refmass = 18000.0
    maxspeedz = 310.0
    maxspeedabz = None
    maxclimbratez = 100.0
    cloptspeedz = 250.0
    maxspeedh = 270.0
    maxspeedabh = None
    maxrollratez = radians(180.0)
    maxpitchratez = radians(40.0)
    maxfuel = 5800.0
    refsfcz = 0.80 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 2.0

    strength = 10.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 8.0
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(30.0), radians(120.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = 6000.0
    tvangle = (radians(-75.0), radians(5.0), radians(60.0))
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 0.0001
    irmuffle = 0.05
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 4.2, 0.8), 1.8),
                  # (Point3(0.0, 0.6, 0.7), 2.0),
                  # (Point3(0.0, -3.4, 0.5), 2.0),
                  # (Point3(0.0, -7.4, 0.6), 1.8),
                  # #Left wing
                  # (Point3(-3.5, -3.2, 0.2), 1.4),
                  # #Right wing
                  # (Point3(+3.5, -3.2, 0.2), 1.4)]
    hitboxdata = [(Point3(0.0, -0.7, 1.0), 2.8, 8.0, 1.3),
                  #Wings
                  (Point3(0.0, -2.7, 0.0), 4.9, 3.3, 0.3)]
    hitboxcritdata = []
    vortexdata = [Point3(-6.6, -7.4, 0.0), Point3(6.6, -7.4, 0.0)]
    fmodelpath = "models/aircraft/f117/f117.egg"
    modelpath = ["models/aircraft/f117/f117-1.egg",
                 "models/aircraft/f117/f117-2.egg",
                 "models/aircraft/f117/f117-3.egg"]
    sdmodelpath = "models/aircraft/f117/f117-shotdown.egg"
    shdmodelpath = "models/aircraft/f117/f117-shadow.egg"
    glossmap = "models/aircraft/f117/f117_gls.png"
    engsoundname = None
    flybysoundname = None
    breakupdata = [
        breakup_small_left("rudder_left"), # before "tail_left"
        breakup_small_left("tail_left"),
        breakup_small_right("rudder_right"), # before "tail_left"
        breakup_small_right("tail_right")
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(1.4, -6.1, -0.05),
                               radius0=0.60, radius1=0.55, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust04.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -7.27, -0.085),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-1.4, -6.1, -0.05),
                               radius0=0.60, radius1=0.55, length=5.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust04.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class Ea6b (Plane):

    species = "ea6b"
    longdes = _("Grumman EA-6B Prowler")
    shortdes = _("EA-6B")

    minmass = 15000.0
    maxmass = 28000.0
    wingarea = 49.1
    wingaspect = 5.2
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(14.0)
    maxthrust = 44e3 * 2
    maxthrustab = None
    thrustincab = None
    maxload = 4.5
    refmass = 18000.0
    maxspeedz = 290.0
    maxspeedabz = None
    maxclimbratez = 60.0
    cloptspeedz = 230.0
    maxspeedh = 270.0
    maxspeedabh = None
    maxrollratez = radians(140.0)
    maxpitchratez = radians(30.0)
    maxfuel = 7000.0
    refsfcz = 0.90 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 2.0

    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 4.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 25.0), radians(180 - 35.0))
    radarrange = 60000.0
    radarangle = (radians(30.0), radians(30.0), radians(45.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 8.0
    irmuffle = 1.0
    iraspect = 0.5

    # hitboxdata = [(Point3(0.0, 4.6, 0.4), 1.7),
                  # (Point3(0.0, 1.0, 0.4), 2.0),
                  # (Point3(0.0, -5.2, 0.6), 1.2),
                  # (Point3(0.0, -8.0, 1.8), 1.7),
                  # #Left wing
                  # (Point3(-2.8, -1.7, 0.6), 1.4),
                  # (Point3(-5.4, -2.6, 0.6), 1.2),
                  # #Right wing
                  # (Point3(+2.8, -1.7, 0.6), 1.4),
                  # (Point3(+5.4, -2.6, 0.6), 1.2)]
    hitboxdata = [(Point3(0.0,  3.1, 0.4), 1.5, 4.3, 1.3),
                  (Point3(0.0, -6.6, 0.6), 0.8, 2.6, 0.8),
                  (Point3(0.0, -8.6, 1.9), 0.4, 1.8, 1.8),
                  #Left wing
                  (Point3(-4.8, -1.9, 0.5), 3.4, 2.5, 0.2),
                  #Right wing
                  (Point3(+4.8, -1.9, 0.5), 3.4, 2.5, 0.2),]
    hitboxcritdata = [(Point3(0.0, -2.6, 0.6), 1.5)]
    vortexdata = [Point3(-8.1, -3.6, 0.5), Point3(8.1, -3.6, 0.5)]
    fmodelpath = "models/aircraft/ea6b/ea6b.egg"
    modelpath = ["models/aircraft/ea6b/ea6b-1.egg",
                 "models/aircraft/ea6b/ea6b-2.egg",
                 "models/aircraft/ea6b/ea6b-3.egg"]
    sdmodelpath = "models/aircraft/ea6b/ea6b-shotdown.egg"
    shdmodelpath = "models/aircraft/ea6b/ea6b-shadow.egg"
    glossmap = "models/aircraft/ea6b/ea6b_gls.png"
    engsoundname = "engine-f16"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_small_up("tail"),
        breakup_small_right("tail_fin_right"),
        breakup_small_left("tail_fin_left"),
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, lnammo=[]):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        # List pylons from innermost to outermost, left then right.
        # List missiles from bigger to smaller.
        self.pylons = [(Point3(-3.71, -1.31, -0.11), Vec3()),
                       (Point3(+3.71, -1.31, -0.11), Vec3()),
                       (Point3(+0.00, +0.78, -0.93), Vec3()),]
        self._init_pylon_handlers(lnammo, fuelfill)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.92, -2.9, 0.11),
                               radius0=0.30, radius1=0.25, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -7.10, -0.075),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-0.92, -2.9, 0.11),
                               radius0=0.30, radius1=0.25, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)


class B1b (Plane):

    species = "b1b"
    longdes = _("Rockwell B-1B Lancer")
    shortdes = _("B-1B")

    # FIXME: Jumbled data across sweeps; differentiate when possible.
    minmass = 87000.0
    maxmass = 215000.0
    wingarea = 181.0
    wingaspect = 7.2 # 3.1 swept, 9.5 unswept
    wingspeff = 0.80
    zlaoa = radians(-2.0)
    maxaoa = radians(18.0)
    maxthrust = 76e3 * 4
    maxthrustab = 135e3 * 4
    thrustincab = 1.2
    maxload = 2.5
    refmass = 140000.0
    maxspeedz = 280.0
    maxspeedabz = 320.0
    maxclimbratez = 80.0
    cloptspeedz = 300.0
    maxspeedh = 280.0
    maxspeedabh = 390.0
    maxrollratez = radians(60.0)
    maxpitchratez = radians(15.0)
    maxfuel = 90000.0
    refsfcz = 0.60 / 3.6e4
    refsfcabz = 1.80 / 3.6e4
    sfcincab = 1.2
    reldragbrake = 0.0
    varsweepmach = (0.60, 0.90)

    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(120.0))
    radarrange = 40000.0
    radarangle = (radians(30.0), radians(30.0), radians(40.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = 0.3
    datalinkrecv = True
    datalinksend = False
    rcs = 10.0
    irmuffle = 1.0
    iraspect = 0.5

    flarechaff = 240
    flchlaunchtype = 1
    flchvistype = 1
    flchmanouver = False

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, 16.0, 0.0), 3.0),
                             # (Point3(0.0, 10.0, 0.0), 3.6),
                             # (Point3(0.0, 3.0, 0.0), 3.8),
                             # (Point3(0.0, -4.0, 0.0), 3.6),
                             # (Point3(0.0, -15.0, 2.0), 2.8)],
                   colldata=[(Point3(0.0,   6.2,  0.3), 1.2, 20.3, 1.8),
                             (Point3(0.0,  13.3, -0.1), 2.5,  6.9, 1.5),
                             (Point3(0.0,   1.7, -0.8), 5.4,  8.1, 2.0)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng",
                   colldata=[(Point3(+3.5, -8.0, -1.5), 2.0)],
                   longdes=_("right engine"), shortdes=_("RENG"),
                   selectable=True),
        HitboxData(name="leng",
                   colldata=[(Point3(-3.5, -8.0, -1.5), 2.0)],
                   longdes=_("left engine"), shortdes=_("LENG"),
                   selectable=True),
        HitboxData(name="rwng",
                   colldata=[(Point3(+7.0, -6.0, -1.0), 1.6),
                             (Point3(+8.2, -9.0, -1.0), 1.6),
                             (Point3(+9.5, -12.0, -1.0), 1.6)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   colldata=[(Point3(-7.0, -6.0, -1.0), 1.6),
                             (Point3(-8.2, -9.0, -1.0), 1.6),
                             (Point3(-9.5, -12.0, -1.0), 1.6)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
        HitboxData(name="tail",
                   colldata=[(Point3(0.0, -16.6,  2.9), 0.6,  2.5, 3.8)],
                   longdes=_("tail"), shortdes=_("TAIL"),
                   selectable=True),
    ]
    fmodelpath = "models/aircraft/b1b/b1b.egg"
    modelpath = ["models/aircraft/b1b/b1b-1.egg",
                 "models/aircraft/b1b/b1b-2.egg",
                 "models/aircraft/b1b/b1b-3.egg"]
    sdmodelpath = "models/aircraft/b1b/b1b-shotdown.egg"
    shdmodelpath = "models/aircraft/b1b/b1b-lowpoly-shadow.egg"
    normalmap = "images/_normalmap_none.png"
    glowmap = "models/aircraft/b1b/b1b_gw.png"
    glossmap = "models/aircraft/b1b/b1b_gls.png"
    engsoundname = "engine-b1b"
    flybysoundname = "flyby-b1b"
    ejectdata = [
        [0.00, 4.00, radians(15.0)],
        [0.00, 2.00, radians(-15.0)],
        [0.00, 1.00, radians(15.0)],
        [0.00, 1.00, radians(-15.0)],
    ]
    varsweeprange = (radians(15.0), radians(67.5))
    varsweeppivot = (Point2(-3.50, 1.00), Point2(3.50, 1.00))
    varsweepspeed = radians(6.0)
    varsweephitbox = ("lwng", "rwng")
    varsweepmodelmin = False

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, trammo=[1200, 1200, 1200]):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(2.63, -8.0, -1.79),
                               radius0=0.80, radius1=0.75, length=10.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -9.0, -1.79),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=300.0, hidedist=3000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)

        exhaust2 = PolyExhaust(parent=self, pos=Point3(-2.63, -8.0, -1.79),
                               radius0=0.80, radius1=0.75, length=10.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=300.0, hidedist=3000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust2)

        exhaust3 = PolyExhaust(parent=self, pos=Point3(4.355, -8.0, -1.79),
                               radius0=0.80, radius1=0.75, length=10.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=300.0, hidedist=3000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust3)

        exhaust4 = PolyExhaust(parent=self, pos=Point3(-4.355, -8.0, -1.79),
                               radius0=0.80, radius1=0.75, length=10.0,
                               speed=20.0, poolsize=18,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=300.0, hidedist=3000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust4)

        # Turrets.
        self._turret_door_up_1 = []
        for nd in self.node.findAllMatches("**/%s" % "turret_door_up"):
            self._turret_door_up_1.append((nd, nd.getY(), nd.getZ(), nd.getP()))
        self._turret_door_down_1 = []
        for nd in self.node.findAllMatches("**/%s" % "turret_door_down"):
            self._turret_door_down_1.append((nd, nd.getY(), nd.getZ(), nd.getP()))
        turret1 = CustomTurret(parent=self,
                               world=world, name="tail", side=side,
                               turnrate = radians(120.0), elevrate = radians(60.0),
                               hcenter=180, harc=150, pcenter=0, parc=150,
                               storepos=Point3(0.023, -18.545, -0.254),
                               storespeed=0.5,
                               storedecof=self._store_turret_deco_1,
                               pos=Point3(0.023, -19.745, -0.254),
                               shellspread=((0.0, 0.2), (60.0, 2.0)),
                               modelpath=(self.node, "turret"),
                               texture=texture, normalmap=self.normalmap,
                               glossmap=self.glossmap, glowmap=self.glowmap)
        cannon1 = M61(parent=turret1,
                      mpos=Point3(0.0, 1.28, 0.05),
                      mhpr=Vec3(0.0, 0.0, 0.0),
                      mltpos=Point3(0.0, 1.7, 0.0),
                      ammo=1200, viseach=5)
        turret1.add_cannon(cannon1)
        self.turrets.append(turret1)

        self._hbx_hull.hitpoints = 120
        self._hbx_reng.hitpoints = 20
        self._hbx_leng.hitpoints = 20
        self._hbx_rwng.hitpoints = 60
        self._hbx_lwng.hitpoints = 60
        self._hbx_tail.hitpoints = 80

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng.minhitdmg = 0
        self._hbx_leng.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0
        self._hbx_tail.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 70
        self._hbx_reng.maxhitdmg = 15
        self._hbx_leng.maxhitdmg = 15
        self._hbx_rwng.maxhitdmg = 20
        self._hbx_lwng.maxhitdmg = 20
        self._hbx_tail.maxhitdmg = 30

        self._hbx_hull.out = False
        self._hbx_reng.out = False
        self._hbx_leng.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False
        self._hbx_tail.out = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            self._hbx_leng.hitpoints = 0
            self._hbx_reng.hitpoints = 0
            self._hbx_hull.out = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.4,
                emradfact=fx_uniform(0.6, 1.0),
                fpos=None,
                spos=Point3(5.0, -1.0, -1.0), #self._hbx_rwng.center,
                slifespan=0.6,
                stcol=0.2)
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.4,
                emradfact=fx_uniform(0.6, 1.0),
                fpos=None,
                spos=Point3(-5.0, -1.0, -1.0), #self._hbx_lwng.center,
                slifespan=0.6,
                stcol=0.2)
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng.hitpoints <= 0 and not self._hbx_reng.out:
            self.explode_minor(offset=self._hbx_reng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(1.0, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 104, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(3.5, -6.0, -1.5),
                fpoolsize=16,
                flength=24.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(3.5, -6.0, -1.5),
                slifespan=2.8,
                stcol=0.1)
            self._hbx_reng.out = True
            self._failure_full = True
        if self._hbx_leng.hitpoints <= 0 and not self._hbx_leng.out:
            self.explode_minor(offset=self._hbx_leng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(1.0, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 104, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(-3.5, -6.0, -1.5),
                fpoolsize=16,
                flength=24.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(-3.5, -6.0, -1.5),
                slifespan=2.8,
                stcol=0.1)
            self._hbx_leng.out = True
            self._failure_full = True
        if self._hbx_tail.hitpoints <= 0 and not self._hbx_tail.out:
            self.explode_minor(offset=self._hbx_tail.center)
            remove_subnodes(self._shotdown_modelnode, ("turret_doors", "tail_misc"))
            remove_subnodes(self.modelnode, ("turret_door_up", "turret_door_down"))
            self.turrets[0].destroy()
            self._hbx_tail.out = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if self._hbx_hull.out:
                remove_subnodes(self._shotdown_modelnode, ("fixed_external_misc_1",))
            if self._hbx_rwng.out:
                breakupdata = [breakup_medium_right("wing_right")]
                remove_subnodes(self._shotdown_modelnode, ("wing_right_misc",))
            if self._hbx_lwng.out:
                breakupdata = [breakup_medium_left("wing_left")]
                remove_subnodes(self._shotdown_modelnode, ("wing_left_misc",))
            if self._hbx_reng.out:
                breakupdata = [
                    breakup_engine_right("engine_right_1"),
                    breakup_engine_down("engine_right_2")
                    ]
            if self._hbx_leng.out:
                breakupdata = [
                    breakup_engine_left("engine_left_1"),
                    breakup_engine_down("engine_left_2")
                    ]
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            for turret in self.turrets:
                turret.set_auto_attack()

            self.set_shotdown(3.0)
            # for model in self.models:
                # model.flattenStrong()

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


    def _store_turret_deco_1 (self, stfac):

        dy = intl01vr(stfac, 0.0, 0.2, 0.0, 0.200)
        dz = intl01vr(stfac, 0.1, 0.4, 0.0, -0.100)
        dpitch = intl01vr(stfac, 0.1, 0.4, 0.0, 40.0)
        for nd, y_0, z_0, pitch_0 in self._turret_door_up_1:
            nd.setY(y_0 - dy)
            nd.setZ(z_0 + dz)
            nd.setP(pitch_0 - dpitch)
        for nd, y_0, z_0, pitch_0 in self._turret_door_down_1:
            nd.setY(y_0 - dy)
            nd.setZ(z_0 - dz)
            nd.setP(pitch_0 + dpitch)


class B52f (Plane):

    species = "b52f"
    longdes = _("Boeing B-52F Stratofortress")
    shortdes = _("B-52F")

    minmass = 90000.0
    maxmass = 220000.0
    wingarea = 370.0
    wingaspect = 8.5
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 75e3 * 8
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 130000.0
    maxspeedz = 260.0
    maxspeedabz = None
    maxclimbratez = 25.0
    cloptspeedz = 230.0
    maxspeedh = 290.0
    maxspeedabh = None
    maxrollratez = radians(30.0)
    maxpitchratez = radians(6.0)
    maxfuel = 144000.0
    refsfcz = 0.60 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 40.0
    irmuffle = 0.5
    iraspect = 0.3

    # minmass = 92000.0
    # maxmass = 190000.0
    # wingarea = 300.0
    # wingaspect = 8.5
    # wingspeff = 0.85
    # zlaoa = radians(-4.0)
    # maxaoa = radians(12.0)
    # maxthrust = 170e3 * 4
    # maxthrustab = None
    # thrustincab = None
    # maxload = 2.5
    # refmass = 130000.0
    # maxspeedz = 260.0
    # maxspeedabz = None
    # maxclimbratez = 50.0
    # cloptspeedz = 240.0
    # maxspeedh = 230.0
    # maxspeedabh = None
    # maxrollratez = radians(36.0)
    # maxpitchratez = radians(6.0)
    # maxfuel = 65000.0
    # refsfcz = 0.45 / 3.6e4
    # refsfcabz = None
    # sfcincab = None
    # reldragbrake = 0.0

    # strength = None
    # minhitdmg = None
    # maxhitdmg = None
    # dmgtime = None
    # visualtype = VISTYPE.TRANSPORT
    # visualangle = (radians(15.0), radians(20.0), radians(100.0))
    # radarrange = None
    # radarangle = None
    # irstrange = None
    # irstangle = None
    # tvrange = None
    # tvangle = None
    # rwrwash = None
    # datalinkrecv = False
    # datalinksend = False
    # rcs = 30.0
    # irmuffle = 0.4
    # iraspect = 0.3

    hitboxdata = [
        HitboxData(name="hull",
                   colldata=[(Point3(0.0,   2.2, 0.3), 1.6, 24.0, 2.2),
                             (Point3(0.0, -16.4, 7.1), 0.4,  3.2, 4.6),
                             (Point3(0.0, -17.0, 1.1), 7.2,  3.8, 0.3)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(10.3, 8.9, -0.6), 1.6)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-10.3, 8.9, -0.6), 1.6)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(18.1, 2.6, -1.0), 1.6)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-18.1, 2.6, -1.0), 1.6)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rtnk",
                   colldata=[(Point3(23.9, -4.3, -1.0), 0.6, 5.3, 0.6)],
                   longdes=_("right tank"), shortdes=_("RTNK"),
                   selectable=True),
        HitboxData(name="ltnk",
                   colldata=[(Point3(-23.9, -4.3, -1.0), 0.6, 5.3, 0.6)],
                   longdes=_("left tank"), shortdes=_("LTNK"),
                   selectable=True),
        HitboxData(name="rwng",
                   colldata=[(Point3( 6.6,  6.1,  1.0), 5.0, 5.9, 0.7),
                             (Point3(15.8,  0.4,  0.4), 4.2, 4.5, 0.5),
                             (Point3(23.0, -5.0, -0.1), 3.0, 3.8, 0.4)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   colldata=[(Point3( -6.6,  6.1,  1.0), 5.0, 5.9, 0.7),
                             (Point3(-15.8,  0.4,  0.4), 4.2, 4.5, 0.5),
                             (Point3(-23.0, -5.0, -0.1), 3.0, 3.8, 0.4)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    fmodelpath = "models/aircraft/b52f/b52f.egg"
    modelpath = ["models/aircraft/b52f/b52f-1.egg",
                 "models/aircraft/b52f/b52f-2.egg",
                 "models/aircraft/b52f/b52f-3.egg"]
    shdmodelpath = "models/aircraft/b52f/b52f-shadow.egg"
    glossmap = "models/aircraft/b52f/b52f_gls.png"
    engsoundname = "engine-b1b"
    flybysoundname = "flyby-b1b"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, trammo=[2400]):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        # Turrets.
        turret = CustomTurret(parent=self,
                              world=world, name=("%s-turret" % name), side=side,
                              turnrate=radians(120.0), elevrate=radians(120.0),
                              hcenter=180, harc=120, pcenter=0, parc=150,
                              shellspread=((0.0, 0.6), (60.0, 2.4)),
                              modelpath=(self.node, "turret"),
                              texture=texture, normalmap=self.normalmap,
                              glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(turret)

        cannon1 = M3(parent=turret,
                     mpos=Point3(-0.10, -22.45, 0.90),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.0, -22.85, 0.80),
                     ammo=(trammo[0] // 4), viseach=5)
        turret.add_cannon(cannon1)
        cannon2 = M3(parent=turret,
                     mpos=Point3(+0.10, -22.45, 0.90),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=None,
                     ammo=(trammo[0] // 4), viseach=5)
        turret.add_cannon(cannon2)
        cannon3 = M3(parent=turret,
                     mpos=Point3(-0.10, -22.45, 0.70),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=None,
                     ammo=(trammo[0] // 4), viseach=5)
        turret.add_cannon(cannon3)
        cannon4 = M3(parent=turret,
                     mpos=Point3(+0.10, -22.45, 0.70),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=None,
                     ammo=(trammo[0] // 4), viseach=5)
        turret.add_cannon(cannon4)

        self._hbx_hull.hitpoints = 160
        self._hbx_reng1.hitpoints = 50
        self._hbx_leng1.hitpoints = 50
        self._hbx_reng2.hitpoints = 50
        self._hbx_leng2.hitpoints = 50
        self._hbx_rtnk.hitpoints = 30
        self._hbx_ltnk.hitpoints = 30
        self._hbx_rwng.hitpoints = 110
        self._hbx_lwng.hitpoints = 110

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rtnk.minhitdmg = 0
        self._hbx_ltnk.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 100
        self._hbx_reng1.maxhitdmg = 30
        self._hbx_leng1.maxhitdmg = 30
        self._hbx_reng2.maxhitdmg = 30
        self._hbx_leng2.maxhitdmg = 30
        self._hbx_rtnk.maxhitdmg = 10
        self._hbx_ltnk.maxhitdmg = 10
        self._hbx_rwng.maxhitdmg = 60
        self._hbx_lwng.maxhitdmg = 60

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rtnk.out = False
        self._hbx_ltnk.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=2.0,
                emradfact=fx_uniform(1.4, 1.8),
                fpos=None,
                spos=Vec3(0.0, -4.0, 0.4),
                slifespan=3.2,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.6,
                emradfact=fx_uniform(0.6, 1.0),
                fpos=None,
                spos=Point3(1.2, 9.3, 1.6),
                slifespan=0.7,
                stcol=0.2)
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.6,
                emradfact=fx_uniform(0.6, 1.0),
                fpos=None,
                spos=Point3(-1.2, 9.3, 1.6),
                slifespan=0.7,
                stcol=0.2)
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(10.3, 9.6, -0.6),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(10.3, 9.6, -0.6),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(-10.3, 9.6, -0.6),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(-10.3, 9.6, -0.6),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(18.1, 3.5, -1.0),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(18.1, 3.5, -1.0),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(-18.1, 3.5, -1.0),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(-18.1, 3.5, -1.0),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_leng2.out = True

        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._hbx_rtnk.hitpoints <= 0 and not self._hbx_rtnk.out:
            self.explode_minor(offset=self._hbx_rtnk.center)
            d100 = randrange(100)
            if d100 < 33:
                self._hbx_rwng.hitpoints = 0
            else:
                self._hbx_reng2.hitpoints = 0
            self._hbx_rtnk.out = True
        if self._hbx_ltnk.hitpoints <= 0 and not self._hbx_ltnk.out:
            self.explode_minor(offset=self._hbx_ltnk.center)
            d100 = randrange(100)
            if d100 < 33:
                self._hbx_lwng.hitpoints = 0
            else:
                self._hbx_leng2.hitpoints = 0
            self._hbx_ltnk.out = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            for turret in self.turrets:
                turret.set_auto_attack()

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class E3b (Plane):

    species = "e3b"
    longdes = _("Boeing E-3 Sentry")
    shortdes = _("E-3B")

    minmass = 73000.0
    maxmass = 150000.0
    wingarea = 283.0
    wingaspect = 7.0
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 93e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 110000.0
    maxspeedz = 280.0
    maxspeedabz = None
    maxclimbratez = 40.0
    cloptspeedz = 240.0
    maxspeedh = 260.0
    maxspeedabh = None
    maxrollratez = radians(42.0)
    maxpitchratez = radians(8.0)
    maxfuel = 60000.0
    refsfcz = 0.55 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = 350000.0
    radarangle = (radians(75.0), radians(20.0), radians(180.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = True
    datalinksend = True
    rcs = 25.0
    irmuffle = 1.0
    iraspect = 0.5

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, +11.0, 0.5), 4.0),
                             # (Point3(0.0, +3.0, 0.5), 4.0),
                             # (Point3(0.0, -5.0, 0.5), 4.0),
                             # (Point3(0.0, -13.0, 0.5), 4.0),
                             # (Point3(0.0, -21.0, 3.0), 4.4)],
                   colldata=[(Point3(0.0,   0.4, 0.4), 2.0, 18.6, 2.3),
                             (Point3(0.0, -21.6, 4.6), 0.8,  3.4, 5.5),
                             (Point3(0.0, -22.7, 1.6), 6.1,  2.4, 0.6)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+10.0, -0.5, -0.8), 1.4)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-10.0, -0.5, -0.8), 1.4)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+14.8, -4.4, -0.3), 1.4)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-14.8, -4.4, -0.3), 1.4)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   colldata=[(Point3(+5.0, -2.0, -0.5), 2.2),
                             (Point3(+9.0, -4.5, -0.1), 2.2),
                             (Point3(+13.0, -7.0, 0.6), 2.2),
                             (Point3(+17.0, -9.5, 1.0), 2.0)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   colldata=[(Point3(-5.0, -2.0, -0.5), 2.2),
                             (Point3(-9.0, -4.5, -0.1), 2.2),
                             (Point3(-13.0, -7.0, 0.6), 2.2),
                             (Point3(-17.0, -9.5, 1.0), 2.0)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
        HitboxData(name="rado",
                   colldata=[(Point3(0.0, -11.6, 6.0), 3.8)],
                   longdes=_("radar dome"), shortdes=_("RADO"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-21.0, -12.1, 1.4), Point3(21.0, -12.1, 1.4)]
    #modelpath = [("models/aircraft/e3b/e3b.egg-1", 800),
                 #("models/aircraft/e3b/e3b.egg-2", 3000),
                 #("models/aircraft/e3b/e3b.egg-3", 12000)]
    fmodelpath = "models/aircraft/e3b/e3b.egg"
    modelpath = ["models/aircraft/e3b/e3b-1.egg",
                 "models/aircraft/e3b/e3b-2.egg",
                 "models/aircraft/e3b/e3b-3.egg"]
    shdmodelpath = "models/aircraft/e3b/e3b-shadow.egg"
    glossmap = "models/aircraft/e3b/e3b_gls.png"
    engsoundname = "engine-airliner"
    flybysoundname = "flyby-b1b"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 130
        self._hbx_reng1.hitpoints = 40
        self._hbx_leng1.hitpoints = 40
        self._hbx_reng2.hitpoints = 40
        self._hbx_leng2.hitpoints = 40
        self._hbx_rwng.hitpoints = 90
        self._hbx_lwng.hitpoints = 90
        self._hbx_rado.hitpoints = 30

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0
        self._hbx_rado.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 55
        self._hbx_reng1.maxhitdmg = 20
        self._hbx_leng1.maxhitdmg = 20
        self._hbx_reng2.maxhitdmg = 20
        self._hbx_leng2.maxhitdmg = 20
        self._hbx_rwng.maxhitdmg = 40
        self._hbx_lwng.maxhitdmg = 40
        self._hbx_rado.maxhitdmg = 20

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False
        self._hbx_rado.out = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=2.0,
                emradfact=fx_uniform(1.1, 1.5),
                fpos=None,
                spos=Vec3(0.0, -6.0, 0.5),
                slifespan=3.0,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self._hbx_reng1.hitpoints = 0
            self._hbx_reng2.hitpoints = 0
            self._hbx_rwng.out = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self._hbx_leng1.hitpoints = 0
            self._hbx_leng2.hitpoints = 0
            self._hbx_lwng.out = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(10.0, -0.5, -0.8),
                fpoolsize=12,
                flength=18.0,
                fspeed=28,
                fdelay=fx_uniform(0.1, 1.0),
                spos=Vec3(10.0, -0.5, -0.8),
                slifespan=2.2,
                stcol=0.1)
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-10.0, -0.5, -0.8),
                fpoolsize=12,
                flength=18.0,
                fspeed=28,
                fdelay=fx_uniform(0.1, 1.0),
                spos=Vec3(-10.0, -0.5, -0.8),
                slifespan=2.2,
                stcol=0.1)
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(14.8, -4.4, -0.3),
                fpoolsize=12,
                flength=18.0,
                fspeed=28,
                fdelay=fx_uniform(0.1, 1.0),
                spos=Vec3(14.8, -4.4, -0.3),
                slifespan=2.2,
                stcol=0.1)
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-14.8, -4.4, -0.3),
                fpoolsize=12,
                flength=18.0,
                fspeed=28,
                fdelay=fx_uniform(0.1, 1.0),
                spos=Vec3(-14.8, -4.4, -0.3),
                slifespan=2.2,
                stcol=0.1)
            self._hbx_leng2.out = True
        if self._hbx_rado.hitpoints <= 0 and not self._hbx_rado.out:
            self.explode_minor(offset=self._hbx_rado.center)
            self._hbx_rado.out = True

        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class Il76 (Plane):

    species = "il76"
    longdes = _("Ilyushin Il-76")
    shortdes = _("Il-76")

    minmass = 92000.0
    maxmass = 190000.0
    wingarea = 300.0
    wingaspect = 8.5
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 170e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 130000.0
    maxspeedz = 260.0
    maxspeedabz = None
    maxclimbratez = 50.0
    cloptspeedz = 240.0
    maxspeedh = 230.0
    maxspeedabh = None
    maxrollratez = radians(36.0)
    maxpitchratez = radians(6.0)
    maxfuel = 65000.0
    refsfcz = 0.45 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 30.0
    irmuffle = 0.4
    iraspect = 0.3

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, 14.0, 0.0), 4.4),
                             # (Point3(0.0, 5.0, 0.0), 5.4),
                             # (Point3(0.0, -6.0, 1.0), 5.4),
                             # (Point3(0.0, -18.0, 4.0), 6.2)],
                   colldata=[(Point3(0.0,   3.0, 0.7), 3.3, 17.0, 3.4),
                             (Point3(0.0, -19.4, 5.0), 2.3,  5.4, 6.1)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+5.2, 6.6, 0.1), 1.4)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-5.2, 6.6, 0.1), 1.4)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+9.0, 4.6, -0.2), 1.4)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-9.0, 4.6, -0.2), 1.4)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   # colldata=[(Point3(+16.0, -3.0, 1.0), 4.0),
                             # (Point3(+23.0, -7.0, 1.0), 4.0)],
                   colldata=[(Point3( +7.9,  0.6, 2.6), 4.6, 5.3, 1.1),
                             (Point3(+17.0, -3.6, 2.3), 4.4, 4.9, 0.7)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   # colldata=[(Point3(-16.0, -3.0, 1.0), 4.0),
                             # (Point3(-23.0, -7.0, 1.0), 4.0)],
                   colldata=[(Point3( -7.9, 0.6, 2.6), 4.6, 5.3, 1.1),
                             (Point3(-17.0, -3.6, 2.3), 4.4, 4.9, 0.7)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-25.8, -8.2, 2.1), Point3(25.8, -8.2, 2.1)]
    #modelpath = [("models/aircraft/il76/il76-1.egg", 800),
                 #("models/aircraft/il76/il76-2.egg", 3000),
                 #("models/aircraft/il76/il76-3.egg", 12000)]
    fmodelpath = "models/aircraft/il76/il76.egg"
    modelpath = ["models/aircraft/il76/il76-1.egg",
                 "models/aircraft/il76/il76-2.egg",
                 "models/aircraft/il76/il76-3.egg"]
    shdmodelpath = "models/aircraft/il76/il76-shadow.egg"
    glossmap = "models/aircraft/il76/il76_gls.png"
    engsoundname = "engine-il76"
    flybysoundname = "flyby-b1b"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 150
        self._hbx_reng1.hitpoints = 40
        self._hbx_leng1.hitpoints = 40
        self._hbx_reng2.hitpoints = 40
        self._hbx_leng2.hitpoints = 40
        self._hbx_rwng.hitpoints = 80
        self._hbx_lwng.hitpoints = 80

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 70
        self._hbx_reng1.maxhitdmg = 25
        self._hbx_leng1.maxhitdmg = 25
        self._hbx_reng2.maxhitdmg = 25
        self._hbx_leng2.maxhitdmg = 25
        self._hbx_rwng.maxhitdmg = 40
        self._hbx_lwng.maxhitdmg = 40

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=2.4,
                emradfact=fx_uniform(1.4, 1.8),
                fpos=None,
                spos=Vec3(0.0, -4.0, 0.4),
                slifespan=3.2,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            self._hbx_reng1.hitpoints = 0
            self._hbx_reng2.hitpoints = 0
            self._hbx_rwng.out = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            self._hbx_leng1.hitpoints = 0
            self._hbx_leng2.hitpoints = 0
            self._hbx_lwng.out = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(5.2, 6.6, 0.1),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(5.2, 6.6, 0.1),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(-5.2, 6.6, 0.1),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(-5.2, 6.6, 0.1),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(9.0, 4.6, -0.2),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(9.0, 4.6, -0.2),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.1,
                emradfact=fx_uniform(0.6, 0.8),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 108, 37, 1.0),
                ftcol=0.6,
                fpos=Vec3(-9.0, 4.6, -0.2),
                fpoolsize=12,
                flength=18.0,
                fspeed=30,
                fdelay=fx_uniform(0.1, 2.0),
                spos=Vec3(-9.0, 4.6, -0.2),
                slifespan=2.3,
                stcol=0.1)
            self._hbx_leng2.out = True

        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class Il78 (Il76):

    maxspeedz = 250.0
    maxclimbratez = 45.0
    cloptspeedz = 230.0
    maxspeedh = 220.0

    species = "il78"
    fmodelpath = "models/aircraft/il78/il78.egg"
    modelpath = ["models/aircraft/il78/il78-1.egg",
                 "models/aircraft/il78/il78-1.egg",
                 "models/aircraft/il78/il78-1.egg"]
    shdmodelpath = "models/aircraft/il78/il78-shadow.egg"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Il76.__init__(self, world, name, side, skill, texture,
                      fuelfill, pos, hpr, speed,
                      damage, faillvl, cnammo, lnammo,
                      cnrnum, cnrrate)


class An124 (Plane):

    species = "an124"
    longdes = _("Antonov An-124")
    shortdes = _("An-124")

    minmass = 175000.0
    maxmass = 405000.0
    wingarea = 628.0
    wingaspect = 8.6
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 230e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 300000.0
    maxspeedz = 250.0
    maxspeedabz = None
    maxclimbratez = 30.0
    cloptspeedz = 230.0
    maxspeedh = 220.0
    maxspeedabh = None
    maxrollratez = radians(26.0)
    maxpitchratez = radians(4.0)
    maxfuel = 210000.0
    refsfcz = 0.45 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 50.0
    irmuffle = 0.4
    iraspect = 0.3

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, 16.0, 0.0), 5.4),
                             # (Point3(0.0, 5.0, 0.0), 6.2),
                             # (Point3(0.0, -7.0, 0.0), 6.6),
                             # (Point3(0.0, -21.0, 0.0), 6.4),
                             # (Point3(0.0, -34.0, 2.0), 6.2)],
                   colldata=[(Point3(0.0,  -0.1, 0.7),  4.5, 25.8, 4.9),
                             (Point3(0.0, -29.5, 4.5),  4.3,  3.5, 6.7),
                             (Point3(0.0, -37.5, 8.0),  2.1,  4.5, 8.4),
                             (Point3(0.0, -38.3, 3.5), 14.2,  4.4, 0.6)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+10.2, 2.4, 0.2), 2.4)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-10.2, 2.4, 0.2), 2.4)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+18.0, -2.1, -0.5), 2.4)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-18.0, -2.1, -0.5), 2.4)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   # colldata=[(Point3(+14.0, -6.0, 2.4), 3.8),
                             # (Point3(+20.8, -8.8, 1.8), 3.4),
                             # (Point3(+27.0, -11.5, 1.2), 3.2)],
                   colldata=[(Point3(+10.5,  -4.3, 3.1), 6.0, 7.3, 1.5),
                             (Point3(+21.7,  -8.8, 2.1), 5.3, 6.1, 1.3),
                             (Point3(+32.0, -12.9, 1.0), 5.0, 4.5, 1.0)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   # colldata=[(Point3(-14.0, -6.0, 2.4), 3.8),
                             # (Point3(-20.8, -8.8, 1.8), 3.4),
                             # (Point3(-27.0, -11.5, 1.2), 3.2)],
                   colldata=[(Point3(-10.5,  -4.3, 3.1), 6.0, 7.3, 1.5),
                             (Point3(-21.7,  -8.8, 2.1), 5.3, 6.1, 1.3),
                             (Point3(-32.0, -12.9, 1.0), 5.0, 4.5, 1.0)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-36.7, -20.0, 0.1), Point3(36.7, -20.0, 0.1)]
    #modelpath = [("models/aircraft/an124/an124.egg", 800),
                 #("models/aircraft/an124/an124-2.egg", 3000),
                 #("models/aircraft/an124/an124-3.egg", 12000)]
    fmodelpath = "models/aircraft/an124/an124.egg"
    modelpath = ["models/aircraft/an124/an124-1.egg",
                 "models/aircraft/an124/an124-2.egg",
                 "models/aircraft/an124/an124-3.egg"]
    shdmodelpath = "models/aircraft/an124/an124-shadow.egg"
    glossmap = "models/aircraft/an124/an124_gls.png"
    engsoundname = ""
    flybysoundname = ""

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 240
        self._hbx_reng1.hitpoints = 80
        self._hbx_leng1.hitpoints = 80
        self._hbx_reng2.hitpoints = 80
        self._hbx_leng2.hitpoints = 80
        self._hbx_rwng.hitpoints = 150
        self._hbx_lwng.hitpoints = 150

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 170
        self._hbx_reng1.minhitdmg = 30
        self._hbx_leng1.minhitdmg = 30
        self._hbx_reng2.minhitdmg = 30
        self._hbx_leng2.minhitdmg = 30
        self._hbx_rwng.maxhitdmg = 100
        self._hbx_lwng.maxhitdmg = 100

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=4.0,
                emradfact=fx_uniform(2.0, 2.8),
                fpos=None,
                spos=Vec3(0.0, -17.3, 0.4),
                slifespan=3.4,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            self._hbx_reng1.hitpoints = 0
            self._hbx_reng2.hitpoints = 0
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            self._hbx_leng1.hitpoints = 0
            self._hbx_leng2.hitpoints = 0
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(10.2, 2.6, 0.2),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(10.2, 2.6, 0.2),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-10.2, 2.6, 0.2),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(-10.2, 2.6, 0.2),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(18.0, -1.8, -0.5),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(18.0, -1.8, -0.5),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-18.0, -1.8, -0.5),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(-18.0, -1.8, -0.5),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_leng2.out = True
        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class An12 (Plane):

    species = "an12"
    longdes = _("Antonov An-12")
    shortdes = _("An-12")

    # FIXME: Data as if turbofan-powered. Switch to turboprop when available.
    minmass = 28000.0
    maxmass = 61000.0
    wingarea = 121.0
    wingaspect = 11.9
    wingspeff = 0.88
    zlaoa = radians(-4.0)
    maxaoa = radians(10.0)
    maxthrust = 54e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 50000.0
    maxspeedz = 160.0
    maxspeedabz = None
    maxclimbratez = 12.0
    cloptspeedz = 150.0
    maxspeedh = 150.0
    maxspeedabh = None
    maxrollratez = radians(32.0)
    maxpitchratez = radians(5.0)
    maxfuel = 17000.0
    refsfcz = 0.34 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(20.0), radians(30.0), radians(110.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 22.0
    irmuffle = 0.2
    iraspect = 0.1
    proprpm = 2000.0
    proprtclkw = True

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0,  10.0, 0.0), 2.1),
                             # (Point3(0.0,  5.5,  0.0), 3.2),
                             # (Point3(0.0,  0.0,  0.0), 3.2),
                             # (Point3(0.0, -5.5,  0.2), 3.2),
                             # (Point3(0.0, -10.8, 1.5), 2.6),
                             # (Point3(0.0, -15.8, 3.0), 2.6)],
                   colldata=[(Point3(0.0,   2.6, 0.2), 2.4, 10.8, 2.3),
                             (Point3(0.0, -11.0, 1.5), 2.1,  2.8, 2.6),
                             (Point3(0.0, -16.3, 5.0), 0.5,  2.5, 3.4),
                             (Point3(0.0, -17.2, 2.3), 6.1,  1.4, 0.2)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+4.9, 1.5, 1.6), 1.2)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-4.9, 1.5, 1.6), 1.2)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+9.7, 0.7, 1.6), 1.0),],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-9.7, 0.7, 1.6), 1.0)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   # colldata=[(Point3(+3.1,  -1.3, 2.0), 1.6),
                             # (Point3(+7.6,  -1.8, 2.0), 1.6),
                             # (Point3(+12.3, -2.2, 2.0), 1.6)],
                   colldata=[(Point3(+10.4, -1.5, 2.0), 8.1, 2.1, 0.45)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   # colldata=[(Point3(-3.1,  -1.3, 2.0), 1.6),
                             # (Point3(-7.6,  -1.8, 2.0), 1.6),
                             # (Point3(-12.3, -2.2, 2.0), 1.6)],
                   colldata=[(Point3(-10.4, -1.5, 2.0), 8.1, 2.1, 0.45)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-20.1, -2.4, 2.3), Point3(20.1, -2.4, 2.3)]
    fmodelpath = "models/aircraft/an12/an12.egg"
    modelpath = ["models/aircraft/an12/an12-1.egg",
                 "models/aircraft/an12/an12-2.egg",
                 "models/aircraft/an12/an12-3.egg"]
    shdmodelpath = "models/aircraft/an12/an12-shadow.egg"
    glossmap = "models/aircraft/an12/an12_gls.png"
    engsoundname = "engine-c130"
    flybysoundname = ""

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, trammo=[400]):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        # Turrets.
        turret = CustomTurret(parent=self,
                              world=world, name=("%s-turret" % name), side=side,
                              turnrate=radians(120.0), elevrate=radians(120.0),
                              hcenter=180, harc=120, pcenter=0, parc=150,
                              modelpath=(self.node, "turret"),
                              texture=texture, normalmap=self.normalmap,
                              glossmap=self.glossmap, glowmap=self.glowmap)
        self.turrets.append(turret)

        cannon1 = Nr23(parent=turret,
                       mpos=Point3(-0.11, -20.00, 2.43),
                       mhpr=Vec3(0.0, 0.0, 0.0),
                       mltpos=Point3(0.0, -20.40, 2.43),
                       ammo=(trammo[0] // 2), viseach=5)
        turret.add_cannon(cannon1)
        cannon2 = Nr23(parent=turret,
                       mpos=Point3(+0.11, -20.00, 2.43),
                       mhpr=Vec3(0.0, 0.0, 0.0),
                       mltpos=None,
                       ammo=(trammo[0] // 2), viseach=5)
        turret.add_cannon(cannon2)

        self._hbx_hull.hitpoints = 170
        self._hbx_reng1.hitpoints = 30
        self._hbx_leng1.hitpoints = 30
        self._hbx_reng2.hitpoints = 30
        self._hbx_leng2.hitpoints = 30
        self._hbx_rwng.hitpoints = 85
        self._hbx_lwng.hitpoints = 85

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 90
        self._hbx_reng1.maxhitdmg = 20
        self._hbx_leng1.maxhitdmg = 20
        self._hbx_reng2.maxhitdmg = 20
        self._hbx_leng2.maxhitdmg = 20
        self._hbx_rwng.maxhitdmg = 40
        self._hbx_lwng.maxhitdmg = 40

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.8,
                emradfact=fx_uniform(1.0, 1.4),
                fpos=None,
                spos=Vec3(0.0, -5.4, 0.2),
                slifespan=3.0,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            self._hbx_reng1.hitpoints = 0
            self._hbx_reng2.hitpoints = 0
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            self._hbx_leng1.hitpoints = 0
            self._hbx_leng2.hitpoints = 0
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.7,
                emradfact=fx_uniform(0.4, 0.6),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 92, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(4.9, 1.7, 1.5),
                fpoolsize=10,
                flength=16.0,
                fspeed=20,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(4.9, 1.7, 1.5),
                slifespan=1.8,
                stcol=0.1)
            self._props["right-1"].targrpm = 0
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.7,
                emradfact=fx_uniform(0.4, 0.6),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 92, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(-4.9, 1.7, 1.5),
                fpoolsize=10,
                flength=16.0,
                fspeed=20,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(-4.9, 1.7, 1.5),
                slifespan=1.8,
                stcol=0.1)
            self._props["left-1"].targrpm = 0
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.7,
                emradfact=fx_uniform(0.4, 0.6),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 92, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(9.7, 1.0, 1.5),
                fpoolsize=10,
                flength=16.0,
                fspeed=20,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(9.7, 1.0, 1.5),
                slifespan=1.8,
                stcol=0.1)
            self._props["right-2"].targrpm = 0
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.7,
                emradfact=fx_uniform(0.4, 0.6),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(238, 92, 16, 1.0),
                ftcol=0.6,
                fpos=Vec3(-9.7, 1.0, 1.5),
                fpoolsize=10,
                flength=16.0,
                fspeed=20,
                fdelay=fx_uniform(1.0, 2.0),
                spos=Vec3(-9.7, 1.0, 1.5),
                slifespan=1.8,
                stcol=0.1)
            self._props["left-2"].targrpm = 0
            self._hbx_leng2.out = True
        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class C130 (Plane):

    species = "c130"
    longdes = _("Lockheed C-130 Hercules")
    shortdes = _("C-130")

    # FIXME: Data as if turbofan-powered. Switch to turboprop when available.
    minmass = 35000.0
    maxmass = 70000.0
    wingarea = 162.0
    wingaspect = 10.1
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(10.0)
    maxthrust = 60e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 55000.0
    maxspeedz = 150.0
    maxspeedabz = None
    maxclimbratez = 10.0
    cloptspeedz = 140.0
    maxspeedh = 140.0
    maxspeedabh = None
    maxrollratez = radians(28.0)
    maxpitchratez = radians(4.0)
    maxfuel = 20000.0
    refsfcz = 0.30 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(20.0), radians(30.0), radians(110.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 25.0
    irmuffle = 0.2
    iraspect = 0.1
    proprpm = 2000.0
    proprtclkw = True

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0, +6, 0), 3.2),
                             # (Point3(0, 0, 0), 3.2),
                             # (Point3(0, -6, 0), 3.2),
                             # (Point3(0, -13, 3.8), 4.4)],
                   colldata=[(Point3(0.0,   1.7, 0.1), 2.6, 9.7, 2.4),
                             (Point3(0.0, -10.0, 0.8), 2.8, 2.0, 2.2),
                             (Point3(0.0, -14.5, 4.8), 0.4, 2.6, 4.5),
                             (Point3(0.0, -14.7, 2.1), 7.9, 2.2, 0.3)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+4.9, -0.8, 1.2), 1.6)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-4.9, -0.8, 1.2), 1.6)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+9.8, -0.8, 1.2), 1.6)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-9.8, -0.8, 1.2), 1.6)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rtnk",
                   colldata=[(Point3(+7.7, -2.9, 0.2), 1.0)],
                   longdes=_("right tank"), shortdes=_("RTNK"),
                   selectable=True),
        HitboxData(name="ltnk",
                   colldata=[(Point3(-7.7, -2.9, 0.2), 1.0),],
                   longdes=_("left tank"), shortdes=_("LTNK"),
                   selectable=True),
        HitboxData(name="rwng",
                   # colldata=[(Point3(+3, -3.5, 2), 1.8),
                             # (Point3(+6.5, -3.5, 2), 1.8),
                             # (Point3(+10, -3.2, 2), 1.8),
                             # (Point3(+13.5, -3.1, 2), 1.8),
                             # (Point3(+17, -2.8, 2), 1.8)],
                   colldata=[(Point3(+11.4, -3.5, 1.9), 8.8, 2.7, 0.7)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   # colldata=[(Point3(-3, -3.5, 2), 1.8),
                             # (Point3(-6.5, -3.5, 2), 1.8),
                             # (Point3(-10, -3.2, 2), 1.8),
                             # (Point3(-13.5, -3.1, 2), 1.8),
                             # (Point3(-17, -2.8, 2), 1.8)],
                   colldata=[(Point3(-11.4, -3.5, 1.9), 8.8, 2.7, 0.7)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    fmodelpath = "models/aircraft/c130/c130.egg"
    modelpath = ["models/aircraft/c130/c130-1.egg",
                 "models/aircraft/c130/c130-2.egg",
                 "models/aircraft/c130/c130-3.egg"]
    sdmodelpath = "models/aircraft/c130/c130-shotdown.egg"
    shdmodelpath = "models/aircraft/c130/c130-shadow.egg"
    glossmap = "models/aircraft/c130/c130_gls.png"
    engsoundname = "engine-c130"
    flybysoundname = ""

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 160
        self._hbx_reng1.hitpoints = 30
        self._hbx_leng1.hitpoints = 30
        self._hbx_reng2.hitpoints = 30
        self._hbx_leng2.hitpoints = 30
        self._hbx_rtnk.hitpoints = 20
        self._hbx_ltnk.hitpoints = 20
        self._hbx_rwng.hitpoints = 80
        self._hbx_lwng.hitpoints = 80

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rtnk.minhitdmg = 0
        self._hbx_ltnk.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 90
        self._hbx_reng1.maxhitdmg = 20
        self._hbx_leng1.maxhitdmg = 20
        self._hbx_reng2.maxhitdmg = 20
        self._hbx_leng2.maxhitdmg = 20
        self._hbx_rtnk.maxhitdmg = 5
        self._hbx_ltnk.maxhitdmg = 5
        self._hbx_rwng.maxhitdmg = 40
        self._hbx_lwng.maxhitdmg = 40

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rtnk.out = False
        self._hbx_ltnk.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._hbx_reng1.removed = False
        self._hbx_leng1.removed = False
        self._hbx_reng2.removed = False
        self._hbx_leng2.removed = False

        self._failure_full = False

    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.8,
                emradfact=fx_uniform(1.0, 1.4),
                fpos=None,
                spos=Vec3(0.0, -2.0, 0.5),
                slifespan=3.1,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self.explode_minor(offset=self._hbx_rwng.center)
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self.explode_minor(offset=self._hbx_lwng.center)
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            self._props["right-1"].targrpm = 0
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=0.9,
                    emradfact=fx_uniform(0.5, 0.7),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(238, 92, 16, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(4.9, 1.0, 1.2),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=22,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(4.9, 1.0, 1.2),
                    slifespan=2.1,
                    stcol=0.1)
            else:
                breakupdata = [
                    breakup_small_front("propeller_right_1"),
                    breakup_engine_down("engine_right_1")
                    ]
                remove_subnodes(self._shotdown_modelnode, ("engine_right_1", "propeller_right_1"))
                AirBreakup(self, breakupdata)
                self._hbx_reng1.removed = True
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            self._props["left-1"].targrpm = 0
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=0.9,
                    emradfact=fx_uniform(0.5, 0.7),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(238, 92, 16, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(-4.9, 1.0, 1.2),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=22,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(-4.9, 1.0, 1.2),
                    slifespan=2.1,
                    stcol=0.1)
            else:
                breakupdata = [
                    breakup_small_front("propeller_left_1"),
                    breakup_engine_down("engine_left_1")
                    ]
                remove_subnodes(self._shotdown_modelnode, ("engine_left_1", "propeller_left_1"))
                AirBreakup(self, breakupdata)
                self._hbx_leng1.removed = True
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            self._props["right-2"].targrpm = 0
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=0.9,
                    emradfact=fx_uniform(0.5, 0.7),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(238, 92, 16, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(9.8, 1.0, 1.2),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=22,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(9.8, 1.0, 1.2),
                    slifespan=2.1,
                    stcol=0.1)
            else:
                breakupdata = [
                    breakup_small_front("propeller_right_2"),
                    breakup_engine_down("engine_right_2")
                    ]
                remove_subnodes(self._shotdown_modelnode, ("engine_right_2", "propeller_right_2"))
                AirBreakup(self, breakupdata)
                self._hbx_reng2.removed = True
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            self._props["left-2"].targrpm = 0
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=0.9,
                    emradfact=fx_uniform(0.5, 0.7),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(238, 92, 16, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(-9.8, 1.0, 1.2),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=22,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(-9.8, 1.0, 1.2),
                    slifespan=2.1,
                    stcol=0.1)
            else:
                breakupdata = [
                    breakup_small_front("propeller_left_2"),
                    breakup_engine_down("engine_left_2")
                    ]
                remove_subnodes(self._shotdown_modelnode, ("engine_left_2", "propeller_left_2"))
                AirBreakup(self, breakupdata)
                self._hbx_leng2.removed = True
            self._hbx_leng2.out = True
        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True
        if self._hbx_rtnk.hitpoints <= 0 and not self._hbx_rtnk.out:
            self.explode_minor(offset=self._hbx_rtnk.center)
            self._hbx_rtnk.out = True
            self._hbx_rwng.hitpoints = 0
        if self._hbx_ltnk.hitpoints <= 0 and not self._hbx_ltnk.out:
            self.explode_minor(offset=self._hbx_ltnk.center)
            self._hbx_ltnk.out = True
            self._hbx_lwng.hitpoints = 0

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = []

            if self._hbx_hull.out:
                breakupdata = [
                    breakup_small_down("cargo_door_1"),
                    breakup_small_back("cargo_door_2")
                    ]
                d100 = randrange(100)
                if d100 > 50:
                    breakupdata.extend([breakup_small_right("tail_fin_right")])
                d100 = randrange(100)
                if d100 > 50:
                    breakupdata.extend([breakup_small_left("tail_fin_left")])
                d100 = randrange(100)
                if d100 > 50:
                    breakupdata.extend([breakup_medium_up("tail")])
                remove_subnodes(self._shotdown_modelnode, ("fixed_external_misc_1",))
                remove_subnodes(self._shotdown_modelnode, ("tail_fin_right_misc", "tail_fin_left_misc", "tail_misc"))
            if self._hbx_rwng.out:
                self._props["right-1"].targrpm = 0
                self._props["right-2"].targrpm = 0
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_reng1.removed:
                    breakupdata.extend([
                        breakup_small_front("propeller_right_1"),
                        breakup_engine_down("engine_right_1")
                        ])
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_reng2.removed:
                    breakupdata.extend([
                        breakup_small_front("propeller_right_2"),
                        breakup_engine_down("engine_right_2")
                        ])
                breakupdata.extend([breakup_medium_right("wing_right")])
                remove_subnodes(self._shotdown_modelnode, ("wing_right_misc",))
            if self._hbx_lwng.out:
                self._props["left-1"].targrpm = 0
                self._props["left-2"].targrpm = 0
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_leng1.removed:
                    breakupdata.extend([
                        breakup_small_front("propeller_left_1"),
                        breakup_engine_down("engine_left_1")
                        ])
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_leng2.removed:
                    breakupdata.extend([
                        breakup_small_front("propeller_left_2"),
                        breakup_engine_down("engine_left_2")
                        ])
                breakupdata.extend([breakup_medium_left("wing_left")])
                remove_subnodes(self._shotdown_modelnode, ("wing_left_misc",))

            if breakupdata:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class Kc135 (Plane):

    species = "kc135"
    longdes = _("Boeing KC-135 Stratotanker")
    shortdes = _("KC-135")

    minmass = 45000.0
    maxmass = 135000.0
    wingarea = 226.0
    wingaspect = 7.0
    wingspeff = 0.85
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 94e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 75000.0
    maxspeedz = 290.0
    maxspeedabz = None
    maxclimbratez = 70.0
    cloptspeedz = 260.0
    maxspeedh = 270.0
    maxspeedabh = None
    maxrollratez = radians(48.0)
    maxpitchratez = radians(8.0)
    maxfuel = 40000.0
    refsfcz = 0.40 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 25.0
    irmuffle = 0.4
    iraspect = 0.3

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, +11.0, 0.5), 4.0),
                             # (Point3(0.0, +3.0, 0.5), 4.0),
                             # (Point3(0.0, -5.0, 0.5), 4.0),
                             # (Point3(0.0, -13.0, 0.5), 4.0),
                             # (Point3(0.0, -21.0, 3.0), 4.4)],
                   colldata=[(Point3(0.0,   0.4, 0.4), 2.0, 18.6, 2.3),
                             (Point3(0.0, -21.6, 4.6), 0.8,  3.4, 5.5),
                             (Point3(0.0, -22.7, 1.6), 6.1,  2.4, 0.6)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+8.86, 1.0, -1.73), 1.4)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-8.86, 1.0, -1.73), 1.4)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+14.18, -3.3, -1.26), 1.4)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-14.18, -3.3, -1.26), 1.4)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   colldata=[(Point3(+5.0, -2.0, -0.5), 2.2),
                             (Point3(+9.0, -4.5, -0.1), 2.2),
                             (Point3(+13.0, -7.0, 0.6), 2.2),
                             (Point3(+17.0, -9.5, 1.0), 2.0)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   colldata=[(Point3(-5.0, -2.0, -0.5), 2.2),
                             (Point3(-9.0, -4.5, -0.1), 2.2),
                             (Point3(-13.0, -7.0, 0.6), 2.2),
                             (Point3(-17.0, -9.5, 1.0), 2.0)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-21.0, -12.1, 1.4), Point3(21.0, -12.1, 1.4)]
    #modelpath = [("models/aircraft/kc135/kc135-1.egg", 800),
                 #("models/aircraft/kc135/kc135-2.egg", 3000),
                 #("models/aircraft/kc135/kc135-3.egg", 12000)]
    fmodelpath = "models/aircraft/kc135/kc135.egg"
    modelpath = ["models/aircraft/kc135/kc135-1.egg",
                 "models/aircraft/kc135/kc135-2.egg",
                 "models/aircraft/kc135/kc135-3.egg"]
    sdmodelpath = "models/aircraft/kc135/kc135-shotdown.egg"
    shdmodelpath = "models/aircraft/kc135/kc135-shadow.egg"
    glossmap = "models/aircraft/kc135/kc135_gls.png"
    engsoundname = "engine-airliner"
    flybysoundname = "flyby-b1b"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 60
        self._hbx_reng1.hitpoints = 20
        self._hbx_leng1.hitpoints = 20
        self._hbx_reng2.hitpoints = 20
        self._hbx_leng2.hitpoints = 20
        self._hbx_rwng.hitpoints = 30
        self._hbx_lwng.hitpoints = 30

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 20
        self._hbx_reng1.maxhitdmg = 10
        self._hbx_leng1.maxhitdmg = 10
        self._hbx_reng2.maxhitdmg = 10
        self._hbx_leng2.maxhitdmg = 10
        self._hbx_rwng.maxhitdmg = 15
        self._hbx_lwng.maxhitdmg = 15

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._hbx_reng1.removed = False
        self._hbx_leng1.removed = False
        self._hbx_reng2.removed = False
        self._hbx_leng2.removed = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=2.0,
                emradfact=fx_uniform(1.1, 1.5),
                fpos=None,
                spos=Vec3(0.0, -6.0, 0.5),
                slifespan=3.0,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self._hbx_rwng.out = True
            self._failure_full = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self._hbx_lwng.out = True
            self._failure_full = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=1.1,
                    emradfact=fx_uniform(0.6, 0.8),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(244, 98, 22, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(10.0, -0.5, -0.8),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=28,
                    fdelay=fx_uniform(0.1, 1.0),
                    spos=Vec3(10.0, -0.5, -0.8),
                    slifespan=2.2,
                    stcol=0.1)
            else:
                breakupdata = [breakup_engine_down("engine_right_1")]
                remove_subnodes(self._shotdown_modelnode, ("engine_right_1",))
                AirBreakup(self, breakupdata)
                self._hbx_reng1.removed = True
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=1.1,
                    emradfact=fx_uniform(0.6, 0.8),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(244, 98, 22, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(-10.0, -0.5, -0.8),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=28,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(-10.0, -0.5, -0.8),
                    slifespan=2.2,
                    stcol=0.1)
            else:
                breakupdata = [breakup_engine_down("engine_left_1")]
                remove_subnodes(self._shotdown_modelnode, ("engine_left_1",))
                AirBreakup(self, breakupdata)
                self._hbx_leng1.removed = True
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            d100 = randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=1.1,
                    emradfact=fx_uniform(0.6, 0.8),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(244, 98, 22, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(14.8, -4.4, -0.3),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=28,
                    fdelay=fx_uniform(0.1, 2.0),
                    spos=Vec3(14.8, -4.4, -0.3),
                    slifespan=2.2,
                    stcol=0.1)
            else:
                breakupdata = [breakup_engine_down("engine_right_2")]
                remove_subnodes(self._shotdown_modelnode, ("engine_right_2",))
                AirBreakup(self, breakupdata)
                self._hbx_reng2.removed = True
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            d100 = 0#randrange(100)
            if d100 < 50:
                fire_n_smoke_1(
                    parent=self, store=self.damage_trails,
                    sclfact=1.1,
                    emradfact=fx_uniform(0.6, 0.8),
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(244, 98, 22, 1.0),
                    ftcol=0.6,
                    fpos=Vec3(-14.8, -4.4, -0.3),
                    fpoolsize=12,
                    flength=18.0,
                    fspeed=28,
                    fdelay=fx_uniform(0.1, 1.0),
                    spos=Vec3(-14.8, -4.4, -0.3),
                    slifespan=2.2,
                    stcol=0.1)
            else:
                breakupdata = [breakup_engine_down("engine_left_2")]
                remove_subnodes(self._shotdown_modelnode, ("engine_left_2",))
                AirBreakup(self, breakupdata)
                self._hbx_leng2.removed = True
            self._hbx_leng2.out = True

        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = []

            if self._hbx_hull.out:
                d100 = randrange(100)
                if d100 < 50:
                    breakupdata.extend([breakup_small_up("tail")])
                d100 = randrange(100)
                if d100 < 50:
                    breakupdata.extend([breakup_small_right("tail_fin_right")])
                d100 = randrange(100)
                if d100 < 50:
                    breakupdata.extend([breakup_small_left("tail_fin_left")])
                remove_subnodes(self._shotdown_modelnode, ("fixed_external_misc_1",))
                remove_subnodes(self._shotdown_modelnode, ("tail_misc", "tail_fin_right_misc", "tail_fin_left_misc"))
            if self._hbx_rwng.out:
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_reng1.removed:
                    breakupdata.extend([breakup_engine_down("engine_right_1")])
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_leng2.removed:
                    breakupdata.extend([breakup_engine_down("engine_right_2")])
                breakupdata.extend([breakup_medium_right("wing_right")])
                remove_subnodes(self._shotdown_modelnode, ("wing_right_misc",))
            if self._hbx_lwng.out:
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_leng1.removed:
                    breakupdata.extend([breakup_engine_down("engine_left_1")])
                d100 = randrange(100)
                if d100 < 50 and not self._hbx_leng2.removed:
                    breakupdata.extend([breakup_engine_down("engine_left_2")])
                breakupdata.extend([breakup_medium_left("wing_left")])
                remove_subnodes(self._shotdown_modelnode, ("wing_left_misc",))

            if breakupdata:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


class Yak40 (Plane):

    species = "yak40"
    longdes = _("Yakovlev Yak-40")
    shortdes = _("Yak-40")

    minmass = 9500.0
    maxmass = 15500.0
    wingarea = 70.0
    wingaspect = 8.9
    wingspeff = 0.85
    zlaoa = radians(-2.0)
    maxaoa = radians(10.0)
    maxthrust = 15e3 * 3
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 12000.0
    maxspeedz = 150.0
    maxspeedabz = None
    maxclimbratez = 10.0
    cloptspeedz = 140.0
    maxspeedh = 170.0
    maxspeedabh = None
    maxrollratez = radians(60.0)
    maxpitchratez = radians(8.0)
    maxfuel = 3000.0
    refsfcz = 0.55 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0

    strength = 5.0
    minhitdmg = 0.0
    maxhitdmg = 7.0
    dmgtime = 10.0
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 10.0
    irmuffle = 0.4
    iraspect = 0.3

    # hitboxdata = [(Point3(0.0,  6.0, 0.4), 1.7),
                  # (Point3(0.0,  3.0, 0.4), 1.7),
                  # (Point3(0.0,  0.0, 0.4), 1.7),
                  # (Point3(0.0, -3.0, 0.4), 1.7),
                  # (Point3(0.0, -5.8, 1.0), 1.3),
                  # (Point3(0.0, -8.2, 3.2), 1.4),
                  # #Left wing
                  # (Point3(-2.8, -0.4, -0.5), 1.2),
                  # (Point3(-5.0, -0.4, -0.3), 1.2),
                  # (Point3(-7.2, -0.4, -0.1), 1.1),
                  # (Point3(-9.4, -0.4,  0.2), 1.1),
                  # #Right wing
                  # (Point3(+2.8, -0.4, -0.5), 1.2),
                  # (Point3(+5.0, -0.4, -0.3), 1.2),
                  # (Point3(+7.2, -0.4, -0.1), 1.1),
                  # (Point3(+9.4, -0.4,  0.2), 1.1)]
    # hitboxcritdata = [(Point3( 0.0, -7.8, 1.1), 0.6),
                      # (Point3(+1.8, -4.0, 0.8), 0.7),
                      # (Point3(-1.8, -4.0, 0.8), 0.7)]
    hitboxdata = [(Point3(0.0,  1.8,  0.35), 1.2, 8.2, 1.4),
                  (Point3(0.0, -8.0,  3.20), 0.4, 2.2, 1.4),
                  #Both wings
                  (Point3(0.0, -0.6, -0.45), 4.4, 2.0, 0.5),
                  #Left wing
                  (Point3(-8.4, -0.6, 0.1), 4.1, 1.7, 0.65),
                  #Right wing
                  (Point3(+8.4, -0.6, 0.1), 4.1, 1.7, 0.65)]
    hitboxcritdata = [(Point3( 0.00, -7.4, 0.8), 0.6, 1.0, 1.0),
                      (Point3(-1.85, -4.1, 0.8), 0.6, 1.5, 0.6),
                      (Point3(+1.85, -4.1, 0.8), 0.6, 1.5, 0.6)]
    vortexdata = [Point3(-12.5, -0.3, 0.54), Point3(12.5, -0.3, 0.54)]
    fmodelpath = "models/aircraft/yak40/yak40.egg"
    modelpath = ["models/aircraft/yak40/yak40-1.egg",
                 "models/aircraft/yak40/yak40-2.egg",
                 "models/aircraft/yak40/yak40-3.egg"]
    sdmodelpath = "models/aircraft/yak40/yak40-shotdown.egg"
    shdmodelpath = "models/aircraft/yak40/yak40-shadow.egg"
    glossmap = "models/aircraft/yak40/yak40_gls.png"
    engsoundname = "engine-airliner"
    flybysoundname = "flight-f18flyby"
    breakupdata = [
        breakup_medium_left("wing_left"),
        breakup_medium_right("wing_right"),
        breakup_engine_left("engine_left"),
        breakup_engine_right("engine_right"),
        breakup_small_left("fixed_external_door"),
        breakup_small_down("trap_door"),
        breakup_small_up("tail_fins"), # before "tail"
        breakup_small_up("tail")
    ]

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[250], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(1.79, -5.50, 0.74),
                               pdir=hprtovec(Vec3(-3.5, 180, 0)),
                               radius0=0.30, radius1=0.28, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyExhaust(parent=self, pos=Point3(-1.79, -5.50, 0.74),
                               pdir=hprtovec(Vec3(3.5, 180, 0)),
                               radius0=0.30, radius1=0.28, length=6.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=None,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust2)
        exhaust3 = PolyExhaust(parent=self, pos=Point3(0.0, -8.0, 1.1),
                               radius0=0.30, radius1=0.28, length=7.0,
                               speed=20.0, poolsize=16,
                               color=exhaustcolor,
                               colorend=exhaustcolorend,
                               tcol=0.6,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=exhaustglowmap,
                               ltpos=Point3(0.0, -8.5, 1.1),
                               ltcolor=exhaustcolorlight,
                               ltradius=exhaustltradius, lthalfat=exhaustlthalfat,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust3)


class Boeing747400 (Plane):

    species = "boeing747400"
    longdes = _("Boeing 747-400")
    shortdes = _("B-747/4")

    minmass = 178000.0
    maxmass = 397000.0
    wingarea = 540.0
    wingaspect = 7.8
    wingspeff = 0.90
    zlaoa = radians(-4.0)
    maxaoa = radians(12.0)
    maxthrust = 260e3 * 4
    maxthrustab = None
    thrustincab = None
    maxload = 2.5
    refmass = 280000.0
    maxspeedz = 280.0
    maxspeedabz = None
    maxclimbratez = 50.0
    cloptspeedz = 240.0
    maxspeedh = 270.0
    maxspeedabh = None
    maxrollratez = radians(30.0)
    maxpitchratez = radians(5.0)
    maxfuel = 173000.0
    refsfcz = 0.40 / 3.6e4
    refsfcabz = None
    sfcincab = None
    reldragbrake = 0.0
    maxflapdeflect = radians(40.0)
    maxflapdeltzlaoa = radians(-8.0)
    maxflapdeltmaxaoa = radians(3.0)
    maxflapdeltreldrag = 2.0
    midflapdeflect = radians(15.0)
    midflapdeltzlaoa = radians(-3.0)
    midflapdeltmaxaoa = radians(-1.0)
    midflapdeltreldrag = 0.5
    maxlandspeed = 100.0
    maxlandsinkrate = 4.0
    maxlandrotangle = radians(15.0)
    minlandrotangle = radians(-2.0)
    maxlandrollangle = radians(10.0)
    reldragwheelbrake = 20.0
    reldragwheel = 1.0
    groundcontact = [Point3(0.0, 3.0, -1.5),
                     Point3(1.5, -0.5, -1.5),
                     Point3(-1.5, -0.5, -1.5)]

    strength = None
    minhitdmg = None
    maxhitdmg = None
    dmgtime = None
    visualtype = VISTYPE.TRANSPORT
    visualangle = (radians(15.0), radians(20.0), radians(100.0))
    radarrange = None
    radarangle = None
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = False
    datalinksend = False
    rcs = 50.0
    irmuffle = 0.4
    iraspect = 0.3

    hitboxdata = [
        HitboxData(name="hull",
                   # colldata=[(Point3(0.0, +20.0, 0.5), 4.8),
                             # (Point3(0.0, +10.0, 0.0), 4.8),
                             # (Point3(0.0, +00.0, 0.0), 4.8),
                             # (Point3(0.0, -10.0, 0.0), 4.8),
                             # (Point3(0.0, -20.0, 0.5), 4.8),
                             # (Point3(0.0, -33.0, 5.0), 6.6)],
                   colldata=[(Point3(0.0,  -4.6, 0.6),  3.5, 34.4, 4.6),
                             (Point3(0.0, -35.2, 9.7),  0.5,  4.6, 4.5),
                             (Point3(0.0, -36.2, 2.6), 11.2,  3.3, 1.0)],
                   longdes=_("hull"), shortdes=_("HULL"),
                   selectable=True),
        HitboxData(name="reng1",
                   colldata=[(Point3(+13.5, +1.0, -2.5), 2.2)],
                   longdes=_("right engine 1"), shortdes=_("RENG1"),
                   selectable=True),
        HitboxData(name="leng1",
                   colldata=[(Point3(-13.5, +1.0, -2.5), 2.2)],
                   longdes=_("left engine 1"), shortdes=_("LENG1"),
                   selectable=True),
        HitboxData(name="reng2",
                   colldata=[(Point3(+21.2, -7.0, -2.0), 2.2)],
                   longdes=_("right engine 2"), shortdes=_("RENG2"),
                   selectable=True),
        HitboxData(name="leng2",
                   colldata=[(Point3(-21.2, -7.0, -2.0), 2.2)],
                   longdes=_("left engine 2"), shortdes=_("LENG2"),
                   selectable=True),
        HitboxData(name="rwng",
                   # colldata=[(Point3(5.0, +0.0, -0.8), 2.6),
                             # (Point3(10.0, -3.0, -0.6), 2.6),
                             # (Point3(15.0, -6.0, -0.5), 2.6),
                             # (Point3(20.0, -10.0, -0.1), 2.4),
                             # (Point3(26.0, -14.0, 0.1), 2.4)],
                   colldata=[(Point3( +8.3,  -1.5, -1.4), 4.8, 8.5, 1.3),
                             (Point3(+18.0,  -8.0, -0.4), 5.0, 5.3, 1.0),
                             (Point3(+27.9, -15.8,  0.5), 5.0, 4.7, 0.8)],
                   longdes=_("right wing"), shortdes=_("RWNG"),
                   selectable=True),
        HitboxData(name="lwng",
                   # colldata=[(Point3(-5.0, +0.0, -0.8), 2.6),
                             # (Point3(-10.0, -3.0, -0.6), 2.6),
                             # (Point3(-15.0, -6.0, -0.5), 2.6),
                             # (Point3(-20.0, -10.0, -0.1), 2.4),
                             # (Point3(-26.0, -14.0, 0.1), 2.4)],
                   colldata=[(Point3( -8.3,  -1.5, -1.4), 4.8, 8.5, 1.3),
                             (Point3(-18.0,  -8.0, -0.4), 5.0, 5.3, 1.0),
                             (Point3(-27.9, -15.8,  0.5), 5.0, 4.7, 0.8)],
                   longdes=_("left wing"), shortdes=_("LWNG"),
                   selectable=True),
    ]
    #vortexdata = [Point3(-32.2, -18.5, 1.0), Point3(32.2, -18.5, 1.0)]
    #modelpath = [("models/aircraft/boeing747400/boeing747400.egg-1", 800),
                 #("models/aircraft/boeing747400/boeing747400.egg-2", 3000),
                 #("models/aircraft/boeing747400/boeing747400.egg-3", 12000)]
    fmodelpath = "models/aircraft/boeing747400/boeing747400.egg"
    modelpath = ["models/aircraft/boeing747400/boeing747400-1.egg",
                 "models/aircraft/boeing747400/boeing747400-2.egg",
                 "models/aircraft/boeing747400/boeing747400-3.egg"]
    shdmodelpath = "models/aircraft/boeing747400/boeing747400-shadow.egg"
    glossmap = "models/aircraft/boeing747400/boeing747400_gls.png"
    engsoundname = "engine-airliner"
    flybysoundname = "flyby-b1b"

    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None, cnammo=[900], lnammo=[],
                  cnrnum=0, cnrrate=0.0):

        Plane.__init__(self, world=world, name=name, side=side, skill=skill,
                       texture=texture,
                       fuelfill=fuelfill, pos=pos, hpr=hpr, speed=speed,
                       damage=damage, faillvl=faillvl)

        self._hbx_hull.hitpoints = 90
        self._hbx_reng1.hitpoints = 20
        self._hbx_leng1.hitpoints = 20
        self._hbx_reng2.hitpoints = 20
        self._hbx_leng2.hitpoints = 20
        self._hbx_rwng.hitpoints = 40
        self._hbx_lwng.hitpoints = 40

        self._hbx_hull.minhitdmg = 0
        self._hbx_reng1.minhitdmg = 0
        self._hbx_leng1.minhitdmg = 0
        self._hbx_reng2.minhitdmg = 0
        self._hbx_leng2.minhitdmg = 0
        self._hbx_rwng.minhitdmg = 0
        self._hbx_lwng.minhitdmg = 0

        self._hbx_hull.maxhitdmg = 30
        self._hbx_reng1.maxhitdmg = 5
        self._hbx_leng1.maxhitdmg = 5
        self._hbx_reng2.maxhitdmg = 5
        self._hbx_leng2.maxhitdmg = 5
        self._hbx_rwng.maxhitdmg = 15
        self._hbx_lwng.maxhitdmg = 15

        self._hbx_hull.out = False
        self._hbx_reng1.out = False
        self._hbx_leng1.out = False
        self._hbx_reng2.out = False
        self._hbx_leng2.out = False
        self._hbx_rwng.out = False
        self._hbx_lwng.out = False

        self._failure_full = False


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > chbx.minhitdmg:
            chbx.hitpoints -= obody.hitforce
        if obody.hitforce > chbx.maxhitdmg and chbx.hitpoints > 0:
            chbx.hitpoints = 0

        if self._hbx_hull.hitpoints <= 0 and not self._hbx_hull.out:
            self.explode_minor(offset=self._hbx_hull.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=3.8,
                emradfact=fx_uniform(1.8, 2.4),
                fpos=None,
                spos=Vec3(0.0, -10.0, 0.5),
                slifespan=3.2,
                stcol=0.2)
            self._hbx_hull.out = True
            self._failure_full = True
        if self._hbx_rwng.hitpoints <= 0 and not self._hbx_rwng.out:
            self._hbx_reng1.hitpoints = 0
            self._hbx_reng2.hitpoints = 0
            self._hbx_rwng.out = True
        if self._hbx_lwng.hitpoints <= 0 and not self._hbx_lwng.out:
            self._hbx_leng1.hitpoints = 0
            self._hbx_leng2.hitpoints = 0
            self._hbx_lwng.out = True
        if self._hbx_reng1.hitpoints <= 0 and not self._hbx_reng1.out:
            self.explode_minor(offset=self._hbx_reng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(+13.5, +2.0, -3.0),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(0.0, 1.0),
                spos=Vec3(+13.5, +2.0, -3.0),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_reng1.out = True
        if self._hbx_leng1.hitpoints <= 0 and not self._hbx_leng1.out:
            self.explode_minor(offset=self._hbx_leng1.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-13.5, +2.0, -3.0),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(0.0, 1.0),
                spos=Vec3(+13.5, +2.0, -3.0),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_leng1.out = True
        if self._hbx_reng2.hitpoints <= 0 and not self._hbx_reng2.out:
            self.explode_minor(offset=self._hbx_reng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(+21.2, -5.0, -2.5),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(0.0, 1.0),
                spos=Vec3(+21.2, -5.0, -2.5),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_reng2.out = True
        if self._hbx_leng2.hitpoints <= 0 and not self._hbx_leng2.out:
            self.explode_minor(offset=self._hbx_leng2.center)
            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=1.4,
                emradfact=fx_uniform(0.8, 1.2),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(244, 98, 22, 1.0),
                ftcol=0.6,
                fpos=Vec3(-21.2, -5.0, -2.5),
                fpoolsize=14,
                flength=28.0,
                fspeed=32,
                fdelay=fx_uniform(0.0, 1.0),
                spos=Vec3(-21.2, -5.0, -2.5),
                slifespan=2.6,
                stcol=0.1)
            self._hbx_leng2.out = True

        if (self._hbx_reng1.hitpoints <= 0 and self._hbx_reng2.hitpoints <= 0) or (self._hbx_leng1.hitpoints <= 0 and self._hbx_leng2.hitpoints <= 0):
            self._failure_full = True

        if self._failure_full:
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            breakupdata = None
            if breakupdata is not None:
                for bkpd in breakupdata:
                    bkpd.texture = self.texture
                AirBreakup(self, breakupdata)
            self._shotdown_modelnode = None

            self.set_shotdown(3.0)

            if self.engine_sound is not None:
                self.engine_sound.stop()

            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

        return False


