# -*- coding: UTF-8 -*-

from pandac.PandaModules import Vec3, Point3

from src.core.body import Body
from src.core.misc import load_model_lod_chain
from src.core.shader import make_stores_shader
from src.core.transl import *


class DropTank (Body):

    family = "droptank"
    species = "generic"
    longdes = _("generic")
    shortdes = _("G/TAN")
    emptymass = 100.0
    diameter = 0.500
    maxfuel = 1150.0 * 0.8
    modelpath = None
    texture = None
    normalmap = None
    glowmap = None
    glossmap = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()

    def __init__ (self):

        raise StandardError("Drop tanks cannot be created as bodies.")


class Tanker (object):
    """
    Generic external store tanker.
    """

    def __init__ (self, stype, parent, points, fuelfill=1.0):
        """
        Parameters:
        - stype (<Tank>): type of tanks being used
        - parent (Body): the body which mounts the tanker
        - points ([int*]): indices of loaded parent pylons
        - fuelfill (float): relative amount of fill-up (0.0-1.0)
        """

        self.stype = stype
        self.parent = parent
        self.world = parent.world

        self._full_points = points

        self._store_model_report_addition = None
        self._store_model_report_removal = None
        self.points = []
        self.store_models = []
        self._create_stores()

        self.maxfuel = len(self.points) * self.stype.maxfuel
        self.fuel = 0.0
        fuelfill = min(max(fuelfill, 0.0), 1.0)
        self.add_fuel(self.maxfuel * fuelfill)
        # FIXME: This way, fuel is not accounted by tanks.
        # E.g. if a tank were to be dropped, there would be no way
        # to remove appropriate amount of fuel from parant.

        self.alive = True
        task = base.taskMgr.add(self._loop, "tanker-loop")


    def destroy (self):

        if not self.alive:
            return
        self._remove_stores()
        self.alive = False


    def _remove_stores (self):

        # FIXME: Does not track fuel.
        for rind in xrange(len(self.points)):
            smodel = self.store_models.pop()
            smodel.removeNode()
            if self.parent.mass is not None:
                self.parent.mass -= self.stype.emptymass
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
        assert not self.store_models
        self.points = []
        self.rounds = 0


    def _create_stores (self):

        self._remove_stores()

        # FIXME: Does not track fuel.
        shader = make_stores_shader(self.world,
                                    normal=bool(self.stype.normalmap),
                                    glow=bool(self.stype.glowmap),
                                    gloss=bool(self.stype.glossmap))
        self.points = list(self._full_points)
        self.store_models = []
        for pind in self.points:
            ppos, phpr = self.parent.pylons[pind][:2]
            ret = load_model_lod_chain(
                self.world.vfov, self.stype.modelpath,
                texture=self.stype.texture, normalmap=self.stype.normalmap,
                glowmap=self.stype.glowmap, glossmap=self.stype.glossmap,
                shadowmap=self.world.shadow_texture,
                scale=self.stype.modelscale)
            lnode = ret[0]
            lnode.reparentTo(self.parent.node)
            ppos1 = ppos + Point3(0.0, 0.0, -0.5 * self.stype.diameter)
            lnode.setPos(ppos1 + self.stype.modeloffset)
            lnode.setHpr(phpr + self.stype.modelrot)
            lnode.setShader(shader)
            self.store_models.append(lnode)
            if self._store_model_report_addition:
                self._store_model_report_addition(lnode)
            if self.parent.mass is not None:
                self.parent.mass += self.stype.emptymass


    def set_store_model_report_functions (self, add_func, rem_func):

        self._store_model_report_addition = add_func
        self._store_model_report_removal = rem_func


    def _loop (self, task):

        if not self.alive:
            return task.done

        return task.cont


    def add_fuel (self, dfuel):

        rfuel = 0.0
        if dfuel > 0.0:
            if self.fuel + dfuel > self.maxfuel:
                rfuel = (self.fuel + dfuel) - self.maxfuel
        else:
            if self.fuel + dfuel < 0.0:
                rfuel = self.fuel + dfuel
        dfuel -= rfuel
        self.fuel += dfuel
        self.parent.fuel += dfuel
        if self.parent.mass is not None:
            self.parent.mass += dfuel
        return rfuel


