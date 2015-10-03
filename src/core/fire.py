# -*- coding: UTF-8 -*-

from math import pi, radians, degrees, asin
import os
import sys

from direct.particles.ForceGroup import ForceGroup
from direct.particles.ParticleEffect import ParticleEffect
from pandac.PandaModules import AntialiasAttrib
from pandac.PandaModules import VBase2, VBase2D, Vec3, Vec4, Point3
from pandac.PandaModules import TransparencyAttrib, AmbientLight, NodePath
from pandac.PandaModules import BaseParticleRenderer, BaseParticleEmitter
from pandac.PandaModules import LinearVectorForce
from pandac.PandaModules import Shader, ColorBlendAttrib
from pandac.PandaModules import MeshDrawer, BoundingSphere

from src import pycv, USE_COMPILED
from src.core.light import AutoPointLight
from src.core.misc import rgba, set_texture, bin_view_b2f
from src.core.misc import make_particles, make_quad, make_quad_lattice
from src.core.misc import set_particle_texture_noext
from src.core.misc import texture_frame, SimpleProps
from src.core.misc import HaltonDistrib, hprtovec, unitv
from src.core.misc import fx_uniform, fx_randrange, fx_choice, fx_randvec
from src.core.misc import NumRandom
from src.core.shader import make_shader
from src.core.debris import AirBreakupPart


