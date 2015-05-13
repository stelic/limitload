# -*- coding: UTF-8 -*-

from pandac.PandaModules import Vec3, Point2, Point3

from src import pycv
from src.core.fire import Fire
from src.core.misc import rgba
from src.core.misc import fx_uniform, fx_randrange
from src.core.trail import Trail, PolyExhaust, PolyBraid


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
        fscl1 = 0.013#0.013
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


def fire_n_smoke_2 (parent, store=None,
                    fpos1=Vec3(0.0, 0.0, 0.0),
                    spos1=Vec3(0.0, 0.0, 2.0),
                    fforfact=1.0,
                    sforfact=1.0,
                    flsfact=1.0,
                    slsfact=1.0,
                    sclfact=1.0,
                    psfact=1.0,
                    emradfact=1.0,
                    emampfact=1.0,
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

    trails = []

    if fpos1 is not None:
        fire1 = Trail(
            parent=parent,
            pos=fpos1, scale1=0.04 * sclfact, scale2=0.06 * sclfact,
            lifespan=2.0 * flsfact, poolsize=int(32 * psfact), force=2.0 * fforfact, alpha=1.0,
            ptype="explosion5-4",
            color=rgba(255, 255, 255, 1.0),
            colorend=rgba(186, 92, 17, 1.0),
            tcol=0.8, additive=False,
            pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
            obpos=fpos1,
            obcolor=(rgba(255, 80, 0, 1.0) * 16), obcolor2=None,
            obradius=30.0 * sclfact, obradius2=10.0, obhalfat=0.6, obpulse=False,
            glowcolor=rgba(255, 255, 255, 1.0),
            emradius=0.08 * emradfact * parent._size_xy,
            emamp=2 * emampfact, emamps=0, ltoff=True, risefact=Vec3(0,0,10),
            absolute=True,
            delay=fdelay1)
        trails.append(fire1)

    fire2 = Trail(
        parent=parent,
        pos=Point3(fx_uniform(0, parent._size_xy * 0.8), fx_uniform(0, parent._size_xy * 0.8), 0),
        scale1=0.01 * sclfact, scale2=0.03 * sclfact,
        lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.95,
        ptype="explosion5-3",
        color=rgba(255, 232, 117, 1.0),
        colorend=rgba(186, 92, 17, 1.0),
        tcol=0.8, additive=False,
        pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        glowcolor=rgba(255, 255, 255, 1.0),
        emradius=1.00 * emradfact,
        emamp=2 * emampfact, emamps=0, ltoff=True, risefact=Vec3(0,0,10),
        absolute=True,
        delay=fdelay2)
    trails.append(fire2)

    fire3 = Trail(
        parent=parent,
        pos=Point3(fx_uniform(0, -parent._size_xy * 0.8), fx_uniform(0, parent._size_xy * 0.8), 0),
        scale1=0.01 * sclfact, scale2=0.02 * sclfact,
        lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.9,
        ptype="explosion5-2",
        color=rgba(255, 255, 41, 1.0),
        colorend=rgba(186, 102, 47, 1.0),
        tcol=0.6, additive=False,
        pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        glowcolor=rgba(255, 255, 255, 1.0),
        emradius=1.20 * emradfact,
        emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        absolute=True,
        delay=fdelay3)
    trails.append(fire3)

    fire4 = Trail(
        parent=parent,
        pos=Point3(fx_uniform(0, -parent._size_xy * 0.8), fx_uniform(0, -parent._size_xy * 0.8), 0),
        scale1=0.01 * sclfact, scale2=0.02 * sclfact,
        lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.95,
        ptype="explosion5-4",
        color=rgba(255, 255, 255, 1.0),
        colorend=rgba(186, 92, 17, 1.0),
        tcol=0.8, additive=False,
        pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        glowcolor=rgba(255, 255, 255, 1.0),
        emradius=1.10 * emradfact,
        emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        absolute=True,
        delay=fdelay4)
    trails.append(fire4)

    fire5 = Trail(
        parent=parent,
        pos=Point3(fx_uniform(0, parent._size_xy * 0.8), fx_uniform(0, -parent._size_xy * 0.8), 0),
        scale1=0.02 * sclfact, scale2=0.03 * sclfact,
        lifespan=1.2 * flsfact, poolsize=int(16 * psfact), force=1.0 * fforfact, alpha=0.9,
        ptype="explosion5-4",
        color=rgba(255, 255, 255, 1.0),
        colorend=rgba(186, 92, 17, 1.0),
        tcol=0.8, additive=False,
        pdir=Vec3(0,0,1), phpr=Vec3(0,0,0),
        glowcolor=rgba(255, 255, 255, 1.0),
        emradius=1.00 * emradfact,
        emamp=2 * emampfact, emamps=1, ltoff=True, risefact=Vec3(0,0,10),
        absolute=True,
        delay=fdelay5)
    trails.append(fire5)

    if spos1 is not None:
        smoke1 = Trail(
            parent=parent,
            pos=spos1, scale1=0.06 * sclfact, scale2=0.18 * sclfact,
            lifespan=3.0 * slsfact, poolsize=int(32 * psfact), force=1.0 * sforfact, alpha=0.6,
            ptype=("smoke1-1", "smoke1-2", "smoke1-3", "smoke1-4"),
            color=rgba(255, 110, 0, 1.0),
            colorend=rgba(32, 32, 32, 1.0),
            tcol=0.6,
            pdir=Vec3(0, 0, 1), phpr=Vec3(0,0,0),
            emradius=0.5 * emradfact * parent._size_xy, emamp=1 * emampfact, emamps=0,
            risefact=Vec3(0,0,10), absolute=True,
            delay=0.0)
        trails.append(smoke1)

    if store is not None:
        store.extend(trails)

    return trails


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


if pycv(py=False, c=True):
    from trail_c import *
