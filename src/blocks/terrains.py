# -*- coding: UTF-8 -*-

from math import radians

from pandac.PandaModules import Vec3, Vec4, Point3

from src.core.clouds import Clouds
from src.core.misc import rgba, clampn
from src.core.sky import Sky, Dome, Sun, Moon, Stars, Fog
from src.core.sound import ActionMusic
from src.core.terrain import Terrain
from src.core.terrain import CutSpec, BlendSpec, LayerSpec, SpanSpec
from src.core.world import World


def setup_world_1 (terraintype, skytype,
                   latitude, longitude,
                   cumulusdens=1.0, cirrusdens=2.0, stratusdens=0.0,
                   cloudseed=0,
                   actionmusic=None, cruisingmusic=None, shotdownmusic=None,
                   victorymusic=None, victoryvolume=1.0,
                   failuremusic=None, failurevolume=1.0,
                   bossmusic=None, bossvolume=1.0,
                   actmusvol=0.5, pauseactmus=False,
                   alliances=None, alliedall=None,
                   fixdt=None, randseed=None,
                   playercntl=2, wstate=False, traces=False,
                   game=None, mission=None,
                   fadein=1.0):

    world = World(game=game, mission=mission,
                  fixdt=fixdt, randseed=randseed)
    if wstate:
        hw = base.aspect_ratio
        world.show_state_info(pos=Point3(hw - 0.05, 0, 0.95), anchor="tr")
    world.player_control_level = playercntl
    world.show_traces = traces
    if fadein is not None:
        world.fade_in(fadein)

    visradius = 80000
    sunblend = (34.0, 1e6, 1e6)
    moonblend = (28.0,)

    sky = create_sky_1(world=world,
                       skytype=skytype,
                       latitude=latitude,
                       longitude=longitude,
                       visradius=visradius,
                       sunblend=sunblend)

    terrain = create_terrain_1(world=world,
                               terraintype=terraintype,
                               visradius=visradius,
                               cumulusdens=cumulusdens,
                               cirrusdens=cirrusdens,
                               stratusdens=stratusdens,
                               cloudseed=cloudseed,
                               sunblend=sunblend,
                               moonblend=moonblend)

    if actionmusic:
        attackedpath = "audio/music/%s" % actionmusic
    else:
        attackedpath = None
    if cruisingmusic:
        cruisingpath = "audio/music/%s" % cruisingmusic
    else:
        cruisingpath = None
    if shotdownmusic:
        shotdownpath = "audio/music/%s" % shotdownmusic
    else:
        shotdownpath = None
    if victorymusic:
        victorypath = "audio/music/%s" % victorymusic
    else:
        victorypath = None
    if failuremusic:
        failurepath = "audio/music/%s" % failuremusic
    else:
        failurepath = None
    if bossmusic:
        bosspath = "audio/music/%s" % bossmusic
    else:
        bosspath = None
    if any((cruisingpath, attackedpath, shotdownpath, victorypath, failurepath, bosspath)):
        action_music = ActionMusic(
            world=world,
            volume=actmusvol,
            cruisingpath=cruisingpath,
            attackedpath=attackedpath,
            shotdownpath=shotdownpath,
            victorypath=victorypath, victoryvolume=victoryvolume,
            failurepath=failurepath, failurevolume=failurevolume,
            bosspath=bosspath, bossvolume=bossvolume)
        world.action_music = action_music
        if pauseactmus:
            action_music.pause()

    if alliedall:
        world.set_allied_to_all(alliedall)
    for alliance in (alliances or []):
        world.make_alliance(alliance)

    return world


