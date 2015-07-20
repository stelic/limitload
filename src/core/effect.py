# -*- coding: UTF-8 -*-

from pandac.PandaModules import Vec3, Point2, Point3

from src import pycv
from src.core.fire import Fire
from src.core.misc import rgba
from src.core.misc import fx_uniform, fx_randrange
from src.core.trail import Trail, PolyExhaust, PolyBraid, PolyBurn


def fire_n_smoke (parent, store=None,
                  fcolor=rgba(255, 255, 255, 1.0),
                  fcolorend=rgba(246, 112, 27, 1.0),
                  fpos=Vec3(0.0, 0.0, 0.0),
                  spos=Vec3(0.0, 0.0, 0.0),
                  spos2=None,
                  ftcol=1.0,
                  stcol=1.0,
                  fforce=30.0,
                  sforce=30.0,
                  flifespan=0.6,
                  slifespan=1.2,
                  sclfact=1.0,
                  psfact=1.0,
                  pdir=Vec3(0, 0, 1),
                  fphpr=Vec3(0,0,0),
                  sphpr=Vec3(0,0,0),
                  emradfact=1.0,
                  emampfact=1.0,
                  absolute=False,
                  fdelay=0.0,
                  invscl=False):

    trails = []

    if not invscl:
        fscl1 = 0.021
        fscl2 = 0.004
        s2scl1 = 0.020 #0.028
        s2scl2 = 0.108 #0.054
    else:
        fscl1 = 0.014#0.013
        fscl2 = 0.028#0.020
        s2scl1 = 0.020 #0.028
        s2scl2 = 0.108 #0.054

    if absolute:
        risef = 10
    else:
        risef = 0

    if fpos is not None:
        fire = Trail(
            parent=parent,
            pos=fpos, scale1=fscl1 * sclfact, scale2=fscl2 * sclfact,
            lifespan=flifespan, poolsize=int(32 * psfact), force=fforce, alpha=1.0,
            ptype="explosion5-1",
            color=fcolor,
            colorend=fcolorend,
            tcol=ftcol, additive=False,
            pdir=pdir, phpr=fphpr,
            ltpos=fpos + Point3(0, 0, 0.5),
            ltcolor=(rgba(255, 80, 0, 1.0) * 2), ltcolor2=None,
            ltradius=20.0 * sclfact, ltradius2=5.0, lthalfat=0.5, ltpulse=True,
            obpos=fpos,
            obcolor=(rgba(255, 80, 0, 1.0) * 16), obcolor2=None,
            obradius=8.0 * sclfact, obradius2=1.0, obhalfat=0.1, obpulse=False,
            glowcolor=rgba(255, 255, 255, 1.0),
            emradius=1.90 * emradfact,
            emamp=2 * emampfact, emamps=1 * emampfact, ltoff=True, risefact=Vec3(0,0,risef),
            absolute=absolute,
            delay=fdelay,
            fardist=2800 * sclfact)
        trails.append(fire)
    if spos is not None:
        smoke = Trail(
            parent=parent,
            pos=spos, scale1=0.025 * sclfact, scale2=0.054 * sclfact,
            lifespan=slifespan, poolsize=int(96 * psfact), force=sforce, alpha=0.6,
            ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            color=rgba(255, 110, 0, 1.0),
            colorend=rgba(34, 32, 31, 1.0),
            tcol=stcol,
            pdir=pdir, phpr=sphpr, emradius=2.10 * emradfact,
            emamp=2 * emampfact, emamps=1 * emampfact, risefact=Vec3(0,0,risef), absolute=absolute,
            delay=0.0,
            fardist=14000 * sclfact)
        trails.append(smoke)
    if spos2 is not None:
        smoke2 = Trail(
            parent=parent,
            pos=spos2, scale1=s2scl1 * sclfact, scale2=s2scl2 * sclfact,
            lifespan=slifespan, poolsize=int(128 * psfact), force=0.0, alpha=0.9,
            ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            color=rgba(255, 110, 0, 1.0),
            #colorend=rgba(31, 29, 28, 1.0),
            colorend=rgba(18, 17, 16, 1.0),
            tcol=stcol,
            glowcolor=rgba(255, 255, 255, 1.0),
            pdir=Vec3(0,0,1), phpr=sphpr, emradius=1.10 * emradfact,
            emamp=1 * emampfact, emamps=1 * emampfact, risefact=Vec3(0,0,10), absolute=True,
            delay=0.0,
            fardist=14000 * sclfact)
        trails.append(smoke2)

    if store is not None:
        store.extend(trails)

    return trails


def fire_n_smoke_1 (parent, store=None,
                    sclfact=1.0,
                    emradfact=1.0,
                    fcolor=rgba(255, 255, 255, 1.0),
                    fcolorend=rgba(246, 112, 27, 1.0),
                    ftcol=1.0,
                    fpos=Vec3(0.0, 0.0, 0.0),
                    fpoolsize=24,
                    flength=26,
                    fspeed=32,
                    fdelay=0.0,
                    spos=Vec3(0.0, 0.0, 0.0),
                    stcol=1.0,
                    slifespan=1.0):

    trails = []

    if fpos is not None:
        fire = PolyExhaust(
            parent=parent,
            pos=fpos,
            radius0=2.0 * sclfact,
            radius1=1.0 * sclfact,
            length=flength,
            speed=fspeed,
            poolsize=fpoolsize,
            color=fcolor,
            colorend=fcolorend,
            tcol=ftcol,
            subnode=None,
            pdir=None,
            emradius=0.6 * emradfact,
            texture="images/particles/explosion7-1.png",
            glowmap=rgba(255, 255, 255, 1.0),
            ltpos=fpos + Point3(0, 0, 0.5),
            ltcolor=(rgba(255, 80, 0, 1.0) * 2),
            ltcolor2=rgba(255, 80, 0, 1.0),
            ltradius=10.0 * sclfact,
            ltradius2=5.0,
            lthalfat=0.5,
            ltpulse=True,
            ltoff=True,
            obpos=fpos,
            obcolor=(rgba(255, 80, 0, 1.0) * 16),
            obcolor2=None,
            obradius=4.0 * sclfact,
            obradius2=1.0,
            obhalfat=0.1,
            obpulse=False,
            frameskip=2,
            dbin=0,
            freezedist=2500.0 * sclfact,
            hidedist=3000.0 * sclfact,
            loddirang=10,
            loddirskip=4,
            delay=fdelay)
        trails.append(fire)
    if spos is not None:
        smoke = PolyBraid(
            parent=parent,
            pos=spos,
            numstrands=3,
            lifespan=slifespan,
            thickness=[1.2 * sclfact, 1.0 * sclfact, 1.1 * sclfact],
            endthickness=[18.0 * sclfact, 15.0 * sclfact, 16.0 * sclfact],
            spacing=1.0,
            offang=None,
            offrad=[1.2 * emradfact, 1.0 * emradfact, 1.1 * emradfact],
            offtang=[0.0, 0.33, 0.66],
            randang=True,
            randrad=True,
            texture=["images/particles/smoke6-1.png", "images/particles/smoke6-2.png", "images/particles/smoke6-3.png"],
            glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            #color=rgba(77, 33, 0, 1.0),#rgba(128, 55, 0, 1.0),
            #endcolor=rgba(31, 29, 28, 1.0),
            color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(255, 239, 230, 1.0)),
            dirlit=pycv(py=False, c=True),
            alphaexp=2.0,
            tcol=stcol,
            segperiod=0.010,
            farsegperiod=pycv(py=0.020, c=None),
            maxpoly=pycv(py=500, c=2000),
            farmaxpoly=2000,
            dbin=3,
            loddistout=14000 * sclfact,
            loddistalpha=12000 * sclfact,
            loddirang=10,
            loddirspcfac=10)
        trails.append(smoke)

    if store is not None:
        store.extend(trails)

    return trails


