# -*- coding: UTF-8 -*-

from math import pow, log

from pandac.PandaModules import Vec3, Point3
from pandac.PandaModules import AmbientLight, PointLight

from src.core.misc import rgba


class AutoPointLight (object):

    _count = 0

    def __init__ (self, parent, color, radius, halfat=None,
                  subnode=None, litnode=None, pos=Point3(),
                  selfmanaged=False, name=None):

        self.parent = parent

        if halfat is None:
            halfat = 0.5

        if name is None:
            name = "aplight%d" % AutoPointLight._count
        self.name = name

        self._pntlt = PointLight(self.name)
        pnode = subnode if subnode is not None else self.parent.node
        self.node = pnode.attachNewNode(self._pntlt)
        self.node.setPos(pos)
        self.litnode = litnode if litnode is not None else self.parent.node
        self.litnode.setLight(self.node)

        self.update(color, radius, halfat, pos)

        self.alive = True
        AutoPointLight._count += 1
        if selfmanaged:
            base.taskMgr.add(self._loop, "autopointlight-loop")
        else:
            self.parent.world.register_plight(self)


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        #if not self.litnode.isEmpty():
            #self.litnode.clearLight(self.node)
        self.node.removeNode()


    def update (self, color=None, radius=None, halfat=None, pos=None):

        if color is not None:
            self._pntlt.setColor(color)
            self.color = color
            self._colamp = Vec3(color[0], color[1], color[2]).length()
        if radius is not None or halfat is not None:
            if radius is None:
                radius = self.radius
            if halfat is None:
                halfat = self.halfat
            assert 0.0 < halfat < 1.0
            radpow = log(0.5) / log(halfat)
            self._pntlt.setAttenuation(Vec3(radius, radpow, 0.0))
            self.radius = radius
            self.halfat = halfat
            self._radpow = radpow
        if pos is not None:
            self.node.setPos(pos)


    def strength (self, dist):

        if self._colamp > 0.0:
            att = 1.0
            if dist > 0.0:
                att -= pow(min(dist / self.radius, 1.0), self._radpow)
            return self._colamp * att
        else:
            return 0.0


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done
        return task.cont


class PointOverbright (object):

    _count = 0

    def __init__ (self, parent, color, radius, halfat=None,
                  subnode=None, pos=Point3(), name=None):

        self.parent = parent

        if halfat is None:
            halfat = 0.5

        if name is None:
            name = "poverbright%d" % PointOverbright._count
        self.name = name

        self._pntlt = PointLight(self.name)
        pnode = subnode if subnode is not None else self.parent.node
        self.node = pnode.attachNewNode(self._pntlt)
        self.node.setPos(pos)

        self.update(color, radius, halfat, pos)

        self.alive = True
        PointOverbright._count += 1
        base.taskMgr.add(self._loop, "poverbright-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def update (self, color=None, radius=None, halfat=None, pos=None):

        if color is not None:
            self._pntlt.setColor(color)
            self.color = color
            self._colamp = Vec3(color[0], color[1], color[2]).length()
        if radius is not None or halfat is not None:
            if radius is None:
                radius = self.radius
            if halfat is None:
                halfat = self.halfat
            assert 0.0 < halfat < 1.0
            radpow = log(0.5) / log(halfat)
            self._pntlt.setAttenuation(Vec3(radius, radpow, 0.0))
            self.radius = radius
            self.halfat = halfat
            self._radpow = radpow
        if pos is not None:
            self.node.setPos(pos)


    def strength (self, dist):

        if self._colamp > 0.0:
            att = 1.0
            if dist > 0.0:
                att -= pow(min(dist / self.radius, 1.0), self._radpow)
            return self._colamp * att
        else:
            return 0.0


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done
        return task.cont


