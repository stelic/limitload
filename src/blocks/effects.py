# -*- coding: UTF-8 -*-

from pandac.PandaModules import VBase2, VBase2D, Vec3, Point3

from src.core.misc import rgba
from src.core.trail import Trail


def flare_smoke (parent, pos, rise, pdir=Vec3(0,-1,0), light=False, delay=0.0):

    if isinstance(pos, (VBase2, VBase2D)):
        if parent is not None:
            z = -parent.world.otr_altitude(parent.pos(offset=Point3(pos[0], pos[1], 0.0))) + rise
        else:
            z = parent.world.elevation(pos) + rise
        pos = Point3(pos[0], pos[1], z)

    if light:
        ltpos = Vec3(pos[0], pos[1], pos[2]+5) + pdir * 0.5
        ltradius = 20.0
        ltradius2 = 5.0
        ltpulse = 0.0001
    else:
        ltpos = None
        ltradius = None
        ltradius2 = None
        ltpulse = None

    Trail(parent=parent,
          pos=pos,
          scale1=0.0025,
          scale2=0.0250,
          lifespan=1.6,
          poolsize=32,
          force=8.0,
          alpha=1.0,
          color=rgba(255, 125, 10, 1.0),
          ptype="smoke1-1",
          pdir=pdir,
          phpr=Vec3(0, 0, 0),
          ltpos=ltpos,
          ltcolor=(rgba(255, 160, 90, 1) * 10),
          ltcolor2=None,
          ltradius=ltradius,
          ltradius2=ltradius2,
          ltpulse=ltpulse,
          littersize=1,
          emradius=0.3,
          emamp=0.5,
          emamps=0.25,
          birthrate=None,
          risefact=Vec3(0, 0, 10),
          ltoff=True,
          colorend=rgba(150, 10, 5, 1.0),
          tcol=0.5,
          absolute=True,
          delay=delay)


