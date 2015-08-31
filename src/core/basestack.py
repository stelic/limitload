# -*- coding: UTF-8 -*-

import __builtin__
from bisect import insort_left
from hashlib import md5
from math import degrees, atan
import os
import sys

from pandac.PandaModules import getConfigShowbase
from pandac.PandaModules import GraphicsEngine, GraphicsOutput
from pandac.PandaModules import GraphicsPipe, GraphicsPipeSelection
from pandac.PandaModules import DataGraphTraverser
from pandac.PandaModules import ClockObject, TrueClock
from pandac.PandaModules import WindowProperties, FrameBufferProperties
from pandac.PandaModules import FrameRateMeter
from pandac.PandaModules import NodePath, Texture, TextureStage
from pandac.PandaModules import Camera, PerspectiveLens, OrthographicLens
from pandac.PandaModules import BitMask32
from pandac.PandaModules import MouseAndKeyboard, MouseWatcher
from pandac.PandaModules import ButtonThrower, KeyboardButton, ModifierButtons
from pandac.PandaModules import AudioManager
from pandac.PandaModules import PandaNode
from pandac.PandaModules import PGTop, PGMouseWatcherBackground
from pandac.PandaModules import ModelNode
from pandac.PandaModules import VBase4, Vec4
from pandac.PandaModules import PStatClient
from pandac.PandaModules import storeAccessibilityShortcutKeys, allowAccessibilityShortcutKeys
from pandac.PandaModules import throwNewFrame
from pandac.PandaModules import ConfigVariableBool
from pandac.PandaModules import TransformState, RenderState
from pandac.PandaModules import CardMaker, ColorBlendAttrib, AntialiasAttrib
from pandac.PandaModules import AmbientLight, DirectionalLight
from pandac.PandaModules import Filename
from pandac.PandaModules import TexturePool
from pandac.PandaModules import DynamicTextFont
from pandac.PandaModules import Transform2SG, Trackball
from pandac.PandaModules import ofstream, Notify

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.showbase.Audio3DManager import Audio3DManager
from direct.showbase.BufferViewer import BufferViewer
from direct.showbase.DirectObject import DirectObject
from direct.showbase.EventManagerGlobal import eventMgr
from direct.showbase.JobManagerGlobal import jobMgr
from direct.showbase.Loader import Loader
from direct.showbase.MessengerGlobal import messenger
from direct.showbase.SfxPlayer import SfxPlayer
from direct.task import Task
from direct.task.TaskManagerGlobal import taskMgr

from src import full_path, real_path, path_exists, path_dirname
from src.core.shader import make_blur_shader, make_desat_shader, make_bloom_shader
from src.core.shader import make_shadow_shader
from src.core.transl import *


