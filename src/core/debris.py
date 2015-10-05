# -*- coding: UTF-8 -*-

from math import radians

from direct.particles.ForceGroup import ForceGroup
from direct.particles.ParticleEffect import ParticleEffect
from pandac.PandaModules import Vec3, Point3, Quat
from pandac.PandaModules import BaseParticleRenderer, BaseParticleEmitter
from pandac.PandaModules import LinearVectorForce

from src import pycv
from src.core.misc import rgba, make_particles, bin_view_b2f
from src.core.misc import unitv, vectohpr, sign, set_texture, vtof
from src.core.misc import fx_uniform, fx_randrange, fx_choice, fx_randvec
from src.core.shader import make_shader
from src.core.trail import PolyBraid, PolyBurn, PolyExhaust


class Debris (object):

    def __init__ (self, world, pnode, pos,
                  firetex=None, smoketex=None, debristex=None,
                  sizefac=1.0, timefac=1.0, amplfac=1.0,
                  smgray=(5, 20)):

        self.world = world
        self._pnode = pnode

        self.node = self._pnode.attachNewNode("debris")
        self.node.setPos(pos)
        self._rnode1 = world.node.attachNewNode("debris-render-1")
        self._rnode2 = world.node.attachNewNode("debris-render-2")
        shader = make_shader(modcol=True)
        for rnode in (self._rnode1, self._rnode2):
            rnode.setDepthWrite(False)
            rnode.setShader(shader)
            self.world.add_altbin_node(rnode)

        self._pfxes = []

        # Fire particles.
        if firetex:
            flspans = []
            for i in range(1):
                frad = 1.8 * sizefac
                fampl = 0.6 * amplfac
                fsc1 = 0.001 * sizefac
                fsc2 = fx_uniform(0.01, 0.02) * sizefac
                flspan = fx_uniform(0.15, 0.3) * timefac
                # fcol = rgba(255, 255, 255, 1.0)
                fcol = rgba(255, 255, fx_randrange(55) + 200, 0.95)
                self._start_pfx(
                    enode=self.node, rnode=self._rnode1,
                    pos=Vec3(), radius=frad, scale1=fsc1, scale2=fsc2,
                    lifespan=flspan, poolsize=6, amplitude=fampl,
                    texpath=firetex, color=fcol,
                    alphamode=BaseParticleRenderer.PRALPHAIN,
                    starttime=0.0)
                flspans.append(flspan)
            self._max_flspan = max(flspans)

        # Smoke particles.
        if smoketex and flspans:
            for flspan in flspans:
                srad = 1.0 * sizefac
                sampl = 2.0 * amplfac
                ssc1 = 0.0001 * sizefac # 0.005
                ssc2 = 0.005 * sizefac # 0.100
                #sstime = flspan * timefac
                #slspan = 0.8 * timefac
                sstime = 0.0 * timefac
                slspan = flspan + 0.8 * timefac
                c = fx_randrange(smgray[0], smgray[1])
                scol = rgba(c, c, c, 0.5)
                self._start_pfx(
                    enode=self.node, rnode=self._rnode2,
                    pos=Vec3(), radius=srad, scale1=ssc1, scale2=ssc2,
                    lifespan=slspan, poolsize=3, amplitude=sampl,
                    texpath=smoketex, color=scol,
                    alphamode=BaseParticleRenderer.PRALPHAOUT,
                    starttime=sstime)

        # Debris particles.
        if debristex:
            if not isinstance(debristex, (list, tuple)):
                debristex = [debristex]
            for i in range(2):
                drad = 4.0 * sizefac
                dampl = 0.4 * amplfac
                dsc = 0.001 * sizefac
                dlspan = (fx_uniform(0.1, 0.3) + 0.6) * timefac
                dcol = rgba(255, 255, 255, 1.0)
                dtexpath = fx_choice(debristex)
                self._start_pfx(
                    enode=self.node, rnode=self._rnode2,
                    pos=Vec3(), radius=drad, scale1=dsc, scale2=dsc,
                    lifespan=dlspan, poolsize=2, amplitude=dampl,
                    texpath=dtexpath, color=dcol,
                    alphamode=BaseParticleRenderer.PRALPHAUSER,
                    starttime=0.0)

        self._time0 = self.world.time

        self.alive = True
        base.taskMgr.add(self._loop, "debris-loop")


    def _start_pfx (self, enode, rnode, pos, radius, scale1, scale2,
                    lifespan, poolsize, amplitude,
                    texpath, color, alphamode, starttime):

        pfx = ParticleEffect()
        pfx.setPos(pos)

        p0 = make_particles()
        p0.setPoolSize(16)
        p0.setPoolSize(poolsize)
        p0.setBirthRate(starttime or 1e-5)
        p0.setLitterSize(poolsize)
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
        p0.renderer.setAlphaMode(alphamode)
        texture = base.load_texture("data", texpath)
        p0.renderer.setTexture(texture)
        # p0.renderer.setUserAlpha(alpha)
        p0.renderer.setColor(color)
        p0.renderer.setXScaleFlag(1)
        p0.renderer.setYScaleFlag(1)
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

        #f0 = ForceGroup("vertex")
        #force0 = LinearVectorForce(Vec3(0.0, 0.0, -amplitude * 2))
        #force0.setActive(1)
        #f0.addForce(force0)

        p0.setRenderParent(rnode)

        #pfx.addForceGroup(f0)
        pfx.addParticles(p0)
        pfx.start(enode)

        self._pfxes.append((pfx, lifespan, starttime))


    def _loop (self, task):

        time1 = self.world.time - self._time0
        pfxes = []
        for pfx, lifespan, starttime in self._pfxes:
            if time1 < starttime + lifespan:
                pfxes.append((pfx, lifespan, starttime))
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

        return task.cont