def create_terrain_1 (world, terraintype, visradius,
                      cumulusdens, cirrusdens, stratusdens, cloudseed,
                      sunblend, moonblend):

    # Common parameters, can be overridden per terrain below.
    sizex = 320000
    sizey = 320000
    celldensity = 1.0
    ltuvstretch = 20
    spreaduv = False
    minheight = None
    maxheight = None
    pntlit = 4
    waterseatex = ("water-1.png", "water-1l.png", "water-1ll.png", 32)
    waterseamaps = ("_gray42.png", "water-nm2.png", "water-nm1.png", "water-nm2.png", Vec4(0,0,0,0.1), 32, 128)#32, 80)
    waterlaketex = ("water-2l.png", "water-2l.png", "water-2ll.png", 64)
    #waterlakemaps = ("_gray126.png", None, "water-nm1.png", "water-nm2.png", Vec4(0,0,0,0.1), 1, 112)
    waterlakemaps = ("_gray126.png", None, "water-lake-nm1.png", "water-lake-nm2.png", Vec4(0,0,0,0.1), 1, 128)
    stratusmap = None
    cumulusmap = None
    cirrusmap = None
    stratusglowmap = None #"clouds_0_0_0_0d1_gw.png"
    cumulusglowmap = None #"clouds_0_0_0_0d1_gw.png"
    cirrusglowmap = None #"clouds_0_0_0_0d1_gw.png"

    #00
    if terraintype == "00-flat0":
        heightmap = "00-flat0.png"
        tilediv = None
        groundmask = None
        groundblend = (
            None,
            None,
            None,
            None,
        )
        watermap = "00-flat-water.png"
        watermask = "00-flat0.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004)
        waterlaketex = None
        waterlakemaps = None
        waterlakeparams = None
        celldensity = 1.0/16
        stratusmap = "00-flat0-clouds-strs.png"
        cumulusmap = "00-flat0-clouds-cmls.png"
        cirrusmap = "00-flat0-clouds-crrs.png"

    # elif terraintype == "00-maze":
         # hmapfile = "00-maze-land.png"
         # wmaskfile = None
         # cmaskfile = None
         # groundtex = groundtex or "russia-siberia-01-1.png"
         # lowgroundtex = lowgroundtex or "russia-siberia-01-1.png"
         # watertex = watertex or None
         # citytex = citytex or None
         # celldensity = 1.0
         # minheight = 0
         # maxheight = 2000

    elif terraintype == "00-zangbo":
        sizex = 180000
        sizey = 180000
        celldensity = 1.0/4
        heightmap = "00-zangbo-land.png"
        tilediv = (3, 3)
        groundmask = None
        groundblend = (
            ["global",
             ("zangbo-test/zangbo-dl.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-dc.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-dr.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-ml.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-mc.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-mr.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-ul.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-uc.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             ("zangbo-test/zangbo-ur.png", None, "zangbo-test/_zangbo-nm.png", "zangbo-test/_zangbo-gw.png", "zangbo-test/_zangbo-gw.png"),
             320, 6000, 2000, 1.0, 1.0,
            ],
            None,
            None,
            None,
        )
        watermap = "00-zangbo-water.png"
        watermask = "00-zangbo-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = ("water-1.png", "water-1l.png", "water-2ll.png", 64)
        waterlakemaps = ("_gray126.png", None, "water-lake-nm1.png", "water-lake-nm2.png", Vec4(0,0,0,0.1), 1, 128)
        waterlakeparams = (0.0002,)
        cirrusmap = "00-flat0-clouds-crrs.png"

    elif terraintype == "00-iraq":
        heightmap = "02-iraq-land.png"
        tilediv = (3, 3)
        groundmask = "02-iraq-landmask.png"
        groundblend = (
            ["global",
             ("02-iraq/_texture-d1.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-d2.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-d3.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-m1.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-m2.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-m3.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-u1.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-u2.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             ("02-iraq/_texture-u3.png", None, "02-iraq/__texture-nm.png", "02-iraq/__texture-gw.png", "02-iraq/__texture-gw.png"),
             320, 6000, 2000, 1.0, 1.0,
            ],
            None,
            None,
            None,
        )
        watermap = "02-iraq-water.png"
        watermask = "02-iraq-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "02-iraq-clouds-cmls.png"
        cirrusmap = "02-iraq-clouds-crrs.png"

    elif terraintype == "00-angola":        
        heightmap = "14-angola-land.png"
        tilediv = (3, 3)
        groundmask = "14-angola-landmask1.png",
        groundblend = (
            ["global",
             ("14-angola/_texture-d1.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-d2.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-d3.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-m1.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-m2.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-m3.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-u1.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-u2.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             ("14-angola/_texture-u3.png", None, "14-angola/__texture-nm.png", "14-angola/__texture-gw.png", "14-angola/__texture-gw.png"),
             320, 6000, 2000, 1.0, 1.0,
            ],
            None,
            None,
            [("africa-luanda.png", None, "africa-luanda-1a-gw.png"), ("asphalt-01.png", None, "africa-luanda-1a-gw.png")],
        )
        watermap = "14-angola-water.png"
        watermask = "14-angola-watermask.png"
        waterseatex = ("water-1.png", "water-1l.png", "water-1ll.png", 32)
        waterseamaps = ("_gray42.png", "water-nm2.png", "water-nm1.png", "water-nm2.png", rgba(0, 0, 0, 0.1), 32, 64)
        waterseaparams = (0.0004,)
        waterlaketex = ("water-2l.png", "water-2l.png", "water-2ll.png", 64)
        waterlakemaps = ("_gray126.png", None, "water-lake-nm1.png", "water-lake-nm2.png", Vec4(0,0,0,0.1), 1, 128)
        waterlakeparams = (0.0003,)
        stratusmap = "14-angola-clouds-strs.png"
        #cumulusmap = "14-angola-clouds-cmls.png"
        cirrusmap = "14-angola-clouds-crrs.png"
    #01
    elif terraintype == "01-taymyr":
        heightmap = "01-taymyr-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-01-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "01-taymyr-water.png"
        watermask = "01-taymyr-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0004,)
        cumulusmap = "01-taymyr-clouds-cmls.png"
        cirrusmap = "01-taymyr-clouds-crrs.png"
    #02
    elif terraintype == "02-iraq":
        heightmap = "02-iraq-land.png"
        tilediv = None
        groundmask = "02-iraq-landmask.png"
        groundblend = (
            [("middle-east-01-1.png", None, Vec4(0,0,0,0.1)), (None, "middle-east-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "02-iraq-water.png"
        watermask = "02-iraq-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "02-iraq-clouds-cmls.png"
        cirrusmap = "02-iraq-clouds-crrs.png"
    #03
    elif terraintype == "03-iran1":
        heightmap = "03-iran1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("middle-east-03-1.png", None, Vec4(0,0,0,0.1)), (None, "middle-east-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "03-iran1-water.png"
        watermask = "03-iran1-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)

    elif terraintype == "03-iran2":
        heightmap = "03-iran2-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("middle-east-03-1.png", None, Vec4(0,0,0,0.1)), (None, "middle-east-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "03-iran2-water.png"
        watermask = "03-iran2-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cirrusmap = "03-iran2-clouds-crrs.png"
    #04
    elif terraintype == "04-russia1":
        heightmap = "04-russia1-land.png"
        tilediv = None
        groundmask = "04-russia1-landmask.png",
        groundblend = (
            [("russia-europe-01-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-europe-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            ["russia-moscow.png", "asphalt-01.png"],
        )
        watermap = "04-russia1-water.png"
        watermask = "04-russia1-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
        stratusmap = "04-russia1-clouds-strs.png"
        cumulusmap = "04-russia1-clouds-cmls.png"
        cirrusmap = "04-russia1-clouds-crrs.png"

    elif terraintype == "04-russia2":
        heightmap = "04-russia2-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-europe-02-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-europe-02-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "04-russia2-water.png"
        watermask = "04-russia2-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
        cumulusmap = "04-russia2-clouds-cmls.png"
        cirrusmap = "04-russia2-clouds-crrs.png"
    #05
    elif terraintype == "05-siberia1":
        heightmap = "05-siberia1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-01-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "05-siberia1-water.png"
        watermask = "05-siberia1-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia1-clouds-cmls.png"
        cirrusmap = "05-siberia1-clouds-crrs.png"

    elif terraintype == "05-siberia2":
        heightmap = "05-siberia2-land.png"
        tilediv = None
        groundmask = "05-siberia2-landmask.png",
        groundblend = (
            [("russia-siberia-02-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-02-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            ["russia-norilsk.png", "asphalt-01.png"],
        )
        watermap = "05-siberia2-water.png"
        watermask = "05-siberia2-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia2-clouds-cmls.png"
        cirrusmap = "05-siberia2-clouds-crrs.png"

    elif terraintype == "05-siberia3":
        heightmap = "05-siberia3-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-03-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "05-siberia3-water.png"
        watermask = "05-siberia3-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia3-clouds-cmls.png"
        cirrusmap = "05-siberia3-clouds-crrs.png"

    elif terraintype == "05-siberia4":
        heightmap = "05-siberia4-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-05-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-05-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "05-siberia4-water.png"
        watermask = "05-siberia4-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia4-clouds-cmls.png"
        cirrusmap = "05-siberia4-clouds-crrs.png"

    elif terraintype == "05-siberia5":
        heightmap = "05-siberia5-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-05-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-05-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "05-siberia5-water.png"
        watermask = "05-siberia5-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia5-clouds-cmls.png"
        cirrusmap = "05-siberia5-clouds-crrs.png"

    elif terraintype == "05-siberia6":
        heightmap = "05-siberia6-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("russia-siberia-05-1.png", None, Vec4(0,0,0,0.1)), (None, "russia-siberia-05-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "05-siberia6-water.png"
        watermask = "05-siberia6-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cumulusmap = "05-siberia6-clouds-cmls.png"
        cirrusmap = "05-siberia6-clouds-crrs.png"
    #06
    elif terraintype == "06-cuba1":
        heightmap = "06-cuba1-land.png"
        tilediv = None
        groundmask = "06-cuba1-landmask.png",
        groundblend = (
            [("cuba-01-1.png", None, Vec4(0,0,0,0.1)), (None, "cuba-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            [("cuba-havana-1.png", None, "cuba-havana-gw.png"), ("asphalt-01.png", None, "cuba-havana-gw.png")],
        )
        watermap = "06-cuba1-water.png"
        watermask = "06-cuba1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = None
        waterlakemaps = None
        waterlakeparams = None
        cirrusmap = "06-cuba1-clouds-crrs.png"

    elif terraintype == "06-cuba2":
        heightmap = "06-cuba2-land.png"
        tilediv = None
        groundmask = "06-cuba2-landmask.png",
        groundblend = (
            [("cuba-01-1.png", None, Vec4(0,0,0,0.1)), (None, "cuba-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            [("cuba-03-1.png", None, Vec4(0,0,0,0.1)), (None, "cuba-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
        )
        watermap = "06-cuba2-water.png"
        watermask = "06-cuba2-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = None
        waterlakemaps = None
        waterlakeparams = None
    #07
    elif terraintype == "07-bahamas":
        heightmap = "07-bahamas-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("bahamas-01-1.png", None, Vec4(0,0,0,0.1)), (None, "bahamas-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "07-bahamas-water.png"
        watermask = "07-bahamas-watermask.png",
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
    #08
    elif terraintype == "08-borderland1":
        heightmap = "08-borderland1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("kutch-01-1.png", None, Vec4(0,0,0,0.1)), (None, "kutch-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "08-borderland1-water.png"
        watermask = "08-borderland1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)

    elif terraintype == "08-borderland2":
        heightmap = "08-borderland2-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("india-01-1.png", None, Vec4(0,0,0,0.1)), (None, "india-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "08-borderland2-water.png"
        watermask = "08-borderland2-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)

    elif terraintype == "08-borderland3":
        heightmap = "08-borderland3-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("middle-east-03-1.png", None, Vec4(0,0,0,0.1)), (None, "middle-east-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "08-borderland3-water.png"
        watermask = "08-borderland3-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
    #09
    elif terraintype == "09-india1":
        heightmap = "09-india1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("india-01-1.png", None, Vec4(0,0,0,0.1)), (None, "india-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "09-india1-water.png"
        watermask = "09-india1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
    #10
    elif terraintype == "10-pakistan1":
        heightmap = "10-pakistan1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("pakistan-01-1.png", None, Vec4(0,0,0,0.1)), (None, "pakistan-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "10-pakistan1-water.png"
        watermask = "10-pakistan1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0004,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
    #11
    elif terraintype == "11-afghanistan1":
        heightmap = "11-afghanistan1-land.png"
        tilediv = None
        groundmask = "11-afghanistan1-landmask.png",
        groundblend = (
            [("middle-east-03-1.png", None, Vec4(0,0,0,0.1)), (None, "middle-east-03-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "11-afghanistan1-water.png"
        watermask = "11-afghanistan1-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0002,)
        cirrusmap = "11-afghanistan1-clouds-crrs.png"
    #12
    elif terraintype == "12-europe1":
        heightmap = "12-europe1-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("europe-01-1.png", None, Vec4(0,0,0,0.1)), (None, "europe-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "12-europe1-water.png"
        watermask = "12-europe1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0005,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)

    elif terraintype == "12-europe2":
        heightmap = "12-europe2-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("europe-01-1.png", None, Vec4(0,0,0,0.1)), (None, "europe-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "12-europe2-water.png"
        watermask = "12-europe2-watermask.png"
        waterseatex = None
        waterseamaps = None
        waterseaparams = None
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
    #13
    elif terraintype == "13-korea1":
        heightmap = "13-korea1-land.png"
        tilediv = None
        groundmask = "13-korea1-landmask.png"
        groundblend = (
            [("korea-01-1.png", None, Vec4(0,0,0,0.1)), (None, "korea-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            [("russia-moscow.png", "russia-moscow-nm.png"), ("asphalt-01.png", "_normal.png")],
        )
        watermap = "13-korea1-water.png"
        watermask = "13-korea1-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0005,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
        cumulusmap = "13-korea1-clouds-cmls.png"
        cirrusmap = "13-korea1-clouds-crrs.png"

    elif terraintype == "13-korea2":
        heightmap = "13-korea2-land.png"
        tilediv = None
        groundmask = None
        groundblend = (
            [("korea-01-1.png", None, Vec4(0,0,0,0.1)), (None, "korea-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            None,
            None,
        )
        watermap = "13-korea2-water.png"
        watermask = "13-korea2-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0005,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
    #14
    elif terraintype == "14-angola":
        heightmap = "14-angola-land.png"
        tilediv = None
        groundmask = "14-angola-landmask.png",
        groundblend = (
            [("africa-02-1.png", None, Vec4(0,0,0,0.1)), (None, "africa-02-1-nm.png", Vec4(0,0,0,0.1))],
            [("africa-01-1.png", None, Vec4(0,0,0,0.1)), (None, "africa-01-1-nm.png", Vec4(0,0,0,0.1))],
            None,
            [("africa-luanda-1.png", None, "africa-luanda-1a-gw.png"), ("asphalt-01.png", None, "africa-luanda-1a-gw.png")],
        )
        watermap = "14-angola-water.png"
        watermask = "14-angola-watermask.png"
        waterseatex = ("water-1.png", "water-1l.png", "water-1ll.png", 32)
        waterseamaps = ("_gray42.png", "water-nm2.png", "water-nm1.png", "water-nm2.png", rgba(0, 0, 0, 0.1), 32, 64)
        waterseaparams = (0.0004,)
        waterlaketex = ("water-1l.png", "water-1l.png", "water-2ll.png", 64)
        waterlakemaps = ("_gray126.png", None, "water-lake-nm1.png", "water-lake-nm2.png", Vec4(0,0,0,0.1), 1, 128)
        waterlakeparams = (0.0003,)
        stratusmap = "14-angola-clouds-strs.png"
        #cumulusmap = "14-angola-clouds-cmls.png"
        cirrusmap = "14-angola-clouds-crrs.png"
    #99
    elif terraintype == "99-vietnam":
        heightmap = "99-vietnam-land.png"
        tilediv = (3, 3)
        groundmask = "99-vietnam-landmask.png"
        groundblend = (
            ["global",
             ("99-vietnam/_texture-ll.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-cl.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-rl.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-lm.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-cm.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-rm.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-lu.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-cu.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             ("99-vietnam/_texture-ru.png", None, "99-vietnam/__texture-nm.png", "99-vietnam/__texture-gw.png", "99-vietnam/__texture-gw.png"),
             320, 6000, 2000, 1.0, 1.0,
            ],
            None,
            None,
            ["vietnam-city.png"],
        )
        watermap = "99-vietnam-water.png"
        watermask = "99-vietnam-watermask.png"
        waterseatex = waterseatex
        waterseamaps = waterseamaps
        waterseaparams = (0.0005,)
        waterlaketex = waterlaketex
        waterlakemaps = waterlakemaps
        waterlakeparams = (0.0003,)
        cirrusmap = "99-vietnam-clouds-crrs.png"

    else:
        raise StandardError("Unknown terrain type '%s'." % terraintype)

    ret = assemble_terrain_cuts_1(
        groundblend=groundblend, groundmask=groundmask,
        watermap=watermap, watermask=watermask,
        waterseatex=waterseatex, waterseamaps=waterseamaps,
        waterseaparams=waterseaparams,
        waterlaketex=waterlaketex, waterlakemaps=waterlakemaps,
        waterlakeparams=waterlakeparams,
        tilediv=tilediv)
    cuts, tiledivx, tiledivy = ret
    terrain = Terrain(world=world, name=terraintype,
                      sizex=sizex, sizey=sizey, visradius=visradius,
                      heightmap=("images/terrain/heightmaps/%s" % heightmap),
                      minheight=minheight, maxheight=maxheight,
                      celldensity=celldensity,
                      tiledivx=tiledivx, tiledivy=tiledivy,
                      cuts=cuts,
                      pntlit=pntlit, sunblend=sunblend)
    world.terrains.append(terrain)

    cloudtex = "images/sky/clouds_tex.png"
    if cumulusmap and cumulusdens > 0.0:
        cumulusmap = "images/sky/cloudmaps/%s" % cumulusmap
        if cumulusglowmap:
            cumulusglowmap = "images/sky/%s" % cumulusglowmap
        cumulus = Clouds(world=world,
                         sizex=sizex, sizey=sizey, visradius=visradius,
                         altitude=(2000, 4000), cloudwidth=(2000, 4500),
                         cloudheight1=(-100, -50), cloudheight2=(400, 800),
                         quaddens=30e-9, quadsize=(300, 600),
                         texture=cloudtex, glowmap=cumulusglowmap,
                         texuvparts=[(0.00, 0.00, 0.25, 0.25),
                                     (0.25, 0.00, 0.25, 0.25),
                                     (0.50, 0.00, 0.25, 0.25),
                                     (0.75, 0.00, 0.25, 0.25),
                                     (0.50, 0.25, 0.25, 0.25),
                                     (0.75, 0.25, 0.25, 0.25)],
                         cloudshape=0, cloudmap=cumulusmap,
                         mingray=0, maxgray=255, clouddens=cumulusdens,
                         wtilesizex=320000, wtilesizey=320000,
                         vsortbase=2, vsortdivs=0,
                         maxnumquads=100000, randseed=cloudseed,
                         sunblend=sunblend, moonblend=moonblend,
                         name=(terraintype + "-clouds-cumulus"))
        # cumulus.node.analyze()
    if stratusmap and stratusdens > 0.0:
        stratusmap = "images/sky/cloudmaps/%s" % stratusmap
        if stratusglowmap:
            stratusglowmap = "images/sky/%s" % stratusglowmap
        stratus = Clouds(world=world,
                         sizex=sizex, sizey=sizey, visradius=visradius,
                         altitude=(1500, 2000), cloudwidth=(2000, 4000),
                         cloudheight1=(-600, -300), cloudheight2=(100, 200),
                         quaddens=30e-9, quadsize=(1000, 2000),
                         texture=cloudtex, glowmap=stratusglowmap,
                         texuvparts=[(0.00, 0.75, 0.25, 0.25),
                                     (0.25, 0.75, 0.25, 0.25),
                                     (0.50, 0.75, 0.25, 0.25)],
                         cloudshape=1, cloudmap=stratusmap,
                         mingray=0, maxgray=255, clouddens=stratusdens,
                         wtilesizex=320000, wtilesizey=320000,
                         vsortbase=2, vsortdivs=0,
                         maxnumquads=100000, randseed=cloudseed,
                         sunblend=sunblend, moonblend=moonblend,
                         name=(terraintype + "-clouds-stratus"))
        # stratus.node.analyze()
    if cirrusmap and cirrusdens > 0.0:
        cirrusmap = "images/sky/cloudmaps/%s" % cirrusmap
        if cirrusglowmap:
            cirrusglowmap = "images/sky/%s" % cirrusglowmap
        cirrus = Clouds(world=world,
                        sizex=sizex, sizey=sizey, visradius=visradius,
                        altitude=(9000, 10000), cloudwidth=(10000, 20000),
                        cloudheight1=(-100, -50), cloudheight2=(50, 100),
                        quaddens=0.5e-9, quadsize=(3000, 5000),
                        texture=cloudtex, glowmap=cirrusglowmap,
                        texuvparts=[(0.00, 0.50, 0.25, 0.25),
                                    (0.25, 0.50, 0.25, 0.25),
                                    (0.50, 0.50, 0.25, 0.25),
                                    (0.75, 0.50, 0.25, 0.25),
                                    (0.00, 0.25, 0.25, 0.25),
                                    (0.25, 0.25, 0.25, 0.25)],
                        cloudshape=1, cloudmap=cirrusmap,
                        mingray=0, maxgray=255, clouddens=cirrusdens,
                        #wtilesizex=80000, wtilesizey=80000,
                        #wtilesizex=160000, wtilesizey=160000,
                        wtilesizex=320000, wtilesizey=320000,
                        vsortbase=2, vsortdivs=0,
                        maxnumquads=100000, randseed=cloudseed,
                        sunblend=sunblend, moonblend=moonblend,
                        name=(terraintype + "-clouds-cirrus"))
        # cirrus.node.analyze()

    return terrain


def create_sky_1 (world, skytype, latitude, longitude, visradius, sunblend):

    # Common parameters, can be overridden per sky type below.
    sunhaloscales = [
        2.0, # sunrise
        8.0, # noon
        2.0, # sunset
        1.0, # evening
        1.0, # midnight
        1.0, # dawn
    ]
    moondiskcolor = rgba(255, 255, 220, 1)
    staralphas = [
        0.5, # sunrise
        0.0, # noon
        0.5, # sunset
        0.9, # evening
        1.0, # midnight
        0.5, # dawn
    ]
    ambientsmokefacs = [
        2.0, # sunrise
        6.0, # noon
        3.0, # sunset
        3.0, # evening
        3.0, # midnight
        2.0, # dawn
    ]
    skymoredayhr = 0.0
    skyspeedup = 1.0
    skyexpalpha = 16.0
    skydomealtcolfac = Vec3(-0.50e-4, -0.50e-4, -0.20e-4)
    skyfogaltcolfac = Vec3(-0.00e-4, -0.00e-4, -0.00e-4)

    if skytype == "video":
        shadowblend = 0.2
        suncolors = [
            rgba(180, 134, 135, 1.0), # sunrise
            rgba(234, 236, 255, 1.0), # noon
            rgba(255, 226, 113, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(33, 65, 88, 1.0), # evening
            rgba(26, 52, 70, 1.0), # midnight
            rgba(33, 65, 88, 1.0), # dawn
        ]
        ambientcolors = [
            rgba(24, 24, 24, 1.0), # sunrise
            rgba(34, 34, 34, 1.0), # noon
            rgba(24, 24, 24, 1.0), # sunset
            rgba(14, 14, 14, 1.0), # evening
            rgba(12, 12, 12, 1.0), # midnight
            rgba(14, 14, 14, 1.0), # dawn
        ]
        skycolors = [
            rgba(81, 74, 140, 1.0), # sunrise
            rgba(204, 210, 255, 1.0), # noon
            rgba(102, 105, 127, 1.0), # sunset
            rgba(13, 15, 19, 1.0), # evening
            rgba(9, 10, 13, 1.0), # midnight
            rgba(13, 15, 19, 1.0), # dawn
        ]
        fogcolors = [
            rgba(180, 134, 135, 1.0), # sunrise
            rgba(234, 236, 255, 1.0), # noon
            rgba(231, 203, 102, 1.0), # sunset
            rgba(33, 65, 88, 1.0), # evening
            rgba(26, 52, 70, 1.0), # midnight
            rgba(33, 65, 88, 1.0), # dawn
        ]
    
    elif skytype == "default":
        shadowblend = 0.2
        suncolors = [
            rgba(180, 134, 136, 1.0), # sunrise
            rgba(234, 249, 255, 1.0), # noon
            rgba(255, 226, 112, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(38, 76, 102, 1.0), # evening
            rgba(47, 93, 126, 1.0), # midnight
            rgba(38, 76, 102, 1.0), # dawn
        ]
        ambientcolors = [
            rgba(24, 24, 24, 1.0), # sunrise
            rgba(34, 34, 34, 1.0), # noon
            rgba(24, 24, 24, 1.0), # sunset
            rgba(14, 14, 14, 1.0), # evening
            rgba(8, 8, 8, 1.0), # midnight
            rgba(14, 14, 14, 1.0), # dawn
        ]
        skycolors = [
            rgba(52, 50, 122, 1.0), # sunrise
            rgba(112, 178, 255, 1.0), # noon
            rgba(31, 58, 96, 1.0), # sunset
            rgba(16, 28, 45, 1.0), # evening
            rgba(4, 8, 12, 1.0), # midnight
            rgba(16, 28, 45, 1.0), # dawn
        ]
        fogcolors = [
            rgba(180, 134, 136, 1.0), # sunrise
            rgba(234, 249, 255, 1.0), # noon
            rgba(255, 226, 112, 1.0), # sunset
            rgba(38, 76, 102, 1.0), # evening
            rgba(47, 93, 126, 1.0), # midnight
            rgba(38, 76, 102, 1.0), # dawn
        ]

    elif skytype == "default2":
        shadowblend = 0.2
        suncolors = [
            rgba(193, 149, 154, 1.0), # sunrise
            rgba(234, 237, 255, 1.0), # noon
            rgba(186, 146, 101, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(14, 11, 18, 1.0), # evening
            rgba(26, 23, 29, 1.0), # midnight
            rgba(14, 11, 18, 1.0), # dawn
        ]
        ambientcolors = [
            rgba(24, 24, 24, 1.0), # sunrise
            rgba(34, 34, 34, 1.0), # noon
            rgba(14, 14, 14, 1.0), # sunset
            rgba(8, 8, 8, 1.0), # evening
            rgba(2, 2, 2, 1.0), # midnight
            rgba(8, 8, 8, 1.0), # dawn
        ]
        skycolors = [
            rgba(67, 65, 114, 1.0), # sunrise
            rgba(168, 170, 236, 1.0), # noon
            rgba(81, 82, 107, 1.0), # sunset
            rgba(12, 10, 13, 1.0), # evening
            rgba(8, 6, 9, 1.0), # midnight
            rgba(12, 10, 13, 1.0), # dawn
        ]
        fogcolors = [
            rgba(193, 149, 154, 1.0), # sunrise
            rgba(234, 237, 255, 1.0), # noon
            rgba(186, 146, 101, 1.0), # sunset
            rgba(14, 11, 18, 1.0), # evening
            rgba(26, 23, 29, 1.0), # midnight
            rgba(14, 11, 18, 1.0), # dawn
        ]

    elif skytype == "siberia":
        shadowblend = 0.3
        suncolors = [
            rgba(200, 141, 144, 1.0), # sunrise
            rgba(243, 250, 255, 1.0), # noon
            rgba(222, 173, 100, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(88, 101, 132, 1.0), # evening
            rgba(117, 141, 172, 1.0), # midnight
            rgba(88, 101, 132, 1.0), # evening
        ]
        ambientcolors = [
            rgba(26, 26, 26, 1.0), # sunrise
            rgba(34, 34, 34, 1.0), # noon
            rgba(18, 18, 18, 1.0), # sunset
            rgba(12, 12, 12, 1.0), # evening
            rgba(8, 8, 8, 1.0), # midnight
            rgba(12, 12, 12, 1.0), # dawn
        ]
        skycolors = [
            rgba(82, 81, 101, 1.0), # sunrise
            rgba(142, 158, 203, 1.0), # noon
            rgba(67, 72, 93, 1.0), # sunset
            rgba(17, 19, 24, 1.0), # evening
            rgba(7, 8, 10, 1.0), # midnight
            rgba(17, 19, 24, 1.0), # dawn
        ]
        fogcolors = [
            rgba(200, 141, 144, 1.0), # sunrise
            rgba(243, 250, 255, 1.0), # noon
            rgba(222, 173, 100, 1.0), # sunset
            rgba(88, 101, 132, 1.0), # evening
            rgba(117, 141, 172, 1.0), # midnight
            rgba(88, 101, 132, 1.0), # evening
        ]

    elif skytype == "tropical":
        shadowblend = 0.1
        suncolors = [
            rgba(255, 181, 208, 1.0), # sunrise
            rgba(184, 226, 255, 1.0), # noon
            rgba(255, 230, 101, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(13, 64, 90, 1.0), # evening
            rgba(28, 141, 196, 1.0), # midnight
            rgba(13, 64, 90, 1.0), # dawn
        ]
        ambientcolors = [
            rgba(38, 38, 38, 1.0), # sunrise
            rgba(44, 44, 44, 1.0), # noon
            rgba(32, 32, 32, 1.0), # sunset
            rgba(24, 24, 24, 1.0), # evening
            rgba(14, 14, 14, 1.0), # midnight
            rgba(24, 24, 24, 1.0), # dawn
        ]
        skycolors = [
            rgba(85, 81, 104, 1.0), # sunrise
            rgba(104, 173, 255, 1.0), # noon
            rgba(47, 64, 81, 1.0), # sunset
            rgba(13, 21, 27, 1.0), # evening
            rgba(6, 10, 12, 1.0), # midnight
            rgba(13, 21, 27, 1.0), # dawn
        ]
        fogcolors = [
            rgba(255, 181, 208, 1.0), # sunrise
            rgba(184, 226, 255, 1.0), # noon
            rgba(255, 230, 101, 1.0), # sunset
            rgba(13, 64, 90, 1.0), # evening
            rgba(28, 141, 196, 1.0), # midnight
            rgba(13, 64, 90, 1.0), # dawn
        ]

    elif skytype == "asia":
        shadowblend = 0.1
        suncolors = [
            rgba(173, 125, 180, 1.0), # sunrise
            rgba(200, 232, 245, 1.0), # noon
            rgba(243, 199, 108, 1.0), # sunset
            rgba(0, 0, 0, 1.0), # evening
            rgba(0, 0, 0, 1.0), # midnight
            rgba(0, 0, 0, 1.0), # dawn
        ]
        mooncolors = [
            rgba(0, 0, 0, 1.0), # sunrise
            rgba(0, 0, 0, 1.0), # noon
            rgba(0, 0, 0, 1.0), # sunset
            rgba(30, 26, 43, 1.0), # evening
            rgba(21, 18, 30, 1.0), # midnight
            rgba(30, 26, 43, 1.0), # dawn
        ]
        ambientcolors = [
            rgba(22, 22, 22, 1.0), # sunrise
            rgba(38, 38, 38, 1.0), # noon
            rgba(28, 28, 28, 1.0), # sunset
            rgba(12, 12, 12, 1.0), # evening
            rgba(4, 4, 4, 1.0), # midnight
            rgba(14, 14, 14, 1.0), # dawn
        ]
        skycolors = [
            rgba(15, 45, 78, 1.0), # sunrise
            rgba(45, 135, 234, 1.0), # noon
            rgba(10, 30, 52, 1.0), # sunset
            rgba(5, 15, 26, 1.0), # evening
            rgba(3, 10, 18, 1.0), # midnight
            rgba(5, 15, 26, 1.0), # dawn
        ]
        fogcolors = [
            rgba(173, 125, 180, 1.0), # sunrise
            rgba(200, 232, 245, 1.0), # noon
            rgba(243, 199, 108, 1.0), # sunset
            rgba(21, 18, 30, 1.0), # evening
            rgba(30, 26, 43, 1.0), # midnight
            rgba(21, 18, 30, 1.0), # dawn
        ]

    else:
        raise StandardError("Unknown sky type '%s'." % skytype)

    dome = Dome(
        world=world, baserad=visradius, height=visradius,
        nbasesegs=128, expalpha=skyexpalpha, sunblend=sunblend)

    # fog = None
    fog = Fog(
        world=world,
        onsetdist=(visradius * 0.5), opaquedist=(visradius * 0.95))
    # fog = Fog(world=world, falloff=0.000025)
    # fog = Fog(world=world, falloff=0.000015)
    # fog = Fog(world=world, falloff=0.00002)

    sunmagfac = 6
    sundiskcolors = [
        clampn(fogcolors[0] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # sunrise
        clampn(fogcolors[1] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # noon
        clampn(fogcolors[2] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # sunset
        clampn(fogcolors[2] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # evening
        clampn(fogcolors[2] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # midnight
        clampn(fogcolors[5] * 1.5, Vec4(), Vec4(1, 1, 1, 1)), # dawn
    ]
    sunbrightcolors = [
        sundiskcolors[0] * 0.9, # sunrise
        sundiskcolors[1] * 1.0, # noon
        sundiskcolors[2] * 0.9, # sunset
        sundiskcolors[3] * 0.2, # evening
        sundiskcolors[4] * 0.0, # midnight
        sundiskcolors[5] * 0.4, # dawn
    ]
    sun = Sun(world=world,
              radius=(visradius * 0.98),
              size=(radians(0.53) * sunmagfac),
              texpath="images/sky/sun.png",
              halosize=(radians(0.53) * sunmagfac),
              halotexpath="images/sky/halo1.png")

    moonmagfac = 5
    moon = Moon(world=world,
                radius=(visradius * 0.98),
                size=(radians(0.53) * moonmagfac),
                texpath="images/sky/moon.png",
                halosize=(radians(0.63) * moonmagfac),
                halotexpath="images/sky/halo1.png",
                color=moondiskcolor)

    stars = Stars(world=world, datapath="images/sky/stars.dat",
                  radius=(visradius * 0.99),
                  mag1=-1.5, mag2=6.0,
                  size1=radians(0.10),
                  size2=radians(0.05),
                  alpha1=1.0, alpha2=0.0,
                  poly1=8, poly2=4,
                  reffov=45,
                  name="stars")

    sky = Sky(world=world,
              latitude=latitude, longitude=longitude,
              moredayhr=skymoredayhr,
              dome=dome, fog=fog, sun=sun, moon=moon, stars=stars,
              suncolors=suncolors, mooncolors=mooncolors,
              ambientcolors=ambientcolors, ambientsmokefacs=ambientsmokefacs,
              skycolors=skycolors, fogcolors=fogcolors,
              sundiskcolors=sundiskcolors, sunbrightcolors=sunbrightcolors,
              sunhaloscales=sunhaloscales, staralphas=staralphas,
              domealtcolfac=skydomealtcolfac, fogaltcolfac=skyfogaltcolfac,
              shadowblend=shadowblend)

    return sky


def assemble_terrain_cuts_1 (groundblend,
                             groundmask=None,
                             watermap=None, watermask=None,
                             waterseatex=None, waterseamaps=None,
                             waterseaparams=None,
                             waterlaketex=None, waterlakemaps=None,
                             waterlakeparams=None,
                             tilediv=None):

    uvscale_high_ground = [16.0, 16.0, 16.0, 16.0]
    uvscale_low_ground = [320.0, 320.0, 320.0, 160.0]
    altitude_high_ground = [6000.0, 6000.0, 6000.0, 2000.0]
    altitude_low_ground = [0.0, 0.0, 0.0, 1000.0]
    radius_high_ground = 20000.0
    radius_low_ground = 10000.0
    alpha_high_ground = [1.0, 1.0, 1.0, 1.0]
    alpha_low_ground = [0.8, 0.8, 0.8, 1.0]
    blend_ind_to_name = ["black", "red", "green", "blue", "alpha"]
    blend_night_glow_ground = [None, None, None, "cityglowfac"]
    normal_blend_mode_ground = "cover"
    gloss_blend_mode_ground = "cover"
    altitude_high_water = 12000.0
    altitude_low_water = 0.0
    radius_high_water = 40000.0
    radius_low_water = 25000.0
    flow_dir_water = (0, 90)
    normal_blend_mode_water = "add"
    gloss_blend_mode_water = "multiply"
    if not tilediv:
        tilediv = (None, None)
    tiledivx, tiledivy = tilediv
    def is_tl (ls):
        return isinstance(ls, (tuple, list))
    def at_ij (ls, i, j, dv=None):
        return (ls[i][j]
                if is_tl(ls) and i < len(ls) and is_tl(ls[i]) and j < len(ls[i])
                else (ls[i]
                      if is_tl(ls) and i < len(ls) and not is_tl(ls[i]) and j == 0
                      else (ls
                            if not is_tl(ls) and i == 0 and j == 0
                            else dv)))
    def assemble_ground_layers (il, ls):
        if ls[0] == "global":
            assert tiledivx == tiledivy # due to single uvscale
            numtex = tiledivx * tiledivy
            drx = 1.0 / tiledivx
            dry = 1.0 / tiledivy
            layers = []
            for name, il in [("high", 0), ("low", 1)]:
                spans = []
                for i in range(tiledivx):
                    for j in range(tiledivy):
                        sls = ls[1 + j * tiledivx + i]
                        spans += [
                            SpanSpec(
                                texture=("images/terrain/%s" % at_ij(sls, 0, 0)
                                         if at_ij(sls, 0, 0) else None),
                                normalmap=("images/terrain/%s" % at_ij(sls, il + 1, 0)
                                           if at_ij(sls, il + 1, 0) else None),
                                glowmap=("images/terrain/%s" % at_ij(sls, il + 3, 0)
                                         if at_ij(sls, il + 3, 0) else None),
                                extents=((i * drx, j * dry),
                                         ((i + 1) * drx, (j + 1) * dry)),
                                relative=True,
                                tilemode=1,
                            )]
                if il == 0:
                    layer = LayerSpec(
                        name=name,
                        uvscale=tiledivx,
                        spans=spans,
                    )
                else:
                    layer = LayerSpec(
                        name=name,
                        altitude=(at_ij(ls, 1 + numtex + 1, 0, altitude_high_ground[il]),
                                  at_ij(ls, 1 + numtex + 2, 0, altitude_low_ground[il])),
                        radius=(radius_high_ground, radius_low_ground),
                        alpha=(at_ij(ls, 1 + numtex + 3, 0, alpha_high_ground[il]),
                               at_ij(ls, 1 + numtex + 4, 0, alpha_low_ground[il])),
                        uvscale=tiledivx,
                        nmuvscale=at_ij(ls, 1 + numtex + 0, 0, uvscale_low_ground[il]),
                        spans=spans,
                    )
                layers.append(layer)
        else:
            layers = [
                LayerSpec(
                    name="high",
                    uvscale=at_ij(ls, 0, 3, uvscale_high_ground[il]),
                    spans=[
                        SpanSpec(
                            name="main",
                            texture=("images/terrain/%s" % at_ij(ls, 0, 0)
                                     if at_ij(ls, 0, 0) else None),
                            normalmap=("images/terrain/%s" % at_ij(ls, 0, 1)
                                       if at_ij(ls, 0, 1) else None),
                            glowmap=("images/terrain/%s" % at_ij(ls, 0, 2)
                                     if isinstance(at_ij(ls, 0, 2), basestring)
                                     else (at_ij(ls, 0, 2)
                                           if isinstance(at_ij(ls, 0, 2), Vec4)
                                           else None)),
                        ),
                    ],
                )]
            if len(ls) > 1:
                layers += [
                    LayerSpec(
                        name="low",
                        altitude=(at_ij(ls, 1, 4, altitude_high_ground[il]),
                                  at_ij(ls, 1, 5, altitude_low_ground[il])),
                        radius=(radius_high_ground, radius_low_ground),
                        alpha=(alpha_high_ground[il], alpha_low_ground[il]),
                        uvscale=at_ij(ls, 1, 3, uvscale_low_ground[il]),
                        spans=[
                            SpanSpec(
                                name="main",
                                texture=("images/terrain/%s" % at_ij(ls, 1, 0)
                                         if at_ij(ls, 1, 0) else None),
                                normalmap=("images/terrain/%s" % at_ij(ls, 1, 1)
                                           if at_ij(ls, 1, 1) else None),
                                glowmap=("images/terrain/%s" % at_ij(ls, 1, 2)
                                         if isinstance(at_ij(ls, 1, 2), basestring)
                                         else (at_ij(ls, 1, 2)
                                               if isinstance(at_ij(ls, 1, 2), Vec4)
                                               else None)),
                            ),
                        ],
                    )]
        return layers
    def assemble_water_layers (il, ls):
        watertex, watermaps, waterparams = ls
        layers = []
        uvsc1 = at_ij(watertex, 3, 0, 1.0)
        for nsf, it, ibm, uvsc in (
            ("high", 0, None, 1.0), ("low1", 1, 2, 1.0), ("low2", 2, 3, uvsc1)):
            txfile = at_ij(watertex, it, 0)
            if txfile:
                layers += [
                    LayerSpec(
                        name=("tex-%s" % nsf),
                        uvscale=uvsc,
                        blendmaskindex=ibm,
                        spans=[
                            SpanSpec(
                                name="main",
                                texture=("images/terrain/%s" % txfile),
                            ),
                        ],
                    ),
                ]
        gsfile = at_ij(watermaps, 0, 0)
        nmfile = at_ij(watermaps, 1, 0)
        gwfile = at_ij(watermaps, 4, 0)
        if nmfile or gsfile or gwfile:
            layers += [
                LayerSpec(
                    name="map-high",
                    uvscale=at_ij(watermaps, 5, 0, 1.0),
                    spans=[
                        SpanSpec(
                            name="main",
                            normalmap=("images/terrain/%s" % nmfile
                                       if nmfile else None),
                            glowmap=("images/terrain/%s" % gwfile
                                     if isinstance(gwfile, basestring)
                                     else (gwfile
                                           if isinstance(gwfile, Vec4)
                                           else None)),
                            glossmap=("images/terrain/%s" % gsfile
                                      if gsfile else None),
                        ),
                    ],
                ),
            ]
        for nsf, it, ifl in (("low1", 2, 0), ("low2", 3, 1)):
            nmfile = at_ij(watermaps, it, 0)
            if nmfile:
                layers += [
                    LayerSpec(
                        name=("map-%s" % nsf),
                        altitude=(at_ij(waterparams, 2, 0, altitude_high_water),
                                at_ij(waterparams, 3, 0, altitude_low_water)),
                        radius=(at_ij(waterparams, 4, 0, radius_high_water),
                                at_ij(waterparams, 5, 0, radius_low_water)),
                        uvscale=at_ij(watermaps, 6, 0, 1.0),
                        normalflow=(at_ij(waterparams, 1, 0, flow_dir_water[ifl])
                                    if ifl > 0 else flow_dir_water[ifl],
                                    at_ij(waterparams, 0, 0, 0.0)),
                        glossflow=(at_ij(waterparams, 1, 0, flow_dir_water[ifl])
                                   if ifl > 0 else flow_dir_water[ifl],
                                   at_ij(waterparams, 0, 0, 0.0)),
                        spans=[
                            SpanSpec(
                                name="main",
                                normalmap=("images/terrain/%s" % nmfile),
                            ),
                        ],
                    ),
            ]
        return layers
    cuts = [
        CutSpec(
            name="ground",
            blendmask=("images/terrain/heightmaps/%s" % groundmask
                       if groundmask else None),
            blends=[(
                BlendSpec(
                    name=blend_ind_to_name[ib],
                    normalblendmode=normal_blend_mode_ground,
                    glossblendmode=gloss_blend_mode_ground,
                    nightglowfacn=blend_night_glow_ground[ib],
                    layers=assemble_ground_layers(ib, ls),
                )
                if ls else None)
                for ib, ls in enumerate(groundblend)
            ]),
    ]
    if watermap:
        cuts += [
            CutSpec(
                name="water",
                cutmask=("images/terrain/heightmaps/%s" % watermap),
                blendmask=("images/terrain/heightmaps/%s" % watermask
                           if watermask else None),
                blends=[(
                    BlendSpec(
                        name=blend_ind_to_name[ib],
                        normalblendmode=normal_blend_mode_water,
                        glossblendmode=gloss_blend_mode_water,
                        layers=assemble_water_layers(ib, ls),
                    )
                    if ls[0] else None)
                    for ib, ls in enumerate((
                        (waterseatex, waterseamaps, waterseaparams),
                        (waterlaketex, waterlakemaps, waterlakeparams),
                    ))
                ]),
        ]
    return cuts, tiledivx, tiledivy


