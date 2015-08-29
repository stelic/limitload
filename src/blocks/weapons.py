# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Vec3, Point3

from src import pycv
from src.core.fire import MuzzleFlash
from src.core.bomb import Bomb
from src.core.droptank import DropTank
from src.core.jammer import JammingPod
from src.core.misc import rgba, remove_subnodes
from src.core.podrocket import PodRocket, RocketPod
from src.core.rocket import Rocket
from src.core.shell import Shell, Cannon
from src.core.trail import PolyTrail, PolyExhaust
from src.core.transl import *
from src.core.turret import Turret


rocketexhaustcolor = rgba(255, 154, 92, 1.0) #rgba(240, 145, 49, 0.8)
rockettrailcolor = rgba(250, 247, 245, 1.0) #rgba(250, 247, 245, 0.8) 
rocketexhaustglowmap = rgba(255, 255, 255, 1.0)
rockettrailglowmap = rgba(0, 0, 0, 0.1)
rockettraildirlit = pycv(py=False, c=True)

class Bullet7p62mm (Shell):

    species = "7p62mm"
    longdes = _(u"7.62×54 mm R")
    shortdes = _(u"7.62 mm")
    caliber = 0.00762
    dragcoeff = 0.30
    mass = 0.030
    pmassfac = 0.4
    hitforce = 0.1

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Bullet12p7mm (Shell):

    species = "12p7mm"
    longdes = _(u"12.7×99 mm NATO")
    shortdes = _(u"12.7 mm")
    caliber = 0.0127
    dragcoeff = 0.30
    mass = 0.070
    pmassfac = 0.4
    hitforce = 0.2

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Shell20mm (Shell):

    species = "20mm"
    longdes = _(u"20×102 mm")
    shortdes = _(u"20 mm")
    caliber = 0.020
    dragcoeff = 0.30
    mass = 0.26
    pmassfac = 0.4
    hitforce = 0.8

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Shell23mm (Shell):

    species = "23mm"
    longdes = _(u"23×115 mm")
    shortdes = _(u"23 mm")
    caliber = 0.023
    dragcoeff = 0.30
    mass = 0.40
    pmassfac = 0.4
    hitforce = 1.0

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Shell30mm (Shell):

    species = "30mm"
    longdes = _(u"30×165 mm")
    shortdes = _(u"30 mm")
    caliber = 0.030
    dragcoeff = 0.30
    mass = 0.82
    pmassfac = 0.4
    hitforce = 1.5

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Shell30mmu (Shell):

    species = "30mmu"
    longdes = _(u"30×173 mm DU")
    shortdes = _(u"30 mm DU")
    caliber = 0.030
    dragcoeff = 0.30
    mass = 1.01
    pmassfac = 0.4
    hitforce = 2.5

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Shell40mm (Shell):

    species = "40mm"
    longdes = _(u"40×364 mm R")
    shortdes = _(u"40 mm")
    caliber = 0.040
    dragcoeff = 0.30
    pmassfac = 0.4
    mass = 2.50
    hitforce = 3.0

    def __init__ (self, world, pos, hpr, vel, acc, effrange,
                  initdt=0.0, visible=False, vzoomed=False, vpuff=False,
                  target=False):

        Shell.__init__(self, world=world, pos=pos, hpr=hpr, vel=vel, acc=acc,
                       effrange=effrange, initdt=initdt,
                       visible=visible, vzoomed=vzoomed, vpuff=vpuff,
                       target=target)


