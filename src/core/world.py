# -*- coding: UTF-8 -*-

from bisect import bisect
from math import radians, sqrt, tan, acos, atan, exp, log

from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import NodePath
from pandac.PandaModules import CullBinManager, ClockObject
from pandac.PandaModules import CollisionTraverser, CollisionHandlerQueue
from pandac.PandaModules import CollisionNode, CollisionSphere
from pandac.PandaModules import AmbientLight, DirectionalLight, PointLight
from pandac.PandaModules import Vec3, Vec4, Point2, Point3

from src import MAX_DT, ANIMATION_FOV
from src.core.body import Body
from src.core.dialog import Dialog
from src.core.interface import PauseMenu, ControlsMenu
from src.core.interface import ShotdownInseqMenu, ShotdownNoseqMenu
from src.core.misc import rgba, SimpleProps, as_sequence
from src.core.misc import make_text, update_text, make_image
from src.core.misc import node_fade_to, node_slide_to
from src.core.misc import map_pos_to_screen, kill_tasks
from src.core.misc import explosion_dropoff, explosion_reach
from src.core.misc import reset_random
from src.core.misc import fx_reset_random
from src.core.misc import report, dbgval
from src.core.sound import Sound3D
from src.core.transl import *


class World (object):

    _count = 0

    def __init__ (self, game=None, mission=None,
                  fixdt=None, randseed=None):

        if World._count > 0:
            raise StandardError("Only one world at a time can be created.")
        World._count += 1

        # Initialize random generators for action and effects.
        if randseed is None:
            randseed = base.randseed
        if randseed is None:
            randseed = (-1, -1)
        if isinstance(randseed, tuple):
            rsd, fxrsd = randseed
        else:
            rsd = randseed
            fxrsd = randseed * 11
        reset_random(rsd)
        fx_reset_random(fxrsd)

        self.parent = None

        self.name = "world"

        self.game = game
        self.mission = mission

        self.sky = None
        self.terrains = []
        self.chaser = None
        self.player = None
        self.action_music = None

        # Player control level:
        # 0 player in control,
        # 1 auto piloted inside the cockpit,
        # 2 auto piloted outside the cockpit.
        self.player_control_level = 0

        # Whether some bodies should show traces.
        self.show_traces = False

        # Gravity.
        self.gravacc = Vec3(0.0, 0.0, -9.81) # gravity acceleration
        self.absgravacc = self.gravacc.length()

        # Air density.
        self.airdens0 = 1.225 #1.2 # air density at sea level
        # Constant in approximation for density factor at altitude:
        # dens/dens0 = exp(fact * alt)
        self._airdens_fact = -1.10e-4 #-1.25e-4 #-1.44e-4

        # Speed of sound.
        self.airspdsnd0 = 340.0 # speed of sound at sea level
        # Constants in approximation for speed of sound factor at altitude:
        # spdsnd/spdsnd0 = 1 + (1 - spdsndfac_talt) * (alt / talt) if alt < talt
        # spdsndfac_talt if alt >= talt
        self._talt = 11000.0
        self._spdsndfac_talt = 0.87

        # Planet radius.
        self.georad = 6400e3

        # Day time.
        self.day_period = 24.0 * 3600
        self.day_time = 12.0 * 3600 # default to noon
        self.time_factor = 1.0
        self.day_time_factor = 1.0

        self.camera = base.world_camera
        self.camlens = self.camera.node().getLens()
        self.vfov = radians(self.camlens.getFov()[1])

        self.root = base.world_root.attachNewNode("world-scene")
        self.node = self.root.attachNewNode("world")
        if base.with_world_shadows:
            self.shadow_root = base.world_shadow_root.attachNewNode("shadow-scene")
            self.shadow_node = self.shadow_root.attachNewNode("shadow")
            self.shadow_camera = base.world_shadow_camera
            self._shadow_area_size = base.world_shadow_area_size
            self._shadow_area_dist = base.world_shadow_area_dist
            self._shadow_dirl_index = 0
        self.shadow_texture = base.world_shadow_texture # None if shadows off

        self.overlay_root = base.overlay_root.attachNewNode("world-overlay")
        self.stage_root = base.stage_root.attachNewNode("world-stage")
        self.uiface_root = base.uiface_root.attachNewNode("world-interface")
        self.node2d = self.uiface_root # compatibility

        # Set some sound number limit bins.
        Sound3D.set_limnum_group("hum", 2)
        if not base.with_sound_doppler:
            Sound3D.set_limnum_group("flyby", 1, byord=True)

        # Initialize shader inputs.
        self.shdinp = SimpleProps()
        self.shdinp.gtimen = "INgtime"
        lt = AmbientLight(self.shdinp.gtimen)
        lt.setColor(Vec4(0.0, 0.0, 0.0, 0.0))
        lnd = NodePath(lt)
        self._gtimespc = lt
        self.node.setShaderInput(self.shdinp.gtimen, lnd)
        self.shdinp.ambln = "INamblight"
        lt = AmbientLight(self.shdinp.ambln)
        lt.setColor(rgba(255, 255, 255, 1.0))
        lnd = NodePath(lt)
        self.node.setShaderInput(self.shdinp.ambln, lnd)
        self.shdinp.ambsmln = "INambsmlight"
        lt = AmbientLight(self.shdinp.ambsmln)
        lt.setColor(rgba(255, 255, 255, 1.0))
        lnd = NodePath(lt)
        self.node.setShaderInput(self.shdinp.ambsmln, lnd)
        self.shdinp.sunln = "INsunlight"
        self.shdinp.moonln = "INmoonlight"
        self.shdinp.dirlns = (self.shdinp.sunln, self.shdinp.moonln)
        for ln in self.shdinp.dirlns:
            lt = DirectionalLight(ln)
            lt.setColor(rgba(0, 0, 0, 1.0))
            self.node.setShaderInput(ln, NodePath(lt))
        self._max_point_lights = 4
        self.shdinp.pntlns = []
        self.shdinp.pntlnds = []
        for il in xrange(self._max_point_lights):
            ln = "INpntlight%d" % il
            self.shdinp.pntlns.append(ln)
            lt = PointLight(ln)
            lt.setColor(rgba(0, 0, 0, 1.0))
            lnd = NodePath(lt)
            self.shdinp.pntlnds.append(lnd)
            self.node.setShaderInput(ln, lnd)
        self.shdinp.fogn = "INfog"
        self._fogspc = DirectionalLight(self.shdinp.fogn)
        self._fogspc.setSpecularColor(Vec4(-0.5, 0.0, 0.0, 0.0))
        self._fogspc.setColor(rgba(0, 0, 0, 0.0))
        self.node.setShaderInput(self.shdinp.fogn, NodePath(self._fogspc))
        self.shdinp.camn = "INviewcam"
        self.shdinp.camtargn = "INviewcamtarg"
        self._camtarg = NodePath("camtarg")
        self._camtarg.reparentTo(self.camera)
        self._camtarg.setPos(0.0, 1000.0, 0.0)
        self.node.setShaderInput(self.shdinp.camn, self.camera)
        self.node.setShaderInput(self.shdinp.camtargn, self._camtarg)
        self.shdinp.pntobrn = "INoverbright"
        ob = PointLight(self.shdinp.pntobrn)
        ob.setColor(rgba(0, 0, 0, 1.0))
        self.node.setShaderInput(self.shdinp.pntobrn, NodePath(ob))
        self.shdinp.glowfacn = "INglowfac"
        self.shdinp.glowaddn = "INglowadd"
        self.node.setShaderInput(self.shdinp.glowfacn, 1.0)
        self.node.setShaderInput(self.shdinp.glowaddn, 0.0)
        self.shdinp.sunposn = "INsunpos"
        self.shdinp.sunbcoln = "INsunbcol"
        pnd = NodePath("sunpos")
        lt = AmbientLight(self.shdinp.sunbcoln)
        lt.setColor(rgba(0, 0, 0, 1.0))
        lnd = NodePath(lt)
        self._sunbcolspc = lt
        self.node.setShaderInput(self.shdinp.sunposn, pnd)
        self.node.setShaderInput(self.shdinp.sunbcoln, lnd)
        self.shdinp.moonposn = "INmoonpos"
        pnd = NodePath("sunpos-dummy")
        self.node.setShaderInput(self.shdinp.moonposn, pnd)
        self._shdinp_sky_first = True
        self._shdinp_fog_first = True
        self._updwait_shdinp_sky = 0.0
        self._updperiod_shdinp_sky = 0.877
        self._updwait_shdinp_fog_color = 0.0
        self._updperiod_shdinp_fog_color = 0.913
        self._updwait_shdinp_fog_dist = 0.0
        self._updperiod_shdinp_fog_dist = 0.137
        self._updwait_shdinp_sunblind = 0.0
        self._updperiod_shdinp_sunblind = 0.0
        if base.with_world_shadows:
            self.shdinp.shadowrefn = "INshadowref"
            self.node.setShaderInput(self.shdinp.shadowrefn, self.shadow_camera)
            self.shdinp.shadowblendn = "INshadowblend"
            self.node.setShaderInput(self.shdinp.shadowblendn, 0.3)
            self.shdinp.shadowdirlin = "INshadowdirli"
            self.node.setShaderInput(self.shdinp.shadowdirlin, self._shadow_dirl_index)
        else:
            self.shdinp.shadowrefn = None
            self.shdinp.shadowblendn = None
            self.shdinp.shadowdirlin = None

        self._bodies = {}
        self._families_by_move_priority = []

        self._single_actions = {}

        self._prev_chaser = None

        self._curr_hummers = []

        self.action_chasers = []

        # Point lighting.
        self._plight_root = NodePath("plight-root")
        self._plight_ctrav = CollisionTraverser("collision-traverser-plight")
        self._plight_bspecs = []
        self._plight_bnext = 0
        self._plight_bmaxtest = 10
        self._plight_lspecs = []
        self._plight_lnext = 0
        self._plight_lmaxtest = 10
        self._plight_tspecs = {}
        self._updperiod_plight_terrain = 0.277
        self._updwait_plight_terrain = 0.0

        self._state_info_text = None
        self._state_info_period = 1.983
        self._state_info_last_time = 0.0
        self._state_info_last_frame = 0.0

        # Collisions.
        self.ctrav = CollisionTraverser("collision-traverser")
        self.cqueue = CollisionHandlerQueue()
        self._collisions = {}

        # Explosions.
        self._explosion_affected_families = set((
            "plane",
            "heli",
            "rocket",
            "turret",
            "vehicle",
            "building",
            "ship",
        ))
        self._explosion_ctrav = CollisionTraverser("collision-traverser-explosion")
        self._explosions = []

        # LIFO removal of bodies.
        self._remove_bodies_spec_by_family = {
            "vehicle": SimpleProps(keepmax=4),
        }
        self._remove_bodies_queue = dict(
            (f, []) for f in self._remove_bodies_spec_by_family)

        self._allied_sides = {}
        self._allied_to_all = set()

        self._stopwatches = {}

        self._fadescreen = FadeScreen(self, self.stage_root)
        self._cutscene = Cutscene(self, self.stage_root)

        #self._altbin = None
        self._altbin = AltBin(world=self,
                              lowalt=-500.0, highalt=10000.0,
                              altstep=1000.0, altoffset=53.0)

        if not fixdt:
            fixdt = base.fixdt
        self.fixdt = fixdt
        if not self.fixdt:
            self.maxdt = MAX_DT
            base.global_clock.setMaxDt(self.maxdt)
            self._num_hist_dt = int(1.0 / self.maxdt + 0.5)
            self._hist_dts = []
        else:
            self.maxdt = self.fixdt
            base.global_clock.setMode(ClockObject.MNonRealTime)
            base.global_clock.setDt(self.fixdt)
        self.reset_clock()

        self._visradius = None
        self._visradius_extfac = 1.02

        self._select_bodies_cache = {}

        # Body tagging.
        self._tagging_bodies = set()
        self._tagging_bodies_by_tag = {}
        self._tagging_tags_by_body = {}
        self._tagging_body_info = {}
        self._tagging_body_expire = {}
        self._tagging_update_period = 0.2
        self._tagging_update_remaining = 0
        self._tagging_update_bodies = []
        self._tagging_update_speed = 0.0
        self._tagging_update_current = 0

        # Pause handling.
        self.pause = ActionPause(self, self.uiface_root)

        base.set_particle_dt_function(lambda: self.dt)
        Dialog.set_dt_function(lambda: self.dt)

        self.alive = True

        # Before and after all other game logic loops in the frame.
        base.taskMgr.add(self._pre_loop, "world-pre-loop", sort=-10)
        base.taskMgr.add(self._post_loop, "world-post-loop", sort=10)


    def destroy (self):

        if not self.alive:
            return
        self.alive = False


    def _cleanup (self):

        for fbodies in self._bodies.values():
            for fsbodies in fbodies.values():
                for body in fsbodies:
                    body.destroy()
                    body.cleanup()
        if self.camera is base.world_camera:
            base.world_camera.reparentTo(base.world_root)
        self._camtarg.removeNode()
        for terrain in self.terrains:
            terrain.destroy()
        if self.sky:
            self.sky.destroy()
        if self.action_music:
            self.action_music.destroy()
        self._cutscene.destroy()
        self._fadescreen.destroy()
        self.pause.destroy()
        if self._altbin:
            self._altbin.destroy()
        self.root.removeNode()
        if base.with_world_shadows:
            self.shadow_root.removeNode()
        self.overlay_root.removeNode()
        self.stage_root.removeNode()
        self.uiface_root.removeNode()
        if self.player:
            self.player.destroy()
            # NOTE: We could skip this and let player destroy itself
            # in the next frame when it detects that the player aircraft
            # has been destroyed, but then the curtain would be removed
            # one frame before the cockpit, causing a visual glitch.
        for bspec in self._plight_bspecs:
            bspec.bcnode.clearPythonTag("bspec")
        for lspec in self._plight_lspecs:
            lspec.light.destroy()
            lspec.bcnode.clearPythonTag("lspec")
        self._plight_root.removeNode()
        World._count -= 1
        base.set_particle_dt_function(None)
        Dialog.set_dt_function(None)
        self.alive = False


    def _pre_loop (self, task):

        if not self.alive:
            return task.done

        # Move bodies.
        for family in self._families_by_move_priority:
            fbodies = self._bodies[family]
            for fsbodies in fbodies.itervalues():
                for body in fsbodies:
                    body.move(self.dt)
                    body.after_move()

        # Detect collisions.
        # This is done in pre-loop so that other game logic loops
        # can check if there is pending collision evaluation in post-loop.
        self.ctrav.traverse(self.node)
        self._collisions = {}
        for centry in self.cqueue.getEntries():
            self._collect_collision(centry, self._collisions)
        self.cqueue.clearEntries()

        # Update times.
        # This must be done after bodies have been moved with old time step,
        # so it must be here instead of in post loop.
        if not self.pause.active:
            if not self.fixdt:
                cdt = base.global_clock.getDt()
                self._hist_dts.append(cdt)
                if len(self._hist_dts) > self._num_hist_dt:
                    self._hist_dts.pop(0)
                self.dt1 = sum(self._hist_dts) / self._num_hist_dt
            else:
                self.dt1 = self.fixdt
            self.dt = self.dt1 * self.time_factor
        else:
            self.dt = self.maxdt * 1e-6
        self.time += self.dt
        self.frame += 1

        glob_wall_time = base.global_clock.getLongTime()
        self.wall_time = glob_wall_time - self._wall_time0
        #print "--update-wall-time", glob_wall_time, self.wall_time

        self.day_time += self.dt * self.day_time_factor
        while self.day_time >= self.day_period:
            self.day_time -= self.day_period

        return task.cont


    def _post_loop (self, task):

        if not self.alive:
            self._cleanup()
            return task.done

        # Evaluate collisions.
        for body, bcs in self._collisions.iteritems():
            # Collect all collided hitboxes by other body.
            obody_bcs = {}
            for obody, chbx, cpos in bcs:
                obody_bcs_1 = obody_bcs.get(obody)
                if obody_bcs_1 is None:
                    obody_bcs_1 = []
                    obody_bcs[obody] = obody_bcs_1
                obody_bcs_1.append((chbx, cpos))
            # Select the first hitbox along other body's
            # relative velocity direction.
            for obody, obody_bcs_1 in obody_bcs.iteritems():
                rovel = obody.vel(refbody=body)
                obody_bcs_1.sort(key=lambda e: e[1].dot(rovel))
                chbx, cpos = obody_bcs_1[0]
                body.collide(obody, chbx, cpos)
        self._collisions = {}

        # Evaluate explosions.
        for force, ref, touch in self._explosions:
            self._evaluate_explosion(force, ref, touch)
        self._explosions = []

        # Select and destroy action chasers.
        if self.action_chasers:
            if self.player_control_level == 0:
                self.action_chasers = [ch for ch in self.action_chasers if ch.alive]
                if self.action_chasers:
                    self.chaser = self.action_chasers[-1]
            else:
                for ch in self.action_chasers:
                    ch.destroy()
                self.action_chasers = []

        # Clean up destroyed bodies.
        for fbodies in self._bodies.itervalues():
            for fsbodies in fbodies.itervalues():
                to_remove = []
                for body in fsbodies:
                    # Destroy body if any ancestor not alive.
                    parent = body
                    while True:
                        parent = parent.parent
                        if parent is None:
                            break
                        if not parent.alive:
                            body.destroy()
                            break
                    if not body.alive:
                        body.cleanup()
                        to_remove.append(body)
                for body in to_remove:
                    fsbodies.remove(body)

        ## Move bodies. Should be done in pre-loop.

        # Do not allow any other but current player chaser when player is active
        # or in cockpit, unless there are some action chasers.
        if (self.player and self.player.alive and
            self.player_control_level <= 1 and not self.action_chasers):
            self.chaser = self.player.chaser

        # Set camera to current chaser.
        if self.chaser is not None and not self.chaser.alive:
            self.chaser = None
        if self._prev_chaser is not self.chaser:
            self._prev_chaser = self.chaser
            if self.chaser is not None:
                self.camera.reparentTo(self.chaser.node)
                self.camera.setPos(0, 0, 0)
                self.camera.setHpr(0, 0, 0)
            else:
                self.camera.wrtReparentTo(self.node)
                cpos = self.camera.getPos()
                elev = self.elevation(cpos)
                cpos[2] = max(cpos[2], elev + 1.0)
                self.camera.setPos(cpos)
        if self.chaser is not None:
            self.camlens.setMinFov(self.chaser.fov)
        else:
            self.camlens.setMinFov(ANIMATION_FOV)
        self.vfov = radians(self.camlens.getFov()[1])

        if self._altbin:
            cpos = self.camera.getPos(self.node)
            self._altbin.set_viewer_altitude(cpos[2])

        # Set camera clip distances.
        if self._visradius is not None:
            neardist = 1.0
            cpos = self.camera.getPos(self.node)
            altvisradius = sqrt(self._visradius**2 + cpos[2]**2)
            fardist = altvisradius * self._visradius_extfac
            self.camlens.setNearFar(neardist, fardist)
        elif self.terrains:
            refterrain = self.terrains[0]
            self._visradius = refterrain.extents()[4]

        # Set sound Doppler effect.
        if base.with_sound_doppler:
            # Set listener velocity for Doppler effect to current chaser.
            if self.chaser is not None and self.chaser.alive:
                chvel = self.chaser.vel()
                base.audio3d_manager.setListenerVelocity(chvel)

        # Update point light application.
        self._update_plight_limits()
        self._update_plight_lights()
        self._update_plight_bodies()
        self._update_plight_terrains()

        # Update tagging.
        self._update_tagging()

        # Expire single actions.
        for akey, (action, donef) in self._single_actions.items():
            if donef(action):
                self._single_actions.pop(akey)

        # Activate cutscene view.
        if self.player_control_level < 2:
            self._cutscene.active = False
        else:
            self._cutscene.active = True

        # Update shader inputs.
        self._gtimespc.setColor(Vec4(self.time, 0.0, 0.0, 0.0))
        if self._shdinp_sky_first:
            if self.sky:
                self._shdinp_sky_first = False
                self.node.setShaderInput(self.shdinp.ambln, self.sky.amblight)
                self.node.setShaderInput(self.shdinp.ambsmln, self.sky.amblight_smoke)
                self.node.setShaderInput(self.shdinp.sunln, self.sky.sunlight)
                self.node.setShaderInput(self.shdinp.moonln, self.sky.moonlight)
                if self.sky.sun:
                    self.node.setShaderInput(self.shdinp.sunposn, self.sky.sun.sunnode)
                if self.sky.moon:
                    self.node.setShaderInput(self.shdinp.moonposn, self.sky.moon.moonnode)
                if base.with_world_shadows:
                    self.node.setShaderInput(self.shdinp.shadowblendn, self.sky.shadowblend)
        if self._shdinp_fog_first and self.sky:
            fog = self.sky.fog
            if fog and fog.color is not None:
                self._shdinp_fog_first = False
                if fog.falloff is None:
                    fogvis = Vec4(0.5, fog.onsetdist, fog.opaquedist, 0.0)
                else:
                    fogvis = Vec4(1.5, fog.falloff, 2.0, 0.0)
                self._fogspc.setSpecularColor(fogvis)
        if not self._shdinp_sky_first:
            if self.frame < 3:
                self._updwait_shdinp_sky = 0.0
            self._updwait_shdinp_sky -= self.dt * self.day_time_factor
            if self._updwait_shdinp_sky <= 0.0:
                self._updwait_shdinp_sky += self._updperiod_shdinp_sky
                self._sunbcolspc.setColor(self.sky.sun_bright_color)
        if not self._shdinp_fog_first and self.sky.fog:
            if self.frame < 3:
                self._updwait_shdinp_fog_color = 0.0
                self._updwait_shdinp_fog_dist = 0.0
            self._updwait_shdinp_fog_color -= self.dt * self.day_time_factor
            if self._updwait_shdinp_fog_color <= 0.0:
                self._updwait_shdinp_fog_color += self._updperiod_shdinp_fog_color
                self._fogspc.setColor(self.sky.fog.color)
            self._updwait_shdinp_fog_dist -= self.dt * self.day_time_factor
            if self._updwait_shdinp_fog_dist <= 0.0:
                self._updwait_shdinp_fog_dist += self._updperiod_shdinp_fog_dist
                fog = self.sky.fog
                if fog.falloff is None and fog.altvardist is not None:
                    cpos = self.camera.getPos(self.node)
                    onsetdist, opaquedist = fog.dist_for_alt(cpos[2])
                    fogvis = Vec4(0.5, onsetdist, opaquedist, 0.0)
                    self._fogspc.setSpecularColor(fogvis)
        if not self._shdinp_sky_first and self.sky.sun:
            if self.frame < 3:
                self._updwait_shdinp_sunblind = 0.0
            self._updwait_shdinp_sunblind -= self.dt
            if self._updwait_shdinp_sunblind <= 0.0:
                self._updwait_shdinp_sunblind += self._updperiod_shdinp_sunblind
                ret = map_pos_to_screen(self.camera, self.sky.sun.sunnode,
                                        scrnode=self.overlay_root)
                sun_spos, sun_back = ret
                if not sun_back:
                    hw = base.aspect_ratio
                    sun_ovr_uv = Point2((sun_spos[0] / hw + 1.0) * 0.5,
                                        (sun_spos[2] + 1.0) * 0.5)
                    sun_str = self.sky.sun_strength
                else:
                    sun_ovr_uv = Point2()
                    sun_str = 0.0
                sun_rad_uv = 0.5 * (self.sky.sun.size / self.vfov)
                #out_dist = radians(26.0) / (0.5 * self.vfov)
                out_dist = 0.8
                spec0 = Vec4(sun_ovr_uv[0], sun_ovr_uv[1], sun_rad_uv, sun_str)
                sbc = self.sky.sun_bright_color
                spec1 = Vec4(sbc[0], sbc[1], sbc[2], out_dist)
                base.set_sun_blinding(spec0, spec1)

        # Update shadows.
        if base.with_world_shadows:
            shd_cam = self.shadow_camera
            if self.sky and self.sky.sun and self.sky.moon:
                sun_pos = self.sky.sun.sunnode.getPos(self.node)
                shd_dirli = 0 if (sun_pos[2] - self.sky.sun.diameter * 0.5 > 0.0) else 1
                if shd_dirli == 0:
                    dirl_quat = self.sky.sunlight.getQuat(self.node)
                else:
                    dirl_quat = self.sky.moonlight.getQuat(self.node)
                dirl_quat.normalize()
                shd_cam.setQuat(dirl_quat)
                foc_pos = None
                if self.chaser is not None:
                    foc_pos = self.chaser.focus_point()
                if foc_pos is not None:
                    shd_pos = foc_pos
                else:
                    cam_pos = self.camera.getPos(self.node)
                    cam_quat = self.camera.getQuat(self.node)
                    shd_asize = self._shadow_area_size
                    shd_pos = cam_pos + cam_quat.getForward() * (shd_asize * 0.25)
                shd_adist = self._shadow_area_dist
                shd_pos += dirl_quat.getForward() * -shd_adist
                shd_cam.setPos(shd_pos)
                if self._shadow_dirl_index != shd_dirli:
                    self._shadow_dirl_index = shd_dirli
                    self.node.setShaderInput(self.shdinp.shadowdirlin, self._shadow_dirl_index)
            else:
                shd_cam.setHpr(0, -90, 0)
                shd_cam.setPos(0, 0, -1000)

        # Invalidate per-frame caches.
        self._select_bodies_cache = {}

        # Take away control from player in pause.
        # FIXME: Cannot be done by changing self.player_control_level.
        pass

        # Update state information.
        if self._state_info_text is not None:
            self._update_state_info()

        return task.cont


    def _update_plight_limits (self):

        hw = base.aspect_ratio
        self._plight_minhangsize = (self.vfov / 100) * 0.5
        self._plight_hdiagfov = atan(tan(self.vfov * 0.5) * sqrt(hw**2 + 1.0))


    def _update_plight_lights (self):

        numlspecs = len(self._plight_lspecs)
        numltest = min(numlspecs, self._plight_lmaxtest)
        for q in xrange(numltest):
            lspec = self._plight_lspecs[self._plight_lnext]
            light = lspec.light
            if light.alive and light.parent.alive:
                lstr0 = light.strength(0.0)
                if lstr0 > 0.0:
                    if not lspec.active:
                        lspec.active = True
                        lspec.bcnode.setIntoCollideMask(0xffff)
                    lpos = light.node.getPos(self.node)
                    lspec.bnode.setPos(lpos)
                    lrad = light.radius
                    lspec.bound.setRadius(lrad)
                    vpos = light.node.getPos(self.camera)
                    if self._sphere_in_view(lrad, vpos):
                        elev = self.elevation(lpos)
                        otralt = lpos[2] - elev
                        if lrad > otralt:
                            gradius = sqrt(max(lrad**2 - otralt**2, 0.0))
                            lstr = light.strength(otralt)
                            lgpos = Point3(lpos[0], lpos[1], elev)
                            vgpos = self.camera.getRelativePoint(self.node, lgpos)
                            lspec.hgangsize = atan(gradius / vgpos.length()) * lstr
                        else:
                            lspec.hgangsize = 0.0
                else:
                    if lspec.active:
                        lspec.active = False
                        lspec.bcnode.setIntoCollideMask(0x0000)
                        lspec.hgangsize = 0.0
                self._plight_lnext = (self._plight_lnext + 1) % numlspecs
            else:
                light.destroy()
                self._plight_lspecs.pop(self._plight_lnext)
                numlspecs -= 1
                if numlspecs == 0:
                    break
                self._plight_lnext %= numlspecs


    def _update_plight_bodies (self):

        test_bspecs = []
        numbspecs = len(self._plight_bspecs)
        numbtest = min(numbspecs, self._plight_bmaxtest)
        for q in xrange(numbtest):
            bspec = self._plight_bspecs[self._plight_bnext]
            body = bspec.body
            if body.alive:
                bcpos = self.camera.getRelativePoint(body.node, body.bboxcenter)
                if self._sphere_in_view(bspec.bradius, bcpos):
                    bwpos = self.node.getRelativePoint(body.node, body.bboxcenter)
                    bspec.bnode.setPos(bwpos)
                    test_bspecs.append(bspec)
                self._plight_bnext = (self._plight_bnext + 1) % numbspecs
            else:
                self._plight_bspecs.pop(self._plight_bnext)
                numbspecs -= 1
                if numbspecs == 0:
                    break
                self._plight_bnext %= numbspecs

        ctrav = self._plight_ctrav
        ctrav.clearColliders()
        cqueue = CollisionHandlerQueue()
        for bspec in test_bspecs:
            ctrav.addCollider(bspec.bnode, cqueue)
        ctrav.traverse(self._plight_root)
        bspecs_lspecs = dict((b, []) for b in test_bspecs)
        for entry in cqueue.getEntries():
            bnode = entry.getFromNode()
            lnode = entry.getIntoNode()
            bspec = bnode.getPythonTag("bspec")
            lspec = lnode.getPythonTag("lspec")
            bspecs_lspecs[bspec].append(lspec)
        #print ("--plight-bodies  numbspecs=%d  numlspecs=%d  "
               #"numtbspecs=%d  numblcoll=%d"
               #% (len(self._plight_bspecs), len(self._plight_lspecs),
                  #len(test_bspecs), len(cqueue.getEntries())))

        for bspec, lspecs in bspecs_lspecs.iteritems():
            body = bspec.body
            # Select strongest lights, relative to body center.
            negstrs_lspecs = []
            for lspec in lspecs:
                light = lspec.light
                if light.alive:
                    lbpos = light.node.getPos(body.node)
                    ldist = (lbpos - body.bboxcenter).length()
                    strength = light.strength(ldist)
                    negstrs_lspecs.append((-strength, ldist, lspec))
            negstrs_lspecs.sort()
            sel_lspecs = [x[-1] for x in negstrs_lspecs[:body.pntlit]]
            self._update_plight_set(body, bspec.linds, sel_lspecs)


    def _update_plight_terrains (self):

        self._updwait_plight_terrain -= self.dt
        if self._updwait_plight_terrain <= 0.0:
            self._updwait_plight_terrain += self._updperiod_plight_terrain
            lspecs_sorted = [(-x.hgangsize, x) for x in self._plight_lspecs
                             if x.hgangsize > 0.0 and x.light.alive]
            lspecs_sorted.sort()
            for terrain in self.terrains:
                tspecs = self._plight_tspecs.get(terrain)
                if tspecs is None:
                    tspecs = SimpleProps(linds={})
                    self._plight_tspecs[terrain] = tspecs
                sel_lspecs = [x[1] for x in lspecs_sorted[:terrain.pntlit]]
                self._update_plight_set(terrain, tspecs.linds, sel_lspecs)


    def _sphere_in_view (self, radius, pos):

        inside = False
        dist = pos.length()
        if radius > dist:
            inside = True
        else:
            hangsize = atan(radius / dist)
            if hangsize > self._plight_minhangsize:
                hoffangc = acos(pos[1] / dist)
                hoffangt = hoffangc - hangsize
                if hoffangt < self._plight_hdiagfov:
                    inside = True
        return inside


    def _update_plight_set (self, obj, olinds, lspecs):

        # Select non-set lights.
        add_lspecs = []
        linds = range(obj.pntlit)
        for lspec in lspecs:
            i = olinds.get(lspec)
            if i is None:
                add_lspecs.append(lspec)
            else:
                linds.remove(i)

        # Set new lights.
        for lspec in add_lspecs:
            #print "--upd-light  add=%s  to=%s" % (lspec.light.name, obj.name)
            i = linds.pop(0)
            obj.node.setShaderInput(self.shdinp.pntlns[i], lspec.light.node)
            olinds[lspec] = i

        # Remove old lights.
        old_lspecs = frozenset(olinds.keys()).difference(lspecs)
        for lspec in old_lspecs:
            i = olinds.pop(lspec)
            if i in linds:
                obj.node.setShaderInput(self.shdinp.pntlns[i], self.shdinp.pntlnds[i])
            #print "--upd-light  remove=%s  from=%s" % (lspec.light.name, obj.name)


    def _update_tagging (self):

        if self._tagging_update_remaining == 0:
            self._tagging_update_bodies = list(self._tagging_bodies)
            self._tagging_update_remaining = len(self._tagging_update_bodies)
            self._tagging_update_speed = self._tagging_update_remaining / self._tagging_update_period
            self._tagging_update_current = 0.0

        update_next = self._tagging_update_current + self._tagging_update_speed * self.dt
        for k in xrange(int(self._tagging_update_current), int(update_next)):
            body = self._tagging_update_bodies[self._tagging_update_remaining - 1]

            tags = tuple(self._tagging_tags_by_body[body])
            for tag in tags:
                tbkey = (tag, body)
                expire, checktime = self._tagging_body_expire[tbkey]
                if expire is not None:
                    expire -= self.time - checktime
                    if expire <= 0.0:
                        self._tagging_tags_by_body[body].remove(tag)
                        self._tagging_bodies_by_tag[tag].remove(body)
                        self._tagging_body_info.pop(tbkey)
                        self._tagging_body_expire.pop(tbkey)
                    else:
                        self._tagging_body_expire[tbkey] = (expire, self.time)
            if not self._tagging_tags_by_body:
                self._tagging_bodies.remove(body)

            self._tagging_update_remaining -= 1
            if self._tagging_update_remaining == 0:
                break
        self._tagging_update_current = update_next


    def reset_clock (self):

        self.dt1 = self.maxdt
        self.dt = self.dt1 * self.time_factor
        self.time = 0.0
        self.frame = 0l
        self._time0 = 0.0
        self.wall_time = 0.0
        self._wall_time0 = base.global_clock.getLongTime()
        #print "--reset-clock", self._wall_time0, self.wall_time
        # NOTE: Do not do self.day_time = 0.0 here,
        # because this time is not part of technical clock.


    def single_action (self, node, name, makef, donef):

        akey = (node, name)

        if akey not in self._single_actions:
            action = makef()
            self._single_actions[akey] = (action, donef)


    def register_body (self, body):

        fbodies = self._bodies.get(body.family)
        if fbodies is None:
            fbodies = {}
            self._bodies[body.family] = fbodies
            if body.family in ("chaser",):
                self._families_by_move_priority.append(body.family)
            else:
                self._families_by_move_priority.insert(0, body.family)
        fsbodies = fbodies.get(body.species)
        if fsbodies is None:
            fsbodies = set()
            fbodies[body.species] = fsbodies
        fsbodies.add(body)

        if body.pntlit > 0 and body.models:
            cnd = CollisionNode(body.name)
            cnd.setIntoCollideMask(0x0000)
            bradius = body.bboxdiag * 0.5
            cs = CollisionSphere(Point3(), bradius)
            cnd.addSolid(cs)
            nd = self._plight_root.attachNewNode(cnd)
            bspec = SimpleProps(body=body,
                                bound=cs, bcnode=cnd, bnode=nd,
                                bradius=bradius, lspecs={}, linds={})
            cnd.setPythonTag("bspec", bspec)
            self._plight_bspecs.append(bspec)


    def register_plight (self, light):

        cnd = CollisionNode(light.name)
        cs = CollisionSphere(Point3(), light.radius)
        cnd.addSolid(cs)
        cnd.setFromCollideMask(0x0000)
        cnd.setIntoCollideMask(0x0000)
        nd = self._plight_root.attachNewNode(cnd)
        nd.setPos(light.node.getPos(self.node))
        lspec = SimpleProps(light=light,
                            bound=cs, bcnode=cnd, bnode=nd,
                            hgangsize=0.0, active=False)
        cnd.setPythonTag("lspec", lspec)
        self._plight_lspecs.append(lspec)


    def iter_bodies (self, family=None, species=None):

        # NOTE: All species must be unique, even from different families.
        if species is None:
            if family is None:
                families = self._bodies.iterkeys()
            else:
                families = as_sequence(family)
            for family in families:
                fbodies = self._bodies.get(family)
                if fbodies is not None:
                    for fsbodies in fbodies.itervalues():
                        for body in fsbodies:
                            yield body
        elif family is None:
            species = set(as_sequence(species))
            for fbodies in self._bodies.itervalues():
                found_species = set()
                for specie in species:
                    fsbodies = fbodies.get(specie)
                    if fsbodies is not None:
                        found_species.add(specie)
                        for body in fsbodies:
                            yield body
                species = species.difference(found_species)
                if not species:
                    break
        else:
            raise StandardError(
                "Pass either family or species argument, not both.")


    def select_bodies (self, family=None, species=None, cache=False):

        if cache:
            skey = (family, species)
            bodies = self._select_bodies_cache.get(skey)
            if bodies is not None:
                return bodies

        # NOTE: All species must be unique, even from different families.
        bodies = []
        if species is None:
            if family is None:
                families = self._bodies.iterkeys()
            else:
                families = as_sequence(family)
            for family in families:
                fbodies = self._bodies.get(family)
                if fbodies is not None:
                    for fsbodies in fbodies.itervalues():
                        bodies.extend(fsbodies)
        elif family is None:
            species = set(as_sequence(species))
            for fbodies in self._bodies.itervalues():
                found_species = set()
                for specie in species:
                    fsbodies = fbodies.get(specie)
                    if fsbodies is not None:
                        bodies.extend(fsbodies)
                        found_species.add(specie)
                species = species.difference(found_species)
                if not species:
                    break
        else:
            raise StandardError(
                "Pass either family or species argument, not both.")
        bodies = tuple(bodies)
        if cache:
            self._select_bodies_cache[skey] = bodies
        return bodies


    def airdens (self, alt):

        return self.airdens0 * self.airdens_factor(alt)


    def airdens_factor (self, alt):

        return exp(self._airdens_fact * alt)


    def airspdsnd (self, altitude):

        return self.airspdsnd0 * self.airspdsnd_factor(altitude)


    def airspdsnd_factor (self, altitude):

        if altitude < self._talt:
            return 1.0 + (self._spdsndfac_talt - 1.0) * (altitude / self._talt)
        else:
            return self._spdsndfac_talt


    def otr_altitude (self, pos):

        return pos[2] - self.elevation(pos)


    def otr_pos (self, pos):

        return Point3(pos[0], pos[1], self.elevation(pos) + pos[2])


    def elevation (self, pos,
                   igntrs=None, wnorm=False, wtype=False, flush=False):

        reftrs = self._get_referent_terrains(igntrs)
        if reftrs:
            x, y = pos[0], pos[1]
            if not wnorm and not wtype: # shortcut for performance
                return max(tr.height_q(x, y, flush) for tr in reftrs)
            else:
                maxh = -1e30
                nmaxh = Vec3()
                tmaxh = -1
                for tr in reftrs:
                    h, n, t = tr.height(x, y, flush)
                    if maxh < h:
                        maxh = h
                        nmaxh = n
                        tmaxh = t
        else:
            maxh = 0.0
            nmaxh = Vec3(0.0, 0.0, 1.0)
            tmaxh = -1

        if wnorm and wtype:
            return maxh, nmaxh, tmaxh
        elif wnorm:
            return maxh, nmaxh
        elif wtype:
            return maxh, tmaxh
        else:
            return maxh


    def max_elevation (self, igntrs=None):

        reftrs = self._get_referent_terrains(igntrs)
        if not reftrs:
            return 0.0

        return max(t.max_height() for t in reftrs)


    def below_surface (self, pos, elev=0.0):

        reftrs = self._get_referent_terrains()
        return any(t.below_surface(pos[0], pos[1], pos[2] - elev) for t in reftrs)


    def intersect_surface (self, pos0, pos1, elev=0.0):

        otr0 = self.otr_altitude(pos0) - elev
        otr1 = self.otr_altitude(pos1) - elev
        ifac = (0.0 - otr0) / (otr1 - otr0)
        posi = pos0 * (1.0 - ifac) + pos1 * ifac
        return posi


    def _get_referent_terrains (self, igntrs=None):

        if igntrs:
            igntrs = [(self.terrains[t] if isinstance(t, int) else t)
                      for t in igntrs]
            reftrs = [t for t in self.terrains if t not in igntrs]
        else:
            reftrs = self.terrains

        return reftrs


    def arena_edge_dist (self, pos):

        if not self.terrains:
            return 1e30
        terrain = self.terrains[0] # referent terrain
        xmin, ymin, xmax, ymax, visradius = terrain.extents()
        x, y = pos[0], pos[1]
        aeneardist = min(x - xmin, xmax - x, y - ymin, ymax - y)
        aedist = aeneardist - visradius
        return aedist


    def inside_arena (self, pos, slack=0.0):

        terrain = self.terrains[0] # referent terrain
        xmin, ymin, xmax, ymax, visradius = terrain.extents()
        x, y = pos[0], pos[1]
        inside = (xmin + visradius - slack < x < xmax - visradius + slack and
                  ymin + visradius - slack < y < ymax - visradius + slack)
        return inside


    def arena_width (self):

        terrain = self.terrains[0] # referent terrain
        xmin, ymin, xmax, ymax, visradius = terrain.extents()
        awidthx = xmax - xmin
        awidthy = ymax - ymin
        return awidthx, awidthy


    def add_action_chaser (self, chaser):

        self.action_chasers.append(chaser)


    def in_collision (self, body):

        return body in self._collisions


    def _collect_collision (self, centry, collisions):

        nd_from = centry.getFromNodePath()
        hbx_from = nd_from.getPythonTag("hitbox")
        body_from = hbx_from.pbody
        nd_into = centry.getIntoNodePath()
        hbx_into = nd_into.getPythonTag("hitbox")
        body_into = hbx_into.pbody
        if body_into is body_from:
            return

        if True:
            if centry.hasSurfacePoint():
                cpos_from = centry.getSurfacePoint(body_from.node)
            else:
                cpos_from = hbx_from.center
            cp = collisions.get(body_from)
            if cp is None:
                cp = []
                collisions[body_from] = cp
            cp.append((body_into, hbx_from, cpos_from))
        if not hbx_into.isfrom or not hbx_from.isinto:
            if centry.hasSurfacePoint():
                cpos_into = centry.getSurfacePoint(body_into.node)
            else:
                cpos_into = hbx_into.center
            cp = collisions.get(body_into)
            if cp is None:
                cp = []
                collisions[body_into] = cp
            cp.append((body_from, hbx_into, cpos_into))


    def explosion_damage (self, force, ref, touch=[]):

        self._explosions.append((force, ref, touch))


    def _evaluate_explosion (self, force, ref, touch=[]):

        # Create collision sphere for extent of explosion.
        maxdist = explosion_reach(force)
        cnd = CollisionNode("explosion")
        cs = CollisionSphere(Point3(), maxdist)
        cnd.addSolid(cs)
        cnd.setIntoCollideMask(0x0000)
        expnd = self.node.attachNewNode(cnd)
        pos = ref.pos() if isinstance(ref, Body) else ref
        expnd.setPos(pos)

        # Collect collided hitboxes, with minimum collision distances.
        ctrav = self._explosion_ctrav
        cqueue = CollisionHandlerQueue()
        ctrav.clearColliders()
        ctrav.addCollider(expnd, cqueue)
        ctrav.traverse(self.node)
        dist_by_hbx = {}
        tbodies = set(b for b, f in touch)
        for centry in cqueue.getEntries():
            bcnode = centry.getIntoNode()
            hbx = bcnode.getPythonTag("hitbox")
            body = hbx.pbody
            if (hbx.active and
                body is not ref and body not in tbodies and
                body.family in self._explosion_affected_families):
                dist = maxdist + 1.0
                if centry.hasSurfacePoint():
                    dist1 = centry.getSurfacePoint(expnd).length()
                    dist = min(dist, dist1)
                dist2 = expnd.getPos(hbx.cnode).length()
                dist = min(dist, dist2)
                odist = dist_by_hbx.get(hbx)
                if odist is None or dist < odist:
                    dist_by_hbx[hbx] = dist
        expnd.removeNode()

        # Create dummy explosion body.
        ebody = None
        if dist_by_hbx or touch:
            ebody = Body(world=self, family="effect", species="explosion",
                         hitforce=force, name="", side="", pos=pos,
                         hitinto=False)
            if isinstance(ref, Body):
                ebody.initiator = ref.initiator

        # Add damage to collided hitboxes.
        for hbx, dist in dist_by_hbx.items():
            ebody.hitforce = explosion_dropoff(force, dist)
            body = hbx.pbody
            body.collide(ebody, hbx, Point3())

        # Add damage to touched hitboxes.
        for body, eforce in touch:
            ebody.hitforce = eforce
            dbgval(1, "thunder-of-god",
                   (self.time, "%.1f", "time", "s"),
                   ("%s(%s)" % (body.name, body.species), "%s", "into"),
                   (eforce, "%.2f", "force"))
            for hbx in body.hitboxes:
                body.collide(ebody, hbx, Point3())

        if ebody:
            ebody.destroy()


    def clear_action_chasers (self):

        self.action_chasers = []


    def fade_in (self, duration=0.0, startalpha=1.0, endalpha=0.0):

        self._fadescreen.fade_in(duration, startalpha, endalpha)


    def fade_out (self, duration=0.0, startalpha=0.0, endalpha=1.0):

        self._fadescreen.fade_out(duration, startalpha, endalpha)


    def show_state_info (self, pos, align="l", anchor="tl"):

        if self._state_info_text is None:
            self._state_info_text = make_text(text="", width=0.6, size=10,
                                              align=align, anchor=anchor,
                                              shcolor=rgba(0, 0, 0, 1),
                                              parent=self.uiface_root)
        self._state_info_text.setPos(pos)
        self._state_info_text.show()


    def hide_state_info (self):

        if self._state_info_text is not None:
            self._state_info_text.hide()


    def _update_state_info (self):

        if self._state_info_text.isHidden():
            return
        etime = self.wall_time - self._state_info_last_time
        if etime < self._state_info_period:
            return
        self._state_info_last_time = self.wall_time
        eframes = self.frame - self._state_info_last_frame
        self._state_info_last_frame = self.frame

        avgdt = etime / eframes
        ls = []
        dayhr = int(self.day_time / 3600)
        daymin = int((self.day_time - dayhr * 3600) / 60)
        ls.append("day-time: %02d:%02d [hr:min]" % (dayhr, daymin))
        ls.append("world-time: %.0f (%.0f) [sec]" % (self.time, self.wall_time))
        ls.append("frame-duration: %.2f [msec]" % (avgdt * 1000))
        ls.append("planes: %d" % len(tuple(self.iter_bodies(family="plane"))))
        text = "\n".join(ls)

        #self._wait_time_state_info = 0.10
        #print "--last-frame-duration: %.1f [msec]" % (self.dt * 1000)

        update_text(self._state_info_text, text=text)


    def make_alliance (self, sides):

        for side in sides:
            allied_sides = self._allied_sides.get(side)
            if allied_sides is None:
                allied_sides = set([side])
                self._allied_sides[side] = allied_sides
            allied_sides.update(sides)


    def break_alliance (self, sides):

        for side in sides:
            allied_sides = self._allied_sides.get(side)
            if allied_sides is not None:
                allied_sides = allied_sides.difference(sides)
                allied_sides.add(side)
                self._allied_sides[side] = allied_sides


    def get_allied_sides (self, side):

        fsides = self._allied_sides.get(side)
        if fsides is None:
            fsides = set([side])
            fsides.update(self._allied_to_all)
            self._allied_sides[side] = fsides

        return fsides


    def get_friendlies (self, families, side):

        friendlies = set()
        allied_sides = self.get_allied_sides(side)
        for family in families:
            for body in self.iter_bodies(family):
                if body.side in allied_sides:
                    friendlies.add(body)
        return friendlies


    def set_allied_to_all (self, sides):

        self._allied_to_all = set(sides)
        for fsides in self._allied_sides.values():
            fsides.update(self._allied_to_all)


    def stopwatch (self, name):

        sw = self._stopwatches.get(name)
        if sw is None:
            sw = Stopwatch(self)
            self._stopwatches[name] = sw
        return sw


    def add_altbin_node (self, node):

        if self._altbin:
            self._altbin.add_node(node)


    def tag_body (self, tag, body, info=None, expire=None):

        self._tagging_bodies.add(body)

        bodies = self._tagging_bodies_by_tag.get(tag)
        if bodies is None:
            bodies = set()
            self._tagging_bodies_by_tag[tag] = bodies
        bodies.add(body)

        tags = self._tagging_tags_by_body.get(body)
        if tags is None:
            tags = set()
            self._tagging_tags_by_body[body] = tags
        tags.add(tag)

        self._tagging_body_info[(tag, body)] = info

        self._tagging_body_expire[(tag, body)] = (expire, self.time)


    def expire_body_tag (self, tag, body):

        tbkey = (tag, body)
        ret = self._tagging_body_expire.get(tbkey)
        if ret is not None:
            self._tagging_body_expire[tbkey] = (0.0, self.time)


    def tagged_bodies (self, tag):

        bodies = self._tagging_bodies_by_tag.get(tag) or set()
        return bodies


    def tagged_body_info (self, tag, body):

        info = self._tagging_body_info.get((tag, body))
        return info


    def remove_body_on_count (self, body):

        rem_spec = self._remove_bodies_spec_by_family.get(body.family)
        if rem_spec is not None:
            rem_bodies = self._remove_bodies_queue[body.family]
            if body not in rem_bodies:
                rem_bodies.append(body)
                if len(rem_bodies) > rem_spec.keepmax:
                    old_body = rem_bodies.pop(0)
                    old_body.destroy()


    # Dummy body-like methods, so that world can be parent to bodies.

    def pos (self, refbody=None, offset=None):

        refbody = refbody or self
        if offset is None:
            if refbody is self:
                return self.node.getPos()
            else:
                return self.node.getPos(refbody.node)
        else:
            return refbody.node.getRelativePoint(self.node, offset)


    def quat (self, refbody=None):

        if refbody is None:
            return self.node.getQuat()
        else:
            return self.node.getQuat(refbody.node)


    def vel (self, refbody=None):

        return Vec3()


    def acc (self, refbody=None):

        return Vec3()


    def angvel (self, refbody=None):

        return Vec3()


    def angacc (self, refbody=None):

        return Vec3()


