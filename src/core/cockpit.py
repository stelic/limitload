# -*- coding: UTF-8 -*-

from bisect import bisect
from math import radians, degrees, pi, sin, cos, tan, acos, atan, atan2
from math import sqrt, log

from pandac.PandaModules import VBase2, Vec3, Vec4, Point2, Point3, Mat4, Quat
from pandac.PandaModules import Point3D
from pandac.PandaModules import NodePath, LODNode, PerspectiveLens, Shader
from pandac.PandaModules import TransparencyAttrib, LightRampAttrib, ColorBlendAttrib
from pandac.PandaModules import AmbientLight, DirectionalLight, PointLight
from pandac.PandaModules import Texture, BitMask32

from src import OUTSIDE_FOV, COCKPIT_FOV
from src import GLSL_PROLOGUE
from src import list_dir_files, join_path
from src.core.bomb import Dropper
from src.core.fire import MuzzleFlash
from src.core.jammer import Jammer
from src.core.light import AutoPointLight, PointOverbright
from src.core.misc import clamp, clampn, pclamp, unitv, vtod, ptod, qtod, sign
from src.core.misc import to_navhead, hpr_to, norm_ang_delta, vectohpr, hprtovec
from src.core.misc import AutoProps, SimpleProps
from src.core.misc import rgba, node_fade_to
from src.core.misc import make_image, make_text, update_text
from src.core.misc import make_frame, make_quad, make_raw_quad
from src.core.misc import load_model, set_texture, texstage_color
from src.core.misc import font_scale_for_ptsize, vert_to_horiz_fov
from src.core.misc import map_pos_to_screen
from src.core.misc import max_intercept_range, intercept_time
from src.core.misc import remove_subnodes
from src.core.misc import intl01vr, intl01v
from src.core.misc import TimeAveraged
from src.core.misc import dbgval
from src.core.plane import Plane
from src.core.podrocket import PodLauncher
from src.core.rocket import Launcher
from src.core.sensor import Contact, DataLink
from src.core.shader import make_shader, printsh, make_text_shader
from src.core.shader import make_shadow_shader
from src.core.shader import make_frag_outputs
from src.core.shell import Cannon
from src.core.sound import Sound2D
from src.core.table import Table1
from src.core.transl import *


DELTA_FOV = COCKPIT_FOV - OUTSIDE_FOV


def select_des (langdes, cpitdes, cpitlang):

    if not cpitlang:
        return langdes
    else:
        return cpitdes.get(cpitlang, langdes)


class Helmet (object):

    def __init__ (self, player):

        self._lang = "ru"

        self.world = player.ac.world
        self.player = player

        self.active = False
        self._prev_active = False
        self._prev_player_control_level = None

        self._screen_distance = 0.10
        self._screen_indicator_scale = 0.0006
        u = self._screen_indicator_scale * self._screen_distance
        uf = self._screen_indicator_scale * 100

        self.node = base.helmet_root.attachNewNode("helmet-root")
        #self.node.setTransparency(TransparencyAttrib.MAlpha)
        #self.node.setSa(0.8)
        #self.node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
        #shader = make_shader()
        #self.node.setShader(shader)
        self._camera = base.helmet_camera
        self._camlens = self._camera.node().getLens()

        #self._model = load_model("foo")
        #self._model.reparentTo(self.node)
        #self._model.setPos(0, 0, 0)
        #self._model.hide()

        self.node2d = self.world.overlay_root.attachNewNode("player-helmet")

        #self._font = "fonts/DejaVuSans-Bold.ttf"
        self._font = "fonts/red-october-regular.otf"
        #self._font = "fonts/DidactGothic.ttf"
        self._helmet_color = rgba(255, 0, 0, 1.0)

        self._screen_node = self.node.attachNewNode("screen")
        shader = make_shader(glow=rgba(255, 255, 255, 0.6), modcol=True)
        self._screen_node.setShader(shader)
        #self._screen_node.setDepthTest(False)
        self._screen_node.setDepthWrite(False)
        self._screen_node.setMaterialOff(True)
        self._text_shader = make_text_shader(glow=rgba(255, 255, 255, 0.4),
                                             shadow=True)

        # View tracking.
        self.view_contact = None
        self.view_body = None
        self._prev_view_contact = None

        # Targeting.
        self.target_contact = None
        self.target_body = None
        self.target_offset = None
        self.target_hitbox = None
        self._prev_cycle_contact_set = {}
        self._cycle_waypoint_target_time_pressed = None
        self._cycle_waypoint_target_deselect_delay = 0.2
        self._cycle_waypoint_target_immediate_deselect = False
        self._cycle_tag_contact_set = set()
        self._wait_cycle_tag = 0.0
        self._cycle_tag_period = 1.13
        self._target_section_index = 0

        # Targeting visuals.
        self._target_node = self._screen_node.attachNewNode("target")
        #self._target_node.setSa(0.5)
        self._target_selected_node = self._target_node.attachNewNode("target-select")
        self._target_selected_other_node = make_image(
            "images/cockpit/cockpit_mig29_helmet_target_selected_a3.png",
            size=128*u, filtr=False, parent=self._target_selected_node)
        self._target_selected_friendly_node = make_image(
            "images/cockpit/cockpit_mig29_helmet_target_selected_friendly.png",
            size=128*u, filtr=False, parent=self._target_selected_node)
        self._target_locked_node = make_image(
            "images/cockpit/cockpit_mig29_helmet_target_locked_a4.png",
            size=128*u, filtr=False, parent=self._target_node)
        self._target_locking_rate = 0.1
        #self._launch_auth_text = make_text(
                #text=select_des(_("LA"), {"ru": u"ПР"}, self._lang),
                #width=0.3, pos=Point3(48*u, 0.0, 48*u),
                #font=self._font, size=8*uf, color=self._helmet_color,
                #align="c", anchor="mc", parent=self._target_node)
        self._view_node = self._screen_node.attachNewNode("view")
        self._target_visual_node = make_image(
            "images/cockpit/cockpit_mig29_helmet_target_visual_tex.png",
            size=128*u, filtr=False, parent=self._view_node)
        self._target_visual_scale_duration = 0.4
        self._target_visual_scale_remtime = None

        # Targeting sounds.
        self._locking_weapon_sound = Sound2D(
            path="audio/sounds/flight-locking-target.ogg", loop=True,
            world=self.world, pnode=self.node2d, volume=0.2, fadetime=0.01)
        self._ready_weapon_sound = Sound2D(
            path="audio/sounds/flight-lock-target.ogg", loop=True,
            world=self.world, pnode=self.node2d, volume=0.2, fadetime=0.01)

        # G-factor effects.
        self._gfac_apply = True
        self._gfac_limup0 = 5.0
        self._gfac_limup1 = 8.0
        self._gfac_limlw0 = -2.0
        self._gfac_limlw1 = -4.0
        self._gfac_visspdfac_loss = 0.2
        self._gfac_visspdfac_recv = 0.4
        self._gfac_visfac_up = 0.0
        self._gfac_visfac_lw = 0.0
        #self._gfac_brtspdfac_loss = 0.1
        #self._gfac_brtspdfac_recv = 0.2
        #self._gfac_brtfac_up = 0.0
        #self._gfac_brtvol_min = 0.05
        #self._gfac_breathing_sound = Sound2D(
            #path="audio/sounds/flight-breathing.ogg", loop=True,
            #world=self.world, pnode=self.node2d,
            #volume=self._gfac_brtvol_min, play=True)
        self._wait_gfactor = 0.0
        self._gfactor_period = 0.053

        # Active navpoints.
        self._wait_actnav = 0.0
        self._actnav_period = 0.51
        self._actnav_names = set()
        self._actnav_text = None
        self._actnav_text_size = 10.0
        self._actnav_text_color = rgba(255, 0, 0, 1.0)
        self._actnav_text_shcolor = rgba(0, 0, 0, 1.0)
        self._actnav_text_sel_color = rgba(255, 255, 255, 1.0)
        self._actnav_seldelay = 0.5
        self._actnav_clrdelay = 5.0
        self._actnav_selnp = AutoProps()

        # Families which prevent player from jumping through a navpoint
        # when they target him or his allies.
        self._no_navjump_when_target_families = (
            "plane",
            "rocket",
        )
        self._no_navjump_when_attacked_families = (
            "plane",
        )
        self._navjump_clear_delay = 10.0
        self._navjump_wait_clear = 5.0 # min wait at zone start

        self._deactivate()

        self.alive = True
        base.taskMgr.add(self._loop, "helmet-loop", sort=-7)
        # ...should come before cockpit and player loops.


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        #self._pointer.detachNode()
        for node in self.node.getChildren():
            node.removeNode()
        self.node.removeNode()
        self.node2d.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.player.alive or not self.player.ac.alive:
            self.destroy()
            return task.done

        dt = self.world.dt

        if self._prev_active != self.active:
            self._prev_active = self.active
            if self.active:
                self._activate()
            else:
                self._deactivate()

        if self.active:
            self._update_view(dt)
            self._update_targeting(dt)
            self._update_cycle_tag(dt)

        self._update_navjumps(dt)

        # Always on, must track state.
        self._update_gfactor(dt)

        self._prev_player_control_level = self.world.player_control_level
        return task.cont


    def _activate (self):

        self._camera.node().setActive(True)
        self.node.show()
        self.node2d.show()


    def _deactivate (self):

        self._camera.node().setActive(False)
        self.node.hide()
        self.node2d.hide()


    def _update_view (self, dt):

        self._camlens.setMinFov(self.player.headchaser.fov)


    def _project_to_visor (self, wnode, offset=None):

        if offset is not None:
            hpos = self.player.headchaser.node.getRelativePoint(wnode, offset)
        else:
            hpos = wnode.getPos(self.player.headchaser.node)
        vpos = Point3(unitv(hpos) * self._screen_distance)
        return vpos


    def _set_on_visor (self, node, pos=Point3(), updir=Vec3(0, 0, 1)):

        node.setPos(pos)
        node.lookAt(pos * 1.1, updir)


    def _update_targeting (self, dt):

        input_deselect = (
            (self._cycle_waypoint_target_time_pressed is not None and
             self.world.time - self._cycle_waypoint_target_time_pressed >
                 self._cycle_waypoint_target_deselect_delay) or
            self._cycle_waypoint_target_immediate_deselect)
        if self._cycle_waypoint_target_immediate_deselect:
            self._cycle_waypoint_target_time_pressed = None
            self._cycle_waypoint_target_immediate_deselect = False

        if (not self.target_contact or
            not self.target_contact.body.alive or
            self.target_contact not in self.player.ac.sensorpack.contacts() or
            not self.target_contact.trackable() or
            self.target_contact.body.shotdown or
            input_deselect):
            self.target_contact = None
            self.target_body = None

        if (not self.view_contact or
            not self.view_contact.body.alive or
            self.view_contact not in self.player.ac.sensorpack.contacts() or
            not self.view_contact.firsthand or
            input_deselect):
            self.view_contact = None
            self.view_body = None

        if (self.view_contact and
            self.view_contact.trackable() and
            not self.target_contact):
            self.target_contact = self.view_contact
            self.target_body = self.view_body

        if not self.target_contact and not self.view_contact:
            self._prev_cycle_contact_set = {}

        play_locking_sound = False
        play_ready_sound = False

        if self.target_contact:
            vpos = self._project_to_visor(self.target_contact.body.node,
                                          self.target_offset)
            self._set_on_visor(self._target_node, vpos)

            self._target_selected_node.show()
            self._target_locked_node.hide()

            if self.player.input_select_weapon >= 0:
                wp = self.player.weapons[self.player.input_select_weapon]
                if isinstance(wp.handle, Launcher) and wp.handle.mtype.seeker:
                    launcher = wp.handle
                    rst, rnds = launcher.ready(target=self.target_contact.body)
                    if rst in ("locking", "locked"):
                        if int(self.world.time / self._target_locking_rate) % 2 == 0:
                            self._target_locked_node.show()
                        else:
                            self._target_locked_node.hide()
                        play_locking_sound = True
                    elif rst == "ready":
                        self._target_locked_node.show()
                        play_ready_sound = True
                #elif isinstance(wp.handle, Dropper):

            self._choose_selection_reticle(self.target_contact)

            self.player.ac.target = self.target_contact.body
        else:
            self._target_selected_node.hide()
            self._target_locked_node.hide()

            self.player.ac.target = None

        if self.view_contact:
            vpos = self._project_to_visor(self.view_contact.body.node,
                                          self.target_offset)
            self._set_on_visor(self._view_node, vpos)
        if self.view_contact is not self._prev_view_contact:
            if self.view_contact and self.view_contact is not self.target_contact:
                ret = map_pos_to_screen(self.world.camera,
                                        self.view_contact.body.node,
                                        scrnode=self.world.overlay_root)
                tpos, back = ret
                if not back and abs(tpos[0]) < 0.2 and abs(tpos[2]) < 0.2:
                    self._target_visual_scale_remtime = self._target_visual_scale_duration
                    self._prev_view_contact = self.view_contact
                else:
                    self._target_visual_scale_remtime = None
            else:
                self._prev_view_contact = self.view_contact
                self._target_visual_scale_remtime = None
        if self._target_visual_scale_remtime:
            self._target_visual_scale_remtime -= dt
            if self._target_visual_scale_remtime > 0.0:
                self._target_visual_node.show()
                tvsc = self._target_visual_scale_remtime / self._target_visual_scale_duration
                self._target_visual_node.setScale(tvsc)
            else:
                self._target_visual_node.hide()
                self._target_visual_scale_remtime = None
        else:
            self._target_visual_node.hide()

        self._locking_weapon_sound.set_state(play_locking_sound)
        self._ready_weapon_sound.set_state(play_ready_sound)


    def _update_cycle_tag (self, dt):

        self._wait_cycle_tag -= dt
        if self._wait_cycle_tag <= 0.0:
            self._wait_cycle_tag += self._cycle_tag_period
            new_cycle_tag_contact_set = set()
            for con in self._cycle_tag_contact_set:
                if con in self.player.ac.sensorpack.contacts():
                    new_cycle_tag_contact_set.add(con)
            self._cycle_tag_contact_set = new_cycle_tag_contact_set


    def _update_gfactor (self, dt):

        self._wait_gfactor -= dt
        if self._wait_gfactor <= 0.0:
            adt = self._gfactor_period - self._wait_gfactor
            self._wait_gfactor += self._gfactor_period
            gfac = self.player.ac.gfactor()

            visfac_up_fin = 0.0
            visfac_lw_fin = 0.0
            if gfac > self._gfac_limup0:
                duplw = (self._gfac_limup1 - self._gfac_limup0)
                visfac_up_fin = (gfac - self._gfac_limup0) / duplw
                visfac_up_fin = clamp(visfac_up_fin, 0.0, 1.0)
            elif gfac < self._gfac_limlw0:
                duplw = (self._gfac_limlw1 - self._gfac_limlw0)
                visfac_lw_fin = (gfac - self._gfac_limlw0) / duplw
                visfac_lw_fin = clamp(visfac_lw_fin, 0.0, 1.0)
            if visfac_up_fin > self._gfac_visfac_up:
                visspdfac_up = self._gfac_visspdfac_loss
            else:
                visspdfac_up = self._gfac_visspdfac_recv
            visspd_up = (visfac_up_fin - self._gfac_visfac_up) * visspdfac_up
            self._gfac_visfac_up += visspd_up * adt
            if visfac_lw_fin > self._gfac_visfac_lw:
                visspdfac_lw = self._gfac_visspdfac_loss
            else:
                visspdfac_lw = self._gfac_visspdfac_recv
            visspd_lw = (visfac_lw_fin - self._gfac_visfac_lw) * visspdfac_lw
            self._gfac_visfac_lw += visspd_lw * adt
            visfac = max(self._gfac_visfac_up, self._gfac_visfac_lw)
            outrad_ds = sqrt(2.0) * (1.0 - visfac)
            if self._gfac_visfac_up > self._gfac_visfac_lw:
                ifac0_ds = visfac**0.7
                ifac1_ds = ifac0_ds + (1.0 - ifac0_ds) * sin(visfac * pi * 0.5)
            else:
                ifac0_ds = 0.0
                ifac1_ds = 0.0
            rad_desat_spec = Vec4(outrad_ds, ifac0_ds, ifac1_ds, 0.0)
            outrad_dk = sqrt(2.0) * (1.0 - visfac)
            ifac0_dk = visfac**4.0
            ifac1_dk = ifac0_dk + (1.0 - ifac0_dk) * sin(visfac * pi * 0.5)**4.0
            colred = 0.0 if self._gfac_visfac_up > self._gfac_visfac_lw else 1.0
            rad_darken_rad_spec = Vec4(outrad_dk, ifac0_dk, ifac1_dk, colred)
            timeang = 2 * pi * self.world.time
            dradampl = 0.05 + 0.01 * sin(timeang / 1.0)
            dradfreq = 8.0
            dradphase = timeang / 4.0
            rad_darken_ang_spec = Vec4(dradampl, dradfreq, dradphase, 0.0)
            if self._gfac_apply:
                base.set_radial_desaturation(rad_desat_spec)
                base.set_radial_darkening(rad_darken_rad_spec, rad_darken_ang_spec)

            #brtfac_up_fin = 0.0
            #if gfac > self._gfac_limup0:
                #duplw = (self._gfac_limup1 - self._gfac_limup0)
                #brtfac_up_fin = (gfac - self._gfac_limup0) / duplw
                #brtfac_up_fin = clamp(brtfac_up_fin, 0.0, 1.0)
            #if brtfac_up_fin > self._gfac_brtfac_up:
                #brtspdfac_up = self._gfac_brtspdfac_loss
            #else:
                #brtspdfac_up = self._gfac_brtspdfac_recv
            #brtspd_up = (brtfac_up_fin - self._gfac_brtfac_up) * brtspdfac_up
            #self._gfac_brtfac_up += brtspd_up * adt
            #brtfac = self._gfac_brtfac_up
            #brtvol = self._gfac_brtvol_min * (1.0 - brtfac) + 1.0 * brtfac
            #if self._gfac_apply:
                #self._gfac_breathing_sound.set_volume(brtvol)


    def set_physio_effects (self, active):

        if active:
            self._gfac_apply = True

        else:
            self._gfac_apply = False

            rad_desat_spec = Vec4(sqrt(2.0), 0, 0, 0)
            base.set_radial_desaturation(rad_desat_spec)
            rad_darken_rad_spec = Vec4(sqrt(2.0), 0, 0, 0)
            rad_darken_ang_spec = Vec4(0, 0, 0, 0)
            base.set_radial_darkening(rad_darken_rad_spec, rad_darken_ang_spec)

            #self._gfac_breathing_sound.set_volume(0.0)


    def _update_navjumps (self, dt):

        if self.player.ac.onground: # outside, to react on runway hops
            self._navjump_wait_clear = self._navjump_clear_delay

        self._wait_actnav -= dt
        self._navjump_wait_clear -= dt
        if self._wait_actnav <= 0.0:
            self._wait_actnav += self._actnav_period
            if not self._navjump_allowed() or self.world.player_control_level > 1:
                self._navjump_wait_clear = self._navjump_clear_delay
            if self._navjump_wait_clear <= 0.0:
                actnps = self.player.cockpit.active_navpoints()
            else:
                actnps = []
            actnp_names = set(np.name for np in actnps)
            if self._actnav_names != actnp_names:
                actnps.sort(key=lambda np: np.longdes)
                self._actnav_textnds = []
                self._actnav_selnp = AutoProps()
                def actf (ci):
                    if ci != self._actnav_selnp.index:
                        if self._actnav_selnp.index is not None:
                            textnd = self._actnav_textnds[self._actnav_selnp.index]
                            update_text(textnd, color=self._actnav_text_color)
                        self._actnav_selnp.index = ci
                        self._actnav_selnp.time0 = self.world.wall_time
                        textnd = self._actnav_textnds[self._actnav_selnp.index]
                        update_text(textnd, color=self._actnav_text_sel_color)
                    elif self._actnav_selnp.time0 + self._actnav_seldelay <= self.world.wall_time:
                        self._jump_to_zone(actnps[ci].tozone, actnps[ci].exitf)
                self.player.set_choice("nav", len(actnps), actf, priority=10)
                if self._actnav_text is not None:
                    self._actnav_text.removeNode()
                    self._actnav_text = None
                if actnp_names:
                    text = select_des(_("Autopilot:"), {"ru": u"Автопилот:"},
                                      self._lang)
                    self._actnav_text = make_text(
                        text=text,
                        width=1.0, pos=Point3(-0.80, 0.0, -0.10),
                        font=self._font, size=self._actnav_text_size,
                        color=self._actnav_text_color,
                        shcolor=self._actnav_text_shcolor,
                        align="t", anchor="tl",
                        shader=self._text_shader,
                        parent=self.node2d)
                    dz = font_scale_for_ptsize(self._actnav_text_size) * 1.5
                    for i, np in enumerate(actnps):
                        keys = self.player.bindings["choice-%d" % (i + 1)].seqs
                        keyfmt = ", ".join(keys)
                        text = (_("[%(key)s] %(navpoint)s") %
                                dict(key=keyfmt, navpoint=np.longdes))
                        textnd = make_text(
                            text=text,
                            width=1.0, pos=Point3(0.0, 0.0, -dz * (i + 1)),
                            font=self._font, size=self._actnav_text_size,
                            color=self._actnav_text_color,
                            shcolor=self._actnav_text_shcolor,
                            align="t", anchor="tl",
                            shader=self._text_shader,
                            parent=self._actnav_text)
                        self._actnav_textnds.append(textnd)
                self._actnav_names = actnp_names
            elif self._actnav_selnp.index is not None:
                if self._actnav_selnp.time0 + self._actnav_clrdelay <= self.world.wall_time:
                    textnd = self._actnav_textnds[self._actnav_selnp.index]
                    update_text(textnd, color=self._actnav_text_color)
                    self._actnav_selnp = AutoProps()


    def _jump_to_zone (self, zoneid, exitf=None):

        if zoneid:
            # Configure plane for jump.
            self.player.input_air_brake = False
            self.player.input_flaps = False
            self.player.input_landing_gear = False
            self.player.input_wheel_brake = False

            m = self.world.mission
            if m and not m.switching_zones():
                m.switch_zone(zoneid, exitf=exitf)


    def _navjump_allowed (self):

        acp = self.player.ac
        friendlies = self.world.get_friendlies(
            self._no_navjump_when_attacked_families, acp.side)
        for family in self._no_navjump_when_target_families:
            for body in self.world.iter_bodies(family):
                if not body.alive:
                    continue
                if body.target in friendlies and body is not acp:
                    return False

        return True


    def cycle_waypoint_target_init (self):

        if self.player.cockpit.hud_mode in ("atk", "gnd"):
            self._cycle_waypoint_target_time_pressed = self.world.time


    def cycle_waypoint_target (self):

        if self.world.action_chasers:
            self.world.clear_action_chasers()
            self._cycle_waypoint_target_time_pressed = None
        elif self.player.cockpit.hud_mode == "nav":
            self.player.cockpit.cycle_waypoint()
            self._cycle_waypoint_target_time_pressed = None
        elif self.player.cockpit.hud_mode in ("atk", "gnd"):
            if self._cycle_waypoint_target_time_pressed is not None:
                time_pressed = self._cycle_waypoint_target_time_pressed
                self._cycle_waypoint_target_time_pressed = None
                if (self.world.time - time_pressed >
                    self._cycle_waypoint_target_deselect_delay):
                    return
            self.cycle_target()


    def deselect_target (self):

        if self.player.cockpit.hud_mode in ("atk", "gnd"):
            self._cycle_waypoint_target_immediate_deselect = True


    def cycle_target (self):

        if not self.active:
            return

        if self.player.input_select_weapon < 0:
            return
        wp = self.player.weapons[self.player.input_select_weapon]

        cycle_contact_set = {}
        all_plock = True
        for con in self.player.ac.sensorpack.contacts():
            if not (con.trackable() or con.firsthand) or con.body.shotdown:
                continue
            if con.body.family in wp.against():
                ret = map_pos_to_screen(self.world.camera, con.body.node,
                                        scrnode=self.world.overlay_root)
                tpos, back = ret
                hw = base.aspect_ratio
                if (not con.trackable() and
                    (back or abs(tpos[0]) > hw or abs(tpos[2]) > 1.0) and
                    con not in self._cycle_tag_contact_set):
                    continue
                if not back:
                    cdist = tpos.length()
                else:
                    cdist = 2 * hw + self.player.ac.dist(con.body)
                prev_con_spec = self._prev_cycle_contact_set.get(con)
                plock = prev_con_spec[1] if prev_con_spec else False
                track = con.trackable()
                cycle_contact_set[con] = [cdist, plock, track]
                if not plock:
                    all_plock = False
        if all_plock:
            for con, con_spec in cycle_contact_set.iteritems():
                con_spec[1] = False

        if cycle_contact_set:
            cycle = sorted(cycle_contact_set.items(), key=lambda x: x[1][0])
            skip_con = None
            if len(cycle_contact_set) > 1:
                #skip_con = self.target_contact
                skip_con = self.view_contact
            sel_con = None
            for con, (cdist, plock, track) in cycle:
                if not plock and con is not skip_con:
                    sel_con = con
                    sel_con_track = track
                    break
            if sel_con:
                if sel_con_track:
                    self.target_contact = sel_con
                    self.target_body = sel_con.body
                    self.cycle_target_section(reset=True)
                    self._choose_selection_reticle(sel_con)
                else:
                    self.target_contact = None
                    self.target_body = None
                self.view_contact = sel_con
                self.view_body = sel_con.body
                cycle_contact_set[sel_con][1] = True
                self._cycle_tag_contact_set.add(sel_con)
            else:
                self.target_contact = None
                self.target_body = None
                self.view_contact = None
                self.view_body = None
                cycle_contact_set = {}

        self._prev_cycle_contact_set = cycle_contact_set


    def cycle_target_section (self, reset=False):

        if not self.active or not self.target_contact:
            return

        target = self.target_contact.body
        self.target_offset = None
        self.target_hitbox = None
        selhitboxes = [x for x in target.hitboxes if x.selectable]
        if selhitboxes:
            if not reset:
                self._target_section_index += 1
                if self._target_section_index >= len(selhitboxes):
                    self._target_section_index = 0 #-1
            else:
                self._target_section_index = 0 #-1
            secname = None
            if self._target_section_index >= 0:
                hbx = selhitboxes[self._target_section_index]
                self.target_offset = hbx.center
                self.target_hitbox = hbx
                secname = hbx.name
            #print "--cycle-target-section", target.species, secname


    def _choose_selection_reticle (self, contact):

        allied_sides = self.world.get_allied_sides(self.player.ac.side)
        if contact.side in allied_sides:
            self._target_selected_friendly_node.show()
            self._target_selected_other_node.hide()
        else:
            self._target_selected_friendly_node.hide()
            self._target_selected_other_node.show()


