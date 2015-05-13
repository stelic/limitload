# -*- coding: UTF-8 -*-

from pandac.PandaModules import Vec3, Point3

from src.core.body import Body
from src.core.misc import load_model_lod_chain
from src.core.misc import uniform
from src.core.shader import make_stores_shader
from src.core.transl import *


class Jammer (object):
    """
    Generic jammer.
    """

    def __init__ (self, ptype, parent, points):
        """
        Parameters:
        - ptype (<JammingPod>): type of pods being attached
        - parent (Body): the body which mounts the dropper
        - points ([int*]): indices of loaded parent pylons
        """

        self.ptype = ptype
        self.parent = parent
        self.world = parent.world
        self._pnode = parent.node
        self._full_points = points

        self.alive = True

        self._store_model_report_addition = None
        self._store_model_report_removal = None
        self.points = []
        self.store_models = []
        self._create_stores()

        task = base.taskMgr.add(self._loop, "jammer-loop")


    def destroy (self):

        if not self.alive:
            return
        self._remove_stores()
        self.alive = False


    def _remove_stores (self):

        for rind in xrange(len(self.points)):
            smodel = self.store_models.pop()
            smodel.removeNode()
            if self.parent.mass is not None:
                self.parent.mass -= self.ptype.mass
            if self._store_model_report_removal:
                self._store_model_report_removal(smodel)
        assert not self.store_models
        self.points = []


    def _create_stores (self):

        self._remove_stores()

        shader = make_stores_shader(self.world,
                                    normal=bool(self.ptype.normalmap),
                                    glow=bool(self.ptype.glowmap),
                                    gloss=bool(self.ptype.glossmap))
        self.points = list(self._full_points)
        self.store_models = []
        for pind in self.points:
            ppos, phpr = self.parent.pylons[pind][:2]
            ret = load_model_lod_chain(
                self.world.vfov, self.ptype.modelpath,
                texture=self.ptype.texture, normalmap=self.ptype.normalmap,
                glowmap=self.ptype.glowmap, glossmap=self.ptype.glossmap,
                shadowmap=self.world.shadow_texture,
                scale=self.ptype.modelscale)
            lnode = ret[0]
            lnode.reparentTo(self.parent.node)
            ppos1 = ppos + Point3(0.0, 0.0, -0.5 * self.ptype.diameter)
            lnode.setPos(ppos1 + self.ptype.modeloffset)
            lnode.setHpr(phpr + self.ptype.modelrot)
            lnode.setShader(shader)
            self.store_models.append(lnode)
            if self._store_model_report_addition:
                self._store_model_report_addition(lnode)
            if self.parent.mass is not None:
                self.parent.mass += self.ptype.mass


    def set_store_model_report_functions (self, add_func, rem_func):

        self._store_model_report_addition = add_func
        self._store_model_report_removal = rem_func


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done

        return task.cont


class JammingPod (Body):

    family = "jammer"
    species = "generic"
    longdes = _("generic")
    shortdes = _("G/JAM")
    mass = 500.0
    diameter = 0.500
    jamradius = 1500.0
    shockradius = 50.0
    modelpath = None
    texture = None
    normalmap = None
    glowmap = None
    glossmap = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()

    def __init__ (self):

        raise StandardError("Jammers cannot be created as bodies.")


class JammingCarpet (object):

    _carpets = set()


    def __init__ (self, world, side, carpetpos, carpetradius,
                  jamtime=None, freetime=None):

        self.world = world
        self.side = side
        self.carpetpos = carpetpos
        self.carpetradius = carpetradius

        self._jamtime = jamtime
        self._freetime = freetime
        self._wait_toggle_active = 0.0

        self.active = True

        self.alive = True
        JammingCarpet._carpets.add(self)
        base.taskMgr.add(self._loop, "jamming-carpet-loop")


    def destroy (self):

        if not self.alive:
            return
        JammingCarpet._carpets.remove(self)
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            self.destroy()
            return task.done

        if self._jamtime and self._freetime:
            self._wait_toggle_active -= self.world.dt
            if self._wait_toggle_active <= 0.0:
                if self.active:
                    self._wait_toggle_active = uniform(*self._freetime)
                    self.active = False
                else:
                    self._wait_toggle_active = uniform(*self._jamtime)
                    self.active = True

        return task.cont


    @staticmethod
    def iter_carpets ():

        for carpet in JammingCarpet._carpets:
            yield carpet