class Pkm (Cannon):

    longdes = _("Kalashnikov PKM")
    shortdes = _("PKM")
    #against = []
    stype = Bullet7p62mm
    ftype = ("long", 0.3)
    mzvel = 800.0
    effrange = 600.0
    rate = 0.08
    burstlen = 40
    soundname = "gun-pkm"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class M3 (Cannon):

    longdes = _("Browning M3")
    shortdes = _("M3")
    #against = []
    stype = Bullet12p7mm
    ftype = ("long", 0.4)
    mzvel = 900.0
    effrange = 800.0
    rate = 0.05
    burstlen = 40
    soundname = "gun-pkm"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Gsh23 (Cannon):

    longdes = _("Gryazev-Shipunov GSh-23")
    shortdes = _("GSh-23")
    #against = []
    stype = Shell23mm
    ftype = ("square", 0.9)
    mzvel = 900.0
    effrange = 1000.0
    rate = 0.03
    burstlen = 20
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Gsh301 (Cannon):

    longdes = _("Gryazev-Shipunov GSh-301")
    shortdes = _("GSh-301")
    cpitdes = {"ru": u"ГШ-301"}
    #against = []
    stype = Shell30mm
    ftype = ("square", 1.0)
    mzvel = 850.0
    effrange = 1200.0
    rate = 0.04
    burstlen = 10
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Gsh623 (Cannon):

    longdes = _("Gryazev-Shipunov GSh-6-23")
    shortdes = _("GSh-6-23")
    #against = []
    stype = Shell23mm
    ftype = ("square", 0.9)
    mzvel = 900.0
    effrange = 1000.0
    rate = 0.008
    burstlen = 25
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Nr23 (Cannon):

    longdes = _("Nudelman-Rikhter NR-23")
    shortdes = _("NR-23")
    #against = []
    stype = Shell23mm
    ftype = ("square", 0.9)
    mzvel = 900.0
    effrange = 1000.0
    rate = 0.08
    burstlen = 10
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class N2a38m (Cannon):

    longdes = _("Tulmashzavod 2A38M")
    shortdes = _("2A38M")
    #against = []
    stype = Shell30mm
    ftype = ("longhalf", 1.4)
    mzvel = 960.0
    effrange = 2000.0
    rate = 0.03
    burstlen = 15
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class M61 (Cannon):

    longdes = _("General Dynamics M61 Vulcan")
    shortdes = _("M61")
    #against = []
    stype = Shell20mm
    ftype = ("square", 0.8)
    mzvel = 1030.0
    effrange = 1000.0
    rate = 0.01
    burstlen = 30
    soundname = "gun-vulcan"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class M230 (Cannon):

    longdes = _("Hughes M230")
    shortdes = _("M230")
    #against = []
    stype = Shell30mm
    ftype = ("long", 1.0)
    mzvel = 800.0
    effrange = 1100.0
    rate = 0.10
    burstlen = 10
    soundname = "gun-vulcan"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Defa554 (Cannon):

    longdes = _("Dassault Aviation DEFA 554")
    shortdes = _("DEFA 554")
    #against = []
    stype = Shell30mm
    ftype = ("square", 1.0)
    mzvel = 820.0
    effrange = 1200.0
    rate = 0.05
    burstlen = 10
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class M39 (Cannon):

    longdes = _("Pontiac M39")
    shortdes = _("M39")
    #against = []
    stype = Shell20mm
    ftype = ("square", 0.8)
    mzvel = 1030.0
    effrange = 1000.0
    rate = 0.04
    burstlen = 10
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class Gau8 (Cannon):

    longdes = _("General Electric GAU-8/A Avenger")
    shortdes = _("GAU-8/A")
    #against = []
    stype = Shell30mmu
    ftype = ("long", 1.1)
    mzvel = 1070.0
    effrange = 1800.0
    rate = 0.014
    burstlen = 20
    soundname = "gun-gau8"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class L70 (Cannon):

    longdes = _("Bofors L/70")
    shortdes = _("L/70")
    #against = []
    stype = Shell40mm
    ftype = ("longhalf", 2.0)
    mzvel = 1030.0
    effrange = 3400.0
    rate = 0.2
    burstlen = 6
    soundname = "gun-gsh"

    def __init__ (self, parent, mpos, mhpr, mltpos,
                  ammo, viseach=0, reloads=0, relrate=0.0):

        Cannon.__init__(self, parent=parent,
                        mpos=mpos, mhpr=mhpr, mltpos=mltpos,
                        ammo=ammo, viseach=viseach,
                        reloads=reloads, relrate=relrate)


