# -*- coding: UTF-8 -*-

from pandac.PandaModules import *

from src.core import *
from src.blocks import *


def setup_background (zc=None, mc=None, gc=None,
                      terraintype="00-flat0", skytype="asia",
                      latitude=None, longitude=None,
                      cumulusdens=1.0, cirrusdens=2.0, stratusdens=0.0,
                      cloudseed=101,
                      pclevel=2, wstate=False, traces=False,
                      fixdt=None, randseed=None,
                      fadein=1.0):

    if latitude is None:
        if mc is not None:
            latitude = mc.mission.zone_clat_clon(mc.zone)[0]
        else:
            latitude = 50.0
    if longitude is None:
        if mc is not None:
            longitude = mc.mission.zone_clat_clon(mc.zone)[1]
        else:
            longitude = 100.0

    world = setup_world_1(terraintype=terraintype, skytype=skytype,
                          latitude=latitude, longitude=longitude,
                          cumulusdens=cumulusdens, cirrusdens=cirrusdens,
                          stratusdens=stratusdens, cloudseed=cloudseed,
                          playercntl=pclevel, wstate=wstate, traces=traces,
                          fixdt=fixdt, randseed=randseed,
                          fadein=fadein)

    if zc is not None:
        zc.world = world

    return world


def equip_player (ac, nomflash=False):

    cpitmfspec = []
    if ac.species in ("mig29", "mig29fd"):
        if not nomflash:
            # MUZZLE FLASH Long
            cpitmfspec = [("longhalf", # mshape
                           1.0, # mscale
                           Point3(-0.7, 4.6, 0.85), # mpos
                           Vec3(0.0, 0.0, 0.0), # mphpr
                           Point3(-0.7, 4.6, 0.85), # mposlt
                           # Point3(-0.7, 5.0, 0.65), # mpos
                           # Vec3(0.0, 0.0, 0.0), # mphpr
                           # Point3(-0.7, 5.0, 0.65), # mposlt
                          )]
            # MUZZLE FLASH Square
            # cpitmfspec = [("square", # mshape
                           # 1.0, # mscale
                           # Point3(-0.7, 5.0, 0.1), # mpos
                           # Vec3(0.0, 0.0, 0.0), # mphpr
                           # Point3(-0.7, 5.0, 0.1), # mposlt
                          # )]
            # MUZZLE FLASH Spec
            # cpitmfspec = [("spec", # mshape
                           # 1.0, # mscale
                           # Point3(-0.7, 5.0, 0.1), # mpos
                           # Vec3(0.0, 0.0, 0.0), # mphpr
                           # Point3(-0.7, 5.0, 0.1), # mposlt
                          # )]
        player = Player(ac=ac,
                        headpos=Point3(0, 4.900, 1.185), # down angle 11 [deg]
                        dimpos=Point3(0, -37, 5),
                        rvpos=Point3(0, -40, 10),
                        cpitpos=Point3(-0.0078, 0.0, 0.0004),
                        cpitmfspec=cpitmfspec,
                        cpitdownto=Point3(0.0, 5.020, 1.078))
    else:
        raise StandardError("Cannot equip player to '%s'." % ac.species)
    return player


def put_model (world, modelpath, pos, scale=1.0, hpr=Vec3(0, 0, 0)):

    model = base.load_model(modelpath)
    model.reparentTo(world.node)
    model.setScale(scale)
    model.setHpr(hpr)
    model.setPos(pos)

    return model


def write_texture_buffers ():

    for iwin in range(base.graphicsEngine.getNumWindows()):
        win = base.graphicsEngine.getWindow(iwin)
        for itex in range(win.countTextures()):
            tex = win.getTexture(itex)
            img = PNMImage()
            tex.store(img)
            img_path = "texbuf-w%02d-t%02d.png" % (iwin, itex)
            img.write(img_path)


def vf (v, d=6):
    return "(%s)" % ", ".join(("%% .%df" % d) % e for e in v)


