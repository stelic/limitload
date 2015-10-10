# -*- coding: UTF-8 -*-

from pandac.PandaModules import *

from src.core import *
from src.blocks import *
from src.skirmish import *

_, p_, n_, pn_ = make_tr_calls_skirmish(__file__)


mission_shortdes = p_("mission name", "Avalanche")

mission_longdes = p_("mission description", """
Ground attack mission. A group of enemy vehicles is spotted in the area. It consists mostly of lightly armored IFVs, but some MBTs are reported too. To complete the task you must destroy the whole group. While vehicles themselves are defenseless against attack from air, keep in mind that enemy infantry, armed with Stingers, is scattered through surrounding hills.

Primary objectives:
- Destroy all enemy vehicles.

Bonus objectives:
- None.

""").strip()

mission_difficulty = MISSION_DIFFICULTY.EASY

mission_type = MISSION_TYPE.ATTACK


def mission_start (gc):

    mission = Mission(gc)
    mission.add_init(loadf=init_cache)
    mission.add_zone("zero", clat=34.89, clon=43.36,
                     enterf=zone_zero_enter,
                     exitf=zone_zero_exit,
                     loopf=zone_zero_loop)

    mc = mission.context
    mc.player_fuelfill = 0.8
    mc.player_ammo_cannons = [450]
    mc.player_ammo_launchers = [(None, 3),(Kh25, 2), (B8m1, 4)]
    mc.player_mfd_mode = "targid"

    mission.switch_zone("zero")

    mc.world_day_time = hrmin_to_sec(*choice(
            [(16, 35)] * 6 +
            [(2, 10)] * 1))

    return mission


def init_cache (mc, gc):

    cache_bodies(["mig29", "mig29fd", "abrams", "bradley"])


def zone_zero_enter (zc, mc, gc):

    setup_world(zc, mc, gc,
                terraintype="00-iraq",
                skytype="default2",
                stratusdens=0.0,
                cumulusdens=0.0,
                cirrusdens=1.2,
                playercntl=2,
                shotdownmusic=None)

    zc.player = create_player(mc=mc, world=zc.world,
                              acsel="mig29fd",
                              name="red",
                              side="taymyr",
                              texture="models/aircraft/mig29/mig29_tex.png",
                              pos=Point3(56000, 24500, 4196),
                              hpr=Vec3(100, 0, 0),
                              speed=200)

    zc.wp1pos = Point2(56000, 23500)

    #Target vehicle group
    zc.target1 = Abrams(world=zc.world, name="harmor1", side="merc",
                        texture="models/vehicles/abrams/abrams_tex.png",
                        pos=(zc.wp1pos + Point2(500, 450)),
                        hpr=Vec3(310, 0, 0),
                        speed=0.0)
    zc.target2 = Abrams(world=zc.world, name="harmor2", side="merc",
                        texture="models/vehicles/abrams/abrams_tex.png",
                        pos=pos_from_horiz(zc.target1, Point2(100, -850)),
                        hpr=Vec3(220, 0, 0),
                        speed=0.0)
    zc.target3 = Bradley(world=zc.world, name="larmor1", side="merc",
                         texture="models/vehicles/bradley/bradley_tex.png",
                         pos=(zc.wp1pos + Point2(-400, 400)),
                         hpr=Vec3(270, 0, 0),
                         speed=0.0)
    zc.target4 = Bradley(world=zc.world, name="larmor2", side="merc",
                         texture="models/vehicles/bradley/bradley_tex.png",
                         pos=pos_from_horiz(zc.target3, Point2(-450, -400)),
                         hpr=Vec3(295, 0, 0),
                         speed=0.0)
    zc.target5 = Bradley(world=zc.world, name="larmor3", side="merc",
                         texture="models/vehicles/bradley/bradley_tex.png",
                         pos=pos_from_horiz(zc.target3, Point2(-300, -800)),
                         hpr=Vec3(180, 0, 0),
                         speed=0.0)
    zc.target6 = Bradley(world=zc.world, name="larmor4", side="merc",
                         texture="models/vehicles/bradley/bradley_tex.png",
                         pos=pos_from_horiz(zc.target3, Point2(200, -1000)),
                         hpr=Vec3(130, 0, 0),
                         speed=0.0)
    zc.enemyvehiclegroup = [zc.target1, zc.target2, zc.target3, zc.target4, zc.target5, zc.target6]

    #SAM carpet
    zc.infantry = SamCarpet(zc.world, mtype=Stinger, mside="merc",
                            targsides=["taymyr"],
                            avgfiretime=25.0, skiptime=15.0, maxrad=None, maxalt=None, rounds=32,
                            carpetpos=zc.wp1pos, carpetradius=2500)

    #Waypoint data
    zc.player.add_waypoint(name="wp1", longdes=_("waypoint 1"), shortdes=_("WP1"),
                           pos=zc.wp1pos, radius=4000, height=500)


def zone_zero_loop (zc, mc, gc):

    zc.world.chaser = zc.world.player.chaser

    yield zc.world, 1.0

    zc.player.show_message("notification", "left", _("Destroy enemy armor below."), duration=1.0)
    zc.player.show_message("notification", "left", _("Watch out for Stingers!"), duration=4.0)

    yield zc.world, 2.0

    zc.world.player_control_level = 0
    zc.world.action_music.set_context("attacked")

    yield zc.world, 2.0

    while True:
        if all(vhc.shotdown for vhc in zc.enemyvehiclegroup) and zc.player and zc.player.ac.alive:
            zc.infantry.destroy()
            zc.world.action_music.set_context("cruising")
            break
        yield zc.world, 1.0

    yield zc.world, 6.0

    mc.mission_completed = True
    zc.world.action_music.set_context("victory")
    zc.player.show_message("notification", "left", _("Enemy armor group destroyed."), duration=1.0)
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