class R13 (Rocket):

    species = "r13"
    longdes = _("Vympel R-13")
    shortdes = _("R-13")
    against = ["plane"]
    mass = 90.0
    diameter = 0.127
    maxg = 22.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 620.0
    maxspeed1 = 850.0
    maxthracc = 200.0
    maxthracc1 = 300.0
    maxvdracc = 2.5
    maxvdracc1 = 1.2
    maxflighttime = 15.0
    minlaunchdist = 600.0
    hitforce = 5.0
    expforce = 50.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 8.0
    decoyresist = 0.3
    rcs = 0.00007
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_r13.egg"]
    texture = "models/weapons/missile_r13_tex.png"
    normalmap = "models/weapons/missile_r13_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.41, 0.0),
                               radius0=0.15, radius1=0.30, length=4.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.51, 0.0),
                             radius0=0.15, radius1=1.30, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class R60 (Rocket):

    species = "r60"
    longdes = _("Vympel R-60")
    shortdes = _("R-60")
    cpitdes = {"ru": u"Р-60"}
    against = ["plane", "heli"]
    mass = 45.0
    diameter = 0.120
    maxg = 28.0
    vmaxalt = 12000.0
    minspeed = 470.0
    minspeed1 = 470.0
    maxspeed = 650.0
    maxspeed1 = 880.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 12.0
    minlaunchdist = 350.0
    hitforce = 3.0
    expforce = 25.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(16.0)
    locktime = 3.0
    decoyresist = 0.6
    rcs = 0.00005
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_r60.egg"]
    texture = "models/weapons/missile_r60_tex.png"
    normalmap = "models/weapons/missile_r60_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.04, 0.0),
                               radius0=0.15, radius1=0.30, length=4.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.14, 0.0),
                             radius0=0.15, radius1=1.30, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class R73 (Rocket):

    species = "r73"
    longdes = _("Vympel R-73")
    shortdes = _("R-73")
    cpitdes = {"ru": u"Р-73"}
    against = ["plane", "heli"]
    mass = 105.0
    diameter = 0.165
    maxg = 32.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 600.0
    maxspeed1 = 850.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 22.0
    minlaunchdist = 300.0
    hitforce = 5.0
    expforce = 50.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(40.0)
    locktime = 2.0
    decoyresist = 0.8
    rcs = 0.00007
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_r73.egg"]
    texture = "models/weapons/missile_r73_tex.png"
    normalmap = "models/weapons/missile_r73_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.46, 0.0),
                               radius0=0.15, radius1=0.30, length=4.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.56, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class R27 (Rocket):

    species = "r27"
    longdes = _("Vympel R-27")
    shortdes = _("R-27")
    cpitdes = {"ru": u"Р-27"}
    against = ["plane"]
    mass = 250.0
    diameter = 0.230
    maxg = 18.0
    vmaxalt = 12000.0
    minspeed = 400.0
    minspeed1 = 400.0
    maxspeed = 800.0
    maxspeed1 = 1300.0
    maxthracc = 450.0
    maxthracc1 = 550.0
    maxvdracc = 3.0
    maxvdracc1 = 1.8
    maxflighttime = 52.0
    minlaunchdist = 2000.0
    hitforce = 18.0
    expforce = 140.0
    seeker = "sarh"
    flightmodes = ["intercept"]
    maxoffbore = radians(16.0)
    locktime = 6.0
    decoyresist = 0.6
    rcs = 0.00016
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_r27.egg"]
    texture = "models/weapons/missile_r27_tex.png"
    normalmap = "models/weapons/missile_r27_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -2.04, 0.0),
                               radius0=0.15, radius1=0.40, length=5.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -2.04, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class R77 (Rocket):

    species = "r77"
    longdes = _("Vympel R-77")
    shortdes = _("R-77")
    cpitdes = {"ru": u"Р-77"}
    against = ["plane", "heli"]
    mass = 175.0
    diameter = 0.200
    maxg = 24.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 850.0
    maxspeed1 = 1400.0
    maxthracc = 600.0
    maxthracc1 = 700.0
    maxvdracc = 2.8
    maxvdracc1 = 1.4
    maxflighttime = 44.0
    minlaunchdist = 800.0
    hitforce = 14.0
    expforce = 75.0
    seeker = "arh"
    flightmodes = ["transfer", "intercept"]
    maxoffbore = radians(30.0)
    locktime = 4.0
    decoyresist = 0.9
    rcs = 0.00012
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_r77.egg"]
    texture = "models/weapons/missile_r77_tex.png"
    normalmap = "models/weapons/missile_r77_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.75, 0.0),
                               radius0=0.15, radius1=0.40, length=5.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.75, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Kh25 (Rocket):

    species = "kh25"
    longdes = _("Zvezda Kh-25")
    shortdes = _("Kh-25")
    shortdes = _("Kh-25")
    cpitdes = {"ru": u"Х-25"}
    against = ["building", "vehicle", "ship"]
    mass = 300.0
    diameter = 0.275
    maxg = 18.0
    vmaxalt = 12000.0
    minspeed = 350.0
    minspeed1 = 350.0
    maxspeed = 550.0
    maxspeed1 = 750.0
    maxthracc = 200.0
    maxthracc1 = 300.0
    maxvdracc = 3.0
    maxvdracc1 = 2.0
    maxflighttime = 22.0
    minlaunchdist = 1000.0
    hitforce = 10.0
    expforce = 550.0
    seeker = "tv"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 4.0
    decoyresist = 0.5
    rcs = 0.00023
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.4)]
    modelpath = ["models/weapons/missile_kh25.egg"]
    texture = "models/weapons/missile_kh25_tex.png"
    normalmap = "models/weapons/missile_kh25_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.85, 0.0),
                               radius0=0.20, radius1=0.50, length=6.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -2.15, 0.0),
                             radius0=0.25, radius1=1.50, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Kh59 (Rocket):

    species = "kh59"
    longdes = _("Raduga Kh-59")
    shortdes = _("Kh-59")
    cpitdes = {"ru": u"Х-59"}
    against = ["building", "ship"]
    mass = 760.0
    diameter = 0.380
    maxg = 12.0
    vmaxalt = 12000.0
    minspeed = 200.0
    minspeed1 = 200.0
    maxspeed = 300.0
    maxspeed1 = 420.0
    maxthracc = 150.0
    maxthracc1 = 230.0
    maxvdracc = 4.0
    maxvdracc1 = 3.0
    maxflighttime = 130.0
    minlaunchdist = 3000.0
    hitforce = 12.0
    expforce = 950.0
    seeker = "intv"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 4.0
    decoyresist = 0.6
    rcs = 0.00050
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_kh59.egg"]
    texture = "models/weapons/missile_kh59_tex.png"
    normalmap = "models/weapons/missile_kh59_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -2.80, 0.0),
                               radius0=0.20, radius1=0.55, length=6.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -3.10, 0.0),
                             radius0=0.26, radius1=1.56, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class S200 (Rocket):

    species = "s200"
    longdes = _("Almaz S-200 Dubna")
    shortdes = _("S-200")
    against = ["plane"]
    mass = 7000.0
    diameter = 0.850
    maxg = 60.0
    vmaxalt = 12000.0
    minspeed = 600.0
    minspeed1 = 1000.0
    maxspeed = 1200.0
    maxspeed1 = 1800.0
    maxthracc = 400.0
    maxthracc1 = 500.0
    maxvdracc = 7.0
    maxvdracc1 = 3.0
    maxflighttime = 180.0
    minlaunchdist = 10000.0
    hitforce = 100.0
    expforce = 800.0
    seeker = "sarh"
    flightmodes = ["transfer", "intercept"]
    maxoffbore = radians(12.0)
    locktime = 10.0
    decoyresist = 0.4
    rcs = 0.00120
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_s200.egg"]
    texture = "models/weapons/missile_s200_tex.png"
    normalmap = "models/weapons/missile_s200_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -5.10, 0.0),
                               radius0=0.50, radius1=1.30, length=14.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=6)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -5.40, 0.0),
                             radius0=0.80, radius1=4.00, lifespan=2.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Osa (Rocket):

    species = "osa"
    longdes = _("Fakel 9M33 Osa")
    shortdes = _("Osa")
    against = ["plane", "heli"]
    mass = 170.0
    diameter = 0.210
    maxg = 20.0
    vmaxalt = 12000.0
    minspeed = 600.0
    minspeed1 = 600.0
    maxspeed = 800.0
    maxspeed1 = 1000.0
    maxthracc = 400.0
    maxthracc1 = 500.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 18.0
    minlaunchdist = 300.0
    hitforce = 8.0
    expforce = 40.0
    seeker = "sarh"
    flightmodes = ["intercept"]
    maxoffbore = radians(20.0)
    locktime = 3.0
    decoyresist = 0.55
    rcs = 0.00008
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_osa.egg"]
    texture = "models/weapons/missile_osa_tex.png"
    normalmap = "models/weapons/missile_osa_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.50, 0.0),
                               radius0=0.40, radius1=1.10, length=12.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=6)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.70, 0.0),
                             radius0=0.60, radius1=3.00, lifespan=2.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Igla (Rocket):

    species = "igla"
    longdes = _("Kolomna Igla")
    shortdes = _("Igla")
    against = ["plane", "heli"]
    mass = 11.0
    diameter = 0.072
    maxg = 32.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 550.0
    maxspeed = 800.0
    maxspeed1 = 950.0
    maxthracc = 200.0
    maxthracc1 = 300.0
    maxvdracc = 1.0
    maxvdracc1 = 0.5
    maxflighttime = 8.0
    minlaunchdist = 200.0
    hitforce = 1.0
    expforce = 14.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(16.0)
    locktime = 4.0
    decoyresist = 0.3
    rcs = 0.00002
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_igla.egg"]
    texture = "models/weapons/missile_igla_tex.png"
    normalmap = "models/weapons/missile_igla_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -0.8, 0.0),
                               radius0=0.05, radius1=0.10, length=2.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.0, 0.0),
                             radius0=0.05, radius1=1.00, lifespan=1.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Stinger (Rocket):

    species = "stinger"
    longdes = _("Raytheon FIM-92 Stinger")
    shortdes = _("FIM-92")
    against = ["plane", "heli"]
    mass = 11.0
    diameter = 0.070
    maxg = 30.0
    vmaxalt = 12000.0
    minspeed = 400.0
    minspeed1 = 500.0
    maxspeed = 700.0
    maxspeed1 = 850.0
    maxthracc = 200.0
    maxthracc1 = 300.0
    maxvdracc = 1.0
    maxvdracc1 = 0.5
    maxflighttime = 8.0
    minlaunchdist = 200.0
    hitforce = 1.0
    expforce = 14.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(14.0)
    locktime = 4.0
    decoyresist = 0.2
    rcs = 0.00002
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_stinger.egg"]
    texture = "models/weapons/missile_stinger_tex.png"
    normalmap = "models/weapons/missile_stinger_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -0.75, 0.0),
                               radius0=0.05, radius1=0.10, length=2.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=3)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -0.95, 0.0),
                             radius0=0.05, radius1=1.00, lifespan=1.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Aim7 (Rocket):

    species = "aim7"
    longdes = _("Raytheon AIM-7 Sparrow")
    shortdes = _("AIM-7")
    against = ["plane"]
    mass = 230.0
    diameter = 0.200
    maxg = 18.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 800.0
    maxspeed1 = 1200.0
    maxthracc = 400.0
    maxthracc1 = 500.0
    maxvdracc = 2.8
    maxvdracc1 = 1.4
    maxflighttime = 35.0
    minlaunchdist = 1500.0
    hitforce = 15.0
    expforce = 180.0
    seeker = "sarh"
    flightmodes = ["transfer", "intercept"]
    maxoffbore = radians(12.0)
    locktime = 8.0
    decoyresist = 0.5
    rcs = 0.00012
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_aim7.egg"]
    texture = "models/weapons/missile_aim7_tex.png"
    normalmap = "models/weapons/missile_aim7_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.83, 0.0),
                               radius0=0.15, radius1=0.40, length=5.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, 2.14, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Aim9 (Rocket):

    species = "aim9"
    longdes = _("Raytheon AIM-9 Sidewinder")
    shortdes = _("AIM-9")
    against = ["plane", "heli"]
    mass = 86.0
    diameter = 0.127
    maxg = 26.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 600.0
    maxspeed1 = 850.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 16.0
    minlaunchdist = 300.0
    hitforce = 4.0
    expforce = 35.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(20.0)
    locktime = 3.0
    decoyresist = 0.7
    rcs = 0.00005
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_aim9.egg"]
    texture = "models/weapons/missile_aim9_tex.png"
    normalmap = "models/weapons/missile_aim9_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.48, 0.0),
                               radius0=0.10, radius1=0.30, length=4.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.78, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Aim120 (Rocket):

    species = "aim120"
    longdes = _("Raytheon AIM-120 AMRAAM")
    shortdes = _("AIM-120")
    against = ["plane", "heli"]
    mass = 152.0
    diameter = 0.180
    maxg = 22.0
    vmaxalt = 12000.0
    minspeed = 450.0
    minspeed1 = 450.0
    maxspeed = 800.0
    maxspeed1 = 1300.0
    maxthracc = 500.0
    maxthracc1 = 600.0
    maxvdracc = 2.5
    maxvdracc1 = 1.2
    maxflighttime = 45.0
    minlaunchdist = 800.0
    hitforce = 12.0
    expforce = 80.0
    seeker = "arh"
    flightmodes = ["transfer", "intercept"]
    maxoffbore = radians(28.0)
    locktime = 5.0
    decoyresist = 0.8
    rcs = 0.00010
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_aim120.egg"]
    texture = "models/weapons/missile_aim120_tex.png"
    normalmap = "models/weapons/missile_aim120_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.91, 0.0),
                               radius0=0.15, radius1=0.40, length=5.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -2.22, 0.0),
                             radius0=0.20, radius1=1.40, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Rim156 (Rocket):

    species = "rim156"
    longdes = _("Raytheon RIM-156 Standard SM-2ER")
    shortdes = _("RIM-156")
    against = ["plane"]
    mass = 1350.0
    diameter = 0.340
    maxg = 18.0
    vmaxalt = 12000.0
    minspeed = 400.0
    minspeed1 = 500.0
    maxspeed = 700.0
    maxspeed1 = 1100.0
    maxthracc = 500.0
    maxthracc1 = 600.0
    maxvdracc = 5.0
    maxvdracc1 = 2.0
    maxflighttime = 160.0
    minlaunchdist = 5000.0
    hitforce = 20.0
    expforce = 220.0
    seeker = "sarh"
    flightmodes = ["transfer", "intercept"]
    maxoffbore = radians(18.0)
    locktime = 5.0
    decoyresist = 0.8
    rcs = 0.00028
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_rim156.egg"]
    texture = "models/weapons/missile_rim156_tex.png"
    normalmap = "models/weapons/missile_rim156_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -3.3, 0.0),
                               radius0=0.40, radius1=1.10, length=12.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=6)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -3.6, 0.0),
                             radius0=0.60, radius1=3.00, lifespan=2.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Rapier (Rocket):

    species = "rapier"
    longdes = _("BAe Rapier")
    shortdes = _("Rapier")
    against = ["plane", "heli"]
    mass = 45.0
    diameter = 0.133
    maxg = 22.0
    vmaxalt = 12000.0
    minspeed = 600.0
    minspeed1 = 600.0
    maxspeed = 800.0
    maxspeed1 = 950.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 12.0
    minlaunchdist = 300.0
    hitforce = 3.0
    expforce = 25.0
    seeker = "tv"
    flightmodes = ["intercept"]
    maxoffbore = radians(18.0)
    locktime = 2.0
    decoyresist = 0.5
    rcs = 0.00004
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_rapier.egg"]
    texture = "models/weapons/missile_rapier_tex.png"
    normalmap = "models/weapons/missile_rapier_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.06, 0.0),
                               radius0=0.40, radius1=1.10, length=12.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=6)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.26, 0.0),
                             radius0=0.60, radius1=3.00, lifespan=2.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Roland (Rocket):

    species = "roland"
    longdes = _("Euromissile Roland")
    shortdes = _("Roland")
    against = ["plane", "heli"]
    mass = 67.0
    diameter = 0.160
    maxg = 22.0
    vmaxalt = 12000.0
    minspeed = 500.0
    minspeed1 = 500.0
    maxspeed = 700.0
    maxspeed1 = 900.0
    maxthracc = 300.0
    maxthracc1 = 400.0
    maxvdracc = 2.0
    maxvdracc1 = 1.0
    maxflighttime = 14.0
    minlaunchdist = 300.0
    hitforce = 3.0
    expforce = 30.0
    seeker = "sarh"
    flightmodes = ["intercept"]
    maxoffbore = radians(20.0)
    locktime = 3.0
    decoyresist = 0.5
    rcs = 0.00005
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_roland.egg"]
    texture = "models/weapons/missile_roland_tex.png"
    normalmap = "models/weapons/missile_roland_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.13, 0.0),
                               radius0=0.40, radius1=1.10, length=12.0,
                               speed=20.0, poolsize=18,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=2000.0,
                               loddirang=20, loddirskip=6)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.33, 0.0),
                             radius0=0.60, radius1=3.00, lifespan=2.5,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Agm65 (Rocket):

    species = "agm65"
    longdes = _("Raytheon AGM-65 Maverick")
    shortdes = _("AGM-65")
    against = ["building", "vehicle", "ship"]
    mass = 250.0
    diameter = 0.300
    maxg = 16.0
    vmaxalt = 12000.0
    minspeed = 250.0
    minspeed1 = 250.0
    maxspeed = 320.0
    maxspeed1 = 480.0
    maxthracc = 150.0
    maxthracc1 = 250.0
    maxvdracc = 3.4
    maxvdracc1 = 2.2
    maxflighttime = 50.0
    minlaunchdist = 1000.0
    hitforce = 8.0
    expforce = 400.0
    seeker = "ir"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 4.0
    decoyresist = 0.5
    rcs = 0.00023
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.4)]
    modelpath = ["models/weapons/missile_agm65.egg"]
    texture = "models/weapons/missile_agm65_tex.png"
    normalmap = "models/weapons/missile_agm65_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -1.20, 0.0),
                               radius0=0.20, radius1=0.50, length=6.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -1.50, 0.0),
                             radius0=0.25, radius1=1.50, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class Bgm109 (Rocket):

    species = "bgm109"
    longdes = _("Raytheon BGM-109 Tomahawk")
    shortdes = _(u"BGM-109")
    against = ["building", "ship"]
    mass = 1300.0
    diameter = 0.520
    maxg = 12.0
    vmaxalt = 12000.0
    minspeed = 180.0
    minspeed1 = 180.0
    maxspeed = 250.0
    maxspeed1 = 380.0
    maxthracc = 100.0
    maxthracc1 = 180.0
    maxvdracc = 4.0
    maxvdracc1 = 3.0
    maxflighttime = 1e6
    minlaunchdist = 3000.0
    hitforce = 20.0
    expforce = 1300.0
    seeker = "intv"
    flightmodes = ["intercept"]
    maxoffbore = radians(10.0)
    locktime = 4.0
    decoyresist = 0.6
    rcs = 0.00500
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.6)]
    modelpath = ["models/weapons/missile_bgm109.egg"]
    texture = "models/weapons/missile_bgm109_tex.png"
    normalmap = "models/weapons/missile_bgm109_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, dropvel=None,
                  target=None, offset=None):

        Rocket.__init__(self, world=world, name=name, side=side,
                        pos=pos, hpr=hpr, speed=speed, dropvel=dropvel,
                        target=target, offset=offset)

        exhaust1 = PolyExhaust(parent=self, pos=Point3(0.0, -2.80, 0.0),
                               radius0=0.20, radius1=0.55, length=7.0,
                               speed=20.0, poolsize=24,
                               color=rocketexhaustcolor,
                               ltoff=True,
                               texture="images/particles/exhaust03.png",
                               glowmap=rocketexhaustglowmap,
                               dbin=0,
                               freezedist=200.0, hidedist=1000.0,
                               loddirang=20, loddirskip=4)
        self.exhaust_trails.append(exhaust1)
        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -3.10, 0.0),
                             radius0=0.26, radius1=1.56, lifespan=2.0,
                             color=rockettrailcolor,
                             texture="images/particles/exhaust06.png",
                             glowmap=rockettrailglowmap,
                             dirlit=rockettraildirlit,
                             dbin=3)
        self.exhaust_trails.append(exhaust2)