class Cockpit (object):

    _shader_cache = {}

    def __init__ (self, player, pos, mfspec, headpos, downto, arenaedge):

        self._lang = "ru"

        self.player = player
        self.world = player.ac.world

        self.node = base.cockpit_root.attachNewNode("cockpit-root")
        self._camera = base.cockpit_camera
        self._camlens = self._camera.node().getLens()
        if base.with_cockpit_shadows:
            self.shadow_node = base.cockpit_shadow_root.attachNewNode("shadow-scene")
            self._shadow_camera = base.cockpit_shadow_camera
            self._shadow_texture = base.cockpit_shadow_texture
            self._shadow_area_size = base.cockpit_shadow_area_size
            self._shadow_area_dist = base.cockpit_shadow_area_dist
            shadowmap = self._shadow_texture
        else:
            shadowmap = None

        self._model = load_model(
            path="models/aircraft/mig29/3dcockpit_mig29.egg",
            texture="models/aircraft/mig29/cockpit_mig29_tex.png",
            normalmap="models/aircraft/mig29/cockpit_mig29_nm.png",
            glowmap="models/aircraft/mig29/cockpit_mig29_gw.png",
            glossmap="models/aircraft/mig29/cockpit_mig29_gls.png",
            shadowmap=shadowmap)
        if base.with_cockpit_shadows:
            self._shadow_model = load_model(
                path="models/aircraft/mig29/3dcockpit_mig29-shadow.egg")

        self._warning_lamps = self._model.find("**/lamp_warnings")
        if not self._warning_lamps.isEmpty():
            set_texture(self._warning_lamps,
                texture="images/cockpit/cockpit_mig29_lamp_warnings_tex.png",
                normalmap="images/_normalmap_none.png",
                glossmap="images/cockpit/cockpit_mig29_lamp_gls.png")
        self._sqr_screen = self._model.find("**/sqr_screen")
        if not self._sqr_screen.isEmpty():
            set_texture(self._sqr_screen,
                texture="images/cockpit/cockpit_mig29_lamp_orange_tex.png",
                normalmap="images/_normalmap_none.png",
                glossmap="images/cockpit/cockpit_mig29_lamp_gls.png")
        self._fuelpanel_lamps = self._model.find("**/fuelpanel_lamps")
        if not self._fuelpanel_lamps.isEmpty():
            set_texture(self._fuelpanel_lamps,
                texture="images/cockpit/cockpit_mig29_lamp_red_tex.png",
                normalmap="images/_normalmap_none.png",
                glossmap="images/cockpit/cockpit_mig29_lamp_gls.png")

        #self._model.ls()
        self._model.reparentTo(self.node)
        self._model.setPos(pos - headpos)
        #self._model.hide()
        self._head_pos = headpos
        if base.with_cockpit_shadows:
            self._shadow_model.reparentTo(self.shadow_node)
            self._shadow_model.setPos(pos - headpos)
            #self._shadow_model.hide()

        # 0 - no aircraft model
        # 1 - world aircraft model
        # 2 - cockpit scene aircraft model
        self._ac_model_type = 2

        acp = self.player.ac
        ac_texture = acp.texture
        ac_normalmap = acp.normalmap or "images/_normalmap_none.png"
        #ac_glowmap = acp.glowmap or "images/_glowmap_none.png"
        ac_glowmap = "models/aircraft/_glowmap.png"
        ac_glossmap = acp.glossmap or "images/_glossmap_none.png"
        if self._ac_model_type == 2:
            self._ac_model = load_model(
                path="models/aircraft/mig29/mig29-player.egg",
                texture=ac_texture, normalmap=ac_normalmap,
                glowmap=ac_glowmap, glossmap=ac_glossmap,
                shadowmap=shadowmap)
            #self._ac_model.ls()
            self._ac_model.reparentTo(self.node)
            self._ac_model.setPos(-headpos)
            #self._ac_model.hide()
            self._ac_model_addons = {}
            for shandlers in (
                acp.launchers,
                acp.podlaunchers,
                acp.droppers,
                acp.tankers,
                acp.jammers,
            ):
                for shandler in shandlers:
                    shandler.set_store_model_report_functions(
                        self._register_addon_model, self._unregister_addon_model)
                    for smodel in shandler.store_models:
                        self._register_addon_model(smodel)
            #if base.with_cockpit_shadows:
            if False:
                self._shadow_ac_model = load_model(
                    path="models/aircraft/mig29/mig29-player.egg")
                self._shadow_ac_model.reparentTo(self.shadow_node)
                self._shadow_ac_model.setPos(-headpos)
                #self._shadow_ac_model.hide()

        #for handle in ("canopy_frame",):
            #geom_node = self._model.find("**/%s" % handle)
            #if not geom_node.isEmpty():
                #set_texture(geom_node,
                            #texture=ac_texture, normalmap=ac_normalmap,
                            #glowmap=ac_glowmap, glossmap=ac_glossmap,
                            #shadowmap=shadowmap)

        canopy_nodes = []
        for handle in ("canopy_glass", "canopy_windscreen"):
            geom_node = self._model.find("**/%s" % handle)
            if not geom_node.isEmpty():
                canopy_nodes.append(geom_node)
                geom_node.setTransparency(TransparencyAttrib.MAlpha)
                #geom_node.setSa(0.0)
                set_texture(geom_node,
                            texture="images/_glass_tex.png",
                            #normalmap="images/_glass_nm.png",
                            normalmap="images/_normalmap_none.png",
                            glowmap="images/_glass_gw.png",
                            glossmap="images/_glass_gls.png",
                            shadowmap=shadowmap)
            if base.with_cockpit_shadows:
                geom_node = self._shadow_model.find("**/%s" % handle)
                if not geom_node.isEmpty():
                    geom_node.removeNode()

        # Initialize shader inputs.
        self._shdinp = SimpleProps()

        self._shdinp.ambln = "INamblight"
        lt = AmbientLight(self._shdinp.ambln)
        lt.setColor(Vec4(1.0, 1.0, 1.0, 1.0))
        self._amblnd = NodePath(lt)
        self.node.setShaderInput(self._shdinp.ambln, self._amblnd)
        lt = AmbientLight(self._shdinp.ambln + "-instr-bright")
        lt.setColor(Vec4(1.0, 1.0, 1.0, 1.0))
        self._amblnd_instr_bright = NodePath(lt)
        lt = AmbientLight(self._shdinp.ambln + "-instr-dim")
        lt.setColor(Vec4(1.0, 1.0, 1.0, 1.0))
        self._amblnd_instr_dim = NodePath(lt)

        self._shdinp.sunln = "INsunlight"
        lt = DirectionalLight(self._shdinp.sunln)
        lt.setColor(Vec4(0.0, 0.0, 0.0, 1.0))
        self._sunlnd = NodePath(lt)
        self.node.setShaderInput(self._shdinp.sunln, self._sunlnd)

        self._shdinp.moonln = "INmoonlight"
        lt = DirectionalLight(self._shdinp.moonln)
        lt.setColor(Vec4(0.0, 0.0, 0.0, 1.0))
        self._moonlnd = NodePath(lt)
        self.node.setShaderInput(self._shdinp.moonln, self._moonlnd)

        self._shdinp.dirlns = (self._shdinp.sunln, self._shdinp.moonln)

        self._max_point_lights = 4
        self._shdinp.pntlns = []
        self._shdinp.pntlnds = []
        for il in xrange(self._max_point_lights):
            ln = "INpntlight%d" % il
            self._shdinp.pntlns.append(ln)
            lt = PointLight(ln)
            lt.setColor(Vec4(0.0, 0.0, 0.0, 1.0))
            lnd = NodePath(lt)
            self._shdinp.pntlnds.append(lnd)
            self.node.setShaderInput(ln, lnd)
        self._last_assigned_point_light_index = -1

        self._shdinp.pntobrn = "INoverbright"
        ob = PointLight(self._shdinp.pntobrn)
        ob.setColor(Vec4(0.0, 0.0, 0.0, 1.0))
        self.node.setShaderInput(self._shdinp.pntobrn, NodePath(ob))

        self._shdinp.camn = "INviewcam"
        self.node.setShaderInput(self._shdinp.camn, self._camera)

        self._shdinp.uvoffscn = "INuvoffscn"
        self.node.setShaderInput(self._shdinp.uvoffscn, Vec4(0.0, 0.0, 1.0, 1.0))

        self._shdinp.glowfacn = "INglowfac"
        self._shdinp.glowaddn = "INglowadd"
        self.node.setShaderInput(self._shdinp.glowfacn, 1.0)
        self.node.setShaderInput(self._shdinp.glowaddn, 0.0)

        if base.with_cockpit_shadows:
            self._shdinp.shadowrefn = "INshadowref"
            self.node.setShaderInput(self._shdinp.shadowrefn, self._shadow_camera)
            self._shadow_blend = 0.4
            self._shadow_blend_canopy = 0.8
            self._shdinp.shadowblendn = "INshadowblend"
            self.node.setShaderInput(self._shdinp.shadowblendn, self._shadow_blend)
            for node in canopy_nodes:
                node.setShaderInput(self._shdinp.shadowblendn, self._shadow_blend_canopy)
            self._shdinp.shadowdirlin = "INshadowdirli"
            self.node.setShaderInput(self._shdinp.shadowdirlin, 0)
        else:
            self._shdinp.shadowrefn = None
            self._shdinp.shadowblendn = None
            self._shdinp.shadowdirlin = None

        # Make global shader.
        make_shader_sunopq = lambda sunopq: make_shader(
            ambln=self._shdinp.ambln, dirlns=self._shdinp.dirlns,
            pntlns=self._shdinp.pntlns, camn=self._shdinp.camn,
            uvoffscn=self._shdinp.uvoffscn, pntobrn=self._shdinp.pntobrn,
            normal=True, glow=True, gloss=True,
            glowfacn=self._shdinp.glowfacn, glowaddn=self._shdinp.glowaddn,
            shadowrefn=self._shdinp.shadowrefn,
            shadowdirlin=self._shdinp.shadowdirlin,
            shadowblendn=self._shdinp.shadowblendn,
            shadowpush=0.0,
            sunopq=sunopq)
        shader = make_shader_sunopq(1.0)
        self.node.setShader(shader)
        if base.with_cockpit_shadows:
            shader = make_shadow_shader()
            self.shadow_node.setShader(shader)

        # Setup muzzle flashes.
        self._mfspec = mfspec
        if len(self._mfspec) != len(self.player.ac.cannons):
            raise StandardError("Different number of aircraft cannons and "
                                "cockpit muzzle flashes.")
        self._own_mflashes = set()
        for i in range(len(self._mfspec)):
            mshape, mscale, mpos, mhpr, mltpos = self._mfspec[i]
            cannon = self.player.ac.cannons[i]
            mpos1 = mpos - headpos
            #mltpos1 = mltpos - headpos
            mltpos1 = None
            mflash = MuzzleFlash(self, mpos1, mhpr, mltpos1, cannon.rate,
                                 shape=mshape, scale=mscale, manbin=True)
            mflash.node.setBin("background", 100)
            cannon.mflashes.append(mflash)
            self._own_mflashes.add(mflash)
            cannon.mpos_override = mpos

        # Waypoints.
        self._waypoints = {}
        self._waypoint_keys = []
        self._current_waypoint = None
        self._at_current_waypoint = False
        self._waypoint_wait_check = 0.0
        self._waypoint_check_period = 0.53

        # Navpoints.
        self._navpoints = {}
        self._navpoint_anon_counter = 0

        # Aerotow.
        self._aerotow_max_dist = 300.0
        self._aerotow_max_offbore = radians(15.0)
        self._aerotow_max_speed_diff = 20.0

        # Head moving.
        self._view_idle_hpr = Vec3(0.0, 0.0, 0.0)
        self._view_base_hpr = self._view_idle_hpr
        self._view_anim_hpr = Vec3(self._view_base_hpr)
        self._view_inert_hpr = Vec3()
        self._view_max_horiz_off = 150.0 # [deg]
        self._view_max_vert_off_up = 80.0 # [deg]
        self._view_horiz_shift_max = Point3(0.22, 0.10, 0.05)
        self._view_horiz_shift_start_off = 90.0 # [deg]
        assert self._view_horiz_shift_start_off <= self._view_max_horiz_off
        scdwp = self.node.getRelativePoint(self._model, downto)
        vdown = -atan2(scdwp[2], scdwp[1])
        self._view_max_vert_off_down = degrees(vdown)
        self._view_look_off = Vec3(0.0, 0.0, 0.0)
        self._view_look_speed = None
        self._view_look_acc = None
        self._view_look_max_speed = Vec3(120.0, 120.0, 0.0) # [deg]
        self._view_look_max_acc = Vec3(360.0, 360.0, 0.0) # [deg]
        self._view_look_snap_back_off_ref = Vec3(10.0, 10.0, 0.0) # [deg]
        self._view_look_snap_back_off_ref_lock_view = Vec3(20.0, 20.0, 0.0) # [deg]
        self._view_look_snap_back_vfov_ref = float(COCKPIT_FOV) # [deg]
        self._view_look_prev_body = None
        self._view_look_prev_base_hpr = self._view_base_hpr
        self._view_idle_fov_off = 0.0
        self._view_fov_off = 0.0
        self._view_min_fov_off = -30
        self._view_max_fov_off = +10
        self._view_aim_fov_off = -30
        assert self._view_aim_fov_off <= self._view_min_fov_off
        self._view_force_fov_off = None
        self._camlens.setMinFov(self.player.headchaser.fov)
        self._view_idle_fov_speed_time = 0.05
        self._view_fov_speed_time = self._view_idle_fov_speed_time
        self._view_fov_min_speed = 1.0 # [deg/s]
        self._view_min_outside_fov = max(OUTSIDE_FOV - 30, 20)
        self._view_max_outside_fov = min(OUTSIDE_FOV + 30, 90)
        self._view_ignore_lock = False
        self._view_prev_ignore_lock = self._view_ignore_lock
        self._view_accel_pst_fw_acc = 1.0 * self.world.absgravacc
        self._view_accel_pst_y_off = 0.0
        self._view_accel_pst_fov_off = 5
        self._view_accel_ngt_fw_acc = -1.0 * self.world.absgravacc
        self._view_accel_ngt_y_off = 0.0
        self._view_accel_ngt_fov_off = -5
        self._view_accel_averager = TimeAveraged(0.5, 0.0)

        # Aim zooming.
        self._aimzoom_target = None
        self._aimzoom_check_time = 0.5
        self._aimzoom_min_dist_size_fac = 10.0
        self._aimzoom_max_dist = 4000.0
        self._aimzoom_max_offbore = radians(3.0)
        self._aimzoom_fov_speed_time = 0.4
        self._aimzoom_time = 0.0

        # Setup instruments.
        self._txscmgr = TexsceneManager("cockpit")
        self._instr_update_fs = []
        self._instr_cleanup_fs = []
        self._instr_night_light_nodes = []
        self.has_radar = self._init_radar()
        self.has_hud = self._init_hud(make_shader_sunopq)
        self.has_warnrec = self._init_warnrec()
        self.has_power = self._init_power()
        self.has_weapons = self._init_weapons()
        self.has_boresight = self._init_boresight()
        self.has_compass = self._init_compass()
        self.has_fuelpanel = self._init_fuelpanel()
        self.has_tachometer = self._init_tachometer()
        self.has_airclock = self._init_airclock()
        self.has_radaraltimeter = self._init_radaraltimeter()
        self.has_aoa = self._init_aoa()
        self.has_machmeter = self._init_machmeter()
        self.has_adi = self._init_adi()
        self.has_vvi = self._init_vvi()
        self.has_bpa = self._init_bpa()
        self.has_mfd = self._init_mfd(arenaedge)
        self.has_countermeasures = self._init_countermeasures()
        self.has_rwr = self._init_rwr()
        self.has_imt = self._init_imt()
        self.has_mdi = self._init_mdi()
        #self.has_radar = False
        #self.has_hud = False
        #self.has_warnrec = False
        #self.has_power = False
        #self.has_weapons = False
        #self.has_boresight = False
        #self.has_compass = False
        #self.has_fuelpanel = False
        #self.has_tachometer = False
        #self.has_airclock = False
        #self.has_radaraltimeter = False
        #self.has_aoa = False
        #self.has_machmeter = False
        #self.has_adi = False
        #self.has_vvi = False
        #self.has_bpa = False
        #self.has_mfd = False
        #self.has_countermeasures = False
        #self.has_rwr = False
        #self.has_imt = False
        #self.has_mdi = False
        #for sc in self._txscmgr._scenes:
            #print "========================", sc.getName()
            #sc.analyze()

        # Setup instrument night lighting.
        self._instr_night_light_lim_sun_strength = 0.5
        self._instr_night_light_auto_on_off = True
        self._instr_night_light_on = False
        self.light_on_off(on=self._instr_night_light_on, auto=True)

        self._init_sounds()

        self.active = False
        self._prev_active = None
        self.node.hide()

        self._prev_player_control_level = None

        self._frame_created = self.world.frame

        self.alive = True
        base.taskMgr.add(self._loop, "cockpit-loop", sort=-6)
        # ...should come after helmet loop, before player loop.


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        for clf in self._instr_cleanup_fs:
            clf()
        for node in self.node.getChildren():
            node.removeNode()
        self.node.removeNode()
        if base.with_cockpit_shadows:
            self.shadow_node.removeNode()
        self._txscmgr.destroy()


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.player.alive or not self.player.ac.alive:
            self.destroy()
            return task.done

        if self._prev_active != self.active:
            self._prev_active = self.active
            if self.active:
                self._activate()
            else:
                self._deactivate()

        if not self.active:
            return task.cont

        dt = self.world.dt

        if self.active:
            self._update_lighting(dt)
            self._update_headpos(dt)
            self._update_waypoints(dt)
            self._update_aimzoom(dt)
            for upf in self._instr_update_fs:
                upf(dt)

        # Always on, must track state.
        self._update_sounds(dt)

        self._prev_player_control_level = self.world.player_control_level

        return task.cont


    def _activate (self):

        if self._ac_model_type != 1:
            self.player.ac.node.hide()

        self._camera.node().setActive(True)
        self.node.show()
        #self.node.setTransparency(TransparencyAttrib.MAlpha)
        #self.node.setSa(0.5)
        #for i in range(len(self.player.ac.cannons)):
            #cn, mpovr = self.player.ac.cannons[i], self._mfspec[i][1]
            #cn.mpos_override = mpovr
        if base.with_cockpit_shadows:
            self._shadow_camera.node().setActive(True)
            self.shadow_node.show()
        for cannon in self.player.ac.cannons:
            for mflash in cannon.mflashes:
                if mflash not in self._own_mflashes:
                    mflash.node.hide()
        self._txscmgr.activate()


    def _deactivate (self):

        if self._ac_model_type != 1:
            self.player.ac.node.show()

        self._camera.node().setActive(False)
        self.node.hide()
        #for cn in self.player.ac.cannons:
            #cn.mpos_override = None
        if base.with_cockpit_shadows:
            self._shadow_camera.node().setActive(False)
            self.shadow_node.hide()
        for cannon in self.player.ac.cannons:
            for mflash in cannon.mflashes:
                if mflash not in self._own_mflashes:
                    mflash.node.show()
        self.player.headchaser.move_to(atref=Vec3(0.0, 1.0, 0.0))
        self._txscmgr.deactivate()


    def _register_addon_model (self, smodel):

        if self._ac_model_type == 2:
            smodelnd = smodel.node()
            if isinstance(smodelnd, LODNode):
                lpos = smodelnd.getHighestSwitch()
                lsmodel = smodel.getChild(lpos)
                omodel = lsmodel.copyTo(self._ac_model)
            else:
                omodel = smodel.copyTo(self._ac_model)
            omodel.setPos(smodel.getPos())
            omodel.setHpr(smodel.getHpr())
            self._ac_model_addons[smodel] = omodel


    def _unregister_addon_model (self, smodel):

        if self._ac_model_type == 2:
            if smodel in self._ac_model_addons:
                omodel = self._ac_model_addons.pop(smodel)
                omodel.removeNode()


    def _update_lighting (self, dt):

        # Project world lights to own.
        # - position of the sun and the moon
        sunhpr = self.world.sky.sunlight.getHpr(self.player.ac.node)
        self._sunlnd.setHpr(sunhpr)
        moonhpr = self.world.sky.moonlight.getHpr(self.player.ac.node)
        self._moonlnd.setHpr(moonhpr)
        # - colors
        amblcol = self.world.sky.amblight.node().getColor()
        self._amblnd.node().setColor(amblcol)
        self._sunlnd.node().setColor(self.world.sky.sunlight.node().getColor())
        self._moonlnd.node().setColor(self.world.sky.moonlight.node().getColor())
        # - shadows
        if base.with_cockpit_shadows:
            self._shadow_camera.setQuat(self._sunlnd.getQuat())

        # Handle instrument lights.
        # - automatically turn on or off
        if self._instr_night_light_auto_on_off:
            if (not self._instr_night_light_on and
                self.world.sky.sun_strength < self._instr_night_light_lim_sun_strength):
                    self.light_on_off(on=True, auto=True)
            elif (self._instr_night_light_on and
                  self.world.sky.sun_strength >= self._instr_night_light_lim_sun_strength):
                    self.light_on_off(on=False, auto=True)
        # - special ambient light based on sun strength
        if not self._instr_night_light_on:
            amblcol_instr = intl01v(self.world.sky.sun_strength,
                                    amblcol, Vec4(1.0, 1.0, 1.0, 1.0))
            self._amblnd_instr_dim.node().setColor(amblcol_instr)


    def _update_headpos (self, dt):

        acp = self.player.ac

        pclev = self.world.player_control_level
        if pclev != self._prev_player_control_level:
            ppclev = self._prev_player_control_level
            if pclev == 2:
                self._view_look_off = Vec3(0.0, 0.0, 0.0)
                self._view_look_speed = None
                self._view_idle_fov_off = 0.0
                self._view_force_fov_off = None
                self._view_fov_speed_time = self._view_idle_fov_speed_time

        # Head moving.
        if (self.player.helmet.view_body is not None and
            #self._view_base_hpr is self._view_idle_hpr and
            not self._view_ignore_lock):
            rvpos = self.player.helmet.view_body.pos(acp)
            view_base_hpr = vectohpr(unitv(rvpos))
        else:
            view_base_hpr = self._view_base_hpr
        view_pos = Vec3()
        view_hpr = Vec3()
        view_vfov = self._camlens.getMinFov()
        view_hfov = vert_to_horiz_fov(view_vfov, base.aspect_ratio)
        #view_hfov = view_vfov * base.aspect_ratio # approx
        view_dfov = 0.0
        hprvelfac = 200.0 * (5.0 / self._view_max_horiz_off)
        #hprvelfac = dhpr.length()**0.1 * 4.0
        # - anim
        thpr = view_base_hpr
        dhpr = thpr - self._view_anim_hpr
        #hprmaxvel = self._view_look_max_speed
        #hprvel = clampn(dhpr * hprvelfac, -hprmaxvel, hprmaxvel)
        hprvel = dhpr * hprvelfac
        self._view_anim_hpr += hprvel * dt
        view_hpr += self._view_anim_hpr
        # - player
        if self._view_look_speed is not None:
            if (abs(self._view_look_speed[0]) < 0.05 and
                abs(self._view_look_speed[1]) < 0.05):
                view_vfov = self._camlens.getMinFov()
                ifac = view_vfov / self._view_look_snap_back_vfov_ref
                if self.player.helmet.view_body and not self._view_ignore_lock:
                    view_look_snap_back_off_ref = self._view_look_snap_back_off_ref_lock_view
                else:
                    view_look_snap_back_off_ref = self._view_look_snap_back_off_ref
                view_look_snap_back_off = view_look_snap_back_off_ref * ifac
                if (abs(self._view_look_off[0]) < view_look_snap_back_off[0] and
                    abs(self._view_look_off[1]) < view_look_snap_back_off[1]):
                    self._view_look_speed = None
        if self._view_look_speed is not None:
            if ((self._view_look_prev_body is not self.player.helmet.view_body and
                 not self._view_ignore_lock) or
                self._view_prev_ignore_lock != self._view_ignore_lock):
                self._view_look_prev_body = self.player.helmet.view_body
                self._view_prev_ignore_lock = self._view_ignore_lock
                self._view_look_speed = None
        self._view_look_prev_base_hpr = view_base_hpr
        if self._view_look_speed is not None:
            self._view_look_off += self._view_look_speed * dt
            self._view_look_speed += self._view_look_acc * dt
        else:
            dhpr = -Vec3(self._view_look_off)
            #hprmaxvel = self._view_look_max_speed
            #hprvel = clampn(dhpr * hprvelfac, -hprmaxvel, hprmaxvel)
            hprvel = dhpr * hprvelfac
            dhpr = hprvel * dt
            self._view_look_off += dhpr
        view_hpr += self._view_look_off
        # - limit base moving (anim plus player)
        view_max_horiz_offc = self._view_max_horiz_off #- view_hfov * 0.5
        view_hpr[0] = clamp(view_hpr[0],
                            -view_max_horiz_offc, view_max_horiz_offc)
        view_max_vert_offc_up = self._view_max_vert_off_up #- view_vfov * 0.5
        view_max_vert_offc_down = self._view_max_vert_off_down - view_vfov * 0.5
        view_hpr[1] = clamp(view_hpr[1],
                            -view_max_vert_offc_down, view_max_vert_offc_up)
        self._view_look_off = view_hpr - self._view_anim_hpr
        # - shift
        if abs(view_hpr[0]) > self._view_horiz_shift_start_off:
            dhpr = abs(view_hpr[0]) - self._view_horiz_shift_start_off
            dhpr_max = self._view_max_horiz_off - self._view_horiz_shift_start_off
            shift_fac = dhpr / dhpr_max
            shift_pos = self._view_horiz_shift_max * shift_fac
            shift_pos[0] *= -sign(view_hpr[0])
            view_pos += shift_pos
        # - inertia
        tpos = Point3()
        thpr = Vec3()
        maxoffpitch = 4.0 # [deg]
        offpitch = -self.player.input_elevator * maxoffpitch
        thpr[1] = offpitch
        maxoffroll = 10.0 # [deg]
        if not acp.onground:
            offroll = self.player.input_ailerons * maxoffroll
            thpr[2] = offroll
        else:
            offsteer = self.player.input_steer * maxoffroll * 0.5
            thpr[0] = -offsteer
        hprvelfac = 16.0 * (2.0 / (maxoffpitch + maxoffroll))
        hprmaxvel = Vec3(11.0, 11.0, 11.0)
        dhpr = thpr - self._view_inert_hpr
        hprvel = clampn(dhpr * hprvelfac, -hprmaxvel, hprmaxvel)
        self._view_inert_hpr += hprvel * dt
        view_hpr += self._view_inert_hpr
        maxoffside = 0.015
        tpos[0] = maxoffside * (self._view_inert_hpr[2] / maxoffroll)
        maxoffupdw = 0.008
        tpos[2] = maxoffupdw * (self._view_inert_hpr[1] / maxoffpitch)
        view_pos += tpos
        # - buffet
        thpr = Vec3(0.0, degrees(-acp.buffet_daoa), degrees(-acp.buffet_dbnk))
        view_hpr += thpr
        # - recoil
        dpos = Vec3(-acp.recoil_dx, 0.0, -acp.recoil_dz)
        view_pos += dpos
        thpr = Vec3(0.0, degrees(-acp.recoil_daoa), degrees(-acp.recoil_dbnk))
        view_hpr += thpr
        # - shake
        dpos = Vec3(-acp.shake_dx, 0.0, -acp.shake_dz)
        view_pos += dpos
        thpr = Vec3(0.0, degrees(-acp.shake_daoa), degrees(-acp.shake_dbnk))
        view_hpr += thpr
        # - rolling
        dpos = Vec3(0.0, 0.0, -acp.rolling_du)
        view_pos += dpos
        # - forward acceleration
        fw_acc = (acp.dynstate.b).dot(acp.dynstate.at)
        fw_acc = self._view_accel_averager.update(fw_acc, dt)
        if fw_acc > 0.0:
            ref_fw_acc = self._view_accel_pst_fw_acc
            ref_fov_off = self._view_accel_pst_fov_off
            ref_y_off = self._view_accel_pst_y_off
        else:
            ref_fw_acc = self._view_accel_ngt_fw_acc
            ref_fov_off = self._view_accel_ngt_fov_off
            ref_y_off = self._view_accel_ngt_y_off
        acc_fac = fw_acc / ref_fw_acc
        view_pos += Point3(0.0, ref_y_off * acc_fac, 0.0)
        view_dfov += ref_fov_off * acc_fac

        # FOV changing.
        target_fov_off = None
        if self._view_force_fov_off is not None:
            if self._view_fov_off != self._view_force_fov_off:
                target_fov_off = self._view_force_fov_off
        else:
            if self._view_fov_off != self._view_idle_fov_off:
                target_fov_off = self._view_idle_fov_off
        if target_fov_off is not None:
            dfov = target_fov_off - self._view_fov_off
            t_fov = self._view_fov_speed_time
            v_fov = dfov / t_fov
            if abs(v_fov) < self._view_fov_min_speed:
                v_fov = self._view_fov_min_speed * sign(dfov)
            fov_off = self._view_fov_off + v_fov * dt
            if (target_fov_off - fov_off) * dfov <= 0.0:
                fov_off = target_fov_off
            self._view_fov_off = fov_off
        view_dfov += self._view_fov_off

        # Update camera.
        pch = self.player.headchaser
        pch.set_offset(dpos=view_pos, dhpr=view_hpr, dfov=view_dfov)
        ch_pos = pch.node.getPos()
        ch_hpr = pch.node.getHpr()
        self._camera.setPos(ch_pos - self._head_pos)
        self._camera.setHpr(ch_hpr)
        self._camlens.setMinFov(self.player.headchaser.fov)

        # Collimated HUD projection moving due to head inertia.
        if self.has_hud:
            vpx, vpy, vpz = view_pos
            hsx, hsy, hsz = self._hud_overlay_node_hsize
            hpos = Point3(vpx / hsx, 0.0, vpz / hsz)
            self._hud_overlay_node.setPos(hpos)


    def _update_waypoints (self, dt):

        self._waypoint_wait_check -= dt
        if self._waypoint_wait_check <= 0.0:
            self._waypoint_wait_check = self._waypoint_check_period
            if self._current_waypoint:
                wp = self._waypoints[self._current_waypoint]
                ret = self._to_marker(wp)
                there, dist, dalt, dhead = ret
                if there:
                    self._at_current_waypoint = True
                else:
                    self._at_current_waypoint = False
                    self._current_tozone_active = False
                self._current_waypoint_dalt = dalt
                self._current_waypoint_dist = dist
                self._current_waypoint_head = dhead


    def _update_aimzoom (self, dt):

        aimzoom_target = None
        if self.player.input_select_weapon >= 0 and not self._view_ignore_lock:
            wp = self.player.weapons[self.player.input_select_weapon]
            if isinstance(wp.handle, (Cannon, PodLauncher)):
                target = self.player.helmet.target_body
                if (target is not None and
                    target.side not in self.world.get_allied_sides(self.player.ac.side)):
                    inside_dist = False
                    inside_angles = False
                    aimzoom_min_dist = self._aimzoom_min_dist_size_fac * target.bboxdiag
                    tdist = target.dist(self.player.ac)
                    if aimzoom_min_dist < tdist < self._aimzoom_max_dist:
                        inside_dist = True
                        ang0 = self._aimzoom_max_offbore
                        if isinstance(wp.handle, Cannon):
                            if not self._hud_gun_lead_node.isHidden() and self._hud_gun_lead_data:
                                anglh, anglv, angth, angtv = self._hud_gun_lead_data
                                if abs(anglh - angth) < ang0 and abs(anglv - angtv) < ang0:
                                    inside_angles = True
                        elif isinstance(wp.handle, PodLauncher):
                            offset = self.player.helmet.target_offset
                            ret = _bore_angles(self.player.ac, target, offset)
                            angth, angtv = ret
                            if abs(angth) < ang0 and abs(angtv) < ang0:
                                inside_angles = True
                    if inside_angles and inside_dist:
                        rtpos = target.pos(self.player.ac)
                        rtdir = unitv(rtpos)
                        ptarea = target.project_bbox_area(rtdir, refbody=self.player.ac)
                        trad = sqrt(ptarea / pi)
                        tdist = rtpos.length()
                        tangsize = atan(trad / tdist)
                        if tangsize < self._aimzoom_max_offbore:
                            aimzoom_target = target
                            if aimzoom_target is self._aimzoom_target:
                                self._aimzoom_time += dt
                            else:
                                self._aimzoom_time = 0.0
                        self._view_fov_speed_time = self._aimzoom_fov_speed_time
                else:
                    # TODO: Add no-lock zoom.
                    pass

        self._aimzoom_target = aimzoom_target
        if aimzoom_target and self._aimzoom_time >= self._aimzoom_check_time:
            self._view_force_fov_off = self._view_aim_fov_off
        else:
            self._view_force_fov_off = None


    def _init_sounds (self):

        self._movables_flow_sound = Sound2D(
            path="audio/sounds/cockpit-mig29-airbrake-flow.ogg",
            world=self.world, pnode=self.node,
            volume=0.0, loop=True)
        self._movables_flow_active = False

        self._airbrake_flow_min_speed = 50.0
        self._airbrake_flow_max_speed = 150.0
        self._airbrake_flow_max_volume = 0.8
        self._prev_airbrake_active = None

        self._lgear_up_sound = Sound2D(
            path="audio/sounds/cockpit-mig29-gearsup.ogg",
            world=self.world, pnode=self.node,
            volume=0.8, loop=False)
        self._lgear_down_sound = Sound2D(
            path="audio/sounds/cockpit-mig29-gearsdn.ogg",
            world=self.world, pnode=self.node,
            volume=0.8, loop=False)
        self._lgear_flow_min_speed = 40.0
        self._lgear_flow_max_speed = 100.0
        self._lgear_flow_max_volume = 0.6
        self._prev_lgear_active = None

        self._flarechaff_launch_sound = Sound2D(
            path="audio/sounds/cockpit-flare.ogg",
            world=self.world, pnode=self.node,
            volume=0.7, loop=False)
        self._prev_flarechaff_count = self.player.ac.flarechaff


    def _update_sounds (self, dt):

        movables_flow_vol = 0.0

        airbrake_active = (self.player.ac.dynstate.brd > 0.0)
        if self._prev_airbrake_active != airbrake_active:
            self._prev_airbrake_active = airbrake_active
            if airbrake_active:
                pass
            else:
                pass
        if airbrake_active:
            speed = self.player.ac.dynstate.v
            airbrake_vol = intl01vr(
                speed,
                self._airbrake_flow_min_speed, self._airbrake_flow_max_speed,
                0.0, self._airbrake_flow_max_volume)
            airbrake_vol *= self.player.ac.dynstate.brd
            movables_flow_vol = max(movables_flow_vol, airbrake_vol)

        lgear_active = self.player.ac.dynstate.lg
        if self._prev_lgear_active != lgear_active:
            self._prev_lgear_active = lgear_active
            if lgear_active:
                if self.world.frame - self._frame_created > 10:
                    self._lgear_up_sound.stop()
                    self._lgear_down_sound.play(fadetime=0.1)
            else:
                if self.world.frame - self._frame_created > 10:
                    self._lgear_down_sound.stop()
                    self._lgear_up_sound.play(fadetime=0.1)
        if lgear_active:
            speed = self.player.ac.dynstate.v
            lgear_vol = intl01vr(
                speed,
                self._lgear_flow_min_speed, self._lgear_flow_max_speed,
                0.0, self._lgear_flow_max_volume)
            movables_flow_vol = max(movables_flow_vol, lgear_vol)

        if movables_flow_vol > 0.0:
            if not self._movables_flow_active:
                self._movables_flow_active = True
                self._movables_flow_sound.play()
            self._movables_flow_sound.set_volume(movables_flow_vol)
        elif self._movables_flow_active:
            self._movables_flow_active = False
            self._movables_flow_sound.stop()

        flarechaff_count = self.player.ac.flarechaff
        if self._prev_flarechaff_count > flarechaff_count:
            self._prev_flarechaff_count = flarechaff_count
            self._flarechaff_launch_sound.stop(fadetime=0.05)
            self._flarechaff_launch_sound.play(fadetime=0.05)


    def light_on_off (self, on=None, auto=False):

        self._instr_night_light_auto_on_off = auto
        if on is True or not self._instr_night_light_on:
            self._instr_night_light_on = True
            self._amblnd_instr_dim.node().setColor(Vec4(1.0, 1.0, 1.0, 1.0))
            for nd in self._instr_night_light_nodes:
                nd.setShaderInput(self._shdinp.glowfacn, 1.0)
                nd.setShaderInput(self._shdinp.glowaddn, 1.0)
        elif on is False or self._instr_night_light_on:
            self._instr_night_light_on = False
            for nd in self._instr_night_light_nodes:
                nd.setShaderInput(self._shdinp.glowfacn, 0.0)
                nd.setShaderInput(self._shdinp.glowaddn, 0.0)


    def _init_radar (self):

        screennd = self._model.find("**/radarpanel_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_radar)
        self._instr_cleanup_fs.append(self._cleanup_radar)

        glassnd = self._model.find("**/radarpanel_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=1024,
            #bgimg="images/cockpit/cockpit_mig29_radar_bg.png")
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="radar-screen")
        self._radar_scene = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_radar_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)

        # See comment-hud-size.
        un = 2.0 / 32.0

        #self._radar_font = "fonts/DejaVuSans-Bold.ttf"
        self._radar_font = "fonts/red-october-regular.otf"
        #self._radar_font = "fonts/DidactGothic.ttf"
        self._radar_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)

        self._radar_screen_extent = 0.96

        self._radar_display_node = self._radar_scene.attachNewNode("radar-display")
        self._radar_display_node.setScale(self._radar_screen_extent)

        outranges_gridnames = (
            #(8000.0, "2x2"),
            #(16000.0, "4x4"),
            (16000.0, "2x2"),
            (64000.0, "8x8"),
        )

        # Radar activity indicator.
        actnd = self._radar_display_node.attachNewNode("radar-active")
        make_image(
            "images/cockpit/cockpit_mig29_radar_active_tex.png",
            pos=Point3(0.0, 0.0, 0.0), size=(32 * un),
            filtr=False, parent=actnd)
        radar_sym = select_des(_("R"), {"ru": u"Р"}, self._lang)
        self._radar_radar_clear_node = make_text(
            text=radar_sym,
            width=0.5, pos=Point3(0.95, 0.0, 0.10),
            font=self._radar_font, size=32, color=self._radar_color,
            align="r", anchor="mr", parent=actnd)
        self._radar_radar_jammed_node = make_text(
            text=("*" + radar_sym),
            width=0.5, pos=Point3(0.95, 0.0, 0.10),
            font=self._radar_font, size=32, color=self._radar_color,
            align="r", anchor="mr", parent=actnd)
        self._radar_radar_jammed = False
        self._radar_radar_jammed_node.hide()
        self._radar_active_radar_node = actnd

        # IRST activity indicator.
        actnd = self._radar_display_node.attachNewNode("irst-active")
        make_text(
            text=select_des(_("IR"), {"ru": u"Т"}, self._lang),
            width=0.5, pos=Point3(0.95, 0.0, -0.10),
            font=self._radar_font, size=32, color=self._radar_color,
            align="r", anchor="mr", parent=actnd)
        self._radar_active_irst_node = actnd

        # Scale.
        self._radar_outranges = []
        self._radar_grid_nodes = []
        for outrange, gname in outranges_gridnames:
            self._radar_outranges.append(outrange)
            gridnd = self._radar_display_node.attachNewNode("grid-%s" % gname)
            make_image(
                "images/cockpit/cockpit_mig29_radar_grid_%s.png" % gname,
                pos=Point3(0.0, 0.0, 0.0), size=(32 * un),
                filtr=False, parent=gridnd)
            make_text(
                text=("%s" % int(outrange / 1000.0 + 0.5)),
                width=0.5, pos=Point3(0.95, 0.0, -0.95),
                font=self._radar_font, size=32, color=self._radar_color,
                align="r", anchor="br", parent=gridnd)
            gridnd.hide()
            self._radar_grid_nodes.append(gridnd)
        make_image(
            "images/cockpit/cockpit_mig29_radar_edge_scale.png",
            pos=Point3(0.0, 0.0, 0.0), size=(32 * un),
            filtr=False, parent=self._radar_display_node)
        make_image(
            "images/cockpit/cockpit_mig29_radar_sweep_cone.png",
            pos=Point3(0.0, 0.0, 0.0), size=(32 * un),
            filtr=False, parent=self._radar_display_node)
        self._radar_range_texts = []
        scrcone = radians(60.0) # as drawn on *_radar_sweep_cone image
        x0 = 0.0
        z0 = -1.0
        outrad = 2.0
        scdiv = 4
        for i in range(1, scdiv - 1):
            crad = i * (outrad / scdiv)
            x = x0 + sin(0.5 * scrcone) * crad
            z = z0 + cos(0.5 * scrcone) * crad
            textnd = make_text(
                width=0.5, pos=Point3(x + 0.06, 0.0, z + 0.02),
                font=self._radar_font, size=26, color=self._radar_color,
                align="l", anchor="ml", parent=self._radar_display_node)
            self._radar_range_texts.append(textnd)
        self._radar_scale = 0
        self._radar_scale_shift = -1 # switch to highest scale at start

        # Contacts.
        self._radar_from_sensors = frozenset(["radar", "irst", "datalink"])
        self._radar_direct_sensors = frozenset(["radar", "irst"])
        self._radar_vertind_dalt = 500.0
        self._radar_blips_node = self._radar_display_node.attachNewNode("blips")
        self._radar_blips_legend = {
            "unknown": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_unknown_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_unknown_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_unknown_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_unknown_tex.png",
                showdalt=True),
            "plane": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_air_enemy_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_air_friendly_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_air_enemy_reported_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_air_friendly_reported_tex.png",
                showdalt=True),
            "heli": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_air_enemy_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_air_friendly_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_air_enemy_reported_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_air_friendly_reported_tex.png",
                showdalt=True),
            "vehicle": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_reported_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_reported_tex.png",
                showdalt=False),
            "building": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_reported_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_reported_tex.png",
                showdalt=False),
            "ship": SimpleProps(
                etexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_tex.png",
                ftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_tex.png",
                ietexpath="images/cockpit/cockpit_mig29_radar_blip_ground_enemy_reported_tex.png",
                iftexpath="images/cockpit/cockpit_mig29_radar_blip_ground_friendly_reported_tex.png",
                showdalt=False),
        }
        self._radar_visible_contacts = set()
        self._radar_blips = {}
        self._radar_blips_blinking = {}
        self._radar_blip_size = 2 * un
        scanperiod = 0.997
        self._radar_contact_update_period = scanperiod
        self._radar_contact_wait_update = scanperiod * 0.5
        self._radar_motion_update_period = 0.163
        self._radar_motion_wait_update = 0.0
        self._radar_blink_update_period = 0.25
        self._radar_blink_wait_update = 0.0
        self._radar_blip_min_alpha = 0.0

        self.player.ac.sensorpack.update(scanperiod=scanperiod, relspfluct=0.0)
        self.player.ac.sensorpack.set_emissive(active=True)
        self.player.ac.sensorpack.start_scanning()

        self._radar_current_emissive = self.player.ac.sensorpack.emissive

        self._prev_target_contact = None

        return True


    def _cleanup_radar (self):

        self._radar_scene.removeNode()


    def _update_radar (self, dt):

        acp = self.player.ac

        if self._radar_scale_shift != 0:
            self._radar_grid_nodes[self._radar_scale].hide()
            nscales = len(self._radar_outranges)
            self._radar_scale += self._radar_scale_shift
            self._radar_scale = pclamp(self._radar_scale, 0, nscales)
            self._radar_grid_nodes[self._radar_scale].show()
            outrange = self._radar_outranges[self._radar_scale]
            rngdiv = len(self._radar_range_texts) + 2
            for i in range(1, rngdiv - 1):
                crng = round(i * (outrange / rngdiv))
                update_text(self._radar_range_texts[i - 1],
                            text=("%.0f" % (crng / 1000)))
            self._radar_scale_shift = 0

        if self._radar_radar_jammed != acp.jammed:
            self._radar_radar_jammed = acp.jammed
            if self._radar_radar_jammed:
                self._radar_radar_jammed_node.show()
                self._radar_radar_clear_node.hide()
            else:
                self._radar_radar_jammed_node.hide()
                self._radar_radar_clear_node.show()

        if self._radar_current_emissive != self.player.ac.sensorpack.emissive:
            self._radar_current_emissive = self.player.ac.sensorpack.emissive
            if self._radar_current_emissive:
                self._radar_active_radar_node.show()
            else:
                self._radar_active_radar_node.hide()

        self._radar_contact_wait_update -= dt
        if self._radar_contact_wait_update <= 0.0:
            self._radar_contact_wait_update += self._radar_contact_update_period

            # Collect new and old visible contacts.
            all_visible_contacts = set()
            all_contacts = acp.sensorpack.contacts()
            sens_by_con = acp.sensorpack.sensors_by_contact()
            for con in all_contacts:
                if self._radar_from_sensors.intersection(sens_by_con[con]):
                    all_visible_contacts.add(con)
            old_visible_contacts = self._radar_visible_contacts.difference(all_visible_contacts)
            new_visible_contacts = all_visible_contacts.difference(self._radar_visible_contacts)
            self._radar_visible_contacts = all_visible_contacts

            # Remove blips of old visible contacts.
            for con in old_visible_contacts:
                blip = self._radar_blips.pop(con)
                blip.node.removeNode()
                self._radar_blips_blinking.pop(con, None)

            # Add blips of new visible contacts.
            for con in new_visible_contacts:
                blip = SimpleProps()
                self._radar_blips[con] = blip
                lgd = self._radar_blips_legend.get(con.family)
                if lgd is None:
                    lgd = self._radar_blips_legend["unknown"]
                blip.node = self._radar_blips_node.attachNewNode("blip")
                blip.symbol_node = self._radar_blips_node.attachNewNode("symbol")
                blip.symbol_key = (None, None)
                if lgd.showdalt:
                    blip.showdalt = True
                    blip.alt_above_node = make_image(
                        texture="images/cockpit/cockpit_mig29_radar_blip_alt_above_tex.png",
                        size=self._radar_blip_size,
                        filtr=False, parent=blip.node)
                    blip.alt_below_node = make_image(
                        texture="images/cockpit/cockpit_mig29_radar_blip_alt_below_tex.png",
                        size=self._radar_blip_size,
                        filtr=False, parent=blip.node)
                else:
                    blip.showdalt = False

            # Update blips, slow part.
            allied_sides = self.world.get_allied_sides(acp.side)
            sens_by_con = self.player.ac.sensorpack.sensors_by_contact()
            for con, blip in self._radar_blips.iteritems():
                friendly = con.side in allied_sides
                direct = bool(self._radar_direct_sensors.intersection(sens_by_con[con]))
                symbol_key = (friendly, direct)
                if blip.symbol_key != symbol_key:
                    blip.symbol_key = symbol_key
                    lgd = self._radar_blips_legend.get(con.family)
                    blip.symbol_node.removeNode()
                    if friendly:
                        symtexpath = lgd.ftexpath if direct else lgd.iftexpath
                    else:
                        symtexpath = lgd.etexpath if direct else lgd.ietexpath
                    blip.symbol_node = make_image(
                        texture=symtexpath, size=self._radar_blip_size,
                        filtr=False, parent=blip.node)

            self._radar_motion_wait_update = 0.0 # to set new blip positions

        # Update blips, fast part.
        self._radar_motion_wait_update -= dt
        if self._radar_motion_wait_update <= 0.0:
            self._radar_motion_wait_update += self._radar_motion_update_period
            pos = acp.pos()
            fdir = acp.quat().getForward()
            hfdir = Vec3(fdir[0], fdir[1], 0.0)
            hudir = Vec3(0, 0, 1)
            if hfdir.normalize() == 0.0:
                hfdir = Vec3(0, 1, 0)
            hrdir = unitv(hfdir.cross(hudir))
            outrange = self._radar_outranges[self._radar_scale]
            sfac = 2.0 / outrange
            for con, blip in self._radar_blips.iteritems():
                if not con.trackable():
                    # It will disappear on next sensor reading.
                    continue
                con.update_for_motion()
                dpos = con.pos - pos
                relbpos = Vec3(dpos.dot(hrdir), dpos.dot(hfdir), dpos.dot(hudir))
                sx = relbpos[0] * sfac
                sz = relbpos[1] * sfac - 1.0
                blip.node.setPos(sx, 0.0, sz)
                if -1.0 < sx < 1.0 and -1.0 < sz < 1.0:
                    blip.node.show()
                else:
                    blip.node.hide()
                dalt = dpos[2]
                if blip.showdalt:
                    if dalt > self._radar_vertind_dalt:
                        blip.alt_above_node.show()
                        blip.alt_below_node.hide()
                    elif dalt < -self._radar_vertind_dalt:
                        blip.alt_above_node.hide()
                        blip.alt_below_node.show()
                    else:
                        blip.alt_above_node.hide()
                        blip.alt_below_node.hide()

        # Update blip blinking.
        tcon = self.player.helmet.target_contact
        if tcon is not self._prev_target_contact:
            blip = self._radar_blips_blinking.pop(self._prev_target_contact, None)
            if blip is not None:
                blip.node.setSa(1.0)
            self._prev_target_contact = tcon
            blip = self._radar_blips.get(tcon)
            if blip is not None:
                self._radar_blips_blinking[tcon] = blip
        if self._radar_blips_blinking:
            minsa = self._radar_blip_min_alpha
            self._radar_blink_wait_update -= dt
            if self._radar_blink_wait_update <= 0.0:
                self._radar_blink_wait_update += self._radar_blink_update_period
            k1 = self._radar_blink_wait_update / self._radar_blink_update_period
            sa = minsa + (1.0 - minsa) * k1
            for blip in self._radar_blips_blinking.itervalues():
                blip.node.setSa(sa)
        else:
            self._radar_blink_wait_update = 0.0


    def radar_on_off (self):

        if self.player.ac.sensorpack.emissive:
            self.player.ac.sensorpack.set_emissive(active=False)
        else:
            self.player.ac.sensorpack.set_emissive(active=True)


    def _init_hud (self, make_shader_sunopq):

        screennd = self._model.find("**/hud_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_hud)
        self._instr_cleanup_fs.append(self._cleanup_hud)
        screennd.setBin("fixed", 120) # higher than "glass" (projection surface)

        glassnd = self._model.find("**/hud_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_black_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        shader = make_shader_sunopq(0.0)
        screennd.setShader(shader)

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=1024,
            uvoffscn=self._shdinp.uvoffscn,
            name="hud")
        self._hud_scene = ret

        screennd.setTransparency(TransparencyAttrib.MAlpha)
        #screennd.setSa(0.8)
        #screennd.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_hud_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)

        #self._hud_font = "fonts/DejaVuSans-Bold.ttf"
        self._hud_font = "fonts/red-october-regular.otf"
        #self._hud_font = "fonts/DidactGothic.ttf"
        #self._hud_font = "fonts/VDS_New.ttf"
        self._hud_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)

        # comment-hud-size:
        # HUD elements will have different in-scene sizes,
        # but these must be in proportion to their texture sizes.
        # E.g. an element using 128x128 texture has to be twice
        # the in-scene size of an element using 64x64 texture.
        # Therefore we introduce the "HUD unit" such that in-scene sizes
        # of all elements can be expressed in integer amounts of this unit.
        un = 2.0 / 32.0

        # Base font size.
        self._hud_base_font_size = 26
        bfsz = self._hud_base_font_size

        self._hud_overlay_node = self._hud_scene.attachNewNode("hud-overlay")
        hoscale = 1.0
        self._hud_overlay_node.setScale(hoscale)
        if False:
            make_image(
                "images/cockpit/cockpit_mig29_hud_limits_tex.png",
                pos=Point2(0.0, 0.0), size=(32 * un),
                filtr=False, parent=self._hud_overlay_node)

        # Mode.
        self.hud_mode = "nav"
        self._hud_mode_text = make_text(
            width=0.5, pos=Point2(-0.50, -0.70),
            font=self._hud_font, size=(1.0 * bfsz), color=self._hud_color,
            align="r", anchor="tr", parent=self._hud_overlay_node)
        self._hud_prev_selwp = -1 # not None, to trigger HUD mode check

        # Altitude and speed.
        self._hud_altspd_period = 0.31
        self._hud_wait_altspd = 0.0
        self._hud_speed_text = make_text(
            width=0.5, pos=Point2(-0.40, 0.70),
            font=self._hud_font, size=(1.15 * bfsz), color=self._hud_color,
            align="r", anchor="mr", parent=self._hud_overlay_node)
        # NOTE: Temporary, until instrument panel done.
        self._hud_altitude_text = make_text(
            width=0.5, pos=Point2(0.40, 0.70),
            font=self._hud_font, size=(1.15 * bfsz), color=self._hud_color,
            align="l", anchor="ml", parent=self._hud_overlay_node)
        self._hud_radar_altitude_text = make_text(
            width=0.5, pos=Point2(0.40, 0.60),
            font=self._hud_font, size=(0.85 * bfsz), color=self._hud_color,
            align="l", anchor="ml", parent=self._hud_overlay_node)
        self._hud_radar_altitude_threshold = 1000.0

        # Heading scale.
        self._hud_heading_period = 0.093
        self._hud_wait_heading = 0.0
        make_image(
            "images/cockpit/cockpit_mig29_hud_heading_baseline_tex.png",
            pos=Point2(0.0, 8 * un), size=(16 * un),
            filtr=False, parent=self._hud_overlay_node)
        hdgsw = 0.66
        hdgscnd = self._hud_overlay_node.attachNewNode("heading-scale")
        hdgscnd.setPos(0.0, 0.0, 12 * un)
        ticknd = make_image(
            "images/cockpit/cockpit_mig29_hud_heading_tick_tex.png",
            size=(2 * un), filtr=False)
        ndiv1 = 36
        dsc1 = 360.0 / ndiv1
        ndiv2 = 2
        dsc2 = 360.0 / (ndiv1 * ndiv2)
        marks_hdgs = []
        tdist1 = hdgsw / 2
        tdist2 = tdist1 / ndiv2
        for i in range(-ndiv1 + 1, ndiv1):
            hdgsc1 = (ndiv1 + i) if i < 0 else i
            nhtextnd = make_text(
                "%02d" % hdgsc1, width=0.2,
                pos=Point2(i * tdist1, 0.015),
                font=self._hud_font, size=(0.75 * bfsz),
                color=self._hud_color,
                align="c", anchor="bc",
                parent=hdgscnd)
            hdg1 = i * dsc1
            marks_hdgs.append((nhtextnd, hdg1))
            for j in range(ndiv2):
                cticknd = ticknd.copyTo(hdgscnd)
                cticknd.setPos(i * tdist1 + j * tdist2, 0.0, 0.0)
                hdg2 = i * dsc1 + j * dsc2
                marks_hdgs.append((cticknd, hdg2))
        self._hud_heading_scale_node = hdgscnd
        self._hud_heading_scale_scrwidth = hdgsw
        self._hud_heading_scale_hdgwidth = dsc1 * (hdgsw / tdist1)
        self._hud_heading_scale_hdg2scr = (self._hud_heading_scale_scrwidth /
                                           self._hud_heading_scale_hdgwidth)
        marks_hdgs.sort(key=lambda x: x[1])
        self._hud_navhdg_marks, self._hud_navhdg_hdgs = zip(*marks_hdgs)
        for snode in self._hud_navhdg_marks:
            snode.hide()
        self._hud_navhdg_prev_phdgm = 0.0
        self._hud_navhdg_prev_phdgm_ind = -1

        # Pitch and roll top.
        self._hud_attitude_node = self._hud_overlay_node.attachNewNode("hud-attitude")

        # Pitch bar.
        self._hud_pitch_period = 0.073
        self._hud_wait_pitch = 0.0
        self._hud_horizon_node = self._hud_attitude_node.attachNewNode("hud-horizon")
        self._hud_horizon_node.setPos(0.0, 0.0, 0.0)
        make_image(
            "images/cockpit/cockpit_mig29_hud_horizon_tex.png",
            pos=Point2(0.0, 0.0), size=(16 * un),
            filtr=False, parent=self._hud_horizon_node)
        self._hud_pitch_text = make_text(
            width=0.5, pos=Point2(0.40, 0.0),
            font=self._hud_font, size=(0.85 * bfsz), color=self._hud_color,
            align="l", anchor="bl", parent=self._hud_horizon_node)
        self._hud_pitch_ptclim = radians(45)
        self._hud_pitch_scrlim = 0.4
        self._hud_pitch_ptc2scr = (self._hud_pitch_scrlim /
                                   self._hud_pitch_ptclim)

        # Roll scale.
        self._hud_roll_period = 0.067
        self._hud_wait_roll = 0.0
        make_image(
            "images/cockpit/cockpit_mig29_hud_roll_scale_tex.png",
            pos=Point2(0.0, 0.0), size=(16 * un),
            filtr=False, parent=self._hud_attitude_node)
        self._hud_roll_attitude_node = make_image(
            "images/cockpit/cockpit_mig29_hud_roll_attitude_tex.png",
            pos=Point2(0.0, 0.0), size=(8 * un),
            filtr=False, parent=self._hud_attitude_node)

        # Waypoints.
        self._hud_waypoint_node = self._hud_overlay_node.attachNewNode("hud-waypoint")
        self._hud_waypoint_period = 0.47
        self._hud_wait_waypoint = 0.0
        self._hud_navbar_nodes = {}
        self._hud_navbar_subnodes = {}
        self._hud_prev_waypoint = None

        # Target root nodes.
        self._hud_attack_node = self._hud_overlay_node.attachNewNode("hud-target")
        self._hud_target_range_node = self._hud_attack_node.attachNewNode("hud-target-range")
        self._hud_pylons_node = self._hud_attack_node.attachNewNode("hud-pylons")

        # Target altitude, speed, heading.
        self._hud_target_altspd_period = 0.89
        self._hud_wait_target_altspd = 0.0
        self._hud_target_speed_text = make_text(
            width=0.5, pos=Point2(-0.40, 0.82),
            font=self._hud_font, size=(0.85 * bfsz), color=self._hud_color,
            align="r", anchor="mr", parent=self._hud_attack_node)
        self._hud_target_altitude_text = make_text(
            width=0.5, pos=Point2(0.40, 0.82),
            font=self._hud_font, size=(0.85 * bfsz), color=self._hud_color,
            align="l", anchor="ml", parent=self._hud_attack_node)
        self._hud_target_relhdg_node = make_image(
            "images/cockpit/cockpit_mig29_hud_target_heading_tex.png",
            pos=Point2(-9.5 * un, -7.5 * un), size=(4 * un),
            filtr=False, parent=self._hud_target_range_node)

        # Target range.
        self._hud_target_range_period = 0.91
        self._hud_wait_target_range = 0.0
        self._hud_target_range_node.setPos(0.0, 0.0, 0.0)
        make_image(
            "images/cockpit/cockpit_mig29_hud_target_range_scale_tex.png",
            pos=Point2(-8 * un, 1 * un), size=(16 * un),
            filtr=False, parent=self._hud_target_range_node)
        self._hud_target_range_scalemax_text = make_text(
            width=0.5, pos=Point2(-10.2 * un, 8.0 * un),
            font=self._hud_font, size=(0.85 * bfsz), color=self._hud_color,
            align="r", anchor="tr", parent=self._hud_target_range_node)
        self._hud_target_range_scale_scrlim = (440. / 1024.) * 2
        self._hud_target_range_indicator_base_z = -6 * un
        rindpos0 = Point2(-9 * un, self._hud_target_range_indicator_base_z)
        self._hud_target_range_indicator_node = make_image(
            "images/cockpit/cockpit_mig29_hud_target_range_indicator_tex.png",
            pos=rindpos0, size=(4 * un), filtr=False,
            parent=self._hud_target_range_node)
        self._hud_target_range_rmax_node = make_image(
            "images/cockpit/cockpit_mig29_hud_target_range_limit_tick_tex.png",
            pos=rindpos0, size=(4 * un), filtr=False,
            parent=self._hud_target_range_node)
        self._hud_target_range_rman_node = make_image(
            "images/cockpit/cockpit_mig29_hud_target_range_limit_tick_tex.png",
            pos=rindpos0, size=(4 * un), filtr=False,
            parent=self._hud_target_range_node)
        self._hud_target_range_rmin_node = make_image(
            "images/cockpit/cockpit_mig29_hud_target_range_limit_tick_tex.png",
            pos=rindpos0, size=(4 * un), filtr=False,
            parent=self._hud_target_range_node)

        # Weapon pylons.
        self._hud_pylons_period = 0.19
        self._hud_wait_pylons = 0.0
        pylnd = make_image(
            "images/cockpit/cockpit_mig29_hud_pylon_tex.png",
            size=(4 * un), filtr=False)
        rndnd = make_image(
            "images/cockpit/cockpit_mig29_hud_round_tex.png",
            size=(4 * un), filtr=False)
        #rrdnd = make_image(
            #"images/cockpit/cockpit_mig29_hud_round_ready_tex.png",
            #size=(4 * un), filtr=False)
        npyl = len(self.player.ac.pylons)
        pyldist = 0.09
        pyloffx = 0.5 * pyldist if (npyl % 2 == 0) else 0.0
        pylz = -11 * un
        self._hud_pylons_round_nodes = []
        self._hud_pylons_round_ready_nodes = []
        for i in range(npyl):
            if npyl % 2 == 0:
                if i % 2 == 0:
                    i1 = (npyl - i) // 2 - 1
                else:
                    i1 = (npyl + i) // 2
            else:
                if i == 0:
                    i1 = npyl // 2
                elif i % 2 == 0:
                    i1 = (npyl + i) // 2
                else:
                    i1 = (npyl - i) // 2 - 1
            pylx = pyloffx + pyldist * (i1 - npyl / 2)
            cpylnd = pylnd.copyTo(self._hud_pylons_node)
            cpylnd.setPos(pylx, 0.0, pylz)
            crndnd = rndnd.copyTo(self._hud_pylons_node)
            crndnd.setPos(pylx, 0.0, pylz)
            self._hud_pylons_round_nodes.append(crndnd)
            #crrdnd = rrdnd.copyTo(self._hud_pylons_node)
            #crrdnd.setPos(pylx, 0.0, pylz)
            #self._hud_pylons_round_ready_nodes.append(crrdnd)
        self._hud_pylons_weapon_text = make_text(
            width=1.0, pos=Point2(0.0, -0.63),
            font=self._hud_font, size=(1.0 * bfsz), color=self._hud_color,
            align="c", anchor="bc", parent=self._hud_pylons_node)
        self._hud_launch_auth_text = make_text(
            text=select_des(_("LA"), {"ru": u"ПР"}, self._lang),
            width=0.3, pos=Point2(0.0, -0.42),
            font=self._hud_font, size=(1.0 * bfsz), color=self._hud_color,
            align="c", anchor="mc", parent=self._hud_pylons_node)
        self._hud_pylons_counter_text = make_text(
            width=0.5, pos=Point2(0.0, -0.42),
            font=self._hud_font, size=(1.15 * bfsz), color=self._hud_color,
            align="c", anchor="tc", parent=self._hud_pylons_node)

        # Gun data.
        self._hud_gun_data_period = 0.17
        self._hud_wait_gun_data = 0.0
        self._hud_gun_node = self._hud_attack_node.attachNewNode("hud-gun")
        self._hud_gun_name_text = make_text(
            width=1.0, pos=Point2(0.0, -0.58),
            font=self._hud_font, size=(1.0 * bfsz), color=self._hud_color,
            align="c", anchor="tc", parent=self._hud_gun_node)
        self._hud_gun_counter_text = make_text(
            width=0.5, pos=Point2(0.0, -0.68),
            font=self._hud_font, size=(1.15 * bfsz), color=self._hud_color,
            align="c", anchor="tc", parent=self._hud_gun_node)

        # Gun lead.
        self._hud_gun_lead_period = 0.0
        self._hud_wait_gun_lead = 0.0
        self._hud_gun_lead_node = self._hud_gun_node.attachNewNode("hud-gun-lead")
        hnpos = screennd.getPos(self.node)
        hnmin0, hnmax0 = screennd.getTightBounds()
        hnmin = self.node.getRelativePoint(screennd.getParent(), hnmin0)
        hnmax = self.node.getRelativePoint(screennd.getParent(), hnmax0)
        self._hud_overlay_node_hsize = (hnmax - hnmin) * 0.5
        vfovup = atan2(hnmax[2] * hoscale, hnpos[1])
        vfovdw = -atan2(hnmin[2] * hoscale, hnpos[1])
        hfovrt = atan2(hnmax[0] * hoscale, hnpos[1])
        hfovlf = -atan2(hnmin[0] * hoscale, hnpos[1])
        if False:
            wcfovfac = (tan(0.5 * radians(COCKPIT_FOV)) /
                        tan(0.5 * radians(OUTSIDE_FOV)))
            vfovdwfc = atan(tan(vfovdw) / wcfovfac)
            hnsize = hnmax0 - hnmin0
            dbgval(1, "hud-view",
                   (hnpos[1], "%.3f", "dist", "m"),
                   (hnpos[0], "%.3f", "rhpos", "m"),
                   (hnpos[2], "%.3f", "rvpos", "m"),
                   (degrees(hfovlf), "%.2f", "hfovlf", "deg"),
                   (degrees(hfovrt), "%.2f", "hfovrt", "deg"),
                   (degrees(vfovdw), "%.2f", "vfovdw", "deg"),
                   (degrees(vfovup), "%.2f", "vfovup", "deg"),
                   (degrees(vfovdwfc), "%.2f", "vfovdwfc", "deg"),
                   (hnsize[0], "%.3f", "height", "m"),
                   (hnsize[2], "%.3f", "width", "m"))
        # HUD center must be in center of view, or else HUD projections are off.
        assert abs(vfovup - vfovdw) < radians(0.1)
        assert abs(hfovrt - hfovlf) < radians(0.1)
        self._hud_gun_lead_hvfov = tan(abs(vfovdw))
        self._hud_gun_lead_projoff_max = 0.80
        #self._hud_gun_lead_outrange = 1200.0 # short
        self._hud_gun_lead_outrange = 1600.0 # long
        self._hud_gun_lead_data = None
        self._hud_gun_lead_vis = 1
        if self._hud_gun_lead_vis == 0:
            make_image(
                "images/cockpit/cockpit_mig29_hud_gun_lead_tex.png",
                pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
                parent=self._hud_gun_lead_node)
            self._hud_gun_lead_range_indicator_node = make_image(
                "images/cockpit/cockpit_mig29_hud_gun_range_indicator_tex.png",
                pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
                parent=self._hud_gun_lead_node)
            self._hud_gun_lead_rmax_node = make_image(
                "images/cockpit/cockpit_mig29_hud_gun_range_limit_tick_tex.png",
                pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
                parent=self._hud_gun_lead_node)
        elif self._hud_gun_lead_vis == 1:
            make_image(
                "images/cockpit/cockpit_mig29_hud_gun_lead_base_long_tex.png",
                pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
                parent=self._hud_gun_lead_node)
            self._hud_gun_lead_range_nodes = []
            glr_root = "images/cockpit/cockpit_mig29_hud_gun_lead_range_tex"
            glr_tex_paths = []
            for fn in list_dir_files("data", glr_root):
                if fn.endswith(".png"):
                    glr_tex_paths.append(join_path(glr_root, fn))
            glr_tex_paths.sort()
            for glr_tex_path in glr_tex_paths:
                rnd = make_image(glr_tex_path,
                                 size=(4 * un), filtr=False,
                                 parent=self._hud_gun_lead_node)
                rnd.hide()
                self._hud_gun_lead_range_nodes.append(rnd)
            self._hud_gun_lead_range_index = -1
            num_steps = len(self._hud_gun_lead_range_nodes)
            self._hud_gun_lead_range_dist_mul = num_steps / self._hud_gun_lead_outrange
            self._hud_gun_lead_range_index_max = num_steps - 1

        # Center pieces in targeting modes.
        self._hud_crosshair_node = make_image(
            "images/cockpit/cockpit_mig29_hud_crosshair_tex.png",
            pos=Point2(0.0, 0.0), size=(4 * un), filtr=False,
            parent=self._hud_attack_node)
        #self._hud_missile_seeker_node = make_image(
            #"images/cockpit/cockpit_mig29_hud_missile_seeker_tex.png",
            #pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
            #parent=self._hud_attack_node)
        #self._hud_bomb_pip_node = make_image(
            #"images/cockpit/cockpit_mig29_hud_missile_seeker_tex.png",
            #pos=Point2(0.0, 0.0), size=(8 * un), filtr=False,
            #parent=self._hud_attack_node)

        # Stall warning.
        self._hud_stall_on = False
        self._hud_stall_period = 0.87
        self._hud_wait_stall = 0.0
        self._hud_stall_text = make_text(
            text=select_des(_("STALL"), {"ru": u"СВ"}, self._lang),
            width=1.0, pos=Point2(0.0, 0.50),
            font=self._hud_font, size=(1.15 * bfsz), color=self._hud_color,
            align="c", anchor="mc", parent=self._hud_overlay_node)
        self._hud_stall_blink_rate = 0.5
        self._hud_stall_sound = Sound2D(
            path="audio/sounds/flight-stall-warning.ogg",
            world=self.world, pnode=self.node,
            volume=0.4, loop=True, fadetime=0.1)

        return True


    def _cleanup_hud (self):

        self._hud_scene.removeNode()


    def _update_hud (self, dt):

        parent = self.player.ac
        ppos = parent.pos()
        phpr = parent.hpr()

        selwp = None
        if self.player.input_select_weapon >= 0:
            selwp = self.player.weapons[self.player.input_select_weapon]
        if self._hud_prev_selwp is not selwp:
            self._hud_prev_selwp = selwp
            if selwp:
                against = selwp.against()
                refagainst = against[0] if against else None
                if refagainst in ("building", "vehicle", "ship"):
                    self.hud_mode = "gnd"
                    update_text(self._hud_mode_text,
                                text=select_des(_("GND"), {"ru": u"ЗМЯ"},
                                                self._lang))
                else:
                    self.hud_mode = "atk"
                    update_text(self._hud_mode_text,
                                text=select_des(_("ATK"), {"ru": u"АТК"},
                                                self._lang))
            else:
                self.hud_mode = "nav"
                update_text(self._hud_mode_text,
                            text=select_des(_("NAV"), {"ru": u"МРШ"},
                                            self._lang))

        self._hud_wait_altspd -= dt
        if self._hud_wait_altspd <= 0.0:
            self._hud_wait_altspd = self._hud_altspd_period
            #pspd = parent.dynstate.v
            pspd = parent.dynstate.vias
            update_text(self._hud_speed_text,
                        text=("%.0f" % (pspd * 3.6)))
            palt = ppos[2]
            update_text(self._hud_altitude_text,
                        text=("%.0f" % (round(palt / 10) * 10)))
            potralt = self.world.otr_altitude(ppos)
            if potralt < self._hud_radar_altitude_threshold:
                self._hud_radar_altitude_text.show()
                update_text(self._hud_radar_altitude_text,
                            text=("%.0f" % potralt))
            else:
                self._hud_radar_altitude_text.hide()

        self._hud_wait_heading -= dt
        if self._hud_wait_heading <= 0.0:
            self._hud_wait_heading = self._hud_heading_period
            phdg = to_navhead(phpr[0])
            hshw = self._hud_heading_scale_hdgwidth * 0.5
            phdgm = phdg if phdg < 180 else (phdg - 360)
            self._update_hud_hdgvis(self._hud_navhdg_prev_phdgm, hshw, show=False,
                                    i0=self._hud_navhdg_prev_phdgm_ind)
            phdgm_ind = self._update_hud_hdgvis(phdgm, hshw, show=True)
            self._hud_navhdg_prev_phdgm = phdgm
            self._hud_navhdg_prev_phdgm_ind = phdgm_ind
            sx = -phdgm * self._hud_heading_scale_hdg2scr
            self._hud_heading_scale_node.setX(sx)

        self._hud_wait_pitch -= dt
        if self._hud_wait_pitch <= 0.0:
            self._hud_wait_pitch = self._hud_pitch_period
            ptc = parent.dynstate.pch
            ptcmlim = self._hud_pitch_ptclim
            ptcm = clamp(ptc, -ptcmlim, ptcmlim)
            sz = -ptcm * self._hud_pitch_ptc2scr
            self._hud_horizon_node.setZ(sz)
            update_text(self._hud_pitch_text,
                        text=("% .0f" % degrees(ptc)))

        self._hud_wait_roll -= dt
        if self._hud_wait_roll <= 0.0:
            self._hud_wait_roll = self._hud_roll_period
            sroll = parent.dynstate.bnk
            self._hud_roll_attitude_node.setR(degrees(sroll))

        self._hud_wait_stall -= dt
        if self._hud_wait_stall <= 0.0:
            self._hud_wait_stall = self._hud_stall_period
            self._hud_stall_on = parent.stalled
        if self._hud_stall_on:
            if int(self.world.time / self._hud_stall_blink_rate) % 2 == 0:
                self._hud_stall_text.show()
            else:
                self._hud_stall_text.hide()
        else:
            self._hud_stall_text.hide()
        self._hud_stall_sound.set_state(self._hud_stall_on)

        if self.hud_mode == "nav":
            self._hud_waypoint_node.show()

            self.player.helmet.target_contact = None

            if self._current_waypoint:
                self._hud_wait_waypoint -= dt
                if self._hud_wait_waypoint <= 0.0:
                    self._hud_wait_waypoint = self._hud_waypoint_period
                    if self._hud_prev_waypoint != self._current_waypoint:
                        if self._hud_prev_waypoint:
                            self._hud_navbar_nodes[self._hud_prev_waypoint].hide()
                        self._hud_prev_waypoint = self._current_waypoint
                    self._hud_navbar_nodes[self._current_waypoint].show()
                    nhead = self._current_waypoint_head
                    ndist = self._current_waypoint_dist
                    ndalt = self._current_waypoint_dalt
                    val = self._hud_navbar_subnodes[self._current_waypoint]
                    namend, headnd, distnd, daltnd = val
                    update_text(headnd, text=("%.0f" % to_navhead(nhead)))
                    update_text(distnd, text=_rn("%.1f" % (ndist / 1000)))
                    if daltnd is not None:
                        update_text(daltnd,
                                    text=("% .0f" % (round(ndalt / 10) * 10)))

        else:
            self._hud_waypoint_node.hide()
            self._hud_wait_waypoint = 0.0

        if self.hud_mode in ("atk", "gnd"):
            self._hud_attack_node.show()

            target = self.player.helmet.target_body

            hastarget = (target and target.alive)
            if hastarget:
                toff = self.player.helmet.target_offset
                tpos = target.pos(offset=toff)
                thpr = target.hpr()

            if selwp and isinstance(selwp.handle, (Cannon, PodLauncher)):
                self._hud_crosshair_node.show()
            else:
                self._hud_crosshair_node.hide()
            #if selwp and isinstance(selwp.handle, Launcher) and selwp.handle.mtype.seeker:
                #self._hud_missile_seeker_node.show()
            #else:
                #self._hud_missile_seeker_node.hide()
            #if selwp and isinstance(selwp.handle, Dropper):
                #self._hud_bomb_pip_node.show()
            #else:
                #self._hud_bomb_pip_node.hide()

            self._hud_wait_target_altspd -= dt
            if self._hud_wait_target_altspd <= 0.0:
                self._hud_wait_target_altspd = self._hud_target_altspd_period
                if hastarget and self.hud_mode == "atk":
                    self._hud_target_speed_text.show()
                    self._hud_target_altitude_text.show()
                    self._hud_target_relhdg_node.show()
                    if isinstance(target, Plane):
                        #tspd = target.dynstate.v
                        tspd = target.dynstate.vias
                    else:
                        tspd = target.speed()
                    update_text(self._hud_target_speed_text,
                                text=("%.0f" % (tspd * 3.6)))
                    talt = tpos[2]
                    update_text(self._hud_target_altitude_text,
                                text=("%.0f" % (round(talt / 10) * 10)))
                    relthdg = thpr[0] - phpr[0]
                    sr = 180 - relthdg
                    self._hud_target_relhdg_node.setR(sr)
                else:
                    self._hud_target_speed_text.hide()
                    self._hud_target_altitude_text.hide()
                    self._hud_target_relhdg_node.hide()

            self._hud_wait_target_range -= dt
            if self._hud_wait_target_range <= 0.0:
                self._hud_wait_target_range = self._hud_target_range_period
                if hastarget:
                    self._hud_target_range_scalemax_text.show()
                    self._hud_target_range_indicator_node.show()
                    trng = (tpos - ppos).length()
                    tscmax = 250000.0
                    while True:
                        if tscmax / 5 < trng:
                            break
                        tscmax /= 5
                    ndec = 0 if tscmax >= 1000.0 else 1
                    update_text(self._hud_target_range_scalemax_text,
                                text=_rn(("%%.%df" % ndec) % (tscmax / 1000)))
                    scrmax = self._hud_target_range_scale_scrlim
                    rng2scr = scrmax / tscmax
                    z0 = self._hud_target_range_indicator_base_z
                    offz = trng * rng2scr
                    sz = z0 + offz
                    self._hud_target_range_indicator_node.setZ(sz)
                    if isinstance(selwp.handle, Launcher) and selwp.handle.mtype.seeker:
                        self._hud_target_range_rmax_node.show()
                        self._hud_target_range_rman_node.show()
                        self._hud_target_range_rmin_node.show()
                        launcher = selwp.handle
                        mtype = launcher.mtype
                        ret = mtype.launch_limits(parent, target, toff)
                        rmin, rman, rmax = ret[:3]
                        sz = z0 + clamp((rmax or 0.0) * rng2scr, 0.0, scrmax)
                        self._hud_target_range_rmax_node.setZ(sz)
                        sz = z0 + clamp((rman or 0.0) * rng2scr, 0.0, scrmax)
                        self._hud_target_range_rman_node.setZ(sz)
                        sz = z0 + clamp((rmin or 0.0) * rng2scr, 0.0, scrmax)
                        self._hud_target_range_rmin_node.setZ(sz)
                    #elif isinstance(selwp.handle, Dropper):
                    else:
                        self._hud_target_range_rmax_node.hide()
                        self._hud_target_range_rman_node.hide()
                        self._hud_target_range_rmin_node.hide()
                else:
                    self._hud_target_range_scalemax_text.hide()
                    self._hud_target_range_indicator_node.hide()
                    self._hud_target_range_rmax_node.hide()
                    self._hud_target_range_rman_node.hide()
                    self._hud_target_range_rmin_node.hide()

            if selwp and isinstance(selwp.handle, (Launcher, Dropper, PodLauncher)):
                self._hud_wait_pylons -= dt
                if self._hud_wait_pylons <= 0.0:
                    self._hud_wait_pylons = self._hud_pylons_period
                    self._hud_pylons_node.show()
                    for rndnd in self._hud_pylons_round_nodes:
                        rndnd.hide()
                    #for rrdnd in self._hud_pylons_round_ready_nodes:
                        #rrdnd.hide()
                    self._hud_launch_auth_text.hide()
                    if isinstance(selwp.handle, Launcher):
                        launcher = selwp.handle
                        points = launcher.points
                        pylwptype = launcher.mtype
                        if target is None and self.has_boresight:
                            target = self.boresight_target
                        rst, fpoints = launcher.ready(target)
                        subrounds = None
                    elif isinstance(selwp.handle, Dropper):
                        dropper = selwp.handle
                        points = dropper.points
                        pylwptype = dropper.btype
                        rst, fpoints = dropper.ready()
                        subrounds = None
                    elif isinstance(selwp.handle, PodLauncher):
                        podlauncher = selwp.handle
                        points = podlauncher.points
                        pylwptype = podlauncher.ptype.rtype
                        #rst, fpoints = podlauncher.ready()
                        rst, fpoints = None, [] # don't show ready state
                        subrounds = podlauncher.rounds
                    else:
                        raise StandardError(
                            "Unknown pylon handler type %s." %
                            type(selwp.handle))
                    for pyl in points:
                        self._hud_pylons_round_nodes[pyl].show()
                    if rst == "ready":
                        self._hud_launch_auth_text.show()
                        #for pyl in fpoints:
                            #self._hud_pylons_round_ready_nodes[pyl].show()
                    update_text(self._hud_pylons_weapon_text,
                                text=select_des(pylwptype.shortdes,
                                                pylwptype.cpitdes, self._lang))
                    if subrounds is not None:
                        self._hud_pylons_counter_text.show()
                        update_text(self._hud_pylons_counter_text,
                                    text=("%d" % subrounds))
                    else:
                        self._hud_pylons_counter_text.hide()
            else:
                self._hud_pylons_node.hide()
                self._hud_pylons_counter_text.hide()

            if selwp and isinstance(selwp.handle, Cannon):
                self._hud_gun_node.show()
                cannon = selwp.handle

                self._hud_wait_gun_data -= dt
                if self._hud_wait_gun_data <= 0.0:
                    self._hud_wait_gun_data = self._hud_gun_data_period
                    update_text(self._hud_gun_name_text,
                                text=select_des(cannon.shortdes,
                                                cannon.cpitdes, self._lang))
                    update_text(self._hud_gun_counter_text,
                                text=("%d" % cannon.ammo))

                self._hud_wait_gun_lead -= dt
                if self._hud_wait_gun_lead <= 0.0:
                    self._hud_wait_gun_lead = self._hud_gun_lead_period
                    show_lead = False
                    if hastarget:
                        tdist = (tpos - ppos).length()
                        if tdist <= self._hud_gun_lead_outrange:
                            ret = _gun_lead(self.world, parent, cannon,
                                            target, toff)
                            if ret:
                                anglh, anglv, angth, angtv = ret
                                tanmaxang = tan(self._hud_gun_lead_hvfov)
                                sx = tan(anglh) / tanmaxang
                                sz = tan(anglv) / tanmaxang
                                if COCKPIT_FOV != OUTSIDE_FOV:
                                    wfov = radians(self.player.headchaser.fov)
                                    cfov = radians(self._camlens.getMinFov())
                                    wcfovfac = tan(0.5 * cfov) / tan(0.5 * wfov)
                                    sx *= wcfovfac
                                    sz *= wcfovfac
                                if (abs(sx) < self._hud_gun_lead_projoff_max and
                                    abs(sz) < self._hud_gun_lead_projoff_max):
                                    show_lead = True
                    if show_lead:
                        #self._hud_attitude_node.hide()
                        #self._hud_crosshair_node.hide()
                        self._hud_gun_lead_node.show()
                        self._hud_gun_lead_node.setX(sx)
                        self._hud_gun_lead_node.setZ(sz)
                        if self._hud_gun_lead_vis == 0:
                            tvel = target.vel()
                            shspeed = cannon.mzvel
                            shrange = cannon.effrange
                            shtime = shrange / shspeed
                            shtime *= 0.9 # for safety
                            rmax = max_intercept_range(tpos, tvel, ppos, shspeed, shtime) or 0.0
                            sr = -270 + 360 * (tdist / self._hud_gun_lead_outrange)
                            self._hud_gun_lead_range_indicator_node.setR(sr)
                            sr = -270 + 360 * (rmax / self._hud_gun_lead_outrange)
                            self._hud_gun_lead_rmax_node.setR(sr)
                        elif self._hud_gun_lead_vis == 1:
                            rind = int(round(tdist * self._hud_gun_lead_range_dist_mul))
                            rind = min(rind, self._hud_gun_lead_range_index_max)
                            rind_prev = self._hud_gun_lead_range_index
                            if rind_prev >= 0:
                                self._hud_gun_lead_range_nodes[rind_prev].hide()
                            self._hud_gun_lead_range_nodes[rind].show()
                            self._hud_gun_lead_range_index = rind
                        self._hud_gun_lead_data = (anglh, anglv, angth, angtv)
                    else:
                        #self._hud_attitude_node.show()
                        #self._hud_crosshair_node.show()
                        self._hud_gun_lead_node.hide()
            else:
                self._hud_gun_node.hide()

        else:
            self._hud_attack_node.hide()
            self._hud_wait_target_altspd = 0.0
            self._hud_wait_target_range = 0.0
            self._hud_wait_pylons = 0.0
            self._hud_wait_gun_lead = 0.0


    def _update_hud_hdgvis (self, phdgm, hshw, show, i0=None):

        numhdgs = len(self._hud_navhdg_hdgs)
        if i0 < 0:
            i0 = bisect(self._hud_navhdg_hdgs, phdgm)
        for k in (-1, 1):
            i = i0
            while True:
                shdg = self._hud_navhdg_hdgs[i]
                snode = self._hud_navhdg_marks[i]
                if abs(shdg - phdgm) < hshw:
                    if show:
                        snode.show()
                    else:
                        snode.hide()
                else:
                    break
                i += k
                if i < 0:
                    i = numhdgs - 1
                elif i >= numhdgs:
                    i = 0
        return i0


    def _init_warnrec (self):

        warnlampnd = self._model.find("**/lamp_masterwarning")
        if warnlampnd.isEmpty():
            return False

        self._instr_update_fs.append(self._update_warnrec)
        self._instr_cleanup_fs.append(self._cleanup_warnrec)

        self._warnrec_incoming_range = 8000.0 # keep equal to _imt_rocket_fardist?

        self._warnrec_update_period = 0.93
        self._warnrec_wait_update = 0.0
        self._warnrec_tracker_families = ("rocket",)
        self._warnrec_locking_families = ("plane", "turret")
        self._warnrec_active = False
        self._warnrec_prev_active = None

        self._warnrec_lamp_node = warnlampnd
        set_texture(self._warnrec_lamp_node,
            texture="images/cockpit/cockpit_mig29_lamp_red_tex.png",
            normalmap="images/_normalmap_none.png",
            glossmap="images/cockpit/cockpit_mig29_lamp_gls.png",
            glowmap="images/cockpit/cockpit_mig29_lamp_gw.png")
        self._warnrec_lamp_base_color = rgba(255, 0, 0, 1.0)
        self._warnrec_lamp_light = AutoPointLight(
            parent=self, color=Vec4(), radius=0.06, halfat=0.3,
            subnode=self._warnrec_lamp_node, pos=Point3(0.0, -0.006, 0.0),
            selfmanaged=True, name="warnrec")
        pntli = self._last_assigned_point_light_index + 1
        assert pntli < self._max_point_lights
        self.node.setShaderInput(self._shdinp.pntlns[pntli],
                                 self._warnrec_lamp_light.node)

        self._warnrec_blink_period = 0.1
        self._warnrec_wait_blink = 0.0
        self._warnrec_lamp_on = True

        self._warnrec_tracker_sound = Sound2D(
            path="audio/sounds/flight-missile-warning.ogg",
            world=self.world, pnode=self.node,
            volume=0.6, loop=True, fadetime=0.1)
        self._warnrec_locking_sound = Sound2D(
            path="audio/sounds/flight-missile-locking.ogg",
            world=self.world, pnode=self.node,
            volume=0.4, loop=True, fadetime=0.1)
        self._warnrec_sound = None

        return True


    def _cleanup_warnrec (self):

        pass


    def _update_warnrec (self, dt):

        self._warnrec_wait_update -= dt
        if self._warnrec_wait_update <= 0.0:
            self._warnrec_wait_update += self._warnrec_update_period

            acp = self.player.ac
            self._warnrec_active = False

            # Check for tracking missiles.
            if not self._warnrec_active:
                trackers = []
                for family in self._warnrec_tracker_families:
                    for body in self.world.iter_bodies(family):
                        if not body.alive:
                            continue
                        if (body.target is acp and
                            body.dist(acp) < self._warnrec_incoming_range):
                            trackers.append(body)
                            break # need only yes/no
                if trackers:
                    self._warnrec_active = "incoming"

            # Check for radars locking a missile.
            if not self._warnrec_active:
                trackers = []
                for family in self._warnrec_locking_families:
                    for body in self.world.iter_bodies(family):
                        if not body.alive:
                            continue
                        if body.sensorpack:
                            cntsbdy = body.sensorpack.contacts_by_body()
                            senscnt = body.sensorpack.sensors_by_contact()
                            contact = cntsbdy.get(acp)
                            if (contact and "radar" in senscnt.get(contact)):
                                for launcher in body.launchers:
                                    if launcher.is_locking(acp):
                                        trackers.append(body)
                                        break # need only yes/no
                if trackers:
                    self._warnrec_active = "locking"

            if self._warnrec_active != self._warnrec_prev_active:
                self._warnrec_prev_active = self._warnrec_active
                if self._warnrec_sound:
                    self._warnrec_sound.set_state(0)

                if self._warnrec_active == "incoming":
                    self._warnrec_wait_blink = 0.0
                    self._warnrec_lamp_on = False
                    self._warnrec_sound = self._warnrec_tracker_sound
                elif self._warnrec_active == "locking":
                    self._warnrec_lamp_on = True
                    self._warnrec_sound = self._warnrec_locking_sound
                elif not self._warnrec_active:
                    self._warnrec_lamp_on = False
                    self._warnrec_sound = None
                else:
                    assert False

                if self._warnrec_sound:
                    self._warnrec_sound.set_state(1)

                if self._warnrec_lamp_on:
                    self._warnrec_lamp_light.update(color=self._warnrec_lamp_base_color)
                    self._warnrec_lamp_node.setShaderInput(self._shdinp.glowfacn, 1.0)
                else:
                    self._warnrec_lamp_light.update(color=Vec4(0, 0, 0, 0))
                    self._warnrec_lamp_node.setShaderInput(self._shdinp.glowfacn, 0.0)

        if self._warnrec_active == "incoming":
            self._warnrec_wait_blink -= dt
            if self._warnrec_wait_blink <= 0.0:
                self._warnrec_wait_blink += self._warnrec_blink_period
                self._warnrec_lamp_on = not self._warnrec_lamp_on
                if self._warnrec_lamp_on:
                    self._warnrec_lamp_light.update(color=self._warnrec_lamp_base_color)
                    self._warnrec_lamp_node.setShaderInput(self._shdinp.glowfacn, 1.0)
                else:
                    self._warnrec_lamp_light.update(color=Vec4(0, 0, 0, 0))
                    self._warnrec_lamp_node.setShaderInput(self._shdinp.glowfacn, 0.0)


    def _init_power (self):

        if False:
            return False
        self._instr_update_fs.append(self._update_power)
        self._instr_cleanup_fs.append(self._cleanup_power)

        # Afterburner light.
        self._power_aftburn_lamp = self._model.find("**/lamp_afterburner")
        if not self._power_aftburn_lamp.isEmpty():
            self._power_aftburn_prev_throttle = None
            self._power_aftburn_update_period = 0.13
            self._power_aftburn_wait_update = 0.0
            set_texture(self._power_aftburn_lamp,
                texture="images/cockpit/cockpit_mig29_lamp_red_tex.png",
                normalmap="images/_normalmap_none.png",
                glossmap="images/cockpit/cockpit_mig29_lamp_gls.png",
                glowmap="images/cockpit/cockpit_mig29_lamp_gw.png")
            # self._power_aftburn_light = AutoPointLight(
                # parent=self, color=Vec4(), radius=0.04, halfat=0.2,
                # subnode=self._power_aftburn_lamp, pos=Point3(0.0, -0.006, 0.0),
                # selfmanaged=True, name="power-aftburn")
            # pntli = self._last_assigned_point_light_index + 1
            # assert pntli < self._max_point_lights
            # self.node.setShaderInput(self._shdinp.pntlns[pntli],
                                     # self._power_aftburn_light.node)

        else:
            self._power_aftburn_lamp = None

        return True


    def _cleanup_power (self):

        pass


    def _update_power (self, dt):

        if self._power_aftburn_lamp is not None:
            self._power_aftburn_wait_update -= dt
            if self._power_aftburn_wait_update <= 0.0:
                self._power_aftburn_wait_update = self._power_aftburn_update_period
                pthr = self.player.ac.dynstate.tl
                if self._power_aftburn_prev_throttle is None:
                    self._power_aftburn_prev_throttle = 2.0 - pthr
                if self._power_aftburn_prev_throttle <= 1.0 and pthr > 1.0:
                    # Afterburner on.
                    # self._power_aftburn_light.update(color=rgba(255, 0, 0, 1.0))
                    self._power_aftburn_lamp.setShaderInput(self._shdinp.glowfacn, 1.0)
                elif self._power_aftburn_prev_throttle > 1.0 and pthr <= 1.0:
                    # Afterburner off.
                    # self._power_aftburn_light.update(color=rgba(0, 0, 0, 1.0))
                    self._power_aftburn_lamp.setShaderInput(self._shdinp.glowfacn, 0.0)
                self._power_aftburn_prev_throttle = pthr


    def _init_weapons (self):

        if False:
            return False
        self._instr_update_fs.append(self._update_weapons)
        self._instr_cleanup_fs.append(self._cleanup_weapons)

        # Gun counter.
        guncntnd = self._model.find("**/ammo_screen")
        self._weapons_has_gun_counter = not guncntnd.isEmpty() and self.player.ac.cannons
        if self._weapons_has_gun_counter:
            self._weapons_has_gun_counter = True
            ret = self._txscmgr.set_texscene(
                node=guncntnd, texsize=128,
                bgimg="images/ui/black.png",
                uvoffscn=self._shdinp.uvoffscn,
                name="gun-counter")
            set_texture(guncntnd,
                        normalmap="images/_normalmap_none.png",
                        glossmap="images/_glossmap_none.png",
                        glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
            guncntnd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
            self._instr_night_light_nodes.append(guncntnd)
            self._weapons_gun_counter_scene = ret
            self._weapons_gun_counter_font = "fonts/red-october-regular.otf"
            #self._weapons_gun_counter_font = "fonts/DidactGothic.ttf"
            self._weapons_gun_counter_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)
            self._weapons_gun_counter_text = make_text(
                width=1.6, pos=Point3(0.0, 0.0, 0.0),
                font=self._weapons_gun_counter_font, size=150,
                color=self._weapons_gun_counter_color,
                align="c", anchor="mc",
                parent=self._weapons_gun_counter_scene)
            self._weapons_gun_counter_prev_count = None
            self._weapons_gun_counter_update_period = 0.21
            self._weapons_gun_counter_wait_update = 0.0

        # !!! Temporary
        remove_subnodes(self._model, ("lamp_pylon_l4", "lamp_pylon_r4"))

        # Pylon lights.
        npyl = len(self.player.ac.pylons)
        self._weapons_pylons_lamp_nodes = []
        for i in range(npyl):
            if npyl % 2 == 0:
                if i % 2 == 0:
                    i1 = (npyl - i) // 2 - 1
                    sn = "l"; so = npyl // 2 - i1
                else:
                    i1 = (npyl + i) // 2
                    sn = "r"; so = i1 - npyl // 2 + 1
            else:
                if i == 0:
                    sn = "c"; so = 0
                elif i % 2 == 1:
                    i1 = (npyl - i) // 2
                    sn = "l"; so = npyl // 2 - i1 + 1
                else:
                    i1 = (npyl + i) // 2 - 1
                    sn = "r"; so = i1 - npyl // 2 + 1
            plnd = self._model.find("**/lamp_pylon_%s%d" % (sn, so))
            if plnd.isEmpty():
                plnd = None
            self._weapons_pylons_lamp_nodes.append(plnd)
        if any(x is not None for x in self._weapons_pylons_lamp_nodes):
            self._weapons_pylons_wait_update = 0.0
            self._weapons_pylons_update_period = 0.23
            npls = len(self._weapons_pylons_lamp_nodes)
            for plnd in self._weapons_pylons_lamp_nodes:
                if plnd is None:
                    continue
                set_texture(plnd,
                    texture="images/cockpit/cockpit_mig29_lamp_red_tex.png",
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/cockpit/cockpit_mig29_lamp_gls.png",
                    glowmap="images/cockpit/cockpit_mig29_lamp_gw.png")
                plnd.setShaderInput(self._shdinp.glowfacn, 0.0)
            self._weapons_pylons_lamp_on = [False] * npls
        else:
            self._weapons_pylons_lamp_nodes = []

        return True


    def _cleanup_weapons (self):

        if self._weapons_has_gun_counter:
            self._weapons_gun_counter_scene.removeNode()


    def _update_weapons (self, dt):

        if self._weapons_pylons_lamp_nodes:
            self._weapons_pylons_wait_update -= dt
            if self._weapons_pylons_wait_update <= 0.0:
                self._weapons_pylons_wait_update = self._weapons_pylons_update_period
                # - collect occupied pylons
                points = set()
                for wp in self.player.weapons:
                    if wp.onpylons:
                        points.update(wp.handle.points)
                # - turn lights on and off
                for i, plnd in enumerate(self._weapons_pylons_lamp_nodes):
                    if not plnd:
                        continue
                    if i in points and not self._weapons_pylons_lamp_on[i]:
                        plnd.setShaderInput(self._shdinp.glowfacn, 1.0)
                        self._weapons_pylons_lamp_on[i] = True
                    elif i not in points and self._weapons_pylons_lamp_on[i]:
                        plnd.setShaderInput(self._shdinp.glowfacn, 0.0)
                        self._weapons_pylons_lamp_on[i] = False

        if self._weapons_has_gun_counter:
            self._weapons_gun_counter_wait_update -= dt
            if self._weapons_gun_counter_wait_update <= 0.0:
                self._weapons_gun_counter_wait_update = self._weapons_gun_counter_update_period
                refcannon = self.player.ac.cannons[0] #!!!
                if self._weapons_gun_counter_prev_count != refcannon.ammo:
                    self._weapons_gun_counter_prev_count = refcannon.ammo
                    update_text(self._weapons_gun_counter_text,
                                text=("%03d" % min(refcannon.ammo, 999)))


    def _init_boresight (self):

        if False:
            return False
        self._instr_update_fs.append(self._update_boresight)
        self._instr_cleanup_fs.append(self._cleanup_boresight)

        self._boresight_on = False

        self._boresight_target_families = (
            "plane",
        )
        self._boresight_maxdist = 10000.0
        self._boresight_maxang = radians(2.5)

        # Targeting sounds.
        self._boresight_locking_sound = Sound2D(
            path="audio/sounds/flight-locking-target.ogg", loop=True,
            world=self.world, pnode=self.node, volume=0.2, fadetime=0.01)
        self._boresight_ready_sound = Sound2D(
            path="audio/sounds/flight-lock-target.ogg", loop=True,
            world=self.world, pnode=self.node, volume=0.2, fadetime=0.01)

        self._boresight_update_period = 0.37
        self._boresight_wait_update = 0.0

        self.boresight_target = None

        return True


    def _cleanup_boresight (self):

        pass


    def _update_boresight (self, dt):

        # FIXME: What now when passive sensors (e.g. IRST) are available too?
        return

        boresight_on = True
        if self.player.ac.sensorpack.emissive:
            boresight_on = False
        elif self.player.input_select_weapon < 0:
            boresight_on = False
        else:
            selwp = self.player.weapons[self.player.input_select_weapon]
            if not (isinstance(selwp.handle, Launcher) and selwp.handle.mtype.seeker):
                boresight_on = False

        if self._boresight_on != boresight_on:
            self._boresight_on = boresight_on
            if not boresight_on:
                self.boresight_target = None
                self._boresight_locking_sound.stop()
                self._boresight_ready_sound.stop()
        if not self._boresight_on:
            return

        self._boresight_wait_update -= dt
        if self._boresight_wait_update <= 0.0:
            self._boresight_wait_update = self._boresight_update_period

            bodies_in_bore = []
            wp_against = selwp.against()
            for family in self._boresight_target_families:
                if family in wp_against:
                    for body in self.world.iter_bodies(family):
                        if not body.alive:
                            continue
                        bdist = self.player.ac.dist(body)
                        boffb = self.player.ac.offbore(body)
                        if (bdist < self._boresight_maxdist and
                            boffb < self._boresight_maxang):
                            bodies_in_bore.append((bdist, body))
            if bodies_in_bore:
                self.boresight_target = sorted(bodies_in_bore)[0][1]
            else:
                self.boresight_target = None

            play_locking_sound = False
            play_ready_sound = False
            if self.boresight_target:
                launcher = selwp.handle
                rst, rnds = launcher.ready(target=self.boresight_target,
                                           locktimefac=1.5)
                if rst in ("locking", "locked"):
                    play_locking_sound = True
                elif rst == "ready":
                    play_ready_sound = True
            self._boresight_locking_sound.set_state(play_locking_sound)
            self._boresight_ready_sound.set_state(play_ready_sound)


    def _init_compass (self):

        screennd = self._model.find("**/compass_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_compass)
        self._instr_cleanup_fs.append(self._cleanup_compass)

        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)
        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="compass")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        bar_height = 0.5
        bar_tex_parth = 1.0 / 9.0
        bar_tex_partw = 3.5 / 12.0
        bar_geom = make_raw_quad(
            szext=(-1.0, -bar_height, 1.0, bar_height),
            uvext=(-0.5 * bar_tex_partw, 0.0, 0.5 * bar_tex_partw, bar_tex_parth))
        self._compass_bar_node = scenend.attachNewNode(bar_geom)
        self._compass_bar_node.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(self._compass_bar_node,
            texture="images/cockpit/cockpit_mig29_compass_bar_tex.png",
            clamp=False, filtr=False)

        marker_height = 0.7
        marker_width = 0.03
        marker_geom = make_raw_quad(
            szext=(-marker_width, -marker_height, marker_width, marker_height))
        marker_node = scenend.attachNewNode(marker_geom)
        marker_node.setTransparency(TransparencyAttrib.MAlpha)
        marker_node.setSa(0.5)
        marker_node.setColor(rgba(255, 0, 0, 1))

        self._compass_update_period = 0.117
        self._compass_wait_update = 0.0

        return True


    def _cleanup_compass (self):

        pass


    def _update_compass (self, dt):

        self._compass_wait_update -= dt
        if self._compass_wait_update <= 0.0:
            self._compass_wait_update += self._compass_update_period

            phpr = self.player.ac.hpr()
            phdg = to_navhead(phpr[0])
            offu = phdg / 360
            self._compass_bar_node.setTexOffset(texstage_color, offu, 0.0)


    def _init_fuelpanel (self):

        screennd = self._model.find("**/fuelpanel_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_fuelpanel)
        self._instr_cleanup_fs.append(self._cleanup_fuelpanel)

        glassnd = self._model.find("**/fuelpanel_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)
        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="fuelpanel")
        self._fuelpanel_scene = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        zoomnd = self._fuelpanel_scene.attachNewNode("zoom")
        zoomnd.setScale(1.14)

        fuelscalend = make_quad(parent=zoomnd, size=2.0)
        fuelscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(fuelscalend,
            texture="images/cockpit/cockpit_mig29_fuelpanel_scale_tex.png",
            filtr=False)

        bar1_bpos = Point3(-0.190, 0.0, -0.800)
        bar1_height = 1.600
        bar1_width = 0.060
        bar1_fuel = 4000.0
        bar1_geom = make_raw_quad(
            szext=(-0.5 * bar1_width, 0.0, 0.5 * bar1_width, bar1_height))
        bar1_node = zoomnd.attachNewNode(bar1_geom)
        bar1_node.setColor(rgba(255, 0, 0, 1))
        bar1_node.setPos(bar1_bpos)
        self._fuelpanel_bar1_node = bar1_node
        self._fuelpanel_bar1_fuel = bar1_fuel

        bar2_bpos = Point3(0.070, 0.0, 0.200)
        bar2_height = 0.600
        bar2_width = 0.060
        bar2_fuel = 1500.0
        bar2_geom = make_raw_quad(
            szext=(-0.5 * bar2_width, 0.0, 0.5 * bar2_width, bar2_height))
        bar2_node = zoomnd.attachNewNode(bar2_geom)
        bar2_node.setColor(rgba(255, 0, 0, 1))
        bar2_node.setPos(bar2_bpos)
        self._fuelpanel_bar2_node = bar2_node
        self._fuelpanel_bar2_fuel = bar2_fuel

        self._fuelpanel_update_period = 1.17
        self._fuelpanel_wait_update = 0.0

        return True


    def _cleanup_fuelpanel (self):

        pass


    def _update_fuelpanel (self, dt):

        self._fuelpanel_wait_update -= dt
        if self._fuelpanel_wait_update <= 0.0:
            self._fuelpanel_wait_update += self._fuelpanel_update_period

            fuel = self.player.ac.fuel

            fuel1 = max(min(fuel, self._fuelpanel_bar1_fuel), 0.0)
            sz1 = fuel1 / self._fuelpanel_bar1_fuel
            self._fuelpanel_bar1_node.setSz(sz1)

            fuel2 = max(min(fuel - fuel1, self._fuelpanel_bar2_fuel), 0.0)
            self._fuelpanel_bar2_node.setSz(fuel2 / self._fuelpanel_bar2_fuel)


    def _init_tachometer (self):

        screennd = self._model.find("**/tachometer_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_tachometer)
        self._instr_cleanup_fs.append(self._cleanup_tachometer)

        glassnd = self._model.find("**/tachometer_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="tachometer")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        scalend = make_quad(parent=scenend, size=2.0)
        scalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(scalend,
            texture="images/cockpit/cockpit_mig29_tachometer_scale_tex.png",
            filtr=False)

        angd0 = degrees(atan2(1040 - 500, 1140 - 500))
        angd1 = degrees(atan2(1080 - 500, 500 - 500))
        angd1ab = degrees(atan2(1080 - 500, 860 - 500))
        self._tachometer_hand_roll0 = -angd0
        self._tachometer_hand_roll1 = 360 - angd1
        self._tachometer_hand_roll1ab = 360 - angd1ab
        tachhandnd = make_quad(parent=scenend, size=2.0)
        tachhandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(tachhandnd,
            texture="images/cockpit/cockpit_mig29_tachometer_hand_tex.png",
            filtr=False)
        self._tachometer_hand_node = tachhandnd

        self._tachometer_update_period = 0.043
        self._tachometer_wait_update = 0.0

        return True


    def _cleanup_tachometer (self):

        pass


    def _update_tachometer (self, dt):

        self._tachometer_wait_update -= dt
        if self._tachometer_wait_update <= 0.0:
            self._tachometer_wait_update += self._tachometer_update_period

            pthr = self.player.ac.dynstate.tl
            if pthr <= 1.0:
                roll0 = self._tachometer_hand_roll0
                roll1 = self._tachometer_hand_roll1
                ifac = pthr
            else:
                roll0 = self._tachometer_hand_roll1
                roll1 = self._tachometer_hand_roll1ab
                ifac = (pthr - 1.0) / (2.0 - 1.0)
            roll = roll0 + ifac * (roll1 - roll0)
            self._tachometer_hand_node.setR(roll)


    def _init_airclock (self):

        screennd = self._model.find("**/airclock_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_airclock)
        self._instr_cleanup_fs.append(self._cleanup_airclock)

        glassnd = self._model.find("**/airclock_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png",
                #filtr=False)

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="airclock")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        scalend = make_quad(parent=scenend, size=2.0)
        scalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(scalend,
            texture="images/cockpit/cockpit_mig29_airclock_scale_tex.png",
            filtr=False)

        hsize_upper = 2.0 * float(500) / 1000
        hcenter_upper = Point3(0.0, 0.0, float(725 - 500) / 500)
        hnode = make_quad(parent=scenend, size=hsize_upper)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_upper_hour_tex.png",
            filtr=False)
        hnode.setPos(hcenter_upper)
        self._airclock_hand_upper_hour_node = hnode
        hnode = make_quad(parent=scenend, size=hsize_upper)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_upper_minute_tex.png",
            filtr=False)
        hnode.setPos(hcenter_upper)
        self._airclock_hand_upper_minute_node = hnode

        hsize_lower = 2.0 * float(500) / 1000
        hcenter_lower = Point3(0.0, 0.0, float(280 - 500) / 500)
        hnode = make_quad(parent=scenend, size=hsize_lower)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_lower_minute_tex.png",
            filtr=False)
        hnode.setPos(hcenter_lower)
        self._airclock_hand_lower_minute_node = hnode

        hnode = make_quad(parent=scenend, size=2.0)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_main_hour_tex.png",
            filtr=False)
        self._airclock_hand_main_hour_node = hnode
        hnode = make_quad(parent=scenend, size=2.0)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_main_minute_tex.png",
            filtr=False)
        self._airclock_hand_main_minute_node = hnode
        hnode = make_quad(parent=scenend, size=2.0)
        hnode.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(hnode,
            texture="images/cockpit/cockpit_mig29_airclock_hand_main_second_tex.png",
            filtr=False)
        self._airclock_hand_main_second_node = hnode

        self._airclock_day_seconds = None

        return True


    def _cleanup_airclock (self):

        pass


    def _update_airclock (self, dt):

        day_seconds = int(self.world.day_time)
        if day_seconds != self._airclock_day_seconds:
            self._airclock_day_seconds = day_seconds

            dhr = day_seconds // 3600
            dmn = (day_seconds - dhr * 3600) // 60
            dsc = day_seconds - dhr * 3600 - dmn * 60
            self._airclock_hand_main_hour_node.setR(dhr * 360.0 / 12.0)
            self._airclock_hand_main_minute_node.setR(dmn * 360.0 / 60.0)
            self._airclock_hand_main_second_node.setR(dsc * 360.0 / 60.0)


    def _init_radaraltimeter (self):

        screennd = self._model.find("**/radaraltimeter_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_radaraltimeter)
        self._instr_cleanup_fs.append(self._cleanup_radaraltimeter)

        glassnd = self._model.find("**/radaraltimeter_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="radaraltimeter")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        scalend = make_quad(parent=scenend, size=2.0)
        scalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(scalend,
            texture="images/cockpit/cockpit_mig29_radaraltimeter_scale_tex.png",
            filtr=False)

        hand_roll_map = sorted([
            (0.0, degrees(atan2(1080 - 500, 500 - 500))),
            (100.0, degrees(atan2(340 - 500, 1120 - 500))),
            (150.0, degrees(atan2(-80 - 500, 760 - 500))),
            (200.0, degrees(atan2(-280 - 500, 480 - 500))),
            (300.0, degrees(atan2(-100 - 500, 40 - 500))),
            (400.0, degrees(atan2(160 - 500, -100 - 500))),
            (600.0, degrees(atan2(500 - 500, -160 - 500))),
            (800.0, degrees(atan2(680 - 500, -120 - 500))),
            (1000.0, degrees(atan2(820 - 500, -100 - 500))),
            (1500.0, degrees(atan2(1080 - 500, -80 - 500))),
        ])
        r0 = hand_roll_map[0][1]
        hand_roll_map = [(h, r0 - r + (360 if r0 - r < 0.0 else 0.0))
                         for h, r in hand_roll_map]
        self._radaraltimeter_hand_roll_table = Table1(*zip(*hand_roll_map))
        self._radaraltimeter_scale_max = max(hand_roll_map)[0]
        handnd = make_quad(parent=scenend, size=2.0)
        handnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(handnd,
            texture="images/cockpit/cockpit_mig29_radaraltimeter_hand_tex.png",
            filtr=False)
        self._radaraltimeter_hand_node = handnd

        self._radaraltimeter_update_period = 0.047
        self._radaraltimeter_wait_update = 0.0

        return True


    def _cleanup_radaraltimeter (self):

        pass


    def _update_radaraltimeter (self, dt):

        self._radaraltimeter_wait_update -= dt
        if self._radaraltimeter_wait_update <= 0.0:
            self._radaraltimeter_wait_update += self._radaraltimeter_update_period

            ppos = self.player.ac.pos()
            potralt = self.world.otr_altitude(ppos)
            potralt1 = clamp(potralt, 0.0, self._radaraltimeter_scale_max)
            hroll = self._radaraltimeter_hand_roll_table(potralt1)
            self._radaraltimeter_hand_node.setR(hroll)


    def _init_aoa (self):

        screennd = self._model.find("**/aoa_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_aoa)
        self._instr_cleanup_fs.append(self._cleanup_aoa)

        glassnd = self._model.find("**/aoa_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="aoa")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        scalend = make_quad(parent=scenend, size=2.0)
        scalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(scalend,
            texture="images/cockpit/cockpit_mig29_aoa_scale_tex.png",
            filtr=False)

        aoa_droll = 17.0
        aoa_zero_roll = 180 - 3.0 * aoa_droll
        self._aoa_hand_aoa_min = radians(-10.0)
        self._aoa_hand_aoa_min_roll = aoa_zero_roll - 2.0 * aoa_droll
        self._aoa_hand_aoa_max = radians(40.0)
        self._aoa_hand_aoa_max_roll = aoa_zero_roll + 8.0 * aoa_droll
        aoahandnd = make_quad(parent=scenend, size=2.0)
        aoahandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(aoahandnd,
            texture="images/cockpit/cockpit_mig29_aoa_hand_tex.png",
            filtr=False)
        self._aoa_hand_aoa_node = aoahandnd

        lfac_droll = 11.0
        lfac_zero_roll = -90 + 17 + 10.0 * lfac_droll
        self._aoa_hand_lfac_min = -4.0
        self._aoa_hand_lfac_min_roll = lfac_zero_roll + 4.0 * lfac_droll
        self._aoa_hand_lfac_max = 10.5
        self._aoa_hand_lfac_max_roll = lfac_zero_roll - 10.5 * lfac_droll
        lfachandnd = make_quad(parent=scenend, size=2.0)
        lfachandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(lfachandnd,
            texture="images/cockpit/cockpit_mig29_aoa_hand_tex.png",
            filtr=False)
        self._aoa_hand_lfac_node = lfachandnd

        self._aoa_update_period = 0.037
        self._aoa_wait_update = 0.0

        return True


    def _cleanup_aoa (self):

        pass


    def _update_aoa (self, dt):

        self._aoa_wait_update -= dt
        if self._aoa_wait_update <= 0.0:
            self._aoa_wait_update += self._aoa_update_period

            roll = intl01vr(self.player.ac.dynstate.a,
                            self._aoa_hand_aoa_min, self._aoa_hand_aoa_max,
                            self._aoa_hand_aoa_min_roll, self._aoa_hand_aoa_max_roll)
            self._aoa_hand_aoa_node.setR(roll)

            roll = intl01vr(self.player.ac.dynstate.n,
                            self._aoa_hand_lfac_min, self._aoa_hand_lfac_max,
                            self._aoa_hand_lfac_min_roll, self._aoa_hand_lfac_max_roll)
            self._aoa_hand_lfac_node.setR(roll)


    def _init_machmeter (self):

        screennd = self._model.find("**/machmeter_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_machmeter)
        self._instr_cleanup_fs.append(self._cleanup_machmeter)

        glassnd = self._model.find("**/machmeter_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        self._machmeter_speed_min = 100 / 3.6
        self._machmeter_speed_min_roll = -80
        self._machmeter_speed_lin = 500 / 3.6
        self._machmeter_speed_lin_roll = -80 + 4 * 33
        self._machmeter_speed_max = 1600 / 3.6
        max_geom_exp = 11.0
        geom_droll = 27.5
        geom_mul = 0.90
        max_geom_droll = geom_droll * (1.0 - geom_mul ** max_geom_exp) / (1.0 - geom_mul)
        assert abs(max_geom_droll - 188.7) < 0.1 # to match texture
        self._machmeter_speed_max_roll = -80 + 4 * 33 + max_geom_droll
        self._machmeter_speed_max_geom_exp = max_geom_exp
        self._machmeter_speed_geom_droll = geom_droll
        self._machmeter_speed_geom_mul = geom_mul

        self._machmeter_mach_min = 0.0
        self._machmeter_mach_min_roll = 0
        self._machmeter_mach_max = 2.8
        self._machmeter_mach_max_roll = 280

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="machmeter")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        scalend = make_quad(parent=scenend, size=2.0)
        scalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(scalend,
            texture="images/cockpit/cockpit_mig29_machmeter_scale_speed_tex.png",
            filtr=False)

        machscalend = make_quad(parent=scenend, size=2.0)
        machscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(machscalend,
            texture="images/cockpit/cockpit_mig29_machmeter_scale_mach_tex.png",
            filtr=False)
        self._machmeter_mach_scale_node = machscalend

        machcovernd = make_quad(parent=scenend, size=2.0)
        machcovernd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(machcovernd,
            texture="images/cockpit/cockpit_mig29_machmeter_mach_cover_tex.png",
            filtr=False)
        self._machmeter_mach_cover_node = machcovernd

        handnd = make_quad(parent=scenend, size=2.0)
        handnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(handnd,
            texture="images/cockpit/cockpit_mig29_machmeter_hand_tex.png",
            filtr=False)
        self._machmeter_hand_node = handnd

        self._machmeter_update_period = 0.153
        self._machmeter_wait_update = 0.0

        return True


    def _cleanup_machmeter (self):

        pass


    def _update_machmeter (self, dt):

        self._machmeter_wait_update -= dt
        if self._machmeter_wait_update <= 0.0:
            self._machmeter_wait_update += self._machmeter_update_period

            pspd = self.player.ac.dynstate.vias
            if pspd < self._machmeter_speed_min:
                roll = self._machmeter_speed_min_roll
            elif pspd < self._machmeter_speed_lin:
                roll = intl01vr(pspd,
                                self._machmeter_speed_min,
                                self._machmeter_speed_lin,
                                self._machmeter_speed_min_roll,
                                self._machmeter_speed_lin_roll)
            elif pspd < self._machmeter_speed_max:
                geom_exp = intl01vr(pspd,
                                    self._machmeter_speed_lin,
                                    self._machmeter_speed_max,
                                    0.0,
                                    self._machmeter_speed_max_geom_exp)
                geom_mul = self._machmeter_speed_geom_mul
                droll1 = self._machmeter_speed_geom_droll
                droll = droll1 * (1.0 - geom_mul ** geom_exp) / (1.0 - geom_mul)
                roll = self._machmeter_speed_lin_roll + droll
            else:
                roll = self._machmeter_speed_max_roll
            self._machmeter_hand_node.setR(roll)
            hand_roll = roll

            pmach = self.player.ac.dynstate.ma
            roll = intl01vr(pmach,
                            self._machmeter_mach_min,
                            self._machmeter_mach_max,
                            self._machmeter_mach_min_roll,
                            self._machmeter_mach_max_roll)
            droll = roll - self._machmeter_mach_min_roll
            self._machmeter_mach_cover_node.setR(hand_roll)
            self._machmeter_mach_scale_node.setR(hand_roll - droll)


    def _init_adi (self):

        screennd = self._model.find("**/adi_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_adi)
        self._instr_cleanup_fs.append(self._cleanup_adi)

        glassnd = self._model.find("**/adi_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="adi")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        pbarbgnd = make_quad(parent=scenend, size=2.0)
        pbarbgnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(pbarbgnd,
            texture="images/cockpit/cockpit_mig29_adi_pitch_bar_bg_tex.png",
            filtr=False)
        bar_width = 360.0 / 1000.0
        bar_tex_partw = 80.0 / 720.0
        bar_tex_parth = bar_tex_partw / bar_width
        bar_geom = make_raw_quad(
            szext=(-bar_width, -1.0, bar_width, 1.0),
            uvext=(0.5 - 0.5 * bar_tex_partw, 0.5 - 0.5 * bar_tex_parth,
                   0.5 + 0.5 * bar_tex_partw, 0.5 + 0.5 * bar_tex_parth))
        self._adi_bar_node = scenend.attachNewNode(bar_geom)
        self._adi_bar_node.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(self._adi_bar_node,
            texture="images/cockpit/cockpit_mig29_adi_pitch_bar_tex.png",
            clamp=False, filtr=False)

        bscalend = make_quad(parent=scenend, size=2.0)
        bscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(bscalend,
            texture="images/cockpit/cockpit_mig29_adi_bank_scale_tex.png",
            filtr=False)
        self._adi_bar_node = scenend.attachNewNode(bar_geom)

        bscalend = make_quad(parent=scenend, size=2.0)
        bscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(bscalend,
            texture="images/cockpit/cockpit_mig29_adi_bank_scale_tex.png",
            filtr=False)

        reqdummynd = make_quad(parent=scenend, size=2.0)
        reqdummynd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(reqdummynd,
            texture="images/cockpit/cockpit_mig29_adi_req_dummy_tex.png",
            filtr=False)

        bpointnd = make_quad(parent=scenend, size=2.0)
        bpointnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(bpointnd,
            texture="images/cockpit/cockpit_mig29_adi_bank_pointer_tex.png",
            filtr=False)
        self._adi_bank_pointer = bpointnd

        self._adi_update_period = 0.049
        self._adi_wait_update = 0.0

        return True


    def _cleanup_adi (self):

        pass


    def _update_adi (self, dt):

        self._adi_wait_update -= dt
        if self._adi_wait_update <= 0.0:
            self._adi_wait_update += self._adi_update_period

            ppch = self.player.ac.dynstate.pch
            offv = ppch / pi
            self._adi_bar_node.setTexOffset(texstage_color, 0.0, offv)

            pbnk = self.player.ac.dynstate.bnk
            self._adi_bank_pointer.setR(degrees(pbnk))


    def _init_vvi (self):

        screennd = self._model.find("**/vvi_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_vvi)
        self._instr_cleanup_fs.append(self._cleanup_vvi)

        glassnd = self._model.find("**/vvi_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="vvi")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        reqdummynd = make_quad(parent=scenend, size=2.0)
        reqdummynd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(reqdummynd,
            texture="images/cockpit/cockpit_mig29_vvi_yaw_dummy_tex.png",
            filtr=False)

        tscalend = make_quad(parent=scenend, size=2.0)
        tscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(tscalend,
            texture="images/cockpit/cockpit_mig29_vvi_scale_turn_tex.png",
            filtr=False)
        thandnd = make_quad(parent=scenend, size=2.0)
        thandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(thandnd,
            texture="images/cockpit/cockpit_mig29_vvi_hand_turn_tex.png",
            filtr=False)
        self._vvi_turn_hand_node = scenend.attachNewNode("turn-hand-platform")
        thand_xc = 0.0
        thand_zc = -1.0 + (190.0 / 1000.0) * 2
        self._vvi_turn_hand_node.setPos(thand_xc, 0.0, thand_zc)
        thandnd.wrtReparentTo(self._vvi_turn_hand_node)
        self._vvi_turn_min = -radians(3.0)
        self._vvi_turn_min_roll = +(3 * 9.0)
        self._vvi_turn_max = radians(3.0)
        self._vvi_turn_max_roll = -(3 * 9.0)

        cscalend = make_quad(parent=scenend, size=2.0)
        cscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(cscalend,
            texture="images/cockpit/cockpit_mig29_vvi_scale_climb_tex.png",
            filtr=False)
        chandnd = make_quad(parent=scenend, size=2.0)
        chandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(chandnd,
            texture="images/cockpit/cockpit_mig29_vvi_hand_climb_tex.png",
            filtr=False)
        self._vvi_climb_hand_node = chandnd
        self._vvi_climb_min = -200.0
        self._vvi_climb_min_roll = -(4 * 17.0 + 12.0 + 3 * 20.0)
        self._vvi_climb_neg = -20.0
        self._vvi_climb_neg_roll = -(4 * 17.0)
        self._vvi_climb_pos = 20.0
        self._vvi_climb_pos_roll = +(4 * 17.0)
        self._vvi_climb_max = 200.0
        self._vvi_climb_max_roll = +(4 * 17.0 + 12.0 + 3 * 20.0)

        self._vvi_update_period = 0.039
        self._vvi_wait_update = 0.0

        return True


    def _cleanup_vvi (self):

        pass


    def _update_vvi (self, dt):

        self._vvi_wait_update -= dt
        if self._vvi_wait_update <= 0.0:
            self._vvi_wait_update += self._vvi_update_period

            crate = self.player.ac.dynstate.cr
            if crate < self._vvi_climb_min:
                croll = self._vvi_climb_min_roll
            elif crate < self._vvi_climb_neg:
                croll = intl01vr(crate, self._vvi_climb_min, self._vvi_climb_neg,
                                 self._vvi_climb_min_roll, self._vvi_climb_neg_roll)
            elif crate < self._vvi_climb_pos:
                croll = intl01vr(crate, self._vvi_climb_neg, self._vvi_climb_pos,
                                 self._vvi_climb_neg_roll, self._vvi_climb_pos_roll)
            elif crate < self._vvi_climb_max:
                croll = intl01vr(crate, self._vvi_climb_pos, self._vvi_climb_max,
                                 self._vvi_climb_pos_roll, self._vvi_climb_max_roll)
            else:
                croll = self._vvi_climb_max_roll
            self._vvi_climb_hand_node.setR(croll)

            trate = self.player.ac.dynstate.tr
            troll = intl01vr(trate, self._vvi_turn_min, self._vvi_turn_max,
                             self._vvi_turn_min_roll, self._vvi_turn_max_roll)
            self._vvi_turn_hand_node.setR(troll)


    def _init_bpa (self):

        screennd = self._model.find("**/bpa_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_bpa)
        self._instr_cleanup_fs.append(self._cleanup_bpa)

        glassnd = self._model.find("**/bpa_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=256,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="bpa")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        oscalend = make_quad(parent=scenend, size=2.0)
        oscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(oscalend,
            texture="images/cockpit/cockpit_mig29_bpa_scale_outer_tex.png",
            filtr=False)
        ohandnd = make_quad(parent=scenend, size=2.0)
        ohandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(ohandnd,
            texture="images/cockpit/cockpit_mig29_bpa_hand_outer_tex.png",
            filtr=False)
        self._bpa_hand_outer_node = ohandnd
        self._bpa_alt_max = 30000.0

        iscalend = make_quad(parent=scenend, size=2.0)
        iscalend.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(iscalend,
            texture="images/cockpit/cockpit_mig29_bpa_scale_inner_tex.png",
            filtr=False)
        ihandnd = make_quad(parent=scenend, size=2.0)
        ihandnd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(ihandnd,
            texture="images/cockpit/cockpit_mig29_bpa_hand_inner_tex.png",
            filtr=False)
        self._bpa_hand_inner_node = ihandnd

        self._bpa_update_period = 0.059
        self._bpa_wait_update = 0.0

        return True


    def _cleanup_bpa (self):

        pass


    def _update_bpa (self, dt):

        self._bpa_wait_update -= dt
        if self._bpa_wait_update <= 0.0:
            self._bpa_wait_update += self._bpa_update_period

            alt = self.player.ac.dynstate.h
            alt1 = clamp(alt, 0.0, self._bpa_alt_max)
            oroll = (alt1 / 1000.0 - int(alt1 / 1000.0)) * 360.0
            self._bpa_hand_outer_node.setR(oroll)
            iroll = (alt1 / self._bpa_alt_max) * 360.0
            self._bpa_hand_inner_node.setR(iroll)


    _mfd_tvdisp_buffer = None
    _mfd_tvdisp_camera_mask = BitMask32.bit(10)

    def _init_mfd (self, arenaedge):

        screennd = self._model.find("**/tvpanel_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_mfd)
        self._instr_cleanup_fs.append(self._cleanup_mfd)

        glassnd = self._model.find("**/tvpanel_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)
        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=512,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="mfd")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_mfd_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_bright)

        #self._mfd_font = "fonts/DejaVuSans-Bold.ttf"
        self._mfd_font = "fonts/red-october-regular.otf"
        #self._mfd_font = "fonts/DidactGothic.ttf"
        #self._mfd_font = "fonts/VDS_New.ttf"
        self._mfd_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)

        # See comment-hud-size.
        un = 2.0 / 32.0

        self._mfd_mode_names = []
        self._mfd_root_nodes = []
        self._mfd_update_periods = []
        self._mfd_update_fast_periods = []
        self._mfd_mode_infs = []
        self._mfd_mode_outfs = []
        self._mfd_mode_can_cycle_over = []

        # Overview map.
        self._mfd_has_overmap = False
        if True:
            self._mfd_mode_names.append("overmap")
            self._mfd_overmap_node = scenend.attachNewNode("mfd-overmap")
            self._mfd_root_nodes.append(self._mfd_overmap_node)
            self._mfd_update_periods.append(0.93)
            self._mfd_update_fast_periods.append(1e6)
            self._mfd_mode_infs.append(None)
            self._mfd_mode_outfs.append(None)
            self._mfd_mode_can_cycle_over.append(True)

            refterrain = self.world.terrains[0]
            minx, miny, maxx, maxy, visradius = refterrain.extents()
            minxa, minya = minx + visradius, miny + visradius
            maxxa, maxya = maxx - visradius, maxy - visradius
            szxa = maxxa - minxa
            szya = maxya - minya
            mapsz = 2.0
            sfac = mapsz / max(szxa, szya)
            self._mfd_overmap_scale = sfac
            self._mfd_overmap_center = Point3(0.5 * (minxa + maxxa),
                                              0.5 * (minya + maxya),
                                              0.0)

            #if refterrain.geomap_path:
                #mapgm = make_raw_quad(
                    #szext=(-0.5 * mapsz, -0.5 * mapsz, 0.5 * mapsz, 0.5 * mapsz),
                    #uvext=refterrain.geomap_uvext_arena)
                #mapnd = self._mfd_overmap_node.attachNewNode(mapgm)
                #set_texture(mapnd, refterrain.geomap_path)

            sfsz = arenaedge * sfac
            sfw = (szxa - 2 * arenaedge) * sfac
            sfh = (szya - 2 * arenaedge) * sfac
            aend = make_frame(
                imgbase="images/cockpit/cockpit_mig29_radar_arena_edge_tex",
                imgsize=sfsz, width=sfw, height=sfh,
                parent=self._mfd_overmap_node)
            aend.setSa(0.25)

            #self._mfd_overmap_ownac_node = make_image(
                #texture="images/cockpit/cockpit_mig29_map_ownac_tex.png",
                #pos=Point3(), size=0.15, filtr=False,
                #parent=self._mfd_overmap_node)
            self._mfd_overmap_glineh_node = make_image(
                texture="images/cockpit/cockpit_mig29_map_glineh_tex.png",
                pos=Point3(), size=2.0, filtr=False,
                parent=self._mfd_overmap_node)
            self._mfd_overmap_glinev_node = make_image(
                texture="images/cockpit/cockpit_mig29_map_glinev_tex.png",
                pos=Point3(), size=2.0, filtr=False,
                parent=self._mfd_overmap_node)

            self._mfd_overmap_waypoint_node = make_image(
                texture="images/cockpit/cockpit_mig29_map_waypoint_tex.png",
                pos=Point3(), size=0.15, filtr=False)
            self._mfd_overmap_waypoints = {}
            self._mfd_overmap_waypoint_text_offset_x = 0.05
            self._mfd_overmap_waypoint_text_offset_z = 0.03

            self._mfd_has_overmap = True

        # TV display.
        self._mfd_has_tvdisp = False
        if self.player.ac.tvrange:
            self._mfd_mode_names.append("tvdisp")
            self._mfd_tvdisp_node = scenend.attachNewNode("mfd-tvdisp")
            self._mfd_root_nodes.append(self._mfd_tvdisp_node)
            self._mfd_update_periods.append(0.171)
            self._mfd_update_fast_periods.append(0.0)
            self._mfd_mode_can_cycle_over.append(False)

            tvdisp_font_color = rgba(0, 255, 0, 1.0)
            tvdisp_font_size = 32

            # TV image.
            if self._mfd_tvdisp_buffer is None:
                tsz = 256
                self._mfd_tvdisp_buffer = base.window.make_texture_buffer(
                    "mfd-tvdisp-view", tsz, tsz)
            #self._mfd_tvdisp_buffer.setSort(0)
            self._mfd_tvdisp_lens = PerspectiveLens()
            self._mfd_tvdisp_camera = base.make_camera(
                window=self._mfd_tvdisp_buffer, lens=self._mfd_tvdisp_lens,
                clear_depth=True)
            self._mfd_tvdisp_camera.node().setScene(self.world.root)
            self._mfd_tvdisp_camera.node().setCameraMask(self._mfd_tvdisp_camera_mask)
            if self._ac_model_type == 1:
                self.player.ac.node.hide(self._mfd_tvdisp_camera_mask)
            texture = self._mfd_tvdisp_buffer.getTexture()
            #texture.setMinfilter(Texture.FTLinearMipmapLinear)
            #texture.setMagfilter(Texture.FTLinearMipmapLinear)
            self._mfd_tvdisp_view_node = make_image(
                texture=texture, size=2.0, filtr=True,
                parent=self._mfd_tvdisp_node)
            self._mfd_tvdisp_min_fov = 2
            self._mfd_tvdisp_max_fov = 15
            self._mfd_tvdisp_idle_fov = 5
            self._mfd_tvdisp_wide_fov = 20
            self._mfd_tvdisp_idle_dhpr = Vec3(0, -30, 0)
            minua, maxua, ta = self.player.ac.tvangle
            self._mfd_tvdisp_gimbal_min_dh = -degrees(ta)
            self._mfd_tvdisp_gimbal_max_dh = +degrees(ta)
            self._mfd_tvdisp_gimbal_min_dp = degrees(minua)
            self._mfd_tvdisp_gimbal_max_dp = degrees(maxua)

            self._mfd_tvdisp_speed_pos = 5000.0
            self._mfd_tvdisp_speed_hpr = 30.0
            self._mfd_tvdisp_speed_fov = self._mfd_tvdisp_wide_fov / 1.0

            # Referent FOV for zoom factor calculation.
            # Not really defined, since game FOV arbitrary, so pick any value.
            self._mfd_tvdisp_ref_fov = 40

            shader = Cockpit.make_shader_tvdisp()
            self._mfd_tvdisp_view_node.setShader(shader)
            rgbf = Vec4(0.30, 0.59, 0.11, 0.0)
            #rgbf = Vec4(0.33, 0.33, 0.33, 0.0)
            #chnf = rgba(255, 255, 255, 0.0)
            #chnf = rgba(255, 127, 64, 0.0)
            chnf = rgba(206, 255, 175, 0.0)
            ctrmat = Mat4(
                chnf[0] * rgbf[0], chnf[1] * rgbf[0], chnf[2] * rgbf[0], 0.0,
                chnf[0] * rgbf[1], chnf[1] * rgbf[1], chnf[2] * rgbf[1], 0.0,
                chnf[0] * rgbf[2], chnf[1] * rgbf[2], chnf[2] * rgbf[2], 0.0,
                              0.0,               0.0,               0.0, 1.0,
            )
            self._mfd_tvdisp_view_node.setShaderInput("ctrmat", ctrmat)
            #self._mfd_tvdisp_time = 0.0
            #self._mfd_tvdisp_view_node.setShaderInput("time", self._mfd_tvdisp_time)
            self._mfd_tvdisp_view_node.setShaderInput("brightfac", 1.0)

            self._mfd_tvdisp_overlay_node = self._mfd_tvdisp_node.attachNewNode("tvdisp-overlay")
            #self._mfd_tvdisp_overlay_node.setScale(1.0)

            # Offset angle scales.
            self._mfd_tvdisp_angle_scale_node = make_image(
                "images/cockpit/cockpit_mig29_mfd_tvdisp_angle_scale_tex.png",
                pos=Point3(0.0, 0.0, 0.0), size=(32 * un),
                filtr=False, parent=self._mfd_tvdisp_overlay_node)
            self._mfd_tvdisp_angle_pointer_horiz_node = make_image(
                "images/cockpit/cockpit_mig29_mfd_tvdisp_angle_pointer_horiz_tex.png",
                pos=Point3(0.0, 0.0, 14 * un), size=(4 * un),
                filtr=False, parent=self._mfd_tvdisp_overlay_node)
            self._mfd_tvdisp_angle_pointer_vert_node = make_image(
                "images/cockpit/cockpit_mig29_mfd_tvdisp_angle_pointer_vert_tex.png",
                pos=Point3(-14 * un, 0.0, 0.0), size=(4 * un),
                filtr=False, parent=self._mfd_tvdisp_overlay_node)
            self._mfd_tvdisp_angle_horiz_min = -50
            self._mfd_tvdisp_angle_horiz_min_x = 10 * un
            self._mfd_tvdisp_angle_horiz_max = 50
            self._mfd_tvdisp_angle_horiz_max_x = -10 * un
            self._mfd_tvdisp_angle_vert_min = -70
            self._mfd_tvdisp_angle_vert_min_z = -8 * un
            self._mfd_tvdisp_angle_vert_max = 10
            self._mfd_tvdisp_angle_vert_max_z = 8 * un

            # Target reticle.
            self._mfd_tvdisp_reticle_idle_node = make_image(
                "images/cockpit/cockpit_mig29_mfd_tvdisp_reticle_idle_tex.png",
                pos=Point3(0.0, 0.0, 0.0), size=(8 * un),
                filtr=False, parent=self._mfd_tvdisp_overlay_node)
            self._mfd_tvdisp_reticle_locked_node = make_image(
                "images/cockpit/cockpit_mig29_mfd_tvdisp_reticle_locked_tex.png",
                pos=Point3(0.0, 0.0, 0.0), size=(8 * un),
                filtr=False, parent=self._mfd_tvdisp_overlay_node)
            self._mfd_tvdisp_target_dist_text = make_text(
                width=0.5, pos=Point3(0.0, 0.0, -4.5 * un),
                font=self._mfd_font, size=tvdisp_font_size,
                color=tvdisp_font_color, align="c", anchor="tc",
                parent=self._mfd_tvdisp_overlay_node)

            # Zoom.
            self._mfd_tvdisp_zoom_text = make_text(
                width=0.5, pos=Point3(11.0 * un, 0.0, -11.0 * un),
                font=self._mfd_font, size=tvdisp_font_size,
                color=tvdisp_font_color, align="c", anchor="mc",
                parent=self._mfd_tvdisp_overlay_node)

            # Orientation of the head when the TV display is active.
            #self._mfd_tvdisp_view_hpr = Vec3(8.0, -16.0, 0.0)
            self._mfd_tvdisp_view_ref_model_pos = Point3(-0.47, 5.31, 0.80) #-0.33, 5.31, 0.80

            self._mfd_tvdisp_update_view_task = None
            def mfd_tvdisp_inf ():
                self._mfd_tvdisp_camera.node().setActive(True)
                self._mfd_tvdisp_camera.setPos(self.player.ac.pos())
                self._mfd_tvdisp_camera.setHpr(self.player.ac.hpr() + self._mfd_tvdisp_idle_dhpr)
                self._mfd_tvdisp_lens.setMinFov(self._mfd_tvdisp_idle_fov)
                selwp = None
                if self.player.input_select_weapon >= 0:
                    selwp = self.player.weapons[self.player.input_select_weapon]
                if selwp and isinstance(selwp.handle, Launcher) and selwp.handle.mtype.seeker:
                    #self._view_base_hpr = self._mfd_tvdisp_view_hpr
                    self._mvd_tvdisp_prev_vfov = 0
                    def update_view (task):
                        view_vfov = self._camlens.getMinFov()
                        if abs(self._mvd_tvdisp_prev_vfov - view_vfov) > 0.5:
                            self._mvd_tvdisp_prev_vfov = view_vfov
                            view_hfov = vert_to_horiz_fov(view_vfov, base.aspect_ratio)
                            fov_hdg, fov_pch = view_hfov * 0.5, view_vfov * 0.5
                            ref_pos = self.node.getRelativePoint(
                                self._model, self._mfd_tvdisp_view_ref_model_pos)
                            ref_hdg = degrees(atan2(-ref_pos[0], ref_pos[1]))
                            ref_pch = degrees(atan2(ref_pos[2], ref_pos[1]))
                            if abs(ref_hdg) > fov_hdg:
                                off_hdg = ref_hdg - fov_hdg * sign(ref_hdg)
                            else:
                                off_hdg = 0.0
                            if abs(ref_pch) > fov_pch:
                                off_pch = ref_pch - fov_pch * sign(ref_pch)
                            else:
                                off_pch = 0.0
                            self._view_base_hpr = Vec3(off_hdg, off_pch, 0.0)
                        return task.cont
                    task = base.taskMgr.add(update_view, "mfd-tvdisp-update-view")
                    self._mfd_tvdisp_update_view_task = task
                else:
                    self._view_base_hpr = self._view_idle_hpr
            def mfd_tvdisp_outf ():
                self._mfd_tvdisp_camera.node().setActive(False)
                self._view_base_hpr = self._view_idle_hpr
                if self._mfd_tvdisp_update_view_task is not None:
                    self._mfd_tvdisp_update_view_task.remove()
                    self._mfd_tvdisp_update_view_task = None
            self._mfd_mode_infs.append(mfd_tvdisp_inf)
            self._mfd_mode_outfs.append(mfd_tvdisp_outf)

            self._mfd_tvdisp_seekers = set(
                ("tv", "intv", "ir", "salh", "radio", "wire"))
            self._mfd_tvdisp_against = set(
                ("vehicle", "ship", "building"))

            self._mfd_has_tvdisp = True

        # Target identifier.
        self._mfd_has_targid = False
        if True:
            self._mfd_mode_names.append("targid")
            self._mfd_targid_node = scenend.attachNewNode("mfd-targid")
            self._mfd_root_nodes.append(self._mfd_targid_node)
            self._mfd_update_periods.append(0.975)
            self._mfd_update_fast_periods.append(1e6)
            self._mfd_mode_can_cycle_over.append(True)
            self._mfd_mode_infs.append(None)
            self._mfd_mode_outfs.append(None)

            #targid_font = self._mfd_font
            targid_font = "fonts/DejaVuSans-Bold.ttf"
            #targid_font = "fonts/DidactGothic.ttf"
            targid_font_color = rgba(255, 0, 0, 1.0)

            self._mfd_targid_families = set(["plane"])

            make_image(
                texture="images/cockpit/cockpit_mig29_radar_grid_4x4.png",
                size=2.0, pos=Point3(),
                filtr=False, parent=self._mfd_targid_node)

            self._mfd_targid_notarg_node = self._mfd_targid_node.attachNewNode("none")
            self._mfd_targid_notarg_node.show()

            notarg_font_size = 32
            make_text(
                text=select_des(p_("target information display: "
                                   "currently there is no target",
                                   "NO TARGET"),
                                {"ru": u"НЕТ ЦЕЛИ"}, self._lang),
                width=2.0, pos=Point2(0.0, 0.0),
                font=targid_font, size=notarg_font_size,
                color=targid_font_color, align="c", anchor="mc",
                parent=self._mfd_targid_notarg_node)

            self._mfd_targid_data_node = self._mfd_targid_node.attachNewNode("data")
            self._mfd_targid_data_node.hide()

            self._mfd_targid_rd_fmt = lambda v: _rn(u"%+.0f%%" % (v * 100))

            vec_size = 0.9
            self._mfd_targid_blank_vec_path = "images/ui/black.png"
            self._mfd_targid_vec_node = make_image(
                texture=self._mfd_targid_blank_vec_path, size=vec_size,
                pos=Point2(-0.5, 0.5),
                filtr=False, parent=self._mfd_targid_data_node)
            self._mfd_targit_current_species = None

            def make_datum_text (wrap=False):
                return make_text(
                    width=col_width, pos=Point2(left_x, top_z),
                    font=targid_font, size=font_size,
                    color=targid_font_color, align="l", anchor="tl",
                    wrap=wrap,
                    parent=self._mfd_targid_data_node)

            def make_datum_rd_text (wrap=False):
                return make_text(
                    width=col_width, pos=Point2(rd_left_x, top_z),
                    font=targid_font, size=font_size,
                    color=targid_font_color, align="l", anchor="tl",
                    wrap=wrap,
                    parent=self._mfd_targid_data_node)

            font_size = 28
            col_width = 0.95
            top_z = 0.9
            left_x = 0.0
            rd_left_x = left_x + col_width * 0.1
            row_height = font_scale_for_ptsize(font_size) * 1.4

            self._mfd_targid_wingload_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "weight to wing area",
                                        u"W/S: %s kg/m²"),
                                     {"ru": u"G/S: %s кг/м²"},
                                     self._lang) % _rn("%.0f" % v))
            self._mfd_targid_wingload_text = make_datum_text()
            top_z -= row_height
            self._mfd_targid_wingload_rd_text = make_datum_rd_text()
            top_z -= row_height * 1.5

            self._mfd_targid_thrtowt_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "thrust to weight",
                                        u"T/W: %s"),
                                     {"ru": u"P/G: %s"},
                                     self._lang) % _rn("%.2f" % v))
            self._mfd_targid_thrtowt_text = make_datum_text()
            top_z -= row_height
            self._mfd_targid_thrtowt_rd_text = make_datum_rd_text()
            top_z -= row_height * 1.5

            #self._mfd_targid_maxlfac_fmt = (
                #lambda v: u"ny: %s" % _rn("%.1f" % v))
            #self._mfd_targid_maxlfac_text = make_datum_text()
            #top_z -= row_height
            #self._mfd_targid_maxlfac_rd_text = make_datum_rd_text()
            #top_z -= row_height * 1.5

            self._mfd_targid_spdtri_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "speed for best turn",
                                        u"Vturn: %s km/h"),
                                     {"ru": u"Vпов: %s км/ч"},
                                     self._lang) % _rn("%.0f" % (v * 3.6)))
            self._mfd_targid_spdtri_text = make_datum_text()
            top_z -= row_height
            self._mfd_targid_spdtri_rd_text = make_datum_rd_text()
            top_z -= row_height * 1.5

            self._mfd_targid_spdcl_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "speed for best climb",
                                        u"Vclimb: %s km/h"),
                                     {"ru": u"Vнаб: %s км/ч"},
                                     self._lang) % _rn("%.0f" % (v * 3.6)))
            self._mfd_targid_spdcl_text = make_datum_text()
            top_z -= row_height
            self._mfd_targid_spdcl_rd_text = make_datum_rd_text()
            top_z -= row_height * 1.5

            font_size = 22
            col_width = 0.90
            top_z = -row_height * 0.5
            left_x = -0.90
            rd_left_x = left_x + col_width * 0.1
            row_height = font_scale_for_ptsize(font_size) * 1.4

            title_font_size = 32
            title_row_height = font_scale_for_ptsize(title_font_size) * 1.4
            self._mfd_targid_title_fmt = lambda v: "%s" % v
            self._mfd_targid_title_text = make_text(
                width=col_width, pos=Point2(left_x, top_z),
                font=targid_font, size=title_font_size,
                color=targid_font_color, align="c", anchor="tl",
                parent=self._mfd_targid_data_node)
            top_z -= title_row_height * 1.2

            self._mfd_targid_klass_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "class",
                                        u"CL: %s"),
                                     {"ru": u"КЛ: %s"},
                                     self._lang) % v)
            self._mfd_targid_klass_text = make_datum_text()
            top_z -= row_height * 1.2

            self._mfd_targid_origin_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "country of origin",
                                        u"OR: %s"),
                                     {"ru": u"ПР: %s"},
                                     self._lang) % v)
            self._mfd_targid_origin_text = make_datum_text()
            top_z -= row_height * 1.2

            self._mfd_targid_span_fmt = (
                lambda v: (
                    (select_des(p_("target information display: "
                                   "span",
                                   u"b: %(1)s/%(2)s m"),
                                {"ru": u"l: %(1)s/%(2)s м"},
                                self._lang) % (_rn("%.1f" % v[0]),
                                               _rn("%.1f" % v[1])))
                    if isinstance(v, tuple) else
                    (select_des(p_("target information display: "
                                   "span",
                                   u"b: %s m"),
                                {"ru": u"l: %s м"},
                                self._lang) % _rn("%.1f" % v))))
            self._mfd_targid_span_text = make_datum_text()
            top_z -= row_height * 1.2

            self._mfd_targid_mass_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "weight",
                                        u"W: %s t"),
                                     {"ru": u"G: %s т"},
                                     self._lang) % _rn("%.1f" % (v * 1e-3)))
            self._mfd_targid_mass_text = make_datum_text()
            top_z -= row_height * 1.2

            self._mfd_targid_maxlfac_fmt = (
                lambda v: select_des(p_("target information display: "
                                        "limit load factor",
                                        u"nmax: %s"),
                                     {"ru": u"ny: %s"},
                                     self._lang) % _rn("%.1f" % v))
            self._mfd_targid_maxlfac_text = make_datum_text()
            top_z -= row_height * 1.2

            self._mfd_has_targid = True

        # Aircraft state information.
        if False:
            self._mfd_mode_names.append("acinfo")
            self._mfd_acinfo_node = scenend.attachNewNode("mfd-acinfo")
            self._mfd_root_nodes.append(self._mfd_acinfo_node)
            self._mfd_update_periods.append(1.01)
            self._mfd_update_fast_periods.append(1e6)
            self._mfd_mode_infs.append(None)
            self._mfd_mode_outfs.append(None)
            self._mfd_mode_can_cycle_over.append(True)

        self._mfd_current_mode_index = 0
        self._mfd_stored_mode_name = None
        self._mfd_wait_update = 0.0
        self._mfd_wait_fast_update = 0.0

        self._mfd_prev_selwp = -1 # not None, to trigger MFD mode check

        # Initialize modes.
        for mind, mname in enumerate(self._mfd_mode_names):
            if mind == self._mfd_current_mode_index:
                self._mfd_root_nodes[mind].show()
                minf = self._mfd_mode_infs[mind]
                if minf:
                    minf()
            else:
                self._mfd_root_nodes[mind].hide()
                moutf = self._mfd_mode_outfs[mind]
                if moutf:
                    moutf()

        return True


    @staticmethod
    def make_shader_tvdisp ():

        shdkey = ("tvdisp")
        shader = Cockpit._shader_cache.get(shdkey)
        if shader is not None:
            return shader

        vshstr = GLSL_PROLOGUE

        vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    l_texcoord0 = p3d_MultiTexCoord0;
}
"""

        fshstr = GLSL_PROLOGUE

        ret = make_frag_outputs(wcolor=True)
        odeclstr, ocolorn = ret

        fshstr += """