class FlowDebris (object):

    def __init__ (self, world, pnode, pos,
                  firetex=None, smoketex=None, debristex=None,
                  sizefac=1.0, timefac=1.0, amplfac=1.0,
                  keepready=None):

        self.world = world
        self._pnode = pnode

        self.node = self._pnode.attachNewNode("flowdebris")
        self.node.setPos(pos)

        self._firetex = firetex
        self._smoketex = smoketex
        self._debristex = debristex
        self._sizefac = sizefac
        self._timefac = timefac
        self._amplfac = amplfac
        if not keepready:
            keepready = 0.0
        elif keepready is True:
            keepready = -1.0
        self._keepready = keepready

        self._rnode = world.node.attachNewNode("flowdebris-render")
        self.world.add_altbin_node(self._rnode)
        if self._firetex:
            rnode = self._rnode.attachNewNode("fire")
            rnode.setDepthWrite(False)
            shader = make_shader(modcol=True)
            rnode.setShader(shader)
            self._rnode_fire = rnode
        if self._smoketex:
            rnode = self._rnode.attachNewNode("smoke")
            rnode.setDepthWrite(False)
            shader = make_shader(ambln=self.world.shdinp.ambln, modcol=True)
            rnode.setShader(shader)
            self._rnode_smoke = rnode
        if self._debristex:
            rnode = self._rnode.attachNewNode("debris")
            rnode.setDepthWrite(False)
            shader = make_shader(ambln=self.world.shdinp.ambln, modcol=True)
            rnode.setShader(shader)
            self._rnode_debris = rnode

        self._pfxes = []
        if self._keepready < 0.0:
            self._make_all_pfx(softstop=True)
        self._keeptime = 0.0

        self.duration = 0.0
        self._prev_duration = 0.0

        self.alive = True
        base.taskMgr.add(self._loop, "flowdebris-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self._clear_all_pfx()
        self._rnode.removeNode()
        self.node.removeNode()


    def _make_all_pfx (self, softstop=False):

        if self._pfxes:
            self._clear_all_pfx()

        if self._firetex:
            fspindir = fx_choice([-1, 1])
            fzspni = fx_uniform(-180, -10)
            fzspnf = fx_uniform(10, 180)
            fzspnv = 10 * fspindir
            pfx = self._make_pfx(
                enode=self.node, rnode=self._rnode_fire,
                pos=Vec3(), radius=(1.8 * self._sizefac),
                scale1=(0.02 * self._sizefac), scale2=(0.007 * self._sizefac),
                birthrate=0.08, lifespan=0.04,
                zspinini=fzspni, zspinfin=fzspnf, zspinvel=fzspnv,
                littersize=1, poolsize=64,
                amplitude=(0.06 * self._amplfac), ampspread=0,
                risefact=Vec3(0,0,0),
                texpath=self._firetex, color=rgba(255, 255, 210, 0.90),
                alphamode=BaseParticleRenderer.PRALPHAOUT,
                softstop=softstop)
            self._pfxes.append(pfx)

        if self._smoketex:
            sspindir = fx_choice([-1, 1])
            szspni = fx_uniform(-180, -20)
            szspnf = fx_uniform(20, 180)
            szspnv = 15 * sspindir
            pfx = self._make_pfx(
                enode=self.node, rnode=self._rnode_smoke,
                pos=Vec3(), radius=(1.0 * self._sizefac),
                scale1=(0.0004 * self._sizefac), scale2=(0.020 * self._sizefac),
                birthrate=0.08, lifespan=0.24,
                zspinini=szspni, zspinfin=szspnf, zspinvel=szspnv,
                littersize=2, poolsize=64,
                amplitude=(1.0 * self._amplfac), ampspread=0,
                risefact=Vec3(0,0,3.5),
                texpath=self._smoketex, color=rgba(20, 20, 20, 0.8),
                alphamode=BaseParticleRenderer.PRALPHAOUT,
                softstop=softstop)
            self._pfxes.append(pfx)

        if self._debristex:
            dspindir = fx_choice([-1, 1])
            dzspni = fx_uniform(-180, -40)
            dzspnf = fx_uniform(40, 180)
            dzspnv = 20 * dspindir
            pfx = self._make_pfx(
                enode=self.node, rnode=self._rnode_debris,
                pos=Vec3(), radius=(1.0 * self._sizefac),
                scale1=(0.001 * self._sizefac), scale2=(0.001 * self._sizefac),
                birthrate=0.40, lifespan=1.0,
                zspinini=dzspni, zspinfin=dzspnf, zspinvel=dzspnv,
                littersize=2, poolsize=64,
                amplitude=(1.0 * self._amplfac), ampspread=12,
                risefact=Vec3(0,0,-9.81),
                texpath=self._debristex, color=rgba(255, 255, 255, 1.0),
                alphamode=BaseParticleRenderer.PRALPHAUSER,
                softstop=softstop)
            self._pfxes.append(pfx)

        #print "--flowdebris-make-pfx"


    def _clear_all_pfx (self):

        for pfx in self._pfxes:
            pfx.cleanup()
        self._pfxes = []
        #print "--flowdebris-clear-pfx"


    def _make_pfx (self, enode, rnode, pos, radius, scale1, scale2,
                   birthrate, lifespan, zspinini, zspinfin, zspinvel,
                   poolsize, littersize, amplitude, ampspread, risefact,
                   texpath, color, alphamode, softstop):

        pfx = ParticleEffect()
        pfx.setPos(pos)

        p0 = make_particles()
        p0.setPoolSize(poolsize)
        p0.setBirthRate(birthrate)
        p0.setLitterSize(littersize)
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
        p0.factory.setFinalAngle(zspinfin)
        p0.factory.setInitialAngle(zspinini)

        p0.setRenderer("SpriteParticleRenderer")
        p0.renderer.setAlphaMode(alphamode)
        texpaths = texpath
        if not isinstance(texpath, (tuple, list)):
            texpaths = [texpaths]
        for texpath in texpaths:
            texture = base.load_texture("data", texpath)
            p0.renderer.addTexture(texture)
        # p0.renderer.setUserAlpha(alpha)
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
        p0.emitter.setAmplitudeSpread(ampspread)
        #p0.emitter.setOffsetForce(Vec3(0.0000, 0.0000, 0.0000))
        #p0.emitter.setExplicitLaunchVector(Vec3(1.0000, 0.0000, 0.0000))
        #p0.emitter.setRadiateOrigin(Point3(0.0000, 0.0000, 0.0000))

        f0 = ForceGroup("vertex")
        force0 = LinearVectorForce(risefact * amplitude)
        force0.setActive(1)
        f0.addForce(force0)

        p0.setRenderParent(rnode)

        pfx.addForceGroup(f0)
        pfx.addParticles(p0)

        pfx.start(enode)
        if softstop:
            pfx.softStop()

        return pfx


    def _loop (self, task):

        if self._pnode.isEmpty():
            self.destroy()
            return task.done
        if not self.alive:
            return task.done

        dt = self.world.dt
        if self.duration > 0.0:
            self.duration -= dt
        if self._prev_duration <= 0.0 and self.duration > 0.0:
            pos0 = self._pnode.getPos(self.world.node)
            self._rnode.setPos(pos0)
            if self._pfxes:
                for pfx in self._pfxes:
                    pfx.softStart()
            else:
                self._make_all_pfx(softstop=False)
        elif self._prev_duration > 0.0 and self.duration <= 0.0:
            if self._keepready > 0.0:
                for pfx in self._pfxes:
                    pfx.softStop()
                self._keeptime = self._keepready
            elif self._keepready == 0.0:
                self._clear_all_pfx()
        self._prev_duration = self.duration

        if self._keeptime > 0.0:
            self._keeptime -= dt
            if self._keeptime <= 0.0:
                self._clear_all_pfx()

        #if self.duration > 0.0:
            #binval = bin_view_b2f(self.node, self.world.camera)
            #self._rnode.setBin("fixed", binval)

        return task.cont


class BreakupPart (object):

    def __init__ (self, body, handle, duration,
                  offpos=None, offdir=None, offspeed=0.0,
                  traildurfac=1.0, traillifespan=0.0,
                  trailthickness=0.0, trailendthfac=4.0,
                  trailspacing=1.0, trailtcol=0.0,
                  trailfire=False,
                  keeptogether=False, texture=None):

        if isinstance(body, tuple):
            model, world = body
            models = [model]
            shadow_model = None
            body = None
            self.world = world
        else:
            self.world = body.world
            models = list(body.models)
            if base.with_world_shadows and body.shadow_node is not None:
                shadow_model = body.shadow_node
            else:
                shadow_model = None

        self.node = self.world.node.attachNewNode("breakup-part")
        if not keeptogether:
            shader = make_shader(ambln=self.world.shdinp.ambln,
                                 dirlns=self.world.shdinp.dirlns)
            self.node.setShader(shader)
            if texture is not None:
                set_texture(self.node, texture)

        if isinstance(handle, basestring):
            handles = [handle]
        else:
            handles = handle

        offset = offpos
        pos = None
        quat = None
        self._together_nodes = []
        for model in models:
            if model is None:
                continue
            for handle in handles:
                nd = model.find("**/%s" % handle)
                if not nd.isEmpty():
                    if offset is None:
                        if body is not None:
                            offset = nd.getPos(body.node)
                        else:
                            offset = nd.getPos(self.world.node)
                    if pos is None:
                        # Must be done here because of wrtReparentTo below.
                        if body is not None:
                            pos = body.pos(offset=offset)
                            quat = body.quat()
                        else:
                            pos = self.world.node.getRelativePoint(model, offset)
                            quat = model.getQuat(self.world.node)
                        self.node.setPos(pos)
                        self.node.setQuat(quat)
                        if offdir is None:
                            offdir = unitv(offset)
                    if not keeptogether:
                        nd.wrtReparentTo(self.node)
                    else:
                        offset2 = nd.getPos(self.node)
                        self._together_nodes.append((nd, offset2))
        if pos is None:
            if offpos is not None:
                pos = offpos
                self.node.setPos(pos)
            else:
                raise StandardError(
                    "No subnodes found for given handle, "
                    "and no initial position given.")
        if shadow_model is not None:
            for handle in handles:
                nd = shadow_model.find("**/%s" % handle)
                if not nd.isEmpty():
                    nd.removeNode()

        if body is not None:
            odir = self.world.node.getRelativeVector(body.node, offdir)
            bvel = body.vel()
        elif models[0] is not None:
            odir = self.world.node.getRelativeVector(models[0], offdir)
            bvel = Vec3(0.0, 0.0, 0.0)
        else:
            odir = offdir
            bvel = Vec3(0.0, 0.0, 0.0)
        vel = bvel + odir * offspeed
        if quat is None:
            quat = Quat()
            quat.setHpr(vectohpr(vel))

        self._pos0 = pos
        self._vel0 = vel
        self._quat0 = quat

        self._duration = duration
        self._time = 0.0

        self._trails = []
        if traildurfac > 0.0 and traillifespan > 0.0 and trailthickness > 0.0:
            self._start_trail(traildurfac, traillifespan, trailthickness,
                              trailendthfac, trailspacing, trailtcol, trailfire)

        self.alive = True
        # Before general loops, e.g. to have updated position in effect loops.
        base.taskMgr.add(self._loop, "breakup-part-loop", sort=-1)


    def destroy (self):

        if not self.alive:
            return
        self.node.removeNode()
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.world.alive:
            # This prevents invalid altitude queries in _move, because
            # _move is not executed by world (like it is for bodies).
            self.destroy()
            return task.done

        dt = self.world.dt

        self._time += dt

        is_duration_func = callable(self._duration)
        if is_duration_func:
            done = self._duration()
        else:
            done = (self._time > self._duration)
        if done:
            self.destroy()
            return task.done

        if is_duration_func:
            rd = 1.0
        else:
            rd = self._time / self._duration

        self._move(dt, rd)

        # Mirro the move to any kept-together nodes.
        for node, offset in self._together_nodes:
            if not node.isEmpty():
                pos = node.getParent().getRelativePoint(self.node, offset)
                node.setPos(pos)
                quat = self.node.getQuat(node.getParent())
                node.setQuat(quat)

        if not is_duration_func:
            for trail, timefac in self._trails:
                trd = self._time / (self._duration * timefac)
                if trd < 1.0:
                    trail.node.setSa((1.0 - trd)**2)
                elif trail.alive:
                    trail.destroy()

        return task.cont


    def _start_trail (self, timefac, lifespan, thickness, endthfac, spacing, tcol, fire_on):

        pass



class AirBreakupPart (BreakupPart):

    def __init__ (self, body, handle, termspeed, duration,
                  offpos=None, offdir=None, offspeed=0.0,
                  rollspeed=0.0, rollrad=0.0,
                  traildurfac=1.0, traillifespan=0.0,
                  trailthickness=0.0, trailendthfac=4.0,
                  trailspacing=1.0, trailtcol=0.0,
                  trailfire=False,
                  texture=None):

        BreakupPart.__init__(self,
                             body=body, handle=handle, duration=duration,
                             offpos=offpos, offdir=offdir, offspeed=offspeed,
                             traildurfac=traildurfac,
                             traillifespan=traillifespan,
                             trailthickness=trailthickness,
                             trailendthfac=trailendthfac,
                             trailspacing=trailspacing,
                             trailtcol=trailtcol,
                             trailfire=trailfire,
                             texture=texture)
        fvel = self._vel0
        quat = self._quat0
        pos = self._pos0

        fdir = unitv(fvel)
        tdir = unitv(quat.getRight().cross(fdir))
        tspeed = rollspeed * rollrad
        tvel = tdir * tspeed

        self._pos = pos
        self._quat = quat
        self._fvel = fvel
        self._tvel = tvel

        self._termspeed = termspeed
        self._rollspeed = rollspeed
        self._rollrad = rollrad


    def _start_trail (self, timefac, lifespan, thickness, endthfac, spacing, tcol, fire_on):

        if True:
            if fire_on:
                fire = PolyExhaust(
                    parent=(self.node, self.world),
                    pos=Vec3(0.0, 0.0, 0.0),
                    radius0=(thickness * endthfac) * 0.4,
                    radius1=thickness * 0.5,
                    length=18,
                    speed=42,
                    poolsize=16,
                    color=rgba(255, 255, 255, 1.0),
                    colorend=rgba(247, 203, 101, 1.0),
                    tcol=0.6,
                    subnode=None,
                    pdir=None,
                    emradius=0.6,
                    texture="images/particles/explosion7-1.png",
                    glowmap=rgba(255, 255, 255, 1.0),
                    ltoff=True,
                    frameskip=2,
                    dbin=0,
                    freezedist=600.0 * (thickness / 0.15),
                    hidedist=800.0 * (thickness / 0.15),
                    loddirang=10,
                    loddirskip=4,
                    delay=0.0)
                self._trails.append((fire, timefac))
            smoke = PolyBraid(
                parent=(self.node, self.world),
                pos=Vec3(0.0, 0.0, 0.0),
                numstrands=1,
                lifespan=lifespan,
                thickness=thickness,
                endthickness=(thickness * endthfac),
                spacing=spacing,
                offang=None,
                offrad=0.0,
                offtang=0.0,
                randang=False,
                randrad=False,
                texture="images/particles/smoke6-1.png",
                glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
                # #texture="images/particles/smoke-trail-1.png",
                # #glowmap="images/particles/smoke-trail-1_gw.png",
                # glowmap=rgba(255, 255, 255, 1.0),
                # color=rgba(247, 173, 64, 1.0),
                # #endcolor=rgba(31, 29, 28, 1.0),
                # endcolor=rgba(13, 12, 12, 1.0),
                color=pycv(py=rgba(247, 173, 64, 1.0), c=rgba(247, 173, 64, 1.0)),
                endcolor=pycv(py=rgba(13, 12, 12, 1.0), c=rgba(255, 239, 230, 1.0)),
                dirlit=pycv(py=False, c=True),
                tcol=tcol,
                alphaexp=2.0,
                segperiod=0.010,
                farsegperiod=pycv(py=0.020, c=None),
                maxpoly=pycv(py=500, c=1000),
                farmaxpoly=1000,
                #texsplit=4, numframes=16,
                dbin=3,
                loddistout=1400 * (thickness / 0.15),
                loddistalpha=1200 * (thickness / 0.15),
                loddirang=5,
                loddirspcfac=5)
            self._trails.append((smoke, timefac))


    def _move (self, dt, rd):

        pos = self._pos
        quat = self._quat
        fvel = self._fvel
        tvel = self._tvel

        termspeed = self._termspeed
        gracc = self.world.gravacc
        fspeed = fvel.length()
        fdir = unitv(fvel)
        absdracc = self.world.absgravacc * (fspeed**2 / termspeed**2)
        if fspeed - absdracc * dt < 0.0:
            absdracc = (fspeed / dt) * 0.5
        dracc = fdir * -absdracc
        facc = gracc + dracc
        #facc = Vec3()
        dfpos = fvel * dt + facc * (0.5 * dt**2)
        fvel1 = fvel + facc * dt

        rollspeed = self._rollspeed
        rollrad = self._rollrad
        if rollspeed != 0.0 and rollrad != 0.0:
            rollspeed1 = rollspeed * (1.0 - rd)**2
            rollrad1 = rollrad * (1.0 - rd)**2
            tdir = unitv(tvel) * (sign(rollspeed * rollrad) or 1)
            fdir1 = unitv(fvel1)
            dsroll = rollspeed1 * dt
            dtquat = Quat()
            dtquat.setFromAxisAngleRad(dsroll, fdir)
            tdir1p = Vec3(dtquat.xform(tdir))
            tdir1 = unitv(fdir1.cross(tdir1p).cross(fdir1))
            tspeed1 = rollspeed1 * rollrad1
            dtpos = tvel * dt
            tvel1 = tdir1 * tspeed1
        else:
            dtpos = Vec3()
            dtquat = Quat()
            tvel1 = Vec3()

        pos1 = pos + dfpos + dtpos
        self.node.setPos(pos1)

        fdir1 = unitv(fvel1)
        paxis = fdir.cross(fdir1)
        if paxis.length() > 1e-5:
            paxis.normalize()
            dspitch = fdir.signedAngleRad(fdir1, paxis)
        else:
            paxis = quat.getRight()
            paxis.normalize()
            dspitch = 0.0
        dfquat = Quat()
        dfquat.setFromAxisAngleRad(dspitch, paxis)
        quat1 = quat * dfquat * dtquat
        self.node.setQuat(quat1)

        self._pos = pos1
        self._quat = quat1
        self._fvel = fvel1
        self._tvel = tvel1


class AirBreakupData (object):

    def __init__ (self, handle, limdamage, duration, termspeed,
                  offdir, offspeed,
                  rollspeeddeg=0.0, rollrad=0.0,
                  traildurfac=0.0, traillifespan=0.0, trailthickness=0.0,
                  trailtcol=0.0, trailfire=False,
                  texture=None):

        self.handle = handle
        self.limdamage = limdamage
        self.duration = duration
        self.termspeed = termspeed
        self.offdir = offdir
        self.offspeed = offspeed
        self.rollspeeddeg = rollspeeddeg
        self.rollrad = rollrad
        self.traildurfac = traildurfac
        self.traillifespan = traillifespan
        self.trailthickness = trailthickness
        self.trailtcol = trailtcol
        self.trailfire = trailfire
        self.texture = texture


class AirBreakup (object):

    def __init__ (self, body, breakupdata):

        rv = lambda x: fx_uniform(*x) if isinstance(x, tuple) else float(x)
        rd = lambda x: fx_randvec(*x) if isinstance(x, tuple) else x
        for bkpd in breakupdata:
            AirBreakupPart(body=body,
                           handle=bkpd.handle,
                           duration=rv(bkpd.duration),
                           termspeed=rv(bkpd.termspeed),
                           offpos=None,
                           offdir=rd(bkpd.offdir),
                           offspeed=rv(bkpd.offspeed),
                           rollspeed=radians(rv(bkpd.rollspeeddeg)),
                           rollrad=rv(bkpd.rollrad),
                           traildurfac=rv(bkpd.traildurfac),
                           traillifespan=rv(bkpd.traillifespan),
                           trailthickness=rv(bkpd.trailthickness),
                           trailtcol=rv(bkpd.trailtcol),
                           trailfire=bkpd.trailfire,
                           texture=bkpd.texture)


class GroundBreakupPart (BreakupPart):

    def __init__ (self, body, handle, duration,
                  offdir, offspeed, tumbledir, tumblespeed,
                  normrestfac=0.2, tangrestfac=0.7, tumblerestfac=0.2,
                  fixelev=0.0,
                  traildurfac=1.0, traillifespan=0.0,
                  trailthickness=0.0, trailendthfac=4.0,
                  trailspacing=1.0, trailtcol=0.0,
                  trailfire=False,
                  keeptogether=False, texture=None):

        offpos = None

        BreakupPart.__init__(self,
                             body=body, handle=handle, duration=duration,
                             offpos=offpos, offdir=offdir, offspeed=offspeed,
                             traildurfac=traildurfac,
                             traillifespan=traillifespan,
                             trailthickness=trailthickness,
                             trailendthfac=trailendthfac,
                             trailspacing=trailspacing,
                             trailtcol=trailtcol,
                             trailfire=trailfire,
                             keeptogether=keeptogether,
                             texture=texture)
        pos = self._pos0
        quat = self._quat0
        vel = self._vel0

        angvel = tumbledir * tumblespeed

        self._pos = pos
        self._quat = quat
        self._vel = vel
        self._angvel = angvel

        self._norm_rest_fac = normrestfac
        self._tang_rest_fac = tangrestfac
        self._tumble_rest_fac = tumblerestfac

        self._fix_elev = fixelev

        self._at_rest = False


    def _start_trail (self, timefac, lifespan, thickness, endthfac, spacing, tcol, fire_on):

        if True:
            if fire_on:
                fire = PolyBurn(
                    parent=(self.node, self.world),
                    pos=Vec3(0.0, 0.0, 0.0),
                    numstrands=1,
                    lifespan=lifespan,
                    thickness=thickness,
                    endthickness=thickness * 0.5,
                    spacing=spacing,
                    emitspeed=8.0,
                    emitradius=1.2,
                    offtang=0.0,
                    texture="images/particles/explosion7-1.png",
                    glowmap=rgba(255, 255, 255, 1.0),
                    color=rgba(255, 255, 255, 1.0),
                    endcolor=rgba(246, 112, 27, 1.0),
                    dirlit=False,
                    alphaexp=2.0,
                    tcol=tcol,
                    maxpoly=pycv(py=500, c=2000),
                    dbin=3,
                    frameskip=pycv(py=2, c=1),
                    delay=0.0)
                    #duration=duration)
                self._trails.append((fire, timefac))


    def _move (self, dt, rd):

        if self._at_rest:
            return

        pos = self._pos
        quat = self._quat
        vel = self._vel
        angvel = self._angvel

        gracc = self.world.gravacc
        pos1 = pos + vel * dt + gracc * (0.5 * dt**2)
        vel1 = vel + gracc * dt
        touch = self.world.below_surface(pos, elev=self._fix_elev)
        if touch:
            gpos = self.world.intersect_surface(pos, pos1, elev=self._fix_elev)
            gnorm = vtof(self.world.elevation(gpos, wnorm=True)[1])
            pos1 -= gnorm * (pos1 - gpos).dot(gnorm) * 2
            vel1_el = unitv(pos1 - pos) * vel1.length()
            vel1_el_n = gnorm * vel1_el.dot(gnorm)
            vel1_el_t = vel1_el - vel1_el_n
            vel1 = vel1_el_n * self._norm_rest_fac + vel1_el_t * self._tang_rest_fac
            self._at_rest = (vel1.length() < 0.5)
            if self._at_rest:
                pos1 = gpos
                vel1 = Vec3(0.0, 0.0, 0.0)
        self.node.setPos(pos1)

        raxis = unitv(self._angvel)
        if raxis.length() == 0.0:
            raxis = Vec3(0.0, 0.0, 1.0)
        absangvel1 = self._angvel.length()
        if touch:
            absangvel1 *= self._tumble_rest_fac
        dquat = Quat()
        dquat.setFromAxisAngleRad(absangvel1 * dt, raxis)
        quat1 = quat * dquat
        angvel1 = raxis * absangvel1
        self.node.setQuat(quat1)

        self._pos = pos1
        self._quat = quat1
        self._vel = vel1
        self._angvel = angvel1


class GroundBreakupData (object):

    def __init__ (self, handle, breakprob, duration,
                  offdir, offspeed, tumbledir, tumblespeeddeg,
                  normrestfac=0.2, tangrestfac=0.7, tumblerestfac=0.2,
                  fixelev=0.0,
                  traildurfac=0.0, traillifespan=0.0, trailthickness=0.0,
                  trailspacing=1.0, trailtcol=0.0, trailfire=False,
                  keeptogether=False, texture=None):

        self.handle = handle
        self.breakprob = breakprob
        self.duration = duration
        self.offdir = offdir
        self.offspeed = offspeed
        self.tumbledir = tumbledir
        self.tumblespeeddeg = tumblespeeddeg
        self.normrestfac = normrestfac
        self.tangrestfac = tangrestfac
        self.tumblerestfac = tumblerestfac
        self.fixelev = fixelev
        self.traildurfac = traildurfac
        self.traillifespan = traillifespan
        self.trailthickness = trailthickness
        self.trailspacing = trailspacing
        self.trailtcol = trailtcol
        self.trailfire = trailfire
        self.keeptogether = keeptogether
        self.texture = texture


class GroundBreakup (object):

    def __init__ (self, body, breakupdata):

        rv = lambda x: fx_uniform(*x) if isinstance(x, tuple) else float(x)
        ri = lambda x: fx_randrange(*x) if isinstance(x, tuple) else int(x)
        rd = lambda x: fx_randvec(*x) if isinstance(x, tuple) else x
        for bkpd in breakupdata:
            if bkpd.duration is not None:
                duration = rv(bkpd.duration)
            else:
                duration = lambda: not body.alive
            GroundBreakupPart(body=body,
                              handle=bkpd.handle,
                              duration=duration,
                              offdir=rd(bkpd.offdir),
                              offspeed=rv(bkpd.offspeed),
                              tumbledir=rd(bkpd.tumbledir),
                              tumblespeed=radians(rv(bkpd.tumblespeeddeg)),
                              normrestfac=rv(bkpd.normrestfac),
                              tangrestfac=rv(bkpd.tangrestfac),
                              tumblerestfac=rv(bkpd.tumblerestfac),
                              fixelev=rv(bkpd.fixelev),
                              traildurfac=rv(bkpd.traildurfac),
                              traillifespan=rv(bkpd.traillifespan),
                              trailthickness=rv(bkpd.trailthickness),
                              trailspacing=rv(bkpd.trailspacing),
                              trailtcol=rv(bkpd.trailtcol),
                              trailfire=bkpd.trailfire,
                              keeptogether=bkpd.keeptogether,
                              texture=bkpd.texture)