class BaseStack (DirectObject):

    _created = False

    def __init__ (self, gameconf, inputconf, fixdt=None, randseed=None,
                  pandalog=None):

        self.alive = False # needed if it crashes during initialization

        DirectObject.__init__(self)

        if BaseStack._created:
            raise StandardError(
                "Cannot create multiple instances of '%(class_)s'." %
                dict(class_=BaseStack.__name__))
        BaseStack._created = True

        __builtin__.base = self

        if pandalog is not None:
            fs = ofstream()
            Filename.textFilename(pandalog).openAppend(fs)
            Notify.ptr().setOstreamPtr(fs, False)
            self._panda_log_fs = fs # also prevents garbage collection
        else:
            self._panda_log_fs = None

        # Since we have already started up a TaskManager, and probably
        # a number of tasks; and since the TaskManager had to use the
        # TrueClock to tell time until this moment, make sure the
        # GlobalClock object is exactly in sync with the TrueClock.
        # Then we can make the TaskManager start using the new GlobalClock.
        global_clock = ClockObject.getGlobalClock()
        true_clock = TrueClock.getGlobalPtr()
        global_clock.setRealTime(true_clock.getShortTime())
        global_clock.tick()
        self.global_clock = global_clock
        taskMgr.globalClock = global_clock # for ?

        panda_notify = directNotify.newCategory("BaseStack")
        self.panda_notify = panda_notify

        panda_config = getConfigShowbase()
        self.panda_config = panda_config

        if panda_config.GetBool("disable-sticky-keys", False):
            storeAccessibilityShortcutKeys()
            allowAccessibilityShortcutKeys(False)

        Task.TaskManager.taskTimerVerbose = panda_config.GetBool("task-timer-verbose", False)
        Task.TaskManager.extendedExceptions = panda_config.GetBool("extended-exceptions", False)
        Task.TaskManager.pStatsTasks = panda_config.GetBool("pstats-tasks", False)
        #taskMgr.resumeFunc = PStatClient.resumeAfterPause

        self.taskMgr = taskMgr
        self.messenger = messenger
        __builtin__.taskMgr = taskMgr # for Audio3DManager
        __builtin__.messenger = messenger # for direct/src/fsm/StatePush.py

        graphics_engine = GraphicsEngine.getGlobalPtr()
        self.graphics_engine = graphics_engine
        self.graphicsEngine = graphics_engine # for BufferViewer

        loader = Loader(self)
        graphics_engine.setDefaultLoader(loader.loader)
        self._loader = loader

        with_antialiasing = gameconf.video.multi_sampling_antialiasing
        with_bloom = True
        with_glow_add = False
        with_world_shadows = True
        with_cockpit_shadows = True
        self.with_antialiasing = with_antialiasing
        self.with_bloom = with_bloom
        self.with_glow_add = with_glow_add
        self.with_world_shadows = with_world_shadows
        self.with_cockpit_shadows = with_cockpit_shadows
        ret = BaseStack._setup_window(panda_notify, panda_config, graphics_engine,
                                      with_antialiasing, with_bloom)
        window, wbuffer = ret
        #is_main_window = True
        #messenger.send("open_window", [window, is_main_window])
        #messenger.send("open_main_window")
        self.window = window
        self.win = window # for BufferViewer
        self.pipe = window.getPipe()
        self.wbuffer = wbuffer
        self.config = panda_config # for DirectGuiBase

        aspect_ratio = BaseStack._get_aspect_ratio(window)
        self.aspect_ratio = aspect_ratio

        ret = BaseStack._get_window_size(window)
        window_size_x, window_size_y = ret
        self.window_size_x = window_size_x
        self.window_size_y = window_size_y

        ret = BaseStack._setup_render(window, wbuffer,
                                      with_antialiasing, with_bloom,
                                      with_world_shadows, with_cockpit_shadows)
        (render_roots, render_cameras, postproc_specs, shadow_specs,
         bloom_specs) = ret
        (stack_root,
         world_root, cockpit_root, helmet_root, overlay_root,
         stage_root, uiface_root, front_root, square_root,
         world_shadow_root, cockpit_shadow_root) = render_roots
        (desat_factor_pack, rad_desat_spec, rad_darken_spec,
         sun_blind_spec) = postproc_specs
        (world_shadow_area_size, world_shadow_area_dist,
         world_shadow_texture,
         cockpit_shadow_area_size, cockpit_shadow_area_dist,
         cockpit_shadow_texture) = shadow_specs
        self.stack_root = stack_root
        self.world_root = world_root
        self.cockpit_root = cockpit_root
        self.helmet_root = helmet_root
        self.overlay_root = overlay_root
        self.stage_root = stage_root
        self.uiface_root = uiface_root
        self.front_root = front_root
        self.square_root = square_root
        self.world_shadow_root = world_shadow_root
        self.cockpit_shadow_root = cockpit_shadow_root
        __builtin__.render = world_root # for Audio3DManager
        __builtin__.render2d = square_root # for BufferViewer
        (world_camera, cockpit_camera, helmet_camera,
         stack_camera, overlay_camera,
         world_shadow_camera, cockpit_shadow_camera) = render_cameras
        self.world_camera = world_camera
        self.cockpit_camera = cockpit_camera
        self.helmet_camera = helmet_camera
        self.overlay_camera = overlay_camera
        self.stack_camera = stack_camera
        self.world_shadow_camera = world_shadow_camera
        self.cockpit_shadow_camera = cockpit_shadow_camera
        self._bloom_specs = bloom_specs

        ret = BaseStack._setup_mouse(window, uiface_root)
        data_root, datagraph_trav, mouse_watcher = ret
        self._data_root = data_root
        self._datagraph_trav = datagraph_trav
        self.mouse_watcher = mouse_watcher

        with_fps = panda_config.GetBool("show-frame-rate-meter", False)
        if with_fps:
            frame_rate_meter = FrameRateMeter("frame-rate-meter")
            frame_rate_meter.setupWindow(window)

        with_particles = True
        self.with_particles = with_particles
        if with_particles:
            ret = BaseStack._setup_particles()
            particle_manager, physics_manager = ret
            self._particle_manager = particle_manager
            self._physics_manager = physics_manager
            self.particleMgr = particle_manager # for Particles
            self.physicsMgr = physics_manager # for Particles
            self._particle_dtf = None

        with_sound_doppler = False
        self.with_sound_doppler = with_sound_doppler
        ret = BaseStack._setup_audio(world_camera, with_sound_doppler)
        sfx_player, audio_manager, audio3d_manager, sound_distance_scale = ret
        self.sfx_player = sfx_player
        self.audio_manager = audio_manager
        self.audio3d_manager = audio3d_manager
        self.sound_distance_scale = sound_distance_scale
        self.sfxManagerList = [audio_manager] # for direct.showbase.Loader

        BaseStack._setup_stats(panda_config)

        with_dev = config.GetBool("want-dev", __debug__)
        self.with_dev = with_dev
        __builtin__.__dev__ = with_dev # for direct.* stuff

        buffer_viewer = BufferViewer()
        self.buffer_viewer = buffer_viewer

        self.accept("window-event", self._window_event)

        self._desat_factor_pack = desat_factor_pack
        self.set_desaturation_strength(0.0)
        self._rad_desat_spec = rad_desat_spec
        self._rad_darken_spec = rad_darken_spec
        self._sun_blind_spec = sun_blind_spec

        self.world_shadow_area_size = world_shadow_area_size
        self.world_shadow_area_dist = world_shadow_area_dist
        self.world_shadow_texture = world_shadow_texture
        self.cockpit_shadow_area_size = cockpit_shadow_area_size
        self.cockpit_shadow_area_dist = cockpit_shadow_area_dist
        self.cockpit_shadow_texture = cockpit_shadow_texture

        self._old_exitf = getattr(sys, "exitfunc", None)
        sys.exitfunc = self._exitf

        self._priority_handler_prios = {}
        self._priority_sorted_prios = {}

        self.gameconf = gameconf
        self.inputconf = inputconf
        self.fixdt = fixdt
        self.randseed = randseed

        self._only_cached = False

        self.frame = 0

        self.alive = True

        taskMgr.finalInit()
        # _loop_prev_transform to run first in the frame.
        taskMgr.add(self._loop_prev_transform, "prev-transform", sort=-51)
        # _loop_data to run before most other things in the frame.
        taskMgr.add(self._loop_data, "data", sort=-50)
        # _loop_garbage_collect to run sometimes late in the frame.
        if ConfigVariableBool("garbage-collect-states").getValue():
            taskMgr.add(self._loop_garbage_collect, "garbage-collect", sort=46)
        # _loop_particles to run before _loop_render.
        if with_particles:
            taskMgr.add(self._loop_particles, "particles", sort=48)
        # _loop_render to run after most other things in the frame.
        taskMgr.add(self._loop_render, "render", sort=50)
        # _loop_audio to run after the cull traversal in the _loop_render
        # to update the position of 3D sounds.
        taskMgr.add(self._loop_audio, "audio", sort=60)
        # _loop_once_late to run once after everything in first frame.
        taskMgr.add(self._loop_once_late, "render", sort=100)
        eventMgr.restart()


    def destroy (self):

        if not self.alive:
            return
        self.alive = False

        self.ignoreAll()

        if self.panda_config.GetBool("disable-sticky-keys", False):
            allowAccessibilityShortcutKeys(True)

        self.taskMgr.destroy()

        self.audio_manager.shutdown()

        self._loader.destroy()

        self.graphics_engine.removeAllWindows()

        del self.window
        del self.pipe

        if self._panda_log_fs is not None:
            self._panda_log_fs.close()


    @staticmethod
    def _setup_window (panda_notify, panda_config, graphics_engine,
                       with_antialiasing, with_bloom):

        name = "window"

        winprops = WindowProperties.getDefault()
        winprops.setFixedSize(True)
        if panda_config.GetBool("read-raw-mice", False):
            winprops.setRawMice(True)

        fbprops = FrameBufferProperties(FrameBufferProperties.getDefault())
        if with_antialiasing:
            fbprops.setMultisamples(with_antialiasing)
        else:
            fbprops.setMultisamples(0)

        selection = GraphicsPipeSelection.getGlobalPtr()
        pipe = selection.makeDefaultPipe()
        if not pipe.isValid():
            panda_notify.error("Cannot create the graphics pipe.")
        panda_notify.info("Default graphics pipe is %(type)s (%(name)s)." %
                          dict(type=pipe.getType().getName(),
                               name=pipe.getInterfaceName()))

        flags = (0
            | GraphicsPipe.BFRequireWindow
        )

        window = graphics_engine.makeOutput(pipe=pipe, name=name, sort=0,
                                            fb_prop=fbprops,
                                            win_prop=winprops,
                                            flags=flags)
        if window is None:
            panda_notify.error("Cannot open the window.")

        window.requestProperties(winprops)

        # Make the window really open.
        graphics_engine.openWindows()

        if not window.isValid():
            panda_notify.error("Cannot open the window (not valid).")

        panda_notify.info("Successfully opened window of type %(type)s (%(name)s)." %
                          dict(type=window.getType(),
                               name=window.getPipe().getInterfaceName()))

        gsg = window.getGsg()

        wname = "wbuffer"

        bfbprops = window.getFbProperties()
        #wfbprops = FrameBufferProperties(bfbprops)
        wfbprops = FrameBufferProperties()
        wfbprops.setDepthBits(bfbprops.getDepthBits())
        wfbprops.setColorBits(bfbprops.getColorBits())
        wfbprops.setRedBits(bfbprops.getRedBits())
        wfbprops.setGreenBits(bfbprops.getGreenBits())
        wfbprops.setBlueBits(bfbprops.getBlueBits())
        wfbprops.setAlphaBits(bfbprops.getAlphaBits())
        if with_antialiasing:
            wfbprops.setMultisamples(bfbprops.getMultisamples())
        num_aux_buffers = 1
        if with_bloom:
            num_aux_buffers += 1
        wfbprops.setAuxRgba(num_aux_buffers)

        wflags = (0
            | GraphicsPipe.BFRefuseWindow
        )

        wbuffer = graphics_engine.makeOutput(pipe=pipe, name=wname, sort=0,
                                             fb_prop=wfbprops,
                                             win_prop=winprops,
                                             flags=wflags,
                                             gsg=gsg,
                                             host=window)
        if wbuffer is None:
            panda_notify.error("Cannot create a buffer.")

        color_tex = Texture()
        color_tex.setWrapU(Texture.WMClamp)
        color_tex.setWrapV(Texture.WMClamp)
        wbuffer.addRenderTexture(color_tex, GraphicsOutput.RTMBindOrCopy)

        sunvis_tex = Texture()
        sunvis_tex.setWrapU(Texture.WMClamp)
        sunvis_tex.setWrapV(Texture.WMClamp)
        wbuffer.addRenderTexture(sunvis_tex, GraphicsOutput.RTMBindOrCopy,
                                 GraphicsOutput.RTPAuxRgba0)

        if with_bloom:
            bloom_tex = Texture()
            bloom_tex.setWrapU(Texture.WMClamp)
            bloom_tex.setWrapV(Texture.WMClamp)
            wbuffer.addRenderTexture(bloom_tex, GraphicsOutput.RTMBindOrCopy,
                                     GraphicsOutput.RTPAuxRgba1)

        return window, wbuffer


    @staticmethod
    def _get_window_size (window):

        if window is not None and window.hasSize():
            return window.getSbsLeftXSize(), window.getSbsLeftYSize()
        else:
            if window is None or not hasattr(window, "getRequestedProperties"):
                winprops = WindowProperties.getDefault()
            else:
                winprops = window.getRequestedProperties()
                if not winprops.hasSize():
                    winprops = WindowProperties.getDefault()
            if winprops.hasSize():
                return winprops.getXSize(), winprops.getYSize()
            else:
                return 0, 0


    @staticmethod
    def _get_aspect_ratio (window):

        window_size_x, window_size_y = BaseStack._get_window_size(window)
        if window_size_x != 0 and window_size_y != 0:
            return float(window_size_x) / float(window_size_y)
        else:
            return 1.0


    @staticmethod
    def _setup_render (window, wbuffer,
                       with_antialiasing, with_bloom,
                       with_world_shadows, with_cockpit_shadows):

        aspect_ratio = BaseStack._get_aspect_ratio(window)

        # Create scene root paths.

        def make_root (name):
            root = NodePath(name)
            return root

        def make_root_2d (name, parent=None, uiface=False, square=False):
            if uiface:
                root = NodePath(PGTop(name))
            else:
                root = NodePath(name)
            if not square:
                root.setScale(1.0 / aspect_ratio, 1.0, 1.0)
            root.setDepthTest(False)
            root.setDepthWrite(False)
            root.setMaterialOff(True)
            root.setTwoSided(True)
            root.setBin("unsorted", 0)
            if parent is not None:
                root.reparentTo(parent)
            return root

        world_root = make_root("world-root")

        cockpit_root = make_root("cockpit-root")

        helmet_root = make_root("helmet-root")

        overlay_root = make_root_2d("overlay-root")

        stack_root = make_root_2d("stack-root", square=True)

        action_root = make_root_2d("action-root", parent=stack_root, square=True)

        stage_root = make_root_2d("stage-root", parent=stack_root)

        uiface_root = make_root_2d("uiface-root", parent=stack_root, uiface=True)

        front_root = make_root_2d("front-root", parent=stack_root)

        square_root = make_root_2d("mouse-root", parent=stack_root, square=True)

        if with_world_shadows:
            world_shadow_root = make_root("world-shadow-root")
        else:
            world_shadow_root = None
        if with_cockpit_shadows:
            cockpit_shadow_root = make_root("cockpit-shadow-root")
        else:
            cockpit_shadow_root = None

        render_roots = (stack_root,
                        world_root, cockpit_root, helmet_root, overlay_root,
                        stage_root, uiface_root, front_root, square_root)
        if with_antialiasing:
            for root in render_roots:
                if root is not None:
                    root.setAntialias(AntialiasAttrib.MAuto)
        render_roots = render_roots + (world_shadow_root, cockpit_shadow_root)

        # Assemble rendering stack.

        color_tex = wbuffer.getTexture(0)
        sunvis_tex = wbuffer.getTexture(1)

        if with_bloom:
            bloom_resfac = 0.5
            bloom_size = 0.04 #0.02
            bloom_samples = 60 #30
            with_randrot = False
            if with_randrot:
                res_rand_tex_path = join_data_path("images/randomred2.png")
                rand_tex = TexturePool.loadTexture(res_rand_tex_path)
            bloom_shader_1 = make_blur_shader(dir="u",
                size=bloom_size, numsamples=bloom_samples,
                randrot=with_randrot,
                hfac=aspect_ratio)
            bloom_shader_2 = make_blur_shader(dir="v",
                size=bloom_size, numsamples=bloom_samples,
                randrot=with_randrot,
                hfac=aspect_ratio, desat=0.0)
            bloom_tex_0 = wbuffer.getTexture(2)
            input_tex_pack_1 = [bloom_tex_0]
            if with_randrot:
                input_tex_pack_1.append(rand_tex)
            bloom_tex_1, dummy = BaseStack._setup_screen_tex_render(
                window=window, input_tex=input_tex_pack_1,
                resfac=bloom_resfac, shader=bloom_shader_1)
            input_tex_pack_2 = [bloom_tex_1]
            if with_randrot:
                input_tex_pack_2.append(rand_tex)
            bloom_tex_2, dummy = BaseStack._setup_screen_tex_render(
                window=window, input_tex=input_tex_pack_2,
                resfac=bloom_resfac, shader=bloom_shader_2)
            bloom_tex = bloom_tex_2

        if with_bloom:
            bloom_shdinp_visiblen = "INvisible"
            bloom_shader = make_bloom_shader(limbrthr=0.5, limbrfac=0.4,
                                             visiblen=bloom_shdinp_visiblen)
            main_tex, main_render_quad = BaseStack._setup_screen_tex_render(
                window=window, input_tex=(color_tex, bloom_tex), resfac=1.0,
                shader=bloom_shader)
            main_render_quad.setShaderInput(bloom_shdinp_visiblen, True)
            bloom_specs = (main_render_quad, bloom_shdinp_visiblen)
        else:
            main_tex = color_tex
            bloom_specs = None

        desat_factor_name = "INdesfac"
        desat_factor_pack = []
        rad_desat_name = "INraddes"
        rad_desat_spec = AmbientLight(rad_desat_name)
        rad_desat_spec.setColor(Vec4(1e10, 0.0, 0.0, 0.0))
        rad_desat_node = NodePath(rad_desat_spec)
        rad_darken_name = "INraddark"
        rad_darken_spec = DirectionalLight(rad_darken_name)
        rad_darken_spec.setColor(Vec4(1e10, 0.0, 0.0, 0.0))
        rad_darken_spec.setSpecularColor(Vec4(0.0, 0.0, 0.0, 0.0))
        rad_darken_node = NodePath(rad_darken_spec)
        sun_blind_name = ("INsunblind1", "INsunblind2")
        sun_blind_spec = (AmbientLight("sunblind1"),
                          AmbientLight("sunblind2"))
        sun_blind_spec[0].setColor(Vec4(0.0, 0.0, 0.0, 0.0))
        sun_blind_spec[1].setColor(Vec4(0.0, 0.0, 0.0, 0.0))
        sun_blind_node = (NodePath(sun_blind_spec[0]),
                          NodePath(sun_blind_spec[1]))
        sunbrpnum = (16, 3)
        sunberad = 0.9
        desat_shader = make_desat_shader(
            desfacn=desat_factor_name,
            raddesn=rad_desat_name, raddarkn=rad_darken_name,
            sunblindn=sun_blind_name,
            sunbrpnum=sunbrpnum, sunberad=sunberad,
            sunbmaxout=1e6, sunboexp=2.0, sunbdexp=2.0,
            hfac=aspect_ratio)
        main_tex_2, main_render_quad_2 = BaseStack._setup_screen_tex_render(
            window=window, input_tex=(main_tex, sunvis_tex), resfac=1.0,
            shader=desat_shader)
        main_render_quad_2.setShaderInput(desat_factor_name, 0.0)
        desat_factor_pack.append((main_render_quad_2, desat_factor_name))
        main_render_quad_2.setShaderInput(rad_desat_name, rad_desat_node)
        main_render_quad_2.setShaderInput(rad_darken_name, rad_darken_node)
        main_render_quad_2.setShaderInput(sun_blind_name[0], sun_blind_node[0])
        main_render_quad_2.setShaderInput(sun_blind_name[1], sun_blind_node[1])

        cm = CardMaker("main")
        cm.setFrameFullscreenQuad()
        main_quad = NodePath(cm.generate())
        main_quad.setAntialias(AntialiasAttrib.MNone)
        main_quad.reparentTo(action_root)
        main_quad.setTexture(main_tex_2)

        cm = CardMaker("cover")
        cm.setFrameFullscreenQuad()
        cm.setColor(Vec4(0, 0, 0, 1))
        cover_quad = NodePath(cm.generate())
        cover_quad.setAntialias(AntialiasAttrib.MNone)
        cover_quad.reparentTo(stack_root)
        cover_quad.setTexture(Texture())
        stack_root.setPythonTag("cover", cover_quad)

        clear_rtp = []
        clear_rtp.append(GraphicsOutput.RTPAuxRgba0)
        if with_bloom:
            clear_rtp.append(GraphicsOutput.RTPAuxRgba1)
        world_camera = BaseStack._make_camera(
            window=wbuffer, sort=0, scene=world_root,
            clear_depth=True, clear_color=Vec4(0, 0, 0, 1),
            clear_rtp=clear_rtp)

        cockpit_camera = BaseStack._make_camera(
            window=wbuffer, sort=1, scene=cockpit_root,
            clear_depth=True)
        cockpit_camera.node().getLens().setNear(0.1)
        cockpit_camera.node().getLens().setFar(100.0)

        helmet_camera = BaseStack._make_camera(
            window=wbuffer, sort=2, scene=helmet_root,
            clear_depth=True)
        helmet_camera.node().getLens().setNear(0.01)
        helmet_camera.node().getLens().setFar(1.0)

        overlay_camera = BaseStack._make_camera_2d(
            window=wbuffer, sort=3, scene=overlay_root,
            coords=(-aspect_ratio, aspect_ratio, -1.0, 1.0))

        stack_camera = BaseStack._make_camera_2d(
            window=window, sort=10, scene=stack_root)

        if with_world_shadows:
            world_shadow_area_size = 100.0
            world_shadow_area_dist = 100.0
            world_shadow_texture_size = 2048
            ret = BaseStack._setup_shadow_tex_render(
                name="world", window=window, sort=-2,
                scene=world_shadow_root,
                texsize=world_shadow_texture_size,
                areasize=world_shadow_area_size,
                areadist=world_shadow_area_dist,
                cullback=False,
                copyram=False)
            world_shadow_camera, world_shadow_texture, world_shadow_area_dist = ret
            world_shadow_specs = (world_shadow_area_size, world_shadow_area_dist,
                                  world_shadow_texture)
        else:
            world_shadow_camera = None
            world_shadow_specs = (None, None, None)
        if with_cockpit_shadows:
            cockpit_shadow_area_size = 2.0
            cockpit_shadow_area_dist = 2.0
            cockpit_shadow_texture_size = 2048
            ret = BaseStack._setup_shadow_tex_render(
                name="cockpit", window=window, sort=-1,
                scene=cockpit_shadow_root,
                texsize=cockpit_shadow_texture_size,
                areasize=cockpit_shadow_area_size,
                areadist=cockpit_shadow_area_dist,
                cullback=True,
                copyram=False)
            cockpit_shadow_camera, cockpit_shadow_texture, cockpit_shadow_area_dist = ret
            cockpit_shadow_specs = (cockpit_shadow_area_size, cockpit_shadow_area_dist,
                                    cockpit_shadow_texture)
        else:
            cockpit_shadow_camera = None
            cockpit_shadow_specs = (None, None, None)

        render_cameras = (world_camera, cockpit_camera, helmet_camera,
                          overlay_camera, stack_camera,
                          world_shadow_camera, cockpit_shadow_camera)

        postproc_specs = (desat_factor_pack,
                          rad_desat_spec, rad_darken_spec, sun_blind_spec)

        shadow_specs = world_shadow_specs + cockpit_shadow_specs

        return (render_roots, render_cameras, postproc_specs, shadow_specs,
                bloom_specs)


    @staticmethod
    def _setup_screen_tex_render (window, input_tex, resfac=1.0, shader=None):

        tsx = int(window.getXSize() * resfac)
        tsy = int(window.getYSize() * resfac)
        texbuf = BaseStack._make_texture_buffer("screen-tex", tsx, tsy, window,
                                                wdepth=False, wcolor=True,
                                                walpha=True)
        output_tex = texbuf.getTexture()
        cm = CardMaker("screen-tex")
        cm.setFrameFullscreenQuad()
        quad = NodePath(cm.generate())
        quad.setDepthTest(False)
        quad.setDepthWrite(False)
        quad.setMaterialOff(True)
        quad.setBin("unsorted", 0)
        if isinstance(input_tex, (tuple, list)):
            for i, input_tex_1 in enumerate(input_tex):
                tex_stage_1 = TextureStage("render%d" % i)
                quad.setTexture(tex_stage_1, input_tex_1)
        else:
            quad.setTexture(input_tex)
        if shader is not None:
            quad.setShader(shader)
        camera = BaseStack._make_camera_2d(window=texbuf, scene=quad)
        render_quad = quad
        return output_tex, render_quad


    @staticmethod
    def _setup_shadow_tex_render (name, window, sort, scene,
                                  texsize, areasize, areadist,
                                  cullback=False, copyram=False):

        lens = OrthographicLens()
        lens.setFilmSize(areasize)
        lens.setNearFar(-areadist * 0.5, areadist * 0.5)
        areadist = 0.0

        #lens = PerspectiveLens()
        #lens.setMinFov(degrees(atan(areasize * 0.5 / areadist)) * 2)
        #lens.setNearFar(areadist * 0.5, areadist * 1.5)

        texbuf = BaseStack._make_texture_buffer("%s-shadow" % name,
                                                texsize, texsize,
                                                window,
                                                sort=sort,
                                                copyram=copyram,
                                                wdepth=True, wcolor=False,
                                                walpha=False)
        clear_color = Vec4(1, 1, 1, 1)
        cam = BaseStack._make_camera(
            window=texbuf, sort=sort, scene=scene, lens=lens,
            clear_depth=True, clear_color=clear_color)
        shader = make_shadow_shader()
        scene.setShader(shader)
        from pandac.PandaModules import CullFaceAttrib
        if cullback:
            cull = CullFaceAttrib.MCullCounterClockwise # back-faces
        else:
            cull = CullFaceAttrib.MCullClockwise # front-faces
        scene.setAttrib(CullFaceAttrib.make(cull))
        tex = texbuf.getTexture()
        tex.setBorderColor(clear_color)
        tex.setWrapU(Texture.WMBorderColor)
        tex.setWrapV(Texture.WMBorderColor)
        return cam, tex, areadist


    @staticmethod
    def _make_camera (window,
                      sort=0, scene=None,
                      display_region=(0.0, 1.0, 0.0, 1.0),
                      aspect_ratio=None,
                      clear_depth=False, clear_color=None, clear_rtp=[],
                      lens=None, mask=None, name=None):

        if not name:
            name = "camera"
        camnd = Camera(name)
        camera = NodePath(camnd)

        if lens is None:
            lens = PerspectiveLens()
            if aspect_ratio is None:
                aspect_ratio = BaseStack._get_aspect_ratio(window)
            lens.setAspectRatio(aspect_ratio)
        camnd.setLens(lens)

        if scene is not None:
            camnd.setScene(scene)
            camera.reparentTo(scene)

        if mask is not None:
            if isinstance(mask, int):
                mask = BitMask32(mask)
            camnd.setCameraMask(mask)

        dr = window.makeDisplayRegion(*display_region)
        dr.setSort(sort)
        if clear_depth:
            dr.setClearDepthActive(True)
        if clear_color is not None:
            dr.setClearColorActive(True)
            dr.setClearColor(clear_color)
            for rtp in clear_rtp:
                dr.setClearActive(rtp, True)
                dr.setClearValue(rtp, clear_color)
        dr.setCamera(camera)

        return camera


    @staticmethod
    def _make_camera_2d (window,
                         sort=10, scene=None,
                         display_region=(0.0, 1.0, 0.0, 1.0),
                         clear_color=None,
                         coords=(-1.0, 1.0, -1.0, 1.0),
                         lens=None, name=None):

        if not name:
            name = "camera2d"
        camnd = Camera(name)
        camera = NodePath(camnd)

        if lens is None:
            left, right, bottom, top = coords
            lens = OrthographicLens()
            lens.setFilmSize(right - left, top - bottom)
            lens.setFilmOffset((right + left) * 0.5, (top + bottom) * 0.5)
            lens.setNearFar(-1000, 1000)
        camnd.setLens(lens)

        if scene is not None:
            camnd.setScene(scene)
            camera.reparentTo(scene)

        dr = window.makeDisplayRegion(*display_region)
        dr.setSort(sort)
        dr.setClearDepthActive(True)
        if clear_color is not None:
            dr.setClearColorActive(True)
            dr.setClearColor(clear_color)
        dr.setCamera(camera)
        # Make any texture reloads on the gui come up immediately.
        dr.setIncompleteRender(False)

        return camera


    @staticmethod
    def _setup_mouse (window, uiface_root):

        data_root_node = NodePath("data-root")
        data_root = data_root_node.node()
        datagraph_trav = DataGraphTraverser()

        # For each mouse/keyboard device, we create
        #  - MouseAndKeyboard
        #  - MouseWatcher
        #  - ButtonThrower
        # Given a ButtonThrower, one can access the MouseWatcher and
        # MouseAndKeyboard using getParent.
        #
        # The MouseAndKeyboard generates mouse events and mouse
        # button/keyboard events; the MouseWatcher passes them through
        # unchanged when the mouse is not over a 2-d button, and passes
        # nothing through when the mouse *is* over a 2-d button.  Therefore,
        # objects that don't want to get events when the mouse is over a
        # button, like the driveInterface, should be parented to
        # MouseWatcher, while objects that want events in all cases, like the
        # chat interface, should be parented to the MouseAndKeyboard.
        button_throwers = []
        pointer_watchers = []
        for i in range(window.getNumInputDevices()):
            name = window.getInputDeviceName(i)
            mk = data_root_node.attachNewNode(MouseAndKeyboard(window, i, name))
            mw = mk.attachNewNode(MouseWatcher("watcher%s" % (i)))
            mb = mw.node().getModifierButtons()
            mb.addButton(KeyboardButton.shift())
            mb.addButton(KeyboardButton.control())
            mb.addButton(KeyboardButton.alt())
            mb.addButton(KeyboardButton.meta())
            mw.node().setModifierButtons(mb)
            bt = mw.attachNewNode(ButtonThrower("buttons%s" % (i)))
            if (i != 0):
                bt.node().setPrefix("mousedev%s-" % (i))
            mods = ModifierButtons()
            mods.addButton(KeyboardButton.shift())
            mods.addButton(KeyboardButton.control())
            mods.addButton(KeyboardButton.alt())
            mods.addButton(KeyboardButton.meta())
            bt.node().setModifierButtons(mods)
            button_throwers.append(bt)
            if window.hasPointer(i):
                pointer_watchers.append(mw.node())
        selected_button_thrower = button_throwers[0]

        mouse_watcher = selected_button_thrower.getParent()
        uiface_root.node().setMouseWatcher(mouse_watcher.node())
        mouse_watcher.node().addRegion(PGMouseWatcherBackground())

        return data_root, datagraph_trav, mouse_watcher


    @staticmethod
    def _setup_particles ():

        from direct.particles.ParticleManagerGlobal import particleMgr
        from direct.showbase.PhysicsManagerGlobal import physicsMgr
        from pandac.PandaModules import LinearEulerIntegrator

        particle_manager = particleMgr
        particle_manager.setFrameStepping(1)

        integrator = LinearEulerIntegrator()
        physics_manager = physicsMgr
        physics_manager.attachLinearIntegrator(integrator)

        return particle_manager, physics_manager


    @staticmethod
    def _setup_audio (world_camera, with_sound_doppler):

        sfx_player = SfxPlayer()

        audio_manager = AudioManager.createAudioManager()

        audio3d_manager = Audio3DManager(audio_manager, world_camera,
                                         taskPriority=43)
        # taskPriority= (actually sort= in terms of tasks) has to be greater
        # than the sort= of effects.Sound3D loops.
        #sound_distance_scale = 0.3048 # default in ft, scale to m
        sound_distance_scale = 1.0 # world coordinates in meters
        audio3d_manager.setDistanceFactor(sound_distance_scale)
        audio3d_manager.setDropOffFactor(1.0)
        if with_sound_doppler:
            audio3d_manager.setDopplerFactor(1.0)
            # ...if > 1.0 exaggerated Doppler effect, if < 1.0 reduced.

        return sfx_player, audio_manager, audio3d_manager, sound_distance_scale


    @staticmethod
    def _setup_stats (panda_config, hostname=None, port=None):

        if not panda_config.GetBool("want-pstats", False):
            return False

        if PStatClient.isConnected():
            PStatClient.disconnect()
        # These default values match the C++ default values.
        if hostname is None:
            hostname = ""
        if port is None:
            port = -1
        PStatClient.connect(hostname, port)
        return PStatClient.isConnected()


    def _window_event (self, window):

        if window == self.window: # really ==
            winprops = window.getProperties()

            if not winprops.getOpen():
                sys.exit() # diverted to self._exitf


    def _exitf (self):

        self.destroy()

        if self._old_exitf:
            self._old_exitf()


    def _loop_prev_transform (self, task):

        PandaNode.resetAllPrevTransform()
        return task.cont


    def _loop_data (self, task):

        self._datagraph_trav.traverse(self._data_root)
        return task.cont


    def _loop_garbage_collect (self, task):

        TransformState.garbageCollect()
        RenderState.garbageCollect()
        return task.cont


    def _loop_particles (self, task):

        if self._particle_dtf:
            dt = self._particle_dtf()
        else:
            dt = self.global_clock.getDt()
        self._particle_manager.doParticles(dt)
        self._physics_manager.doPhysics(dt)

        return task.cont


    def _loop_render (self, task):

        self.graphics_engine.renderFrame()
        throwNewFrame()

        self.frame += 1

        return task.cont


    def _loop_audio (self, task):

        self.audio_manager.update()
        return task.cont


    def _loop_once_late (self, task):

        self.stack_root.getPythonTag("cover").removeNode()
        self.stack_root.clearPythonTag("cover")

        return task.done


    def make_camera (self, window,
                     sort=0, scene=None,
                     display_region=(0.0, 1.0, 0.0, 1.0),
                     aspect_ratio=None, clear_depth=False, clear_color=None,
                     lens=None, mask=None, name=None):

        return BaseStack._make_camera(window=window, sort=sort, scene=scene,
                                      display_region=display_region,
                                      aspect_ratio=aspect_ratio,
                                      clear_depth=clear_depth,
                                      clear_color=clear_color,
                                      lens=lens, mask=mask, name=name)


    def make_camera_2d (self, window,
                        sort=0, scene=None,
                        display_region=(0.0, 1.0, 0.0, 1.0),
                        clear_color=None,
                        coords=(-1.0, 1.0, -1.0, 1.0),
                        lens=None, name=None):

        return BaseStack._make_camera_2d(window=window, sort=sort, scene=scene,
                                         display_region=display_region,
                                         clear_color=clear_color,
                                         coords=coords,
                                         lens=lens, name=name)


    _texture_buffers = []

    @staticmethod
    def _make_texture_buffer (name, sizex, sizey, window,
                              sort=None, copyram=False,
                              wdepth=True, wcolor=True, walpha=True):

        if name is None:
            name = "tbuffer%d" % len(BaseStack._texture_buffers)
        if sort is None:
            sort = len(BaseStack._texture_buffers) + 1
        fbprops = FrameBufferProperties()
        if wdepth:
            fbprops.setDepthBits(1)
        if wcolor:
            fbprops.setColorBits(1)
        if walpha:
            fbprops.setAlphaBits(1)
        winprops = WindowProperties()
        winprops.setSize(sizex, sizey)
        flags = GraphicsPipe.BFRefuseWindow
        tbuffer = window.getEngine().makeOutput(pipe=window.getPipe(),
                                                name=name,
                                                sort=sort,
                                                fb_prop=fbprops,
                                                win_prop=winprops,
                                                flags=flags,
                                                gsg=window.getGsg(),
                                                host=window)
        tex = Texture()
        tex.setWrapU(Texture.WMClamp)
        tex.setWrapV(Texture.WMClamp)
        tex.setMinfilter(Texture.FTLinearMipmapLinear)
        tex.setMagfilter(Texture.FTLinearMipmapLinear)
        if copyram:
            mode = GraphicsOutput.RTMCopyRam
        else:
            mode = GraphicsOutput.RTMBindOrCopy
        tbuffer.addRenderTexture(tex, mode)

        BaseStack._texture_buffers.append(tbuffer)

        return tbuffer


    def make_texture_buffer (self, name, sizex, sizey,
                             wdepth=True, wcolor=True, walpha=True):

        return BaseStack._make_texture_buffer(name, sizex, sizey, self.window,
                                              wdepth=wdepth, wcolor=wcolor,
                                              walpha=walpha)


    def set_desaturation_strength (self, strength):

        for render_quad, desat_factor_name in self._desat_factor_pack:
            render_quad.setShaderInput(desat_factor_name, strength)


    def set_radial_desaturation (self, spec):

        self._rad_desat_spec.setColor(spec)


    def set_radial_darkening (self, rad_spec, ang_spec):

        self._rad_darken_spec.setColor(rad_spec)
        self._rad_darken_spec.setSpecularColor(ang_spec)


    def set_sun_blinding (self, spec0, spec1):

        self._sun_blind_spec[0].setColor(spec0)
        self._sun_blind_spec[1].setColor(spec1)


    def set_particle_dt_function (self, dtf):

        self._particle_dtf = dtf


    def set_priority (self, handler, key, prio):

        handler_prios = self._priority_handler_prios.get(handler)
        if handler_prios is None:
            handler_prios = {}
            self._priority_handler_prios[handler] = handler_prios
        old_prio = handler_prios.get(key)
        handler_prios[key] = prio

        sorted_prios = self._priority_sorted_prios.get(key)
        if sorted_prios is None:
            sorted_prios = []
            self._priority_sorted_prios[key] = sorted_prios
        elif old_prio is not None:
            sorted_prios.remove(old_prio)
        insort_left(sorted_prios, prio)


    def remove_priority (self, handler, key=None):

        handler_prios = self._priority_handler_prios[handler]
        if key is not None:
            keys = [key]
        else:
            keys = handler_prios.keys()
        for key in keys:
            prio = handler_prios.pop(key)
            sorted_prios = self._priority_sorted_prios[key]
            sorted_prios.remove(prio)
            #print "--prio-rem-15", handler, key
            if not sorted_prios:
                self._priority_sorted_prios.pop(key)
        if not handler_prios and key is None:
            self._priority_handler_prios.pop(handler)


    def challenge_priority (self, handler, key):

        handler_prios = self._priority_handler_prios[handler]
        prio = handler_prios[key]
        max_prio = self._priority_sorted_prios[key][-1]
        successful = (prio == max_prio)
        #print "--prio-chl-10", handler, key, prio, max_prio, successful
        return successful


    def run (self):

        self.taskMgr.run()


    _file_key_hex_cache = {}

    def _file_key_hex (self, category, file_path):

        ckey = (category, file_path)
        key_hex = self._file_key_hex_cache.get(ckey)
        if key_hex is None:
            real_file_path = real_path(category, file_path)
            key_hex = md5(open(real_file_path, "rb").read()).hexdigest()
            self._file_key_hex_cache[ckey] = key_hex
        return key_hex


    def _file_cached (self, category, file_path, cache_file_path):

        key_path = cache_file_path + ".key"
        if not path_exists("cache", key_path):
            return False
        key_hex = self._file_key_hex(category, file_path)
        old_key_hex = open(real_path("cache", key_path), "rb").read()
        if old_key_hex != key_hex:
            return False
        if not path_exists("cache", cache_file_path):
            return False
        return True


    def _write_file_key_hex (self, category, file_path, cache_file_path):

        key_hex = self._file_key_hex(category, file_path)
        key_path = cache_file_path + ".key"
        fh = open(real_path("cache", key_path), "wb")
        fh.write(key_hex)
        fh.close()
        return key_hex


    _full_file_cext_path_cache = {}
    _file_object_cache = {}
    _file_path_cache = {}

    def _load_file_with_cache (self, category, file_path_noext,
                               test_ext, cache_ext,
                               load_func, write_func, copy_func, cache):

        ckey = (category, file_path_noext)
        full_file_cext_path = self._full_file_cext_path_cache.get(ckey)
        write_cache = False
        all_ckey_ext = []
        if full_file_cext_path is None:
            # Find actual file path, with extension.
            # Order of extensions is expected to be from likely newer to
            # likely older, in case there are several matching files.
            file_path = self._file_path_cache.get(ckey)
            if file_path is None:
                if isinstance(test_ext, basestring):
                    test_ext = (test_ext,)
                test_ext_cext = test_ext + (cache_ext,)
                # FIXME: Remove extensions from paths in all calls.
                # For the moment, remove extensions here.
                for ext in test_ext_cext:
                    if file_path_noext.endswith(ext):
                        file_path_noext = file_path_noext[:-len(ext)]
                        break
                num_files = 0
                for ext in test_ext_cext:
                    test_file_path = file_path_noext + ext
                    if path_exists(category, test_file_path):
                        file_path = test_file_path
                        num_files += 1
                if num_files == 0:
                    raise StandardError(
                        "File '%s.*' not found." % file_path_noext)
                elif num_files >= 2:
                    raise StandardError(
                        "Multiple files '%s.*' with different extensions." %
                        file_path_noext)
                self._file_path_cache[ckey] = file_path
            if cache and self._only_cached:
                raise StandardError("File '%s' not cached." % file_path)

            if file_path.endswith(cache_ext):
                full_file_cext_path = full_path(category, file_path)
                full_file_load_path = full_file_cext_path
                record_cached = True
            elif cache:
                file_cext_path = file_path_noext + cache_ext
                full_file_cext_path = full_path("cache", file_cext_path)
                record_cached = True
                if self._file_cached(category, file_path, file_cext_path):
                    full_file_load_path = full_file_cext_path
                else:
                    full_file_path = full_path(category, file_path)
                    full_file_load_path = full_file_path
                    write_cache = True
            else:
                record_cached = False
                full_file_path = full_path(category, file_path)
                full_file_load_path = full_file_path

            if record_cached:
                self._full_file_cext_path_cache[ckey] = full_file_cext_path
                # FIXME: Remove extensions from paths in all calls.
                # For the moment, record cached for all extensions too.
                for ext in test_ext_cext:
                    ckey_ext = (category, file_path_noext + ext)
                    self._full_file_cext_path_cache[ckey_ext] = full_file_cext_path
                    all_ckey_ext.append(ckey_ext)

            need_load = True
        else:
            full_file_load_path = full_file_cext_path
            need_load = not copy_func

        if need_load:
            obj = load_func(full_file_load_path)
            if copy_func:
                for ckey_ext in all_ckey_ext:
                    self._file_object_cache[ckey_ext] = obj
        if copy_func:
            cached_obj = self._file_object_cache[ckey]
            obj = copy_func(cached_obj)

        if write_cache:
            cache_dir_path = path_dirname(file_cext_path)
            if not path_exists("cache", cache_dir_path):
                os.makedirs(real_path("cache", cache_dir_path))
            write_func(obj, full_file_cext_path)
            self._write_file_key_hex(category, file_path, file_cext_path)

        return obj


    def set_only_cached (self, active):

        self._only_cached = bool(active)


    def load_model (self, category, model_path_noext, cache=True):

        model = self._load_file_with_cache(
            category=category,
            file_path_noext=model_path_noext,
            test_ext=(".egg", ".egg.pz"),
            cache_ext=".bam",
            load_func=self._load_model_any,
            write_func=self._write_model_bam,
            copy_func=self._copy_model,
            cache=cache)
        return model


    def _load_model_any (self, full_model_path):

        model = self._loader.loadModel(Filename(full_model_path),
                                       noCache=True)
        return model


    def _write_model_bam (self, model, full_model_bam_path):

        model.writeBamFile(Filename(full_model_bam_path))


    def _copy_model (self, base_model):

        parent = NodePath("copy")
        model = base_model.copyTo(parent)
        parent.removeNode()
        return model


    def load_texture (self, category, texture_path_noext):

        texture = self._load_file_with_cache(
            category=category,
            file_path_noext=texture_path_noext,
            test_ext=(".png", ".jpg", ".tga"),
            cache_ext=".txo",
            load_func=self._load_texture_any,
            write_func=self._write_texture_txo,
            copy_func=None,
            cache=True)
        return texture


    def _load_texture_any (self, full_texture_path):

        texture = self._loader.loadTexture(Filename(full_texture_path))
        return texture


    def _write_texture_txo (self, texture, full_texture_txo_path):

        texture.write(Filename(full_texture_txo_path))


    def load_sound (self, category, sound_path):

        full_sound_path = full_path(category, sound_path)
        sound = self._loader.loadSfx(full_sound_path)
        return sound


    _font_cache = {}

    def load_font (self, category, font_path,
                   pixels_per_unit=30, line_height=None,
                   fg_color=None,
                   outline_color=None, outline_width=1.0, outline_feather=0.0):

        pixels_per_unit = int(pixels_per_unit)
        if outline_color is None:
            outline_width = None; outline_feather = None
        ckey = (font_path, pixels_per_unit, line_height, fg_color,
                outline_color, outline_width, outline_feather)
        font = BaseStack._font_cache.get(ckey)
        if font is not None:
            return font

        full_font_path = full_path(category, font_path)
        #font = self._loader.loadFont(full_font_path)
        font = DynamicTextFont(full_font_path, 0)
        font.setPixelsPerUnit(pixels_per_unit)
        if line_height is not None:
            font.setLineHeight(line_height)
        if fg_color is not None:
            font.setFg(fg_color)
        if outline_color is not None:
            font.setOutline(outline_color, outline_width, outline_feather)

        BaseStack._font_cache[ckey] = font
        return font


    def write_model_bam (self, model, category, model_path):

        full_model_path = full_path(category, model_path)
        self._write_model_bam(model, full_model_path)


    def center_mouse_pointer (self):

        center_x = self.window_size_x // 2
        center_y = self.window_size_y // 2
        base.window.movePointer(0, center_x, center_y)


    _vrot_initialized = False
    _vrot_trackball = None
    _vrot_mouse_to_camera = None

    def set_view_rotation (self, active):

        if not BaseStack._vrot_initialized:
            trackball = NodePath(Trackball("trackball"))
            trackball.reparentTo(self.mouse_watcher)
            mouse_to_camera = NodePath(Transform2SG("mouse-to-camera"))
            mouse_to_camera.node().setNode(base.world_camera.node())
            mouse_to_camera.reparentTo(trackball)
            BaseStack._vrot_trackball = trackball
            BaseStack._vrot_mouse_to_camera = mouse_to_camera
            BaseStack._vrot_initialized = True
        mouse_to_camera = BaseStack._vrot_mouse_to_camera
        trackball = BaseStack._vrot_trackball
        camera = self.world_camera
        scene = self.world_root

        if active:
            camera.reparentTo(trackball)
            mouse_to_camera.reparentTo(trackball)
        else:
            camera.reparentTo(scene)
            mouse_to_camera.detachNode()


    def set_bloom (self, visible):

        if not self._bloom_specs:
            return
        quad_node, shdinp_visiblen = self._bloom_specs
        quad_node.setShaderInput(shdinp_visiblen, bool(visible))


    def set_bindings (self, bindings):

        self._bindings = bindings