# def fire_n_smoke_2braid (parent, store=None,
                    # sclfact = 1.0,
                    # emradfact = 1.0,
                    # zvelfact = 1.0,
                    # fcolor = rgba(255, 255, 255, 1.0),
                    # fcolorend = rgba(246, 112, 27, 1.0),
                    # ftcol = 1.0,
                    # flifespan = 1.0,
                    # fpos = Vec3(0.0, 0.0, 0.0),
                    # fdelay = 0.0,
                    # spos = Vec3(0.0, 0.0, 0.0),
                    # stcol = 0.5,
                    # slifespan = 1.0):

    # trails = []

    # if fpos is not None:
        # fire = PolyBraid(
            # parent=parent,
            # pos=fpos,
            # numstrands=1,
            # lifespan=flifespan,
            # thickness=1.0 * sclfact,
            # endthickness=0.5 * sclfact,
            # spacing=0.2,
            # partvel=Vec3(0, 0, 1 * zvelfact),
            # emittang=Vec3(0, 0, 1),
            # emitnorm=Vec3(1, 0, 0),
            # offang=None,
            # offrad=1.0 * emradfact,
            # offtang=0.0,
            # randang=True,
            # randrad=True,
            # texture="images/particles/explosion7-1.png",
            # glowmap=rgba(255, 255, 255, 1.0),

            # ltpos=fpos + Point3(0, 0, 0.5),
            # ltcolor=(rgba(255, 80, 0, 1.0) * 2),
            # ltcolor2=rgba(255, 80, 0, 1.0),
            # ltradius=10.0 * sclfact,
            # ltradius2=5.0,
            # lthalfat=0.5,
            # ltpulse=True,
            # obpos=fpos,
            # obcolor=(rgba(255, 80, 0, 1.0) * 16),
            # obcolor2=None,
            # obradius=4.0 * sclfact,
            # obradius2=1.0,
            # obhalfat=0.1,
            # obpulse=False,

            # color=fcolor,
            # endcolor=fcolorend,
            # dirlit=False,
            # alphaexp=2.0,
            # tcol=ftcol,
            # segperiod=0.010,
            # farsegperiod=pycv(py=0.020, c=None),
            # maxpoly=pycv(py=500, c=2000),
            # farmaxpoly=2000,
            # dbin=3,
            # loddistout=10000 * sclfact,
            # loddistalpha=7000 * sclfact,
            # loddirang=10,
            # loddirspcfac=10,
            # delay=fdelay)
        # trails.append(fire)
    # if spos is not None:
        # smoke = PolyBraid(
            # parent=parent,
            # pos=spos,
            # numstrands=1,
            # lifespan=slifespan,
            # thickness=2.0 * sclfact,
            # endthickness=6.0 * sclfact,
            # spacing=0.5,
            # partvel=Vec3(0, 0, 1 * zvelfact),
            # emittang=Vec3(0, 0, 1),
            # emitnorm=Vec3(1, 0, 0),
            # offang=None,
            # offrad=1.0 * emradfact,
            # offtang=0.0,
            # randang=True,
            # randrad=True,
            # texture="images/particles/smoke6-1.png",
            # glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            # # color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            # # endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(255, 239, 230, 1.0)),
            # color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            # endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(85, 80, 77, 1.0)),
            # dirlit=pycv(py=False, c=True),
            # alphaexp=1.0,
            # tcol=stcol,
            # segperiod=0.010,
            # farsegperiod=pycv(py=0.020, c=None),
            # maxpoly=pycv(py=500, c=2000),
            # farmaxpoly=2000,
            # dbin=3,
            # loddistout=10000 * sclfact,
            # loddistalpha=7000 * sclfact,
            # loddirang=10,
            # loddirspcfac=10)
        # trails.append(smoke)

    # if store is not None:
        # store.extend(trails)

    # return trails