class AltBin (object):

    _count = 0

    def __init__ (self, world, lowalt, highalt, altstep, altoffset=0.0):

        if AltBin._count > 0:
            raise StandardError(
                "Only one altitude binning at a time can be created.")
        AltBin._count += 1

        self._world = world

        self._binmgr = CullBinManager.getGlobalPtr()

        self._alts = []
        alt = lowalt
        while alt < highalt:
            alt1 = alt + altoffset
            self._alts.append(alt1)
            alt += altstep

        # Insert layers between predefined opaque and transparent bin.
        # Increase sort value of predefined bins as necessary.
        # FIXME: Pick default values by examining Panda's default bin set.
        self._sort1 = 20 + 1 # sort of opaque is 20
        self._sort2 = self._sort1 + len(self._alts) + 1
        for i, bn in enumerate(("transparent", "fixed", "unsorted")):
            self._binmgr.setBinSort(bn, self._sort2 + i)

        self._binnames = []
        self._binaltsinds = []
        numalts = len(self._alts)
        for i in xrange(numalts + 1):
            bn = "altbin-layer-%d" % i
            binind = self._binmgr.findBin(bn)
            if binind < 0:
                self._binmgr.addBin(bn, CullBinManager.BTBackToFront, 0)
                binind = self._binmgr.findBin(bn)
            else:
                self._binmgr.setBinActive(binind, True)
            self._binnames.append(bn)
            if i == 0:
                binalt = self._alts[0] - 0.5 * altstep
            elif i == numalts:
                binalt = self._alts[-1] + 0.5 * altstep
            else:
                binalt = 0.5 * (self._alts[i - 1] + self._alts[i])
            self._binaltsinds.append((binalt, binind))

        self._nodes = []

        self._viewalt = 0.0

        self._updwait_setsort = 0.0
        self._updperiod_setsort = 0.127
        self._updcnt_binnode = 0
        self._updframe_binnode = 5

        self.alive = True
        base.taskMgr.add(self._loop, "altbin-loop")


    def destroy (self):

        if not self.alive:
            return
        for ba, bi in self._binaltsinds:
            self._binmgr.setBinActive(bi, False)
        AltBin._count -= 1
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self._world.alive:
            self.destroy()
            return task.done

        dt = self._world.dt

        self._updwait_setsort -= dt
        if self._updwait_setsort <= 0.0:
            self._updwait_setsort = self._updperiod_setsort
            baisrt = [(abs(ba - self._viewalt), bi) for ba, bi in self._binaltsinds]
            baisrt.sort()
            for i, (ba, bi) in enumerate(baisrt):
                self._binmgr.setBinSort(bi, self._sort2 - i - 1)

        numnodes = len(self._nodes)
        if numnodes > 0:
            for k in xrange(min(self._updframe_binnode, numnodes)):
                self._updcnt_binnode = (self._updcnt_binnode + 1) % numnodes
                node = self._nodes[self._updcnt_binnode]
                if not node.isEmpty():
                    alt = node.getPos(self._world.node)[2]
                    i = bisect(self._alts, alt)
                    node.setBin(self._binnames[i], 0) # sort value ignored
                else:
                    self._nodes.pop(self._updcnt_binnode)
                    self._updcnt_binnode -= 1
                    numnodes -= 1
                    if numnodes == 0:
                        break

        return task.cont


    def set_viewer_altitude (self, altitude):

        self._viewalt = altitude


    def add_node (self, node):

        self._nodes.append(node)


