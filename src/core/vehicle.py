# -*- coding: UTF-8 -*-

from math import floor, radians, degrees, pi, sin, cos, atan2

from pandac.PandaModules import Vec3, Vec3D, Vec4, Point3, Point3D, Quat
from pandac.PandaModules import NodePath, AmbientLight

from src import pycv
from src import join_path, path_exists, path_dirname, path_basename
from src.core.body import Body
from src.core.curve import Segment, Arc
from src.core.debris import GroundBreakup
from src.core.effect import fire_n_smoke_2
from src.core.fire import PolyExplosion
from src.core.misc import AutoProps, rgba, norm_ang_delta, to_navhead
from src.core.misc import sign, unitv, clamp, vtod, vtof, ptod, ptof
from src.core.misc import make_text, update_text
from src.core.misc import uniform, randrange, randunit
from src.core.misc import fx_uniform
from src.core.misc import load_model_lod_chain
from src.core.shader import make_shader
from src.core.sound import Sound3D


class Vehicle (Body):

    family = "vehicle"
    species = "generic"
    longdes = None
    shortdes = None

    maxspeed = 30.0
    maxslope = radians(30.0)
    maxturnrate = radians(90.0)
    maxthracc = 10.0
    maxvdracc = 5.0
    strength = 20.0
    minhitdmg = 0.0
    maxhitdmg = 10.0
    rcs = 0.005
    hitboxdata = []
    hitdebris = None
    # hitdebris = AutoProps(
        # #firetex="images/particles/explosion1.png",
        # #smoketex="images/particles/smoke1-1.png",
        # debristex=[
            # "images/particles/airplanedebris_1.png",
            # "images/particles/airplanedebris_2.png",
            # "images/particles/airplanedebris_3-1.png",
            # "images/particles/airplanedebris_3-2.png",
            # "images/particles/airplanedebris_3-3.png"])
    hitflash = AutoProps()
    groundcontact = [
        Point3(0.0, 1.0, 0.0),
        Point3(-1.0, -1.0, 0.0),
        Point3(+1.0, -1.0, 0.0)]
    modelpath = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    sdmodelpath = None
    shdmodelpath = None
    normalmap = None
    glowmap = rgba(0,0,0, 0.1)
    glossmap = None
    engsoundname = None
    engminvol = 0.0
    engmaxvol = 0.4
    trkspdfac = []
    breakupdata = []

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None, sink=None, damage=None):

        if pos is None:
            pos = Point3()
        if hpr is None:
            hpr = Vec3()
        if sink is None:
            sink = 0.0
        if speed is None:
            speed = 0.0
        pos = Point3(pos[0], pos[1], 0.0)

        self.texture = texture

        if isinstance(self.modelpath, basestring):
            shdmodind = 0
        elif self.modelpath:
            shdmodind = min(len(self.modelpath) - 1, 1)
        else:
            shdmodind = None

        Body.__init__(self,
            world=world,
            family=self.family, species=self.species,
            hitforce=(self.strength * 0.1),
            name=name, side=side,
            modeldata=AutoProps(
                path=self.modelpath, shadowpath=self.shdmodelpath,
                texture=texture, normalmap=self.normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            hitboxdata=self.hitboxdata,
            hitlight=AutoProps(),
            hitdebris=self.hitdebris, hitflash=self.hitflash,
            amblit=True, dirlit=True, pntlit=2, fogblend=True,
            obright=True, shdshow=True, shdmodind=shdmodind,
            ltrefl=(self.glossmap is not None),
            pos=pos, hpr=hpr, vel=speed)

        self.maxbracc = self.maxspeed / 4.0

        # Detect shotdown maps.
        self._shotdown_texture = self.texture
        self._shotdown_normalmap = self.normalmap
        self._shotdown_glowmap = self.glowmap if not isinstance(self.glowmap, Vec4) else None
        self._shotdown_glossmap = self.glossmap
        self._shotdown_change_maps = False
        if isinstance(self.modelpath, basestring):
            ref_modelpath = self.modelpath
        elif isinstance(self.modelpath, (tuple, list)):
            ref_modelpath = self.modelpath[0]
        else:
            ref_modelpath = None
        if ref_modelpath:
            ref_modeldir = path_dirname(ref_modelpath)
            ref_modelname = path_basename(ref_modeldir)
            if self.texture:
                test_path = self.texture.replace("_tex.", "_burn.")
                if path_exists("data", test_path):
                    self._shotdown_texture = test_path
                    self._shotdown_change_maps = True
            if self.normalmap:
                test_path = join_path(ref_modeldir,
                                      ref_modelname + "_burn_nm.png")
                if path_exists("data", test_path):
                    self._shotdown_normalmap = test_path
                    self._shotdown_change_maps = True
            if self.glowmap and not isinstance(self.glowmap, Vec4):
                test_path = join_path(ref_modeldir,
                                      ref_modelname + "_burn_gw.png")
                if path_exists("data", test_path):
                    self._shotdown_glowmap = test_path
                    self._shotdown_change_maps = True
            if self.glossmap:
                test_path = join_path(ref_modeldir,
                                      ref_modelname + "_burn_gls.png")
                if path_exists("data", test_path):
                    self._shotdown_glossmap = test_path
                    self._shotdown_change_maps = True

        # Prepare shotdown model.
        self._shotdown_modelnode = None
        if self.sdmodelpath:
            modelchain = self.sdmodelpath
            if isinstance(modelchain, basestring):
                modelchain = [modelchain]
            ret = load_model_lod_chain(
                    world.vfov, modelchain,
                    texture=self._shotdown_texture,
                    normalmap=self._shotdown_normalmap,
                    glowmap=self._shotdown_glowmap,
                    glossmap=self._shotdown_glossmap,
                    shadowmap=self.world.shadow_texture,
                    scale=self.modelscale,
                    pos=self.modeloffset, hpr=self.modelrot)
            lnode, models, fardists = ret[:3]
            lnode.setShader(self.shader)
            self._shotdown_modelnode = lnode
            self._shotdown_models = models
            self._shotdown_fardists = fardists
            for mlevel, model in enumerate(models):
                model.setTwoSided(True)

        # Locally reposition and reorient vehicle such as that
        # all ground contact points have local z-coordinates zero.
        # Do this by first rotating ground contact plane around axis
        # normal to z-axis and to initial ground contact plane normal,
        # until the ground contact plane normal becomes the z-axis,
        # then shift ground contact plane along z-axis to become xy-plane.
        if len(self.groundcontact) != 3:
            raise StandardError(
                "There must be exactly 3 ground contact points.")
        self._platform = self.node.attachNewNode("vehicle-platform")
        gcf, gcl, gcr = self.groundcontact
        gcn = unitv((gcl - gcf).cross(gcr - gcf))
        zdir = Vec3(0, 0, 1)
        graxis = gcn.cross(zdir)
        if graxis.normalize():
            gang = gcn.signedAngleRad(zdir, graxis)
            q = Quat()
            q.setFromAxisAngleRad(gang, graxis)
            self._platform.setQuat(q)
        self._modgndcnts = []
        for rgcp in self.groundcontact:
            rgcp1 = self.node.getRelativePoint(self._platform, rgcp)
            goffz = rgcp1[2] # equal by construction for all points
            rgcp1[2] = 0.0
            self._modgndcnts.append(rgcp1)
        self._platform.setPos(gcn * -goffz)
        self.modelnode.reparentTo(self._platform)

        # Fix vehicle to the ground, according to contact points.
        self.sink = sink
        self._gyro = world.node.attachNewNode("vehicle-gyro-%s" % name)
        gfix = Vehicle._fix_to_ground(self.world, self._gyro,
                                      self._modgndcnts, self.sink,
                                      ptod(pos), vtod(hpr))
        pos1, hpr1 = gfix[:2]
        self.node.setPos(ptof(pos1))
        self.node.setHpr(vtof(hpr1))
        self._prev_gfix = gfix

        tvelg = speed
        self._prev_dyn = (tvelg,)

        width, length, height = self.bbox
        self.size = (length + width + height) / 3
        self._length = length
        self._size_xy = min(width, length)

        # Models for detecting moving parts.
        mvpt_models = list(self.models)
        if base.with_world_shadows and self.shadow_node is not None:
            mvpt_models += [self.shadow_node]
        if self.sdmodelpath:
            mvpt_models += self._shotdown_models

        # Detect turning axles.
        self._axles = []
        for model in mvpt_models:
            axlends = model.findAllMatches("**/axle*")
            for axlend in axlends:
                c1, c2 = axlend.getTightBounds()
                dx, dy, dz = c2 - c1
                wheelrad = 0.5 * (abs(dy) + abs(dz)) / 2
                self._axles.append((axlend, wheelrad))

        # Detect turning tracks.
        # Use ambient light as shader input for uv-scroll.
        self._tracks = []
        for model in mvpt_models:
            tracknds = model.findAllMatches("**/track*")
            for it, tracknd in enumerate(tracknds):
                spdfac = self.trkspdfac[it]
                kwargs = dict(self.shader_kwargs)
                kwargs["uvscrn"] = "INuvscr"
                shader = make_shader(**kwargs)
                tracknd.setShader(shader)
                uvscr = AmbientLight(name=("uvscr-track-%d" % it))
                tracknd.setShaderInput(kwargs["uvscrn"], NodePath(uvscr))
                uvoff = Vec4()
                uvscr.setColor(uvoff)
                self._tracks.append((tracknd, spdfac, uvoff, uvscr))

        # Detect lights.
        # Set up turning on/off through glow factor.
        self._lights = []
        for model in mvpt_models:
            for lnd in model.findAllMatches("**/lights"):
                kwargs = dict(self.shader_kwargs)
                kwargs["glow"] = rgba(255, 255, 255, 1.0)
                kwargs["glowfacn"] = self.world.shdinp.glowfacn
                shader = make_shader(**kwargs)
                lnd.setShader(shader)
                self._lights.append(lnd)
        self.set_lights(on=False)

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, maxdist=3000, limnum="hum",
                volume=self.engmaxvol, loop=True, fadetime=2.5)
            self.engine_sound.play()
        else:
            self.engine_sound = None

        self.damage = damage or 0.0

        self.damage_trails = []

        self.launchers = []
        self.turrets = []
        self.decoys = []

        self._prev_path = None
        self._path_pos = 0.0
        self._throttle = 0.0

        # Control inputs.
        self.zero_inputs()

        # Autopilot constants.
        self._ap_adjperiod = 1.03
        self._ap_adjpfloat = 0.2

        # Autopilot state.
        self.zero_ap()

        # Route settings.
        self._route_current_point = None
        self._route_points = []
        self._route_point_inc = 1
        self._route_patrol = False
        self._route_circle = False

        self._state_info_text = None
        self._wait_time_state_info = 0.0

        base.taskMgr.add(self._loop, "vehicle-loop-%s" % self.name)


    def destroy (self):

        if not self.alive:
            return
        if self.engine_sound is not None:
            self.engine_sound.stop()
        for turret in self.turrets:
            turret.destroy()
        for launcher in self.launchers:
            launcher.destroy()
        if self._state_info_text is not None:
            self._state_info_text.removeNode()
        self._gyro.removeNode()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > self.minhitdmg:
            self.damage += obody.hitforce
        if obody.hitforce > self.maxhitdmg and self.damage < self.strength:
            self.damage = self.strength

        if self.damage >= self.strength:
            self.set_shotdown(5.0)

            d100 = randrange(100)
            if d100 < 66:
                self.explode_minor()

            fire_n_smoke_2(
                parent=self, store=None,
                sclfact = fx_uniform(0.5, 0.6) * self._size_xy,
                emradfact = fx_uniform(0.5, 0.7) * self._size_xy,
                zvelfact = 6.0,
                fcolor = rgba(255, 255, 255, 1.0),
                fcolorend = rgba(246, 112, 27, 1.0),
                ftcol = 0.5,
                flifespan = 0.8,
                fspacing=0.1,
                fpos = Vec3(0.0, 0.0, 1.0),
                fdelay = fx_uniform(0.1, 3.0),
                spos = Vec3(0.0, 0.0, 1.0),
                stcol = 0.4,
                slifespan = 4.0)

            for turret in self.turrets:
                turret.set_ap()

            # Switch to shotdown model.
            # Or set shotdown maps.
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
            elif self._shotdown_change_maps:
                for model in self.models:
                    set_texture(model,
                                texture=self._shotdown_texture,
                                normalmap=self._shotdown_normalmap,
                                glowmap=self._shotdown_glowmap,
                                glossmap=self._shotdown_glossmap,
                                shadowmap=self.world.shadow_texture)

            # Set up breakup.
            for handle in ("misc",):
                if randunit() > 0.0:
                    for model in self.models:
                        nd = model.find("**/%s" % handle)
                        if not nd.isEmpty():
                            nd.removeNode()
            selected_breakupdata = []
            selected_handles = set()
            accum_handle_prob = {}
            for bkpd in self.breakupdata:
                if bkpd.handle not in selected_handles:
                    ref_prob = randunit()
                    if bkpd.handle not in accum_handle_prob:
                        accum_handle_prob[bkpd.handle] = 0.0
                    ref_prob -= accum_handle_prob[bkpd.handle]
                    if bkpd.breakprob >= ref_prob:
                        selected_breakupdata.append(bkpd)
                        selected_handles.add(bkpd.handle)
                    else:
                        accum_handle_prob[bkpd.handle] += bkpd.breakprob
            if selected_breakupdata:
                for bkpd in selected_breakupdata:
                    for model in self.models:
                        nd = model.find("**/%s" % bkpd.handle)
                        subnd = nd.find("**/%s_misc" % bkpd.handle)
                        if not subnd.isEmpty():
                            subnd.removeNode()
                    if bkpd.texture is None:
                        bkpd.texture = self.texture
                GroundBreakup(self, selected_breakupdata)

            self._ap_active = True
            self._ap_pause = 0.0

            self.world.remove_body_on_count(self)

        return False


    def explode (self, destroy=True, offset=None):

        if not self.alive:
            return

        exp = PolyExplosion(
            world=self.world, pos=self.pos(offset=offset),
            firepart=3, smokepart=3,
            sizefac=6.0, timefac=1.0, amplfac=1.4,
            smgray=pycv(py=(10,30), c=(220, 255)), debrispart=(3, 5),
            debrispitch=(10, 80),
            debristcol=0.1)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()
        # if destroy:
            # self.destroy()
        # self.world.explosion_damage(self.hitforce * 0.2, self)


    def explode_minor (self, offset=None):

        exp = PolyExplosion(
            world=self.world, pos=self.pos(offset=offset),
            sizefac=1.0, timefac=0.4, amplfac=0.6,
            smgray=pycv(py=(65,80), c=(220, 255)), smred=0)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()


    def zero_inputs (self):

        self.path = None
        self.pspeed = None


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        speed = self.speed()

        # Turn wheels.
        for axlend, wheelrad in self._axles:
            if axlend.isEmpty():
                continue
            daxlerot = degrees(-(speed / wheelrad) * dt)
            axlerot = axlend.getP() + daxlerot
            axlend.setP(axlerot)

        # Turn tracks.
        for tracknd, spdfac, uvoff, uvscr in self._tracks:
            if tracknd.isEmpty():
                continue
            uvoff[1] += speed * spdfac * dt
            uvoff[1] -= floor(uvoff[1])
            uvscr.setColor(uvoff)

        # Set engine sound volume based on throttle.
        if self.engine_sound is not None:
            sfac = self._throttle
            engvol = self.engminvol + sfac * (self.engmaxvol - self.engminvol)
            self.engine_sound.set_volume(engvol)

        # Apply autopilot.
        self._ap_pause -= dt
        if self._ap_active and self._ap_pause <= 0.0:
            if not self.controlout:
                minwait = self._ap_adjperiod - self._ap_adjpfloat
                maxwait = self._ap_adjperiod + self._ap_adjpfloat
                adjperiod1 = uniform(minwait, maxwait)
                if self._ap_target:
                    if self._ap_target.alive and not self._ap_target.shotdown:
                        pass
                        #self._ap_input_attack(self._ap_pause)
                    else:
                        self.set_ap(speed=0.0, turnrate=0.0)
                else:
                    self._ap_pause = adjperiod1
                    self._ap_input_nav(self._ap_pause)
            else:
                self._ap_pause = 0.0
                self._ap_input_shotdown(dt)

        if self._state_info_text is not None:
            self._update_state_info(dt)

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        if dt == 0.0:
            return

        pos, hpr, tdir, ndir, hdir, tspf = self._prev_gfix
        tvelg, = self._prev_dyn
        zdir = Vec3D(0, 0, 1)

        if self._prev_path is not self.path: # must come before next check
            self._prev_path = self.path
            self._path_pos = 0.0
        if self.path is None or self.path.length() < self._path_pos:
            if self.path is not None:
                ptdir = self.path.tangent(self.path.length())
            else:
                ptdir = hdir
            self.path = Segment(Vec3D(), ptdir * 1e5, zdir)
            self._prev_path = self.path
            self._path_pos = 0.0

        slope = radians(hpr[1])
        speed = tvelg / cos(slope)
        turnrate = self.turnrate()

        if self.pspeed is None:
            self.pspeed = speed

        optspeed, maxspeed = self.limspeeds(slope=slope, tspf=tspf)
        self.pspeed = clamp(self.pspeed, 0.0, maxspeed)
        ret = self.limaccs(slope=slope, tspf=tspf,
                           speed=speed, turnrate=turnrate)
        minacc, maxacc, maxaccv0 = ret
        dspeed = self.pspeed - speed
        if dspeed >= 0.0:
            tacc = min(dspeed * 0.5, maxacc)
        else:
            tacc = max(dspeed * 20.0, minacc)

        s = self._path_pos
        if abs(speed) > 0.0 or abs(tacc) > 0.0:
            dpg = self.path.point(s)
            taccg = tacc * cos(slope)
            s1 = s + tvelg * dt + taccg * (0.5 * dt**2)
            dp1g = self.path.point(s1)
            tvel1g = tvelg + taccg * dt
            t1g = self.path.tangent(s1)
            vel1g = t1g * tvel1g
            dposg = dp1g - dpg
            dpos = dposg # slope not important
            self._path_pos = s1
            h1 = degrees(atan2(-t1g[0], t1g[1]))
            dhpr = Vec3D(h1 - hpr[0], 0, 0) # slope not important
        else:
            taccg = 0.0
            tvel1g = 0.0
            s1 = s
            dpos = Vec3D()
            dhpr = Vec3D()

        if dpos.lengthSquared() > 0.0 or dhpr.lengthSquared() > 0.0:
            gfix1 = Vehicle._fix_to_ground(self.world, self._gyro,
                                           self._modgndcnts, self.sink,
                                           pos + dpos, hpr + dhpr)
        else:
            gfix1 = self._prev_gfix
        pos1, hpr1, tdir1, ndir1, hdir1, tspf1 = gfix1
        self._prev_gfix = gfix1
        self._prev_dyn = (tvel1g,)

        self.node.setPos(ptof(pos1))
        self.node.setHpr(vtof(hpr1))

        slope1 = radians(hpr1[1])
        vel = tdir1 * (tvel1g / cos(slope1))
        n1g = self.path.normal(s1)
        r1g = self.path.radius(s1)
        acc = tdir1 * (taccg / cos(slope1)) + n1g * (tvel1g**2 / r1g)
        self._prev_vel = Vec3(self._vel) # needed in base class
        self._vel = vtof(vel) # needed in base class
        self._acc = vtof(acc) # needed in base class

        # Derive throttle level, needed for effects.
        self._throttle = 1.0 - maxacc / (maxaccv0 or 1e-5)
        self._throttle = clamp(self._throttle, 0.0, 1.0)


    @staticmethod
    def _fix_to_ground (world, gyro, gcont, sink, pos1, hpr1):

        # NOTE: Use only rotation on gyro, to avoid single-precision
        # roundoff errors due to large translations.

        # Compute approximate ground contact plane as if
        # the rotation were only by heading.
        gyro.setHpr(hpr1[0], 0.0, 0.0)
        gcpcs = []
        for rgcp in gcont:
            gcp1c = ptod(world.node.getRelativePoint(gyro, rgcp))
            elv = world.elevation(pos1 + gcp1c)
            gcpc = Point3D(gcp1c[0], gcp1c[1], gcp1c[2] + elv)
            gcpcs.append(gcpc)
        gcfc, gclc, gcrc = gcpcs
        ndir = unitv((gclc - gcfc).cross(gcrc - gcfc))  # plane normal
        gpz = (gcfc[2] + gclc[2] + gcrc[2]) / 3
        gp = Point3D(pos1[0], pos1[1], gpz)  # referent plane point

        # Compute true position and rotation
        # by keeping the x and y position and the heading rotation,
        # and projecting the rest to the approximate ground contact plane.
        h1 = radians(hpr1[0])
        hdir = Vec3D(-sin(h1), cos(h1), 0.0)
        tdirz = -(hdir[0] * ndir[0] + hdir[1] * ndir[1]) / ndir[2]
        tdir = unitv(Vec3D(hdir[0], hdir[1], tdirz))
        gyro.lookAt(ptof(tdir), vtof(ndir))
        cp = ptod(world.node.getRelativePoint(gyro, gcont[0]))
        posz = (- ((pos1[0] + cp[0] - gp[0]) * ndir[0] +
                   (pos1[1] + cp[1] - gp[1]) * ndir[1]) / ndir[2]
                - (cp[2] - gp[2]))
        pos = Point3D(pos1[0], pos1[1], posz)
        if sink:
            pos += ndir * -sink
        hpr = vtod(gyro.getHpr())

        # Speed reduction factor for terrain type.
        tspf = 1.0  #!!! read from terrain

        return pos, hpr, tdir, ndir, hdir, tspf


    def limspeeds (self, slope=None, tspf=None):

        if slope is None:
            slope = radians(self.hpr()[1])
        if tspf is None:
            tspf = 1.0  #!!! read from terrain

        if slope >= 0.0 and slope <= self.maxslope:
            rfac = (self.maxslope - slope) / self.maxslope
            maxspeed = self.maxspeed * rfac
        elif slope > self.maxslope:
            maxspeed = 0.0
        elif slope < 0.0:
            maxspeedplus = self.maxspeed * 1.0
            pfac = (-slope) / (0.5 * pi)
            maxspeed = self.maxspeed + maxspeedplus * pfac

        maxspeed *= tspf

        optspeed = 0.8 * maxspeed #!!!

        return optspeed, maxspeed


    def limturnrates (self, slope=None, tspf=None, speed=None):

        if slope is None:
            slope = radians(self.hpr()[1])
        if tspf is None:
            tspf = 1.0  #!!! read from terrain
        if speed is None:
            speed = self.speed()

        optspeed, maxspeed = self.limspeeds(slope=slope, tspf=tspf)
        maxturnspeed = 2.0 #!!!
        zeroturnspeed = max(1.2 * maxspeed, 2 * maxturnspeed)
        if speed <= zeroturnspeed:
            if speed < maxturnspeed:
                sfac = speed / maxturnspeed
            else:
                sfac = 1.0 - (speed - maxturnspeed) / (zeroturnspeed - maxturnspeed)
            maxturnrate = self.maxturnrate * sfac
        else:
            maxturnrate = 0.0

        return maxturnrate


    def limaccs (self, slope=None, tspf=None, speed=None, turnrate=None):

        if slope is None:
            slope = radians(self.hpr()[1])
        if tspf is None:
            tspf = 1.0  #!!! read from terrain
        if speed is None:
            speed = self.speed()
        if turnrate is None:
            turnrate = self.turnrate()

        maxthracc = self.maxthracc
        maxvdracc = self.maxvdracc
        maxslope = self.maxslope

        # Terrain influence.
        maxthracc *= tspf
        maxvdracc *= 0.5 + 0.5 / tspf

        # Speed influence.
        optspeed, maxspeed = self.limspeeds(slope=slope, tspf=tspf)
        if speed < maxspeed and maxspeed > 0:
            sfac = speed / maxspeed
            maxacc = maxthracc * (1.0 - sfac)
        else:
            maxacc = 0.0
        minacc = -self.maxbracc * (0.5 + 0.5 / tspf)
        maxaccv0 = maxthracc

        # Slope influence.
        if slope > maxslope:
            sfac = (slope - maxslope) / (0.5 * pi - maxslope)
            sdacc = -maxacc - (self.world.absgravacc - maxthracc) * sfac
        elif slope > 0.0:
            sdacc = -maxacc * (slope / maxslope)
        else:
            sdacc = self.world.absgravacc * -sin(slope)
        minacc += sdacc
        maxacc += sdacc
        maxaccv0 += sdacc

        # Turn rate influence.
        maxturnrate = self.limturnrates(slope=slope, tspf=tspf, speed=speed)
        if maxacc > 0.0:
            maxturnrate_mod = maxturnrate
            # Bound max turn rate from below,
            # so that the following correction does not explode.
            minmaxturnrate = radians(1.0)
            if maxturnrate_mod < minmaxturnrate:
                maxturnrate_mod = minmaxturnrate
            # Reduce maxacc to zero when max turn rate reached.
            tdacc = -maxacc * (abs(turnrate) / maxturnrate_mod)
        else:
            # Add some more arbitrary reduction to acceleration.
            trfac = 2.0
            tdacc = -maxvdracc * abs(turnrate) * trfac
        minacc += tdacc
        maxacc += tdacc

        return minacc, maxacc, maxaccv0


    def set_route (self, points, patrol=False, circle=False):

        self._route_points = points
        self._route_patrol = patrol
        self._route_circle = circle
        self._route_current_point = 0
        self._route_point_inc = 1


    def set_ap (self,
                speed=None, turnrate=None, heading=None, point=None,
                enroute=False, target=None):

        if self.controlout:
            return

        self._ap_speed = speed
        self._ap_turnrate = turnrate
        self._ap_heading = heading
        self._ap_point = point
        self._ap_target = target
        self._ap_enroute = enroute

        self._ap_active = True
        self._ap_pause = 0.0


    def zero_ap (self):

        if self.controlout:
            return

        self.set_ap()

        self._ap_active = False


    def _ap_input_nav (self, adt):

        w = self.world

        #print "========== ap-vehicle-nav-start (world-time=%.2f)" % (w.time)

        tspeed = self._ap_speed
        tturnrate = self._ap_turnrate
        thead = self._ap_heading
        tpoint = self._ap_point
        tenroute = self._ap_enroute

        if tturnrate is not None:
            tturnrate = radians(tturnrate)
        if thead is not None:
            thead = radians(thead)

        pos, hpr, tdir, ndir, hdir, tspf = self._prev_gfix
        posg = Point3D(pos[0], pos[1], 0.0)
        zdir = Point3D(0, 0, 1)
        head = radians(hpr[0])
        slope = radians(hpr[1])
        vel = vtod(self.vel())
        speed = vel.length()
        turnrate = self.turnrate()
        optspeed, maxspeed = self.limspeeds(slope=slope, tspf=tspf)
        maxturnrate = self.limturnrates(slope=slope, tspf=tspf, speed=speed)

        # Correct targets for route target.
        break_on_tpoint = True
        if tenroute:
            if self._route_current_point is not None:
                rpos = self._route_points[self._route_current_point]
                rposg = Point3D(rpos[0], rpos[1], 0.0)
                rptdist = (rposg - posg).length()
                minturnrad = speed / max(maxturnrate, 1e-2)
                if rptdist < max(1.5 * minturnrad, 2.0 * self._length):
                    # Select next point.
                    np = self._route_current_point + self._route_point_inc
                    npts = len(self._route_points)
                    if not (0 <= np < npts):
                        if self._route_patrol:
                            if self._route_circle:
                                if np < 0:
                                    np = npts - 1
                                else:
                                    np = 0
                            else:
                                self._route_point_inc *= -1
                                np += 2 * self._route_point_inc
                        else:
                            np = None
                    # If next point is not final, cancel breaking at it.
                    if np is not None:
                        npp = np + self._route_point_inc
                        if self._route_patrol or 0 <= npp < npts:
                            break_on_tpoint = False
                    self._route_current_point = np
                    #print "--vhc-route-next-point", self.name, np, self._route_points[np]
                else:
                    tpoint = rpos
                    thead = None
            else:
                # No route, stop.
                tpoint = None
                tspeed = 0.0
                tturnrate = 0.0
                thead = head

        # Correct targets for point target.
        if tpoint is not None:
            tpointg = Point3D(tpoint[0], tpoint[1], 0.0)
            # Set target heading based on given point, ignoring any given.
            dpos = vtod(tpointg) - posg
            thead = atan2(-dpos.getX(), dpos.getY())
            tturnrate = None
            ptdist = dpos.length()
            if break_on_tpoint and ptdist < 1.0 * self._length:
                # Arrived, stop.
                tpoint = None
                tspeed = 0.0
                tturnrate = 0.0
                thead = head

        # Determine updated speed.
        if tpoint is not None:
            speed1 = None
            if break_on_tpoint:
                # Compute stopping distance with a bit smaller deceleration
                # than actual; don't break like mad.
                ret = self.limaccs(slope=slope, tspf=tspf,
                                   speed=speed, turnrate=turnrate)
                minacc, maxacc, maxaccv0 = ret
                bracc = minacc * 0.5
                brtime = speed / -bracc
                brdist = speed * brtime + bracc * (0.5 * brtime**2)
                if brdist > ptdist:
                    dcacc = bracc * 1.2
                    speed1 = speed + dcacc * adt
            if speed1 is None:
                if tspeed is not None:
                    speed1 = tspeed
                else:
                    speed1 = optspeed
        elif tspeed is not None:
            speed1 = tspeed
        else:
            speed1 = speed

        # Determine updated turn rate.
        if tturnrate is not None:
            turnrate1 = tturnrate
        elif thead is not None:
            atime = 2.0 # !!!
            dhead = norm_ang_delta(head, thead)
            turnrate1 = clamp(dhead / atime, -maxturnrate, maxturnrate)
        else:
            turnrate1 = 0.0

        # Input path.
        head1 = thead if thead is not None else head
        rad01 = abs(speed / turnrate1) if abs(turnrate1) > 1e-5 else 1e30
        dhead = norm_ang_delta(head, head1)
        if abs(dhead) > 1e-6:
            etime = adt + 0.5
            rad01b = abs(speed * etime / dhead)
            rad01 = max(rad01, rad01b)
        infrad = 1e6
        indhead = (rad01 < infrad and abs(dhead) > 1e-6)
        if indhead:
            rdir = zdir.cross(hdir) * sign(dhead)
            path1 = Arc(rad01, abs(dhead), Vec3D(), hdir, rdir)
        else:
            path1 = Segment(Vec3D(), hdir * 1e5, zdir)
        self.path = path1

        # Input speed.
        self.pspeed = speed1

        # Unused inputs.
        pass


    def _ap_input_shotdown (self, adt):

        self.pspeed = 0.0


    def set_lights (self, on):

        for lnd in self._lights:
            if on:
                lnd.setShaderInput(self.world.shdinp.glowfacn, 1.0)
            else:
                lnd.setShaderInput(self.world.shdinp.glowfacn, 0.0)


    def jump_to (self, pos=None, hpr=None, speed=None):

        gfix = self._fix_to_ground(self.world, self._gyro,
                                   self._modgndcnts, self.sink,
                                   ptod(pos), vtod(hpr))
        pos1, hpr1 = gfix[:2]

        Body.jump_to(self, ptof(pos1), vtof(hpr1), speed)

        self.node.setPos(ptof(pos1))
        self.node.setHpr(vtof(hpr1))
        self._prev_gfix = gfix

        tvelg = speed
        self._prev_dyn = (tvelg,)

        self.zero_inputs()
        self.set_ap()


    def show_state_info (self, pos, align="l", anchor="tl"):

        if self._state_info_text is None:
            self._state_info_text = make_text(
                text="", width=1.0, size=10, align=align, anchor=anchor,
                shcolor=rgba(0, 0, 0, 1), parent=self.world.node2d)
        self._state_info_text.setPos(pos)
        self._state_info_text.show()


    def hide_state_info (self):

        if self._state_info_text is not None:
            self._state_info_text.hide()


    def _update_state_info (self, dt):

        if self._state_info_text.isHidden():
            return
        if self._wait_time_state_info > 0.0:
            self._wait_time_state_info -= dt
            return
        self._wait_time_state_info = fx_uniform(1.0, 2.0)

        d = degrees

        ls = []
        ls.append("name: %s" % self.name)
        pos = self.pos()
        ls.append("position: x=%.1f y=%.1f z=%.1f [m]" % tuple(pos))
        hpr = self.hpr()
        ls.append("heading: % .1f [deg]" % to_navhead(hpr[0]))
        speed = self.speed()
        optspeed, maxspeed = self.limspeeds()
        ls.append("speed: %.1f (%.1f/%.1f) [m/s]" %
                  (speed, optspeed, maxspeed))
        turnrate = self.turnrate()
        maxturnrate = self.limturnrates()
        ls.append("turn-rate: % .1f (% .1f) [deg/s]"
                  % (d(turnrate), d(maxturnrate)))
        facc = self.acc(self)[1]
        minacc, maxacc, maxaccv0 = self.limaccs()
        ls.append("path-acceleration: % .1f (% .1f/% .1f) [m/s^2]"
                  % (facc, minacc, maxacc))
        ls.append("slope: % .1f [deg]" % hpr[1])
        text = "\n".join(ls)

        update_text(self._state_info_text, text=text)