class S8 (PodRocket):

    species = "s8"
    longdes = _("S-8")
    shortdes = _("S-8")
    cpitdes = {"ru": u"С-8"}
    mass = 15.0
    diameter = 0.080
    maxspeed = 600.0
    maxthracc = 400.0
    maxvdracc = 4.0
    maxflighttime = 6.0
    minlaunchdist = 200.0
    hitforce = 1.0
    expforce = 30.0
    rcs = 0.00005
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 1.0)]
    modelpath = ["models/weapons/missile_s8.egg"]
    texture = "models/weapons/missile_s8_tex.png"
    normalmap = "models/weapons/missile_s8_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, extvis=False):

        PodRocket.__init__(self, world=world, name=name, side=side,
                           pos=pos, hpr=hpr, speed=speed,
                           extvis=extvis)

        # exhaust1 = PolyTrail(parent=self, pos=Point3(0.0, -1.51, 0.0),
                             # radius0=0.05, radius1=0.20, lifespan=0.2,
                             # color=rockettrailcolor,
                             # texture="images/particles/exhaust06.png",
                             # glowmap=rockettrailglowmap,
                             # dbin=3)
        # self.exhaust_trails.append(exhaust1)


class B8m1 (RocketPod):

    rtype = S8
    mass = 160.0 # empty
    diameter = 0.520
    rate = 0.10
    rounds = 20
    modelpath = ["models/weapons/missile_s8_b8m1rp.egg"]
    texture = "models/weapons/missile_s8_tex.png"
    normalmap = "models/weapons/missile_s8_nm.png"

    def __init__ (self):

        RocketPod.__init__(self)