def fire_n_smoke_2 (parent, store=None,
                    sclfact = 1.0,
                    emradtype="circle",
                    emradfact = 1.0,
                    zvelfact = 1.0,
                    fcolor = rgba(255, 255, 255, 1.0),
                    fcolorend = rgba(246, 112, 27, 1.0),
                    ftcol = 1.0,
                    flifespan = 1.0,
                    fspacing=0.2,
                    fpos = Vec3(0.0, 0.0, 0.0),
                    fdelay = 0.0,
                    spos = Vec3(0.0, 0.0, 0.0),
                    stcol = 0.5,
                    slifespan = 1.0):

    trails = []

    if emradtype == "circle":
        emitradius = [("circle", 1.0 * emradfact)]
    elif emradtype == "fat-x":
        emitradius = [("xaxis", -1.0 * emradfact, 1.0 * emradfact, 0.4 * emradfact)]
    elif emradtype == "fat-y":
        emitradius = [("yaxis", -1.0 * emradfact, 1.0 * emradfact, 0.4 * emradfact)]

    duration = fx_uniform(120, 240)

    if fpos is not None:
        fire = PolyBurn(
            parent=parent,
            pos=fpos,
            numstrands=1,
            lifespan=flifespan,
            thickness=2.0 * sclfact,
            endthickness=1.0 * sclfact,
            spacing=fspacing,
            emitspeed=1 * zvelfact,
            emitradius=emitradius,
            offtang=0.0,
            texture="images/particles/explosion7-1.png",
            glowmap=rgba(255, 255, 255, 1.0),

            ltpos=fpos + Point3(0, 0, 0.5),
            ltcolor=(rgba(255, 80, 0, 1.0) * 2),
            ltcolor2=rgba(255, 80, 0, 1.0),
            ltradius=10.0 * sclfact,
            ltradius2=5.0,
            lthalfat=0.5,
            ltpulse=True,
            obpos=fpos,
            obcolor=(rgba(255, 80, 0, 1.0) * 16),
            obcolor2=None,
            obradius=4.0 * sclfact,
            obradius2=1.0,
            obhalfat=0.1,
            obpulse=False,

            color=fcolor,
            endcolor=fcolorend,
            dirlit=False,
            alphaexp=2.0,
            tcol=ftcol,
            maxpoly=pycv(py=500, c=2000),
            dbin=3,
            frameskip=pycv(py=2, c=1),
            delay=fdelay,
            duration=duration)
        trails.append(fire)
    if spos is not None:
        smoke = PolyBurn(
            parent=parent,
            pos=spos,
            numstrands=1,
            lifespan=slifespan,
            thickness=4.0 * sclfact,
            endthickness=12.0 * sclfact,
            spacing=0.6,
            emitspeed=1 * zvelfact,
            emitradius=emitradius,
            offtang=0.0,
            texture="images/particles/smoke6-1.png",
            glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            # color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            # endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(255, 239, 230, 1.0)),
            color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(85, 80, 77, 1.0)),
            dirlit=pycv(py=False, c=True),
            alphaexp=1.0,
            tcol=stcol,
            maxpoly=pycv(py=500, c=2000),
            dbin=3,
            frameskip=pycv(py=2, c=1),
            duration=duration * 1.2)
        trails.append(smoke)

    if store is not None:
        store.extend(trails)

    return trails


# def fire_n_smoke_3exhaust(parent, store=None,
                    # fpos1=Vec3(0.0, 0.0, 0.0),
                    # spos1=Vec3(0.0, 0.0, 2.0),
                    # flsfact=1.0,
                    # slsfact=1.0,
                    # sclfact=2.0,
                    # forcefact=1.0,
                    # psfact=1.0,
                    # emradfact=2.0,
                    # fdelay1=None,
                    # fdelay2=None,
                    # fdelay3=None,
                    # fdelay4=None,
                    # fdelay5=None):

    # if fdelay1 is None:
        # fdelay1 = fx_uniform(0.1, 1.0)
    # if fdelay2 is None:
        # fdelay2 = fx_uniform(1.0, 4.0)
    # if fdelay3 is None:
        # fdelay3 = fx_uniform(1.0, 4.0)
    # if fdelay4 is None:
        # fdelay4 = fx_uniform(1.0, 4.0)
    # if fdelay5 is None:
        # fdelay5 = fx_uniform(1.0, 4.0)

    # trails = []

    # if fpos1 is not None:
        # fire1 = PolyExhaust(
            # parent=parent,
            # pos=fpos1,
            # radius0=5.0 * sclfact,
            # radius1=7.0 * sclfact,
            # length=16.0 * forcefact,
            # speed=12 * forcefact,
            # poolsize=12 * psfact,
            # color=rgba(255, 255, 255, 1.0),
            # colorend=rgba(186, 92, 17, 1.0),
            # tcol=0.8,
            # subnode=None,
            # pdir=Vec3(0,0,1),
            # emradius=5.0 * emradfact,
            # texture="images/particles/explosion6-1.png",
            # glowmap=rgba(255, 255, 255, 1.0),
            # ltoff=True,

            # obpos=fpos1,
            # obcolor=(rgba(255, 80, 0, 1.0) * 16),
            # obcolor2=None,
            # obradius=30.0 * sclfact,
            # obradius2=10.0,
            # obhalfat=0.4,
            # obpulse=0.0,

            # frameskip=2,
            # dbin=0,
            # freezedist=2500.0 * sclfact,
            # hidedist=3000.0 * sclfact,
            # loddirang=10,
            # loddirskip=4,
            # delay=fdelay1)
        # trails.append(fire1)

    # fire2 = PolyExhaust(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        # radius0=1.0 * sclfact,
        # radius1=3.0 * sclfact,
        # length=8.0 * forcefact,
        # speed=8 * forcefact,
        # poolsize=12 * psfact,
        # color=rgba(255, 232, 117, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8,
        # subnode=None,
        # pdir=Vec3(0,0,1),
        # emradius=1.0 * emradfact,
        # texture="images/particles/explosion6-1.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # ltoff=True,
        # frameskip=2,
        # dbin=0,
        # freezedist=2500.0 * sclfact,
        # hidedist=3000.0 * sclfact,
        # loddirang=10,
        # loddirskip=4,
        # delay=fdelay2)
    # trails.append(fire2)

    # fire3 = PolyExhaust(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        # radius0=1.0 * sclfact,
        # radius1=2.0 * sclfact,
        # length=8.0 * forcefact,
        # speed=8 * forcefact,
        # poolsize=12 * psfact,
        # color=rgba(255, 255, 41, 1.0),
        # colorend=rgba(186, 102, 47, 1.0),
        # tcol=0.6,
        # subnode=None,
        # pdir=Vec3(0,0,1),
        # emradius=1.2 * emradfact,
        # texture="images/particles/explosion6-2.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # ltoff=True,
        # frameskip=2,
        # dbin=0,
        # freezedist=2500.0 * sclfact,
        # hidedist=3000.0 * sclfact,
        # loddirang=10,
        # loddirskip=4,
        # delay=fdelay3)
    # trails.append(fire3)

    # fire4 = PolyExhaust(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        # radius0=1.0 * sclfact,
        # radius1=2.0 * sclfact,
        # length=8.0 * forcefact,
        # speed=8 * forcefact,
        # poolsize=12 * psfact,
        # color=rgba(255, 255, 255, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8,
        # subnode=None,
        # pdir=Vec3(0,0,1),
        # emradius=1.1 * emradfact,
        # texture="images/particles/explosion6-3.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # ltoff=True,
        # frameskip=2,
        # dbin=0,
        # freezedist=2500.0 * sclfact,
        # hidedist=3000.0 * sclfact,
        # loddirang=10,
        # loddirskip=4,
        # delay=fdelay4)
    # trails.append(fire4)

    # fire5 = PolyExhaust(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        # radius0=2.0 * sclfact,
        # radius1=3.0 * sclfact,
        # length=6.0 * forcefact,
        # speed=6 * forcefact,
        # poolsize=10 * psfact,
        # color=rgba(255, 255, 255, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8,
        # subnode=None,
        # pdir=Vec3(0,0,1),
        # emradius=1.0 * emradfact,
        # texture="images/particles/explosion6-4.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # ltoff=True,
        # frameskip=2,
        # dbin=0,
        # freezedist=2500.0 * sclfact,
        # hidedist=3000.0 * sclfact,
        # loddirang=10,
        # loddirskip=4,
        # delay=fdelay5)
    # trails.append(fire5)

    # if spos1 is not None:
        # smoke1 = PolyExhaust(
            # parent=parent,
            # pos=spos1,
            # radius0=8.0 * sclfact,
            # radius1=20.0 * sclfact,
            # length=78.0 * forcefact,
            # speed=36 * forcefact,
            # poolsize=16 * psfact,
            # color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            # colorend=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(43, 40, 39, 1.0)),
            # tcol=0.6,
            # subnode=None,
            # pdir=Vec3(0,0,1),
            # emradius=0.5 * emradfact * parent._size_xy,
            # texture="images/particles/smoke6-1.png",
            # glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            # ltoff=pycv(py=True, c=False),
            # frameskip=2,
            # dbin=0,
            # freezedist=3000.0 * sclfact,
            # hidedist=4000.0 * sclfact,
            # loddirang=10,
            # loddirskip=4,
            # delay=0.0)
        # trails.append(smoke1)

    # if store is not None:
        # store.extend(trails)

    # return trails
