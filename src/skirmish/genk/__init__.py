# -*- coding: UTF-8 -*-

from math import *

from pandac.PandaModules import *

from src.core import *
from src.blocks import *

_, p_, n_, pn_ = make_tr_calls_skirmish(__file__)


def check_after_mission (mc, gc):

    mobj = []
    if mc.mission_completed:
        mobj.append(_("Mission objectives completed."))
    else:
        mobj.append(_("Mission failed."))
    if mc.mission_bonus:
        mobj.append(_("Bonus objective completed."))

    govr = False

    return mobj, govr


