# -*- coding: UTF-8 -*-

from math import degrees, radians, pi, sin, cos, asin, acos, tan, atan, atan2
from math import sqrt
import os

from direct.directtools.DirectGeometry import LineNodePath
from pandac.PandaModules import Vec2, Vec3, Vec4, Vec3D, Point2, Point3, Point3D
from pandac.PandaModules import NodePath, Quat, QuatD
from pandac.PandaModules import TransparencyAttrib

from src import join_path, path_exists, path_dirname, path_basename
from src import pycv
from src.core.body import Body
from src.core.bomb import Bomb, Dropper
from src.core.curve import Segment, Arc, HelixZ, ArcedHelixZ
from src.core.decoy import FlareChaff
from src.core.debris import AirBreakup
from src.core.droptank import DropTank, Tanker
from src.core.effect import fire_n_smoke_1, fire_n_smoke_4
from src.core.fire import Splash, PolyExplosion
from src.core.jammer import Jammer, JammingPod, JammingCarpet
from src.core.misc import AutoProps, SimpleProps, rgba
from src.core.misc import remove_subnodes, set_texture
from src.core.misc import load_model_lod_chain, load_model
from src.core.misc import sign, clamp, unitv, ptod, vtod, vtof, norm_ang_delta
from src.core.misc import set_hpr_vfu, update_towards, hprtovec
from src.core.misc import intl01r, intl01v, intl10r
from src.core.misc import line_intersect_2d, pos_from_horiz, great_circle_dist
from src.core.misc import to_navhead, make_text, update_text
from src.core.misc import randunit, uniform, randrange, choice
from src.core.misc import fx_uniform, fx_choice
from src.core.misc import report, debug, dbgval
from src.core.planedyn import GROUND, AIRBRAKE, FLAPS
from src.core.planedyn import PlaneDynamics, PlaneSkill
from src.core.podrocket import RocketPod, PodLauncher
from src.core.rocket import Rocket, Launcher
from src.core.sensor import SIZEREF, SensorPack
from src.core.sensor import FighterVisual, TransportVisual, Radar, Irst, Tv
from src.core.sensor import Rwr, Comm, DataLink, MagicTargeted
from src.core.sensor import FighterVisualCollisionWarning
from src.core.sensor import TransportVisualCollisionWarning
from src.core.shader import make_shader
from src.core.shell import Shell, Cannon
from src.core.sound import Sound3D, Sound2D
from src.core.trail import PolyBraid, PolyExhaust, PolyTrail


VISTYPE = SimpleProps(
    NONE="", # must evaluate to False
    FIGHTER="fighter",
    TRANSPORT="transport",
)


# FIXME: Move all autopilot computations to PlaneDynamics.

