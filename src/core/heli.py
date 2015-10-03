# -*- coding: UTF-8 -*-

from math import degrees

from pandac.PandaModules import Vec3, Vec3D, Vec4, Point3, QuatD
from pandac.PandaModules import TransparencyAttrib

from src import pycv
from src.core.body import Body
from src.core.curve import Segment
from src.core.debris import AirBreakup
from src.core.effect import fire_n_smoke_1
from src.core.fire import PolyExplosion
from src.core.misc import clamp, unitv, vtod, vtof, qtod, qtof, to_navhead
from src.core.misc import AutoProps, rgba, remove_subnodes, set_texture
from src.core.misc import make_text, update_text, load_model_lod_chain
from src.core.misc import uniform, randrange, randunit
from src.core.misc import fx_uniform, fx_choice
from src.core.rocket import Rocket, Launcher
from src.core.sound import Sound3D
from src.core.trail import PolyBraid


class Heli (Body):

    family = "heli"
    species = "generic"
    longdes = None
    shortdes = None

    minmass = 8000.0
    maxmass = 12000.0
    maxspeed = 90.0
    strength = 12.0
    minhitdmg = 1.0
    maxhitdmg = 10.0
    dmgtime = 4.0
    rcs = 1.0
    irmuffle = 0.5
    iraspect = 0.8
    mainrpm = 400.0
    tailrpm = 1400.0

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
    modelpath = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    fmodelpath = None
    sdmodelpath = None
    shdmodelpath = None
    normalmap = None
    glowmap = rgba(0,0,0, 0.1)
    glossmap = None
    engsoundname = None
    engminvol = 0.0
    engmaxvol = 0.4
    breakupdata = []

    def __init__ (self, world, name, side, texture=None,
                  pos=None, hpr=None, speed=None,
                  damage=None, faillvl=None):

        if pos is None:
            pos = Point3()
        if hpr is None:
            hpr = Vec3()
        if speed is None:
            speed = 0.0

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
            hitforce=(self.minmass / 100.0),
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
            amblit=True, dirlit=True, pntlit=4, fogblend=True,
            ltrefl=(self.glossmap is not None),
            shdshow=True, shdmodind=shdmodind,
            pos=pos, hpr=hpr, vel=speed)

        self.mass = self.minmass

        width, length = self.bbox.getXy()
        self.size = (width + length) / 2
        self._size_xy = min(width, length)

        for mlevel, model in enumerate(self.models):
            # remove_subnodes(model, ("FWDstrut", "nose_strut", "Lstrut", "main_left_strut", "main_left_strut_1", "main_left_strut_2", "Rstrut", "main_right_strut", "main_right_strut_1", "main_right_strut_2", "FWDgear", "nose_wheel", "Lgear", "main_left_wheel", "main_left_wheel_1", "main_left_wheel_2", "Rgear", "main_right_wheel", "main_right_wheel_1", "main_right_wheel_2", "hose_left", "hose_middle", "hose_right")) # !!! Temporary
            self._init_model(model, mlevel)

        # Detect shotdown maps.
        self._shotdown_texture = self.texture
        self._shotdown_normalmap = self.normalmap
        self._shotdown_glowmap = self.glowmap if not isinstance(self.glowmap, Vec4) else None
        self._shotdown_glossmap = self.glossmap
        self._shotdown_change_maps = False

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
                self._init_model(model, mlevel)

        # Detect rotors.
        self._rotors = {}
        max_mlevel_rot = 0
        rotor_models = list(self.models)
        if base.with_world_shadows and self.shadow_node is not None:
            rotor_models += [self.shadow_node]
        if self.sdmodelpath:
            rotor_models += self._shotdown_models
        for rotname, rotrpm, rotaxid, rotdir in (
            ("rotor", self.mainrpm, 0, 1),
            ("rotor_counter", self.mainrpm, 0, -1),
            ("rotor_tail", self.tailrpm, 1, 1),
        ):
            rotnds = []
            for mlevel, model in enumerate(rotor_models):
                rotnd = model.find("**/%s" % rotname)
                if not rotnd.isEmpty():
                    rotnds.append(rotnd)
                    if mlevel < len(self.models): # due to shadow/shotdown model
                        max_mlevel_rot = max(max_mlevel_rot, mlevel)
            if rotnds:
                rs = AutoProps()
                rs.nodes = rotnds
                rs.rpm = rotrpm
                rs.axid = rotaxid
                rs.turndir = rotdir
                self._rotors[rotname] = rs
        if self._rotors:
            self._fardist_rotors = self.fardists[max_mlevel_rot]

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, maxdist=3000, limnum="hum",
                volume=0.0, loop=True, fadetime=2.5)
            self.engine_sound.play()
        else:
            self.engine_sound = None

        self._state_info_text = None
        self._wait_time_state_info = 0.0

        self._prev_path = None
        self._path_pos = 0.0
        self._throttle = 0.0

        self.cannons = []
        self.turrets = []
        self.launchers = []
        self.decoys = []

        self.damage_trails = []

        self.damage = damage or 0.0
        self.failure_level = faillvl or 0
        self.max_failure_level = 3
        self.must_not_explode = False
        for i in range(1, self.failure_level + 1):
            self._add_damage_trails(level=i)

        self._wait_damage_recovery = 0.0

        # Sensor signatures.
        self.ireqpower = 0.0
        self._maxpwr = self.maxmass * (0.25e3 * (self.maxspeed / 250.0))
        self._ireqpwrfac = self.irmuffle

        # Control inputs.
        self.zero_inputs()

        # Autopilot constants and state.
        self._ap_adjperiod = 2.0
        self._ap_adjpfloat = 0.4

        # Autopilot state.
        self.zero_ap()

        # Breakup.
        self._breakup_track_hits = []
        self._breakup_hit_time_range = 0.2

        base.taskMgr.add(self._loop, "heli-loop-%s" % self.name)


    def _init_pylon_handlers (self, pload):
        # NOTE: self.pylons must be set before call.

        for launcher in self.launchers:
            launcher.destroy()
        self.launchers = []

        if not pload:
            return

        if pload[0] == 1:
            # Direct placement, input is [(loadtype, (pylonindex, ...)), ...].
            pload = pload[1:] # remove placement type indicator
            for ptype, pindices in pload:
                if ptype is not None and pindices:
                    launcher = Launcher(ptype, points=pindices,
                                        rate=2.0, # !!!
                                        parent=self)
                    self.launchers.append(launcher)
        else:
            # Automatic placement, input is [(loadtype, numrounds), ...].
            # May contain a placement type indicator, remove it.
            if isinstance(pload[0], int):
                pload = pload[1:]
            nrounds_total = 0
            pqueue = list(enumerate(self.pylons))
            for ptype, nrounds in pload:
                points = []
                i = 0
                while nrounds > len(points) and i < len(pqueue):
                    pind, pylon = pqueue[i]
                    trst = pylon[2] if len(pylon) > 2 else ()
                    if ptype is None or not trst or issubclass(ptype, trst):
                        points.append(pind)
                        pqueue.pop(i)
                    else:
                        i += 1
                if ptype is not None:
                    if issubclass(ptype, Rocket):
                        launcher = Launcher(
                            ptype, points=points,
                            rate=2.0, #!!!
                            parent=self)
                        self.launchers.append(launcher)
                if not pqueue:
                    break


    def _init_model (self, model, mlevel):

        if mlevel == 0:
            for handle in ("Pilot", "pilot", "co_pilot"):
                geom = model.find("**/%s" % handle)
                if not geom.isEmpty():
                    set_texture(geom,
                        texture="models/aircraft/pilots/pilot_tex.png",
                        normalmap=-1, glowmap=None,
                        glossmap="models/aircraft/pilots/pilot_gls.png")

            for handle in (
                "canopy_glass", "canopy_glass_1", "canopy_glass_2",
                "canopy_windscreen", "canopy_back_glass"):
                geom = model.find("**/%s" % handle)
                if not geom.isEmpty():
                    geom.setTransparency(TransparencyAttrib.MAlpha)
        else:
            remove_subnodes(model, ("Pilot", "pilot"))


    def zero_inputs (self):

        self.path = None
        self.pspeed = None
        self.dspeed = None


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        pos = self.pos()

        if self.world.below_surface(pos):
            vel = self.vel()
            posg = self.world.intersect_surface(pos - vel * dt, pos)
            self.explode(pos=posg, ground=True)

        cdist = self.node.getDistance(self.world.camera)

        # Set engine sound volume.
        if self.engine_sound is not None:
            sfac = self._throttle
            engvol = self.engminvol + sfac * (self.engmaxvol - self.engminvol)
            self.engine_sound.set_volume(engvol)

        # Turn rotors.
        if self._rotors and cdist < self._fardist_rotors:
            for rs in self._rotors.values():
                dangdeg = (rs.rpm * 6.0) * dt * rs.turndir
                for rnd in rs.nodes:
                    hpr = rnd.getHpr()
                    hpr[rs.axid] += dangdeg
                    rnd.setHpr(hpr)

        # Set sensor signatures.
        pwr = self._maxpwr * self._throttle
        self.ireqpower = pwr * self._ireqpwrfac

        # Apply autopilot.
        self._ap_pause -= dt
        if self._ap_active and self._ap_pause <= 0.0:
            if not self.controlout:
                pass
            else:
                self._ap_input_shotdown(dt)

        if self._wait_damage_recovery > 0.0:
            self._wait_damage_recovery -= dt
            if self._wait_damage_recovery <= 0.0:
                self.damage = 0.0

        if self._state_info_text is not None:
            self._update_state_info(dt)

        return task.cont


    def destroy (self):

        if not self.alive:
            return
        for cannon in self.cannons:
            cannon.destroy()
        for turret in self.turrets:
            turret.destroy()
        for launcher in self.launchers:
            launcher.destroy()
        if self._state_info_text is not None:
            self._state_info_text.removeNode()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > self.minhitdmg:
            self.damage += obody.hitforce
        if obody.hitforce > self.maxhitdmg and self.damage < self.strength:
            self.damage = self.strength

        self._breakup_track_hits.append((obody.hitforce, self.world.time))

        while self.damage > self.strength:
            self.failure_level += 1

            if self.failure_level == 1:
                d100 = randrange(100)
                if d100 < 10:
                    self.explode_minor()
                self._add_damage_trails(level=1)
            elif self.failure_level == 2:
                d100 = randrange(100)
                if d100 < 15:
                    self.explode_minor()
                self._add_damage_trails(level=2)
            if randunit() < 0.20:
                self.failure_level = self.max_failure_level
            self.damage -= self.strength
        self._wait_damage_recovery = self.dmgtime

        if self.failure_level >= self.max_failure_level:
            self.set_shotdown(3.0)
            self.target = None

            d100 = randrange(100)
            if d100 < 20:
                self.explode_minor()
            else:
                snd = Sound3D(
                    "audio/sounds/%s.ogg" % "explosion01",
                    parent=self, volume=1.0, fadetime=0.1)
                snd.play()

            if self.engine_sound is not None:
                self.engine_sound.stop()
            for trail in self.damage_trails:
                trail.destroy()
            self.damage_trails = []

            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.11 * self._size_xy * fx_uniform(0.9, 1.2),
                emradfact=0.11 * self._size_xy * fx_uniform(0.9, 1.1),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(247, 203, 101, 1.0),
                ftcol=0.6,
                fpos=Vec3(0.0, 0.0, 0.0),
                fpoolsize=16,
                flength=24.0,
                fspeed=28,
                fdelay=fx_choice([0.1, fx_uniform(0.5, 6.0)]),
                spos=Vec3(0.0, 0.0, 0.0),
                slifespan=2.0,
                stcol=0.1)

            # Switch to shotdown model.
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists

            # Set up breakup.
            for handle in ("fixed_external_misc", "fixed_external_misc_1", "fixed_external_misc_2"):
                if randunit() > 0.6:
                    for model in self.models:
                        nd = model.find("**/%s" % handle)
                        if not nd.isEmpty():
                            nd.removeNode()
            ref_hitforce = 0
            while self._breakup_track_hits:
                hitforce, time = self._breakup_track_hits.pop()
                if time + self._breakup_hit_time_range < self.world.time:
                    break
                ref_hitforce = max(ref_hitforce, hitforce)
            selected_breakupdata = []
            for bkpd in self.breakupdata:
                ref_damage = randunit() * bkpd.limdamage
                if ref_damage < ref_hitforce:
                    selected_breakupdata.append(bkpd)
            if selected_breakupdata:
                for bkpd in selected_breakupdata:
                    for model in self.models:
                        nd = model.find("**/%s" % bkpd.handle)
                        subnd = nd.find("**/%s_misc" % bkpd.handle)
                        if not subnd.isEmpty():
                            subnd.removeNode()
                    if bkpd.texture is None:
                        bkpd.texture = self.texture
                for launcher in self.launchers:
                    launcher.destroy()
                AirBreakup(self, selected_breakupdata)

            # Set up falling autopilot.
            explode = False
            if not self.must_not_explode:
                totstrength = self.strength * self.max_failure_level
                if obody.hitforce > totstrength:
                    dc = (totstrength / obody.hitforce)**0.25
                    if randunit() > dc:
                        explode = True
            if not explode: #False:
                ap = self._init_shotdown_1(obody, chbx, cpos)
            else:
                ap = self._init_shotdown_2(obody, chbx, cpos)
            self._ap_input_shotdown = ap

        return False


    def explode (self, destroy=True, offset=None, pos=None, ground=False):

        if not self.alive:
            return

        if pos is None:
            pos = self.pos(offset=offset)
        elif offset is not None:
            pos = pos + offset
        if ground:
            debrispitch = (10, 80)
        else:
            debrispitch = (-45, 45)
        exp = PolyExplosion(
            world=self.world, pos=pos,
            firepart=3, smokepart=3,
            sizefac=0.4 * self._size_xy, timefac=1.2, amplfac=1.2,
            smgray=pycv(py=(10,30), c=(220, 255)), debrispart=(4, 6),
            debrispitch=debrispitch)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()
        if destroy:
            self.set_crashed()
            self.destroy()
        self.world.explosion_damage(self.hitforce * 0.2, self)


    def explode_minor (self, offset=None):

        exp = PolyExplosion(
            world=self.world, pos=self.pos(offset=offset),
            sizefac=1.0, timefac=0.5, amplfac=0.6,
            smgray=pycv(py=(45,60), c=(220, 255)), smred=0)
        snd = Sound3D(
            "audio/sounds/%s.ogg" % "explosion01",
            parent=exp, volume=1.0, fadetime=0.1)
        snd.play()


    def _add_damage_trails (self, level):

        dsclfact=self._size_xy * fx_uniform(0.8, 1.1)
        demradfact=self._size_xy * fx_uniform(0.8, 1.0)
        if level == 1:
            smk1 = PolyBraid(
                parent=self,
                pos=Vec3(0.0, 0.0, 0.0),
                numstrands=1,
                lifespan=0.2,
                thickness=0.12 * dsclfact,
                endthickness=0.6 * dsclfact,
                spacing=1.0,
                offang=None,
                offrad=0.08 * demradfact,
                offtang=0.0,
                randang=True,
                randrad=True,
                texture="images/particles/smoke6-1.png",
                glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
                color=pycv(py=rgba(31, 29, 28, 0.2), c=rgba(255, 239, 230, 0.2)),
                dirlit=pycv(py=False, c=True),
                alphaexp=2.0,
                segperiod=0.010,
                farsegperiod=pycv(py=0.020, c=None),
                maxpoly=pycv(py=500, c=1000),
                farmaxpoly=1000,
                dbin=3,
                loddistout=1400 * dsclfact,
                loddistalpha=1200 * dsclfact,
                loddirang=5,
                loddirspcfac=5)
            self.damage_trails.append(smk1)
        elif level == 2:
            smk2 = PolyBraid(
                parent=self,
                pos=Vec3(0.0, 0.0, 0.0),
                numstrands=1,
                lifespan=0.34,
                thickness=0.14 * dsclfact,
                endthickness=0.6 * dsclfact,
                spacing=1.0,
                offang=None,
                offrad=0.08 * demradfact,
                offtang=0.0,
                randang=True,
                randrad=True,
                texture="images/particles/smoke6-1.png",
                glowmap=pycv(py=rgba(255, 255, 255, 1.0), c=rgba(0, 0, 0, 0.1)),
                color=pycv(py=rgba(31, 29, 28, 0.4), c=rgba(255, 239, 230, 0.4)),
                dirlit=pycv(py=False, c=True),
                alphaexp=2.0,
                segperiod=0.010,
                farsegperiod=pycv(py=0.020, c=None),
                maxpoly=pycv(py=500, c=1000),
                farmaxpoly=1000,
                dbin=3,
                loddistout=1400 * dsclfact,
                loddistalpha=1200 * dsclfact,
                loddirang=5,
                loddirspcfac=5)
            self.damage_trails.append(smk2)


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        if dt == 0.0:
            return

        mass = self.mass
        pos = vtod(self.pos())
        alt = pos[2]
        vel = vtod(self.vel())
        vdir = Vec3D(vel)
        vdir.normalize()
        speed = vel.length()
        quat = qtod(self.quat())
        udir = quat.getUp()
        fdir = quat.getForward()
        rdir = quat.getRight()
        zdir = Vec3D(0.0, 0.0, 1.0)
        angvel = vtod(self.angvel())
        relangvel = vtod(self.angvel(self))
        ppitch = self.ppitch()
        turnrate = self.turnrate()

        if self._prev_path is not self.path: # must come before next check
            self._prev_path = self.path
            self._path_pos = 0.0
        if self.path is None or self.path.length() < self._path_pos:
            tdir = fdir
            ndir = udir
            if self.path is not None:
                tdir = self.path.tangent(self.path.length())
                ndir = self.path.normal(self.path.length())
            self.path = Segment(Vec3D(), tdir * 1e5, ndir)
            self._prev_path = self.path
            self._path_pos = 0.0

        if self.pspeed is None:
            self.pspeed = speed

        # ====================
        # Translation.

        maxspeed = self.maxspeed
        maxacc = 5.0 #!!!
        minacc = -5.0 #!!!
        if self.dspeed is None:
            self.pspeed = clamp(self.pspeed, 0.0, maxspeed)
            dspeed = self.pspeed - speed
            if dspeed >= 0.0:
                tacc = min(dspeed * 0.5, maxacc)
            else:
                tacc = max(dspeed * 0.5, minacc)
        else:
            tacc = self.dspeed / dt

        s = self._path_pos
        dp = self.path.point(s)
        t = self.path.tangent(s)
        tvel = vel.dot(t)
        s1 = s + tvel * dt + tacc * (0.5 * dt**2)
        dp1 = self.path.point(s1)
        tvel1 = tvel + tacc * dt
        t1 = self.path.tangent(s1)
        vel1 = t1 * tvel1
        dpos = dp1 - dp
        #acc = (dpos - vel * dt) / (0.5 * dt**2)
        n1 = self.path.normal(s1)
        r1 = self.path.radius(s1)
        acc = t1 * tacc + n1 * (tvel1**2 / r1)
        self._path_pos = s1
        #print "% .4e % .4e % .4e" % (dt, dpos[2], dpos[2] / dt)

        self.node.setPos(vtof(pos + dpos))
        self._prev_vel = Vec3(self._vel) # needed in base class
        self._vel = vtof(vel1) # needed in base class
        self._acc = vtof(acc) # needed in base class

        # Derive throttle level, needed for effects and sensor signatures.
        limspeed1 = maxspeed * 0.1
        limspeed2 = maxspeed * 0.5
        minthrottle = 0.6
        if speed < limspeed1:
            self._throttle = 1.0
        elif speed < limspeed2:
            sfac = (speed - limspeed1) / (limspeed2 - limspeed1)
            self._throttle = minthrottle + (1.0 - minthrottle) * (1.0 - sfac**2)
        else:
            sfac = (speed - limspeed2) / (maxspeed - limspeed2)
            self._throttle = minthrottle + (1.0 - minthrottle) * sfac**2
        self._throttle = clamp(self._throttle, 0.0, 1.0)

        # ====================
        # Rotation.

        r = r1

        yaxis = zdir
        fdir1 = t1
        yfdir = unitv(fdir - yaxis * fdir.dot(yaxis))
        yfdir1 = unitv(fdir1 - yaxis * fdir1.dot(yaxis))
        if yfdir.length() > 0.5 and yfdir1.length() > 0.5:
            dsyaw = yfdir.signedAngleRad(yfdir1, yaxis)
        else:
            dsyaw = 0.0
        ydang = dsyaw
        ydquat = QuatD()
        ydquat.setFromAxisAngleRad(ydang, yaxis)

        dquat = ydquat
        quat1 = quat * dquat

        angvel1 = (yaxis * ydang) / dt
        angacc = (angvel1 - angvel) / dt

        self.node.setQuat(qtof(quat1))
        self._angvel = vtof(angvel1) # needed in base class
        self._angacc = vtof(angacc) # needed in base class


    def zero_ap (self):

        if self.controlout:
            return

        self.set_ap()

        self._ap_active = False


    def set_ap (self):

        if self.controlout:
            return

        self._ap_active = True
        self._ap_pause = 0.0


    def _init_shotdown_1 (self, obody, chbx, cpos):

        self._ap_active = True
        self._ap_pause = 0.0

        return self._ap_input_shotdown_1


    def _ap_input_shotdown_1 (self, adt):

        #print "===== ap-heli-shotdown-1-start (world-time=%.2f)" % (w.time)

        self._ap_input_flat_fall(adt)

        #print "===== ap-heli-shotdown-1-end"


    def _init_shotdown_2 (self, obody, chbx, cpos):

        self._fall_time0 = self.world.time

        self._ap_active = True
        self._ap_pause = 0.0

        return self._ap_input_shotdown_2


    def _ap_input_shotdown_2 (self, adt):

        if self.world.time - self._fall_time0 > 1.0:
            self.explode()

        self._ap_input_flat_fall(adt)


    def _ap_input_flat_fall (self, adt):

        w = self.world

        vel = vtod(self.vel())
        speed = vel.length()
        min_speed = 0.01
        if speed < min_speed:
            speed = min_speed
            vel = vtod(self.quat().getForward()) * speed
        vel1 = vel + vtod(w.gravacc) * w.dt
        vdir1 = unitv(vel1)
        zdir = Vec3D(0.0, 0.0, 1.0)
        ndir1 = unitv(vdir1.cross(zdir).cross(vdir1))
        self.path = Segment(Vec3D(), vel1 * w.dt, ndir1)
        speed1 = vel1.length()
        self.dspeed = speed1 - speed


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
        alt = pos[2]
        ls.append("position: x=%.1f y=%.1f z=%.1f [m]" % tuple(pos))
        otralt = self.world.otr_altitude(pos)
        ls.append("altitude: % .1f (% .1f) [m]" % (alt, otralt))
        vel = self.vel()
        head = math.atan2(-vel[0], vel[1])
        ls.append("heading: % .1f [deg]" % to_navhead(d(head)))
        speed = vel.length()
        ls.append("speed: %.1f (%.1f) [m/s]" % (speed, self.maxspeed))
        text = "\n".join(ls)

        update_text(self._state_info_text, text=text)