class Stopwatch (object):

    def __init__ (self, clock):

        self._clock = clock
        self.reset()


    def reset (self, inittime=0.0, onread=False):

        if not onread:
            self._time = self._clock.time
            self._passtime = inittime
            self._reset_on_read = False
        else:
            self._reset_on_read = True
            self._reset_on_read_inittime = inittime


    def read (self):

        self._update()
        return self._passtime


    def _update (self):

        if self._reset_on_read:
            self.reset(inittime=self._reset_on_read_inittime)

        newtime = self._clock.time
        self._passtime += newtime - self._time
        self._time = newtime


    def __eq__ (self, sec):
        self._update()
        return self._passtime == sec
    def __lt__ (self, sec):
        self._update()
        return self._passtime < sec
    def __le__ (self, sec):
        self._update()
        return self._passtime <= sec
    def __gt__ (self, sec):
        self._update()
        return self._passtime > sec
    def __ge__ (self, sec):
        self._update()
        return self._passtime >= sec


class Cutscene (object):

    def __init__ (self, world, pnode):

        self.alive = True
        self.world = world

        self.active = False
        self._prev_active = False

        self.node = pnode.attachNewNode("cutscene")
        self.nd_up = self.node.attachNewNode("cutscene-up")
        self.nd_up.hide()
        self.nd_down = self.node.attachNewNode("cutscene-down")
        self.nd_down.hide()

        self._bar_height = 0.3

        hw = base.aspect_ratio
        self._black_up = make_image(
            "images/ui/black.png",
            size=(2 * hw, self._bar_height),
            pos=Point3(0.0, 0.0, 1.0 + self._bar_height * 0.5),
            parent=self.nd_up)
        self._black_down = make_image(
            "images/ui/black.png",
            size=(2 * hw, self._bar_height),
            pos=Point3(0.0, 0.0, -1.0 - self._bar_height * 0.5),
            parent=self.nd_down)

        Dialog.set_screen_size_function(
            lambda: (-hw, hw,
                     -1.0 + self.nd_down.getPos()[2],
                     1.0 + self.nd_up.getPos()[2]))
        Dialog.set_autoplace_offset_function(lambda: self.nd_up.getPos())

        task = base.taskMgr.add(self._loop, "cutscene")
        task.prev_time = 0.0
        self._subtasks = []


    def _loop (self, task):

        if not self.alive:
            return task.done

        dt = task.time - task.prev_time
        task.prev_time = task.time

        if self.active != self._prev_active:
            kill_tasks(self._subtasks)
            if self.active:
                t1 = node_fade_to(self.nd_up, 1.0, 1.0, 0.0,
                                  startf=self.nd_up.show,
                                  timer=self.world)
                t2 = node_slide_to(self.nd_up,
                                   Point3(0.0, 0.0, -self._bar_height), 1.0,
                                   timer=self.world)
                t3 = node_fade_to(self.nd_down, 1.0, 1.0, 0.0,
                                  startf=self.nd_down.show,
                                  timer=self.world)
                t4 = node_slide_to(self.nd_down,
                                   Point3(0.0, 0.0, self._bar_height), 1.0,
                                   timer=self.world)
            else:
                t1 = node_fade_to(self.nd_up, 0.0, 1.0,
                                  endf=self.nd_up.hide,
                                  timer=self.world)
                t2 = node_slide_to(self.nd_up,
                                   Point3(0.0, 0.0, 0.0), 1.0,
                                   timer=self.world)
                t3 = node_fade_to(self.nd_down, 0.0, 1.0,
                                  endf=self.nd_down.hide,
                                  timer=self.world)
                t4 = node_slide_to(self.nd_down,
                                   Point3(0.0, 0.0, 0.0), 1.0,
                                   timer=self.world)
            self._subtasks = [t1, t2, t3, t4]

        self._prev_active = self.active
        return task.cont


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        Dialog.set_screen_size_function(None)
        Dialog.set_autoplace_offset_function(None)
        self.node.removeNode()