# def fire_n_smoke_3braid (parent, store=None,
                    # fpos1=Vec3(0.0, 0.0, 0.0),
                    # spos1=Vec3(0.0, 0.0, 2.0),
                    # sclfact=2.0,
                    # emradfact=2.0,
                    # forcefact=1.0,
                    # flsfact=1.0,
                    # slsfact=1.0,
                    # fdelay1=None,
                    # fdelay2=None,
                    # fdelay3=None,
                    # fdelay4=None,
                    # fdelay5=None):

    # if fdelay1 is None:
        # fdelay1 = fx_uniform(0.1, 1.0)
    # if fdelay2 is None:
        # fdelay2 = fx_uniform(1.0, 4.0)
    # if fdelay3 is None:
        # fdelay3 = fx_uniform(1.0, 4.0)
    # if fdelay4 is None:
        # fdelay4 = fx_uniform(1.0, 4.0)
    # if fdelay5 is None:
        # fdelay5 = fx_uniform(1.0, 4.0)

    # trails = []

    # if fpos1 is not None:
        # fire1 = PolyBraid(
            # parent=parent,
            # pos=fpos1,
            # # # # # numstrands=3,
            # numstrands=1,
            # lifespan=2.0 * flsfact,
            # # # # # thickness=[6.0 * sclfact, 4.0 * sclfact, 5.0 * sclfact],
            # # # # # endthickness=[9.0 * sclfact, 6.0 * sclfact, 7.0 * sclfact],
            # thickness=5.0 * sclfact,
            # endthickness=7.0 * sclfact,
            # spacing=0.2,
            # partvel=Vec3(0, 0, 10 * forcefact),
            # emittang=Vec3(0, 0, 1),
            # emitnorm=Vec3(1, 0, 0),
            # offang=None,
            # # # # # offrad=[6.0 * emradfact, 4.0 * emradfact, 5.0 * emradfact],
            # offrad=5.0 * emradfact,
            # # # # # offtang=[0.0, 0.33, 0.66],
            # offtang=0.0,
            # randang=True,
            # randrad=True,
            # # # # # texture=["images/particles/explosion6-1.png", "images/particles/explosion6-2.png", "images/particles/explosion6-3.png"],
            # texture="images/particles/explosion7-1.png",
            # glowmap=rgba(255, 255, 255, 1.0),

            # obpos=fpos1,
            # obcolor=(rgba(255, 80, 0, 1.0) * 16),
            # obcolor2=None,
            # obradius=30.0 * sclfact,
            # obradius2=10.0,
            # obhalfat=0.6,
            # obpulse=False,

            # color=rgba(255, 255, 255, 1.0),
            # endcolor=rgba(186, 92, 17, 1.0),
            # dirlit=False,
            # alphaexp=2.0,
            # tcol=0.8,
            # segperiod=0.010,
            # farsegperiod=pycv(py=0.020, c=None),
            # maxpoly=pycv(py=500, c=2000),
            # farmaxpoly=2000,
            # dbin=3,
            # loddistout=10000 * sclfact,
            # loddistalpha=7000 * sclfact,
            # loddirang=10,
            # loddirspcfac=10,
            # delay=fdelay1)
        # trails.append(fire1)

    # fire2 = PolyBraid(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        # numstrands=1,
        # lifespan=1.0 * flsfact,
        # thickness=1.0 * sclfact,
        # endthickness=3.0 * sclfact,
        # spacing=0.2,
        # partvel=Vec3(0, 0, 10 * forcefact),
        # emittang=Vec3(0, 0, 1),
        # emitnorm=Vec3(1, 0, 0),
        # offang=None,
        # offrad=1.0 * emradfact,
        # offtang=0.0,
        # randang=True,
        # randrad=True,
        # texture="images/particles/explosion6-1.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # color=rgba(255, 232, 117, 1.0),
        # endcolor=rgba(186, 92, 17, 1.0),
        # dirlit=False,
        # alphaexp=2.0,
        # tcol=0.8,
        # segperiod=0.010,
        # farsegperiod=pycv(py=0.020, c=None),
        # maxpoly=pycv(py=500, c=2000),
        # farmaxpoly=2000,
        # dbin=3,
        # loddistout=10000 * sclfact,
        # loddistalpha=7000 * sclfact,
        # loddirang=10,
        # loddirspcfac=10,
        # delay=fdelay2)
    # trails.append(fire2)

    # fire3 = PolyBraid(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        # numstrands=1,
        # lifespan=1.0 * flsfact,
        # thickness=1.0 * sclfact,
        # endthickness=2.0 * sclfact,
        # spacing=0.2,
        # partvel=Vec3(0, 0, 10 * forcefact),
        # emittang=Vec3(0, 0, 1),
        # emitnorm=Vec3(1, 0, 0),
        # offang=None,
        # offrad=1.2 * emradfact,
        # offtang=0.0,
        # randang=True,
        # randrad=True,
        # texture="images/particles/explosion6-2.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # color=rgba(255, 255, 41, 1.0),
        # endcolor=rgba(186, 102, 47, 1.0),
        # dirlit=False,
        # alphaexp=2.0,
        # tcol=0.6,
        # segperiod=0.010,
        # farsegperiod=pycv(py=0.020, c=None),
        # maxpoly=pycv(py=500, c=2000),
        # farmaxpoly=2000,
        # dbin=3,
        # loddistout=10000 * sclfact,
        # loddistalpha=7000 * sclfact,
        # loddirang=10,
        # loddirspcfac=10,
        # delay=fdelay3)
    # trails.append(fire3)

    # fire4 = PolyBraid(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        # numstrands=1,
        # lifespan=1.0 * flsfact,
        # thickness=1.0 * sclfact,
        # endthickness=2.0 * sclfact,
        # spacing=0.2,
        # partvel=Vec3(0, 0, 10 * forcefact),
        # emittang=Vec3(0, 0, 1),
        # emitnorm=Vec3(1, 0, 0),
        # offang=None,
        # offrad=1.1 * emradfact,
        # offtang=0.0,
        # randang=True,
        # randrad=True,
        # texture="images/particles/explosion6-3.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # color=rgba(255, 255, 255, 1.0),
        # endcolor=rgba(186, 92, 17, 1.0),
        # dirlit=False,
        # alphaexp=2.0,
        # tcol=0.8,
        # segperiod=0.010,
        # farsegperiod=pycv(py=0.020, c=None),
        # maxpoly=pycv(py=500, c=2000),
        # farmaxpoly=2000,
        # dbin=3,
        # loddistout=10000 * sclfact,
        # loddistalpha=7000 * sclfact,
        # loddirang=10,
        # loddirspcfac=10,
        # delay=fdelay4)
    # trails.append(fire4)

    # fire5 = PolyBraid(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        # numstrands=1,
        # lifespan=1.0 * flsfact,
        # thickness=2.0 * sclfact,
        # endthickness=3.0 * sclfact,
        # spacing=0.2,
        # partvel=Vec3(0, 0, 10 * forcefact),
        # emittang=Vec3(0, 0, 1),
        # emitnorm=Vec3(1, 0, 0),
        # offang=None,
        # offrad=1.0 * emradfact,
        # offtang=0.0,
        # randang=True,
        # randrad=True,
        # texture="images/particles/explosion6-4.png",
        # glowmap=rgba(255, 255, 255, 1.0),
        # color=rgba(255, 255, 255, 1.0),
        # endcolor=rgba(186, 92, 17, 1.0),
        # dirlit=False,
        # alphaexp=2.0,
        # tcol=0.8,
        # segperiod=0.010,
        # farsegperiod=pycv(py=0.020, c=None),
        # maxpoly=pycv(py=500, c=2000),
        # farmaxpoly=2000,
        # dbin=3,
        # loddistout=10000 * sclfact,
        # loddistalpha=7000 * sclfact,
        # loddirang=10,
        # loddirspcfac=10,
        # delay=fdelay5)
    # trails.append(fire5)

    # if spos1 is not None:
        # smoke1 = PolyBraid(
            # parent=parent,
            # pos=spos1,
            # # # # # numstrands=3,
            # numstrands=1,
            # lifespan=3.0 * slsfact,
            # # # # # thickness=[8.0 * sclfact, 6.0 * sclfact, 7.0 * sclfact],
            # # # # # endthickness=[20.0 * sclfact, 18.0 * sclfact, 19.0 * sclfact],
            # thickness=8.0 * sclfact,
            # endthickness=20.0 * sclfact,
            # spacing=0.15,
            # partvel=Vec3(0, 0, 40 * forcefact),
            # emittang=Vec3(0, 0, 1),
            # emitnorm=Vec3(1, 0, 0),
            # offang=None,
            # # # # # offrad=[0.5 * emradfact * parent._size_xy, 0.3 * emradfact * parent._size_xy , 0.4 * emradfact * parent._size_xy],
            # offrad=0.5 * emradfact * parent._size_xy,
            # # # # # offtang=[0.0, 0.33, 0.66],
            # offtang=0.0,
            # randang=True,
            # randrad=True,
            # # # # # texture=["images/particles/smoke6-1.png", "images/particles/smoke6-2.png", "images/particles/smoke6-3.png"],
            # texture="images/particles/smoke6-1.png",
            # glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            # #color=rgba(77, 33, 0, 1.0),#rgba(128, 55, 0, 1.0),
            # #endcolor=rgba(31, 29, 28, 1.0),
            # color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            # endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(43, 40, 39, 1.0)),
            # dirlit=pycv(py=False, c=True),
            # alphaexp=1.0,
            # tcol=0.6,
            # segperiod=0.010,
            # farsegperiod=pycv(py=0.020, c=None),
            # maxpoly=pycv(py=500, c=2000),
            # farmaxpoly=2000,
            # dbin=3,
            # loddistout=14000 * sclfact,
            # loddistalpha=12000 * sclfact,
            # loddirang=10,
            # loddirspcfac=10)
        # trails.append(smoke1)

    # if store is not None:
        # store.extend(trails)

    # return trails