const float pi = 3.14165;

uniform mat4 ctrmat;
//uniform vec1 time;
uniform float brightfac;
uniform sampler2D p3d_Texture0;
in vec2 l_texcoord0;
"""
        fshstr += odeclstr
        fshstr += """
void main ()
{
    // Get base color.
    vec4 color = texture(p3d_Texture0, l_texcoord0);

    // Convert to monochrome.
    color = ctrmat * color;

    // Add brightness.
    color = clamp(color * brightfac, 0.0, 1.0);

    // Add interlace.
    float il = (1.0 - pow(abs(sin(l_texcoord0[1] * 60 * pi)), 0.5)) * 0.1;
    color = color - il;

    // Fix alpha.
    color.a = 1.0;

    %(ocolorn)s = color;
}
""" % locals()

        if 0:
            printsh((vshstr, fshstr), showas)
        shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
        Cockpit._shader_cache[shdkey] = shader
        return shader


    def _cleanup_mfd (self):

        if self._mfd_has_tvdisp:
            if self._mfd_tvdisp_update_view_task is not None:
                self._mfd_tvdisp_update_view_task.remove()


    def _update_mfd (self, dt):

        selwp = None
        if self.player.input_select_weapon >= 0:
            selwp = self.player.weapons[self.player.input_select_weapon]
        if self._mfd_prev_selwp is not selwp:
            self._mfd_prev_selwp = selwp
            if self._mfd_has_tvdisp:
                if ((selwp and isinstance(selwp.handle, Launcher) and
                     selwp.handle.mtype.seeker in self._mfd_tvdisp_seekers and
                     self._mfd_tvdisp_against.intersection(selwp.handle.mtype.against)) or
                    (selwp and isinstance(selwp.handle, PodLauncher) and
                     self._mfd_tvdisp_against.intersection(selwp.against()))):
                    name = self._mfd_mode_names[self._mfd_current_mode_index]
                    if name != "tvdisp":
                        self._mfd_stored_mode_name = name
                    self.cycle_mfd_mode(skip="tvdisp", force=True)
                elif self._mfd_stored_mode_name:
                    self.cycle_mfd_mode(skip=self._mfd_stored_mode_name)
                    self._mfd_stored_mode_name = None
                brightfac = 1.0 + (1.0 - self.world.sky.sun_strength) * 2.0
                self._mfd_tvdisp_view_node.setShaderInput("brightfac", brightfac)

        mmind = self._mfd_current_mode_index
        mfd_mode = self._mfd_mode_names[mmind]

        self._mfd_wait_update -= dt
        if self._mfd_wait_update <= 0.0:
            mfd_update_period = self._mfd_update_periods[mmind]
            self._mfd_wait_update += mfd_update_period

            if 0: pass

            elif mfd_mode == "overmap":
                sfac = self._mfd_overmap_scale
                cpos = self._mfd_overmap_center

                ppos = self.player.ac.pos()
                mppos = (ppos - cpos) * sfac
                #phdg = self.player.ac.hpr()[0]
                #oacnd = self._mfd_overmap_ownac_node
                #oacnd.setX(mppos[0])
                #oacnd.setZ(mppos[1])
                #oacnd.setR(-phdg)
                self._mfd_overmap_glineh_node.setZ(mppos[1])
                self._mfd_overmap_glinev_node.setX(mppos[0])

            elif mfd_mode == "tvdisp":
                drw = self.world.camera.node().getDisplayRegion(0)
                drv = self._mfd_tvdisp_camera.node().getDisplayRegion(0)
                drv.setClearColor(drw.getClearColor())

                chpr = self._mfd_tvdisp_camera.getHpr(self.player.ac.node)
                apx = intl01vr(chpr[0],
                               self._mfd_tvdisp_angle_horiz_min,
                               self._mfd_tvdisp_angle_horiz_max,
                               self._mfd_tvdisp_angle_horiz_min_x,
                               self._mfd_tvdisp_angle_horiz_max_x)
                self._mfd_tvdisp_angle_pointer_horiz_node.setX(apx)
                apz = intl01vr(chpr[1],
                               self._mfd_tvdisp_angle_vert_min,
                               self._mfd_tvdisp_angle_vert_max,
                               self._mfd_tvdisp_angle_vert_min_z,
                               self._mfd_tvdisp_angle_vert_max_z)
                self._mfd_tvdisp_angle_pointer_vert_node.setZ(apz)

                cfov = self._mfd_tvdisp_lens.getMinFov()
                zoom_fac = self._mfd_tvdisp_ref_fov / cfov
                update_text(self._mfd_tvdisp_zoom_text,
                            text=("x%.0f" % zoom_fac))

                show_locked = False
                show_range = False
                target = self.player.helmet.target_body
                if target and target.alive:
                    targcon = self.player.helmet.target_contact
                    sens_by_con = self.player.ac.sensorpack.sensors_by_contact()
                    if "tv" in sens_by_con[targcon]:
                        show_range = True
                        if self.player.input_select_weapon >= 0:
                            wp = self.player.weapons[self.player.input_select_weapon]
                            if isinstance(wp.handle, Launcher) and wp.handle.mtype.seeker:
                                launcher = wp.handle
                                rst, rnds = launcher.ready(target)
                                if rst == "ready":
                                    show_locked = True
                if show_locked:
                    self._mfd_tvdisp_reticle_idle_node.hide()
                    self._mfd_tvdisp_reticle_locked_node.show()
                else:
                    self._mfd_tvdisp_reticle_idle_node.show()
                    self._mfd_tvdisp_reticle_locked_node.hide()
                if show_range:
                    toff = self.player.helmet.target_offset
                    tdist = target.dist(self.player.ac, offset=toff)
                else:
                    tdist = 0.0
                update_text(self._mfd_tvdisp_target_dist_text,
                            text=_rn("%.1f" % (tdist / 1000)))

            elif mfd_mode == "targid":
                target = self.player.helmet.target_body
                if (target and target.alive and
                    target.family in self._mfd_targid_families):

                    acp = self.player.ac
                    dqt = target.dynstate
                    dqp = acp.dynstate

                    if target.species != self._mfd_targit_current_species:
                        self._mfd_targid_notarg_node.hide()
                        self._mfd_targid_data_node.show()
                        self._mfd_targit_current_species = target.species

                        tdb = _targid_database.get(target.species)
                        if tdb is None:
                            tdb = AutoProps()

                        vec_image_path = tdb.vecimagepath
                        if not vec_image_path:
                            vec_image_path = self._mfd_targid_blank_vec_path
                        set_texture(self._mfd_targid_vec_node, vec_image_path,
                                    filtr=False)

                        shortdes = tdb.shortdes or u"--"
                        update_text(self._mfd_targid_title_text,
                                    self._mfd_targid_title_fmt(shortdes))

                        wingload = target.refmass / target.wingarea
                        update_text(self._mfd_targid_wingload_text,
                                    self._mfd_targid_wingload_fmt(wingload))
                        pl_wingload = acp.refmass / acp.wingarea
                        wingload_rd = wingload / pl_wingload - 1.0
                        update_text(self._mfd_targid_wingload_rd_text,
                                    self._mfd_targid_rd_fmt(wingload_rd))

                        #maxlfac = target.maxload
                        #update_text(self._mfd_targid_maxlfac_text,
                                    #self._mfd_targid_maxlfac_fmt(maxlfac))
                        #pl_maxlfac = acp.maxload
                        #maxlfac_rd = maxlfac / pl_maxlfac - 1.0
                        #update_text(self._mfd_targid_maxlfac_rd_text,
                                    #self._mfd_targid_rd_fmt(maxlfac_rd))

                        klass = tdb.klass or "--"
                        klass = klass.replace("-", " ")
                        update_text(self._mfd_targid_klass_text,
                                    self._mfd_targid_klass_fmt(klass))

                        origin = tdb.origin or "--"
                        update_text(self._mfd_targid_origin_text,
                                    self._mfd_targid_origin_fmt(origin))

                        span = tdb.span or sqrt(target.wingaspect * target.wingarea)
                        update_text(self._mfd_targid_span_text,
                                    self._mfd_targid_span_fmt(span))

                        mass = tdb.mass or target.refmass
                        update_text(self._mfd_targid_mass_text,
                                    self._mfd_targid_mass_fmt(mass))

                        maxlfac = target.maxload
                        update_text(self._mfd_targid_maxlfac_text,
                                    self._mfd_targid_maxlfac_fmt(maxlfac))

                    refweight = target.refmass * self.world.absgravacc
                    thrtowt = dqt.tmaxab / refweight
                    update_text(self._mfd_targid_thrtowt_text,
                                self._mfd_targid_thrtowt_fmt(thrtowt))
                    pl_refweight = acp.refmass * self.world.absgravacc
                    pl_thrtowt = dqp.tmaxab / refweight
                    thrtowt_rd = thrtowt / pl_thrtowt - 1.0
                    update_text(self._mfd_targid_thrtowt_rd_text,
                                self._mfd_targid_rd_fmt(thrtowt_rd))

                    perf = target.dyn.tab_all_mh[target.dyn.hasab](target.refmass, dqt.h)
                    spd = dqt.v
                    ispd = target.dyn.resvias(dqt.h, dqt.pr, 0.5 * dqt.rho * spd**2)[1]

                    spdtri = perf[6]
                    ispdtri = target.dyn.resvias(dqt.h, dqt.pr, 0.5 * dqt.rho * spdtri**2)[1]
                    update_text(self._mfd_targid_spdtri_text,
                                self._mfd_targid_spdtri_fmt(ispdtri))
                    ispdtri_rd = ispd / ispdtri - 1.0
                    update_text(self._mfd_targid_spdtri_rd_text,
                                self._mfd_targid_rd_fmt(ispdtri_rd))

                    spdcl = perf[3]
                    ispdcl = target.dyn.resvias(dqt.h, dqt.pr, 0.5 * dqt.rho * spdcl**2)[1]
                    update_text(self._mfd_targid_spdcl_text,
                                self._mfd_targid_spdcl_fmt(ispdcl))
                    spdcl_rd = ispd / ispdcl - 1.0
                    update_text(self._mfd_targid_spdcl_rd_text,
                                self._mfd_targid_rd_fmt(spdcl_rd))

                else:
                    if self._mfd_targit_current_species:
                        self._mfd_targit_current_species = None
                        self._mfd_targid_data_node.hide()
                        self._mfd_targid_notarg_node.show()

            elif mfd_mode == "acinfo":
                pass

        self._mfd_wait_fast_update -= dt
        if self._mfd_wait_fast_update <= 0.0:
            mfd_update_fast_period = self._mfd_update_fast_periods[mmind]
            self._mfd_wait_fast_update += mfd_update_fast_period

            if 0: pass

            elif mfd_mode == "tvdisp":
                phpr = self.player.ac.hpr()
                ppos = self.player.ac.pos()
                targcon = self.player.helmet.target_contact
                sens_by_con = self.player.ac.sensorpack.sensors_by_contact()
                target = self.player.helmet.target_body
                chpr_t = None
                if target and target.alive and "tv" in sens_by_con[targcon]:
                    toff = self.player.helmet.target_offset
                    tpos = target.pos(offset=toff)
                    tpos[2] += target.bbox[2] * 0.33
                    dpos = tpos - ppos
                    chpr_t = vectohpr(dpos)
                    tdist = dpos.length()
                    if len(target.fardists) >= 1 and target.fardists[0] > 0.0:
                        tldist1 = min(target.fardists[0], tdist)
                        tcdist = tldist1 * 0.9
                        cpos_t = intl01vr(tcdist, 0.0, tdist, tpos, ppos)
                    else:
                        tcdist = tdist
                        cpos_t = ppos
                    tsz = target.bbox.length()
                    tangsz = atan(0.5 * tsz / tcdist) * 2
                    cfov_t = degrees(tangsz * 1.0)
                    cfov_ti = self._mfd_tvdisp_wide_fov
                    dh = norm_ang_delta(phpr[0], chpr_t[0], indeg=True)
                    dp = norm_ang_delta(phpr[1], chpr_t[1], indeg=True)
                    if not (self._mfd_tvdisp_gimbal_min_dh < dh < self._mfd_tvdisp_gimbal_max_dh and
                            self._mfd_tvdisp_gimbal_min_dp < dp < self._mfd_tvdisp_gimbal_max_dp):
                        chpr_t = None
                        self.player.helmet.target_contact = None
                        self.player.helmet.target_body = None
                if chpr_t is None:
                    cpos_t = ppos
                    chpr_t = phpr + self._mfd_tvdisp_idle_dhpr
                    cfov_t = self._mfd_tvdisp_idle_fov
                    cfov_ti = self._mfd_tvdisp_idle_fov

                cpos = self._mfd_tvdisp_camera.getPos()
                chpr = self._mfd_tvdisp_camera.getHpr()
                cfov = self._mfd_tvdisp_lens.getMinFov()

                #cdpos = cpos_t - cpos
                #cspdpos = min(cdpos.length() / dt, self._mfd_tvdisp_speed_pos)
                #cvelpos = unitv(cdpos) * cspdpos
                #cpos_n = cpos + cvelpos * dt
                cpos_n = cpos_t

                #cdhpr = chpr_t - chpr
                #maxspdhpr = self._mfd_tvdisp_speed_hpr
                #cvelhpr = Vec3(*[min(abs(dx) / dt, maxspdhpr) * sign(dx)
                                 #for dx in cdhpr])
                #chpr_n = chpr + cvelhpr * dt
                #if any(abs(v) > maxspdhpr * 0.9 for v in cvelhpr):
                    #cfov_t = max(cfov_t, cfov_ti)
                ##chpr_n = chpr_t

                cdir = hprtovec(chpr)
                cdir_t = hprtovec(chpr_t)
                crdir = cdir.cross(cdir_t)
                if crdir.length() > 1e-7:
                    crdir.normalize()
                    crang = cdir.signedAngleDeg(cdir_t, crdir)
                    crspd = min(crang / dt, self._mfd_tvdisp_speed_hpr)
                    rot = Quat()
                    rot.setFromAxisAngle(crspd * dt, crdir)
                    cdir_n = Vec3(rot.xform(cdir))
                    chpr_n = vectohpr(cdir_n)
                    if crspd > self._mfd_tvdisp_speed_hpr * 0.9:
                        cfov_t = max(cfov_t, cfov_ti)
                else:
                    chpr_n = chpr
                #chpr_n = chpr_t

                cdfov = cfov_t - cfov
                cspdfov = min(abs(cdfov) / dt, self._mfd_tvdisp_speed_fov)
                cvelfov = sign(cdfov) * cspdfov
                cfov_n = cfov + cvelfov * dt
                #cfov_n = cfov_t

                self._mfd_tvdisp_camera.setPos(cpos_n)
                self._mfd_tvdisp_camera.setHpr(chpr_n)
                self._mfd_tvdisp_lens.setMinFov(cfov_n)

                #self._mfd_tvdisp_time += dt
                #self._mfd_tvdisp_view_node.setShaderInput("time", self._mfd_tvdisp_time)


    def _init_countermeasures (self):

        if False:
            return False
        self._instr_update_fs.append(self._update_countermeasures)
        self._instr_cleanup_fs.append(self._cleanup_countermeasures)

        # Flare-chaff counter.
        fccntnd = self._model.find("**/cm_screen")
        self._countermeasures_has_flarechaff_counter = not fccntnd.isEmpty()
        if self._countermeasures_has_flarechaff_counter:
            self._countermeasures_has_flarechaff_counter = True
            ret = self._txscmgr.set_texscene(
                node=fccntnd, texsize=128,
                bgimg="images/ui/black.png",
                uvoffscn=self._shdinp.uvoffscn,
                name="flarechaff-counter")
            set_texture(fccntnd,
                        normalmap="images/_normalmap_none.png",
                        glossmap="images/_glossmap_none.png",
                        glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
            fccntnd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
            self._instr_night_light_nodes.append(fccntnd)
            self._countermeasures_flarechaff_counter_scene = ret
            self._countermeasures_flarechaff_counter_font = "fonts/red-october-regular.otf"
            #self._countermeasures_flarechaff_counter_font = "fonts/DidactGothic.ttf"
            self._countermeasures_flarechaff_counter_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)
            self._countermeasures_flarechaff_counter_text = make_text(
                width=1.6, pos=Point3(0.0, 0.0, 0.0),
                font=self._countermeasures_flarechaff_counter_font, size=150,
                color=self._countermeasures_flarechaff_counter_color,
                align="c", anchor="mc",
                parent=self._countermeasures_flarechaff_counter_scene)
            self._countermeasures_flarechaff_counter_prev_count = None
            self._countermeasures_flarechaff_counter_update_period = 0.21
            self._countermeasures_flarechaff_counter_wait_update = 0.0

        return True


    def _cleanup_countermeasures (self):

        if self._countermeasures_has_flarechaff_counter:
            self._countermeasures_flarechaff_counter_scene.removeNode()


    def _update_countermeasures (self, dt):

        if self._countermeasures_has_flarechaff_counter:
            self._countermeasures_flarechaff_counter_wait_update -= dt
            if self._countermeasures_flarechaff_counter_wait_update <= 0.0:
                self._countermeasures_flarechaff_counter_wait_update = self._countermeasures_flarechaff_counter_update_period
                numfc = self.player.ac.flarechaff
                if self._countermeasures_flarechaff_counter_prev_count != numfc:
                    self._countermeasures_flarechaff_counter_prev_count = numfc
                    update_text(self._countermeasures_flarechaff_counter_text,
                                text=("%02d" % min(numfc, 99)))


    def _init_rwr (self):

        screennd = self._model.find("**/rwr_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_rwr)
        self._instr_cleanup_fs.append(self._cleanup_rwr)

        glassnd = self._model.find("**/rwr_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        sc_tc = 1.3
        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=512,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            zoomspec=(sc_tc, 0.0, (sc_tc * 0.94 - 1.0) * 0.5),
            name="rwr")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        h_ref = 1000
        def size_pos_bl (s_ref=h_ref, x_ref=0, z_ref=0):
            #s_ref, x_ref, z_ref = map(float, (s_ref, x_ref, z_ref))
            size = s_ref / (0.5 * h_ref)
            pos = Point2((x_ref + 0.5 * s_ref) / (0.5 * h_ref) - 1.0,
                         (z_ref + 0.5 * s_ref) / (0.5 * h_ref) - 1.0)
            return size, pos

        size, pos = size_pos_bl(1000, 0, 0)
        fixed1nd = make_image(
            texture="images/cockpit/cockpit_mig29_rwr_fixed_1_tex.png",
            size=size, pos=pos, filtr=False, parent=scenend)

        size, pos = size_pos_bl(500, 250, 400)
        fixed2nd = make_image(
            texture="images/cockpit/cockpit_mig29_rwr_fixed_2_tex.png",
            size=size, pos=pos, filtr=False, parent=scenend)

        self._rwr_update_period = 0.571
        self._rwr_wait_update = 0.0

        return True


    def _cleanup_rwr (self):

        pass


    def _update_rwr (self, dt):

        self._rwr_wait_update -= dt
        if self._rwr_wait_update <= 0.0:
            self._rwr_wait_update += self._rwr_update_period


    def _init_imt (self):

        screennd = self._model.find("**/imt_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_imt)
        self._instr_cleanup_fs.append(self._cleanup_imt)

        glassnd = self._model.find("**/imt_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=512,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="imt")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_radar_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)

        h_ref = 1000
        def size_pos_bl (s_ref=h_ref, x_ref=0, z_ref=0):
            #s_ref, x_ref, z_ref = map(float, (s_ref, x_ref, z_ref))
            size = s_ref / (0.5 * h_ref)
            pos = Point2((x_ref + 0.5 * s_ref) / (0.5 * h_ref) - 1.0,
                         (z_ref + 0.5 * s_ref) / (0.5 * h_ref) - 1.0)
            return size, pos

        size, pos = size_pos_bl(1000, 0, 0)
        self._imt_sectors_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_sectors_tex.png",
            size=size, pos=pos, filtr=False, parent=scenend)
        self._imt_sectors_zoom_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_sectors_zoom_tex.png",
            size=size, pos=pos, filtr=False, parent=scenend)
        self._imt_sectors_zoom_node.hide()

        self._imt_num_lock_sectors = 16
        self._imt_lock_sector_nodes = []
        size, pos0 = size_pos_bl(250, 375, 750)
        for i in range(self._imt_num_lock_sectors):
            rhdg = -180.0 + (360.0 / self._imt_num_lock_sectors) * i
            srot, crot = sin(radians(rhdg)), cos(radians(rhdg))
            pos = Point2(crot * pos0[0] - srot * pos0[1],
                         srot * pos0[0] + crot * pos0[1])
            lock_node = make_image(
                texture="images/cockpit/cockpit_mig29_imt_radar_lock_tex.png",
                size=size, pos=pos, hpr=Vec3(0, 0, -rhdg),
                parent=scenend)
            lock_node.hide()
            self._imt_lock_sector_nodes.append(lock_node)
        self._imt_lock_sectors_active = set()
        self._imt_tracker_families = ["plane", "turret"]

        size = size_pos_bl(125)[0]
        self._imt_centerpiece_close_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_centerpiece_close_tex.png",
            size=size,
            parent=scenend)
        self._imt_centerpiece_close_node.hide()

        size = size_pos_bl(125)[0]
        self._imt_track_node = scenend.attachNewNode("track")
        self._imt_missile_base_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_missile_base_tex.png",
            size=size)
        self._imt_missile_below_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_missile_below_tex.png",
            size=size)
        self._imt_missile_above_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_missile_above_tex.png",
            size=size)
        self._imt_approach_time_in_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_approach_time_in_tex.png",
            size=size)
        self._imt_approach_time_out_node = make_image(
            texture="images/cockpit/cockpit_mig29_imt_approach_time_out_tex.png",
            size=size)
        self._imt_rocket_fardist = 8000.0
        self._imt_rocket_neardist = 4000.0
        screen_rad = size_pos_bl(880)[0] * 0.5
        self._imt_fardist_to_screen_scale = screen_rad / self._imt_rocket_fardist
        self._imt_neardist_to_screen_scale = screen_rad / self._imt_rocket_neardist
        self._imt_vert_limit_half_cone = radians(15.0)
        self._imt_rocket_time_in = 2.0
        self._imt_rocket_time_out = 4.0
        self._imt_min_rad_time = screen_rad * 0.05
        self._imt_tracked_rockets = set()
        self._imd_tracked_rocket_nodes = {}

        self._imt_update_period = 0.571
        self._imt_wait_update = 0.0

        self._imt_update_period_fast = 0.066
        self._imt_wait_update_fast = 0.0

        return True


    def _cleanup_imt (self):

        pass


    def _update_imt (self, dt):

        self._imt_wait_update -= dt
        self._imt_wait_update_fast -= dt

        if self._imt_wait_update <= 0.0 or self._imt_wait_update_fast <= 0.0:
            acp = self.player.ac
            pos = acp.pos()
            fdir = acp.quat().getForward()
            hfdir = Vec3(fdir[0], fdir[1], 0.0)
            if hfdir.normalize() == 0.0:
                hfdir = Vec3(0.0, 1.0, 0.0)
            hudir = Vec3(0.0, 0.0, 1.0)
            hrdir = unitv(hfdir.cross(hudir))
            vel = acp.vel()

        if self._imt_wait_update <= 0.0:
            self._imt_wait_update += self._imt_update_period

            trackers = set()
            for family in self._imt_tracker_families:
                for body in self.world.iter_bodies(family):
                    if not body.alive:
                        continue
                    if body.target is acp and body.sensorpack:
                        contact = body.sensorpack.contacts_by_body().get(acp)
                        if (contact and
                            "radar" in body.sensorpack.sensors_by_contact().get(contact)):
                            trackers.add(body)
            #print "--imt-trackers", trackers

            lock_sect_inds = set()
            if trackers:
                for tracker in trackers:
                    dpos = tracker.pos() - pos
                    hdpos = Vec3(dpos[0], dpos[1], 0.0)
                    rhdg = degrees(atan2(dpos.dot(-hrdir), dpos.dot(hfdir)))
                    lock_ind = int(((rhdg + 180.0) / 360.0) * self._imt_num_lock_sectors + 0.5)
                    lock_ind %= self._imt_num_lock_sectors
                    lock_sect_inds.add(lock_ind)
            for lock_ind in self._imt_lock_sectors_active.difference(lock_sect_inds):
                self._imt_lock_sector_nodes[lock_ind].hide()
            for lock_ind in lock_sect_inds:
                self._imt_lock_sector_nodes[lock_ind].show()
            self._imt_lock_sectors_active = lock_sect_inds

            rockets = set()
            for body in self.world.iter_bodies("rocket"):
                if not body.alive:
                    continue
                if body.dist(acp) < self._imt_rocket_fardist:
                    rockets.add(body)
            #print "--imt-rockets", rockets

            for rocket in self._imt_tracked_rockets.difference(rockets):
                swiv = self._imd_tracked_rocket_nodes[rocket][0]
                swiv.removeNode()
                self._imd_tracked_rocket_nodes.pop(rocket)
            for rocket in rockets.difference(self._imt_tracked_rockets):
                swiv = self._imt_track_node.attachNewNode("swiv")
                blip = self._imt_missile_base_node.copyTo(swiv)
                blip.hide()
                above = self._imt_missile_above_node.copyTo(blip)
                above.hide()
                below = self._imt_missile_below_node.copyTo(blip)
                below.hide()
                outbar = self._imt_approach_time_out_node.copyTo(swiv)
                outbar.hide()
                inbar = self._imt_approach_time_in_node.copyTo(swiv)
                inbar.hide()
                self._imd_tracked_rocket_nodes[rocket] = (
                    swiv, blip, above, below, outbar, inbar)
            self._imt_tracked_rockets = rockets

        if self._imt_wait_update_fast <= 0.0:
            self._imt_wait_update_fast += self._imt_update_period_fast
            min_rad_time = self._imt_min_rad_time

            any_far = False
            for rocket in self._imt_tracked_rockets:
                if not rocket.alive:
                    continue
                if (rocket.target is not acp or
                    rocket.dist(acp) > self._imt_rocket_neardist):
                    any_far = True
            if any_far or not self._imt_tracked_rockets:
                self._imt_sectors_node.show()
                self._imt_sectors_zoom_node.hide()
                scr_scale = self._imt_fardist_to_screen_scale
            else:
                self._imt_sectors_node.hide()
                self._imt_sectors_zoom_node.show()
                scr_scale = self._imt_neardist_to_screen_scale

            any_near = False
            for rocket in self._imt_tracked_rockets:
                if not rocket.alive:
                    swiv = self._imd_tracked_rocket_nodes[rocket][0]
                    swiv.hide()
                    continue
                rpos = rocket.pos()
                dpos = rpos - pos
                hdpos = Vec3(dpos[0], dpos[1], 0.0)
                rhdpos = Vec3(dpos.dot(hrdir), dpos.dot(hfdir), dpos.dot(hudir))
                rhdg = degrees(atan2(-rhdpos[0], rhdpos[1]))
                rdir = unitv(dpos)
                rvel = rocket.vel()
                avel = (rvel - vel).dot(-rdir)
                rdist = dpos.length()
                rad_pos = rdist * scr_scale
                rad_time_out = (avel * self._imt_rocket_time_out) * scr_scale
                rad_time_in = (avel * self._imt_rocket_time_in) * scr_scale
                ret = self._imd_tracked_rocket_nodes[rocket]
                vlhcone = atan2(rhdpos[2], rhdpos.getXy().length())
                swiv, blip, above, below, outbar, inbar = ret
                swiv.setR(-rhdg)
                blip.setZ(rad_pos)
                blip.show()
                above.hide()
                below.hide()
                if vlhcone > self._imt_vert_limit_half_cone:
                    above.setR(rhdg)
                    above.show()
                elif vlhcone < -self._imt_vert_limit_half_cone:
                    below.setR(rhdg)
                    below.show()
                outbar.hide()
                inbar.hide()
                if rocket.target is acp:
                    if rad_pos > rad_time_out > min_rad_time:
                        outbar.setZ(rad_time_out)
                        outbar.show()
                    if rad_pos > rad_time_in > min_rad_time:
                        inbar.setZ(rad_time_in)
                        inbar.show()
                    if rad_pos < rad_time_in:
                        any_near = True
            if any_near:
                self._imt_centerpiece_close_node.show()
            else:
                self._imt_centerpiece_close_node.hide()


    def _init_mdi (self):

        screennd = self._model.find("**/mdi_screen")
        if screennd.isEmpty():
            return False
        self._instr_update_fs.append(self._update_mdi)
        self._instr_cleanup_fs.append(self._cleanup_mdi)

        glassnd = self._model.find("**/mdi_glass")
        if not glassnd.isEmpty():
            glassnd.setTransparency(TransparencyAttrib.MAlpha)
            #glassnd.setSa(0.1)
            glassnd.setBin("fixed", 110)
            #set_texture(glassnd,
                #texture="images/cockpit/cockpit_mig29_glass_tex.png",
                #glossmap="images/cockpit/cockpit_mig29_gs.png")

        ret = self._txscmgr.set_texscene(
            node=screennd, texsize=512,
            bgimg="images/ui/black.png",
            uvoffscn=self._shdinp.uvoffscn,
            name="mdi")
        scenend = ret

        set_texture(screennd,
                    normalmap="images/_normalmap_none.png",
                    glossmap="images/_glossmap_none.png",
                    glowmap="images/cockpit/cockpit_mig29_instr_toplt1_gw.png")
        screennd.setShaderInput(self._shdinp.ambln, self._amblnd_instr_dim)
        self._instr_night_light_nodes.append(screennd)

        fixednd = make_quad(parent=scenend, size=2.0)
        fixednd.setTransparency(TransparencyAttrib.MAlpha)
        set_texture(fixednd,
            texture="images/cockpit/cockpit_mig29_mdi_fixed_tex.png",
            filtr=False)

        self._mdi_light_nodes = {}
        for ln in ("airbrake", "flaps", "gear", "grids", "hook"):
            lnd = make_image(
                texture=("images/cockpit/cockpit_mig29_mdi_light_%s_tex.png" % ln),
                size=2.0, parent=scenend)
            lnd.hide()
            self._mdi_light_nodes[ln] = lnd

        self._mdi_gear_warn_node = make_image(
            texture="images/cockpit/cockpit_mig29_mdi_light_warn_tex.png",
            size=2.0, parent=scenend)
        self._mdi_gear_warn_node.hide()
        self._mdi_gear_warn_limit_speed = self.player.ac.maxlandspeed
        self._mdi_gear_warn_limit_otralt = 50.0
        self._mdi_gear_warn_active = False
        self._mdi_gear_warn_wait_blink = 0.0
        self._mdi_gear_warn_blink_period = 0.25

        self._mdi_update_period = 0.231
        self._mdi_wait_update = 0.0

        return True


    def _cleanup_mdi (self):

        pass


    def _update_mdi (self, dt):

        self._mdi_wait_update -= dt

        if self._mdi_wait_update <= 0.0:
            self._mdi_wait_update += self._mdi_update_period

            light_on = {
                "airbrake": self.player.ac.dynstate.brd,
                "flaps": self.player.ac.dynstate.fld,
                "gear": self.player.ac.dynstate.lg,
                "grids": False,
                "hook": False,
            }
            for ln, lnd in self._mdi_light_nodes.items():
                if lnd.isHidden() != (not light_on[ln]):
                    if lnd.isHidden():
                        lnd.show()
                    else:
                        lnd.hide()

            if not self.player.ac.dynstate.lg:
                self._mdi_gear_warn_active = False
                pclrate = self.player.ac.climbrate()
                pspeed = self.player.ac.speed()
                if pclrate < 0.0 and pspeed < self._mdi_gear_warn_limit_speed:
                    ppos = self.player.ac.pos()
                    potralt = self.world.otr_altitude(ppos)
                    if potralt < self._mdi_gear_warn_limit_otralt:
                        self._mdi_gear_warn_active = True
            else:
                self._mdi_gear_warn_active = False
            if not self._mdi_gear_warn_active:
                self._mdi_gear_warn_node.hide()

        if self._mdi_gear_warn_active:
            self._mdi_gear_warn_wait_blink -= dt
            if self._mdi_gear_warn_wait_blink <= 0.0:
                self._mdi_gear_warn_wait_blink += self._mdi_gear_warn_blink_period
                self._warnrec_lamp_on = not self._warnrec_lamp_on
                if self._mdi_gear_warn_node.isHidden():
                    self._mdi_gear_warn_node.show()
                else:
                    self._mdi_gear_warn_node.hide()


    def add_waypoint (self, name, longdes, shortdes,
                      pos, radius, height=None,
                      tozone=None, active=True, exitf=None):

        if name in self._waypoints:
            raise StandardError(
                "Trying to add already existing waypoint '%s'." % name)

        wp = AutoProps()
        wp.name = name
        wp.longdes = longdes
        wp.shortdes = shortdes
        wp.pos = pos
        wp.radius = radius
        wp.height = height
        wp.elev = self.world.elevation(pos)
        self._waypoints[name] = wp
        self._waypoint_keys.append(name)

        if tozone and name not in self._navpoints:
            self.add_navpoint(name, longdes, shortdes, tozone,
                              pos, radius, height, active, exitf=exitf)


        # Create navigation bar node for this waypoint.
        if self.has_hud:
            bfsz = self._hud_base_font_size
            navbarnd = self._hud_waypoint_node.attachNewNode("navbar-%s" % name)
            navbarnd.setPos(0.20, 0.0, -0.40)
            navbarnd.hide()
            self._hud_navbar_nodes[name] = navbarnd
            # Waypoint name.
            namend = make_text(
                shortdes, width=0.5,
                pos=Point3(0.0, 0.0, 0.0),
                font=self._hud_font, size=(1.0 * bfsz),
                color=self._hud_color,
                align="r", anchor="tl", parent=navbarnd)
            # Heading to waypoint.
            headnd = make_text(
                width=0.5,
                pos=Point3(0.0, 0.0, -0.12),
                font=self._hud_font, size=(0.85 * bfsz),
                color=self._hud_color,
                align="r", anchor="tl", parent=navbarnd)
            # Distance to waypoint.
            distnd = make_text(
                width=0.5,
                pos=Point3(0.0, 0.0, -0.22),
                font=self._hud_font, size=(0.85 * bfsz),
                color=self._hud_color,
                align="r", anchor="tl", parent=navbarnd)
            # Altitude difference to waypoint.
            daltnd = None
            if height is None or height >= 0.0:
                daltnd = make_text(
                    width=0.5,
                    pos=Point3(0.0, 0.0, -0.32),
                    font=self._hud_font, size=(0.85 * bfsz),
                    color=self._hud_color,
                    align="r", anchor="tl", parent=navbarnd)

            ndspec = (namend, headnd, distnd, daltnd)
            self._hud_navbar_subnodes[name] = ndspec

        # Create overview map bar node for this waypoint.
        if self.has_mfd and self._mfd_has_overmap:
            sfac = self._mfd_overmap_scale
            cpos = self._mfd_overmap_center
            pos1 = pos
            if isinstance(pos, VBase2):
                pos1 = Point3(pos[0], pos[1], 0.0)
            mpos = (pos1 - cpos) * sfac
            symbnd = self._mfd_overmap_waypoint_node.copyTo(self._mfd_overmap_node)
            symbnd.setX(mpos[0])
            symbnd.setZ(mpos[1])
            namend = make_text(
                shortdes, width=0.5,
                font=self._mfd_font, size=20,
                color=self._mfd_color,
                align="l", anchor="ml",
                parent=self._mfd_overmap_node)
            namend.setX(mpos[0] + self._mfd_overmap_waypoint_text_offset_x)
            namend.setZ(mpos[1] + self._mfd_overmap_waypoint_text_offset_z)
            wpspec = (symbnd, namend)
            self._mfd_overmap_waypoints[name] = wpspec

        if self._current_waypoint is None:
            self.select_waypoint(name)


    def select_waypoint (self, name):

        self._current_waypoint = name
        self._at_current_waypoint = False
        self._waypoint_wait_check = 0.0


    def cycle_waypoint (self):

        if not self._current_waypoint:
            if self._waypoint_keys:
                self.select_waypoint(self._waypoint_keys[0])
        else:
            i = self._waypoint_keys.index(self._current_waypoint)
            i1 = i + 1
            if i1 >= len(self._waypoint_keys):
                i1 = 0
            self.select_waypoint(self._waypoint_keys[i1])


    def _to_marker (self, md):

        ppos = self.player.ac.pos()
        bmpos = md.pos
        if bmpos is None:
            bmpos = Point3()
        if not md.onbody:
            mpos = bmpos
            onground = isinstance(bmpos, VBase2)
        else:
            mpos = md.onbody.pos() + bmpos
            onground = False
        if md.height is not None and md.height < 0.0:
            mpos = Point3(mpos[0], mpos[1], ppos[2])
        elif onground:
            mpos = Point3(mpos[0], mpos[1], md.elev)
        dalt = ppos.getZ() - mpos.getZ()
        dist = (ppos - mpos).length()
        dhead = hpr_to(ppos, mpos)[0]
        there = (md.radius is not None and dist < md.radius and
                 (md.height is None or md.height < 0.0 or
                  (onground and 0.0 < dalt < md.height) or
                  (not onground and -0.5 * md.height < dalt < 0.5 * md.height)))
        return there, dist, dalt, dhead


    def at_waypoint (self, name):

        return self._to_marker(self._waypoints[name])[0]


    def waypoint_dist (self, key):

        wp = self._waypoints[key]
        if isinstance(wp.pos, VBase2):
            dpos = wp.pos - self.player.ac.pos().getXy()
        else:
            dpos = wp.pos - self.player.ac.pos()
        return dpos.length()


    def add_navpoint (self, name, longdes, shortdes, tozone,
                      pos=None, radius=None, height=None,
                      active=True, onbody=None, aerotow=False, exitf=None):

        if not name:
            name = "!anon-%d" % self._navpoint_anon_counter
            self._navpoint_anon_counter += 1
        if name in self._navpoints:
            raise StandardError(
                "Trying to add already existing navpoint '%s'." % name)

        np = AutoProps()
        np.name = name
        np.longdes = longdes
        np.shortdes = shortdes
        np.pos = pos
        np.radius = radius
        np.height = height
        np.tozone = tozone
        np.active = active
        np.onbody = onbody
        np.aerotow = aerotow
        np.exitf = exitf

        if not np.onbody and isinstance(np.pos, VBase2):
            np.elev = self.world.elevation(np.pos)

        self._navpoints[name] = np

        return name


    def update_navpoint (self, name, tozone=False,
                         pos=False, radius=False, height=False,
                         active=None, onbody=False, aerotow=False, exitf=False):

        if name not in self._navpoints:
            raise StandardError("Trying to update non-existing navpoint '%s'." % name)

        np = self._navpoints[name]
        if tozone is not False:
            np.tozone = tozone
        if pos is not False:
            np.pos = pos
        if radius is not False:
            np.radius = radius
        if height is not False:
            np.height = height
        if active is not None:
            np.active = active
        if onbody is not False:
            np.onbody = onbody
        if aerotow is not False:
            np.aerotow = aerotow
        if exitf is not False:
            np.exitf = exitf

        if not np.onbody and isinstance(np.pos, VBase2):
            np.elev = self.world.elevation(np.pos)


    def active_navpoints (self):

        actnps = []
        for npname, np in self._navpoints.items():
            if np.onbody and (not np.onbody.alive or np.onbody.shotdown):
                self._navpoints.pop(npname)
            elif (np.active() if callable(np.active) else np.active):
                if np.aerotow:
                    if self._aerotow_active(np.onbody):
                        actnps.append(np)
                elif self._to_marker(np)[0]:
                    actnps.append(np)
        return actnps


    def _aerotow_active (self, tac):

        active = False
        # FIXME: Temporary, until in-game hook implemented.
        if not tac.shotdown:
            bdist = self.player.ac.dist(tac)
            if bdist < self._aerotow_max_dist:
                spdiff = abs(self.player.ac.speed() - tac.speed())
                offb = self.player.ac.offbore(tac)
                offbinv = tac.offbore(self.player.ac)
                if (spdiff < self._aerotow_max_speed_diff and
                    offb < self._aerotow_max_offbore and
                    offbinv > pi - self._aerotow_max_offbore):
                    active = True
        return active


    def cycle_radar_scale (self, up=False):

        self._radar_scale_shift = 1 if up else -1
        self._radar_contact_wait_update = 0.0


    def cycle_mfd_mode (self, skip=1, force=False):

        if not self.has_mfd:
            return None

        nmms = len(self._mfd_mode_names)
        if nmms < 1:
            return None
        mmind0 = self._mfd_current_mode_index

        if isinstance(skip, basestring):
            if skip in self._mfd_mode_names:
                mmind1 = self._mfd_mode_names.index(skip)
            else:
                mmind1 = mmind0
        else:
            if not self._mfd_mode_can_cycle_over[mmind0]:
                return None
            mmind1 = mmind0
            while True:
                mmind1 = pclamp(mmind1 + skip, 0, nmms)
                if self._mfd_mode_can_cycle_over[mmind1]:
                    break
        if mmind0 == mmind1 and not force:
            return mmind0

        moutf0 = self._mfd_mode_outfs[mmind0]
        if moutf0:
            moutf0()
        self._mfd_root_nodes[mmind0].hide() # in case not in moutf0

        minf1 = self._mfd_mode_infs[mmind1]
        if minf1:
            minf1()
        self._mfd_root_nodes[mmind1].show() # in case not in minf1

        self._mfd_current_mode_index = mmind1
        self._mfd_wait_update = 0.0
        self._mfd_wait_fast_update = 0.0

        return mmind1


    def set_view_horiz (self, off=0.0):

        self._view_look_speed = Vec3(self._view_look_max_speed[0] * -off,
                                     0.0,
                                     0.0)
        self._view_look_acc = Vec3(self._view_look_max_acc[0] * -off,
                                   0.0,
                                   0.0)


    def set_view_vert (self, off=0.0):

        self._view_look_speed = Vec3(0.0,
                                     self._view_look_max_speed[1] * off,
                                     0.0)
        self._view_look_acc = Vec3(0.0,
                                   self._view_look_max_acc[1] * off,
                                   0.0)


    def set_view_look (self, off=(0.0, 0.0)):

        self._view_look_speed = Vec3(self._view_look_max_speed[0] * -off[0],
                                     self._view_look_max_speed[1] * off[1],
                                     0.0)
        self._view_look_acc = Vec3(self._view_look_max_acc[0] * -off[0],
                                   self._view_look_max_acc[1] * off[1],
                                   0.0)


    def zoom_view (self, dfov=0.0):

        p = self.player
        ch = self.world.chaser
        if ch is None:
            return
        if ch is p.headchaser:
            self._view_idle_fov_off = clamp(self._view_idle_fov_off + dfov,
                self._view_min_fov_off, self._view_max_fov_off)
            self._view_force_fov = None
            self._view_fov_speed_time = self._view_idle_fov_speed_time
            self._aimzoom_time = 0.0
        elif ch in (p.dimchaser, p.rvchaser, p.targchaser):
            ch.fov = clamp(ch.fov + dfov,
                self._view_min_outside_fov, self._view_max_outside_fov)


    def view_lock_on_off (self, on=None):

        if on is None:
            self._view_ignore_lock = not self._view_ignore_lock
        else:
            self._view_ignore_lock = not on
        return not self._view_ignore_lock


    def add_reported_target (self, body):

        contact = Contact(body=body,
                          family=body.family,
                          side=body.side,
                          pos=body.pos(),
                          vel=body.vel(),
                          track=True)
        self.world.tag_body(tag=DataLink.name_tag(self.player.ac.name),
                            body=body, info=contact, expire=None)


    def remove_reported_target (self, body):

        self.world.expire_body_tag(tag=DataLink.name_tag(self.player.ac.name),
                                   body=body)


class VirtualCockpit (object):

    def __init__ (self, player):

        self._lang = "ru"

        self.player = player
        self.world = player.ac.world

        self.node = self.world.overlay_root.attachNewNode("player-virtcpit")
        shader = make_shader(glow=rgba(255, 255, 255, 0.6))
        self.node.setShader(shader)
        self._text_shader = make_text_shader(glow=rgba(255, 255, 255, 0.6))
        #self.node = self.world.uiface_root.attachNewNode("player-virtcpit")
        #self._text_shader = None

        self.node.setSa(1.0)

        # Setup instruments.
        self._instr_update_fs = []
        self._instr_cleanup_fs = []
        self._init_attitude()

        self.active = False
        self._prev_active = None

        self.alive = True
        base.taskMgr.add(self._loop, "virtcpit-loop", sort=-6)
        # ...should come after helmet loop, before player loop.


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        for clf in self._instr_cleanup_fs:
            clf()
        self.node.removeNode()


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.player.alive or not self.player.ac.alive:
            self.destroy()
            return task.done

        if self._prev_active != self.active:
            self._prev_active = self.active
            if self.active:
                self.node.show()
            else:
                self.node.hide()

        if not self.active:
            return task.cont

        dt = self.world.dt

        # Instruments.
        for upf in self._instr_update_fs:
            upf(dt)

        return task.cont


    def _init_attitude (self):

        self._has_attitude = True
        self._instr_update_fs.append(self._update_attitude)
        self._instr_cleanup_fs.append(self._cleanup_attitude)

        size = 1.0
        hw = base.aspect_ratio
        #pos = Point3(hw - size * 0.5, 0.0, -1.0 + size * 0.5)
        pos = Point3(0.0, 0.0, 0.0)

        #attnd = make_quad(size=size, pos=pos, parent=self.node)
        #res = _create_instr_scene(sname="attitude-slide", snode=attnd)
        #self._attitude_scene, self._attitude_cam, self._attitude_buf = res
        #attnd.setTransparency(TransparencyAttrib.MAlpha)

        attnd = self.node.attachNewNode("virtcpit-attitude")
        attnd.setScale(0.5 * size)
        attnd.setPos(pos)
        self._attitude_scene = attnd
        text_shader = make_text_shader()

        #self._attitude_font = "fonts/DejaVuSans-Bold.ttf"
        self._attitude_font = "fonts/red-october-regular.otf"
        #self._attitude_font = "fonts/DidactGothic.ttf"
        self._attitude_color = rgba(255, 0, 0, 1.0) # (0, 255, 128, 1.0)

        # See comment on sizes and units in Cockpit._init_hud.
        self._attitude_unit = 2.0 / 32.0
        un = self._attitude_unit

        # Base font size.
        self._attitude_base_font_size = 26
        bfsz = self._attitude_base_font_size

        # Pitch bar.
        self._attitude_pitch_period = 0.13
        self._attitude_wait_pitch = 0.0
        self._attitude_horizon_node = self._attitude_scene.attachNewNode("attitude-horizon")
        self._attitude_horizon_node.setPos(0.0, 0.0, 0.0)
        make_image(
            "images/cockpit/cockpit_mig29_hud_horizon_tex.png",
            pos=Point2(0.0, 0.0), size=(16 * un),
            filtr=False, parent=self._attitude_horizon_node)
        self._attitude_pitch_text = make_text(
            width=0.5, pos=Point2(0.40, 0.0),
            font=self._attitude_font, size=(0.85 * bfsz),
            color=self._attitude_color,
            align="l", anchor="bl", parent=self._attitude_horizon_node,
            shader=self._text_shader)
        self._attitude_pitch_ptclim = radians(45)
        self._attitude_pitch_scrlim = 0.4
        self._attitude_pitch_ptc2scr = (self._attitude_pitch_scrlim /
                                        self._attitude_pitch_ptclim)

        # Roll scale.
        self._attitude_roll_period = 0.11
        self._attitude_wait_roll = 0.0
        im = make_image(
            "images/cockpit/cockpit_mig29_hud_roll_scale_tex.png",
            pos=Point2(0.0, 0.0), size=(16 * un),
            filtr=False, parent=self._attitude_scene)
        self._attitude_roll_attitude_node = make_image(
            "images/cockpit/cockpit_mig29_hud_roll_attitude_tex.png",
            pos=Point2(0.0, 0.0), size=(8 * un),
            filtr=False, parent=self._attitude_scene)


    def _cleanup_attitude (self):

        self._attitude_scene.removeNode()


    def _update_attitude (self, dt):

        parent = self.player.ac

        self._attitude_wait_pitch -= dt
        if self._attitude_wait_pitch <= 0.0:
            self._attitude_wait_pitch = self._attitude_pitch_period
            ptc = parent.dynstate.pch
            ptcmlim = self._attitude_pitch_ptclim
            ptcm = clamp(ptc, -ptcmlim, ptcmlim)
            sz = -ptcm * self._attitude_pitch_ptc2scr
            self._attitude_horizon_node.setZ(sz)
            update_text(self._attitude_pitch_text,
                        text=("% .0f" % degrees(ptc)))

        self._attitude_wait_roll -= dt
        if self._attitude_wait_roll <= 0.0:
            self._attitude_wait_roll = self._attitude_roll_period
            sroll = parent.dynstate.bnk
            self._attitude_roll_attitude_node.setR(degrees(sroll))


class TexsceneManager (object):

    _have_panda = True
    _store = {}

    def __init__ (self, name, maxtexsize=2048, mintexsize=64):

        self._name = name
        self._maxtexsize = maxtexsize
        self._mintexsize = mintexsize

        if self._have_panda:
            get = TexsceneManager._store.get(name)
            if get is None:
                tsz = self._maxtexsize
                self._buffer = base.make_texture_buffer(name, tsz, tsz)
                self._texture = self._buffer.getTexture()

                self._scene = NodePath("%s-scene-root" % name)
                self._scene.setDepthTest(False)
                self._scene.setDepthWrite(False)
                self._scene.setMaterialOff(True)
                #self._scene.setTwoSided(True)
                self._scene.setBin("unsorted", 0)

                self._camera = base.make_camera_2d(window=self._buffer)
                self._camera.node().setScene(self._scene)

                put = self._buffer, self._scene, self._camera, self._texture
                TexsceneManager._store[name] = put
            else:
                self._buffer, self._scene, self._camera, self._texture = get
                for node in self._scene.getChildren():
                    node.removeNode()

        if self._maxtexsize % self._mintexsize != 0:
            raise StandardError(
                "Maximum texture size not divisible with minimum size.")
        ndiv = maxtexsize // mintexsize
        nlev = 0
        while ndiv % 2 == 0:
            ndiv //= 2
            nlev += 1
        if ndiv != 1:
            raise StandardError(
                "Ratio of maximum to minimum texture size not a power of two.")
        self._num_tex_lev = nlev
        self._texarea_map = []

        self._scene_id = 0
        self._scenes = []


    def destroy (self):

        pass
        #self._buffer ...
        #TexsceneManager._store.pop(self._name)


    def set_texscene (self, node, texsize,
                      bgimg=None, uvoffscn=None, zoomspec=None,
                      name=None):

        if name is None:
            name = "%s-scene-%d" % (self._name, self._scene_id)
        self._scene_id += 1

        res = self._reserve_texarea(texsize)
        texoffu, texoffv = res[:2]
        #print "--set-texscene", name, texsize, texoffu, texoffv, res[2]

        uoff = texoffu / float(self._maxtexsize)
        voff = texoffv / float(self._maxtexsize)
        ufac = texsize / float(self._maxtexsize)
        vfac = texsize / float(self._maxtexsize)

        if self._have_panda:
            scene = self._scene.attachNewNode(name)

            # Avoid leakage from adjacent scenes.
            offsc = 0.99
            ufac1 = ufac * offsc
            vfac1 = vfac * offsc

            scene.setPos(-1.0 + uoff * 2 + ufac1, 0.0, -1.0 + voff * 2 + vfac1)
            scene.setScale(ufac1, 1.0, vfac1)
            #scene.setAntialias(node.getAntialias())

            if zoomspec:
                sc, uc, vc = zoomspec
                ufac2 = ufac1 / sc
                vfac2 = vfac1 / sc
                uoff2 = uoff + ufac2 * ((sc - 1.0) * 0.5 + uc)
                voff2 = voff + vfac2 * ((sc - 1.0) * 0.5 + vc)
            else:
                uoff2, voff2, ufac2, vfac2 = uoff, voff, ufac1, vfac1

            if uvoffscn:
                node.setShaderInput(uvoffscn, Vec4(uoff2, voff2, ufac2, vfac2))
            else:
                node.setTexScale(texstage_color, Vec3(ufac2, vfac2, 1.0))
                node.setTexPos(texstage_color, Vec3(uoff2, voff2, 0.0))
            set_texture(node, texture=self._texture, filtr=False)

            if bgimg:
                make_image(bgimg, size=2.0, pos=Point3(), parent=scene)

            self._scenes.append(scene)
            return scene

        else:
            return texoffu, texoffv


    def _reserve_texarea (self, texsize):

        if texsize <= self._maxtexsize:
            texlevel = int(log(self._maxtexsize // texsize) / log(2))
        else:
            texlevel = -1
        if texlevel < 0:
            raise StandardError(
                "Trying to reserve texture area for size "
                "greater than maximum size (%d > %d)." %
                (texsize, self._maxtexsize))

        texarea_trav = ((0, 0), (1, 0), (1, 1), (0, 1))
        ret = self._reserve_texarea_w(self._texarea_map, texarea_trav,
                                      texlevel, self._maxtexsize,
                                      0, 0, [])
        if not ret:
            raise StandardError(
                "Cannot reserve texture area of requested size (%d)." %
                texsize)
        return ret


    def _reserve_texarea_w (self, areamap, areatrav,
                            texlevel, texsize,
                            texoffu, texoffv, areapath):

        if texlevel == 0:
            if len(areamap) == 0:
                areamap.append(True)
                return texoffu, texoffv, areapath
            else:
                return False
        else:
            texsize1 = texsize // 2
            texlevel1 = texlevel - 1
            for i, (ku, kv) in enumerate(areatrav):
                texoffu1 = texoffu + texsize1 * ku
                texoffv1 = texoffv + texsize1 * kv
                if i < len(areamap):
                    if isinstance(areamap[i], list):
                        ret = self._reserve_texarea_w(areamap[i], areatrav,
                                                      texlevel1, texsize1,
                                                      texoffu1, texoffv1,
                                                      areapath + [i])
                    else:
                        ret = False
                        break
                else:
                    areamap1 = []
                    ret = self._reserve_texarea_w(areamap1, areatrav,
                                                  texlevel1, texsize1,
                                                  texoffu1, texoffv1,
                                                  areapath + [i])
                    if ret:
                        areamap.append(areamap1)
                if ret:
                    return ret


    def activate (self):

        self._camera.node().setActive(True)


    def deactivate (self):

        self._camera.node().setActive(False)


def _gun_lead (world, attacker, cannon, target, offset=None):

    tpos = ptod(target.pos(offset=offset))
    tvel = vtod(target.vel())
    tacc = vtod(target.acc())
    apos = ptod(attacker.pos())
    ret = cannon.launch_dynamics(dbl=True)
    sfvel, sdvelp, sfacc, sdaccp, setime = ret
    ret = intercept_time(tpos, tvel, tacc, apos, sfvel, sdvelp, sfacc, sdaccp,
                         finetime=setime, epstime=5e-3, maxiter=5)
    if not ret:
        return None
    inttime, tpos1, ddir1 = ret
    aquat = qtod(attacker.quat())
    afdir = aquat.getForward()
    if afdir.dot(ddir1) < 0.0: # no rear hemisphere
        return None
    audir = aquat.getUp()
    ardir = aquat.getRight()
    ddir0 = unitv(tpos - apos)
    angh0 = atan2(ddir0.dot(ardir), ddir0.dot(afdir))
    angv0 = 0.5 * pi - acos(clamp(ddir0.dot(audir), -1.0, 1.0))
    #ddir1 = unitv(tpos1 - apos)
    angh1 = atan2(ddir1.dot(ardir), ddir1.dot(afdir))
    angv1 = 0.5 * pi - acos(clamp(ddir1.dot(audir), -1.0, 1.0))

    #langh = angh1; langv = angv1
    langh = angh0 - angh1; langv = angv0 - angv1
    #langh = angh0; langv = angv0 # test hud
    #print "--gun-lead-ang", degrees(langh), degrees(langv)
    return langh, langv, angh0, angv0


def _bore_angles (attacker, target, offset=None):

    tpos = ptod(target.pos(offset=offset))
    apos = ptod(attacker.pos())
    aquat = qtod(attacker.quat())
    afdir = aquat.getForward()
    audir = aquat.getUp()
    ardir = aquat.getRight()
    ddir = unitv(tpos - apos)
    angh = atan2(ddir.dot(ardir), ddir.dot(afdir))
    angv = 0.5 * pi - acos(clamp(ddir.dot(audir), -1.0, 1.0))
    return angh, angv


def _rn (nstr):

    nstr = nstr.replace(".", ",")
    return nstr


_targid_database = {
    "mig29": AutoProps(
        shortdes=u"МиГ-29",
        klass=u"истребитель",
        vecimagepath="models/aircraft/mig29/mig29_vec.png",
        origin=u"СССР",
        span=None,
        mass=None,
    ),
    "su27": AutoProps(
        shortdes=u"Су-27",
        klass=u"истребитель",
        vecimagepath="models/aircraft/su27/su27_vec.png",
        origin=u"СССР",
        span=None,
        mass=None,
    ),
    "f15": AutoProps(
        shortdes=u"Ф-15",
        klass=u"истребитель",
        vecimagepath="models/aircraft/f15/f15_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
    "f18": AutoProps(
        shortdes=u"Ф/А-18",
        klass=u"истребитель-бомбардировщик",
        vecimagepath="models/aircraft/f18/f18_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
    "f16": AutoProps(
        shortdes=u"Ф-16",
        klass=u"истребитель",
        vecimagepath="models/aircraft/f16/f16_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
    "f22": AutoProps(
        shortdes=u"Ф-22",
        klass=u"истребитель",
        vecimagepath="models/aircraft/f22/f22_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
    "a10": AutoProps(
        shortdes=u"А-10",
        klass=u"штурмовик",
        vecimagepath="models/aircraft/a10/a10_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
    "mirage2000": AutoProps(
        shortdes=u"Мираж 2000",
        klass=u"истребитель",
        vecimagepath="models/aircraft/mirage2000/mirage2000_vec.png",
        origin=u"Франция",
        span=None,
        mass=None,
    ),
    "b1b": AutoProps(
        shortdes=u"Б-1Б",
        klass=u"бомбардировщик",
        vecimagepath="models/aircraft/b1b/b1b_vec.png",
        origin=u"США",
        span=None,
        mass=None,
    ),
}