class FadeScreen (object):

    def __init__ (self, world, pnode):

        self.world = world

        self.node = pnode.attachNewNode("fade-screen")
        self.node.show()

        hw = base.aspect_ratio
        self._black = make_image(
            "images/ui/black.png", size=(hw * 2, 2.0),
            pos=Point3(0.0, 0.0, 0.0),
            parent=self.node)

        self._fade_task = None

        self.alive = True


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        kill_tasks(self._fade_task)
        self._fade_task = None
        self.node.removeNode()


    def fade_in (self, duration=0.0, startalpha=1.0, endalpha=0.0):

        kill_tasks(self._fade_task)
        self._fade_task = node_fade_to(self.node, duration=duration,
                                       startalpha=startalpha,
                                       endalpha=endalpha,
                                       startf=self.node.show,
                                       endf=(self.node.hide if endalpha == 0.0 else None),
                                       timer=self.world)


    def fade_out (self, duration=0.0, startalpha=0.0, endalpha=1.0):

        kill_tasks(self._fade_task)
        self._fade_task = node_fade_to(self.node, duration=duration,
                                       startalpha=startalpha,
                                       endalpha=endalpha,
                                       startf=self.node.show,
                                       endf=(self.node.hide if endalpha == 0.0 else None),
                                       timer=self.world)


