# -*- coding: UTF-8 -*-

from pandac.PandaModules import *

from src.core import *
from src.blocks import *
from src.skirmish import *

_, p_, n_, pn_ = make_tr_calls_skirmish(__file__)


mission_shortdes = p_("mission name", "Incoming")

mission_longdes = p_("mission description", """
A true dogfight mission. The enemy will be coming in waves, one after another. You never know how many or which type of aircraft is going to hunt you next. To win, you must survive and destroy each wave.

Primary objectives:
- Shoot down all enemy planes.

Bonus objectives:
- Do not fire any missiles.

""").strip()

mission_difficulty = MISSION_DIFFICULTY.HARD

mission_type = MISSION_TYPE.DOGFIGHT


def mission_start (gc):

    mission = Mission(gc)
    mission.add_init(loadf=init_cache)
    mission.add_zone("zero", clat=34.89, clon=43.36, #clat=43.34, clon=31.04,
                     enterf=zone_zero_enter,
                     exitf=zone_zero_exit,
                     loopf=zone_zero_loop)

    mc = mission.context
    mc.player_fuelfill = 0.8
    mc.player_ammo_cannons = [450]
    mc.player_ammo_launchers = [(None, 3),(R27, 2), (R73, 2), (R60, 2)]
    mc.player_mfd_mode = "targid"

    mission.switch_zone("zero")

    mc.world_day_time = hrmin_to_sec(*choice(
            [(6, 30)] * 3 +
            [(12, 30)] * 10 +
            [(17, 30)] * 3 +
            [(23, 30)] * 1))

    return mission


def init_cache (mc, gc):

    cache_bodies(["mig29", "mig29fd", "f14", "f15", "f16"])


def zone_zero_enter (zc, mc, gc):

    # setup_world(zc, mc, gc,
                # terraintype="00-flat0",
                # skytype="default",
                # stratusdens=0.0,
                # cumulusdens=0.0,
                # cirrusdens=2.0,
                # playercntl=2,
                # shotdownmusic=None)
    setup_world(zc, mc, gc,
                terraintype="00-iraq",
                skytype="default2",
                stratusdens=0.0,
                cumulusdens=0.0,
                cirrusdens=2.0,
                playercntl=2,
                shotdownmusic=None)

    zc.player = create_player(mc=mc, world=zc.world,
                              acsel="mig29fd",
                              name="red",
                              side="taymyr",
                              texture="models/aircraft/mig29/mig29_tex.png",
                              pos=Point3(0, 0, 6000),
                              hpr=Vec3(180, 0, 0),
                              speed=220)

    zc.enemyplanegroup = []


def zone_zero_loop (zc, mc, gc):

    zc.world.chaser = zc.world.player.chaser

    if gc.quick_exit:
        zc.world.player_control_level = 1
        yield zc.world, 1.0
        zc.world.destroy()
        mc.mission.end(exitf=False, state="quit")

    yield zc.world, 1.0

    zc.player.show_message("notification", "left", _("Incoming enemy planes!"), duration=1.0)
    zc.player.show_message("notification", "left", _("Good luck!"), duration=4.0)

    yield zc.world, 2.0

    zc.world.player_control_level = 0
    zc.world.action_music.set_context("attacked")

    yield zc.world, 2.0

    waves = 4
    while True:
        if waves > 0 and all(ac.shotdown for ac in zc.enemyplanegroup) and zc.player and zc.player.ac.alive:
            pos = pos_from_horiz(zc.player.ac, Point3(choice([-4000, 2000, 0, 2000, 4000]), choice([-10000, -7000, 7000, 10000]), randrange(4000, 7000)), absz=True)
            hpr = hpr_from_horiz(zc.player.ac, Vec3(choice([0, 180]), 0, 0))
            d3 = choice([0, 1, 2])
            if d3 == 0:
                enemyac = F16(world=zc.world, name="blue", side="usaf",
                              texture="models/aircraft/f16/f16_tex.png",
                              fuelfill=0.50,
                              pos=pos,
                              hpr=hpr,
                              speed=200,
                              lnammo=[(None, 6), (Aim9, 2)])
                zc.enemyplanegroup.append(enemyac)
                d2 = choice([0, 1])
                if d2 == 1:
                    enemyac1 = F16(world=zc.world, name="blue1", side="usaf",
                                   texture="models/aircraft/f16/f16_tex.png",
                                   fuelfill=0.50,
                                   speed=200,
                                   lnammo=[(None, 8)])
                    formation_pair(enemyac, enemyac1, compact=choice([2.0, 3.0, 4.0]), jumpto=True)
                    zc.enemyplanegroup.append(enemyac1)
            elif d3 == 1:
                enemyac = F15(world=zc.world, name="blue", side="usaf",
                              texture="models/aircraft/f15/f15_tex.png",
                              fuelfill=0.50,
                              pos=pos,
                              hpr=hpr,
                              speed=200,
                              lnammo=[(Aim9, 4), (Aim7, 2)])
                zc.enemyplanegroup.append(enemyac)
            elif d3 == 2:
                enemyac = F14(world=zc.world, name="blue", side="usaf",
                              texture="models/aircraft/f14/f14_tex.png",
                              fuelfill=0.50,
                              pos=pos,
                              hpr=hpr,
                              speed=200,
                              lnammo=[(None, 4), (Aim9, 2), (None, 2)])
                zc.enemyplanegroup.append(enemyac)
                d100 = randrange(100)
                if d100 > 80:
                    enemyac1 = F14(world=zc.world, name="blue1", side="usaf",
                                   texture="models/aircraft/f14/f14_tex.png",
                                   fuelfill=0.50,
                                   speed=200,
                                   lnammo=[(None, 6), (Aim9, 2)])
                    formation_pair(enemyac, enemyac1, compact=choice([2.0, 3.0, 4.0]), jumpto=True)
                    zc.enemyplanegroup.append(enemyac1)
            for ac in zc.enemyplanegroup: ac.set_ap(target=zc.player.ac)
            waves = waves - 1
        elif waves <= 0 and all(ac.shotdown for ac in zc.enemyplanegroup) and zc.player and zc.player.ac.alive:
            zc.world.action_music.set_context("cruising")
            break
        yield zc.world, 1.0

    yield zc.world, 6.0

    if len(mc.mission.player_releases(family="rocket")) == 0:
        mc.mission_bonus = True

    mc.mission_completed = True
    zc.world.action_music.set_context("victory")
    zc.player.show_message("notification", "left", _("All enemy planes destroyed."), duration=1.0)
    if mc.mission_bonus:
        zc.player.show_message("notification", "left", _("No missile was fired."), duration=1.0)
        zc.player.show_message("notification", "left", _("Excellent work."), duration=4.0)
    else:
        zc.player.show_message("notification", "left", _("Good work."), duration=4.0)

    yield zc.world, 5.0

    mc.mission.end()


def zone_zero_exit (zc, mc, gc):

    if zc.player and zc.player.alive:
        store_player_state(mc, zc.player)
        yield zc.world, zone_flyout(zc) + 3.0

    zc.world.destroy()


# ========================================
# Background.

mission_skipconfirm = True