class Rpg7 (PodRocket):

    species = "rpg7"
    longdes = _("RPG-7")
    shortdes = _("RPG-7")
    mass = 2.6
    diameter = 0.093
    maxspeed = 115.0
    maxthracc = 2000.0
    maxvdracc = 4.0
    maxflighttime = 4.5
    minlaunchdist = 10.0
    hitforce = 0.1
    expforce = 20.0
    rcs = 0.00001
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 2.0)]
    modelpath = [("models/weapons/missile_rpg7.egg")]
    texture = "models/weapons/missile_rpg7_tex.png"
    normalmap = "models/weapons/missile_rpg7_nm.png"

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None, extvis=False):

        PodRocket.__init__(self, world=world, name=name, side=side,
                           pos=pos, hpr=hpr, speed=speed,
                           extvis=extvis, basictrail=False)
    # def __init__ (self, world, name, side,
                  # pos=None, hpr=None, speed=None, target=None, offset=None):

        # Rocket.__init__(self, world=world, name=name, side=side,
                        # pos=pos, hpr=hpr, speed=speed,
                        # target=target, offset=offset)

        exhaust2 = PolyTrail(parent=self, pos=Point3(0.0, -0.46, 0.0),
                             radius0=0.15, radius1=1.40, lifespan=2.0,
                             color=rgba(250, 250, 250, 0.8),
                             texture="images/particles/exhaust06.png", dbin=-2)
        self.exhaust_trails.append(exhaust2)


