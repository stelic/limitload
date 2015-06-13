# -*- coding: UTF-8 -*-

from math import pi, sin

from pandac.PandaModules import Vec3, Point3
from pandac.PandaModules import TransparencyAttrib

from src import pycv
from src.core.body import Body
from src.core.misc import rgba, make_image, unitv
from src.core.misc import fx_choice
from src.core.shader import make_shader
from src.core.trail import PolyTrail


class FlareChaff (Body):

    def __init__ (self, world, pos, vel, refbody=None, vistype=0):

        if refbody:
            self._pos = refbody.pos(offset=pos)
            self._vel = (refbody.vel() +
                         world.node.getRelativeVector(refbody.node, vel))
            self._hpr = Vec3()
        else:
            self._pos = pos
            self._vel = vel
            self._hpr = Vec3()

        if vistype == 0:
            self._size = 2.0
        elif vistype == 1:
            self._size = 3.0
        self._lifespan = 2.0
        self._sdrag = 0.002
        self._pulse_period = 0.2
        self._pulse_size = 0.7
        self._lifetime = 0.0

        self.lifespan = self._lifespan

        mass = 0.05 + 0.20 + 0.15 # service + flare + chaff

        Body.__init__(self,
            world=world,
            family="flarechaff", species="flarechaff",
            hitforce=0.0,
            name="", side="",
            mass=mass,
            pos=self._pos, hpr=self._hpr, vel=self._vel)

        # texture = fx_choice([
            # "images/particles/flare5.png",
            # "images/particles/flare6.png",
            # "images/particles/flare7.png",
        # ])
        if vistype == 0:
            texture = "images/particles/flare3.png"
        elif vistype == 1:
            texture = "images/particles/flare2.png"
        flnode = make_image(texture=texture,
                            size=(self._size, self._size), filtr=False,
                            parent=self.node)
        flnode.setBillboardPointEye(0.0)
        flnode.setTransparency(TransparencyAttrib.MAlpha)
        flnode.setDepthWrite(False)
        shader = make_shader(glow=rgba(255, 255, 255, 1.0))
        flnode.setShader(shader)
        self.world.add_altbin_node(flnode)
        self._flnode = flnode

        rho = self.world.airdens(self._pos[2])
        self._daccv = -0.5 * rho * self._sdrag / mass
        self._acc = Vec3()

        if vistype == 0:
            trail = PolyTrail(parent=self, pos=Point3(),
                              radius0=0.6, radius1=1.2,
                              #radius0=0.4, radius1=0.8,
                              lifespan=(self._lifespan * 0.5),
                              segperiod=0.010, farsegperiod=pycv(py=0.100, c=None),
                              maxpoly=pycv(py=100, c=200), farmaxpoly=pycv(py=100, c=200),
                              randcircle=pycv(py=0.8, c=0.5),
                              #color=rgba(255, 150, 63, 1.0), # Flare 2
                              color=rgba(255, 186, 98, 1.0), # Flare 3
                              #color=rgba(255, 211, 116, 1.0), # Flare 5,6,7
                              #colorend=rgba(130, 126, 123, 1.0),
                              colorend=rgba(130, 104, 85, 1.0),
                              tcol=pycv(py=0.3, c=0.2),
                              texture="images/particles/exhaust06.png",
                              glowmap=rgba(128, 128, 128, 1.0),
                              dirlit=pycv(py=False, c=True))
        elif vistype == 1:
            trail = PolyTrail(parent=self, pos=Point3(),
                              radius0=0.8, radius1=1.6,
                              #radius0=0.5, radius1=1.0,
                              lifespan=(self._lifespan * 0.5),
                              segperiod=0.010, farsegperiod=pycv(py=0.100, c=None),
                              maxpoly=pycv(py=100, c=200), farmaxpoly=pycv(py=100, c=200),
                              randcircle=pycv(py=0.9, c=0.6),
                              color=rgba(255, 166, 94, 1.0), # Flare 2
                              colorend=rgba(130, 91, 39, 1.0),
                              tcol=pycv(py=0.3, c=0.2),
                              texture="images/particles/exhaust06.png",
                              glowmap=rgba(128, 128, 128, 1.0),
                              dirlit=pycv(py=False, c=True))
        else:
            raise StandardError("Unknown decoy visual type %d." % vistype)

        base.taskMgr.add(self._loop, "flarechaff-loop")


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        self._lifetime += dt
        if self._lifetime >= self._lifespan:
            self.destroy()
            return task.done

        if self._pulse_period > 0.0:
            pfac = sin(self.world.time * pi / self._pulse_period) * 0.5 + 0.5
            scale = 1.0 * pfac + self._pulse_size * (1.0 - pfac)
            self._flnode.setScale(scale)

        alpha = abs(1.0 - self._lifetime / self._lifespan)**0.5
        self._flnode.setSa(alpha)

        return task.cont


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos, silent=True)
        if inert:
            return True

        self.destroy()

        return False


    def move (self, dt):

        vel = self._vel
        pos = self._pos

        speed = vel.length()
        vdir = unitv(vel)
        acc = vdir * (self._daccv * speed**2) + self.world.gravacc
        pos += vel * dt
        vel += acc * dt

        self.node.setPos(pos)
        self._pos = pos

        # Needed in base class.
        self._prev_vel = self._vel
        self._vel = vel
        self._acc = acc


    def decay (self):

        dec = abs(self._lifetime / self._lifespan)**4
        return dec


