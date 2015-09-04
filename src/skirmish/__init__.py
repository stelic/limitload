# -*- coding: UTF-8 -*-

from pandac.PandaModules import *

from src.core import *
from src.blocks import *


def setup_world (zc, mc, gc,
                 terraintype, skytype,
                 playercntl,
                 cumulusdens=1.0, cirrusdens=2.0, stratusdens=1.0,
                 cloudseed=0,
                 alliances=None,
                 actionmusic="limitload-action.ogg",
                 cruisingmusic=None,
                 shotdownmusic="podmosk.ogg",
                 victorymusic="pobeda.ogg", victoryvolume=1.0,
                 failuremusic=None, failurevolume=1.0,
                 actmusvol=0.5, pauseactmus=False,
                 fadein=1.0):

    zc.world = setup_world_1(
        terraintype=terraintype, skytype=skytype,
        latitude=mc.mission.zone_clat_clon(mc.zone)[0],
        longitude=mc.mission.zone_clat_clon(mc.zone)[1],
        cumulusdens=cumulusdens, cirrusdens=cirrusdens,
        stratusdens=stratusdens, cloudseed=cloudseed,
        actionmusic=actionmusic,
        cruisingmusic=cruisingmusic,
        shotdownmusic=shotdownmusic,
        victorymusic=victorymusic, victoryvolume=victoryvolume,
        failuremusic=failuremusic, failurevolume=failurevolume,
        actmusvol=actmusvol,
        pauseactmus=pauseactmus,
        alliances=alliances, alliedall=["", "civilian"],
        playercntl=playercntl, wstate=False,
        game=gc.game, mission=mc.mission,
        fadein=fadein)

    zc.action_music = zc.world.action_music
    zc.terrain = zc.world.terrains[0]


create_player = create_player_1