class TurretM61 (Turret):

    species = "turrm61"
    turnrate = radians(120.0)
    elevrate = radians(60.0)
    radarrange = 2000.0
    modelpath = ["models/weapons/turret_m61.egg"]

    def __init__ (self, world, name, side,
                  hcenter, harc, pcenter, parc,
                  pos=None, hpr=None,
                  storepos=None, storespeed=1.0, storedecof=None,
                  parent=None,
                  cnammo=[1200]):

        Turret.__init__(self, world=world, name=name, side=side,
                        parent=parent, pos=pos, hpr=hpr,
                        storepos=storepos, storespeed=storespeed,
                        storedecof=storedecof,
                        hcenter=hcenter, harc=harc, pcenter=pcenter, parc=parc)

        cannon = M61(parent=self,
                     mpos=Point3(0.0, 1.2, 0.0),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.0, 1.6, 0.0),
                     ammo=cnammo[0], viseach=5)
        self.add_cannon(cannon)


class TurretL70 (Turret):

    species = "turrl70"
    turnrate = radians(120.0)
    elevrate = radians(60.0)
    radarrange = 5000.0
    modelpath = ["models/weapons/turret_m61.egg"]; modelscale=4.0

    def __init__ (self, world, name, side,
                  hcenter, harc, pcenter, parc,
                  pos=None, hpr=None,
                  storepos=None, storespeed=1.0, storedecof=None,
                  parent=None,
                  cnammo=[600]):

        Turret.__init__(self, world=world, name=name, side=side,
                        parent=parent, pos=pos, hpr=hpr,
                        storepos=storepos, storespeed=storespeed,
                        storedecof=storedecof,
                        hcenter=hcenter, harc=harc, pcenter=pcenter, parc=parc)

        cannon = L70(parent=self,
                     mpos=Point3(0.0, 4.8, 0.0),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.0, 5.4, 0.0),
                     ammo=cnammo[0], viseach=3)
        self.add_cannon(cannon)