class Plane (Body):

    family = "plane"
    species = "generic"
    longdes = None
    shortdes = None

    # Dynamics parameters.
    minmass = 10000.0
    maxmass = 20000.0
    wingarea = 40.0
    wingaspect = 4.0
    wingspeff = 0.70
    zlaoa = radians(0.0)
    maxaoa = radians(20.0)
    maxthrust = 40e3 * 2
    maxthrustab = 70e3 * 2
    thrustincab = 1.4
    maxload = 8.0
    refmass = 11000.0
    maxspeedz = 310.0
    maxspeedabz = 400.0
    maxclimbratez = 250.0
    cloptspeedz = 290.0
    maxspeedh = 290.0
    maxspeedabh = 600.0
    maxrollratez = radians(100.0)
    maxpitchratez = radians(20.0)
    maxfuel = 4000.0
    refsfcz = 0.80 / 3.6e4
    refsfcabz = 2.00 / 3.6e4
    sfcincab = 1.1
    reldragbrake = 2.0
    maxflapdeflect = radians(30.0)
    maxflapdeltzlaoa = radians(-10.0)
    maxflapdeltmaxaoa = radians(-5.0)
    maxflapdeltreldrag = 2.0
    midflapdeflect = radians(10.0)
    midflapdeltzlaoa = radians(-5.0)
    midflapdeltmaxaoa = radians(-2.0)
    midflapdeltreldrag = 0.5
    maxlandspeed = 140.0
    maxlandsinkrate = 8.0
    maxlandrotangle = radians(20.0)
    minlandrotangle = radians(-2.0)
    maxlandrollangle = radians(20.0)
    reldragwheelbrake = 20.0
    reldragwheel = 1.0
    groundcontact = [Point3(0.0, 3.0, -1.5),
                     Point3(1.5, -0.5, -1.5),
                     Point3(-1.5, -0.5, -1.5)]
    groundcanland = (GROUND.RUNWAY, GROUND.DIRT, GROUND.GRASS, GROUND.ICE)
    varsweepmach = None

    # Other simulation parameters.
    strength = 8.0
    minhitdmg = 0.0
    maxhitdmg = 6.0
    dmgtime = 4.0
    visualtype = VISTYPE.FIGHTER
    visualangle = (radians(90 + 10.0), radians(90 - 10.0), radians(180 - 20.0))
    radarrange = 50000.0
    radarangle = (radians(30.0), radians(30.0), radians(30.0))
    irstrange = None
    irstangle = None
    tvrange = None
    tvangle = None
    rwrwash = None
    datalinkrecv = True
    datalinksend = False
    rcs = 5.0
    irmuffle = 1.0
    iraspect = 0.5

    # Decoy parameters.
    flarechaff = 40
    flchlaunchtype = 0
    flchvistype = 0
    flchmanouver = True

    # Effects parameters.
    hitboxdata = []
    hitboxcritdata = []
    hitdebris = None
    #hitdebris = AutoProps(
        ##firetex="images/particles/explosion1.png",
        ##smoketex="images/particles/smoke1-1.png",
        #debristex=[
            #"images/particles/airplanedebris_1.png",
            #"images/particles/airplanedebris_2.png",
            #"images/particles/airplanedebris_3-1.png",
            #"images/particles/airplanedebris_3-2.png",
            #"images/particles/airplanedebris_3-3.png"],
        #keepready=5.0)
    hitflash = AutoProps()
    modelpath = None
    modelscale = 1.0
    modeloffset = Point3()
    modelrot = Vec3()
    fmodelpath = None
    sdmodelpath = None
    shdmodelpath = None
    vortexdata = []
    normalmap = "images/_normalmap_none.png"
    glowmap = rgba(0, 0, 0, 0.1)
    glossmap = None
    pilottexture = "models/aircraft/pilots/pilot_tex.png"
    pilotglossmap = "models/aircraft/pilots/pilot_gls.png"
    engsoundname = None
    cpengsoundname = None
    engminvol = 0.0
    engmaxvol = 0.4
    engminvolab = 0.6 #!!!
    engmaxvolab = 0.8 #!!!
    proprpm = 0.0
    proprtclkw = True
    flybysoundname = None
    ejectdata = None
    breakupdata = []
    varsweeprange = None
    varsweeppivot = None
    varsweepspeed = None
    varsweephitbox = None
    varsweepmodelmin = False

    dyn = None

    @classmethod
    def derive_dynamics (cls, rep=False, envtab=True):

        dyn = cls.__dict__.get("dyn") # avoid fetching from base class
        if dyn is not None:
            return dyn

        if len(cls.groundcontact) != 3:
            raise StandardError("Expected exactly 3 ground contact points.")
        plgn, plgmr, plgml = cls.groundcontact
        if not (plgn[0] == 0.0):
            raise StandardError(
                "First ground contact point (nose LG) must have "
                "zero x-coordinate.")
        if not (plgmr[0] > 0.0):
            raise StandardError(
                "Second ground contact point (right main LG) must have "
                "positive x-coordinate.")
        if not (plgmr[0] == -plgml[0] and plgmr[1] == plgml[1] and plgmr[2] == plgml[2]):
            raise StandardError(
                "Second and third ground contact points (main LG) must be "
                "symmetric over the yz-plane.")
        if not (plgn[1] > plgmr[1]):
            raise StandardError(
                "First ground contact point (nose LG) must have "
                "larger y-coordinate than the second (main LG).")

        cls.dyn = PlaneDynamics(
            name=cls.species,

            g0=9.81,
            htrop=11000.0,
            hstrat=20000.0,
            gam=1.4,
            rhoz=1.225,
            rhoefac=-1.10e-4,
            prz=1.013e5,
            prefac=-1.35e-4,
            vsndz=340.0,
            vsndfacht=0.868,

            mmin=cls.minmass,
            mmax=cls.maxmass,
            mref=cls.refmass,
            nmaxref=cls.maxload,

            s=cls.wingarea,
            ar=cls.wingaspect,
            e=cls.wingspeff,
            a0z=cls.zlaoa,
            amaxz=cls.maxaoa,

            tmaxz=cls.maxthrust,
            tmaxabz=cls.maxthrustab,
            tincab=cls.thrustincab,

            vmaxz=cls.maxspeedz,
            vmaxabz=cls.maxspeedabz,
            crmaxz=cls.maxclimbratez,
            voptcz=cls.cloptspeedz,

            vmaxh=cls.maxspeedh,
            vmaxabh=cls.maxspeedabh,

            pomaxz=cls.maxpitchratez,
            romaxz=cls.maxrollratez,

            mfmax=cls.maxfuel,
            sfcz=cls.refsfcz,
            sfcabz=cls.refsfcabz,
            cincab=cls.sfcincab,

            rsd0br=cls.reldragbrake,

            da0fl1=cls.maxflapdeltzlaoa,
            damaxfl1=cls.maxflapdeltmaxaoa,
            rsd0fl1=cls.maxflapdeltreldrag,
            da0fl2=cls.midflapdeltzlaoa,
            damaxfl2=cls.midflapdeltmaxaoa,
            rsd0fl2=cls.midflapdeltreldrag,

            lgny=plgn[1],
            lgnz=plgn[2],
            lgmx=plgmr[0],
            lgmy=plgmr[1],
            lgmz=plgmr[2],

            rmugbr=cls.reldragwheelbrake,
            rsd0lg=cls.reldragwheel,

            rep=rep,
            envtab=envtab,
        )

        return cls.dyn


    def __init__ (self, world, name, side, skill=None, texture=None,
                  fuelfill=None, pos=None, hpr=None, speed=None,
                  onground=False,
                  damage=None, faillvl=None):

        self.__class__.derive_dynamics(rep=False)

        if pos is None:
            pos = Point3()
        if hpr is None:
            hpr = Vec3()
        if fuelfill is None:
            fuelfill = 0.5
        fuelfill = min(max(fuelfill, 0.0), 1.0)
        if speed is None or speed <= 0.0:
            if onground:
                speed = PlaneDynamics.MINSPEED * 1.05
            else:
                mass = self.minmass + self.maxfuel * fuelfill
                speed = self.dyn.tab_voptrf[0](mass, pos[2])

        if skill is None:
            self.skill = PlaneSkill()
        elif isinstance(skill, basestring):
            self.skill = PlaneSkill.preset(skill)
        else:
            self.skill = skill
        #self.skill = None

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
                texture=self.texture, normalmap=self.normalmap,
                glowmap=self.glowmap, glossmap=self.glossmap,
                scale=self.modelscale,
                offset=self.modeloffset, rot=self.modelrot),
            hitboxdata=self.hitboxdata, hitboxcritdata=self.hitboxcritdata,
            sensordata=AutoProps(
                scanperiod=2.0,
                relspfluct=0.1,
                maxtracked=1),
            hitlight=AutoProps(),
            hitdebris=self.hitdebris, hitflash=self.hitflash,
            amblit=True, dirlit=True, pntlit=4, fogblend=True,
            obright=True, ltrefl=True,
            shdshow=True, shdmodind=shdmodind,
            pos=pos, hpr=hpr, vel=speed)

        self.fuelfill = fuelfill
        self.fuel = self.maxfuel * self.fuelfill
        self.mass = self.minmass + self.fuel
        self.fuelcons = 0.0
        self.fuelfillcons = 0.0
        self.onground = onground
        self.dynstate = None
        self.helix_dummy = None # (debugging)

        span, length = self.bbox.getXy()
        self.size = (span + length) / 2
        self._size_xy = min(span, length)

        for mlevel, model in enumerate(self.models):
            remove_subnodes(model, (
                "FWDstrut", "nose_strut",
                "Lstrut", "main_left_strut", "main_left_strut_1", "main_left_strut_2",
                "Rstrut", "main_right_strut", "main_right_strut_1", "main_right_strut_2",
                "FWDgear", "nose_wheel",
                "Lgear", "main_left_wheel", "main_left_wheel_1", "main_left_wheel_2",
                "Rgear", "main_right_wheel", "main_right_wheel_1", "main_right_wheel_2",
                "hose_left", "hose_middle", "hose_right")) # !!! Temporary
            self._init_model(model, mlevel)

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
                self._init_model(model, mlevel)
                model.setTwoSided(True)

        # Detect turning props.
        self._props = {}
        propacctime = 6.0
        proprpmacc = self.proprpm / propacctime
        propdacctime = 12.0
        proprpmdacc = self.proprpm / propdacctime
        turndirr = self.proprtclkw and -1 or 1
        max_mlevel_prop = 0
        prop_models = list(self.models)
        if base.with_world_shadows and self.shadow_node is not None:
            prop_models += [self.shadow_node]
        if self.sdmodelpath:
            prop_models += self._shotdown_models
        for sd, turndir in ("left", -turndirr), ("right", turndirr):
            ip = 1
            while True:
                propnds = []
                for mlevel, model in enumerate(prop_models):
                    propname = "propeller_%s_%d" % (sd, ip)
                    propnd = model.find("**/%s" % propname)
                    if not propnd.isEmpty():
                        propnds.append(propnd)
                        if mlevel < len(self.models): # due to shadow model
                            max_mlevel_prop = max(max_mlevel_prop, mlevel)
                if not propnds:
                    break
                ps = AutoProps()
                ps.nodes = propnds
                ps.rpm = self.proprpm
                ps.targrpm = self.proprpm
                ps.turndir = turndir
                ps.rpmacc = proprpmacc
                ps.rpmdacc = proprpmdacc
                self._props["%s-%d" % (sd, ip)] = ps
                ip += 1
        if self._props:
            self._fardist_props = self.fardists[max_mlevel_prop]

        # Detect engine flame walls.
        self._engine_flame_walls = []
        for model in self.models:
            flwnd = model.find("**/%s" % "flame")
            if not flwnd.isEmpty():
                shader = make_shader(ambln=self.world.shdinp.ambln,
                                     glow=rgba(255, 255, 255, 1.0),
                                     glowfacn=self.world.shdinp.glowfacn)
                flwnd.setShader(shader)
                flwnd.setTransparency(TransparencyAttrib.MAlpha)
                texture = None
                if base.with_bloom:
                    texture = "models/aircraft/_engineflame.png"
                set_texture(flwnd, texture=texture, normalmap=-1,
                            glowmap=-1, glossmap=-1, shadowmap=-1)
                self._engine_flame_walls.append(flwnd)
        self._engine_hot_walls = []
        for model in self.models:
            ehwnd = model.find("**/%s" % "hotwall")
            if not ehwnd.isEmpty():
                shader = make_shader(ambln=self.world.shdinp.ambln,
                                     glow=rgba(255, 255, 255, 1.0),
                                     glowfacn=self.world.shdinp.glowfacn)
                ehwnd.setShader(shader)
                set_texture(ehwnd, normalmap=-1, glowmap=-1, glossmap=-1,
                            shadowmap=-1)
                self._engine_hot_walls.append(ehwnd)
        if self._engine_hot_walls:
            for flwnd in self._engine_flame_walls:
                flwnd.hide()
            self._engine_flame_walls = []

        if self.engsoundname:
            self.engine_sound = Sound3D(
                path=("audio/sounds/%s.ogg" % self.engsoundname),
                parent=self, maxdist=3000, limnum="hum",
                volume=0.0, loop=True, fadetime=2.5)
            self.engine_sound.play()
        else:
            self.engine_sound = None

        # Set up variable sweep visuals.
        if self.varsweepmach:
            # Shuffle model nodes to pivoting arms.
            self._varsweep_arm_lefts = []
            self._varsweep_arm_rights = []
            if base.with_world_shadows and self.shadow_node is not None:
                ref_models = self.models + [self.shadow_node]
            else:
                ref_models = self.models
            piv_pos_left, piv_pos_right = self.varsweeppivot
            if self.varsweephitbox:
                hbx_name_left, hbx_name_right = self.varsweephitbox
                hbx_left = self.hitboxmap[hbx_name_left]
                hbx_right = self.hitboxmap[hbx_name_right]
            for mlevel, model in enumerate(ref_models):
                # - left
                plnd = model.attachNewNode("pivot-wing-left")
                plnd.setPos(piv_pos_left[0], piv_pos_left[1], 0.0)
                plnd.setHpr(0, 0, 180)
                wing_arm_left = plnd.attachNewNode("pivot-arm")
                wlnd = model.find("**/wing_left")
                wlnd.wrtReparentTo(wing_arm_left)
                if self.varsweephitbox and mlevel == 0:
                    hbx_left.cnode.wrtReparentTo(wing_arm_left)
                self._varsweep_arm_lefts.append(wing_arm_left)
                # - right
                prnd = model.attachNewNode("pivot-wing-right")
                prnd.setPos(piv_pos_right[0], piv_pos_right[1], 0.0)
                prnd.setHpr(0, 0, 0)
                wing_arm_right = prnd.attachNewNode("pivot-arm")
                wrnd = model.find("**/wing_right")
                wrnd.wrtReparentTo(wing_arm_right)
                if self.varsweephitbox and mlevel == 0:
                    hbx_right.cnode.wrtReparentTo(wing_arm_right)
                self._varsweep_arm_rights.append(wing_arm_right)
            # Set initial sweep.
            self._varsweep_force_relang = None
            self._varsweep_force_jump = False
            self._varsweep_ang = self._get_sweep_angle(speed, pos[2])
            self._set_sweep_pivot(self._varsweep_ang)

        self.cockpit_engine_sound = None
        # ...must be started when the player is attached.

        if not base.with_sound_doppler:
            self._in_flyby = False

        self._state_info_text = None
        self._wait_time_state_info = 0.0

        self._prev_path = None
        self._path_pos = 0.0

        self.cannons = []
        self.turrets = []
        self.launchers = []
        self.podlaunchers = []
        self.droppers = []
        self.jammers = []
        self.tankers = []
        self.exhaust_trails = []
        self.damage_trails = []
        self.decoys = []

        self.damage = damage or 0.0
        self._damage_critical = 0.0
        self.failure_level = faillvl or 0
        self.max_failure_level = 3
        self.must_not_explode = False
        self.stalled = False
        for i in range(1, self.failure_level + 1):
            self._add_damage_trails(level=i)

        self.target = None # read-only! Use set_act().

        # Trail (debugging).
        self._trace = None
        if world.show_traces:
            if side in ("bstar", "vvs", "vcaf"):
                trcol = rgba(255, 0, 0, 1)
            elif side in ("nato", "usaf", "usn", "usmc"):
                trcol = rgba(0, 0, 255, 1)
            else:
                trcol = rgba(0, 255, 0, 1)
            self._trace = LineNodePath(parent=world.node, thickness=1.0,
                                       colorVec=trcol)
            self._trace_segs = []
            self._trace_lens = []
            self._trace_len = 0.0
            self._trace_maxlen = 2000.0

        self._first_loop = True

        self._prev_pos = None
        self._prev_vel = None
        self._prev_gsp = None
        self._prev_gsr = None
        self._prev_fire_cannon_spec = None

        self._wait_damage_recovery = 0.0
        self._wait_cannon_burst = 0.0
        self._cannon_burst_period = 2.0

        self._dummy_cannon = None

        # Auto attack constants and state.
        self._aatk_period = 3.0
        self._aatk_period_float = 1.0
        self._aatk_wait = uniform(0.0, self._aatk_period)
        self._aatk_paused = False
        self._aatk_families = []
        self._aatk_maxvisdist = 3000.0
        self._aatk_targprio = 0
        self._aatk_prev_leader = None
        self._aatk_prev_formpos = None

        # Autopilot constants and state.
        self._act_shootdist = 700.0
        self._act_input_controlout = None
        # FIXME: Dirty way of firing missiles.
        # Remove when proper missile modes become available.
        self._fudge_missile_attack = True
        if self._fudge_missile_attack:
            self._act_matk_enroute = {}
            self._act_matk_prev_launcher = None
        self.set_act()

        # Controls state.
        self.set_cntl()

        # Route settings.
        self._route_current_point = None
        self._route_points = []
        self._route_point_inc = 1
        self._route_patrol = False
        self._route_circle = False

        # Jamming constants and state.
        self._jm_period = 2.0
        self._jm_period_float = 0.5
        self._jm_carrier_families = ["plane"]
        self._jm_wait = 0.0
        self.jammed = False

        # Buffet.
        self._wait_buffet = 0.0
        self._buffet_period = 0.05
        self.buffet_daoa = 0.0
        self.buffet_dbnk = 0.0
        self._buffet_in_progress = False

        # Recoil.
        self._wait_recoil = 0.0
        self._recoil_period = None
        self._recoil_strength = None
        self._recoil_prev_ammo = None
        self.recoil_dz = 0.0
        self.recoil_dx = 0.0
        self.recoil_daoa = 0.0
        self.recoil_dbnk = 0.0
        self._recoil_in_progress = False

        # Shake.
        self._shake_last_hitforce = 0.0
        self._shake_strength = 0.0
        self.shake_dz = 0.0
        self.shake_dx = 0.0
        self.shake_daoa = 0.0
        self.shake_dbnk = 0.0
        self._shake_in_progress = False

        # Rolling.
        self._rolling_in_progress = False
        self._rolling_period = 0.0
        self._rolling_time = 0.0
        self._rolling_targ_du = 0.0
        self._rolling_speed_du = 0.0
        self.rolling_du = 0.0

        # Sensor signature.
        self.ireqpower = 0.0
        self._ireqpwrfac = self.irmuffle

        # Sensors.
        if self.visualtype == VISTYPE.FIGHTER:
            fa, ra, sa = self.visualangle
            airvis = FighterVisual(parent=self,
                                   dfamilies=["plane", "heli",
                                              "rocket-v", "shell-v"],
                                   frontangle=fa, rearangle=ra, sideangle=sa,
                                   refsizetype=SIZEREF.PROJAREA,
                                   relsight=1.0, considersun=True)
            self.sensorpack.add(airvis, "visual-air")
            gndvis = FighterVisual(parent=self,
                                   dfamilies=["vehicle", "ship", "building"],
                                   frontangle=fa, rearangle=ra, sideangle=sa,
                                   refsizetype=SIZEREF.DIAG,
                                   relsight=0.5, considersun=False)
            self.sensorpack.add(gndvis, "visual-ground")
        elif self.visualtype == VISTYPE.TRANSPORT:
            da, ua, ta = self.visualangle
            airvis = TransportVisual(parent=self,
                                     dfamilies=["plane", "heli",
                                                "rocket-v", "shell-v"],
                                     downangle=da, upangle=ua, topangle=ta,
                                     refsizetype=SIZEREF.PROJAREA,
                                     relsight=1.0, considersun=True)
            self.sensorpack.add(airvis, "visual-air")
            gndvis = TransportVisual(parent=self,
                                     dfamilies=["vehicle", "ship", "building"],
                                     downangle=da, upangle=ua, topangle=ta,
                                     refsizetype=SIZEREF.DIAG,
                                     relsight=0.5, considersun=False)
            self.sensorpack.add(gndvis, "visual-ground")
        if self.radarrange:
            da, ua, ta = self.radarangle
            radar = Radar(parent=self,
                          dfamilies=["plane", "heli", "ship"],
                          refrange=self.radarrange,
                          downangle=da, upangle=ua, topangle=ta)
            self.sensorpack.add(radar, "radar")
        if self.irstrange:
            da, ua, ta = self.irstangle
            irst = Irst(parent=self,
                        dfamilies=["plane", "heli"],
                        refrange=self.irstrange,
                        downangle=da, upangle=ua, topangle=ta)
            self.sensorpack.add(irst, "irst")
        if self.tvrange:
            minua, maxua, ta = self.tvangle
            tv = Tv(parent=self,
                    dfamilies=["vehicle", "ship", "building"],
                    refrange=self.tvrange,
                    minupangle=minua, maxupangle=maxua, topangle=ta,
                    refsizetype=SIZEREF.DIAG)
            self.sensorpack.add(tv, "tv")
        if self.rwrwash:
            rwr = Rwr(parent=self,
                      dfamilies=["plane", "vehicle", "ship"],
                      minwash=self.rwrwash)
            self.sensorpack.add(rwr, "rwr")
        if self.datalinkrecv or self.datalinksend:
            datalink = DataLink(parent=self,
                                dfamilies=["plane", "heli", "vehicle", "ship", "building"],
                                sfamilies=["plane", "heli", "vehicle", "ship"],
                                canrecv=self.datalinkrecv,
                                cansend=self.datalinksend)
            self.sensorpack.add(datalink, "datalink")
        if True:
            comm = Comm(parent=self,
                        dfamilies=["plane", "heli", "vehicle", "ship"])
            self.sensorpack.add(comm, "comm")
        if True:
            magtargd = MagicTargeted(parent=self,
                                     dfamilies=["plane"])
            self.sensorpack.add(magtargd, "magic-targd")
        self.sensorpack.start_scanning()

        # Collision warning.
        insidetime = 2.0
        insidedist = self.bboxdiag * 2.0
        self._cw_sensorpack = SensorPack(parent=self,
                                         scanperiod=(insidetime * 0.5),
                                         relspfluct=(insidetime * 0.1),
                                         maxtracked=0)
        if self.visualtype == VISTYPE.FIGHTER:
            fa, ra, sa = self.visualangle
            cwv = FighterVisualCollisionWarning(
                parent=self, dfamilies=["plane", "heli"],
                insidedist=insidedist, insidetime=insidetime,
                frontangle=fa, rearangle=ra, sideangle=sa,
                refsizetype=SIZEREF.DIAG,
                relsight=1.0, considersun=True)
            self._cw_sensorpack.add(cwv, "collwarn-visual")
        elif self.visualtype == VISTYPE.TRANSPORT:
            da, ua, ta = self.visualangle
            cwv = TransportVisualCollisionWarning(
                parent=self, dfamilies=["plane", "heli"],
                insidedist=insidedist, insidetime=insidetime,
                downangle=da, upangle=ua, topangle=ta,
                refsizetype=SIZEREF.DIAG,
                relsight=1.0, considersun=True)
            self._cw_sensorpack.add(cwv, "collwarn-visual")
        self._cw_sensorpack.start_scanning()

        # Attack warning.
        self._aw_sensorpack = SensorPack(parent=self,
                                         scanperiod=1.0,
                                         relspfluct=0.2,
                                         maxtracked=0)
        if self.visualtype == VISTYPE.FIGHTER:
            fa, ra, sa = self.visualangle
            atkvis = FighterVisual(parent=self,
                                   dfamilies=["rocket-v", "shell-v"],
                                   frontangle=fa, rearangle=ra, sideangle=sa,
                                   refsizetype=SIZEREF.DIAG,
                                   relsight=1.0, considersun=True)
            self._aw_sensorpack.add(airvis, "atkwarn-visual")
        elif self.visualtype == VISTYPE.TRANSPORT:
            da, ua, ta = self.visualangle
            atkvis = TransportVisual(parent=self,
                                     dfamilies=["rocket-v", "shell-v"],
                                     downangle=da, upangle=ua, topangle=ta,
                                     refsizetype=SIZEREF.DIAG,
                                     relsight=1.0, considersun=True)
            self._aw_sensorpack.add(atkvis, "atkwarn-visual")
            atkmtd = MagicTargeted(parent=self,
                                   dfamilies=["rocket"])
            self._aw_sensorpack.add(atkmtd, "atkwarn-magic-targd")
        self._aw_sensorpack.start_scanning()

        # Visible vortices.
        self._vortices_max_alt = 5000.0
        self._vortices_min_lfac = 5.0
        self._vortices_max_lfac = 8.0
        self._vortices_active = False
        self._vortices = []
        for vd in self.vortexdata:
            vpos = vd
            radius0 = 0.40
            vpos_mod = Point3(vpos[0] - radius0 * 0.5 * sign(vpos[0]),
                              vpos[1], vpos[2])
            vortex = PolyTrail(parent=self, pos=vpos_mod,
                               radius0=radius0, radius1=1.60, lifespan=1.5,
                               color=rgba(250, 250, 250, 0.6),
                               texture="images/particles/exhaust06.png",
                               glowmap=rgba(0, 0, 0, 0.1),
                               dirlit=True,
                               loddistout=3000.0, loddistalpha=1000.0,
                               segperiod=0.010, farsegperiod=pycv(py=0.050, c=None))
            vortex.set_active(False)
            self._vortices.append(vortex)

        # Missile evasion.
        self._attacking_missile = None
        if self.flarechaff:
            self._decoy_next_launch_index = 0
            self._wait_decoy = 0.0
            if self.flchlaunchtype == 0:
                self._decoy_missile_dist_time = 2.0
                self._decoy_launch_freq = [0.20]
                self._decoy_launch_pos = [
                    [Point3(-0.5, -4.0, 0.0)],
                    [Point3(+0.5, -4.0, 0.0)],
                ]
                self._decoy_launch_vel = [
                    [hprtovec(Vec3(+15, -30, 0)) * 30.0],
                    [hprtovec(Vec3(-15, -30, 0)) * 30.0],
                ]
            elif self.flchlaunchtype == 1:
                self._decoy_missile_dist_time = 1.0
                self._decoy_launch_freq = [0.20, 1.1]
                lngrp = len(self._decoy_launch_freq)
                lnpgh = 6
                ldx = 1.0; ldy = -10.0
                lh0 = 15.0; lh1 = 90.0
                lp0 = -50.0; lp1 = -10.0; lpe = 0.5
                lspd0 = 30.0; lspd1 = 20.0
                lnh = lngrp * lnpgh
                self._decoy_launch_pos = []
                self._decoy_launch_vel = []
                for j in range(lngrp):
                    pos = []
                    self._decoy_launch_pos.append(pos)
                    vel = []
                    self._decoy_launch_vel.append(vel)
                    for i in range(j, lnh, lngrp):
                        ifac = float(i) / (lnh - 1)
                        pos.append(Point3(-ldx, ldy, 0.0))
                        pos.append(Point3(+ldx, ldy, 0.0))
                        lspd = lspd0 + (lspd1 - lspd0) * ifac
                        lp = lp0 + (lp1 - lp0) * ifac**lpe
                        vhpr_1 = Vec3(+lh0 + (lh1 - lh0) * ifac, lp, 0)
                        vhpr_2 = Vec3(-lh0 - (lh1 - lh0) * ifac, lp, 0)
                        vel.append(hprtovec(vhpr_1) * lspd)
                        vel.append(hprtovec(vhpr_2) * lspd)
            else:
                raise StandardError(
                    "Unknown flare-chaff deployment method %d." %
                    self.flchlaunchtype)

        self._evade_missile_aatk_paused = False
        self.evade_missile_manouver = self.flchmanouver
        self.evade_missile_decoy = True

        # Ejection.
        self.ejection_triggered = False
        self._wait_eject = 0.5
        self.ejection = None
        self.must_eject_time = 0.0

        # Breakup.
        self._breakup_track_hits_gun_fixed = 0.0
        self._breakup_track_hits_gun_level = 0.0
        self._breakup_track_hits_vol = []
        self._breakup_hit_time_range = 0.2
        self._breakup_gun_damage_factor = 2.0

        #base.taskMgr.add(self._loop, "plane-loop-%s" % self.name)
        base.taskMgr.add(self._loop, "plane-loop")


    def _init_dynamics (self):

        # Must not be done in the constructor,
        # because mass may be changed by filling equipment lists.

        pos = self.pos()
        vel = self.vel()

        if self.helix_dummy is not None:
            self.dynstate = AutoProps(
                g=self.helix_dummy.g,
                p=self.helix_dummy.p,
                v=self.helix_dummy.v,
                hdg=self.helix_dummy.hdg,
                cr=self.helix_dummy.cr,
                tr=self.helix_dummy.tr,
                refsz=self.helix_dummy.refsz,
                gc=False,
            )
            dq = self.dynstate
            self._move_by_helix(dq, 0.0)
        else:
            self.dynstate = AutoProps()
            dq = self.dynstate
            if self.onground:
                hg, ng, tg = self._ground_data()
                self._landgear = True
            else:
                hg, ng, tg = None, None, None
            self.dyn.resolve_stat(dq, self.mass, ptod(pos), vtod(vel),
                                  hg, ng, tg)
            self.dyn.update_fstep(dq, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  hg, ng, tg,
                                  extraq=True) # to derive quantities
            mon = False
            #mon = (self.name == "red")
            if mon:
                dbgval(1, "init",
                       (dq.m, "%.0f", "m", "kg"),
                       (dq.h, "%.0f", "h", "m"),
                       (dq.v, "%.1f", "v", "m/s"),
                       (dq.cr, "%.1f", "cr", "m/s"),
                       (degrees(dq.a), "%.2f", "a", "deg"),
                       (dq.tl, "%.3f", "tl"),
                       (dq.ct, "%.2f", "ct", "m/s^2"),
                       (degrees(dq.phi), "%.2f", "phi", "deg"))


    def _init_pylon_handlers (self, pload, fuelfill=None):
        # NOTE: self.pylons must be set before call.

        for launcher in self.launchers:
            launcher.destroy()
        for podlauncher in self.podlaunchers:
            podlauncher.destroy()
        for dropper in self.droppers:
            dropper.destroy()
        for jammer in self.jammers:
            jammer.destroy()
        for tanker in self.tankers:
            tanker.destroy()

        self.launchers = []
        self.podlaunchers = []
        self.droppers = []
        self.jammers = []
        self.tankers = []

        if not pload:
            return

        if fuelfill is not None:
            tankfill = max(fuelfill - 1.0, 0.0)
            tankfuel = self.maxfuel * tankfill

        if pload[0] == 1:
            # Direct placement, input is [(loadtype, (pylonindex, ...), s), ...].
            pload = pload[1:] # remove placement type indicator
            for ptype, points, rounds in pload:
                if ptype is not None and points:
                    if issubclass(ptype, Rocket):
                        launcher = Launcher(
                            ptype, points=points,
                            rate=2.0, # !!!
                            parent=self)
                        self.launchers.append(launcher)
                    if issubclass(ptype, RocketPod):
                        podlauncher = PodLauncher(
                            ptype, points=points, rounds=rounds,
                            parent=self)
                        self.podlaunchers.append(podlauncher)
                    elif issubclass(ptype, Bomb):
                        dropper = Dropper(
                            ptype, points=points,
                            rate=1.0, # !!!
                            parent=self)
                        self.droppers.append(dropper)
                    elif issubclass(ptype, JammingPod):
                        jammer = Jammer(ptype, points=points, parent=self)
                        self.jammers.append(jammer)
                    elif issubclass(ptype, DropTank):
                        if fuelfill is not None:
                            tankfuel1 = min(tankfuel, ptype.maxfuel)
                            tankfuel -= tankfuel1
                            tankfill1 = tankfuel1 / ptype.maxfuel
                        else:
                            tankfill1 = 1.0
                        tanker = Tanker(
                            ptype, points=points,
                            fuelfill=tankfill1, parent=self)
                        self.tankers.append(tanker)
        else:
            # Automatic placement, input is [(loadtype, numrounds), ...].
            # May contain a placement type indicator, remove it.
            if isinstance(pload[0], int):
                pload = pload[1:]
            pqueue = list(enumerate(self.pylons))
            for ptype, pnum in pload:
                points = []
                i = 0
                while pnum > len(points) and i < len(pqueue):
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
                    if issubclass(ptype, RocketPod):
                        podlauncher = PodLauncher(
                            ptype, points=points,
                            parent=self)
                        self.podlaunchers.append(podlauncher)
                    elif issubclass(ptype, Bomb):
                        dropper = Dropper(
                            ptype, points=points,
                            rate=1.0, #!!!
                            parent=self)
                        self.droppers.append(dropper)
                    elif issubclass(ptype, JammingPod):
                        jammer = Jammer(ptype, points=points, parent=self)
                        self.jammers.append(jammer)
                    elif issubclass(ptype, DropTank):
                        if fuelfill is not None:
                            tankfuel1 = min(tankfuel, ptype.maxfuel)
                            tankfuel -= tankfuel1
                            tankfill1 = tankfuel1 / ptype.maxfuel
                        else:
                            tankfill1 = 1.0
                        tanker = Tanker(
                            ptype, points=points,
                            fuelfill=tankfill1, parent=self)
                        self.tankers.append(tanker)
                if not pqueue:
                    break


    def _init_model (self, model, mlevel):

        if mlevel == 0:
            for handle in ("Pilot", "pilot", "co_pilot"):
                geom = model.find("**/%s" % handle)
                if not geom.isEmpty():
                    set_texture(geom,
                        texture=self.pilottexture,
                        normalmap=-1, glowmap=None,
                        glossmap=self.pilotglossmap,
                        shadowmap=self.world.shadow_texture)

            for handle in (
                "canopy_glass", "canopy_glass_1", "canopy_glass_2",
                "canopy_windscreen", "canopy_back_glass"):
                geom = model.find("**/%s" % handle)
                if not geom.isEmpty():
                    geom.setTransparency(TransparencyAttrib.MAlpha)
        else:
            remove_subnodes(model, ("Pilot", "pilot"))


    def set_cntl (self, daoa=None, droll=None, dthrottle=None,
                  dairbrake=None, flaps=FLAPS.RETRACTED,
                  landgear=False, dsteer=None, wheelbrake=False):

        self._daoa = daoa or 0.0
        self._droll = droll or 0.0
        self._dthrottle = dthrottle or 0.0
        self._dairbrake = dairbrake or 0.0
        self._flaps = flaps
        self._landgear = landgear if not self.onground else True
        self._dsteer = dsteer or 0.0
        self._wheelbrake = wheelbrake


    def _set_cntl_with_spdacc (self, da, dr, dtl, dbrd, fld, dtmu):

        dq = self.dynstate
        cq = self._act_state

        pomax, romax, tlvmax = dq.pomax, dq.romax, dq.tlvmax
        psmax, rsmax, tlcmax = dq.psmax, dq.rsmax, dq.tlcmax
        brdvmax = dq.brdvmax

        if not cq.inited:
            cq.ao, cq.ro, cq.tlv = dq.ao, dq.ro, dq.tlv
            cq.inited = True
        cao, cro, ctlv = cq.ao, cq.ro, cq.tlv
        tcao, tcro, tctlv = 0.0, 0.0, 0.0

        def getca ():
            return cq.dtmca, cq.dac, cq.ao
        def setca (dtmca, dac, ao):
            cq.dtmca, cq.dac, cq.ao = dtmca, dac, ao
        def getcr ():
            return cq.dtmcr, cq.drc, cq.ro
        def setcr (dtmcr, drc, ro):
            cq.dtmcr, cq.drc, cq.ro = dtmcr, drc, ro
        def getctl ():
            return cq.dtmctl, cq.dtlc, cq.tlv
        def setctl (dtmctl, dtlc, tlv):
            cq.dtmctl, cq.dtlc, cq.tlv = dtmctl, dtlc, tlv
        def getcbrd ():
            return cq.dtmcbrd, cq.dbrdc
        def setcbrd (dtmcbrd, dbrdc):
            cq.dtmcbrd, cq.dbrdc = dtmcbrd, dbrdc

        dtmeps = self.world.dt * 1e-2

        ret = self.dyn.input_program_settm(da, cao, tcao, pomax, psmax, dtmu,
                                           getca, setca)
        inpfa = ret[0]
        if inpfa is None:
            ret = self.dyn.input_program_mintm(da, cao, tcao, pomax, psmax,
                                               getca, setca, dtmeps)
            inpfa = ret[0]

        ret = self.dyn.input_program_settm(dr, cro, tcro, romax, rsmax, dtmu,
                                           getcr, setcr)
        inpfr = ret[0]
        if inpfr is None:
            ret = self.dyn.input_program_mintm(dr, cro, tcro, romax, rsmax,
                                               getcr, setcr, dtmeps)
            inpfr = ret[0]

        ret = self.dyn.input_program_settm(dtl, ctlv, tctlv, tlvmax, tlcmax, dtmu,
                                           getctl, setctl)
        inpftl = ret[0]
        if inpftl is None:
            ret = self.dyn.input_program_mintm(dtl, ctlv, tctlv, tlvmax, tlcmax,
                                               getctl, setctl, dtmeps)
            inpftl = ret[0]

        ret = self.dyn.input_program_constv(dbrd, brdvmax,
                                            getcbrd, setcbrd)
        inpfbrd = ret[0]

        self.set_cntl(inpfa, inpfr, inpftl, inpfbrd, fld)


    def _loop (self, task):

        if not self.alive:
            return task.done

        dq = self.dynstate
        if dq is None:
            self._init_dynamics()
            dq = self.dynstate

        dt = self.world.dt

        pos = self.pos()
        vel = self.vel()

        if dq.gc != self.onground:
            self.onground = dq.gc
            if self.onground:
                snd = Sound3D(path="audio/sounds/flight-touchdowncenter.ogg",
                              parent=self, volume=1.0, fadetime=0.1)
                snd.play()

        if self._first_loop:
            self._first_loop = False
            self._prev_vel = vel
            self._prev_gsp = dq.gsp
            self._prev_gsr = dq.gsr

        if not self.onground:
            crash = self.world.below_surface(pos)
            if crash:
                gpos = self.world.intersect_surface(pos - vel * dt, pos)
        else:
            # In case of touchdown, values from air just before.
            pvel = self._prev_vel
            pgsp = self._prev_gsp
            pgsr = self._prev_gsr
            crash = (
                pvel.length() > self.maxlandspeed or
                pvel[2] < -self.maxlandsinkrate or
                not self.minlandrotangle + dq.ag < pgsp < self.maxlandrotangle or
                abs(pgsr) > self.maxlandrollangle or
                dq.tg not in self.groundcanland)
            if crash:
                gpos = pos
            #dbgval(1, "pln-land-check", crash, pvel.length(), pvel[2], degrees(pgsp), degrees(pgsr))
        if crash:
            dbgval(1, "plane-crash",
                   (self.world.time, "%.2f", "time", "s"),
                   ("%s(%s)" % (self.name, self.species), "%s", "this"))
            self.explode(pos=gpos, offset=Vec3(0.0, 0.0, 5.0), ground=True)

        cdist = self.node.getDistance(self.world.camera)

        # Kill trails if no fuel left.
        if self.fuel == 0.0 and self.exhaust_trails:
            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []
            self.engminvol = 0.0

        # Set size of exhaust trails.
        lrsize0 = 0.2
        alpha0 = 0.1
        thr, maxthr, maxthrab = dq.t, dq.tmax, dq.tmaxab
        if thr <= maxthr:
            lrsize = lrsize0
        else:
            lrifac = (thr - maxthr) / (maxthrab - maxthr)
            lrsize = lrsize0 + (1.0 - lrsize0) * lrifac
        ltcscale = lrsize**0.5
        drsize = 0.8 + (1.0 - 0.8) * lrsize
        for trail in self.exhaust_trails:
            trail.length = trail.init_length * lrsize
            trail.radius0 = trail.init_radius0 * drsize
            trail.radius1 = trail.init_radius1 * drsize
            alifac = (lrsize - lrsize0) / (1.0 - lrsize0)
            alpha = alpha0 + (trail.init_color[3] - alpha0) * alifac
            trail.color[3] = alpha
            trail.light_cscale = ltcscale

        # Set engine flame walls.
        flwspd = 1 / 4.0
        for flwnd in self._engine_flame_walls:
            throttle = dq.tl
            alpha = flwnd.getSa()
            if throttle > 0.0 and alpha < 1.0:
                alpha = clamp(alpha + flwspd * dt, 0.0, 1.0)
                flwnd.setSa(alpha)
            elif throttle <= 0.0 and alpha > 0.0:
                alpha = clamp(alpha - flwspd * dt, 0.0, 1.0)
                flwnd.setSa(alpha)
            glowfac = clamp(throttle * 1.3, 0.0, 1.0)
            flwnd.setShaderInput(self.world.shdinp.glowfacn, glowfac)
        for ehwnd in self._engine_hot_walls:
            throttle = dq.tl
            glowfac = clamp(throttle * 1.3, 0.0, 1.0)
            ehwnd.setShaderInput(self.world.shdinp.glowfacn, glowfac)

        # Set sensor signatures.
        pwr = dq.t * dq.v
        self.ireqpower = pwr * self._ireqpwrfac

        # Make and remove cockpit engine sound as needed.
        if self.cpengsoundname:
            if (not self.cockpit_engine_sound and
                self.world.player and self.world.player.alive and
                self.world.player.ac is self):
                self.cockpit_engine_sound = Sound2D(
                    path=("audio/sounds/%s.ogg" % self.cpengsoundname),
                    loop=True, world=self.world,
                    pnode=self.world.player.cockpit.node,
                    volume=0.0, fadetime=2.5)
                self._prev_cockpit_active = None
            if self.cockpit_engine_sound and not self.world.player.alive:
                self.cockpit_engine_sound.stop()
                self.cockpit_engine_sound = None
                self.engine_sound.play()

        # Set engine sound volume based on throttle.
        if self.engine_sound is not None:
            if self.dynstate.tl <= 1.0:
                sfac = self.dynstate.tl
                engvol = self.engminvol + sfac * (self.engmaxvol - self.engminvol)
            else:
                sfac = self.dynstate.tl - 1.0
                engvol = self.engminvolab + sfac * (self.engmaxvolab - self.engminvolab)
            self.engine_sound.set_volume(engvol)
            if self.cockpit_engine_sound is not None:
                self.cockpit_engine_sound.set_volume(engvol)
                # Switch sounds if necessary.
                if self._prev_cockpit_active != self.world.player.cockpit.active:
                    self._prev_cockpit_active = self.world.player.cockpit.active
                    if self.world.player.cockpit.active:
                        self.engine_sound.pause()
                        self.cockpit_engine_sound.play()
                    else:
                        self.engine_sound.play()
                        self.cockpit_engine_sound.pause()

        # Turn props.
        if self._props and cdist < self._fardist_props:
            for ps in self._props.values():
                if ps.rpm > ps.targrpm:
                    ps.rpm = max(ps.rpm - ps.rpmdacc * dt, ps.targrpm)
                elif ps.rpm < ps.targrpm:
                    ps.rpm = min(ps.rpm + ps.rpmacc * dt, ps.targrpm)
                dangdeg = (ps.rpm * 6.0) * dt * ps.turndir
                for pnd in ps.nodes:
                    pnd.setR(pnd.getR() + dangdeg)

        # Update variable sweep.
        if self.varsweepmach:
            speed = vel.length()
            self._varsweep_target_ang = self._get_sweep_angle(speed, pos[2])
            if self._varsweep_ang != self._varsweep_target_ang:
                if self._varsweep_force_jump:
                    self._varsweep_ang = self._varsweep_target_ang
                    self._varsweep_force_jump = False
                else:
                    self._varsweep_ang = update_towards(
                        self._varsweep_target_ang, self._varsweep_ang,
                        self.varsweepspeed, dt)
                self._set_sweep_pivot(self._varsweep_ang)

        # Flyby sound handling.
        if not base.with_sound_doppler and self.flybysoundname:
            # If player is in control, play flyby sound only if current chaser
            # is in cockpit, to avoid strange effects when launching weapons, etc.
            refbody = None
            if (self.world.player and self.world.player.alive and
                self.world.player_control_level <= 1):
                refbody = self.world.player.ac
                attached = self.world.player.ac is self
            elif self.world.chaser:
                refbody = self.world.chaser
                attached = self.world.chaser.is_attached_to(self)
            if refbody is not None and not refbody.alive:
                refbody = None
                attached = False
            if refbody and not refbody.ignore_flyby and not attached:
                if self.dist(refbody) < 60:
                    refvel = refbody.vel()
                    #if abs((vel - refvel).dot(unitv(refvel))) > 100:
                    if (vel - refvel).length() > 50:
                        if not self._in_flyby:
                            snd = Sound3D(
                                path=("audio/sounds/%s.ogg" % self.flybysoundname),
                                parent=self, subnode=refbody.node,
                                limnum="flyby", volume=1.0, fadetime=0.01)
                            snd.play()
                            self._in_flyby = True
                else:
                    self._in_flyby = False

        # Check jamming.
        if self.radarrange:
            self._jm_wait -= dt
            if self._jm_wait <= 0.0:
                pfl = self._jm_period_float
                self._jm_wait = self._jm_period + uniform(-pfl, pfl)
                allied_sides = self.world.get_allied_sides(self.side)
                self.jammed = False
                for family in self._jm_carrier_families:
                    for body in self.world.iter_bodies(family):
                        if (not body.shotdown and body.jammers and
                            body.side not in allied_sides):
                            jdist = 0.0
                            for jammer in body.jammers:
                                jdist += jammer.ptype.jamradius * len(jammer.points)
                            bdist = self.dist(body)
                            if bdist < jdist:
                                self.jammed = True
                                break
                    if self.jammed:
                        break
                if not self.jammed:
                    for carpet in JammingCarpet.iter_carpets():
                        if (carpet.alive and carpet.active and
                            carpet.side not in allied_sides):
                            cdist = (pos - carpet.carpetpos).length()
                            jdist = carpet.carpetradius
                            if cdist < jdist:
                                self.jammed = True
                                break

        self._update_vortices(dt)

        if self.decoys:
            self.decoys = [d for d in self.decoys if d.alive]

        if self._fudge_missile_attack:
            for t, mls in self._act_matk_enroute.items():
                mod_mls = [ml for ml in mls if ml.alive]
                if mod_mls:
                    self._act_matk_enroute[t] = mod_mls
                else:
                    self._act_matk_enroute.pop(t)

        if self._wait_damage_recovery > 0.0:
            self._wait_damage_recovery -= dt
            if self._wait_damage_recovery <= 0.0:
                self.damage = 0.0
                self._damage_critical = 0.0
                self._breakup_track_hits_gun_level = 0.0

        if (not self.world.player or self.world.player.ac is not self or
            self.world.player_control_level != 0):
            if not self.controlout:
                #self._update_act_0(dt)
                self._update_act_1(dt)
                #self._update_act_2(dt)
            else:
                self._update_act_out(dt)

        if self._state_info_text is not None:
            self._update_state_info(dt)

        if self._trace is not None and self._prev_pos is not None:
            while self._trace_len >= self._trace_maxlen and self._trace_segs:
                tseg = self._trace_segs.pop(0)
                tlen = self._trace_lens.pop(0)
                self._trace_len -= tlen
            self._trace_segs.append((self._prev_pos, pos))
            self._trace_lens.append((pos - self._prev_pos).length())
            self._trace_len += self._trace_lens[-1]
            self._trace.reset()
            self._trace.drawLines(self._trace_segs)
            #self._trace.drawTo(pos)
            self._trace.create()

        self._prev_pos = pos
        self._prev_vel = vel
        self._prev_gsp = dq.gsp
        self._prev_gsr = dq.gsr
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
        for podlauncher in self.podlaunchers:
            podlauncher.destroy()
        for dropper in self.droppers:
            dropper.destroy()
        for jammer in self.jammers:
            jammer.destroy()
        for tanker in self.tankers:
            tanker.destroy()
        if self._dummy_cannon is not None:
            self._dummy_cannon.destroy()
        if self._state_info_text is not None:
            self._state_info_text.removeNode()
        if self._trace is not None:
            self._trace.removeNode()
        self._cw_sensorpack.destroy()
        self._aw_sensorpack.destroy()
        Body.destroy(self)


    def collide (self, obody, chbx, cpos):

        inert = Body.collide(self, obody, chbx, cpos)
        if inert:
            return True

        if obody.hitforce > self.minhitdmg:
            self.damage += obody.hitforce
        if obody.hitforce > self.maxhitdmg and self.damage < self.strength:
            self.damage = self.strength
        self._shake_last_hitforce += obody.hitforce

        if isinstance(obody, Shell):
            self._breakup_track_hits_gun_level += obody.hitforce
        else: # volume hits, e.g. explosion or collision
            self._breakup_track_hits_vol.append((obody.hitforce, self.world.time))

        while (self.damage > self.strength and
               self.failure_level < self.max_failure_level):
            self.failure_level += 1
            if self.failure_level == 1:
                self._add_damage_trails(level=1)
            elif self.failure_level == 2:
                pass
            elif self.failure_level == 3:
                d100 = randrange(100)
                if d100 >= 80:
                    self.max_failure_level += 1
                    for trail in self.damage_trails:
                        trail.destroy()
                    self._add_damage_trails(level=2)
            else:
                d100 = randrange(100)
                if d100 >= 90:
                    self.max_failure_level += 1
            self.damage -= self.strength
            self._breakup_track_hits_gun_fixed += self._breakup_track_hits_gun_level
            self._breakup_track_hits_gun_level = 0.0

        if chbx.critical:
            self._damage_critical += obody.hitforce
            if self._damage_critical > self.strength * 0.5:
                self.explode_minor()
                self.failure_level = self.max_failure_level

        self._wait_damage_recovery = self.dmgtime

        if self.failure_level >= self.max_failure_level:
            self.set_shotdown(3.0)
            self.target = None

            d100 = randrange(100)
            if d100 < 20:
                firedelay = fx_uniform(0.1, 1.0)
                self.explode_minor()
            elif d100 >= 80:
                firedelay = 3.0
            else:
                firedelay = fx_choice([0.1, fx_uniform(0.5, 6.0)])
                snd = Sound3D(path="audio/sounds/%s.ogg" % "explosion01",
                              parent=self, volume=1.0, fadetime=0.1)
                snd.play()

            if self.engine_sound is not None:
                self.engine_sound.stop()
            if self.cockpit_engine_sound is not None:
                self.cockpit_engine_sound.stop()
            for trail in self.exhaust_trails:
                trail.destroy()
            self.exhaust_trails = []
            for trail in self.damage_trails:
                trail.destroy()
            self.damage_trails = []

            fire_n_smoke_1(
                parent=self, store=self.damage_trails,
                sclfact=0.1 * self._size_xy * fx_uniform(0.9, 1.2),
                emradfact=0.1 * self._size_xy * fx_uniform(0.9, 1.1),
                fcolor=rgba(255, 255, 255, 1.0),
                fcolorend=rgba(247, 203, 101, 1.0),
                ftcol=0.6,
                fpos=Vec3(0.0, 0.0, 0.0),
                fpoolsize=24,
                flength=36.0,
                fspeed=42,
                fdelay=firedelay,
                spos=Vec3(0.0, 0.0, 0.0),
                slifespan=3.0,
                stcol=0.1)

            # Switch to shotdown model.
            # Or set shotdown maps.
            # NOTE: To avoid conflict with a possible subsequent ejection
            # in eject method, mask the existence of the shotdown model.
            if self._shotdown_modelnode is not None:
                self.modelnode.removeNode()
                self.modelnode = self._shotdown_modelnode
                self.modelnode.reparentTo(self.node)
                self.models = self._shotdown_models
                self.fardists = self._shotdown_fardists
                self.texture = self._shotdown_texture
                self._shotdown_modelnode = None
            elif self._shotdown_change_maps:
                for model in self.models:
                    set_texture(model,
                                texture=self._shotdown_texture,
                                normalmap=self._shotdown_normalmap,
                                glowmap=self._shotdown_glowmap,
                                glossmap=self._shotdown_glossmap,
                                shadowmap=self.world.shadow_texture)

            # Set up breakup.
            for handle in ("fixed_external_misc", "fixed_external_misc_1", "fixed_external_misc_2"):
                if randunit() > 0.6:
                    for model in self.models:
                        nd = model.find("**/%s" % handle)
                        if not nd.isEmpty():
                            nd.removeNode()
            ref_hitforce_vol = 0
            while self._breakup_track_hits_vol:
                hitforce, time = self._breakup_track_hits_vol.pop()
                if time + self._breakup_hit_time_range < self.world.time:
                    break
                ref_hitforce_vol = max(ref_hitforce_vol, hitforce)
            ref_hitforce_gun = self._breakup_track_hits_gun_fixed
            ref_hitforce_gun *= self._breakup_gun_damage_factor
            selected_breakupdata = []
            if ref_hitforce_vol > ref_hitforce_gun:
                for bkpd in self.breakupdata:
                    ref_damage = randunit() * bkpd.limdamage
                    if ref_damage < ref_hitforce_vol:
                        selected_breakupdata.append(bkpd)
            elif ref_hitforce_gun > 0:
                nearest_bkpd = None
                nearest_dist = None
                for bkpd in self.breakupdata:
                    handle = bkpd.handle
                    if isinstance(handle, (list, tuple)):
                        handle = handle[0]
                    nd = self.models[0].find("**/%s" % handle)
                    dist = (cpos - nd.getPos(self.node)).length()
                    if nearest_dist is None or nearest_dist > dist:
                        nearest_dist = dist
                        nearest_bkpd = bkpd
                if nearest_bkpd:
                    bkpd = nearest_bkpd
                    ref_damage = randunit() * bkpd.limdamage
                    if ref_damage < ref_hitforce_gun:
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
                for podlauncher in self.podlaunchers:
                    podlauncher.destroy()
                for dropper in self.droppers:
                    dropper.destroy()
                for jammer in self.jammers:
                    jammer.destroy()
                for tanker in self.tankers:
                    tanker.destroy()
                AirBreakup(self, selected_breakupdata)
                if len(selected_breakupdata) == len(self.breakupdata):
                    if randunit() < 0.8:
                        self.explode(destroy=False)
                    else:
                        self.explode(destroy=(not self.must_not_explode))

            # Set up falling autopilot.
            ap = self._init_shotdown_1(obody, chbx, cpos)
            self._act_input_controlout = ap

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
            sizefac=0.4 * self._size_xy, timefac=1.2, amplfac=1.4,
            smgray=pycv(py=(10, 30), c=(220, 255)),
            debrispart=(4, 6), debrispitch=debrispitch, debristcol=0.2)
        # exp = Splash(world=self.world, pos=self.pos(),
                     # size=42.0, relsink=0.5,
                     # numquads=1,
                     # texture="images/particles/effects-rocket-exp-3.png",
                     # texsplit=8, fps=24, numframes=28,
                     # glowmap="images/particles/effects-rocket-exp-3_gw.png")
        snd = Sound3D(path="audio/sounds/%s.ogg" % "explosion01",
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
            smgray=pycv(py=(65, 80), c=(220, 255)), smred=0)
        snd = Sound3D(path="audio/sounds/%s.ogg" % "explosion01",
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

        dq = self.dynstate
        if dq is None:
            self._init_dynamics()
            dq = self.dynstate

        if self.helix_dummy is not None:
            ret = self._move_by_helix(dq, dt)
            self.stalled = False
        else:
            ret = self._move_by_cntl(dt)
            ret = self._update_buffet(dt, ret)
            if self.cannons:
                ret = self._update_recoil(dt, ret)
            ret = self._update_shake(dt, ret)
            ret = self._update_rolling(dt, ret)
            self.stalled = (not dq.amin <= dq.a <= dq.amax)

        pos, fdir, udir, rdir = ret
        self.node.setPos(vtof(pos))
        set_hpr_vfu(self.node, vtof(fdir), vtof(udir))


    def _move_by_cntl (self, dtm):

        dq = self.dynstate

        da, dr, dtl = self._daoa, self._droll, self._dthrottle
        dbrd = self._dairbrake
        dgso = self._dsteer
        if callable(da):
            da = da(dq, dtm)
        if callable(dr):
            dr = dr(dq, dtm)
        if callable(dtl):
            dtl = dtl(dq, dtm)
        if callable(dbrd):
            dbrd = dbrd(dq, dtm)
        if callable(dgso):
            dgso = dgso(dq, dtm)
        if self.fuel <= 0.0:
            tlv = -0.25
            dtl = clamp(tlv * dtm, -dq.tl, 0.0)

        dq.m = self.mass # may change by releasing stores, etc.
        dq.fld = self._flaps
        dq.lg = self._landgear
        dq.brw = self._wheelbrake

        if self._landgear:
            hg, ng, tg = self._ground_data()
        else:
            hg, ng, tg = None, None, None
        self.dyn.update_fstep(dq, da, dr, dtl, dbrd, dgso, dtm,
                              hg, ng, tg,
                              extraq=True)

        mon = False
        #mon = (self.name == "red")
        pef = 50
        if mon and pef and self.world.frame % pef == 0:
            dbgval(1, "mbcntl",
                   (self.world.time, "%7.2f", "tm", "s"),
                   (dq.m, "%6.0f", "m", "kg"),
                   (dq.h, "%5.0f", "h", "m"),
                   (dq.v, "%5.1f", "v", "m/s"),
                   (dq.cr, "%+6.1f", "cr", "m/s"),
                   (degrees(dq.tr), "%+7.2f", "tr", "deg/s"),
                   (dq.ct, "%+6.2f", "ct", "m/s^2"),
                   (dq.n, "%+6.2f", "n"),
                   (degrees(dq.hdg), "%+6.1f", "hdg", "deg"),
                   (degrees(dq.bnk), "%+6.1f", "bnk", "deg"),
                   (degrees(dq.tht), "%+7.2f", "tht", "deg"),
                   (degrees(dq.a), "%+6.2f", "a", "deg"),
                   (dq.tl, "%5.3f", "tl"))

        dfuel = dq.m - self.mass
        dintfuel = self._update_tankers(dfuel)
        self.fuel += dintfuel
        if self.fuel < 0.0:
            dfuel -= self.fuel
            self.fuel = 0.0
        self.mass = dq.m
        self.fuelfill = self.fuel / self.maxfuel
        if dtm > 0.0:
            self.fuelfillcons = dfuel / dtm
            self.fuelcons = self.fuelfillcons / self.maxfuel

        # Needed in base class.
        self._prev_vel = self._vel
        self._vel = vtof(dq.u)
        self._acc = vtof(dq.b)
        self._angvel = vtof(dq.o)
        self._angacc = vtof(dq.s)

        pos, fdir, udir, rdir = dq.p, dq.at, dq.an, dq.ab
        #pos, fdir, udir, rdir = dq.p, dq.xit, dq.ant, dq.anb
        return pos, fdir, udir, rdir


    # (debugging)
    @staticmethod
    def _move_by_helix (dq, dtm):

        g = dq.g
        p, v, hdg, cr, tr = dq.p, dq.v, dq.hdg, dq.cr, dq.tr

        p1 = Point3D(p)
        u1 = Vec3D()
        hdg1 = hdg

        if cr != 0.0:
            p1 += Vec3D(0.0, 0.0, cr * dtm)

        xinh = Vec3D(-cos(hdg), -sin(hdg), 0.0)
        if tr != 0.0:
            hdg1 += tr * dtm
            xinh1 = Vec3D(-cos(hdg1), -sin(hdg1), 0.0)
            b1 = xinh1 * (v * tr)
            srad = v / tr
            p1 += (xinh - xinh1) * srad
            n1 = v**2 / (abs(srad) * g)
        else:
            b1 = Vec3D()
            xith = Vec3D(-sin(hdg), cos(hdg), 0.0)
            p1 += xith * (v**2 - cr**2)**0.5 * dtm
            n1 = 1.0

        tht1 = atan2(cr, v)
        xit1 = Vec3D(-sin(hdg1) * cos(tht1), cos(hdg1) * cos(tht1), sin(tht1))
        u1 = xit1 * v

        tl1 = 0.5

        dq.p, dq.h, dq.hdg, dq.tht = p1, p1[2], hdg1, tht1
        dq.u, dq.b, dq.n = u1, b1, n1
        dq.tl = tl1

        pos, fdir, udir = dq.p, xit1, Vec3D(0.0, 0.0, 1.0)
        return pos, fdir, udir


    def _update_buffet (self, dt, posatt):

        dq = self.dynstate

        self._wait_buffet -= dt
        if self._wait_buffet <= 0.0:
            self._wait_buffet += self._buffet_period
            aoa, aoa_min, aoa_max = dq.a, dq.amin, dq.amax
            aoa_span = aoa_max - aoa_min
            if aoa > aoa_max - aoa_span * 0.1:
                aoa_lim = aoa_max
            elif aoa < aoa_min + aoa_span * 0.1:
                aoa_lim = aoa_min
            else:
                aoa_lim = aoa
            buffet_strength = clamp(abs(aoa - aoa_lim) / (aoa_span * 0.2),
                                    0.0, 1.0)
            daoa_lim_ref = radians(0.30)
            self._buffet_daoa_speed = daoa_lim_ref / self._buffet_period
            dbnk_lim_ref = radians(0.80)
            self._buffet_dbnk_speed = dbnk_lim_ref / self._buffet_period
            if buffet_strength > 0.0:
                daoa_lim = daoa_lim_ref * buffet_strength
                if self.buffet_daoa < 0.0:
                    self._buffet_daoa_targ = uniform(0.0, daoa_lim)
                else:
                    self._buffet_daoa_targ = uniform(-daoa_lim, 0.0)
                dbnk_lim = dbnk_lim_ref * buffet_strength
                if self.buffet_dbnk < 0.0:
                    self._buffet_dbnk_targ = uniform(0.0, dbnk_lim)
                else:
                    self._buffet_dbnk_targ = uniform(-dbnk_lim, 0.0)
                self._buffet_in_progress = True
            else:
                self._buffet_daoa_targ = 0.0
                self._buffet_dbnk_targ = 0.0

        if self._buffet_in_progress:
            off_targ = False
            self.buffet_daoa = update_towards(
                self._buffet_daoa_targ, self.buffet_daoa,
                self._buffet_daoa_speed, dt)
            off_targ = off_targ or self._buffet_daoa_targ != self.buffet_daoa
            self.buffet_dbnk = update_towards(
                self._buffet_dbnk_targ, self.buffet_dbnk,
                self._buffet_dbnk_speed, dt)
            off_targ = off_targ or self._buffet_dbnk_targ != self.buffet_dbnk
            self._buffet_in_progress = off_targ
            pos, fdir, udir, rdir = posatt
            rot = QuatD()
            rot.setFromAxisAngleRad(self.buffet_daoa, rdir)
            fdir1 = unitv(Vec3D(rot.xform(fdir)))
            rot.setFromAxisAngleRad(self.buffet_dbnk, fdir)
            udir1 = unitv(Vec3D(rot.xform(udir)))
            return pos, fdir1, udir1, rdir
        else:
            return posatt


    _recoil_ref_ke = 0.8 * 800.0**2

    def _update_recoil (self, dt, posatt):

        self._wait_recoil -= dt
        if self._wait_recoil <= 0.0:
            refcannon = self.cannons[0]
            if self._recoil_period is None:
                self._recoil_period = refcannon.rate
                self._recoil_strength = sum(
                    (c.stype.mass * c.mzvel**2) / (Plane._recoil_ref_ke)
                    for c in self.cannons)
                # self._recoil_dz_max = 0.0020
                # self._recoil_dx_max = 0.0005
                # self._recoil_daoa_max = radians(0.05)
                # self._recoil_dbnk_max = radians(0.40)
                self._recoil_dz_max = 0.0010
                self._recoil_dx_max = 0.0003
                self._recoil_daoa_max = radians(0.03)
                self._recoil_dbnk_max = radians(0.20)
                self._recoil_dz_speed = self._recoil_dz_max / self._recoil_period
                self._recoil_dx_speed = self._recoil_dx_max / self._recoil_period
                self._recoil_daoa_speed = self._recoil_daoa_max / self._recoil_period
                self._recoil_dbnk_speed = self._recoil_dbnk_max / self._recoil_period
            self._wait_recoil += self._recoil_period
            if self._recoil_prev_ammo is None:
                self._recoil_prev_ammo = refcannon.ammo
            if self._recoil_prev_ammo != refcannon.ammo:
                self._recoil_prev_ammo = refcannon.ammo
                dz_max = uniform(-self._recoil_dz_max * 0.25, self._recoil_dz_max)
                self._recoil_dz_targ = dz_max * self._recoil_strength
                dx_max = uniform(-self._recoil_dx_max, self._recoil_dx_max)
                self._recoil_dx_targ = dx_max * self._recoil_strength
                daoa_max = uniform(-self._recoil_daoa_max, self._recoil_daoa_max)
                self._recoil_daoa_targ = daoa_max * self._recoil_strength
                dbnk_max = uniform(-self._recoil_dbnk_max, self._recoil_dbnk_max)
                self._recoil_dbnk_targ = dbnk_max * self._recoil_strength
                self._recoil_in_progress = True
            else:
                self._recoil_dz_targ = 0.0
                self._recoil_dx_targ = 0.0
                self._recoil_daoa_targ = 0.0
                self._recoil_dbnk_targ = 0.0

        if self._recoil_in_progress:
            off_targ = False
            self.recoil_dx = update_towards(
                self._recoil_dx_targ, self.recoil_dx,
                self._recoil_dx_speed, dt)
            off_targ = off_targ or self._recoil_dx_targ != self.recoil_dx
            self.recoil_dz = update_towards(
                self._recoil_dz_targ, self.recoil_dz,
                self._recoil_dz_speed, dt)
            off_targ = off_targ or self._recoil_dz_targ != self.recoil_dz
            self.recoil_daoa = update_towards(
                self._recoil_daoa_targ, self.recoil_daoa,
                self._recoil_daoa_speed, dt)
            off_targ = off_targ or self._recoil_daoa_targ != self.recoil_daoa
            self.recoil_dbnk = update_towards(
                self._recoil_dbnk_targ, self.recoil_dbnk,
                self._recoil_dbnk_speed, dt)
            off_targ = off_targ or self._recoil_dbnk_targ != self.recoil_dbnk
            self._recoil_in_progress = off_targ
            pos, fdir, udir, rdir = posatt
            dpos = udir * self.recoil_dz + rdir * self.recoil_dz
            pos1 = pos + dpos
            rot = QuatD()
            rot.setFromAxisAngleRad(self.recoil_daoa, rdir)
            fdir1 = unitv(Vec3D(rot.xform(fdir)))
            rot.setFromAxisAngleRad(self.recoil_dbnk, fdir)
            udir1 = unitv(Vec3D(rot.xform(udir)))
            return pos1, fdir1, udir1, rdir
        else:
            return posatt


    _shake_ref_hitforce = 30.0
    _shake_ref_mass = 15000.0
    _shake_ref_duration = 2.0
    _shake_ref_strength = 1.0
    _shake_max_fac = 2.0
    _shake_ref_period = 0.05
    _shake_ref_dx_max = 0.100
    _shake_ref_dz_max = 0.100
    _shake_ref_daoa_max = radians(2.0)
    _shake_ref_dbnk_max = radians(10.0)

    def _update_shake (self, dt, posatt):

        if self._shake_last_hitforce > 0.0:
            hitforce = self._shake_last_hitforce
            self._shake_last_hitforce = 0.0
            fac_hitforce = (hitforce / Plane._shake_ref_hitforce)**1
            fac_mass = (self.mass / Plane._shake_ref_mass)**-1
            fac_total = fac_hitforce * fac_mass
            fac_total = min(fac_total, Plane._shake_max_fac)
            strength = Plane._shake_ref_strength * fac_total
            if self._shake_strength < strength:
                self._shake_strength = strength
                duration = Plane._shake_ref_duration * fac_total
                self._shake_duration = duration
                self._shake_cycle_period = Plane._shake_ref_period * fac_total
                self._shake_time = 0.0
                self._shake_cycle_time = self._shake_cycle_period
                self._shake_in_progress = True

        if self._shake_in_progress:
            if self._shake_time < self._shake_duration:
                fac_time = self._shake_time / self._shake_duration
                strength = self._shake_strength * (1.0 - fac_time)
                period = self._shake_cycle_period
                if self._shake_cycle_time >= period:
                    self._shake_cycle_time -= period
                    dz_max = Plane._shake_ref_dz_max * strength
                    dx_max = Plane._shake_ref_dx_max * strength
                    daoa_max = Plane._shake_ref_daoa_max * strength
                    dbnk_max = Plane._shake_ref_dbnk_max * strength
                    self._shake_dz_speed = max(dz_max, abs(self.shake_dz)) / period
                    self._shake_dx_speed = max(dx_max, abs(self.shake_dx)) / period
                    self._shake_daoa_speed = max(daoa_max, abs(self.shake_daoa)) / period
                    self._shake_dbnk_speed = max(dbnk_max, abs(self.shake_dbnk)) / period
                    self._shake_dz_targ = uniform(-dz_max, dz_max)
                    self._shake_dx_targ = uniform(-dx_max, dx_max)
                    self._shake_daoa_targ = uniform(-daoa_max, daoa_max)
                    self._shake_dbnk_targ = uniform(-dbnk_max, dbnk_max)
            else:
                fac_time = 1.0
                strength = 0.0
                self._shake_dz_targ = 0.0
                self._shake_dx_targ = 0.0
                self._shake_daoa_targ = 0.0
                self._shake_dbnk_targ = 0.0
                adt = (dt * 0.5 + 1e-6)
                self._shake_dz_speed = abs(self.shake_dz) / adt
                self._shake_dx_speed = abs(self.shake_dx) / adt
                self._shake_daoa_speed = abs(self.shake_daoa) / adt
                self._shake_dbnk_speed = abs(self.shake_dbnk) / adt
            self._shake_time += dt
            self._shake_cycle_time += dt
            self._shake_strength = strength

            off_targ = False
            self.shake_dx = update_towards(
                self._shake_dx_targ, self.shake_dx,
                self._shake_dx_speed, dt)
            off_targ = off_targ or self._shake_dx_targ != self.shake_dx
            self.shake_dz = update_towards(
                self._shake_dz_targ, self.shake_dz,
                self._shake_dz_speed, dt)
            off_targ = off_targ or self._shake_dz_targ != self.shake_dz
            self.shake_daoa = update_towards(
                self._shake_daoa_targ, self.shake_daoa,
                self._shake_daoa_speed, dt)
            off_targ = off_targ or self._shake_daoa_targ != self.shake_daoa
            self.shake_dbnk = update_towards(
                self._shake_dbnk_targ, self.shake_dbnk,
                self._shake_dbnk_speed, dt)
            off_targ = off_targ or self._shake_dbnk_targ != self.shake_dbnk
            self._shake_in_progress = off_targ or fac_time < 1.0
            pos, fdir, udir, rdir = posatt
            dpos = udir * self.shake_dz + rdir * self.shake_dz
            pos1 = pos + dpos
            rot = QuatD()
            rot.setFromAxisAngleRad(self.shake_daoa, rdir)
            fdir1 = unitv(Vec3D(rot.xform(fdir)))
            rot.setFromAxisAngleRad(self.shake_dbnk, fdir)
            udir1 = unitv(Vec3D(rot.xform(udir)))
            return pos1, fdir1, udir1, rdir
        else:
            return posatt


    _rolling_ref_mass = 15000.0
    _rolling_ref_speed = 100.0
    _rolling_ref_max_period = 0.050
    _rolling_ref_max_du = 0.0010

    def _update_rolling (self, dt, posatt):

        if self._rolling_in_progress:
            dq = self.dynstate
            if self._rolling_time >= self._rolling_period:
                mfac = self.mass / Plane._rolling_ref_mass
                sfac = self.speed() / Plane._rolling_ref_speed
                tfac = dq.grh
                max_du = Plane._rolling_ref_max_du * mfac**-0.5 * sfac * tfac
                max_period = Plane._rolling_ref_max_period * mfac**-0.5 * sfac
                if self.onground:
                    targ_du = uniform(-max_du, max_du)
                else:
                    targ_du = 0.0
                period = uniform(0.5 * max_period, max_period)
                speed_du = abs(targ_du - self.rolling_du) / period
                self._rolling_targ_du = targ_du
                self._rolling_speed_du = speed_du
                self._rolling_period = period
                self._rolling_time = 0.0
            pos, fdir, udir, rdir = posatt
            self.rolling_du = update_towards(
                self._rolling_targ_du, self.rolling_du,
                self._rolling_speed_du, dt)
            if self.rolling_du == 0.0:
                self._rolling_in_progress = False
            self._rolling_time += dt
            pos1 = pos + udir * self.rolling_du
            return pos1, fdir, udir, rdir
        else:
            if self.onground:
                self._rolling_in_progress = True
                self._rolling_period = 0.0
            return posatt


    def _update_act_0 (self, dt):

        assert not self.controlout

        pass


    def _update_act_1 (self, dt):

        assert not self.controlout

        pos = self.pos()
        vel = self.vel()

        # Check missile attack.
        if self._attacking_missile is None:
            contacts_by_family = self._aw_sensorpack.contacts_by_family()
            contacts_selected = []
            contacts_rocket_vis = contacts_by_family.get("rocket-v", [])
            for contact in contacts_rocket_vis:
                rck = contact.body.parent
                if rck.alive and rck.target is self:
                    condist = (pos - rck.pos()).length()
                    contacts_selected.append((condist, rck))
            contacts_rocket = contacts_by_family.get("rocket", [])
            for contact in contacts_rocket:
                rck = contact.body
                if rck.alive and rck.target is self:
                    condist = (pos - rck.pos()).length()
                    contacts_selected.append((condist, rck))
            if contacts_selected:
                self._attacking_missile = min(contacts_selected)[1]
                if self.evade_missile_manouver:
                    self._act_state = AutoProps()
                    self._act_pause = 0.0
                    if not self._aatk_paused:
                        self._evade_missile_aatk_paused = True
                        self._aatk_paused = True
        else:
            if (not self._attacking_missile.alive or
                self._attacking_missile.target is not self):
                self._attacking_missile = None
                if self._evade_missile_aatk_paused:
                    self._evade_missile_aatk_paused = False
                    self._aatk_paused = False
                if self.evade_missile_manouver:
                    self._act_state = AutoProps()
                    self._act_pause = 0.0

        # Update decoys.
        if self.evade_missile_decoy:
            if self._wait_decoy > 0.0:
                self._wait_decoy -= dt
            if self._attacking_missile and self.flarechaff:
                rdist = self._attacking_missile.dist(self)
                rspeed = (self._attacking_missile.vel() - vel).length()
                rtime = rdist / rspeed
                if rtime < self._decoy_missile_dist_time:
                    if self._wait_decoy <= 0.0:
                        self._wait_decoy = self.fire_decoy()

        # Choose target if auto attack is engaged.
        if self._aatk_families and not self._aatk_paused:
            self._aatk_wait -= dt
            if self._aatk_wait <= 0.0:
                pfl = self._aatk_period_float
                self._aatk_wait = self._aatk_period + uniform(-pfl, pfl)
                tbody, prio = self._choose_target(self._aatk_families)
                if tbody and tbody is not self._act_target:
                    if self._act_target and self._act_target.alive:
                        # Check whether to cancel current target.
                        tdist = self.dist(self._act_target)
                        tdistn = self.dist(tbody)
                        if (prio > self._aatk_targprio or
                            tdist < self._aatk_maxvisdist or
                            tdistn > tdist + 0.5 * self._aatk_maxvisdist):
                            tbody = None
                    if tbody:
                        dbgval(1, "auto-attack",
                               (self.world.time, "%.1f", "time", "s"),
                               ("%s(%s)" % (self.name, self.species), "%s", "attacker"),
                               ("%s(%s)" % (tbody.name, tbody.species), "%s", "defender"))
                        if self._act_leader:
                            self._aatk_prev_leader = self._act_leader
                            self._aatk_prev_formpos = self._act_formpos
                        self.set_act(target=tbody)
                        self._aatk_targprio = prio
                        self._aatk_paused = False

        # Cancel target if no appropriate weapon.
        if self._act_target:
            if not self.cannons and not self.jammers:
                self._act_target = None
        # Cancel target if friendly.
        if self._act_target:
            allied_sides = self.world.get_allied_sides(self.side)
            contacts_by_body = self.sensorpack.contacts_by_body()
            contact = contacts_by_body.get(self._act_target)
            if contact is not None and contact.side in allied_sides:
                self._act_target = None

        # Apply autopilot.
        self._act_pause -= dt
        if self._act_active and self._act_pause <= 0.5 * dt:
            self.target = None
            if self._attacking_missile and self.evade_missile_manouver:
                # Nevertheless register pre-evasion target, for game logic.
                if self._act_target:
                    self.target = self._act_target
                self._act_pause = self._act_input_mslevade()
            elif self._act_target:
                if self._act_target.alive and not self._act_target.shotdown:
                    self.target = self._act_target
                    self._act_pause = self._act_input_attack()
                elif self._aatk_prev_leader:
                    self.set_act(leader=self._aatk_prev_leader,
                                 formpos=self._aatk_prev_formpos)
                else:
                    self.set_act(enroute=True)
                    # ...if no route set, goes circling.
            elif self._act_leader:
                if self._act_leader.alive and not self._act_leader.shotdown:
                    self._act_pause = self._act_input_form()
                else:
                    if self._act_leader._route_points:
                        self.set_route(points=self._act_leader._route_points,
                                       patrol=self._act_leader._route_patrol,
                                       circle=self._act_leader._route_circle)
                    self.set_act(enroute=True)
            else:
                self._act_pause = self._act_input_nav()


    def _update_act_2 (self, dt):

        assert not self.controlout

        pos = self.pos()
        vel = self.vel()


    def _update_act_out (self, dt):

        assert self.controlout

        self.target = None

        self._act_pause -= dt
        if self._act_active and self._act_pause <= 0.5 * dt:
            if self._act_input_controlout:
                self._act_pause = self._act_input_controlout()

        # Execute ejection.
        if self.ejection_triggered and not self.ejection:
            self._wait_eject -= self.world.dt
            if self._wait_eject <= 0.0:
                wrefbody = (self.world.player and self.world.player.ac is self)
                self.ejection = Ejection(plane=self, wrefbody=wrefbody)


    def set_auto_attack (self, families=[]):

        self._aatk_families = families
        #self.sensorpack.start_scanning(families)


    def _choose_target (self, families):

        allied_sides = self.world.get_allied_sides(self.side)
        pos = self.pos()

        # Test for return-fire attack on nearest attacker,
        # from the first requested family onwards.
        # Only return fire if attacker in visual.
        contacts_by_sensor = self.sensorpack.contacts_by_sensor()
        contacts_targd = contacts_by_sensor.get("magic-targd", [])
        if contacts_targd:
            contacts_visair = contacts_by_sensor.get("visual-air", [])
            contacts_visgnd = contacts_by_sensor.get("visual-ground", [])
            contacts_selected = []
            for contact in contacts_targd:
                if not contact.body.alive or contact.body.shotdown:
                    continue
                if (contact.family in families and contact.pos is not None and
                    (contact in contacts_visair or contact in contacts_visgnd)):
                    condist = (pos - contact.pos).length()
                    contacts_selected.append((condist, contact))
            if contacts_selected:
                contact = min(contacts_selected)[1]
                return contact.body, 5

        # Find first family with an attackabe contact,
        # and sort by increasing distance within that family.
        contacts_by_family = self.sensorpack.contacts_by_family()
        contacts_selected = []
        for family in families:
            for contact in contacts_by_family.get(family, []):
                if not contact.body.alive or contact.body.shotdown:
                    continue
                if contact.side not in allied_sides and contact.pos is not None:
                    condist = (self.pos() - contact.pos).length()
                    contacts_selected.append((condist, contact))
            if contacts_selected:
                break
        if contacts_selected:
            contact = min(contacts_selected)[1]
            return contact.body, 0

        return None, 0


    def set_route (self, points, patrol=False, circle=False):

        self._route_points = points
        self._route_patrol = patrol
        self._route_circle = circle
        self._route_current_point = 0
        self._route_point_inc = 1


    def zero_act (self):

        if self.controlout:
            return

        self.set_act()

        self._act_active = False


    # Compatibility.
    def zero_ap (self, *args, **kwargs):

        self.zero_act(*args, **kwargs)


    def set_act (self,
                 altitude=None, speed=None, climbrate=None, turnrate=None,
                 heading=None, point=None, otraltitude=None,
                 leader=None, formpos=None, target=None,
                 useab=False, maxg=None, invert=False, enroute=False):

        if self.controlout:
            return

        if leader is not None and formpos is None:
            formpos = Point3(uniform(-900.0, 900.0),
                             uniform(-400.0, 400.0),
                             uniform(-100.0, 100.0))

        self._act_altitude = altitude
        self._act_speed = speed
        self._act_climbrate = climbrate
        self._act_turnrate = turnrate
        self._act_heading = heading
        self._act_point = point
        self._act_otraltitude = otraltitude
        self._act_leader = leader
        self._act_formpos = formpos
        self._act_target = target
        self._act_useab = useab
        self._act_maxg = maxg
        self._act_invert = invert
        self._act_enroute = enroute

        # This would be automatically assigned later,
        # but do it here in order to be able to check for
        # "ac.target is something" right after this call.
        self.target = self._act_target

        # Temporarily pause automatic attack if target given,
        # enable it if target not given and auto attack was set previously.
        # (If the call arrived from auto target choice, it will unpause it
        # itself after this call.)
        if self._act_target:
            self._aatk_paused = True
            self._evade_missile_aatk_paused = False
        elif self._aatk_families:
            self._aatk_paused = False

        # If target given but no auto attack was set,
        # set up auto attack on the family of the target.
        if self._act_target and not self._aatk_families:
            self.set_auto_attack([self._act_target.family])

        # Clean previous autopilot-specific state.
        self._act_state = AutoProps()
        self._act_pause = 0.0

        self._act_active = True


    # Compatibility.
    def set_ap (self, *args, **kwargs):

        self.set_act(*args, **kwargs)


    def _act_input_nav (self):

        if not self.dynstate:
            return 0.0

        w = self.world
        dq = self.dynstate
        cq = self._act_state

        #print "========== ap-plane-nav-start (world-time=%.2f)" % (w.time)

        tclimbrate = self._act_climbrate
        tspeed = self._act_speed
        talt = self._act_altitude
        thead = self._act_heading
        tpoint = self._act_point
        tturnrate = self._act_turnrate
        totralt = self._act_otraltitude
        tmaxg = self._act_maxg
        tinvert = self._act_invert
        tenroute = self._act_enroute
        useab = 1 if (self._act_useab and self.dyn.hasab) else 0

        if tturnrate is not None:
            tturnrate = radians(tturnrate)
        if thead is not None:
            thead = radians(thead)

        mass = dq.m
        alt = dq.h
        pos = dq.p
        elev = w.elevation(pos)
        speed = dq.v
        maxg = dq.nmax
        ming = dq.nmin
        vdir = dq.xit
        vdirh = dq.xith
        phead = dq.hdg
        ppitch = dq.tht
        tmax = dq.tmax
        tmaxab = dq.tmaxab
        zdir = Vec3D(0.0, 0.0, 1.0)

        if cq.speed0 is None:
            cq.speed0, cq.alt0, cq.phead0 = speed, alt, phead

        # NOTE: Quantity set and ordering as returned by PlaneDynamics.comp_env.
        ret_mh = self.dyn.tab_all_mh[useab](mass, alt)
        (minspeed, maxspeed, amaxclimbrate, optspeedc,
         amaxturnratei, amaxturnrates, optspeedti, optspeedts,
         amaxrangefac, optspeedr, optthrottler) = ret_mh
        asfacmax = 0.95
        amaxclimbrate *= asfacmax
        amaxturnratei *= asfacmax
        amaxturnrates *= asfacmax
        ret_mhv = self.dyn.tab_all_mhv[useab](mass, alt, speed)
        (maxclimbrate, maxturnratei, maxturnrates, maxrangefac,
         maxaccel, maxthrust, levelthrust, specfuelcons, iaspeed) = ret_mhv
        sfacmax = 0.95
        maxclimbrate *= sfacmax
        maxturnratei *= sfacmax
        maxturnrates *= sfacmax

        # Min climb rate: still possible to pull up at current max loading.
        cmintht = 1.0 - ((alt - elev) * w.absgravacc * (maxg - 1.0)) / speed**2
        cmintht = clamp(cmintht, 0.0, 1.0)
        smintht = -(1.0 - cmintht**2)**0.5
        smintht = max(smintht, sin(radians(-30.0)))
        minclimbrate = speed * smintht

        # Correct targets for route target.
        if tenroute:
            if self._route_current_point is not None:
                rpos = ptod(self._route_points[self._route_current_point])
                rptdist = (rpos - pos).length()
                if rptdist < speed * 5.0:
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
                    #print "--pln-route-next-point", self.name, pos, self._route_current_point, np
                    self._route_current_point = np
                else:
                    tpoint = rpos
                if tspeed is None:
                    tspeed = optspeedr
                if tmaxg is None:
                    tmaxg = 2.0
            else:
                # No route, circle.
                tpoint = None
                thead = None
                talt = max(cq.alt0, 2000.0, elev + 1000.0)
                tspeed = optspeedti
                tturnrate = min(radians(3.0), maxturnrates)

        # Determine navigation targets for a point target.
        if tpoint is not None:
            if isinstance(tpoint, Body):
                tpoint = tpoint.pos()
            elif isinstance(tpoint, NodePath):
                tpoint = tpoint.getPos(self.world.node)
            elif isinstance(tpoint, Point2):
                tpoint = Point3(tpoint[0], tpoint[1], alt)
            dpos = vtod(tpoint) - pos
            thead = atan2(-dpos.getX(), dpos.getY())
            if talt is None:
                talt = tpoint.getZ()

        # If target altitude given as well,
        # follow terrain only if OTR altitude smaller than requested.
        if totralt is not None and talt is not None:
            if totralt < talt - elev:
                totralt = None

        # Use initial speed, altitude, and heading as targets if not given.
        if tspeed is None:
            tspeed = cq.speed0
        if talt is None and totralt is None and tclimbrate is None:
            talt = cq.alt0
        if thead is None and tturnrate is None:
            thead = cq.phead0

        # Update time.
        adt = 2.0 + uniform(-0.4, 0.4)

        # Determine target speed and vertical speed.
        if tmaxg is None:
            tmaxg = 4.0
        maxlfac = max(min(tmaxg, maxg - 1.2), 1.3)
        minlfac = max(min(-0.5 * tmaxg, -1.5), ming + 0.5)
        if tclimbrate is not None:
            speed1 = tspeed if tspeed is not None else speed
            climbrate1 = tclimbrate
        elif totralt is not None:
            # Lookahead distance.
            plfac = maxg - 1.0
            plrad = speed**2 / ((plfac - 1) * w.absgravacc)
            fwdist = plrad * 2.0
            # Average and maximum ground slope over the lookahead distance.
            gslopes = []
            nsamples = int(round((fwdist / plrad) * 3))
            for i in xrange(nsamples):
                fwseg = (fwdist / nsamples) * (i + 1)
                tpos = pos + vdirh * fwseg
                telev = self.world.elevation(tpos)
                gslope = (telev - elev) / fwseg
                gslopes.append(gslope)
            gslopeavg = sum(gslopes) / nsamples
            gslopemax = max(gslopes)
            gsangavg = atan(gslopeavg)
            gsangmax = atan(gslopemax)
            # Target climb rate and speed.
            otralt = alt - elev
            #print "--nav-otr", alt, otralt, totralt, degrees(gsangavg), degrees(gsangmax)
            vppos = Point2(0.0, alt)
            vpdir = unitv(Vec2(vdirh.length(), vdir[2]))
            grpos = Point2(0.0, elev)
            grdir = unitv(Vec2(1.0, gslopeavg))
            res = line_intersect_2d(vppos, vpdir, grpos, grdir, mults=True)
            if res:
                gsec, vplen, grlen = res
            else:
                vplen = -1e30
            climbratesl = speed * sin(gsangavg)
            if vplen > 0.0:
                secang = acos(clamp(vpdir.dot(grdir), -1.0, 1.0))
                tangrad = vplen * tan((pi - secang) / 2)
                atime = adt * 3.0
                mlfac = maxlfac if otralt > totralt else minlfac
                mlrad = speed**2 / ((mlfac - 1) * w.absgravacc)
                if mlrad > tangrad:
                    maxlfac = speed**2 / (tangrad * w.absgravacc) + 1
                    climbrate1 = climbratesl
                    speed1 = speed
                else:
                    climbrate1 = clamp((totralt - otralt) / atime + climbratesl,
                                          minclimbrate, maxclimbrate)
                    speed1 = speed
            else:
                if otralt > totralt:
                    atime = adt * 3.0
                else:
                    atime = adt * 1.0
                    maxlfac = clamp(maxlfac * 1.5, 1.0, maxg)
                climbrate1 = clamp((totralt - otralt) / atime + climbratesl,
                                      minclimbrate, maxclimbrate)
                speed1 = speed
            # TODO: Obstacle avoidance correction (gslopemax).
        elif talt is not None:
            lfac01 = maxlfac if alt > talt else minlfac
            rad01 = speed**2 / ((lfac01 - 1) * w.absgravacc)
            try:
                abs(talt - alt) < abs(rad01 * (1 - cos(ppitch)))
            except:
                dbgval(0, "nav-otr-300",
                       (talt, "%f", "talt", "m"),
                       (alt, "%f", "alt", "m"),
                       (rad01, "%f", "rad01", "m"),
                       (degrees(ppitch), "%f", "ppitch", "deg"))
                raise
            if abs(talt - alt) < abs(rad01 * (1 - cos(ppitch))):
                speed1 = speed
                climbrate1 = 0.0
            else:
                # Keep climbing or descending.
                atime = 5.0 # !!!
                climbrate1 = (talt - alt) / atime
                if climbrate1 > maxclimbrate:
                    rvv = abs(maxclimbrate / amaxclimbrate)
                    climbrate1 = maxclimbrate * rvv**0.25
                    speed1 = optspeedc
                elif climbrate1 < minclimbrate:
                    climbrate1 = minclimbrate
                    speed1 = tspeed if tspeed is not None else speed
                else:
                    speed1 = tspeed if tspeed is not None else speed
        elif tspeed is not None:
            speed1 = tspeed
            climbrate1 = 0.0
        else:
            speed1 = speed
            climbrate1 = 0.0

        # Determine target turn rate.
        if tturnrate is not None:
            turnrate1 = tturnrate
        elif thead is not None:
            atime = 5.0 # !!!
            dphead = norm_ang_delta(phead, thead)
            limturnrate1 = w.absgravacc * (maxlfac**2 - 1.0)**0.5 / speed
            maxturnrate1 = min(maxturnrates, limturnrate1)
            turnrate1 = clamp(dphead / atime, -maxturnrate1, maxturnrate1)
        else:
            turnrate1 = 0.0

        # Correct targets for turn-climb coupling.
        ret = self.dyn.correct_turn_climb(climbrate1, turnrate1,
                                          maxclimbrate, maxturnrates)
        climbrate1, turnrate1 = ret

        # Determine dummy target acceleration to reach target speed faster.
        atime = 10.0 #!!!
        crtr_fac = ((1.0 - climbrate1 / maxclimbrate) *
                    (1.0 - turnrate1 / maxturnrates))
        accel1 = clamp((speed1 - speed) / atime, 0.0, maxaccel * crtr_fac)

        #print ("--state  h=%.0f[m]  v=%.1f[m/s]  cr=%.1f[m/s]  tr=%.1f[deg/s]  "
               #"a=%.2f[deg]  tht=%.2f[deg]  bnk=%.1f[deg]  n=% 6.2f"
               #% (alt, speed, dq.cr, degrees(dq.tr),
                  #degrees(dq.a), degrees(dq.tht), degrees(dq.bnk), dq.n))
        #print ("--targets  v1=%.1f[m/s]  cr1=%.1f[m/s]  tr1=%.1f[deg/s]"
               #% (speed1, climbrate1, degrees(turnrate1)))

        # Compute target path.
        adjextra = 0.0

        ppitch1 = asin(clamp(climbrate1 / speed1, -0.99, 0.99))
        lfac01v = maxlfac if ppitch1 > ppitch else minlfac
        rad01v = abs(speed**2 / ((lfac01v - 1) * w.absgravacc))
        dppitch = ppitch1 - ppitch
        if abs(dppitch) > 1e-6:
            etime = adt + adjextra
            rad01vb = abs(speed * etime / dppitch)
            rad01v = max(rad01v, rad01vb)

        etime = adt + adjextra
        if thead is not None:
            phead1 = thead
        else:
            phead1 = phead + turnrate1 * etime
        rad01t = abs(speed / turnrate1) if abs(turnrate1) > 1e-5 else 1e30
        lfac01t = (speed**2 / (rad01t * w.absgravacc))**2 + 1.0
        dphead = norm_ang_delta(phead, phead1)
        if abs(dphead) > 1e-6:
            rad01tb = abs(speed * etime / dphead)
            rad01t = max(rad01t, rad01tb)

        infrad = 1e6
        indpitch = (rad01v < infrad and abs(dppitch) > 1e-6)
        indhead = (rad01t < infrad and abs(dphead) > 1e-6)
        #print "--5", rad01v, degrees(dppitch), indpitch, rad01t, degrees(dphead), indhead
        if indpitch and indhead:
            dpheadv = (rad01v / rad01t) * (sin(ppitch1) - sin(ppitch))
            if abs(dpheadv) < abs(dphead):
                dphead = abs(dpheadv) * sign(dphead)
            path = ArcedHelixZ(rad01t, dphead, rad01v * sign(dppitch),
                               Vec3D(), vtod(vdir))
            #print "--6", rad01t, degrees(dphead), rad01v * sign(dppitch)
        elif indpitch:
            ndir = vdir.cross(zdir).cross(vdir) * sign(dppitch)
            path = Arc(rad01v, abs(dppitch),
                       Vec3D(), vtod(vdir), vtod(ndir))
            #print "--7", rad01v, degrees(dppitch), ndir
        elif indhead:
            path = HelixZ(rad01t, dphead, Vec3D(), vtod(vdir))
            #print "--8", rad01t, degrees(dphead)
        else:
            ndir = vdir.cross(zdir).cross(vdir)
            path = Segment(Vec3D(), vtod(vdir) * 1e5, vtod(ndir))
            #print "--9", ndir
        tpathtang = path.tangent(0.0)
        tpathnorm = path.normal(0.0)
        tpathrad = path.radius(0.0)

        # Input control.
        tmaxref = tmaxab if useab else tmax
        facedir = -1 if tinvert else 1
        ret = self.dyn.diff_to_path_tnr(dq, tpathtang, tpathnorm, tpathrad,
                                        speed1, accel1, tmaxref=tmaxref,
                                        nmininv=minlfac, facedir=facedir,
                                        bleedv=True, bleedr=True)
        da, dr, dtl, dbrd, fld, phit, invt = ret
        if da is None:
            da, dr, dtl, dbrd, fld = 0.0, 0.0, 0.0, 0.0, FLAPS.RETRACTED
        self._set_cntl_with_spdacc(da, dr, dtl, dbrd, fld, adt * 0.8)

        #print "========== ap-plane-nav-end"
        return adt


    def _act_input_form (self):

        if not self.dynstate or not self._act_leader.dynstate:
            return 0.0

        #print "========== ap-plane-form-start (world-time=%.2f)" % (w.time)

        w = self.world
        l = self._act_leader
        dq = self.dynstate
        dql = l.dynstate

        tformpos = self._act_formpos
        tinvert = self._act_invert
        useab = 1 if (l._act_useab and self.dyn.hasab) else 0

        mass = dq.m
        pos = dq.p
        alt = dq.h
        vdir = dq.xit
        speed = dq.v
        phead = dq.hdg
        ppitch = dq.tht
        climbrate = dq.cr
        maxg = dq.nmax
        ming = dq.nmin
        tmax = dq.tmax
        tmaxab = dq.tmaxab
        lpos = dql.p
        lvel = dql.u
        lvdir = dql.xit
        lspeed = dql.v
        zdir = Vec3D(0.0, 0.0, 1.0)

        # Update time.
        adtmin = 0.5
        adtmax = 2.0 + uniform(-0.4, 0.4)
        ldist = (lpos - pos).length()
        ldist1 = 500.0 #!!!
        adt = clamp(ldist / ldist1, adtmin, adtmax)
        adjextra = 0.0

        # Form-up direction.
        fpos = ptod(pos_from_horiz(l, tformpos))
        min_otr_alt = 50.0
        fpos[2] = max(fpos[2], w.elevation(fpos) + min_otr_alt)
        dfpos = fpos - pos
        fdist = dfpos.length()
        #lpos1 = lpos + lvel * adt + lacc * (0.5 * adt**2)
        #rlpos1 = l.node.getRelativePoint(l.node, vtof(lpos1 - lpos))
        #formpos1 = self._act_formpos + rlpos1
        #dfpos1 = ptod(pos_from_horiz(l, formpos1)) - pos
        #fdist1 = dfpos1.length()
        dfpos1 = dfpos
        fdist1 = fdist
        rtime = 4.0
        mdist = lspeed * rtime
        if fdist1 > mdist:
            tdir = unitv(dfpos1)
        else:
            tdir = unitv(dfpos1 + lvdir * (mdist - fdist1))

        # NOTE: Quantity set and ordering as returned by PlaneDynamics.comp_env.
        ret_mh = self.dyn.tab_all_mh[useab](mass, alt)
        (minspeed, maxspeed, amaxclimbrate, optspeedc,
         amaxturnratei, amaxturnrates, optspeedti, optspeedts,
         amaxrangefac, optspeedr, optthrottler) = ret_mh
        ret_mhv = self.dyn.tab_all_mhv[useab](mass, alt, speed)
        (maxclimbrate, maxturnratei, maxturnrates, maxrangefac,
         maxaccel, maxthrust, levelthrust, specfuelcons, iaspeed) = ret_mhv

        # Target speed.
        mang = radians(45.0)
        mfac, tpspeed, tpspeed2 = None, None, None
        if lvdir.dot(vdir) > cos(mang):
            pfdist = dfpos1.dot(vdir)
            mfac = 0.05 if pfdist > 0.0 else 0.20
            tpspeed = lvel.dot(vdir)
            tpspeed2 = tpspeed + mfac * pfdist
            if tpspeed2 > maxspeed and not useab and self.dyn.hasab:
                useab = 1
                ret_mh = self.dyn.tab_all_mh[useab](mass, alt)
                (minspeed, maxspeed, amaxclimbrate, optspeedc,
                 amaxturnratei, amaxturnrates, optspeedti, optspeedts,
                 amaxrangefac, optspeedr, optthrottler) = ret_mh
            speed1 = clamp(tpspeed2,
                              max(0.6 * tpspeed, minspeed),
                              min(1.4 * tpspeed, maxspeed))
            atime = 2.0 #!!!
            acc1 = (speed1 - speed) / atime
        else:
            if lspeed > maxspeed and self.dyn.hasab:
                useab = 1
                ret_mh = self.dyn.tab_all_mh[useab](mass, alt)
                (minspeed, maxspeed, amaxclimbrate, optspeedc,
                 amaxturnratei, amaxturnrates, optspeedti, optspeedts,
                 amaxrangefac, optspeedr, optthrottler) = ret_mh
            speed1 = clamp(lspeed, minspeed, maxspeed)
            atime = 2.0 #!!!
            acc1 = (speed1 - speed) / atime

        # Target climb rate.
        ppitch1 = atan2(tdir.getZ(), tdir.getXy().length())
        climbrate1 = speed1 * sin(ppitch1)

        # Target minimal load factor.
        if fdist1 < mdist:
            ming1 = -2.5
        else:
            ming1 = -1.0

        # Target turn rate.
        atime = adt
        thead = atan2(-tdir.getX(), tdir.getY())
        dphead = norm_ang_delta(phead, thead)
        maxlfac = maxg - 0.5
        minlfac = ming + 0.5
        limturnrate1 = w.absgravacc * (maxlfac**2 - 1.0)**0.5 / speed
        maxturnrate1 = min(maxturnratei, limturnrate1)
        turnrate1 = clamp(dphead / atime, -maxturnrate1, maxturnrate1)

        #print "--apl-form-10", fdist, tpspeed, mfac, tpspeed2, speed1

        # Correct targets for turn-climb coupling.
        ret = self.dyn.correct_turn_climb(climbrate1, turnrate1,
                                          maxclimbrate, maxturnrates)
        climbrate1, turnrate1 = ret

        # Input path.
        ppitch1 = asin(clamp(climbrate1 / speed1, -0.99, 0.99))
        lfac01v = maxlfac if ppitch1 > ppitch else minlfac
        rad01v = abs(speed**2 / ((lfac01v - 1) * w.absgravacc))
        dppitch = ppitch1 - ppitch
        if abs(dppitch) > 1e-6:
            atime = adt + adjextra
            rad01vb = abs(speed * atime / dppitch)
            rad01v = max(rad01v, rad01vb)

        phead1 = thead if thead is not None else phead
        rad01t = abs(speed / turnrate1) if abs(turnrate1) > 1e-5 else 1e30
        lfac01t = (speed**2 / (rad01t * w.absgravacc))**2 + 1.0
        dphead = norm_ang_delta(phead, phead1)
        if abs(dphead) > 1e-6:
            atime = adt + adjextra
            rad01tb = abs(speed * atime / dphead)
            rad01t = max(rad01t, rad01tb)

        infrad = 1e6
        indpitch = (rad01v < infrad and abs(dppitch) > 1e-6)
        indhead = (rad01t < infrad and abs(dphead) > 1e-6)
        #print "--5", rad01v, degrees(dppitch), indpitch, rad01t, degrees(dphead), indhead
        if indpitch and indhead:
            dpheadv = (rad01v / rad01t) * (sin(ppitch1) - sin(ppitch))
            if abs(dpheadv) < abs(dphead):
                dphead = abs(dpheadv) * sign(dphead)
            path = ArcedHelixZ(rad01t, dphead, rad01v * sign(dppitch),
                               Vec3D(), vtod(vdir))
            #print "--6", rad01t, degrees(dphead), rad01v * sign(dppitch)
        elif indpitch:
            ndir = vdir.cross(zdir).cross(vdir) * sign(dppitch)
            path = Arc(rad01v, abs(dppitch),
                       Vec3D(), vtod(vdir), vtod(ndir))
            #print "--7", rad01v, degrees(dppitch), ndir
        elif indhead:
            path = HelixZ(rad01t, dphead, Vec3D(), vtod(vdir))
            #print "--8", rad01t, degrees(dphead)
        else:
            ndir = vdir.cross(zdir).cross(vdir)
            path = Segment(Vec3D(), vtod(vdir) * 1e5, vtod(ndir))
            #print "--9", ndir
        tpathtang = path.tangent(0.0)
        tpathnorm = path.normal(0.0)
        tpathrad = path.radius(0.0)

        # Input control.
        tmaxref = tmaxab if useab else tmax
        facedir = -1 if tinvert else 1
        ret = self.dyn.diff_to_path_tnr(dq, tpathtang, tpathnorm, tpathrad,
                                        speed1, acc1, tmaxref=tmaxref,
                                        nmininv=minlfac, facedir=facedir,
                                        bleedv=True, bleedr=True)
        da, dr, dtl, dbrd, fld, phit, invt = ret
        if da is None:
            da, dr, dtl, dbrd, fld = 0.0, 0.0, 0.0, 0.0, FLAPS.RETRACTED
        self._set_cntl_with_spdacc(da, dr, dtl, dbrd, fld, adt * 0.5)

        #print ("--  name=%s  formdist=%.1f[m]" % (self.name, fdist))
        #print "========== ap-plane-form-end"
        return adt


    def _act_input_attack (self):

        if not self.dynstate:
            return 0.0

        w = self.world

        #print "========== ap-plane-attack-start (world-time=%.2f)" % (w.time)

        name = self.name
        dq = self.dynstate
        cq = self._act_state

        atime = w.time
        dt = w.dt

        t = self._act_target
        if hasattr(t, "dynstate"):
            if not t.dynstate:
                return 0.0
            tdq = t.dynstate
            tpos = tdq.p
            tvel = tdq.u
            tacc = tdq.b
            tant = tdq.ant
        else:
            tpos = ptod(t.pos())
            tvel = vtod(t.vel())
            tacc = vtod(t.acc())
            tant = Vec3D(0, 0, 1)
        tsize = t.size

        elev = w.elevation(dq.p)

        if self.cannons:
            refcannon = self.cannons[0]
        else:
            if self._dummy_cannon is None:
                self._dummy_cannon = Cannon(parent=self,
                                            mpos=Point3(), mhpr=Vec3(),
                                            mltpos=None, ammo=0)
            refcannon = self._dummy_cannon
        shdist = self._act_shootdist
        shldf = lambda: refcannon.launch_dynamics(dbl=True)
        freeab = self._act_useab
        skill = self.skill

        mon = False
        #mon = (self.name == "red1")
        #mon = (self.name == "blue1")
        atyp = 1
        if atyp == 1:
            ret = self.dyn.diff_to_path_gatk(cq, dq, atime, dt, elev,
                                             tpos, tvel, tacc, tsize,
                                             shdist, shldf, freeab,
                                             skill=skill, mon=mon)
            dtmu, inpfa, inpfr, inpftl, inpfbrd, sig, release = ret
        elif atyp == 2:
            ret = self.dyn.diff_to_path_gtrk(cq, dq, atime, dt, elev,
                                             tpos, tvel, tacc, tant, tsize,
                                             shdist, shldf, freeab,
                                             skill=skill, mon=mon)
            dtmu, inpfa, inpfr, inpftl, inpfbrd, sig, release = ret
        else:
            assert False

        fld = FLAPS.RETRACTED
        self.set_cntl(inpfa, inpfr, inpftl, inpfbrd, fld)

        if self.cannons:
            if self._wait_cannon_burst <= 0.0:
                if release:
                    #from src.core.cockpit import _gun_lead
                    #angh, angv = _gun_lead(w, self, self.cannons[0], t)
                    #print "--hud-gun-lead", degrees(angh), degrees(angv)
                    ftime = 0.0
                    for cannon in self.cannons:
                        ftime1 = cannon.fire(
                            rounds=-2, # -2 means nominal burst length
                            #target=t, # debug
                        )
                        ftime = max(ftime, ftime1)
                    self._wait_cannon_burst = ftime + self._cannon_burst_period
                    #self._wait_cannon_burst += 2.0 # debug
                    #print "--cannon-burst  from=%s(%s)  \n\n\n" % (self.name, self.species)
                else:
                    self._wait_cannon_burst = 0.0
            self._wait_cannon_burst -= dtmu

        if self._fudge_missile_attack:
            if len(self._act_matk_enroute.get(t, [])) < 1:
                pos = dq.p
                dtpos = tpos - pos
                tdist = dtpos.length()
                mindist = 1.0 * shdist
                sel_launcher = None
                if tdist > mindist and not release:
                    cap_launchers = []
                    for launcher in self.launchers:
                        if launcher.rounds > 0:
                            wp = launcher.mtype
                            if issubclass(wp, Rocket) and t.family in wp.against:
                                ret = wp.launch_limits(self, t)
                                rmin, rman, rmax = ret[:3]
                                if rmin < tdist < rman:
                                    cap_launchers.append(launcher)
                    if cap_launchers:
                        cap_launchers.sort(key=lambda l: l.mtype.maxg)
                        sel_launcher = cap_launchers[-1]
                    if sel_launcher:
                        lmls = sel_launcher.fire(target=t)
                        if lmls:
                            emls = self._act_matk_enroute.get(t)
                            if emls is None:
                                emls = []
                                self._act_matk_enroute[t] = emls
                            emls.extend(lmls)
                if self._act_matk_prev_launcher is not sel_launcher:
                    if self._act_matk_prev_launcher:
                        self._act_matk_prev_launcher.ready(target=None)
                    self._act_matk_prev_launcher = sel_launcher

        #print "========== ap-plane-attack-end"
        return dtmu


    def _act_input_mslevade (self):

        if not self.dynstate:
            return 0.0

        w = self.world

        #print "========== ap-plane-mslevade-start (world-time=%.2f)" % (w.time)

        name = self.name
        dq = self.dynstate
        cq = self._act_state

        atime = w.time
        dt = w.dt

        m = self._attacking_missile
        mpos = vtod(m.pos())
        mvel = vtod(m.vel())
        macc = vtod(m.acc())

        elev = w.elevation(dq.p)

        freeab = True
        skill = self.skill

        mon = False
        #mon = (self.name == "red1")
        #mon = (self.name == "blue1")
        ret = self.dyn.diff_to_path_mevd(cq, dq, atime, dt, elev,
                                         mpos, mvel, macc, freeab,
                                         skill=skill, mon=mon)
        dtmu, inpfa, inpfr, inpftl, inpfbrd = ret

        fld = FLAPS.RETRACTED
        self.set_cntl(inpfa, inpfr, inpftl, inpfbrd, fld)

        return dtmu


    def _init_shotdown_1 (self, obody, chbx, cpos):

        self._wait_eject_trigger = None
        if not self.ejection:
            if self.must_eject_time:
                if self.must_eject_time > 0.0:
                    self._wait_eject_trigger = float(self.must_eject_time)
            else:
                d100 = randrange(100)
                if d100 < 80:
                    self._wait_eject_trigger = uniform(2.0, 4.0)

        rollrate = self.rollrate()
        self._act_rollrate_sign = sign(rollrate) or choice([-1, 1])
        self._act_max_rollrate = clamp(1.2 * abs(rollrate), radians(30.0), radians(180.0))
        self._act_rollrate_acc = radians(5.0)
        self._act_absrollrate = abs(rollrate)

        self._act_active = True
        self._act_pause = 0.0

        return self._act_input_shotdown_1


    def _act_input_shotdown_1 (self):

        #print "===== ap-plane-shotdown-1-start (world-time=%.2f)" % (w.time)

        ret = self._act_input_roll_fall()

        #print "===== ap-plane-shotdown-1-end"
        return ret


    def _act_input_roll_fall (self):

        w = self.world
        dq = self.dynstate
        cq = self._act_state

        if self.helix_dummy is not None:
            dq.cr = -100.0

        else:
            aoa = dq.a
            maxpitchrate = dq.pomax
            zlaoa = dq.a0
            nnlaoa = dq.a1m
            taoa = 0.5 * (zlaoa + nnlaoa)
            daoa = taoa - aoa
            daoa *= w.dt / 1.0

            if self._act_absrollrate < self._act_max_rollrate:
                self._act_absrollrate += self._act_rollrate_acc * w.dt
            droll = self._act_absrollrate * self._act_rollrate_sign * w.dt

            throttle = dq.tl
            dthrottle = -throttle

            airbrake = dq.brd
            dairbrake = -airbrake

            flaps = FLAPS.RETRACTED
            landgear = False

            self.set_cntl(daoa=daoa, droll=droll, dthrottle=dthrottle,
                          dairbrake=dairbrake, flaps=flaps,
                          landgear=landgear)

        if self._wait_eject_trigger is not None:
            self._wait_eject_trigger -= w.dt
            if self._wait_eject_trigger <= 0.0:
                self.eject()

        pause = 0.0
        return pause


    def jump_to (self, pos=None, hpr=None, speed=None, onground=False):

        Body.jump_to(self, pos, hpr, speed)

        self.dynstate = AutoProps()
        dq = self.dynstate
        vel = self.vel()
        if onground:
            hg, ng, tg = self._ground_data()
        else:
            hg, ng, tg = None, None, None
        self.dyn.resolve_stat(dq, self.mass, ptod(pos), vtod(vel),
                              hg, ng, tg)
        self.dyn.update_fstep(dq, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                              hg, ng, tg,
                              extraq=True)
        set_hpr_vfu(self.node, vtof(dq.at), vtof(dq.an))
        self.onground = dq.gc
        if self.onground:
            self._landgear = True

        # Needed in base class.
        self._vel = vtof(dq.u)
        self._acc = vtof(dq.b)
        self._angvel = vtof(dq.o)
        self._angacc = vtof(dq.s)
        self._prev_vel = Vec3(self._vel)

        self.set_cntl()
        self.set_act(speed=dq.v, climbrate=dq.cr, useab=(dq.tl > 1.0))


    def add_fuel (self, dfuel, minfuel=None, maxfuel=None):

        if minfuel is None:
            minfuel = 0.0
        if maxfuel is None:
            maxfuel = self.maxfuel
            for tanker in self.tankers:
                maxfuel += tanker.maxfuel

        if dfuel > maxfuel - self.fuel:
            dfuel1 = maxfuel - self.fuel
            if dfuel1 < 0.0:
                dfuel1 = 0.0
        elif dfuel < minfuel - self.fuel:
            dfuel1 = minfuel - self.fuel
            if dfuel1 > 0.0:
                dfuel1 = 0.0
        else:
            dfuel1 = dfuel

        # Add first to internal tanks, take first from drop tanks.
        if dfuel1 > 0.0:
            dintfuel1 = min(dfuel1, self.maxfuel - self.fuel)
            self.fuel += dintfuel1
            self.mass += dintfuel1
            self._update_tankers(dfuel1 - dintfuel1)
        else:
            dintfuel1 = self._update_tankers(dfuel1)
            self.fuel += dintfuel1
            self.mass += dintfuel1
        self.fuelfill = self.fuel / self.maxfuel

        return dfuel1


    def add_fuelfill (self, dfuelfill, minfuelfill=None, maxfuelfill=None):

        if minfuelfill is None:
            minfuelfill = 0.0
        if maxfuelfill is None:
            maxfuelfill = 1.0
            for tanker in self.tankers:
                maxfuelfill += tanker.maxfuel / self.maxfuel

        dfuel = dfuelfill * self.maxfuel
        minfuel = minfuelfill * self.maxfuel
        maxfuel = maxfuelfill * self.maxfuel
        dfuel1 = self.add_fuel(dfuel, minfuel, maxfuel)
        dfuelfill1 = dfuel1 / self.maxfuel

        return dfuelfill1


    def set_min_fuel (self, minfuel):

        if minfuel > self.fuel:
            dfuel = self.add_fuel(minfuel - self.fuel)
        else:
            dfuel = 0.0
        return dfuel


    def set_min_fuelfill (self, minfuelfill):

        minfuel = minfuelfill * self.maxfuel
        dfuel = self.set_min_fuel(minfuel)
        dfuelfill = dfuel / self.maxfuel
        return dfuelfill


    def _update_tankers (self, dfuel):

        # Add to innermost first, take from outermost first.
        tankers = self.tankers if dfuel > 0.0 else reversed(self.tankers)
        for tanker in tankers:
            dfuel = tanker.add_fuel(dfuel)
        return dfuel


    def subs_fuel_optcruise (self, gpos1, gpos2, minfuel=None):

        dist = great_circle_dist(self.world.georad, gpos1, gpos2)
        maxrange = self.dyn.rmax
        dfuel = -(self.maxfuel * (dist / maxrange))
        dfuel1 = self.add_fuel(dfuel, minfuel)
        return dfuel1


    def get_time_optcruise (self, gpos1, gpos2):

        dist = great_circle_dist(self.world.georad, gpos1, gpos2)
        mass = self.mass
        alt = self.dyn.hrmax
        optspeedr = self.dyn.tab_voptrf[0](mass, alt)
        ctime = dist / optspeedr
        return ctime


    def _update_vortices (self, dt):

        if not self._vortices:
            return
        refvortex = self._vortices[0]

        active = False
        cvdist = self.world.camera.getDistance(self.node)
        if cvdist < (refvortex.loddistout or 1e10):
            alt = self.dynstate.h
            if alt < self._vortices_max_alt:
                min_lfac = self._vortices_min_lfac
                lfac = self.dynstate.n
                if lfac > min_lfac:
                    max_lfac = self._vortices_max_lfac
                    aint = intl10r(alt, 0.0, self._vortices_max_alt)
                    lint = intl01r(lfac, min_lfac, max_lfac)
                    radfac = aint * lint**0.5
                    lenfac = aint * lint
                    for vortex in self._vortices:
                        vortex.radius0 = vortex.init_radius0 * radfac
                        vortex.radius1 = vortex.init_radius1 * radfac
                        vortex.lifespan = vortex.init_lifespan * lenfac
                    active = True

        if self._vortices_active != active:
            self._vortices_active = active
            for vortex in self._vortices:
                vortex.set_active(active)


    def fire_decoy (self):

        i = self._decoy_next_launch_index
        self._decoy_next_launch_index += 1
        if self.flarechaff > 0:
            pos = self._decoy_launch_pos[i % len(self._decoy_launch_pos)]
            vel = self._decoy_launch_vel[i % len(self._decoy_launch_vel)]
            for k in xrange(max(len(pos), len(vel))):
                decoy = FlareChaff(world=self.world,
                                   pos=pos[k % len(pos)], vel=vel[k % len(vel)],
                                   refbody=self, vistype=self.flchvistype)
                self.decoys.append(decoy)
                self.flarechaff -= 1
            #snd = Sound3D(path="audio/sounds/flarechaff.ogg",
                          #parent=self, volume=1.0, fadetime=0.1)
            #snd.play()
        rlp = self._decoy_launch_freq[i % len(self._decoy_launch_freq)]
        wait_next = self._decoy_missile_dist_time * rlp
        return wait_next


    def _ground_data (self):

        hg, ng, tg = self.world.elevation(self.pos(), wnorm=True, wtype=True,
                                          flush=True)
        ng = vtod(ng)
        return hg, ng, tg


    def _get_sweep_angle (self, speed, alt):

        if self._varsweep_force_relang is not None:
            relang = clamp(self._varsweep_force_relang, 0.0, 1.0)
        else:
            snd_speed = self.dyn.resatm(alt)[5]
            mach = speed / snd_speed
            min_mach, max_mach = self.varsweepmach
            relang = intl01r(mach, min_mach, max_mach)
        min_ang, max_ang = self.varsweeprange
        ang = intl01v(relang, min_ang, max_ang)
        return ang


    def _set_sweep_pivot (self, ang):

        if self.varsweepmodelmin:
            min_ang = self.varsweeprange[0]
            piv_ang = min_ang - ang
        else:
            max_ang = self.varsweeprange[1]
            piv_ang = max_ang - ang
        for piv_node in self._varsweep_arm_lefts:
            piv_node.setH(degrees(piv_ang))
        for piv_node in self._varsweep_arm_rights:
            piv_node.setH(degrees(piv_ang))

        if self.varsweephitbox:
            lname, rname = self.varsweephitbox
            lhbx = self.hitboxmap[lname]
            rhbx = self.hitboxmap[rname]
            lhbx.center = lhbx.cnode.getPos(self.node)
            rhbx.center = rhbx.cnode.getPos(self.node)


    def set_sweep (self, relang=None, jump=False):

        self._varsweep_force_relang = relang
        self._varsweep_force_jump = jump


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
        pd = self.dyn
        dq = self.dynstate

        useab = 1 if dq.tl > 1.0 else 0
        ret_mh = pd.tab_all_mh[useab](dq.m, dq.h)
        (vmin, vmax, crmax, voptc, trimax, trsmax, voptti, voptts,
         rfmax, voptrf, tloptrf) = ret_mh
        ret_mhv = pd.tab_all_mhv[useab](dq.m, dq.h, dq.v)
        (crmaxv, trimaxv, trsmaxv, rfmaxv, ctmaxv, tlvlv, tmaxv, sfcv,
         vias) = ret_mhv

        ls = []
        ls.append("name: %s" % self.name)
        #ls.append("world-time: %.0f (%.0f) [s]"
                  #% (self.world.time, self.world.wall_time))
        #ls.append("frame-duration: %.1f [msec]" % (self.world.dt * 1000))
        ls.append("position: (%.1f, %.1f, %.1f) [m]" % tuple(dq.p))
        hagl = self.world.otr_altitude(dq.p)
        ls.append("altitude: % .1f (% .1f) [m]" % (dq.h, hagl))
        ls.append("heading: %.1f [deg]" % to_navhead(d(dq.hdg)))
        ls.append("mass: %.0f (%.0f/%.0f) [kg]" % (dq.m, pd.mmin, pd.mmax))
        fuelcons = -dq.sfc * dq.t
        ls.append("fuel: %.0f (% .2f/s) [kg]" % (self.fuel, fuelcons))
        ls.append("speed: %.1f (%.1f/%.1f/%.1f/%.1f/%.1f) [m/s]" %
                  (dq.v, vmin, voptts, voptti, voptc, vmax))
        ls.append("climb-rate: % .1f (%.1f/%.1f) [m/s]" %
                  (dq.cr, crmaxv, crmax))
        ls.append("turn-rate: % .1f (%.1f/%.1f/%.1f/%.1f) [deg/s]" %
                  (d(dq.tr), d(trimaxv), d(trsmaxv), d(trimax), d(trsmax)))
        ls.append("throttle: %.3f" % (dq.tl))
        #ls.append("acceleration: % .1f [m/s^2]" % dq.c.length())
        ls.append("path-acceleration: %.1f [m/s^2]" % (dq.ct))
        ls.append("angle-of-attack: % .1f (%.1f/%.1f) [deg]" %
                  (d(dq.a), d(dq.amin), d(dq.amax)))
        ls.append("load-factor: % .1f" % dq.n)
        ls.append("path-pitch: % .1f [deg]" % d(dq.tht))
        #ls.append("pitch-rate: % .1f [deg/s]" % d(dq.???))
        ls.append("bank: % .1f [deg]" % d(dq.bnk))
        #ls.append("bank-rate: % .1f [deg/s]" % d(dq.???))
        text = "\n".join(ls)

        update_text(self._state_info_text, text=text)


    def eject (self):

        if self.ejection_triggered:
            return
        can_eject = ((self.fmodelpath and self.sdmodelpath) and
                     self.must_eject_time >= 0.0)
        if not can_eject:
            return
        self.ejection_triggered = True

        self.controlout = True

        self.target = None

        if self.cockpit_engine_sound is not None:
            self.cockpit_engine_sound.stop()

        # Switch to shotdown model, to get access to ejection nodes,
        # but restore non-shotdown textures.
        # NOTE: To avoid conflict with a possible subsequent shootdown
        # in collide method, mask the existence of the shotdown model.
        if self._shotdown_modelnode is not None:
            self.modelnode.removeNode()
            self.modelnode = self._shotdown_modelnode
            self.modelnode.reparentTo(self.node)
            self.models = self._shotdown_models
            self.fardists = self._shotdown_fardists
            self._shotdown_modelnode = None
            if self._shotdown_change_maps:
                glowmap = self.glowmap if not isinstance(self.glowmap, Vec4) else None
                for model in self.models:
                    set_texture(model,
                                texture=self.texture,
                                normalmap=self.normalmap,
                                glowmap=glowmap,
                                glossmap=self.glossmap,
                                shadowmap=self.world.shadow_texture)

        # Set up falling autopilot.
        ap = self._init_powercrash_1()
        self._act_input_controlout = ap


    def _init_powercrash_1 (self):

        rollrate = self.rollrate()
        self._act_rollrate_sign = sign(rollrate) or choice([-1, 1])
        self._act_max_rollrate = clamp(1.2 * abs(rollrate), radians(10.0), radians(90.0))
        self._act_rollrate_acc = radians(2.0)
        self._act_absrollrate = abs(rollrate)

        self._act_active = True
        self._act_pause = 0.0

        self._wait_eject_trigger = None

        return self._act_input_powercrash_1


    def _act_input_powercrash_1 (self):

        ret = self._act_input_roll_fall()

        return ret


class Ejection (object):

    def __init__ (self, plane, wrefbody=False):

        self.world = plane.world
        self._plane = plane

        for model in plane.models:
            nd = model.find("**/eject_sys")
            if not nd.isEmpty():
                nd.removeNode()

        self.node = self.world.node.attachNewNode("ejection")
        self.node.setPos(plane.pos())
        shader = make_shader(ambln=self.world.shdinp.ambln,
                             dirlns=self.world.shdinp.dirlns)
        self.node.setShader(shader)

        fmodel = load_model(plane.fmodelpath)

        self._eject_specs = []
        i = 0
        while True:
            ext = ("_%d" % (i + 1)) if i > 0 else ""

            for ib, cbase in enumerate(["canopy_frame"]):
                cnd = fmodel.find("**/%s" % (cbase + ext))
                if not cnd.isEmpty():
                    pos = cnd.getPos(fmodel)
                    cnd.setPos(pos)
                    hpr = cnd.getHpr(fmodel)
                    cnd.setHpr(hpr)
                    cnd.reparentTo(plane.node)
                    cnd.setShader(shader)
                    set_texture(cnd, texture=plane.texture)
                    for gbase in ["canopy_glass"]:
                        gnd = cnd.find("**/%s" % (gbase + ext))
                        if not gnd.isEmpty():
                            gnd.setTransparency(TransparencyAttrib.MAlpha)
                    if plane.ejectdata:
                        cwait = plane.ejectdata[i][0]
                    else:
                        cwait = 0.50
                    es = SimpleProps(name="cover%s" % (i + 1), typ="cover",
                                     node=cnd, wait=cwait, loop=self._loop_cover,
                                     mass=30.0, sdrag=0.5, upspeed=5.0,
                                     rotspeed=radians(360),
                                     lifetime=5.0, fadetime=1.0)
                    if ib > 0:
                        es.wait = 0.0
                    self._eject_specs.append(es)

            snd = fmodel.find("**/%s" % ("pilot_seat" + ext))
            if not snd.isEmpty():
                pos = snd.getPos(fmodel)
                snd.setPos(pos)
                hpr = snd.getHpr(fmodel)
                snd.setHpr(hpr)
                snd.reparentTo(plane.node)
                snd.setShader(shader)
                set_texture(snd, texture=plane.texture)
                pnd = snd.find("**/%s" % ("pilot" + ext))
                if not pnd.isEmpty():
                    set_texture(pnd, texture="models/aircraft/pilots/pilot_tex.png")
                if plane.ejectdata:
                    pwait, pbank = plane.ejectdata[i][1:3]
                else:
                    pwait, pbank = 0.20, 0.0
                es = SimpleProps(name="pilot%s" % (i + 1), typ="pilot",
                                 node=snd, wait=pwait, loop=self._loop_pilot,
                                 mass=uniform(140.0, 160.0), sdrag=0.5,
                                 upspeed=15.0, upbank=pbank,
                                 boostacc=(2.0 * self.world.absgravacc),
                                 boosttime=1.5, righttime=1.5,
                                 unfurltime=2.0,
                                 pilotmass=uniform(70.0, 90.0), cansdrag=25.0,
                                 canhorspeed=uniform(1.0, 2.0),
                                 canturnrate=radians(uniform(20.0, 30.0)),
                                 lifetime=30.0, fadetime=2.0)
                self._eject_specs.append(es)
            else:
                break

            i += 1

        self._num_waiting = len(self._eject_specs)
        self._num_flying = 0
        self._wait_next_eject = 0.0

        self._want_ref_body = wrefbody
        self._ref_body = None

        self.alive = True
        base.taskMgr.add(self._loop, "ejection-loop")
        #self.world.time_factor = 0.1


    def destroy (self):

        if not self.alive:
            return
        if self._ref_body is not None:
            self._ref_body.destroy()
        self.node.removeNode()
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done

        if not self._plane.alive:
            self._num_waiting = 0
        if self._num_waiting == 0 and self._num_flying == 0:
            self.destroy()
            return task.done

        if self._num_waiting > 0:
            dt = self.world.dt
            self._wait_next_eject -= dt
            if self._wait_next_eject <= 0.0:
                es = self._eject_specs.pop(0)
                task = base.taskMgr.add(es.loop, "ejection-%s-loop" % es.name)
                task.spec = es
                task.stage = 0
                task.wtime = 0.0
                task.rbody = None
                self._num_waiting -= 1
                if self._num_waiting > 0:
                    es = self._eject_specs[0]
                    self._wait_next_eject += es.wait

        return task.cont


    def _loop_cover (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        cs = task.spec

        moved = False

        if task.stage == 0:
            self._num_flying += 1
            cs.node.wrtReparentTo(self.node)
            cs.node.setTwoSided(True)
            cs.pos = cs.node.getPos()
            udir = self._plane.quat().getUp()
            cs.vel = self._plane.vel() + udir * cs.upspeed
            cs.rho = self.world.airdens(cs.node.getPos(self.world.node)[2])
            cs.transp = False

            cs.smoketime = 0.10
            pos = cs.node.getPos(self._plane.node)
            pos[2] -= 0.0
            task.smoke = PolyExhaust(
                parent=self._plane, pos=pos,
                radius0=1.5, radius1=3.0,
                length=(cs.smoketime * 1.0),
                speed=(cs.smoketime * 2.0), poolsize=6,
                color=rgba(255, 255, 255, 1.0),
                colorend=rgba(128, 128, 128, 1.0),
                tcol=0.6,
                # subnode=None,
                pdir=Vec3(0,0,1),
                emradius=0.6,
                texture="images/particles/smoke6-1.png",
                glowmap=rgba(0, 0, 0, 0.1),
                ltoff=False,
                frameskip=2,
                dbin=0,
                freezedist=800.0,
                hidedist=1000.0,
                loddirang=10,
                loddirskip=4)

            task.stage = 1

        if task.stage == 1 and not moved:
            moved = True

            gacc = self.world.gravacc
            vdir = unitv(cs.vel)
            speed = cs.vel.length()
            dacc = vdir * (-0.5 * cs.rho * speed**2 * cs.sdrag / cs.mass)
            dspeed_d = (dacc * dt).length()
            max_dspeed_d = 0.5 * speed
            if dspeed_d > max_dspeed_d:
                dacc *= max_dspeed_d / dspeed_d
            cs.vel += (gacc + dacc) * dt
            cs.pos += cs.vel * dt
            cs.node.setPos(cs.pos)

            ifac = task.wtime / cs.lifetime
            rotspeed = cs.rotspeed * (1.0 - ifac)
            dang = rotspeed * dt
            quat = cs.node.getQuat()
            fdir = quat.getForward()
            udir = quat.getUp()
            rdir = quat.getRight()
            adir = unitv(rdir + udir * (0.1 * dt))
            rot = Quat()
            rot.setFromAxisAngleRad(dang, adir)
            fdir = unitv(Vec3(rot.xform(fdir)))
            set_hpr_vfu(cs.node, fdir, udir)

            if task.wtime >= cs.lifetime - cs.fadetime:
                if not cs.transp:
                    cs.node.setTransparency(TransparencyAttrib.MAlpha)
                    cs.transp = True
                alpha = (cs.lifetime - task.wtime) / cs.fadetime
                cs.node.setSa(alpha)

            if task.wtime >= cs.lifetime:
                task.stage = 2

        if task.stage == 2:
            cs.node.removeNode()
            self._num_flying -= 1
            return task.done

        if task.smoke is not None and task.wtime >= cs.smoketime:
            task.smoke.end()
            task.smoke = None

        task.wtime += dt

        return task.cont


    def _loop_pilot (self, task):

        if not self.alive:
            return task.done

        dt = self.world.dt
        ps = task.spec

        moved = False

        zdir = Vec3(0.0, 0.0, 1.0)

        if task.stage == 0:
            moved = True

            self._num_flying += 1
            ps.node.wrtReparentTo(self.node)
            ps.pos = ps.node.getPos()
            quat = self._plane.quat()
            fdir0 = quat.getForward()
            udir0 = quat.getUp()
            rdir0 = quat.getRight()
            rang = radians(-10.0)
            bang = ps.upbank
            rot = Quat()
            rot.setFromAxisAngleRad(rang, rdir0)
            udir = unitv(Vec3(rot.xform(udir0)))
            rot.setFromAxisAngleRad(bang, fdir0)
            udir = unitv(Vec3(rot.xform(udir)))
            ps.vel = self._plane.vel() + udir * ps.upspeed
            ps.rightdir = unitv(udir.cross(zdir))
            ps.rightang = acos(udir.dot(zdir))
            self._sum_rightang = 0.0
            ps.rightspeed = ps.rightang / ps.righttime
            ps.transp = False

            task.exhaust = PolyExhaust(
                parent=self, subnode=ps.node,
                pos=Point3(0.0, 0.0, -0.5),
                pdir=Vec3(0.0, 0.0, -1.0),
                radius0=0.15, radius1=0.40, length=3.0,
                speed=20.0, poolsize=16,
                color=rgba(240, 188, 102, 0.5),
                colorend=rgba(113, 101, 154, 0.6),
                tcol=0.6,
                ltoff=True,
                texture="images/particles/exhaust03.png",
                glowmap=rgba(255, 255, 255, 1.0),
                freezedist=100.0, hidedist=1000.0,
                frameskip=pycv(py=2, c=1),
                loddirang=15, loddirskip=2)

            ps.firetime = 0.20
            pos = ps.node.getPos(self._plane.node)
            pos[2] -= 0.0
            task.fire = PolyExhaust(
                parent=self._plane, pos=pos,
                radius0=0.8, radius1=1.6,
                length=(ps.firetime * 1.0),
                speed=(ps.firetime * 3.0), poolsize=8,
                color=rgba(255, 255, 255, 1.0),
                colorend=rgba(246, 222, 183, 1.0),
                tcol=0.5,
                pdir=Vec3(0,0,1),
                emradius=0.5,
                texture="images/particles/explosion6-1.png",
                glowmap=rgba(255, 255, 255, 1.0),
                ltoff=True,
                frameskip=2,
                dbin=0,
                freezedist=800.0,
                hidedist=1000.0,
                loddirang=10,
                loddirskip=4)

            if self._want_ref_body and self._ref_body is None:
                # Create dummy ejection body.
                rbody = Body(world=self.world,
                             family="effect", species="ejection",
                             name=("%s-eject-ref" % self._plane.name),
                             side=self._plane.side,
                             hitforce=0.0,
                             hitinto=False, hitfrom=False)
                self._ref_body = rbody
                task.rbody = rbody

            assert ps.righttime <= ps.boosttime

            task.stage = 1
            #print "--eject-pilot  stage=%d" % task.stage

            if 0:
                g = self.world.absgravacc
                v0 = ps.upspeed
                ab = ps.boostacc
                tb = ps.boosttime
                tzz = (v0 + ab * tb) / g
                hzz = v0 * tzz - 0.5 * g * tzz**2 + ab * tb * (tzz - 0.5 * tb)
                dgbval(1, "ejection-deriv-zero-zero",
                       ("%s(%s)" % (self._plane.name, self._plane.species), "%s", "from"),
                       (hzz, "%.1f", "height", "m"),
                       (tzz, "%.2f", "time", "s"))

        if task.stage == 1 and not moved:
            moved = True

            gacc = self.world.gravacc
            vdir = unitv(ps.vel)
            speed = ps.vel.length()
            rho = self.world.airdens(ps.node.getPos(self.world.node)[2])
            dacc = vdir * (-0.5 * rho * speed**2 * ps.sdrag / ps.mass)
            dspeed_d = (dacc * dt).length()
            max_dspeed_d = 0.5 * speed
            if dspeed_d > max_dspeed_d:
                dacc *= max_dspeed_d / dspeed_d
            if task.wtime <= ps.boosttime:
                bacc = zdir * ps.boostacc
            else:
                bacc = Vec3()
            ps.vel += (gacc + dacc + bacc) * dt
            ps.pos += ps.vel * dt
            ps.node.setPos(ps.pos)

            if task.wtime <= ps.righttime:
                dang = ps.rightspeed * dt
                rot = Quat()
                rot.setFromAxisAngleRad(dang, ps.rightdir)
                quat = ps.node.getQuat()
                fdir = quat.getForward()
                udir = quat.getUp()
                fdir = unitv(Vec3(rot.xform(fdir)))
                udir = unitv(Vec3(rot.xform(udir)))
                set_hpr_vfu(ps.node, fdir, udir)

            if task.wtime >= ps.boosttime * 1.1:
                task.stage = 2
                ps.unfurled = False
                #print "--eject-pilot  stage=%d" % task.stage

        if task.stage == 2 and not moved:
            moved = True

            if not ps.unfurled:
                ps.unfurled = True
                quat = ps.node.getQuat()
                rdir = quat.getRight()
                ps.node.removeNode()
                ps.node = load_model(
                    path="models/aircraft/pilots/pilot_parachute.egg",
                    texture="models/aircraft/pilots/pilot_tex.png")
                ps.node.reparentTo(self.node)
                bmin, bmax = ps.node.getTightBounds()
                cablen = abs(bmin[2])
                vdir = unitv(ps.vel)
                pos = ps.pos - vdir * cablen
                udir = -vdir
                fdir = unitv(udir.cross(rdir))
                set_hpr_vfu(ps.node, fdir, udir)
                ps.unfhorspeed = (ps.vel - zdir * ps.vel.dot(zdir)).length()
                ps.unfudir = udir
                ps.unfrdir = rdir
                ps.wtime0 = task.wtime

            gacc = self.world.gravacc
            vdir = unitv(ps.vel)
            speed = ps.vel.length()
            rho = self.world.airdens(ps.node.getPos(self.world.node)[2])
            tfac = intl01r(task.wtime - ps.wtime0, 0.0, ps.unfurltime)
            sdrag = ps.cansdrag * tfac**2
            dacc = vdir * (-0.5 * rho * speed**2 * sdrag / ps.pilotmass)
            dspeed_d = (dacc * dt).length()
            max_dspeed_d = 0.5 * speed
            if dspeed_d > max_dspeed_d:
                dacc *= max_dspeed_d / dspeed_d
            ps.vel += (gacc + dacc) * dt
            ps.pos += ps.vel * dt
            ps.node.setPos(ps.pos)

            speed = ps.vel.length()
            quat = ps.node.getQuat()
            rdir = quat.getRight()
            horspeed = (ps.vel - zdir * ps.vel.dot(zdir)).length()
            ifac = intl01r(horspeed, ps.canhorspeed, ps.unfhorspeed)
            udir = unitv(intl01v(ifac**0.5, zdir, ps.unfudir))
            fdir = unitv(udir.cross(ps.unfrdir))
            set_hpr_vfu(ps.node, fdir, udir)

            if horspeed <= ps.canhorspeed:
                task.stage = 3
                ps.seatoff = False
                #print "--eject-pilot  stage=%d" % task.stage

        if task.stage == 3 and not moved:
            moved = True

            if not ps.seatoff:
                ps.turndir = choice([-1, 1])
                ps.seatoff = True

            gacc = self.world.gravacc
            vdir = Vec3(0.0, 0.0, -1.0)
            speed = ps.vel.length()
            rho = self.world.airdens(ps.node.getPos(self.world.node)[2])
            dacc = vdir * (-0.5 * rho * speed**2 * ps.cansdrag / ps.pilotmass)
            ps.vel += (gacc + dacc) * dt
            ps.pos += ps.vel * dt
            ps.node.setPos(ps.pos)

            quat = ps.node.getQuat()
            udir = quat.getUp()
            fdir = quat.getForward()
            dang = ps.turndir * ps.canturnrate * dt
            rot = Quat()
            rot.setFromAxisAngleRad(dang, udir)
            ps.vel = Vec3(rot.xform(ps.vel))
            fdir = unitv(Vec3(rot.xform(fdir)))
            udir = unitv(Vec3(rot.xform(udir)))
            set_hpr_vfu(ps.node, fdir, udir)

            if task.wtime >= ps.lifetime - ps.fadetime:
                if not ps.transp:
                    ps.node.setTransparency(TransparencyAttrib.MAlpha)
                    ps.transp = True
                alpha = (ps.lifetime - task.wtime) / ps.fadetime
                ps.node.setSa(alpha)

            if task.wtime >= ps.lifetime:
                task.stage = 4
                #print "--eject-pilot  stage=%d" % task.stage

        if task.stage == 4:
            ps.node.removeNode()
            self._num_flying -= 1
            if task.rbody is not None:
                task.rbody.destroy()
            return task.done

        if task.fire is not None and task.wtime >= ps.firetime:
            task.fire.end()
            task.fire = None

        if task.exhaust is not None and task.wtime >= ps.boosttime:
            task.exhaust.end()
            task.exhaust = None

        if task.rbody is not None and task.rbody.alive and not ps.node.isEmpty():
            task.rbody.node.setPos(ps.node.getPos(self.world.node))
            task.rbody.node.setQuat(ps.node.getQuat(self.world.node))

        task.wtime += dt

        #speed = ps.vel.length()
        #horspeed = (ps.vel - zdir * ps.vel.dot(zdir)).length()
        #print "--eject-pilot  speed=%.1f[m/s]  horspeed=%.1f[m/s]" % (speed, horspeed)

        return task.cont


    def ref_body (self):

        return self._ref_body