def fire_n_smoke_3 (parent, store=None,
                    fpos1=Vec3(0.0, 0.0, 0.0),
                    spos1=Vec3(0.0, 0.0, 2.0),
                    sclfact=2.0,
                    emradfact=2.0,
                    forcefact=1.0,
                    flsfact=1.0,
                    slsfact=1.0,
                    fdelay1=None,
                    fdelay2=None,
                    fdelay3=None,
                    fdelay4=None,
                    fdelay5=None):

    if fdelay1 is None:
        fdelay1 = fx_uniform(0.1, 1.0)
    if fdelay2 is None:
        fdelay2 = fx_uniform(1.0, 4.0)
    if fdelay3 is None:
        fdelay3 = fx_uniform(1.0, 4.0)
    if fdelay4 is None:
        fdelay4 = fx_uniform(1.0, 4.0)
    if fdelay5 is None:
        fdelay5 = fx_uniform(1.0, 4.0)

    duration = fx_uniform(180, 300)

    trails = []

    if fpos1 is not None:
        fire1 = PolyBurn(
            parent=parent,
            pos=fpos1,
            # # # # numstrands=3,
            numstrands=1,
            lifespan=2.0 * flsfact,
            # # # # thickness=[6.0 * sclfact, 4.0 * sclfact, 5.0 * sclfact],
            # # # # endthickness=[9.0 * sclfact, 6.0 * sclfact, 7.0 * sclfact],
            thickness=10.0 * sclfact,
            endthickness=14.0 * sclfact,
            spacing=0.15,
            emitspeed=10 * forcefact,
            # # # # emitradius=[6.0 * emradfact, 4.0 * emradfact, 5.0 * emradfact],
            emitradius=5.0 * emradfact,
            # # # # offtang=[0.0, 0.33, 0.66],
            offtang=0.0,
            # # # # texture=["images/particles/explosion6-1.png", "images/particles/explosion6-2.png", "images/particles/explosion6-3.png"],
            texture="images/particles/explosion7-1.png",
            glowmap=rgba(255, 255, 255, 1.0),

            obpos=fpos1,
            obcolor=(rgba(255, 80, 0, 1.0) * 16),
            obcolor2=None,
            obradius=30.0 * sclfact,
            obradius2=10.0,
            obhalfat=0.6,
            obpulse=False,

            color=rgba(255, 255, 255, 1.0),
            endcolor=rgba(186, 92, 17, 1.0),
            dirlit=False,
            alphaexp=2.0,
            tcol=0.8,
            maxpoly=pycv(py=500, c=2000),
            dbin=3,
            frameskip=pycv(py=2, c=1),
            delay=fdelay1,
            duration=duration)
        trails.append(fire1)

    fire2 = PolyBurn(
        parent=parent,
        pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        numstrands=1,
        lifespan=1.0 * flsfact,
        thickness=2.0 * sclfact,
        endthickness=6.0 * sclfact,
        spacing=0.15,
        emitspeed=10 * forcefact,
        emitradius=1.0 * emradfact,
        offtang=0.0,
        texture="images/particles/explosion6-1.png",
        glowmap=rgba(255, 255, 255, 1.0),
        color=rgba(255, 232, 117, 1.0),
        endcolor=rgba(186, 92, 17, 1.0),
        dirlit=False,
        alphaexp=2.0,
        tcol=0.8,
        maxpoly=pycv(py=500, c=2000),
        dbin=3,
        frameskip=pycv(py=2, c=1),
        delay=fdelay2,
        duration=duration * 0.6)
    trails.append(fire2)

    fire3 = PolyBurn(
        parent=parent,
        pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, parent._size_xy * 0.9), 0.0 * sclfact),
        numstrands=1,
        lifespan=1.0 * flsfact,
        thickness=2.0 * sclfact,
        endthickness=4.0 * sclfact,
        spacing=0.15,
        emitspeed=10 * forcefact,
        emitradius=1.2 * emradfact,
        offtang=0.0,
        texture="images/particles/explosion6-2.png",
        glowmap=rgba(255, 255, 255, 1.0),
        color=rgba(255, 255, 41, 1.0),
        endcolor=rgba(186, 102, 47, 1.0),
        dirlit=False,
        alphaexp=2.0,
        tcol=0.6,
        maxpoly=pycv(py=500, c=2000),
        dbin=3,
        frameskip=pycv(py=2, c=1),
        delay=fdelay3,
        duration=duration * 0.6)
    trails.append(fire3)

    fire4 = PolyBurn(
        parent=parent,
        pos=Point3(fx_uniform(0, -parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        numstrands=1,
        lifespan=1.0 * flsfact,
        thickness=2.0 * sclfact,
        endthickness=4.0 * sclfact,
        spacing=0.15,
        emitspeed=10 * forcefact,
        emitradius=1.1 * emradfact,
        offtang=0.0,
        texture="images/particles/explosion6-3.png",
        glowmap=rgba(255, 255, 255, 1.0),
        color=rgba(255, 255, 255, 1.0),
        endcolor=rgba(186, 92, 17, 1.0),
        dirlit=False,
        alphaexp=2.0,
        tcol=0.8,
        maxpoly=pycv(py=500, c=2000),
        dbin=3,
        frameskip=pycv(py=2, c=1),
        delay=fdelay4,
        duration=duration * 0.6)
    trails.append(fire4)

    fire5 = PolyBurn(
        parent=parent,
        pos=Point3(fx_uniform(0, parent._size_xy * 0.9), fx_uniform(0, -parent._size_xy * 0.9), 0.0 * sclfact),
        numstrands=1,
        lifespan=1.0 * flsfact,
        thickness=4.0 * sclfact,
        endthickness=6.0 * sclfact,
        spacing=0.15,
        emitspeed=10 * forcefact,
        emitradius=1.0 * emradfact,
        offtang=0.0,
        texture="images/particles/explosion6-4.png",
        glowmap=rgba(255, 255, 255, 1.0),
        color=rgba(255, 255, 255, 1.0),
        endcolor=rgba(186, 92, 17, 1.0),
        dirlit=False,
        alphaexp=2.0,
        tcol=0.8,
        maxpoly=pycv(py=500, c=2000),
        dbin=3,
        frameskip=pycv(py=2, c=1),
        delay=fdelay5,
        duration=duration * 0.6)
    trails.append(fire5)

    if spos1 is not None:
        smoke1 = PolyBurn(
            parent=parent,
            pos=spos1,
            # # # # numstrands=3,
            numstrands=1,
            lifespan=3.0 * slsfact,
            # # # # thickness=[8.0 * sclfact, 6.0 * sclfact, 7.0 * sclfact],
            # # # # endthickness=[20.0 * sclfact, 18.0 * sclfact, 19.0 * sclfact],
            thickness=16.0 * sclfact,
            endthickness=40.0 * sclfact,
            spacing=0.1,
            emitspeed=40 * forcefact,
            # # # # emitradius=[0.5 * emradfact * parent._size_xy, 0.3 * emradfact * parent._size_xy , 0.4 * emradfact * parent._size_xy],
            emitradius=0.5 * emradfact * parent._size_xy,
            # # # # offtang=[0.0, 0.33, 0.66],
            offtang=0.0,
            # # # # texture=["images/particles/smoke6-1.png", "images/particles/smoke6-2.png", "images/particles/smoke6-3.png"],
            texture="images/particles/smoke6-1.png",
            glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
            #color=rgba(77, 33, 0, 1.0),#rgba(128, 55, 0, 1.0),
            #endcolor=rgba(31, 29, 28, 1.0),
            color=pycv(py=rgba(77, 33, 0, 1.0), c=rgba(255, 109, 0, 1.0)),
            endcolor=pycv(py=rgba(18, 17, 16, 1.0), c=rgba(43, 40, 39, 1.0)),
            dirlit=pycv(py=False, c=True),
            alphaexp=1.0,
            tcol=0.6,
            maxpoly=pycv(py=500, c=2000),
            dbin=3,
            frameskip=pycv(py=2, c=1),
            duration=duration * 1.3)
        trails.append(smoke1)

    if store is not None:
        store.extend(trails)

    return trails


# def fire_n_smoke_2p (parent, store=None,
                     # fpos1=Vec3(0.0, 0.0, 0.0),
                     # spos1=Vec3(0.0, 0.0, 2.0),
                     # fforfact=1.0,
                     # sforfact=1.0,
                     # flsfact=1.0,
                     # slsfact=1.0,
                     # sclfact=1.0,
                     # psfact=1.0,
                     # emradfact=1.0,
                     # emampfact=1.0,
                     # fdelay1=None,
                     # fdelay2=None,
                     # fdelay3=None,
                     # fdelay4=None,
                     # fdelay5=None):

    # if fdelay1 is None:
        # fdelay1 = fx_uniform(0.1, 1.0)
    # if fdelay2 is None:
        # fdelay2 = fx_uniform(1.0, 4.0)
    # if fdelay3 is None:
        # fdelay3 = fx_uniform(1.0, 4.0)
    # if fdelay4 is None:
        # fdelay4 = fx_uniform(1.0, 4.0)
    # if fdelay5 is None:
        # fdelay5 = fx_uniform(1.0, 4.0)

    # trails = []

    # if fpos1 is not None:
        # fire1 = Trail(
            # parent=parent,
            # pos=fpos1, scale1=0.04 * sclfact, scale2=0.06 * sclfact,
            # lifespan=2.0 * flsfact, poolsize=int(32 * psfact), force=2.0 * fforfact, alpha=1.0,
            # ptype="explosion5-4",
            # color=rgba(255, 255, 255, 1.0),
            # colorend=rgba(186, 92, 17, 1.0),
            # tcol=0.8, additive=False,
            # pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
            # obpos=fpos1,
            # obcolor=(rgba(255, 80, 0, 1.0) * 16), obcolor2=None,
            # obradius=30.0 * sclfact, obradius2=10.0, obhalfat=0.6, obpulse=False,
            # glowcolor=rgba(255, 255, 255, 1.0),
            # emradius=0.08 * emradfact * parent._size_xy,
            # emamp=2 * emampfact, emamps=0, ltoff=True, risefact=Vec3(0,0,10),
            # absolute=True,
            # delay=fdelay1)
        # trails.append(fire1)

    # fire2 = Trail(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.8), fx_uniform(0, parent._size_xy * 0.8), 0),
        # scale1=0.01 * sclfact, scale2=0.03 * sclfact,
        # lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.95,
        # ptype="explosion5-3",
        # color=rgba(255, 232, 117, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8, additive=False,
        # pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        # glowcolor=rgba(255, 255, 255, 1.0),
        # emradius=1.00 * emradfact,
        # emamp=2 * emampfact, emamps=0, ltoff=True, risefact=Vec3(0,0,10),
        # absolute=True,
        # delay=fdelay2)
    # trails.append(fire2)

    # fire3 = Trail(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.8), fx_uniform(0, parent._size_xy * 0.8), 0),
        # scale1=0.01 * sclfact, scale2=0.02 * sclfact,
        # lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.9,
        # ptype="explosion5-2",
        # color=rgba(255, 255, 41, 1.0),
        # colorend=rgba(186, 102, 47, 1.0),
        # tcol=0.6, additive=False,
        # pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        # glowcolor=rgba(255, 255, 255, 1.0),
        # emradius=1.20 * emradfact,
        # emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        # absolute=True,
        # delay=fdelay3)
    # trails.append(fire3)

    # fire4 = Trail(
        # parent=parent,
        # pos=Point3(fx_uniform(0, -parent._size_xy * 0.8), fx_uniform(0, -parent._size_xy * 0.8), 0),
        # scale1=0.01 * sclfact, scale2=0.02 * sclfact,
        # lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.95,
        # ptype="explosion5-4",
        # color=rgba(255, 255, 255, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8, additive=False,
        # pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        # glowcolor=rgba(255, 255, 255, 1.0),
        # emradius=1.10 * emradfact,
        # emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        # absolute=True,
        # delay=fdelay4)
    # trails.append(fire4)

    # fire5 = Trail(
        # parent=parent,
        # pos=Point3(fx_uniform(0, parent._size_xy * 0.8), fx_uniform(0, -parent._size_xy * 0.8), 0),
        # scale1=0.02 * sclfact, scale2=0.03 * sclfact,
        # lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.9,
        # ptype="explosion5-4",
        # color=rgba(255, 255, 255, 1.0),
        # colorend=rgba(186, 92, 17, 1.0),
        # tcol=0.8, additive=False,
        # pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        # glowcolor=rgba(255, 255, 255, 1.0),
        # emradius=1.00 * emradfact,
        # emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        # absolute=True,
        # delay=fdelay5)
    # trails.append(fire5)

    # if spos1 is not None:
        # smoke1 = Trail(
            # parent=parent,
            # pos=spos1, scale1=0.06 * sclfact, scale2=0.18 * sclfact,
            # lifespan=3.0 * slsfact, poolsize=int(32 * psfact), force=1.0 * sforfact, alpha=0.6,
            # ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            # color=rgba(255, 110, 0, 1.0),
            # colorend=rgba(32, 32, 32, 1.0),
            # tcol=0.6,
            # pdir=Vec3(0, 0, 1), phpr=Vec3(0,0,0),
            # emradius=0.5 * emradfact * parent._size_xy, emamp=1 * emampfact, emamps=0,
            # risefact=Vec3(0,0,10), absolute=True,
            # delay=0.0)
        # trails.append(smoke1)

    # if store is not None:
        # store.extend(trails)

    # return trails


# def fire_n_smoke_3 (parent, store=None,
                    # fpos1=Vec3(0.0, 0.0, 0.0),
                    # spos1=Vec3(0.0, 0.0, 0.0),
                    # spoolsize=32,
                    # salpha=0.6,
                    # fdelay1=None,
                    # fdelay2=None,
                    # fdelay3=None,
                    # fdelay4=None):

    # if fdelay1 is None:
        # fdelay1 = fx_uniform(0.0, 1.0)
    # if fdelay2 is None:
        # fdelay2 = fx_uniform(1.0, 4.0)
    # if fdelay3 is None:
        # fdelay3 = fx_uniform(1.0, 4.0)
    # if fdelay4 is None:
        # fdelay4 = fx_uniform(1.0, 4.0)

    # trails = []

    # if fpos1 is not None:
        # fire1 = Fire(world=parent.world,
                     # size=(parent._size_xy, parent._size_xy * 0.8),
                     # color=rgba(255, 219, 188, 1.0),
                     # pos=fpos1,
                     # hpr=Vec3(0, 0, 0),
                     # nsides=0,
                     # fps=fx_randrange(32,64),
                     # parent=parent)
        # trails.append(fire1)
    # # pos = [Point2(fx_uniform(0, self._size_xy * 0.8), fx_uniform(0, self._size_xy * 0.7)),
           # # Point2(fx_uniform(0, self._size_xy * 0.8), fx_uniform(-self._size_xy * 0.7, 0)),
           # # Point2(fx_uniform(-self._size_xy * 0.8, 0), fx_uniform(0, self._size_xy * 0.7)),
           # # Point2(fx_uniform(-self._size_xy * 0.8, 0), fx_uniform(-self._size_xy * 0.7, 0))]
    # for i in range(fx_randrange(3, 6)):
        # pos = Point2(fx_uniform(-parent._size_xy * 0.8, parent._size_xy * 0.8), fx_uniform(-parent._size_xy * 0.7, parent._size_xy * 0.7))
        # w, h = parent._size_xy * 0.4, parent._size_xy * 0.25
        # width, height = w + fx_uniform(-w/2, w/2), h + fx_uniform(-h/2, h/2)
        # fire = Fire(
            # world=parent.world,
            # size=(width, height),
            # color=rgba(255, 236, 188, 1.0),
            # pos=pos,
            # hpr=Vec3(0, 0, 0),
            # sink=0.25 * height,
            # nsides=0,
            # fps=fx_randrange(32,64),
            # parent=parent)
        # trails.append(fire)
    # if spos1 is not None:
        # smoke1 = Trail(
            # parent=parent,
            # pos=Vec3(0.0, 0.0, 2.0), scale1=0.06, scale2=0.18,
            # lifespan=3.0, poolsize=spoolsize, force=1.0, alpha=salpha,
            # ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            # color=rgba(255, 140, 0, 1.0),
            # colorend=rgba(32, 32, 32, 1.0),
            # tcol=0.6,
            # pdir=Vec3(0, 0, 1), phpr=Vec3(0,0,0),
            # emradius=0.5 * parent._size_xy, emamp=0, emamps=0,
            # risefact=Vec3(0,0,10), absolute=True,
            # delay=0.0)
        # trails.append(smoke1)

    # if store is not None:
        # store.extend(trails)

    # return trails


def fire_n_smoke_4 (parent, store=None,
                    fpos=Vec3(0.0, 0.0, 0.0),
                    spos=None,
                    stcol=1.0,
                    fforce=30.0,
                    sforce=30.0,
                    flifespan=0.6,
                    slifespan=1.2,
                    sclfact=1.0,
                    psfact=1.0,
                    pdir=Vec3(0, 0, 1),
                    fphpr=Vec3(0,0,0),
                    sphpr=Vec3(0,0,0),
                    emradfact=1.0,
                    emampfact=1.0,
                    absolute=False,
                    fdelay=0.0):

    trails = []

    if absolute:
        risef = 10
    else:
        risef = 0

    if fpos is not None:
        fire = Trail(
            parent=parent,
            pos=fpos, scale1=1.0 * sclfact, scale2=1.0 * sclfact,
            lifespan=flifespan, poolsize=int(32 * psfact), force=fforce,
            alpha=1.0, alphaout=True,
            ptype="fire-trail/fire-trail", fps=24,
            color=rgba(255, 255, 255, 1.0),
            pdir=pdir, phpr=fphpr,
            ltpos=fpos + Point3(0, 0, 0.5),
            ltcolor=(rgba(255, 80, 0, 1.0) * 2), ltcolor2=None,
            ltradius=20.0 * sclfact, ltradius2=5.0, lthalfat=0.5, ltpulse=True,
            obpos=fpos,
            obcolor=(rgba(255, 80, 0, 1.0) * 16), obcolor2=None,
            obradius=3.0 * sclfact, obradius2=1.0, obhalfat=0.2, obpulse=False,
            glowcolor=rgba(255, 255, 255, 0.5),
            emradius=1.90 * emradfact,
            emamp=2 * emampfact, emamps=1 * emampfact, ltoff=True, risefact=Vec3(0,0,risef), absolute=absolute,
            delay=fdelay,
            fardist=2800 * sclfact)
        trails.append(fire)
    if spos is not None:
        smoke = Trail(
            parent=parent,
            pos=spos, scale1=0.01 * sclfact, scale2=0.03 * sclfact,
            lifespan=slifespan, poolsize=int(64 * psfact), force=0.0, alpha=0.9,
            ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            color=rgba(255, 110, 0, 1.0),
            #colorend=rgba(31, 29, 28, 1.0),
            colorend=rgba(18, 17, 16, 1.0),
            tcol=stcol,
            glowcolor=rgba(255, 255, 255, 1.0),
            pdir=Vec3(0,0,1), phpr=sphpr, emradius=1.10 * emradfact,
            emamp=1 * emampfact, emamps=1 * emampfact, risefact=Vec3(0,0,10), absolute=True,
            delay=0.0,
            fardist=14000 * sclfact)
        trails.append(smoke)

    if store is not None:
        store.extend(trails)

    return trails