class TurretN2a38m (Turret):

    species = "turrmn2a38m"
    turnrate = radians(90.0)
    elevrate = radians(90.0)
    radarrange = 3000.0
    modelpath = ["models/weapons/turret_n2a38m.egg"]
    # texture = "models/weapons/turret_n2a38m_tex.png"

    def __init__ (self, world, name, side,
                  hcenter, harc, pcenter, parc,
                  pos=None, hpr=None,
                  storepos=None, storespeed=1.0, storedecof=None,
                  parent=None,
                  cnammo=[2000, 2000], hasradar=False):

        Turret.__init__(self, world=world, name=name, side=side,
                        parent=parent, pos=pos, hpr=hpr,
                        storepos=storepos, storespeed=storespeed,
                        storedecof=storedecof,
                        hcenter=hcenter, harc=harc, pcenter=pcenter, parc=parc)

        cannon1 = N2a38m(parent=self,
                         mpos=Point3(1.90, 5.34, 1.0),
                         mhpr=Vec3(0.0, 0.0, 0.0),
                         mltpos=Point3(1.90, 5.74, 1.0),
                         ammo=cnammo[0], viseach=5)
        self.add_cannon(cannon1)
        cannon2 = N2a38m(parent=self,
                         mpos=Point3(-1.90, 5.34, 1.0),
                         mhpr=Vec3(0.0, 0.0, 0.0),
                         mltpos=Point3(-1.90, 5.74, 1.0),
                         ammo=cnammo[1], viseach=5)
        self.add_cannon(cannon2)

        if not hasradar:
            for model in self._models:
                remove_subnodes(model, ("turret_radar",))