class MuzzleFlash (object):

    def __init__ (self, parent, pos, hpr, ltpos, rate,
                  shape="long", scale=1.0, subnode=None, manbin=False):

        self.alive = True
        self.world = parent.world

        pnode = subnode if subnode is not None else parent.node
        self.node = pnode.attachNewNode("muzzle-flash")
        self.node.setPos(pos)
        self.node.setHpr(hpr)
        self.node.hide()
        if not manbin:
            parent.world.add_altbin_node(self.node)

        if shape == "long":
            modelpath = "models/weapons/fx_muzzle_flash_long.egg"
            texture = "models/weapons/fx_muzzle_flash_long_tex.png"
            ltradius = 4.0
            lthalfat = 0.1
            minsize = Vec3(0.040, 0.060, 0.040)
            maxsize = Vec3(0.090, 0.110, 0.090)
            minhpr = Vec3(0, 0, -60)
            maxhpr = Vec3(0, 0, 60)
        elif shape == "longhalf":
            modelpath = "models/weapons/fx_muzzle_flash_longhalf.egg"
            texture = "models/weapons/fx_muzzle_flash_long_tex.png"
            ltradius = 5.0
            lthalfat = 0.2
            minsize = Vec3(0.040, 0.060, 0.040)
            maxsize = Vec3(0.090, 0.110, 0.090)
            minhpr = Vec3(0, 0, -60)
            maxhpr = Vec3(0, 0, 60)
        elif shape == "square":
            modelpath = "models/weapons/fx_muzzle_flash_square.egg"
            texture = "models/weapons/fx_muzzle_flash_square_tex.png"
            ltradius = 5.0
            lthalfat = 0.2
            minsize = Vec3(0.050, 0.060, 0.050)
            maxsize = Vec3(0.100, 0.100, 0.100)
            minhpr = Vec3(0, 0, -60)
            maxhpr = Vec3(0, 0, 60)
        # elif shape == "spec":
            # modelpath = "models/weapons/fx_muzzle_flash_spec.egg"
            # texture = "models/weapons/fx_muzzle_flash_long_tex.png"
            # ltradius = 5.0
            # lthalfat = 0.2
            # minsize = Vec3(0.14, 0.12, 0.16)
            # maxsize = Vec3(0.14, 0.12, 0.16)
            # minhpr = Vec3(0, 0, -60)
            # maxhpr = Vec3(0, 0, 60)
        elif shape == "hit":
            modelpath = "models/weapons/fx_hit.egg"
            texture = "models/weapons/fx_hit_tex.png"
            minsize = Vec3(0.05, 0.05, 0.05)
            maxsize = Vec3(0.10, 0.10, 0.10)
            minhpr = Vec3(-180, -90, -180)
            maxhpr = Vec3(180, 90, 180)
        else:
            raise StandardError("Uknown muzzle flash shape '%s'." % shape)

        self._model = base.load_model("data", modelpath)
        self._model.reparentTo(self.node)
        self._model.setScale(1e-5) # not zero, would be singular
        # self._model.setTwoSided(True)
        self._model.setTransparency(TransparencyAttrib.MAlpha)
        self._model.setDepthWrite(False)
        use_glow = True
        if use_glow:
            glowmap = rgba(255,255,255,1.0)
            self._model.setSa(1.0)

            if isinstance(glowmap, Vec4):
                glow = glowmap
                glowmap = None
            else:
                glow = (glowmap is not None)
            shader = make_shader(ambln=parent.world.shdinp.ambln, glow=glow)
        else:
            glowmap = None
            self._model.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
            self._model.setSa(0.5)
            shader = make_shader(selfalpha=True)
        self._model.setShader(shader)

        set_texture(self._model, texture=texture, glowmap=glowmap)

        if ltpos is not None:
            self._lt2_base_color = rgba(255, 225, 161, 1.0) * 4
            self._lt2_base_radius = ltradius
            self._lt2_base_halfat = lthalfat
            self._lt2 = AutoPointLight(
                parent=parent, subnode=subnode, color=self._lt2_base_color,
                radius=(self._lt2_base_radius * scale),
                halfat=(self._lt2_base_halfat * scale),
                pos=ltpos, name="muzzle-flash")
        else:
            self._lt2 = None

        self._rate = rate
        self._minsize = minsize
        self._maxsize = maxsize
        self._minhpr = minhpr
        self._maxhpr = maxhpr
        self._scale = scale

        self.active = False
        self._time = 0.0

        base.taskMgr.add(self._loop, "muzzle-mflash-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self._lt2 is not None:
            self._lt2.destroy()
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        if self.active:
            if self._rate - self._time < 0.05:
                self.node.show()
                if self._lt2 is not None:
                    lt_color = self._lt2_base_color * fx_uniform(0.5, 1.0)
                    self._lt2.update(color=lt_color)
            else:
                self.node.hide()
                if self._lt2 is not None:
                    self._lt2.update(color=(self._lt2_base_color * 0.0))
            self._time -= dt
            if self._time < 0:
                self._time = self._rate
                size = Vec3(fx_uniform(self._minsize[0], self._maxsize[0]),
                            fx_uniform(self._minsize[1], self._maxsize[1]),
                            fx_uniform(self._minsize[2], self._maxsize[2]))
                self._model.setScale(size * self._scale)
                hpr = Vec3(fx_uniform(self._minhpr[0], self._maxhpr[0]),
                           fx_uniform(self._minhpr[1], self._maxhpr[1]),
                           fx_uniform(self._minhpr[2], self._maxhpr[2]))
                self._model.setHpr(hpr)
        else:
            self._time = self._rate
            self.node.hide()
            if self._lt2 is not None:
                self._lt2.update(color=(self._lt2_base_color * 0.0))

        return task.cont


    def update (self, pos=None, hpr=None, ltpos=None, scale=None):

        if pos is not None:
            self.node.setPos(pos)
        if hpr is not None:
            self.node.setHpr(hpr)
        if self._lt2 is not None:
            self._lt2.update(pos=ltpos)
        if scale is not None:
            self._scale = scale
            if self._lt2 is not None:
                self._lt2.update(radius=(self._lt2_base_radius * scale),
                                 halfat=(self._lt2_base_halfat * scale))


class Blast (object):

    def __init__ (self, parent, pos, scale, lifespan, amplitude,
                  alpha, color, ptype,
                  fps=24):

        self.alive = True

        self._parent = parent
        self._pnode = parent.node
        self.world = parent.world

        self._pfx = ParticleEffect()
        self._pfx.setPos(pos)
        #self._pfx.setHpr(Vec3(0, 0, 90))
        #pfx.setScale(1.0)

        p0 = make_particles()
        p0.setPoolSize(16)
        p0.setBirthRate(0.01)
        p0.setLitterSize(16)
        p0.setLitterSpread(0)
        #p0.setSystemLifespan(1.0)
        #p0.setLocalVelocityFlag(1)
        #p0.setSystemGrowsOlderFlag(0)

        p0.setFactory("PointParticleFactory")
        p0.factory.setLifespanBase(lifespan)
        p0.factory.setLifespanSpread(0.0)
        #p0.factory.setMassBase(1.00)
        #p0.factory.setMassSpread(0.00)
        #p0.factory.setTerminalVelocityBase(400.0000)
        #p0.factory.setTerminalVelocitySpread(0.0000)

        p0.setRenderer("SpriteParticleRenderer")
        p0.renderer.setAlphaMode(BaseParticleRenderer.PRALPHAOUT)
        set_particle_texture_noext(p0.renderer, "images/particles/%s" % ptype)
        p0.renderer.setAnimateFramesEnable(True)
        p0.renderer.setAnimateFramesRate(fps)
        p0.renderer.setUserAlpha(alpha)
        p0.renderer.setColor(color)
        p0.renderer.setXScaleFlag(1)
        p0.renderer.setYScaleFlag(1)
        p0.renderer.setInitialXScale(scale)
        p0.renderer.setFinalXScale(scale)
        p0.renderer.setInitialYScale(scale)
        p0.renderer.setFinalYScale(scale)

        p0.setEmitter("SphereVolumeEmitter")
        p0.emitter.setRadius(0.1)
        p0.emitter.setEmissionType(BaseParticleEmitter.ETRADIATE)
        p0.emitter.setAmplitude(amplitude)
        p0.emitter.setAmplitudeSpread(0.2 * amplitude)
        #p0.emitter.setOffsetForce(Vec3(0.0000, 0.0000, 0.0000))
        #p0.emitter.setExplicitLaunchVector(Vec3(1.0000, 0.0000, 0.0000))
        #p0.emitter.setRadiateOrigin(Point3(0.0000, 0.0000, 0.0000))

        #f0 = ForceGroup("vertex")
        #force0 = LinearVectorForce(Vec3(0.0, 0.0, -amplitude * 2))
        #force0.setActive(1)
        #f0.addForce(force0)

        self._rnode = pnode.getParent().attachNewNode("blast-render")
        p0.setRenderParent(self._rnode)
        self._rnode.setDepthWrite(False)
        shader = make_shader(modcol=True)
        self._rnode.setShader(shader)
        self._parent.world.add_altbin_node(self._rnode)

        #self._pfx.addForceGroup(f0)
        self._pfx.addParticles(p0)
        self._pfx.start(self._pnode)

        self._lifespan = lifespan

        task = base.taskMgr.add(self._loop, "blast-loop")
        task.prev_time = 0.0


    def _loop (self, task):

        #binval = bin_view_b2f(self._pfx, self._parent.world.camera)
        #self._rnode.setBin("fixed", binval)

        if self.world.time < self._lifespan:
            return task.cont
        else:
            self.alive = False
            self._pfx.cleanup()
            self._rnode.removeNode()
            return task.done


class Explosion (object):

    def __init__ (self, world, pos,
                  firetex=("explosion6-1", "explosion6-2", "explosion6-3", "explosion6-4"),
                  smoketex=("smoke6-1", "smoke6-2", "smoke6-3", "smoke6-4"),
                  firepart=1, smokepart=1,
                  sizefac=1.0, timefac=1.0, amplfac=1.0,
                  smgray=(30, 45), smred=10, firepeak=(0.4, 0.8),
                  firefps=24, smokefps=24,
                  debrispart=0, debrisheading=(-180, 180),
                  debrispitch=(-90, 90), debristcol=0.0):

        self.world = world

        has_fire = bool(firetex) and firepart > 0
        has_smoke = bool(smoketex) and smokepart > 0

        self.node = world.node.attachNewNode("explosion")
        self.node.setPos(pos)

        self._rnode1 = self.node.attachNewNode("explosion-render-1")
        self._rnode1.setDepthWrite(False)
        self.world.add_altbin_node(self._rnode1)

        self._rnode2 = self.node.attachNewNode("explosion-render-2")
        self._rnode2.setDepthWrite(False)
        self.world.add_altbin_node(self._rnode2)

        if has_fire:
            self._lt1_color_atstart = rgba(255, 255, 0, 1.0) * 1
            self._lt1_radius_atstart = 10.0 * sizefac
            self._lt1_color_atpeak = rgba(255, 255, 0, 1.0) * 10
            self._lt1_radius_atpeak = 100.0 * sizefac
            self._lt1_color_atend = rgba(0, 0, 0, 1.0)
            self._lt1_radius_atend = 10.0 * sizefac
            self._lt1 = AutoPointLight(
                parent=self, color=self._lt1_color_atstart,
                radius=self._lt1_radius_atstart, halfat=0.5,
                litnode=world.node, name="explosion")
        else:
            self._lt1 = None

        if has_fire:
            glowcol1 = rgba(255, 255, 255, 1.0)
            shader1 = make_shader(glow=glowcol1, modcol=True) #, selfalpha=True)
            self._rnode1.setShader(shader1)
            #self._rnode1.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        else:
            shader1 = make_shader(modcol=True)
            self._rnode1.setShader(shader1)

        glowcol2 = rgba(255, 255, 255, 1.0)
        shader2 = make_shader(ambln=self.world.shdinp.ambln, glow=glowcol2,
                              modcol=True)
        self._rnode2.setShader(shader2)

        self._pfxes = []

        # Fire particles.
        if has_fire:
            fstime = 0.05
            max_flspan = 0.0
            for i in range(firepart):
                if firepart > 1:
                    pdir = fx_randvec()
                    fpos = pdir * (2.0 * sizefac)
                else:
                    fpos = Point3()
                frad = 5.6 * sizefac
                fampl = 1.1 * amplfac
                fsc1 = 0.004 * sizefac * 0.25
                fsc2 = fx_uniform(0.04, 0.08) * sizefac * 0.25
                flspan = fx_uniform(0.5, 1.0) * timefac
                fcol1 = rgba(255, 248, 243, 1.0)
                if firepeak[0] < 1.0:
                    fcol2 = rgba(255, 255, 255, 1.0)
                    fcol3 = rgba(112, 62, 23, 1.0)
                    fcol = (fcol1, fcol2, fcol3, firepeak)
                else:
                    fcol = fcol1
                self._start_pfx(
                    enode=self.node, rnode=self._rnode1,
                    pos=fpos, radius=frad, scale1=fsc1, scale2=fsc2,
                    lifespan=flspan, zspin=0.0, zspinvel=0.0,
                    poolsize=8, amplitude=fampl,
                    texpath=firetex, color=fcol,
                    alphamode=BaseParticleRenderer.PRALPHAOUT,
                    starttime=fstime, fps=firefps)
                max_flspan = max(max_flspan, flspan)

            if firepeak[0] < 1.0:
                self._lt1_starttime = fstime
                self._lt1_lifespan = max_flspan
                self._lt1_peakat = 0.05
                self._lt1_peakto = firepeak[0]
            else:
                self._lt1_starttime = fstime
                self._lt1_lifespan = max_flspan
                self._lt1_peakat = 0.05
                self._lt1_peakto = 0.80
        else:
            self._lt1_starttime = 0.0
            self._lt1_lifespan = 0.0
            self._lt1_peakat = 0.0
            self._lt1_peakto = 0.0

        # Smoke particles.
        if has_smoke:
            for i in range(smokepart):
                srad = 5.0 * sizefac
                sampl = 5.0 * amplfac
                ssc1 = 0.006 * sizefac * 0.25 # 0.001
                ssc2 = 0.12 * sizefac * 0.25 # 0.050
                slspan = fx_uniform(4.5, 5.0) * timefac
                sstime = 0.0 * timefac
                sspindir = fx_choice([-1, 1])
                szspin = fx_uniform(0, 0) * sspindir
                szspinvel = 0 * sspindir
                if isinstance(smgray, tuple):
                    c = fx_randrange(smgray[0], smgray[1] + 1)
                else:
                    c = smgray
                if smred <= 0 or c + smred > 255:
                    scolmodred = 0
                else:
                    scolmodred = fx_randrange(smred + 1)
                scol1 = rgba(c + scolmodred, c, c, 0.5)
                smokepeak = (0.2, 0.6)
                if smokepeak[0] < 1.0:
                    scol2 = rgba(c + scolmodred, c, c, 0.5)
                    c3 = c * 0.30
                    scol3 = rgba(c3 + scolmodred, c3, c3, 0.5)
                    scol = (scol1, scol2, scol3, smokepeak)
                else:
                    scol = scol1
                self._start_pfx(
                    enode=self.node, rnode=self._rnode2,
                    pos=Point3(), radius=srad, scale1=ssc1, scale2=ssc2,
                    lifespan=slspan, zspin=szspin, zspinvel=szspinvel,
                    poolsize=11, amplitude=sampl,
                    texpath=smoketex, color=scol,
                    alphamode=BaseParticleRenderer.PRALPHAOUT,
                    starttime=sstime, fps=smokefps)

        # Debris trails.
        if isinstance(debrispart, tuple):
            debrispart = fx_randrange(debrispart[0], debrispart[1] + 1)
        if isinstance(debrisheading, (int, float)):
            debrisheading = (debrisheading, debrisheading)
        if isinstance(debrispitch, (int, float)):
            debrispitch = (debrispitch, debrispitch)
        for i in xrange(debrispart):
            offdir = fx_randvec(minh=debrisheading[0], maxh=debrisheading[1],
                                minp=debrispitch[0], maxp=debrispitch[1])
            AirBreakupPart(body=(None, self.world),
                           handle=None,
                           duration=4.75 * timefac,
                           termspeed=fx_uniform(10.0, 20.0) * sizefac,
                           offpos=(pos + offdir * 2.0 * sizefac),
                           offdir=offdir,
                           offspeed=fx_uniform(30.0, 60.0),
                           traillifespan=4.75 * timefac,
                           trailthickness=fx_uniform(0.25, 0.5) * sizefac,
                           trailendthfac=16.0,
                           trailspacing=1.0,
                           trailtcol=debristcol)

        self._time0 = self.world.time

        self.alive = True
        base.taskMgr.add(self._loop, "explosion-loop")


    def _start_pfx (self, enode, rnode, pos, radius, scale1, scale2,
                    lifespan, zspin, zspinvel, poolsize, amplitude,
                    texpath, color, alphamode, starttime, fps):

        pfx = ParticleEffect()
        pfx.setPos(pos)

        p0 = make_particles()
        p0.setPoolSize(poolsize)
        p0.setBirthRate(starttime or 1e-5)
        p0.setLitterSize(poolsize)
        p0.setLitterSpread(0)
        #p0.setSystemLifespan(1.0)
        #p0.setLocalVelocityFlag(1)
        #p0.setSystemGrowsOlderFlag(0)

        # p0.setFactory("PointParticleFactory")
        # p0.factory.setLifespanBase(lifespan)
        # p0.factory.setLifespanSpread(0.0)
        # #p0.factory.setMassBase(1.00)
        # #p0.factory.setMassSpread(0.00)
        # #p0.factory.setTerminalVelocityBase(400.0000)
        # #p0.factory.setTerminalVelocitySpread(0.0000)

        p0.setFactory("ZSpinParticleFactory")
        p0.factory.setLifespanBase(lifespan)
        p0.factory.setLifespanSpread(0.0)
        #p0.factory.setMassBase(1.00)
        #p0.factory.setMassSpread(0.00)
        #p0.factory.setTerminalVelocityBase(400.0000)
        #p0.factory.setTerminalVelocitySpread(0.0000)
        p0.factory.setAngularVelocity(zspinvel)
        p0.factory.setFinalAngle(zspin)
        p0.factory.setInitialAngle(0)

        p0.setRenderer("SpriteParticleRenderer")
        p0.renderer.setAlphaMode(alphamode)
        texpaths = texpath
        if not isinstance(texpaths, (tuple, list)):
            texpaths = [texpaths]
        #any_card = False
        #for texpath in texpaths:
            #has_card = set_particle_texture_noext(p0.renderer, "images/particles/%s" % otexpath, add=True)
            #any_card = any_card or has_card
        texpath = fx_choice(texpaths)
        has_card = set_particle_texture_noext(p0.renderer, "images/particles/%s" % texpath)
        p0.renderer.setAnimateFramesEnable(has_card)
        p0.renderer.setAnimateFramesRate(fps)

        if not isinstance(color, tuple):
            p0.renderer.setColor(color)
        p0.renderer.setXScaleFlag(1)
        p0.renderer.setYScaleFlag(1)
        p0.renderer.setAnimAngleFlag(1)
        p0.renderer.setInitialXScale(scale1)
        p0.renderer.setFinalXScale(scale2)
        p0.renderer.setInitialYScale(scale1)
        p0.renderer.setFinalYScale(scale2)

        p0.setEmitter("SphereVolumeEmitter")
        p0.emitter.setRadius(radius)
        p0.emitter.setEmissionType(BaseParticleEmitter.ETRADIATE)
        p0.emitter.setAmplitude(amplitude)
        #p0.emitter.setAmplitudeSpread(0.0)
        #p0.emitter.setOffsetForce(Vec3(0.0000, 0.0000, 0.0000))
        #p0.emitter.setExplicitLaunchVector(Vec3(1.0000, 0.0000, 0.0000))
        #p0.emitter.setRadiateOrigin(Point3(0.0000, 0.0000, 0.0000))

        f0 = ForceGroup("vertex") #Gravity settings.
        force0 = LinearVectorForce(Vec3(0.0, 0.0, 0.0)) #amplitude * 0.7))
        force0.setActive(1)
        f0.addForce(force0)

        p0.setRenderParent(rnode)

        pfx.addForceGroup(f0) #To enable gravity.
        pfx.addParticles(p0)
        pfx.start(enode)

        self._pfxes.append((pfx, p0, lifespan, starttime, color))


    def _loop (self, task):

        time1 = self.world.time - self._time0

        pfxes = []
        for pfx, p0, lifespan, starttime, color in self._pfxes:
            if time1 < starttime + lifespan - self.world.dt * 2:
                pfxes.append((pfx, p0, lifespan, starttime, color))
                if isinstance(color, tuple) and time1 >= starttime:
                    col_s, col_p, col_e, peakat = color
                    time_c = time1 - starttime
                    time_p = lifespan * peakat[0]
                    time_e = lifespan * peakat[1]
                    if time_c < time_p:
                        ifac = time_c / time_p
                        col = col_s + (col_p - col_s) * ifac
                    elif time_c < time_e:
                        ifac = (time_c - time_p) / (time_e - time_p)
                        col = col_p + (col_e - col_p) * ifac
                    else:
                        col = col_e
                    p0.renderer.setColor(col)
            else:
                pfx.cleanup()
        self._pfxes = pfxes
        if not self._pfxes:
            self.alive = False
            self._rnode1.removeNode()
            self._rnode2.removeNode()
            self.node.removeNode()
            return task.done

        #binval = bin_view_b2f(self._pfxes[0][0], self.world.camera)
        #self._rnode1.setBin("fixed", binval)
        #self._rnode2.setBin("fixed", binval - 0)

        if self._lt1:
            col_s = self._lt1_color_atstart
            col_p = self._lt1_color_atpeak
            col_e = self._lt1_color_atend
            rad_s = self._lt1_radius_atstart
            rad_p = self._lt1_radius_atpeak
            rad_e = self._lt1_radius_atend
            time_c = time1 - self._lt1_starttime
            time_e = self._lt1_lifespan
            time_p1 = self._lt1_lifespan * self._lt1_peakat
            time_p2 = self._lt1_lifespan * self._lt1_peakto
            if time_c < 0.0:
                col = col_s
                rad = rad_s
            elif time_c < time_p1:
                ifac = time_c / time_p1
                col = col_s + (col_p - col_s) * ifac
                rad = rad_s + (rad_p - rad_s) * ifac
            elif time_c < time_p2:
                col = col_p
                rad = rad_p
            elif time_c < time_e:
                ifac = (time_c - time_p2) / (time_e - time_p2)
                col = col_p + (col_e - col_p) * ifac
                rad = rad_p + (rad_e - rad_p) * ifac
            else:
                col = col_e
                rad = rad_e
            self._lt1.update(color=col, radius=rad)

        return task.cont


class PolyExplosion (object):

    def __init__ (self, world, pos,
                  firetex=("explosion6-1", "explosion6-2", "explosion6-3", "explosion6-4"),
                  fireglow=rgba(255, 255, 255, 1.0),
                  firetexsplit=1,
                  firenumframes=1,
                  #firetex="images/particles/effects-rocket-exp-4.png",
                  #fireglow="images/particles/effects-rocket-exp-4_gw.png",
                  #firetexsplit=8,
                  #firenumframes=48,
                  smoketex=("smoke6-1", "smoke6-2", "smoke6-3", "smoke6-4"),
                  smokeglow=rgba(0, 0, 0, 0.1),
                  smoketexsplit=1,
                  smokenumframes=1,
                  firepart=1, smokepart=1,
                  sizefac=1.0, timefac=1.0, amplfac=1.0,
                  smgray=pycv(py=(30, 45), c=(254, 255)), smred=10, firepeak=(0.4, 0.8),
                  dirlit=pycv(py=False, c=True),
                  debrispart=0, debrisheading=(-180, 180),
                  debrispitch=(-90, 90), debristcol=0.0,
                  randseed=None):

        self.world = world

        self.node = world.node.attachNewNode("explosion")
        self.node.setAntialias(AntialiasAttrib.MNone)
        self.node.setPos(pos)

        self._parts = []

        pick = lambda d, i: d[i] if isinstance(d, (tuple, list)) else d
        rest = lambda t: (t if (not isinstance(t, basestring) or "." in t)
                          else ("images/particles/%s.png" % t))

        if randseed is None:
            randseed = fx_randrange(2**31)
            # ...not -1, to propagate determinism if global seed is set.
        self._rg = NumRandom(randseed)
        # ...instance attribute in order not to be garbage collected while
        # being used through reference in C++ version of PolyExplosionGeom.

        # Fire particles.
        fstime = 0.05
        max_flspan = 0.0
        fnumtex = len(firetex) if isinstance(firetex, (tuple, list)) else 1
        for i in range(firepart):
            fi = self._rg.randrange(fnumtex)
            ftex = rest(pick(firetex, fi))
            fglow = rest(pick(fireglow, fi))
            ftexsp = pick(firetexsplit, fi)
            fnumfr = pick(firenumframes, fi)
            #fanim = pick(fireanim, fi)
            fanim = (ftexsp > 1 and fnumfr > 1)
            if firepart > 1:
                pdir = self._rg.randvec()
                fpos = Point3(pdir * (2.0 * sizefac))
            else:
                fpos = Point3(0.0, 0.0, 0.0)
            frad = 5.0 * sizefac
            fsz1 = 1.0 * sizefac
            fsz2 = self._rg.uniform(9.0, 18.0) * sizefac
            fampl = 1.2 * amplfac
            flspan = self._rg.uniform(0.5, 1.0) * timefac
            fpeak1, fpeak2 = firepeak
            if fanim:
                fcol1 = rgba(255, 255, 255, 1.0)
                fcol2 = Vec4(0.0, 0.0, 0.0, 0.0)
                fcol3 = Vec4(0.0, 0.0, 0.0, 0.0)
                fpeak1 = 1.0
            else:
                fcol1 = rgba(255, 248, 243, 1.0)
                if fpeak1 < 1.0:
                    fcol2 = rgba(255, 255, 255, 1.0)
                    fcol3 = rgba(112, 62, 23, 1.0)
                else:
                    fcol2 = Vec4(0.0, 0.0, 0.0, 0.0)
                    fcol3 = Vec4(0.0, 0.0, 0.0, 0.0)
            fplsz = 8
            part = self._create_part(
                world=world, pnode=self.node, dirlit=dirlit,
                texture=ftex, glowmap=fglow,
                texsplit=ftexsp, numframes=fnumfr, animated=fanim,
                size1=fsz1, size2=fsz2,
                color1=fcol1, color2=fcol2, color3=fcol3,
                colpeak1=fpeak1, colpeak2=fpeak2,
                pos=fpos, radius=frad, amplitude=fampl,
                lifespan=flspan, poolsize=fplsz,
                starttime=fstime,
                randgen=self._rg)
            self._parts.append(part)
            max_flspan = max(max_flspan, flspan)

        # Smoke particles.
        snumtex = len(smoketex) if isinstance(smoketex, (tuple, list)) else 1
        for i in range(smokepart):
            si = self._rg.randrange(snumtex)
            stex = rest(pick(smoketex, si))
            sglow = rest(pick(smokeglow, si))
            stexsp = pick(smoketexsplit, si)
            snumfr = pick(smokenumframes, si)
            #sanim = pick(smokeanim, si)
            sanim = (stexsp > 1 and snumfr > 1)
            spos = Point3(0.0, 0.0, 0.0)
            srad = 5.0 * sizefac
            ssz1 = 1.5 * sizefac
            ssz2 = 30.0 * sizefac
            sampl = 5.0 * amplfac
            slspan = self._rg.uniform(4.5, 5.0) * timefac
            sstime = 0.0 * timefac
            smokepeak = pycv(py=(0.2, 0.6), c=(0.2, 0.4))
            speak1, speak2 = smokepeak
            if sanim:
                scol1 = rgba(255, 255, 255, 1.0)
                scol2 = Vec4(0.0, 0.0, 0.0, 0.0)
                scol3 = Vec4(0.0, 0.0, 0.0, 0.0)
                speak1 = 1.0
            else:
                if isinstance(smgray, tuple):
                    c = self._rg.randrange(smgray[0], smgray[1] + 1)
                else:
                    c = smgray
                if smred <= 0 or c + smred > 255:
                    scolmodred = 0
                else:
                    scolmodred = self._rg.randrange(smred + 1)
                scol1 = pycv(py=rgba(c + scolmodred, c, c, 0.5), c=rgba(c + scolmodred, c, c, 1.0))
                if speak1 < 1.0:
                    scol2 = pycv(py=rgba(c + scolmodred, c, c, 0.5), c=rgba(c + scolmodred, c, c, 1.0))
                    c3 = pycv(py=c * 0.30, c=c * 0.30)
                    scol3 = pycv(py=rgba(c3 + scolmodred, c3, c3, 0.5), c=rgba(c3 + scolmodred, c3, c3, 1.0))
                else:
                    scol2 = Vec4(0.0, 0.0, 0.0, 0.0)
                    scol3 = Vec4(0.0, 0.0, 0.0, 0.0)
            splsz = 11
            part = self._create_part(
                world=world, pnode=self.node, dirlit=dirlit,
                texture=stex, glowmap=sglow,
                texsplit=stexsp, numframes=snumfr, animated=sanim,
                size1=ssz1, size2=ssz2,
                color1=scol1, color2=scol2, color3=scol3,
                colpeak1=speak1, colpeak2=speak2,
                pos=spos, radius=srad, amplitude=sampl,
                lifespan=slspan, poolsize=splsz,
                starttime=sstime,
                randgen=self._rg)
            self._parts.append(part)

        # Lighting.
        if firepart > 0:
            self._lt1_color_atstart = rgba(255, 255, 0, 1.0) * 1
            self._lt1_radius_atstart = 10.0 * sizefac
            self._lt1_color_atpeak = rgba(255, 255, 0, 1.0) * 10
            self._lt1_radius_atpeak = 100.0 * sizefac
            self._lt1_color_atend = rgba(0, 0, 0, 1.0)
            self._lt1_radius_atend = 10.0 * sizefac
            self._lt1 = AutoPointLight(
                parent=self, color=self._lt1_color_atstart,
                radius=self._lt1_radius_atstart, halfat=0.5,
                litnode=world.node, name="explosion")
            self._lt1_starttime = fstime
            self._lt1_lifespan = max_flspan
            if firepeak[0] < 1.0:
                self._lt1_peakat = 0.05
                self._lt1_peakto = firepeak[0]
            else:
                self._lt1_peakat = 0.05
                self._lt1_peakto = 0.80
        else:
            self._lt1 = None

        # Debris trails.
        if isinstance(debrispart, tuple):
            debrispart = self._rg.randrange(debrispart[0], debrispart[1] + 1)
        if isinstance(debrisheading, (int, float)):
            debrisheading = (debrisheading, debrisheading)
        if isinstance(debrispitch, (int, float)):
            debrispitch = (debrispitch, debrispitch)
        for i in xrange(debrispart):
            offdir = self._rg.randvec(
                minh=debrisheading[0], maxh=debrisheading[1],
                minp=debrispitch[0], maxp=debrispitch[1])
            AirBreakupPart(body=(None, self.world),
                           handle=None,
                           duration=4.75 * timefac,
                           termspeed=self._rg.uniform(10.0, 20.0) * sizefac,
                           offpos=(pos + offdir * 2.0 * sizefac),
                           offdir=offdir,
                           offspeed=self._rg.uniform(30.0, 60.0),
                           traillifespan=4.75 * timefac,
                           trailthickness=self._rg.uniform(0.25, 0.5) * sizefac,
                           trailendthfac=16.0,
                           trailspacing=1.0,
                           trailtcol=debristcol)

        self._time0 = self.world.time

        self.alive = True
        base.taskMgr.add(self._loop, "polyexplosion-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    @staticmethod
    def _create_part (world, pnode, dirlit,
                      texture, glowmap,
                      texsplit, numframes, animated,
                      size1, size2,
                      color1, color2, color3, colpeak1, colpeak2,
                      pos, radius, amplitude, lifespan, poolsize,
                      randgen, starttime):

        geom = PolyExplosionGeom(pnode,
                                 texsplit, numframes, animated,
                                 size1, size2,
                                 color1, color2, color3, colpeak1, colpeak2,
                                 pos, radius, amplitude, lifespan, poolsize,
                                 randgen)
        gnode = geom.root()
        world.add_altbin_node(gnode)

        if dirlit:
            ambln = world.shdinp.ambln
            dirlns = world.shdinp.dirlns
        else:
            ambln = world.shdinp.ambsmln
            dirlns = []
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)
        shader = make_shader(ambln=ambln, dirlns=dirlns,
                             glow=glow, modcol=True)
        gnode.setShader(shader)
        set_texture(gnode, texture=texture, glowmap=glowmap, clamp=True)

        part = SimpleProps(geom=geom, starttime=starttime, started=False)

        return part


    def _loop (self, task):

        time1 = self.world.time - self._time0

        parts = []
        for part in self._parts:
            if not part.started:
                if time1 >= part.starttime:
                    part.geom.start(self.world.camera)
                    part.started = True
            else:
                cont = part.geom.update(self.world.camera, self.world.dt)
                if not cont:
                    continue
            parts.append(part)
        if not parts:
            self.destroy()
            return task.done
        self._parts = parts

        if self._lt1:
            col_s = self._lt1_color_atstart
            col_p = self._lt1_color_atpeak
            col_e = self._lt1_color_atend
            rad_s = self._lt1_radius_atstart
            rad_p = self._lt1_radius_atpeak
            rad_e = self._lt1_radius_atend
            time_c = time1 - self._lt1_starttime
            time_e = self._lt1_lifespan
            time_p1 = self._lt1_lifespan * self._lt1_peakat
            time_p2 = self._lt1_lifespan * self._lt1_peakto
            if time_c < 0.0:
                col = col_s
                rad = rad_s
            elif time_c < time_p1:
                ifac = time_c / time_p1
                col = col_s + (col_p - col_s) * ifac
                rad = rad_s + (rad_p - rad_s) * ifac
            elif time_c < time_p2:
                col = col_p
                rad = rad_p
            elif time_c < time_e:
                ifac = (time_c - time_p2) / (time_e - time_p2)
                col = col_p + (col_e - col_p) * ifac
                rad = rad_p + (rad_e - rad_p) * ifac
            else:
                col = col_e
                rad = rad_e
            self._lt1.update(color=col, radius=rad)

        return task.cont


# :also-compiled:
class PolyExplosionGeom (object):

    def __init__ (self, pnode,
                  texsplit, numframes, animated,
                  size1, size2,
                  color1, color2, color3, colpeak1, colpeak2,
                  pos, radius, amplitude, lifespan, poolsize,
                  randgen):

        self._poolsize = poolsize
        self._texsplit = texsplit
        self._numframes = numframes
        self._animated = animated
        self._size1 = size1
        self._size2 = size2
        self._color1 = color1
        self._color2 = color2
        self._color3 = color3
        self._colpeak1 = colpeak1
        self._colpeak2 = colpeak2
        self._radius = radius
        self._amplitude = amplitude
        self._lifespan = lifespan
        self._poolsize = poolsize

        self._rg = randgen

        self._node = pnode.attachNewNode("polyexplosion-geom")
        self._node.setPos(pos)

        self._started = False


    def start (self, camera):

        if self._started:
            return

        self._gen = MeshDrawer()
        self._gen.setBudget(self._poolsize * 2)
        gnode = self._gen.getRoot()
        gnode.setDepthWrite(False)
        gnode.setTransparency(TransparencyAttrib.MAlpha)
        gnode.reparentTo(self._node)

        frind = 0 if self._animated else self._rg.randrange(self._numframes)
        frame = texture_frame(self._texsplit, frind)
        self._frame1 = frame

        size = self._size1

        color = self._color1

        #distrib = HaltonDistrib(1)
        distrib = HaltonDistrib(self._rg.randrange(10) * 100)
        self._particles = []
        for i in xrange(self._poolsize):
            #rad = self._rg.uniform(0.0, self._radius)
            #pos = self._rg.randvec() * rad
            d3 = distrib.next3()
            hpr = Vec3(degrees((2 * pi) * d3[0]), degrees(asin(2 * d3[1] - 1)), 0.0)
            rad = self._radius * d3[2]**0.333
            pos = hprtovec(hpr) * rad
            vel = unitv(pos) * self._amplitude
            p = SimpleProps(pos=pos, vel=vel,
                            frame=frame, size=size, color=color)
            self._particles.append(p)

        self._draw_particles(camera)

        self._time = 0.0
        self._started = True
        self._done = False


    def update (self, camera, adt):

        if not self._started:
            return True
        elif self._done:
            return False

        self._time += adt
        if self._time >= self._lifespan:
            if not self._done:
                self._clear(camera)
                self._done = True
            return False

        ifac = self._time / self._lifespan

        if self._animated:
            frind = int(self._numframes * ifac)
            frame = texture_frame(self._texsplit, frind)
        else:
            frame = self._frame1

        size = self._size1 + (self._size2 - self._size1) * ifac

        if self._colpeak1 < 1.0:
            time_c = self._time
            time_p = self._lifespan * self._colpeak1
            time_e = self._lifespan * self._colpeak2
            if time_c < time_p:
                ifac1 = time_c / time_p
                color = self._color1 + (self._color2 - self._color1) * ifac1
            elif time_c < time_e:
                ifac2 = (time_c - time_p) / (time_e - time_p)
                color = self._color2 + (self._color3 - self._color2) * ifac2
            else:
                color = self._color3
        else:
            color = self._color1
        color = Vec4(color)
        color[3] *= (1.0 - ifac)

        for p in self._particles:
            p.pos += p.vel * adt
            p.size = size
            p.frame = frame
            p.color = color

        self._draw_particles(camera)

        return True


    def _draw_particles (self, camera):

        self._gen.begin(camera, self._gen.getRoot())
        for p in self._particles:
            self._gen.billboard(p.pos, p.frame, p.size * 0.5, p.color)
        self._gen.end()

        center = Point3(0.0, 0.0, 0.0)
        maxreach = self._radius
        gnode = self._gen.getRoot()
        gnode.node().setBounds(BoundingSphere(center, maxreach))
        gnode.node().setFinal(True)


    def _clear (self, camera):

        self._gen.begin(camera, self._gen.getRoot())
        self._gen.end()


    def root (self):

        return NodePath(self._node)


class Fire (object):

    def __init__ (self, world, size, color=rgba(255, 255, 255, 1.0), pos=Point3(), hpr=Vec3(), sink=0.0, nsides=2, fps=24, parent=None):

        if isinstance(pos, (VBase2, VBase2D)):
            if parent is not None:
                z = -world.otr_altitude(parent.pos(offset=Point3(pos[0], pos[1], 0.0))) - sink
            else:
                z = world.elevation(pos) - sink
            pos = Point3(pos[0], pos[1], z)

        self.world = world
        self.parent = parent or world
        self.fps = fps

        self.node = self.parent.node.attachNewNode("fire")
        self.node.setPos(pos)
        self.node.setHpr(hpr)
        self.node.setColorScale(color)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.node.setDepthWrite(False)
        shader = make_shader(modcol=True)
        self.node.setShader(shader)
        self.world.add_altbin_node(self.node)

        if not nsides:
            nsides = 1
            self.node.setBillboardAxis()

        frame_tex_path_fmt = "images/fire/frame_%04d.png"
        frame_start = 1
        frame_num = 89

        self._board_nodes = []
        if isinstance(size, tuple):
            width, height = size
        else:
            width = height = size
        for i in range(nsides):
            bnd = make_quad(parent=self.node,
                            pos=Point3(0.0, 0.0, 0.5 * height),
                            hpr=Vec3(i * (180.0 / nsides), 0, 0),
                            size=(width, height),
                            twosided=True)
            self._board_nodes.append(bnd)

        self._frame_texs = []
        for i in range(frame_num):
            tex_ind = frame_start + i
            frame_tex_path = frame_tex_path_fmt % tex_ind
            frame_tex = base.load_texture("data", frame_tex_path)
            self._frame_texs.append(frame_tex)

        self._wait_next_frame = 0.0
        self._next_frame = 0

        self.alive = True
        base.taskMgr.add(self._loop, "fire-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done

        self._wait_next_frame -= self.world.dt
        if self._wait_next_frame <= 0.0:
            self._wait_next_frame = 1.0 / self.fps
            for bnd in self._board_nodes:
                set_texture(bnd, self._frame_texs[self._next_frame])
            self._next_frame += 1
            if self._next_frame >= len(self._frame_texs):
                self._next_frame = 0

        #binval = bin_view_b2f(self.node, self.world.camera)
        #self.node.setBin("fixed", binval)

        return task.cont


class Splash (object):

    _cache_geom = {}

    def __init__ (self, world, pos, size, texture, texsplit,
                  relsink=0.5, numquads=4, fps=24, numframes=None,
                  glowmap=None,
                  debrispart=0, debrisheading=(-180, 180),
                  debrispitch=(-90, 90), debristcol=0.0):

        self.world = world

        self._texture_split = texsplit
        self._texture_step = 1.0 / texsplit

        self._num_frames = numframes
        if self._num_frames is None:
            self._num_frames = self._texture_split**2

        gkey = (size, numquads, texsplit)
        base_node = self._cache_geom.get(gkey)
        if base_node is None:
            radius = 0.5 * size
            step = self._texture_step * 0.9999 # avoid u, v > 1 in floor() in shader
            uvext = ((0.0, 0.0), (0.0, step), (step, step), (step, 0.0))
            if numquads > 1:
                slant = 0.5 * pi / (numquads + 1)
            elif numquads == 1:
                slant = 0.0
            else:
                raise StandardError("Number of quads must be at least 1.")
            base_node = make_quad_lattice(length=size,
                                          radius0=radius, radius1=radius,
                                          numquads=numquads, slant=slant,
                                          uvext=uvext)
            self._cache_geom[gkey] = base_node
        self.node = world.node.attachNewNode("splash")
        if numquads == 1:
            self.node.setBillboardAxis()
        sub_node = base_node.copyTo(self.node)
        sub_node.setP(90.0)
        sub_node.setZ(-size * relsink)
        self.node.setPos(pos)

        self.node.setTwoSided(True)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.node.setDepthWrite(False)
        self.world.add_altbin_node(self.node)

        uvscrn = "INuvscr"
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)
        shader = make_shader(ambln=self.world.shdinp.ambln, glow=glow,
                             modcol=True, uvscrn=uvscrn)
        self.node.setShader(shader)
        set_texture(self.node, texture, glowmap=glowmap, clamp=True)
        self._uv_scroll = AmbientLight(name="uvscr-splash")
        self.node.setShaderInput(uvscrn, NodePath(self._uv_scroll))
        self._uv_offset = Vec4(0.0, 0.0, 0.0, 0.0)
        self._uv_scroll.setColor(self._uv_offset)

        # Debris trails.
        if isinstance(debrispart, tuple):
            debrispart = fx_randrange(debrispart[0], debrispart[1] + 1)
        if isinstance(debrisheading, (int, float)):
            debrisheading = (debrisheading, debrisheading)
        if isinstance(debrispitch, (int, float)):
            debrispitch = (debrispitch, debrispitch)
        for i in xrange(debrispart):
            offdir = fx_randvec(minh=debrisheading[0], maxh=debrisheading[1],
                                minp=debrispitch[0], maxp=debrispitch[1])
            AirBreakupPart(body=(None, self.world),
                           handle=None,
                           duration=4.75 * timefac,
                           termspeed=fx_uniform(10.0, 20.0) * sizefac,
                           offpos=(pos + offdir * 2.0 * sizefac),
                           offdir=offdir,
                           offspeed=fx_uniform(30.0, 60.0),
                           traillifespan=4.75 * timefac,
                           trailthickness=fx_uniform(0.25, 0.5) * sizefac,
                           trailendthfac=16.0,
                           trailspacing=1.0,
                           trailtcol=debristcol)

        self._time_step = 1.0 / fps
        self._wait_next_frame = 0.0
        self._frame_counter = 0
        self._index_u = 0
        self._index_v = 0

        self.alive = True
        base.taskMgr.add(self._loop, "splash-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        self._wait_next_frame -= self.world.dt
        if self._wait_next_frame <= 0.0:
            self._wait_next_frame += self._time_step
            if self._frame_counter == self._num_frames:
                self.destroy()
                return task.done

            self._uv_offset[0] = self._index_u * self._texture_step
            self._uv_offset[1] = 1.0 - (self._index_v + 1) * self._texture_step
            self._uv_scroll.setColor(self._uv_offset)

            self._frame_counter += 1
            self._index_u += 1
            if self._index_u == self._texture_split:
                self._index_u = 0
                self._index_v += 1

        return task.cont


if USE_COMPILED:
    from fire_c import *
