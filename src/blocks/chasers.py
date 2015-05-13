# -*- coding: UTF-8 -*-

from pandac.PandaModules import Point3

from src.core.chaser import TrackChaser
from src.core.misc import pos_from


def FpChaser (plane):

    # FIXME: For every plane point= should be different, as it aims the cockpit.
    return TrackChaser(world=plane.world, point=Point3(0, 6, 1),
                       relto=plane, rotrel=True,
                       atref=Vec3(0, 1, 0), upref=Vec3(0, 1, 0),
                       lookrel=True,
                       drift=("instlag", 0.0, 0.25))


def RvChaser (plane):

    return TrackChaser(world=plane.world,
                       point=Point3(0, -40, 10),
                       relto=plane, rotrel=True,
                       atref=plane, upref=plane,
                       drift=("instlag", 0.0, 0.25))


def FvChaser (plane):

    return TrackChaser(world=plane.world,
                       point=Point3(0, 25, 3),
                       relto=plane, rotrel=True,
                       atref=plane, upref=plane,
                       drift=("instlag", 0.0, 0.25))


def FlyByChaser (plane):

    return TrackChaser(world=plane.world,
                       point=pos_from(plane, Point3(-15, 400, 0)),
                       relto=None, rotrel=False,
                       atref=plane, upref=Vec3(0,0,1),
                       drift=("instlag", 0.0, 0.25))


def TargetChaser (plane, target):

    return TrackChaser(world=plane.world,
                       point=Point3(0, -20, 3),
                       relto=plane, rotrel=True,
                       atref=target, upref=Vec3(0,0,1),
                       drift=("instlag", 0.0, 0.25))


# def FreeChaser(world, pos):

    # return TrackChaser(world, point=pos, drift="instlag-mid")