class TurretPkm (Turret):

    species = "turrpkm"
    turnrate = radians(180.0)
    elevrate = radians(90.0)
    radarrange = None
    modelpath = ["models/weapons/turret_pkm.egg"]
    texture = "models/weapons/turret_pkm_tex.png"

    def __init__ (self, world, name, side,
                  hcenter, harc, pcenter, parc,
                  pos=None, hpr=None,
                  storepos=None, storespeed=1.0, storedecof=None,
                  parent=None,
                  cnammo=[200], cnreloads=[2], cnrelrate=[12.0]):

        Turret.__init__(self, world=world, name=name, side=side,
                        parent=parent, pos=pos, hpr=hpr,
                        storepos=storepos, storespeed=storespeed,
                        storedecof=storedecof,
                        hcenter=hcenter, harc=harc, pcenter=pcenter, parc=parc)

        cannon = Pkm(parent=self,
                     mpos=Point3(0.0, 0.46, 0.03),
                     mhpr=Vec3(0.0, 0.0, 0.0),
                     mltpos=Point3(0.0, 0.86, 0.0),
                     ammo=cnammo[0], reloads=cnreloads[0],
                     relrate=cnrelrate[0], viseach=5)
        self.add_cannon(cannon)


class Fab500 (Bomb):

    species = "fab500"
    longdes = _("FAB-500")
    shortdes = _("FAB-500")
    cpitdes = {"ru": u"ФАБ-500"}
    mass = 510.0
    diameter = 0.400
    maxspeed = 400.0
    hitforce = 10.0
    expforce = 2000.0
    rcs = 0.00030
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 2.0)]
    modelpath = ["models/weapons/bomb_fab500.egg"]
    texture = "models/weapons/bomb_fab500_tex.png"
    normalmap = "models/weapons/bomb_fab500_nm.png"
    engsoundname = None

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None):

        Bomb.__init__(self, world=world, name=name, side=side,
                      pos=pos, hpr=hpr, speed=speed)


class Mk84 (Bomb):

    species = "mk84"
    longdes = _("Mark 84 Hammer")
    shortdes = _("Mk 84")
    mass = 907.0
    diameter = 0.458
    maxspeed = 440.0
    hitforce = 18.0
    expforce = 3600.0
    rcs = 0.00046
    hitboxdata = [(Point3(0.0, 0.0, 0.0), 2.0)]
    modelpath = ["models/weapons/bomb_mk84.egg"]
    texture = "models/weapons/bomb_mk84_tex.png"
    normalmap = "models/weapons/bomb_mk84_nm.png"
    engsoundname = None

    def __init__ (self, world, name, side,
                  pos=None, hpr=None, speed=None):

        Bomb.__init__(self, world=world, name=name, side=side,
                      pos=pos, hpr=hpr, speed=speed)


class Alq99 (JammingPod):

    species = "alq99"
    longdes = _("EDO Corporation AN/ALQ-99")
    shortdes = _("ALQ-99")
    mass = 430.0
    diameter = 0.500
    jamradius = 1500.0
    shockradius = 50.0
    modelpath = ["models/weapons/jammingpod_alq99.egg"]
    texture = "models/weapons/jammingpod_alq99_tex.png"
    normalmap = "models/weapons/jammingpod_alq99_nm.png"

    def __init__ (self):

        Jammer.__init__(self)


class Ptb1150 (DropTank):

    species = "ptb1150"
    longdes = _("PTB-1150")
    shortdes = _("PTB-1150")
    emptymass = 100.0
    diameter = 0.500
    maxfuel = 1150.0 * 0.8
    modelpath = ["models/weapons/droptank_ptb1150.egg"]
    texture = "models/weapons/droptank_ptb1150_tex.png"

    def __init__ (self):

        DropTank.__init__(self)


class Ptb1500 (DropTank):

    species = "ptb1500"
    longdes = _("PTB-1500")
    shortdes = _("PTB-1500")
    emptymass = 125.0
    diameter = 0.600
    maxfuel = 1500.0 * 0.8
    modelpath = ["models/weapons/droptank_ptb1500.egg"]
    texture = "models/weapons/droptank_ptb1500_tex.png"

    def __init__ (self):

        DropTank.__init__(self)


class Us370gal (DropTank):

    species = "us370gal"
    longdes = _("USAF 370 gal")
    shortdes = _("US-370")
    emptymass = 100.0
    diameter = 0.600
    maxfuel = 1400.0 * 0.8
    modelpath = ["models/weapons/droptank_us370gal.egg"]
    texture = "models/weapons/droptank_us370gal_tex.png"

    def __init__ (self):

        DropTank.__init__(self)


class Us600gal (DropTank):

    species = "us600gal"
    longdes = _("USAF 600 gal")
    shortdes = _("US-600")
    emptymass = 100.0
    diameter = 0.800
    maxfuel = 2270.0 * 0.8
    modelpath = ["models/weapons/droptank_us600gal.egg"]
    texture = "models/weapons/droptank_us600gal_tex.png"

    def __init__ (self):

        DropTank.__init__(self)