class ActionPause (DirectObject):

    def __init__ (self, world, pnode):

        DirectObject.__init__(self)

        self.world = world

        self.node = pnode.attachNewNode("pause")
        self.node.hide()

        self._keyseq_activate = "escape"
        self.accept(self._keyseq_activate, self._activate)

        self.active = None
        self._menu = None

        self._can_resume = True
        self._player_shotdown = False

        self.set_active(False)

        self.alive = True


    def destroy (self):

        if not self.alive:
            return
        self.ignoreAll()
        base.remove_priority("pause")
        if self._menu:
            self._menu.destroy()
        self.node.removeNode()
        self.alive = False


    def _activate (self):

        if not base.challenge_priority("pause", self._keyseq_activate):
            return
        self.set_active(True)


    def set_active (self, active, canresume=True, desat=0.6):

        if active == self.active:
            return

        if self._menu:
            self._menu.destroy()

        if active == True:
            self.active = True
            base.set_priority("pause", self._keyseq_activate, 0)
            self.node.show()
            base.set_desaturation_strength(desat)
            base.center_mouse_pointer()
            self._can_resume = canresume
            self._menu = self._make_menu()
            self._loop_stage = "pause"
            self._menu_task = base.taskMgr.add(self._menu_loop, "pause-menu")
        else:
            self.active = False
            base.set_priority("pause", self._keyseq_activate, 30)
            base.set_desaturation_strength(0.0)
            base.center_mouse_pointer()
            self.node.hide()


    def set_player_shotdown (self, shotdown):

        self._player_shotdown = shotdown


    def _menu_loop (self, task):

        if not self.alive:
            return task.done

        if not self._menu.alive:
            sname, sargs = self._menu.selection()
            if not sname:
                self.set_active(False)
            elif sname == "restart":
                assert self.world.mission is not None
                self.world.destroy()
                self.destroy()
                self.world.mission.end(exitf=False, state="restart")
                return task.done
            elif sname == "quit":
                assert self.world.mission is not None
                self.world.destroy()
                self.destroy()
                self.world.mission.end(exitf=False, state="quit")
                return task.done
            elif sname == "proceed":
                assert self.world.mission is not None
                self.world.destroy()
                self.destroy()
                self.world.mission.end(exitf=False, state="proceed")
                return task.done
            elif sname == "quit-game":
                if self.world.mission is not None:
                    self.world.destroy()
                    self.destroy()
                    self.world.mission.end(exitf=False, state="quit-game")
                    return task.done
                else:
                    report(_("Quitting game from pause."))
                    exit(1)

        return task.cont


    def _make_menu (self):

        wrestart = (self.world.mission is not None)
        wquit = (self.world.mission is not None)
        if self._player_shotdown:
            if self.world.mission and self.world.mission.in_sequence:
                wproceed = True
                menu = ShotdownInseqMenu(wrestart=wrestart,
                                         wquit=wquit, wproceed=wproceed,
                                         parent=self.node)
            else:
                menu = ShotdownNoseqMenu(wrestart=wrestart, wquit=wquit,
                                         parent=self.node)
        else:
            wcontrols = True
            wquitgame = True
            menu = PauseMenu(wresume=self._can_resume, wrestart=wrestart,
                             wcontrols=wcontrols,
                             wquit=wquit, wquitgame=wquitgame,
                             parent=self.node)
        return menu


