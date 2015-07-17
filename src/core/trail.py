# -*- coding: UTF-8 -*-

from math import pi, radians, sqrt, sin, cos, floor, acos

from direct.particles.ForceGroup import ForceGroup
from direct.particles.ParticleEffect import ParticleEffect
from pandac.PandaModules import AntialiasAttrib
from pandac.PandaModules import Vec2, Vec3, Vec4, Point3, Quat
from pandac.PandaModules import BaseParticleRenderer, BaseParticleEmitter
from pandac.PandaModules import LinearVectorForce
from pandac.PandaModules import MeshDrawer
from pandac.PandaModules import BoundingSphere
from pandac.PandaModules import NodePath, LODNode
from pandac.PandaModules import TransparencyAttrib, ColorBlendAttrib

from src import pycv, USE_COMPILED
from src.core.light import AutoPointLight, PointOverbright
from src.core.misc import rgba, unitv, clamp, make_particles, bin_view_b2f
from src.core.misc import SimpleProps, set_texture, print_each, is_on_screen
from src.core.misc import intl10r, intl01vr, set_particle_texture_noext
from src.core.misc import fx_randunit, fx_uniform, fx_choice
from src.core.shader import make_shader


class Trail (object):

    def __init__ (self, parent, pos, scale1, scale2, lifespan, poolsize,
                  force, alpha, color, ptype,
                  subnode=None, pdir=Vec3(0.0, -1.0, 0.0), phpr=Vec3(0, 0, 0),
                  ltpos=None,
                  ltcolor=Vec4(1, 1, 1, 1), ltcolor2=None,
                  ltradius=10.0, ltradius2=None, lthalfat=0.5,
                  ltpulse=0.0,
                  obpos=None,
                  obcolor=Vec4(1, 1, 1, 1), obcolor2=None,
                  obradius=10.0, obradius2=None, obhalfat=0.5,
                  obpulse=0.0,
                  glowcolor=None,
                  littersize=1, emradius=0.0, emamp=0, emamps=0,
                  birthrate=None, risefact=Vec3(0.0, 0.0, 0.0),
                  ltoff=False, colorend=None, alphaout=True, fps=24,
                  tcol=0.5, additive=False,
                  absolute=False, delay=0.0, fardist=None):

        self.alive = True
        self._parent = parent
        self._pnode = subnode or parent.node
        self.world = parent.world

        if pdir is not None:
            pdir = unitv(pdir)
        self._pdir = pdir
        self._pos = pos
        self._phpr = phpr

        self._absolute = absolute

        self._alpha = alpha
        self._alphaout = alphaout
        self._birthrate = birthrate
        self._color = Vec4(color)
        self._colorend = Vec4(colorend) if colorend is not None else None
        self._tcol = tcol
        self._emradius = emradius
        self._emamp = emamp
        self._emamps = emamps
        self.force = force
        self._lifespan = lifespan
        self._littersize = littersize
        self._poolsize = poolsize
        self._ptype = ptype
        self._risefact = risefact
        self.scale1 = scale1
        self.scale2 = scale2
        self._fps = fps
        self._additive = additive

        self._ltpos = ltpos
        self._ltcolor = ltcolor
        self._ltcolor2 = ltcolor2 if ltcolor2 is not None else ltcolor
        self._ltradius = ltradius
        self._ltradius2 = ltradius2 if ltradius2 is not None else ltradius
        self._lthalfat = lthalfat
        if ltpulse is True:
            ltpulse = 0.010
        self._ltpulse_rate = ltpulse
        self._ltpulse_wait = 0.0

        self._obpos = obpos
        self._obcolor = obcolor
        self._obcolor2 = obcolor2 if obcolor2 is not None else obcolor
        self._obradius = obradius
        self._obradius2 = obradius2 if obradius2 is not None else obradius
        self._obhalfat = obhalfat
        if obpulse is True:
            obpulse = 0.010
        self._obpulse_rate = obpulse
        self._obpulse_wait = 0.0

        self._glowcolor = glowcolor

        self._ltoff = ltoff

        self._fardist = fardist

        self._pfx = None
        self._rnode = None
        self._rlodnode = None
        self._lights = []
        self._overbright = []
        self._pnode_gone = False

        self._wait_delay = delay

        pvel = self._parent.vel()
        rpvel = self._pnode.getRelativeVector(self.world.node, pvel)
        self._last_odir = -unitv(rpvel)

        self._end = False
        self._end_time = None

        task = base.taskMgr.add(self._loop, "trail-loop")


    def _make_trail (self):

        self._pfx = ParticleEffect()
        if self._pdir is not None:
            offdir = self._pdir
        else:
            offdir = Vec3(0.0, -1.0, 0.0)
        posoff = 0.5 # number depends on particle size
        self._pfx.setPos(self._pos + offdir * posoff)
        self._pfx.setHpr(self._phpr)
        #pfx.setScale(1.0)

        p0 = make_particles()
        p0.setPoolSize(self._poolsize)
        if self._birthrate is None:
            self._birthrate = (float(self._lifespan) / self._poolsize) * 1.05
        p0.setBirthRate(self._birthrate)
        p0.setLitterSize(self._littersize)
        p0.setLitterSpread(0)
        #p0.setSystemLifespan(0.00)
        #p0.setLocalVelocityFlag(1)
        #p0.setSystemGrowsOlderFlag(0)

        p0.setFactory("PointParticleFactory")
        p0.factory.setLifespanBase(self._lifespan)
        p0.factory.setLifespanSpread(0.0)
        #p0.factory.setMassBase(1.00)
        #p0.factory.setMassSpread(0.00)
        #p0.factory.setTerminalVelocityBase(400.0000)
        #p0.factory.setTerminalVelocitySpread(0.0000)

        p0.setRenderer("SpriteParticleRenderer")
        if self._alphaout:
            alpha_mode = BaseParticleRenderer.PRALPHAOUT
        else:
            alpha_mode = BaseParticleRenderer.PRALPHAUSER
        p0.renderer.setAlphaMode(alpha_mode)
        ptypes = self._ptype
        if not isinstance(ptypes, (list, tuple)):
            ptypes = [ptypes]
        any_card = False
        for ptype in ptypes:
            has_card = set_particle_texture_noext(p0.renderer, "images/particles/%s" % ptype, add=True)
            any_card = any_card or has_card
        #ptype = fx_choice(ptypes)
        #any_card = set_particle_texture_noext(p0.renderer, "images/particles/%s" % ptype)
        p0.renderer.setUserAlpha(self._alpha)
        p0.renderer.setAnimateFramesEnable(any_card)
        p0.renderer.setAnimateFramesRate(self._fps)
        if self._colorend is None:
            p0.renderer.setColor(self._color)
        else:
            cim = p0.renderer.getColorInterpolationManager()
            tfac0 = 0.0
            tfac1 = self._tcol
            cim.addConstant(0.0, tfac0, self._color)
            cim.addLinear(tfac0, tfac1, self._color, self._colorend)
            cim.addConstant(tfac1, 1.0, self._colorend)
        p0.renderer.setXScaleFlag(1)
        p0.renderer.setYScaleFlag(1)
        p0.renderer.setInitialXScale(self.scale1)
        p0.renderer.setFinalXScale(self.scale2)
        p0.renderer.setInitialYScale(self.scale1)
        p0.renderer.setFinalYScale(self.scale2)
        #p0.renderer.setAnimAngleFlag(0)
        #p0.renderer.setNonanimatedTheta(0.0000)
        #p0.renderer.setAlphaBlendMethod(BaseParticleRenderer.PPBLENDLINEAR)
        #p0.renderer.setAlphaDisable(0)

        if self._emradius == 0.0:
            p0.setEmitter("PointEmitter")
        else:
            p0.setEmitter("DiscEmitter")
            p0.emitter.setRadius(self._emradius)
            p0.emitter.setEmissionType(BaseParticleEmitter.ETRADIATE)
            p0.emitter.setAmplitude(self._emamp)
            p0.emitter.setAmplitudeSpread(self._emamps)
            #p0.emitter.setExplicitLaunchVector(Vec3(1.0000, 0.0000, 0.0000))
            #p0.emitter.setRadiateOrigin(Point3(0.0000, 0.0000, 0.0000))

        f0 = ForceGroup("vertex")
        force0 = LinearVectorForce(self._risefact)
        force0.setActive(1)
        f0.addForce(force0)

        self.init_force = self.force
        self.init_scale1 = self.scale1
        self.init_scale2 = self.scale2

        self._prev_force = None
        self._prev_scale1 = None
        self._prev_scale2 = None

        self._pfx.addParticles(p0)
        self._pfx.addForceGroup(f0)

        self._p0 = p0
        if self._absolute:
            if self._fardist:
                rlod = LODNode("trail-render")
                self._rlodnode = NodePath(rlod)
                self._rlodnode.reparentTo(self.world.node)
                self._rlodpos0 = self._pnode.getPos(self.world.node)
                self._rlodnode.setPos(self._rlodpos0)
                self._rnode = NodePath("trail-render")
                rlod.addSwitch(self._fardist, 0)
                self._rnode.reparentTo(self._rlodnode)
                self._rnode.setPos(self._pos)
            else:
                self._rnode = self.world.node.attachNewNode("trail-render")
                self._rnode.setPos(self._pnode.getPos(self.world.node) + self._pos)
        else:
            if self._fardist:
                rlod = LODNode("trail-render")
                self._rlodnode = NodePath(rlod)
                self._rlodnode.reparentTo(self._pnode)
                self._rlodnode.setPos(self._pos)
                self._rnode = NodePath("trail-render")
                rlod.addSwitch(self._fardist, 0)
                self._rnode.reparentTo(self._rlodnode)
            else:
                self._rnode = self._pnode.attachNewNode("trail-render")
                self._rnode.setPos(self._pos)
        self._rnode.setDepthWrite(False)
        p0.setRenderParent(self._rnode)
        self._pfx.start(self._pnode)
        ambln = self.world.shdinp.ambsmln if not self._ltoff else None
        shader = make_shader(ambln=ambln,
                             glow=self._glowcolor, modcol=True,
                             selfalpha=self._additive)
        self._rnode.setShader(shader)
        self.world.add_altbin_node(self._rnode)
        if self._additive:
            self._rnode.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))

        if self._ltpos is not None:
            ltpos = self._ltpos
            if self._ltcolor is None:
                self._ltcolor = rgba(255, 255, 255, 1.0)
            if not isinstance(ltpos, (list, tuple)):
                ltpos = [ltpos]
            for lp in ltpos:
                lt = AutoPointLight(
                    parent=self._parent, color=self._ltcolor,
                    radius=self._ltradius, halfat=self._lthalfat,
                    pos=lp, name="trail")
                self._lights.append(lt)
            self.light_cscale = 1.0
            self._prev_light_cscale = None

        if self._obpos is not None:
            obpos = self._obpos
            if self._obcolor is None:
                self._obcolor = rgba(255, 255, 255, 1.0)
            self._overbright = PointOverbright(
                parent=self._parent, color=self._obcolor,
                radius=self._obradius, halfat=self._obhalfat,
                pos=self._obpos, name="trail")
            self._pnode.setShaderInput(self.world.shdinp.pntobrn,
                                       self._overbright.node)
            self.overbright_cscale = 1.0
            self._prev_overbright_cscale = None


    def _loop (self, task):

        if not self.alive:
            return task.done

        if self._wait_delay >= 0.0:
            self._wait_delay -= max(self.world.dt, 1e-10) # must go < 0.0 if 0.0
            if self._wait_delay <= 0.0:
                if not self._pnode.isEmpty():
                    self._make_trail()
            else:
                return task.cont

        if self._rnode is None or self._rnode.isEmpty():
            self.destroy()
            return task.done

        if self._end:
            if self._end_time is None:
                self._end_time = self.world.time
                self._p0.setBirthRate(self._lifespan - self.world.maxdt)
            if self.world.time - self._end_time > self._lifespan:
                self.destroy()
                return task.done

        if self._pnode.isEmpty():
            if self._absolute:
                if not self._pnode_gone:
                    self._pnode_gone = True
                    self._pnode_gone_time = self.world.time
                    self._p0.setBirthRate(self._lifespan)
                if self.world.time - self._pnode_gone_time > self._lifespan:
                    self.destroy()
                    return task.done
            else:
                self.destroy()
                return task.done
        else:
            if self._absolute and self._rlodnode is not None:
                ppos = self._pnode.getPos(self.world.node)
                self._rlodnode.setPos(ppos)
                self._rnode.setPos(self._rlodpos0 - ppos)
            pass
            #binval = bin_view_b2f(self._pnode, self.world.camera)
            #self._rnode.setBin("fixed", binval)

        if self._pdir is not None:
            odir = self._pdir
            update_force = (self._prev_force != self.force)
        else:
            if self._parent.alive:
                pvel = self._parent.vel()
                rpvel = self._pnode.getRelativeVector(self.world.node, pvel)
                odir = -unitv(rpvel)
                self._last_odir = odir
            else:
                odir = self._last_odir
            update_force = True
        if update_force:
            self._prev_force = self.force
            self._p0.emitter.setOffsetForce(odir * self.force)

        if self._prev_scale1 != self.scale1:
            self._prev_scale1 = self.scale1
            self._p0.renderer.setInitialXScale(self.scale1)
            self._p0.renderer.setInitialYScale(self.scale1)
        if self._prev_scale2 != self.scale2:
            self._prev_scale2 = self.scale2
            self._p0.renderer.setFinalXScale(self.scale2)
            self._p0.renderer.setFinalYScale(self.scale2)

        if self._lights:
            if self._ltpulse_rate:
                self._ltpulse_wait -= self.world.dt
                if self._ltpulse_wait < 0.0:
                    self._ltpulse_wait += self._ltpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._ltcolor + (self._ltcolor2 - self._ltcolor) * ifac
                    radius = self._ltradius + (self._ltradius2 - self._ltradius) * ifac
                    for lt in self._lights:
                        lt.update(color=color, radius=radius)
            elif self._prev_light_cscale != self.light_cscale:
                self._prev_light_cscale = self.light_cscale
                for lt in self._lights:
                    color = self._ltcolor * self.light_cscale
                    lt.update(color=color)

        if self._overbright:
            if self._obpulse_rate:
                self._obpulse_wait -= self.world.dt
                if self._obpulse_wait < 0.0:
                    self._obpulse_wait += self._obpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._obcolor + (self._obcolor2 - self._obcolor) * ifac
                    radius = self._obradius + (self._obradius2 - self._obradius) * ifac
                    self._overbright.update(color=color, radius=radius)
            elif self._prev_overbright_cscale != self.overbright_cscale:
                self._prev_overbright_cscale = self.overbright_cscale
                color = self._obcolor * self.overbright_cscale
                self._overbright.update(color=color)

        return task.cont


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self._pfx is not None:
            self._pfx.cleanup()
        if self._rnode is not None:
            self._rnode.removeNode()
        if self._rlodnode is not None:
            self._rlodnode.removeNode()
        for lt in self._lights:
            lt.destroy()
        if self._overbright:
            if not self._pnode.isEmpty():
                self._pnode.clearShaderInput(self.world.shdinp.pntobrn)
            self._overbright.destroy()


    def end (self):

        self._end = True


class PolyTrail (object):

    def __init__ (self, parent, pos, radius0, radius1, lifespan, color,
                  segperiod=0.005, farsegperiod=pycv(py=0.100, c=None),
                  maxpoly=2000, farmaxpoly=2000,
                  randcircle=0.0,
                  texture=None, glowmap=None, dirlit=False,
                  colorend=None, tcol=1.0,
                  dbin=0, loddistout=None, loddistalpha=None):

        if isinstance(parent, tuple):
            self.parent = None
            self.pnode, self.world = parent
        else:
            self.world = parent.world
            self.parent = parent
            self.pnode = None

        self.radius0 = float(radius0)
        self.radius1 = float(radius1)
        self.lifespan = float(lifespan)
        self.color = Vec4(color)
        self.colorend = Vec4(colorend if colorend is not None else color)
        self.loddistout = loddistout

        self._pos = pos
        self._dbin = dbin
        self._tcol = tcol

        self.node = self.world.node.attachNewNode("polytrail-root")
        self.node.setAntialias(AntialiasAttrib.MNone)
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)
        #self.node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        if dirlit:
            #ambln = self.world.shdinp.ambln
            ambln = self.world.shdinp.ambsmln
            dirlns = self.world.shdinp.dirlns
        else:
            ambln = self.world.shdinp.ambsmln
            dirlns = []
        shader = make_shader(ambln=ambln, dirlns=dirlns,
                             glow=glow, modcol=True) #, selfalpha=True)
        self.node.setShader(shader)

        if self.parent:
            self.node.setPos(self.parent.pos())
            apos = self.parent.pos(refbody=self.node, offset=self._pos)
            aquat = self.parent.quat()
        elif self.pnode is not None:
            self.node.setPos(self.pnode.getPos(self.world.node))
            apos = self.node.getRelativePoint(self.pnode, self._pos)
            aquat = self.pnode.getQuat(self.world.node)
        else:
            assert False
        if farsegperiod and farsegperiod > segperiod:
            pspec = ((farmaxpoly, farsegperiod), (maxpoly, segperiod))
        else:
            pspec = ((maxpoly, segperiod),)
        accu = []
        for npoly, segp in pspec:
            tpack = PolyTrailGeom(npoly, randcircle, segp,
                                  apos, aquat, self.node)
            #set_texture(tpack.node(), texture=texture, glowmap=glowmap)
            # ...this crashes on Windows/VC 15.00something.
            tnode = tpack.node()
            set_texture(tnode, texture=texture, glowmap=glowmap)
            self.world.add_altbin_node(tnode)
            accu.append(tpack)
        if len(accu) == 2:
            self._farpack, self._nearpack = accu
        else:
            self._farpack = None
            self._nearpack, = accu
        self._neartime = 0.0
        if self._farpack:
            self._fartime = 0.0

        self._lodout_dist = loddistout
        self._lodout_alpha = loddistalpha
        self._lodout_pause_wait = 0.0
        self._lodout_pause_period = 0.917
        self._lodout_alpha_fac = 0.0
        self._active = True

        self.init_radius0 = self.radius0
        self.init_radius1 = self.radius1
        self.init_lifespan = self.lifespan
        self.init_color = Vec4(self.color)

        self.alive = True
        base.taskMgr.add(self._loop, "polytrail-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        apos = Point3()
        aquat = Quat()
        havepq = False
        if ((self.parent and self.parent.alive) or
            (self.pnode is not None and not self.pnode.isEmpty())):
            if self._active:
                havepq = True
                if self.parent and self.parent.alive:
                    apos = self.parent.pos(refbody=self.node, offset=self._pos)
                    aquat = self.parent.quat()
                else:
                    apos = self.node.getRelativePoint(self.pnode, self._pos)
                    aquat = self.pnode.getQuat(self.world.node)
            elif (not self._nearpack.any_visible() and
                  not (self._farpack and self._farpack.any_visible())):
                self.node.hide()
                return task.cont
        elif (not self._nearpack.any_visible() and
              not (self._farpack and self._farpack.any_visible())):
            self.destroy()
            return task.done

        if self._lodout_dist is not None:
            hidden = self.node.isHidden()
            lodapos = apos if havepq else self._nearpack.prev_apos()
            loddist = (self.world.camera.getPos(self.node) - lodapos).length()
            if self._lodout_pause_wait <= 0.0:
                if ((loddist > self._lodout_dist and not hidden) or
                    (loddist < self._lodout_dist and hidden)):
                    if not hidden:
                        self.node.hide()
                        hidden = True
                    else:
                        self.node.show()
                        hidden = False
                    self._lodout_pause_wait = self._lodout_pause_period
                    self._nearpack.clear(self.world.camera,
                                         havepq, apos, aquat)
                    if self._farpack:
                        self._farpack.clear(self.world.camera,
                                            havepq, apos, aquat)
                    self._neartime = 0.0
                    if self._farpack:
                        self._fartime = 0.0
            else:
                self._lodout_pause_wait -= dt
            if not hidden and self._lodout_alpha is not None:
                if loddist > self._lodout_alpha:
                    self._lodout_alpha_fac = intl10r(
                        loddist, self._lodout_alpha, self._lodout_dist)
                else:
                    self._lodout_alpha_fac = 0.0
            if hidden:
                return task.cont

        cleared_near = False
        camfw = self.world.camera.getQuat(self.node).getForward()
        dbpos = camfw * self._dbin
        bpos = (apos if havepq else self._nearpack.prev_apos()) + dbpos
        if self._farpack:
            self._fartime += dt
            if self._fartime >= self._farpack.seg_period():
                self._farpack.update(self.world.camera,
                                     self.lifespan, self._lodout_alpha_fac,
                                     self.radius0, self.radius1,
                                     self.color, self.colorend, self._tcol,
                                     bpos, havepq, apos, aquat,
                                     self._fartime)
                self._fartime = 0.0
                self._nearpack.clear(self.world.camera,
                                     havepq, apos, aquat)
                cleared_near = True
        self._neartime += dt
        if not cleared_near and self._neartime >= self._nearpack.seg_period():
            self._nearpack.update(self.world.camera,
                                  self.lifespan, self._lodout_alpha_fac,
                                  self.radius0, self.radius1,
                                  self.color, self.colorend, self._tcol,
                                  bpos, havepq, apos, aquat,
                                  self._neartime)
            self._neartime = 0.0

        return task.cont


    def set_active (self, active):

        if active != self._active:
            self._active = active
            if active:
                apos = None
                if self.parent and self.parent.alive:
                    apos = self.parent.pos(refbody=self.node, offset=self._pos)
                    aquat = self.parent.quat()
                elif self.pnode is not None and not self.pnode.isEmpty():
                    apos = self.node.getRelativePoint(self.pnode, self._pos)
                    aquat = self.pnode.getQuat(self.world.node)
                if apos is not None:
                    for tpack in (self._nearpack, self._farpack):
                        if tpack:
                            tpack.set_prev(apos, aquat)


# :also-compiled:
class PolyTrailGeom (object):

    def __init__ (self, numpoly, randcircle, segperiod,
                  apos, aquat, pnode):

        self._gen = MeshDrawer()
        self._gen.setBudget(numpoly)
        gnode = self._gen.getRoot()
        gnode.setDepthWrite(False)
        gnode.setTransparency(TransparencyAttrib.MAlpha)
        gnode.setTwoSided(True)
        gnode.reparentTo(pnode)

        self._randcircle = randcircle
        self._segperiod = segperiod
        self._segs = []
        self._prev_dang = 0.0
        self._prev_drad = 0.0
        self._prev_apos = apos
        self._prev_aquat = aquat


    def update (self, camera, lifespan, lodalfac,
                radius0, radius1, color, endcolor, tcol,
                bpos, havepq, apos, aquat, adt):

        if havepq:
            if apos != self._prev_apos:
                dang = self._prev_dang
                drad = self._prev_drad
                if self._randcircle > 0.0:
                    dang = fx_uniform(0.0, 2 * pi)
                    drad = sqrt(fx_randunit()) * self._randcircle
                self._segs.insert(0, [0.0,
                                      apos, self._prev_apos,
                                      dang, self._prev_dang,
                                      drad, self._prev_drad])
                self._prev_apos = apos
                self._prev_aquat = aquat
                self._prev_dang = dang
                self._prev_drad = drad
        elif self._segs:
            apos = self._prev_apos
            aquat = self._prev_aquat
        else:
            return

        color0 = Vec4(color)
        color1 = Vec4(endcolor)
        if lodalfac > 0.0:
            color0[3] *= lodalfac
            color1[3] *= lodalfac
        aup = aquat.getUp()
        art = aquat.getRight()
        tfac1 = tcol
        maxreach = 0.0
        gnode = self._gen.getRoot()
        gnode.setPos(bpos)
        self._gen.begin(camera, gnode)
        i = 0
        numsegs = len(self._segs)
        #needpoly = 0
        while i < numsegs:
            tseg = self._segs[i]
            ctime, ap0, ap1, da0, da1, dr0, dr1 = tseg
            if ctime < lifespan:
                ifac = ctime / lifespan
                p0 = Vec3(ap0 - bpos)
                p1 = Vec3(ap1 - bpos)
                frame = Vec4(0.0, 0.0, 1.0, 1.0)
                rad = radius0 + (radius1 - radius0) * ifac
                if ifac < tfac1:
                    color = color0 + (color1 - color0) * (ifac / tfac1)
                else:
                    color = Vec4(color1)
                color[3] *= (1.0 - ifac)
                p0l = p0 + art * (dr0 * cos(da0)) + aup * (dr0 * sin(da0))
                p1l = p1 + art * (dr1 * cos(da1)) + aup * (dr1 * sin(da1))
                self._gen.crossSegment(p0l, p1l, frame, rad, color)
                #needpoly += 4
                ctime += adt
                tseg[0] = ctime
                maxreach = max(maxreach, p0.length())
                i += 1
            else:
                self._segs.pop(i)
                numsegs -= 1
        self._gen.end()
        if numsegs > 0:
            gnode.node().setBounds(BoundingSphere(Point3(), maxreach))
            gnode.node().setFinal(True)


    def clear (self, camera, havepq, apos, aquat):

        self._segs = []
        self._gen.begin(camera, self._gen.getRoot())
        self._gen.end()
        self._prev_dang = 0.0
        self._prev_drad = 0.0
        if havepq:
            self._prev_apos = apos
            self._prev_aquat = aquat


    def node (self):

        return self._gen.getRoot()


    def any_visible (self):

        return len(self._segs) > 0


    def prev_apos (self):

        return self._prev_apos


    def prev_aquat (self):

        return self._prev_aquat


    def seg_period (self):

        return self._segperiod


    def set_prev (self, apos, aquat):

        self._prev_apos = apos
        self._prev_aquat = aquat


class PolyExhaust (object):

    def __init__ (self, parent, pos, radius0, radius1, length, speed,
                  poolsize, color,
                  subnode=None, colorend=None, tcol=1.0,
                  pdir=Vec3(0.0, -1.0, 0.0),
                  emradius=None, texture=None, glowmap=None,
                  ltpos=None,
                  ltcolor=Vec4(1, 1, 1, 1), ltcolor2=None,
                  ltradius=10.0, ltradius2=None, lthalfat=0.5,
                  ltpulse=0.0, ltoff=False,
                  obpos=None,
                  obcolor=Vec4(1, 1, 1, 1), obcolor2=None,
                  obradius=10.0, obradius2=None, obhalfat=0.5,
                  obpulse=0.0,
                  frameskip=2, dbin=0.0,
                  freezedist=200.0, hidedist=2000.0,
                  loddirang=None, loddirskip=3,
                  delay=0.0):

        if isinstance(parent, tuple):
            self.parent = None
            parent_node, self.world = parent
        else:
            self.world = parent.world
            self.parent = parent
            parent_node = parent.node

        self.pos = pos
        self.radius0 = float(radius0)
        self.radius1 = float(radius1)
        self.length = float(length)
        self.speed = float(speed)
        self.poolsize = int(poolsize)
        self.subnode = subnode
        self.color = Vec4(color)
        self.colorend = Vec4(colorend if colorend is not None else color)
        self.tcol = float(tcol)
        self.pdir = pdir
        self.emradius = float(emradius or 0.0)
        self.frameskip = int(frameskip or 0)
        self.freezedist = float(freezedist)
        self.hidedist = float(hidedist)
        self.dbin = float(dbin)

        self._ltcolor = ltcolor
        self._ltcolor2 = ltcolor2 if ltcolor2 is not None else ltcolor
        self._ltradius = ltradius
        self._ltradius2 = ltradius2 if ltradius2 is not None else ltradius
        if ltpulse is True:
            ltpulse = 0.010
        self._ltpulse_rate = ltpulse
        self._ltpulse_wait = 0.0

        self._obcolor = obcolor
        self._obcolor2 = obcolor2 if obcolor2 is not None else obcolor
        self._obradius = obradius
        self._obradius2 = obradius2 if obradius2 is not None else obradius
        if obpulse is True:
            obpulse = 0.010
        self._obpulse_rate = obpulse
        self._obpulse_wait = 0.0

        self._pnode = self.subnode or parent_node
        self._prev_pnode_pos = self._pnode.getPos(self.world.node)

        self.node = None
        self._snode = None
        self._light = None
        self._overbright = None

        self._emskip = 1
        self._emskip_count = 0
        self._loddir_ang = radians(loddirang) if loddirang else None
        self._loddir_skip = loddirskip
        self._loddir_pause_wait = 0.0
        self._loddir_pause_period = 0.433

        self.node = self.world.node.attachNewNode("polyexhaust-root")
        self.node.setAntialias(AntialiasAttrib.MNone)

        def start ():

            self._geom = PolyExhaustGeom(self.node, self.poolsize)

            glowmap1 = glowmap
            if isinstance(glowmap1, Vec4):
                glow = glowmap1
                glowmap1 = None
            else:
                glow = (glowmap1 is not None)
            ambln = self.world.shdinp.ambsmln if not ltoff else None
            shader = make_shader(ambln=ambln, glow=glow, modcol=True) #, selfalpha=True)
            self.node.setShader(shader)
            set_texture(self.node, texture=texture, glowmap=glowmap1)

            self.node.reparentTo(self._pnode)
            self.node.setPos(self.pos)

            self.world.add_altbin_node(self.node)

            if ltpos is not None and self.parent:
                self.light_cscale = 1.0
                self._prev_light_cscale = None
                self._light = AutoPointLight(
                    parent=self.parent, color=ltcolor,
                    radius=ltradius, halfat=lthalfat,
                    pos=ltpos, name="exhaust")
                self._light_color = ltcolor

            if obpos is not None and self.parent:
                self._overbright = PointOverbright(
                    parent=self.parent, color=obcolor,
                    radius=obradius, halfat=obhalfat,
                    pos=obpos, name="exhaust")
                self.parent.node.setShaderInput(self.world.shdinp.pntobrn,
                                                self._overbright.node)

        self._waitframe = 0
        self._waittime = 0.0
        self._time0 = self.world.time

        self.init_radius0 = self.radius0
        self.init_radius1 = self.radius1
        self.init_length = self.length
        self.init_speed = self.speed
        self.init_color = Vec4(self.color)

        self._last_apos = self.world.node.getRelativePoint(self._pnode, self.pos)
        self._last_aquat = self._pnode.getQuat(self.world.node)
        self._last_pdir = pdir

        self._end = False

        self._start = start
        if delay > 0.0:
            self._wait_delay = delay
        else:
            self._wait_delay = None
            self._start()

        self.alive = True
        base.taskMgr.add(self._loop, "polyexhaust-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self._light:
            self._light.destroy()
        if self._overbright:
            if not self.parent.node.isEmpty():
                self.parent.node.clearShaderInput(self.world.shdinp.pntobrn)
            self._overbright.destroy()
        if self.node is not None:
            self.node.removeNode()
        if self._snode is not None:
            self._snode.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        parent_alive = ((not self.parent or self.parent.alive) and
                        not self._pnode.isEmpty())

        if self._wait_delay is not None:
            self._wait_delay -= dt
            if self._wait_delay <= 0.0:
                if not parent_alive:
                    self.destroy()
                    return task.done
                self._start()
                self._wait_delay = None
            else:
                return task.cont

        if parent_alive:
            self._last_apos = self.world.node.getRelativePoint(self._pnode, self.pos)
            self._last_aquat = self._pnode.getQuat(self.world.node)
        elif self._snode is None:
            self._snode = self.world.node.attachNewNode("polyexhaust-parent")
            self._snode.setPos(self._last_apos)
            self._snode.setQuat(self._last_aquat)
            self.node.wrtReparentTo(self._snode)

        if self._light is not None:
            if self._prev_light_cscale != self.light_cscale:
                self._prev_light_cscale = self.light_cscale
                color = self._light_color * self.light_cscale
                self._light.update(color=color)
            if self._ltpulse_rate:
                self._ltpulse_wait -= self.world.dt
                if self._ltpulse_wait < 0.0:
                    self._ltpulse_wait += self._ltpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._ltcolor + (self._ltcolor2 - self._ltcolor) * ifac
                    radius = self._ltradius + (self._ltradius2 - self._ltradius) * ifac
                    self._light.update(color=color, radius=radius)

        if self._overbright:
            if self._obpulse_rate:
                self._obpulse_wait -= self.world.dt
                if self._obpulse_wait < 0.0:
                    self._obpulse_wait += self._obpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._obcolor + (self._obcolor2 - self._obcolor) * ifac
                    radius = self._obradius + (self._obradius2 - self._obradius) * ifac
                    self._overbright.update(color=color, radius=radius)

        lifespan = self.length / max(self.speed, 1e-3)

        if self.world.time - self._time0 > lifespan and parent_alive:
            # ...if parent is not alive, proper cleanup is needed.
            self.node.show()
            if is_on_screen(self.world.camera, self.node):
                cdist = self.node.getDistance(self.world.camera)
                if cdist > self.freezedist:
                    if cdist > self.hidedist:
                        self.node.hide()
                    return task.cont
            else:
                self.node.hide()
                return task.cont

        self._waittime += dt
        self._waitframe += 1
        if self._waitframe < self.frameskip:
            return task.cont

        pdir = self.pdir
        if pdir is None:
            if parent_alive:
                if self.parent:
                    pvel = self.parent.vel()
                else:
                    pnode_pos = self._pnode.getPos(self.world.node)
                    pvel = (pnode_pos - self._prev_pnode_pos) / (dt + 1e-6)
                    self._prev_pnode_pos = pnode_pos
                rpvel = self._pnode.getRelativeVector(self.world.node, pvel)
                pdir = -unitv(rpvel)
            elif self._last_pdir is not None:
                pdir = self._last_pdir
            else:
                pdir = Vec3(0, -1, 0)
        self._last_pdir = pdir

        camfw = self.world.camera.getQuat(self.node.getParent()).getForward()
        if self._loddir_ang is not None:
            if self._loddir_pause_wait <= 0.0:
                self._loddir_pause_wait = self._loddir_pause_period
                if self._geom.num_particles() >= 2:
                    bdir = unitv(self._geom.chord(pdir))
                    bcang = acos(clamp(camfw.dot(bdir), -1.0, 1.0))
                    if bcang > 0.5 * pi:
                        bcang = pi - bcang
                    self._emskip = int(intl01vr(bcang, 0.0, self._loddir_ang,
                                                self._loddir_skip, 1))
                else:
                    self._emskip = 1
            else:
                self._loddir_pause_wait -= self._waittime

        dbpos = camfw * self.dbin
        cont = self._geom.update(self.world.camera,
                                 parent_alive, self._end, pdir,
                                 lifespan, self.speed, self.emradius,
                                 self.radius0, self.radius1,
                                 self.color, self.colorend, self.tcol,
                                 dbpos, self._emskip,
                                 self._waittime)
        if not cont:
            self.destroy()
            return task.done

        self._waitframe = 0
        self._waittime = 0.0

        return task.cont


    def end (self):

        self._end = True


# :also-compiled:
class PolyExhaustGeom (object):

    def __init__ (self, pnode, poolsize):

        self._poolsize = poolsize

        self._gen = MeshDrawer()
        self._gen.setBudget(self._poolsize * 4)
        gnode = self._gen.getRoot()
        gnode.setDepthWrite(False)
        gnode.setTransparency(TransparencyAttrib.MAlpha)
        #gnode.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        gnode.setTwoSided(True)
        gnode.reparentTo(pnode)

        self._emittime = 0.0
        self._emskip_count = 0

        self._particles = []


    def update (self, camera, palive, sigend, pdir,
                lifespan, speed, emradius,
                radius0, radius1, color0, color1, tcol,
                dbpos, emskip, adt):

        if emradius > 0.0:
            ndir = pdir.cross(Vec3(0, 0, 1))
            if ndir.normalize() == 0.0:
                ndir = Vec3(1, 0, 0)

        if palive and not sigend:
            self._emittime += adt
            while self._emittime >= 0.0:
                pos0 = Vec3()
                if emradius > 0.0:
                    ang = fx_uniform(0.0, 2 * pi)
                    q = Quat()
                    q.setFromAxisAngleRad(ang, pdir)
                    rad = sqrt(fx_randunit()) * emradius
                    pos0 += Vec3(q.xform(ndir)) * rad
                self._emskip_count += 1
                if self._emskip_count >= emskip:
                    self._emskip_count = 0
                    dist = speed * self._emittime
                    dist -= speed * adt # will be added below
                    self._particles.insert(0, [pos0, dist, self._emittime])
                birthrate = lifespan / self._poolsize
                self._emittime -= birthrate

        elif not self._particles:
            return False

        tfac0 = 0.0
        tfac1 = tcol
        dcolor = color1 - color0
        self._gen.begin(camera, self._gen.getRoot())
        for i in xrange(len(self._particles)):
            tseg = self._particles[i]
            pos0, dist, ctime = tseg
            if ctime >= lifespan:
                for j in xrange(i, len(self._particles)):
                    self._particles.pop()
                break
            ifac = clamp(ctime / lifespan, 0.0, 1.0)
            ifac1 = clamp((ifac - tfac0) / (tfac1 - tfac0), 0.0, 1.0)
            color = color0 + dcolor * ifac1
            color[3] = color0[3] * (1.0 - ifac)
            radius = radius0 + (radius1 - radius0) * ifac
            frame = Vec4(0.0, 0.0, 1.0, 1.0)
            pos = pos0 + pdir * dist - dbpos
            self._gen.billboard(Vec3(pos), frame, radius, color)
            ctime += adt
            dist += speed * adt
            tseg[1] = dist
            tseg[2] = ctime
        self._gen.end()
        #print_each(1043, 0.5, "--exhaust", len(self._particles))

        if len(self._particles) > 0:
            maxreach = speed * lifespan * 1.2
            gnode = self._gen.getRoot()
            gnode.node().setBounds(BoundingSphere(Point3(), maxreach))
            gnode.node().setFinal(True)

        return True


    def num_particles (self):

        return len(self._particles)


    def chord (self, pdir):

        pos0a, dista = self._particles[0][:2]
        pos0b, distb = self._particles[-1][:2]
        posa = pos0a + pdir * dista
        posb = pos0b + pdir * distb
        chord = posa - posb
        return chord


class PolyBraid (object):

    def __init__ (self, parent, pos, numstrands, lifespan, thickness, texture,
                  segperiod=0.005, farsegperiod=0.100,
                  maxpoly=2000, farmaxpoly=2000,
                  endthickness=None, spacing=0.5,
                  color=Vec4(1, 1, 1, 1), endcolor=None,
                  tcol=1.0, alphaexp=2.0,
                  offang=None, offrad=None, offtang=None,
                  randang=None, randrad=None,
                  glowmap=None, dirlit=False,
                  ltpos=None,
                  ltcolor=Vec4(1, 1, 1, 1), ltcolor2=None,
                  ltradius=10.0, ltradius2=None, lthalfat=0.5,
                  ltpulse=0.0,
                  obpos=None,
                  obcolor=Vec4(1, 1, 1, 1), obcolor2=None,
                  obradius=10.0, obradius2=None, obhalfat=0.5,
                  obpulse=0.0,
                  texsplit=None, numframes=None,
                  dbin=0, loddistout=None, loddistalpha=None,
                  loddirang=None, loddirspcfac=10.0,
                  delay=0.0, partvel=Vec3(0, 0, 0),
                  emittang=Vec3(0, -1, 0), emitnorm=Vec3(1, 0, 0)):

        if isinstance(parent, tuple):
            self.pnode, other = parent
            if hasattr(other, "world"):
                # FIXME: The question is actually isinstance(other, Body),
                # but not possible to import Body due to order of imports.
                self.parent = other
                self.world = self.parent.world
            else:
                self.parent = None
                self.world = other
        else:
            self.world = parent.world
            self.parent = parent
            self.pnode = parent.node

        self.node = self.world.node.attachNewNode("polybraid-root")
        self.node.setAntialias(AntialiasAttrib.MNone)
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)
        #self.node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        if dirlit:
            ambln = self.world.shdinp.ambln
            dirlns = self.world.shdinp.dirlns
        else:
            ambln = self.world.shdinp.ambsmln
            dirlns = []
        shader = make_shader(ambln=ambln, dirlns=dirlns,
                             glow=glow, modcol=True) #, selfalpha=True)
        self.node.setShader(shader)

        self._pos = pos
        self._lifespan = lifespan
        self._dbin = dbin

        self._ltcolor = ltcolor
        self._ltcolor2 = ltcolor2 if ltcolor2 is not None else ltcolor
        self._ltradius = ltradius
        self._ltradius2 = ltradius2 if ltradius2 is not None else ltradius
        if ltpulse is True:
            ltpulse = 0.010
        self._ltpulse_rate = ltpulse
        self._ltpulse_wait = 0.0

        self._obcolor = obcolor
        self._obcolor2 = obcolor2 if obcolor2 is not None else obcolor
        self._obradius = obradius
        self._obradius2 = obradius2 if obradius2 is not None else obradius
        if obpulse is True:
            obpulse = 0.010
        self._obpulse_rate = obpulse
        self._obpulse_wait = 0.0

        self._lodout_dist = loddistout
        self._lodout_alpha = loddistalpha
        self._lodout_pause_wait = 0.0
        self._lodout_pause_period = 0.917
        self._lodout_alpha_fac = 0.0

        self._loddir_ang = radians(loddirang) if loddirang else None
        self._loddir_spacing_fac = loddirspcfac
        self._loddir_pause_wait = 0.0
        self._loddir_pause_period = 0.433

        self._light = None
        self._overbright = None

        def gv (spec, i, default=(None,)):
            if isinstance(spec, (tuple, list)):
                return spec[i]
            elif spec is not None:
                return spec
            elif default != (None,):
                return default
            else:
                raise StandardError("Value cannot be resolved.")

        def start ():
            if farsegperiod and farsegperiod > segperiod:
                pspec = ((farmaxpoly, farsegperiod), (maxpoly, segperiod))
            else:
                pspec = ((maxpoly, segperiod),)
            self.node.setPos(self.pnode.getPos(self.world.node))
            apos = self.node.getRelativePoint(self.pnode, self._pos)
            aquat = self.pnode.getQuat(self.world.node)
            self._braids = []
            for npoly, segp in pspec:
                braid = PolyBraidGeom(segp, partvel, emittang, emitnorm,
                                      apos, aquat)
                for i in range(numstrands):
                    snode = braid.add_strand(
                        gv(thickness, i),
                        gv(endthickness, i, gv(thickness, i)),
                        gv(spacing, i),
                        gv(offang, i, 0.0),
                        gv(offrad, i, 0.0),
                        gv(offtang, i, 0.0),
                        gv(randang, i, 0.0),
                        gv(randrad, i, 0.0),
                        gv(color, i),
                        gv(endcolor, i, gv(color, i)),
                        gv(tcol, i),
                        gv(alphaexp, i),
                        gv(texsplit, i, 0),
                        gv(numframes, i, 0),
                        npoly,
                        self.node)
                    set_texture(snode,
                        texture=gv(texture, i),
                        glowmap=gv(glowmap, i, None))
                    self.world.add_altbin_node(snode)
                self._braids.append(braid)
            if len(self._braids) == 2:
                self._farbraid, self._nearbraid = self._braids
            else:
                self._farbraid = None
                self._nearbraid, = self._braids
            self._neartime = 0.0
            if self._farbraid:
                self._fartime = 0.0

            if ltpos is not None and self.parent:
                self._light = AutoPointLight(
                    parent=self.parent, color=ltcolor,
                    radius=ltradius, halfat=lthalfat,
                    pos=ltpos, name="polybraid")

            if obpos is not None and self.parent:
                self._overbright = PointOverbright(
                    parent=self.parent, color=obcolor,
                    radius=obradius, halfat=obhalfat,
                    pos=obpos, name="polybraid")
                self.parent.node.setShaderInput(self.world.shdinp.pntobrn,
                                                self._overbright.node)

        self._start = start
        if delay > 0.0:
            self._wait_delay = delay
        else:
            self._wait_delay = None
            self._start()

        self.alive = True
        base.taskMgr.add(self._loop, "polybraid-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self._light:
            self._light.destroy()
        if self._overbright:
            if not self.parent.node.isEmpty():
                self.parent.node.clearShaderInput(self.world.shdinp.pntobrn)
            self._overbright.destroy()
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        if self._wait_delay is not None:
            self._wait_delay -= dt
            if self._wait_delay <= 0.0:
                if self.pnode.isEmpty():
                    self.destroy()
                    return task.done
                self._start()
                self._wait_delay = None
            else:
                return task.cont

        apos = Point3()
        aquat = Quat()
        havepq = False
        if not self.pnode.isEmpty():
            apos = self.node.getRelativePoint(self.pnode, self._pos)
            aquat = self.pnode.getQuat(self.world.node)
            havepq = True
        elif (not self._nearbraid.any_visible() and
              not (self._farbraid and self._farbraid.any_visible())):
            self.destroy()
            return task.done

        if self._lodout_dist is not None:
            hidden = self.node.isHidden()
            lodapos = apos if havepq else self._nearbraid.prev_apos()
            loddist = (self.world.camera.getPos(self.node) - lodapos).length()
            if self._lodout_pause_wait <= 0.0:
                if ((loddist > self._lodout_dist and not hidden) or
                    (loddist < self._lodout_dist and hidden)):
                    if not hidden:
                        self.node.hide()
                        hidden = True
                    else:
                        self.node.show()
                        hidden = False
                    self._lodout_pause_wait = self._lodout_pause_period
                    self._nearbraid.clear(self.world.camera,
                                          havepq, apos, aquat)
                    if self._farbraid:
                        self._farbraid.clear(self.world.camera,
                                             havepq, apos, aquat)
                    self._neartime = 0.0
                    if self._farbraid:
                        self._fartime = 0.0
            else:
                self._lodout_pause_wait -= dt
            if not hidden and self._lodout_alpha is not None:
                if loddist > self._lodout_alpha:
                    self._lodout_alpha_fac = intl10r(
                        loddist, self._lodout_alpha, self._lodout_dist)
                else:
                    self._lodout_alpha_fac = 0.0
            if hidden:
                return task.cont

        if self._loddir_ang is not None:
            if self._loddir_pause_wait <= 0.0:
                self._loddir_pause_wait = self._loddir_pause_period
                cquat = self.world.camera.getQuat(self.world.node)
                cdir = cquat.getForward()
                for braid in self._braids:
                    if not braid.any_visible():
                        continue
                    ap1 = braid.start_point()
                    ap2 = braid.end_point()
                    bdir = unitv(ap1 - ap2)
                    bcang = acos(clamp(cdir.dot(bdir), -1.0, 1.0))
                    if bcang > 0.5 * pi:
                        bcang = pi - bcang
                    spfac = intl01vr(bcang, 0.0, self._loddir_ang,
                                     self._loddir_spacing_fac, 1.0)
                    braid.multiply_init_dtang(spfac)
            else:
                self._loddir_pause_wait -= dt

        cleared_near = False
        camfw = self.world.camera.getQuat(self.node).getForward()
        dbpos = camfw * self._dbin
        bpos = (apos if havepq else self._nearbraid.prev_apos()) + dbpos
        if self._farbraid:
            self._fartime += dt
            if self._fartime >= self._farbraid.seg_period():
                self._farbraid.update(self.world.camera,
                                      self._lifespan, self._lodout_alpha_fac,
                                      bpos, havepq, apos, aquat, self._fartime)
                self._fartime = 0.0
                self._nearbraid.clear(self.world.camera,
                                      havepq, apos, aquat)
                cleared_near = True
        self._neartime += dt
        if not cleared_near and self._neartime >= self._nearbraid.seg_period():
            self._nearbraid.update(self.world.camera,
                                   self._lifespan, self._lodout_alpha_fac,
                                   bpos, havepq, apos, aquat, self._neartime)
            self._neartime = 0.0

        if self._light:
            if self._ltpulse_rate:
                self._ltpulse_wait -= self.world.dt
                if self._ltpulse_wait < 0.0:
                    self._ltpulse_wait += self._ltpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._ltcolor + (self._ltcolor2 - self._ltcolor) * ifac
                    radius = self._ltradius + (self._ltradius2 - self._ltradius) * ifac
                    self._light.update(color=color, radius=radius)

        if self._overbright:
            if self._obpulse_rate:
                self._obpulse_wait -= self.world.dt
                if self._obpulse_wait < 0.0:
                    self._obpulse_wait += self._obpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._obcolor + (self._obcolor2 - self._obcolor) * ifac
                    radius = self._obradius + (self._obradius2 - self._obradius) * ifac
                    self._overbright.update(color=color, radius=radius)

        return task.cont


# :also-compiled:
class PolyBraidGeom (object):

    def __init__ (self, segperiod, partvel, emittang, emitnorm, apos, aquat):

        self._strands = []
        self._segs = []
        self._segperiod = segperiod
        self._partvel = partvel
        self._prev_apos = apos
        self._prev_aquat = aquat

        self._emittang = unitv(emittang)
        self._emitnorm = unitv(emitnorm)
        self._emitnorm = unitv(self._emitnorm - self._emittang * self._emitnorm.dot(self._emittang))
        self._emitbnrm = unitv(self._emittang.cross(self._emitnorm))


    def add_strand (self, thickness, endthickness, spacing,
                    offang, offrad, offtang, randang, randrad,
                    color, endcolor, tcol, alphaexp,
                    texsplit, numframes,
                    maxpoly, pnode):

        if numframes == 0:
            numframes = texsplit**2

        strand = SimpleProps()
        self._strands.append(strand)

        strand.thickness = thickness
        strand.endthickness = endthickness
        strand.spacing = spacing
        strand.offang = offang
        strand.offrad = offrad
        strand.offtang = offtang
        strand.randang = randang
        strand.randrad = randrad
        strand.color = color
        strand.endcolor = endcolor
        strand.tcol = tcol
        strand.alphaexp = alphaexp
        strand.texsplit = texsplit
        strand.numframes = numframes

        strand.gen = MeshDrawer()
        strand.gen.setBudget(maxpoly)
        strand.node = strand.gen.getRoot()
        strand.node.setDepthWrite(False)
        strand.node.setTransparency(TransparencyAttrib.MAlpha)
        strand.node.reparentTo(pnode)

        strand.dtang = strand.thickness * strand.spacing * 2
        strand.dtang0 = -strand.offtang * strand.dtang
        strand.dang0 = radians(strand.offang)
        strand.drad0 = strand.offrad
        strand.segs = []
        strand.prev_dang = strand.dang0
        strand.prev_drad = strand.drad0
        strand.init_dtang = strand.dtang

        return strand.node


    def update (self, camera, lifespan, lodalfac, bpos,
                havepq, apos, aquat, adt):

        ddtang0 = 0.0
        if havepq:
            prev_apos_pv = self._prev_apos + self._partvel * adt
            dpos = apos - prev_apos_pv
            ddtang0 = dpos.length()
            if ddtang0 > 0.0:
                bseg = SimpleProps(ctime=0.0, apos0=apos, apos1=prev_apos_pv)
                self._segs.insert(0, bseg)
                self._prev_apos = apos
                self._prev_aquat = aquat
                for strand in self._strands:
                    dang = strand.prev_dang
                    if strand.randang:
                        dang = fx_uniform(0.0, 2 * pi)
                    drad = strand.prev_drad
                    if strand.randrad:
                        drad = sqrt(fx_randunit()) * strand.drad0
                    sseg = SimpleProps(dang=dang, prev_dang=strand.prev_dang,
                                       drad=drad, prev_drad=strand.prev_drad)
                    strand.segs.insert(0, sseg)
                    strand.prev_dang = dang
                    strand.prev_drad = drad
        elif self._segs:
            apos = self._prev_apos
            aquat = self._prev_aquat
        else:
            return

        maxreach = 0.0
        for strand in self._strands:
            strand.node.setPos(bpos)
            strand.gen.begin(camera, strand.node)
            strand.numpart = 0
            strand.dtang0 -= ddtang0
            while strand.dtang0 < -strand.init_dtang:
                strand.dtang0 += strand.init_dtang
            strand.color0 = Vec4(strand.color)
            strand.color1 = Vec4(strand.endcolor)
            if lodalfac > 0.0:
                strand.color0[3] *= lodalfac
                strand.color1[3] *= lodalfac
        i = 0
        atang = unitv(Vec3(aquat.xform(self._emittang)))
        anorm = unitv(Vec3(aquat.xform(self._emitnorm)))
        abnrm = unitv(Vec3(aquat.xform(self._emitbnrm)))
        numsegs = len(self._segs)
        needpoly = 0
        clen = 0.0
        while i < numsegs:
            bseg = self._segs[i]
            if bseg.ctime < lifespan:
                ifac = bseg.ctime / lifespan
                p0, p1 = Vec3(bseg.apos0 - bpos), Vec3(bseg.apos1 - bpos)
                dlen = (p1 - p0).length()
                for strand in self._strands:
                    np0 = strand.numpart
                    spc = strand.dtang
                    np1 = int(floor((clen + dlen) / spc) + 1)
                    dnp = np1 - np0
                    if dnp > 0:
                        #ds = strand.dtang0
                        ds = 0.0
                        sseg = strand.segs[i]
                        da0, da1 = sseg.dang, sseg.prev_dang
                        dr0, dr1 = sseg.drad, sseg.prev_drad
                        p0l = p0 + anorm * (dr0 * cos(da0)) - atang * ds + abnrm * (dr0 * sin(da0))
                        p1l = p1 + anorm * (dr1 * cos(da1)) - atang * ds + abnrm * (dr1 * sin(da1))
                        ro0 = (0.0 + np0 * spc - clen) / dlen
                        dpl = p1l - p0l
                        p0l1 = p0l + dpl * ro0
                        dlen1 = dnp * spc
                        dpl1 = dpl * (dlen1 / dlen)
                        p1l1 = p0l1 + dpl1
                        thck0, thck1 = strand.thickness, strand.endthickness
                        thck = thck0 + (thck1 - thck0) * ifac
                        col0, col1 = strand.color0, strand.color1
                        tfac1 = strand.tcol
                        if ifac < tfac1:
                            col = col0 + (col1 - col0) * (ifac / tfac1)
                        else:
                            col = Vec4(col1)
                        alexp = strand.alphaexp
                        col[3] *= (1.0 - ifac)**alexp
                        if strand.texsplit > 0:
                            dcoord = 1.0 / strand.texsplit
                            frind = int(strand.numframes * ifac)
                            uind = frind % strand.texsplit
                            vind = frind // strand.texsplit
                            uoff = uind  * dcoord
                            voff = 1.0 - (vind + 1) * dcoord
                            frame = Vec4(uoff, voff, dcoord, dcoord)
                        else:
                            frame = Vec4(0.0, 0.0, 1.0, 1.0)
                        strand.gen.stream(p0l1, p1l1, frame, thck, col, dnp, 0.0)
                        needpoly += dnp * 2
                    strand.numpart = np1
                bseg.ctime += adt
                bseg.apos0 += self._partvel * adt
                bseg.apos1 += self._partvel * adt
                clen += dlen
                maxreach = max(maxreach, p1.length())
                i += 1
            else:
                self._segs.pop(i)
                for strand in self._strands:
                    strand.segs.pop(i)
                numsegs -= 1
        for strand in self._strands:
            strand.gen.end()
            if numsegs > 0:
                strand.node.node().setBounds(BoundingSphere(Point3(), maxreach))
                strand.node.node().setFinal(True)


    def clear (self, camera, havepq, apos, aquat):

        self._segs = []
        for strand in self._strands:
            strand.gen.begin(camera, strand.node)
            strand.gen.end()
            strand.segs = []
            strand.prev_dang = strand.dang0
            strand.prev_drad = strand.drad0
        if havepq:
            self._prev_apos = apos
            self._prev_aquat = aquat


    def any_visible (self):

        return len(self._segs) > 0


    def prev_apos (self):

        return self._prev_apos


    def prev_aquat (self):

        return self._prev_aquat


    def start_point (self):

        return self._segs[0].apos0


    def end_point (self):

        return self._segs[-1].apos1


    def seg_period (self):

        return self._segperiod


    def multiply_init_dtang (self, spfac):

        for strand in self._strands:
            strand.dtang = strand.init_dtang * spfac


class PolyBurn (object):

    def __init__ (self, parent, pos, lifespan, thickness,
                  emitradius, emitspeed, texture,
                  numstrands=1, maxpoly=2000,
                  endthickness=None, spacing=0.5, offtang=0.0,
                  color=Vec4(1, 1, 1, 1), endcolor=None,
                  tcol=1.0, alphaexp=2.0,
                  glowmap=None, dirlit=False,
                  ltpos=None,
                  ltcolor=Vec4(1, 1, 1, 1), ltcolor2=None,
                  ltradius=10.0, ltradius2=None, lthalfat=0.5,
                  ltpulse=0.0,
                  obpos=None,
                  obcolor=Vec4(1, 1, 1, 1), obcolor2=None,
                  obradius=10.0, obradius2=None, obhalfat=0.5,
                  obpulse=0.0,
                  texsplit=None, numframes=None,
                  frameskip=2, dbin=0.0,
                  delay=0.0, duration=None):

        if isinstance(parent, tuple):
            self.pnode, other = parent
            if hasattr(other, "world"):
                # FIXME: The question is actually isinstance(other, Body),
                # but not possible to import Body due to order of imports.
                self.parent = other
                self.world = self.parent.world
            else:
                self.parent = None
                self.world = other
        else:
            self.world = parent.world
            self.parent = parent
            self.pnode = parent.node

        self.node = self.world.node.attachNewNode("polyburn-root")
        self.node.setAntialias(AntialiasAttrib.MNone)
        if isinstance(glowmap, Vec4):
            glow = glowmap
            glowmap = None
        else:
            glow = (glowmap is not None)
        #self.node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        if dirlit:
            ambln = self.world.shdinp.ambln
            dirlns = self.world.shdinp.dirlns
        else:
            ambln = self.world.shdinp.ambsmln
            dirlns = []
        shader = make_shader(ambln=ambln, dirlns=dirlns,
                             glow=glow, modcol=True) #, selfalpha=True)
        self.node.setShader(shader)

        self._pos = pos
        self._lifespan = lifespan
        self._frameskip = frameskip
        self._dbin = dbin

        self._ltcolor = ltcolor
        self._ltcolor2 = ltcolor2 if ltcolor2 is not None else ltcolor
        self._ltradius = ltradius
        self._ltradius2 = ltradius2 if ltradius2 is not None else ltradius
        if ltpulse is True:
            ltpulse = 0.010
        self._ltpulse_rate = ltpulse
        self._ltpulse_wait = 0.0

        self._obcolor = obcolor
        self._obcolor2 = obcolor2 if obcolor2 is not None else obcolor
        self._obradius = obradius
        self._obradius2 = obradius2 if obradius2 is not None else obradius
        if obpulse is True:
            obpulse = 0.010
        self._obpulse_rate = obpulse
        self._obpulse_wait = 0.0

        self._light = None
        self._overbright = None

        def gv (spec, i, default=(None,)):
            if isinstance(spec, (tuple, list)):
                return spec[i]
            elif spec is not None:
                return spec
            elif default != (None,):
                return default
            else:
                raise StandardError("Value cannot be resolved.")

        def start ():
            self.node.setPos(self.pnode.getPos(self.world.node))
            apos = self.node.getRelativePoint(self.pnode, self._pos)
            aquat = self.pnode.getQuat(self.world.node)
            self._geom = PolyBurnGeom(apos, aquat)
            for i in range(numstrands):
                emitspec = gv(emitradius, i)
                if isinstance(emitspec, tuple):
                    emitname = emitspec[0]
                    if emitname == "circle":
                        emittype = 0
                        radius, = emitspec[1:]
                        emitparam1 = Vec4(radius, 0.0, 0.0, 0.0)
                    elif emitname == "yaxis":
                        emittype = 1
                        ymin, ymax, width = emitspec[1:]
                        emitparam1 = Vec4(ymin, ymax, width, 0.0)
                    elif emitname == "xaxis":
                        emittype = 2
                        xmin, xmax, width = emitspec[1:]
                        emitparam1 = Vec4(xmin, xmax, width, 0.0)
                    else:
                        raise StandardError("Unknown emission type '%s'." % emitname)
                else:
                    emittype = 0
                    radius = emitspec
                    emitparam1 = Vec4(radius, 0.0, 0.0, 0.0)
                snode = self._geom.add_strand(
                    gv(thickness, i),
                    gv(endthickness, i, gv(thickness, i)),
                    emittype,
                    emitparam1,
                    gv(emitspeed, i),
                    gv(spacing, i),
                    gv(offtang, i),
                    gv(color, i),
                    gv(endcolor, i, gv(color, i)),
                    gv(tcol, i),
                    gv(alphaexp, i),
                    gv(texsplit, i, 0),
                    gv(numframes, i, 0),
                    gv(maxpoly, i),
                    self.node)
                set_texture(snode,
                    texture=gv(texture, i),
                    glowmap=gv(glowmap, i, None))
                self.world.add_altbin_node(snode)

            self._wait_update = 0.0
            self._wait_update_frame = 0

            if ltpos is not None and self.parent:
                self._light = AutoPointLight(
                    parent=self.parent, color=ltcolor,
                    radius=ltradius, halfat=lthalfat,
                    pos=ltpos, name="polyburn")

            if obpos is not None and self.parent:
                self._overbright = PointOverbright(
                    parent=self.parent, color=obcolor,
                    radius=obradius, halfat=obhalfat,
                    pos=obpos, name="polyburn")
                self.parent.node.setShaderInput(self.world.shdinp.pntobrn,
                                                self._overbright.node)

        self._start = start
        if delay > 0.0:
            self._wait_delay = delay
        else:
            self._wait_delay = None
            self._start()

        self._wait_remove = duration

        self.alive = True
        base.taskMgr.add(self._loop, "polyburn-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        if self._light:
            self._light.destroy()
        if self._overbright:
            if not self.parent.node.isEmpty():
                self.parent.node.clearShaderInput(self.world.shdinp.pntobrn)
            self._overbright.destroy()
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt

        if self._wait_delay is not None:
            self._wait_delay -= dt
            if self._wait_delay <= 0.0:
                if self.pnode.isEmpty():
                    self.destroy()
                    return task.done
                self._start()
                self._wait_delay = None
            else:
                return task.cont

        if self._wait_remove is not None:
            self._wait_remove -= dt

        apos = Point3()
        aquat = Quat()
        havepq = False
        if (not self.pnode.isEmpty() and
            (self._wait_remove is None or self._wait_remove > 0.0)):
            apos = self.node.getRelativePoint(self.pnode, self._pos)
            aquat = self.pnode.getQuat(self.world.node)
            havepq = True
        elif not self._geom.any_visible():
            self.destroy()
            return task.done

        cleared_near = False
        camfw = self.world.camera.getQuat(self.node).getForward()
        dbpos = camfw * self._dbin
        bpos = (apos if havepq else self._geom.prev_apos()) + dbpos
        self._wait_update += dt
        self._wait_update_frame += 1
        if self._wait_update_frame >= self._frameskip:
            self._geom.update(self.world.camera, self._lifespan,
                              bpos, havepq, apos, aquat, self._wait_update)
            self._wait_update = 0.0
            self._wait_update_frame = 0

        if self._light:
            if self._ltpulse_rate:
                self._ltpulse_wait -= self.world.dt
                if self._ltpulse_wait < 0.0:
                    self._ltpulse_wait += self._ltpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._ltcolor + (self._ltcolor2 - self._ltcolor) * ifac
                    radius = self._ltradius + (self._ltradius2 - self._ltradius) * ifac
                    self._light.update(color=color, radius=radius)

        if self._overbright:
            if self._obpulse_rate:
                self._obpulse_wait -= self.world.dt
                if self._obpulse_wait < 0.0:
                    self._obpulse_wait += self._obpulse_rate
                    ifac = 0.5 * (sin(fx_uniform(0.0, 2 * pi)) + 1.0)
                    color = self._obcolor + (self._obcolor2 - self._obcolor) * ifac
                    radius = self._obradius + (self._obradius2 - self._obradius) * ifac
                    self._overbright.update(color=color, radius=radius)

        return task.cont


# :also-compiled:
class PolyBurnGeom (object):

    def __init__ (self, apos, aquat):

        self._prev_apos = apos
        self._prev_aquat = aquat

        self._total_particle_count = 0

        self._strands = []


    def add_strand (self, thickness, endthickness,
                    emittype, emitparam1, emitspeed,
                    spacing, offtang,
                    color, endcolor, tcol, alphaexp,
                    texsplit, numframes,
                    maxpoly, pnode):

        if numframes == 0:
            numframes = texsplit**2

        strand = SimpleProps()
        self._strands.append(strand)

        strand.thickness = thickness
        strand.endthickness = endthickness
        strand.emittype = emittype
        strand.emitparam1 = emitparam1
        strand.emitspeed = emitspeed
        strand.spacing = spacing
        strand.color = color
        strand.endcolor = endcolor
        strand.tcol = tcol
        strand.alphaexp = alphaexp
        strand.texsplit = texsplit
        strand.numframes = numframes

        strand.gen = MeshDrawer()
        strand.gen.setBudget(maxpoly)
        strand.node = strand.gen.getRoot()
        strand.node.setDepthWrite(False)
        strand.node.setTransparency(TransparencyAttrib.MAlpha)
        strand.node.reparentTo(pnode)

        strand.dtang = -offtang * thickness
        strand.absspacing = thickness * spacing

        strand.particles = []

        return strand.node


    def update (self, camera, lifespan, bpos, havepq, apos, aquat, adt):

        if havepq:
            dpos = apos - self._prev_apos
            for strand in self._strands:
                ddtang = strand.emitspeed * adt
                strand.dtang += ddtang
                while strand.dtang > 0.0:
                    ctime = strand.dtang / strand.emitspeed
                    offx = 0.0; offy = 0.0
                    if strand.emittype == 0: # "circle"
                        dang = fx_uniform(0.0, 2 * pi)
                        drad = sqrt(fx_randunit()) * strand.emitparam1[0]
                        offx = drad * cos(dang)
                        offy = drad * sin(dang)
                    elif strand.emittype == 1: # "yaxis"
                        offx = fx_uniform(-strand.emitparam1[2], strand.emitparam1[2])
                        offy = fx_uniform(strand.emitparam1[0], strand.emitparam1[1])
                    elif strand.emittype == 2: # "xaxis"
                        offx = fx_uniform(strand.emitparam1[0], strand.emitparam1[1])
                        offy = fx_uniform(-strand.emitparam1[2], strand.emitparam1[2])
                    papos = apos - dpos * (ctime / adt) + Point3(offx, offy, strand.dtang)
                    particle = SimpleProps(ctime=ctime, apos=papos)
                    strand.particles.append(particle)
                    strand.dtang -= strand.absspacing
                    self._total_particle_count += 1
            self._prev_apos = apos
            self._prev_aquat = aquat
        elif self._total_particle_count > 0:
            apos = self._prev_apos
            aquat = self._prev_aquat
        else:
            return

        for strand in self._strands:
            strand.node.setPos(bpos)
            strand.gen.begin(camera, strand.node)
            strand.color0 = Vec4(strand.color)
            strand.color1 = Vec4(strand.endcolor)
            particle_count = len(strand.particles)
            partvel = Vec3(0.0, 0.0, 1.0) * strand.emitspeed
            maxreach = 0.0
            i = 0
            while i < particle_count:
                particle = strand.particles[i]
                if particle.ctime < lifespan:
                    ifac = particle.ctime / lifespan
                    pos = particle.apos - bpos
                    thck0, thck1 = strand.thickness, strand.endthickness
                    thck = thck0 + (thck1 - thck0) * ifac
                    col0, col1 = strand.color0, strand.color1
                    tfac1 = strand.tcol
                    if ifac < tfac1:
                        col = col0 + (col1 - col0) * (ifac / tfac1)
                    else:
                        col = Vec4(col1)
                    alexp = strand.alphaexp
                    col[3] *= (1.0 - ifac)**alexp
                    if strand.texsplit > 0:
                        dcoord = 1.0 / strand.texsplit
                        frind = int(strand.numframes * ifac)
                        uind = frind % strand.texsplit
                        vind = frind // strand.texsplit
                        uoff = uind  * dcoord
                        voff = 1.0 - (vind + 1) * dcoord
                        frame = Vec4(uoff, voff, dcoord, dcoord)
                    else:
                        frame = Vec4(0.0, 0.0, 1.0, 1.0)
                    rad = thck * 0.5
                    strand.gen.billboard(Vec3(pos), frame, rad, col)
                    maxreach = max(maxreach, pos.length())
                    particle.apos += partvel * adt
                    particle.ctime += adt
                    i += 1
                else:
                    strand.particles.pop(i)
                    particle_count -= 1
                    self._total_particle_count -= 1
            strand.gen.end()
            if particle_count > 1:
                strand.node.node().setBounds(BoundingSphere(Point3(), maxreach))
                strand.node.node().setFinal(True)


    def clear (self, camera, havepq, apos, aquat):

        for strand in self._strands:
            strand.gen.begin(camera, strand.node)
            strand.gen.end()
            strand.particles = []
        self._total_particle_count = 0
        if havepq:
            self._prev_apos = apos
            self._prev_aquat = aquat


    def any_visible (self):

        return self._total_particle_count > 0


    def prev_apos (self):

        return self._prev_apos


    def prev_aquat (self):

        return self._prev_aquat


if USE_COMPILED:
    from trail_c import *
