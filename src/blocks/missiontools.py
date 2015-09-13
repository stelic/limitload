# -*- coding: UTF-8 -*-

from inspect import isclass
from math import radians, degrees, pi, sin, cos, atan2

from pandac.PandaModules import Vec3, Point2, Point3

from src import join_path, split_path, walk_dir_files
from src.blocks.planes import Mig29fd
from src.core.chaser import TrackChaser
from src.core.misc import AutoProps, great_circle_dist, fill_particles_cache
from src.core.misc import hprtovec, pos_from, pos_from_point
from src.core.misc import make_image
from src.core.misc import uniform, choice
from src.core.misc import dbgval
from src.core.player import Player
from src.core.transl import *


def cache_bodies (include=[]):

    include_base = [
        "particles",
        "weapons",
        "ui",
        "pilot",
        "engine",
        "_none",
    ]
    exclude_base = [
        "heightmaps",
        "terrain",
    ]

    full_include = include_base + include
    full_exclude = exclude_base

    # Models and textures.
    model_paths = []
    texture_paths = []
    for dirpath in (
        join_path("models"),
        join_path("images"),
    ):
        for root, filelist in walk_dir_files("data", dirpath):
            for fn in filelist:
                fp = join_path(root, fn)
                fpels = split_path(fp)
                if (any(e in fpels for e in full_include) and
                    not any(e in fpels for e in full_exclude)):
                    if fn.endswith((".egg", ".egg.pz")):
                        model_paths.append(fp)
                    elif fn.endswith((".png", ".tga", ".jpg")):
                        texture_paths.append(fp)
    model_paths.sort()
    texture_paths.sort()

    model_mode = 1
    if model_mode == 0:
        pass
    elif model_mode == 1:
        for i, model_path in enumerate(model_paths):
            base.load_model("data", model_path)
            #print "--model-cache", model_path, i + 1, len(model_paths)
    else:
        assert False

    texture_mode = base.gameconf.video.preload_textures
    if texture_mode == 0:
        pass
    elif texture_mode == 1:
        # NOTE: Texture loading relies on having Panda configuration variable
        # preload-textures set to true. Or else texture will be really loaded
        # from disk only when it must appear on screen.
        for i, texture_path in enumerate(texture_paths):
            texture = base.load_texture("data", texture_path)
            #print "--texture-cache", texture_path, i + 1, len(texture_paths)
        # ...but still does not work.
        # Nevertheless, it is useful to write cached files on disk.
    elif texture_mode == 2:
        load_tex = base.uiface_root.attachNewNode("load-tex")
        hw = base.aspect_ratio
        for i, texture_path in enumerate(texture_paths):
            np = make_image(texture_path, size=0.01, parent=load_tex)
            #print "--texture-cache", texture_path, i + 1, len(texture_paths)
        make_image("images/ui/black.png", size=(hw * 2, 2.0), parent=load_tex)
        def remove_load_tex (task):
            if task.getElapsedFrames() >= 1:
                load_tex.removeNode()
                return task.done
            return task.cont
        taskMgr.add(remove_load_tex, "load-tex")
    else:
        assert False

    # Plane dynamics.
    from src.core.plane import Plane
    import src.blocks.planes as mod
    for attn, attv in sorted(mod.__dict__.items()):
        if (isclass(attv) and issubclass(attv, Plane) and attv is not Plane
            and attv.species in include):
            attv.derive_dynamics()

    # Cannon dynamics.
    from src.core.shell import Cannon
    import src.blocks.weapons as mod
    for attn, attv in sorted(mod.__dict__.items()):
        if isclass(attv) and issubclass(attv, Cannon) and attv is not Cannon:
            attv.derive_dynamics()

    # Particles.
    fill_particles_cache(1000)


def create_player_1 (mc, world, acsel, name, side, pos, hpr, speed,
                     texture, onground=False, noeject=False):

    if acsel == "mig29fd":
        actype = Mig29fd
        headpos = Point3(0, 4.900, 1.185) # down angle 11 [deg]
        dimpos = Point3(0, -37, 5)
        rvpos = Point3(0, -40, 10)
        cpitpos = Point3(-0.0078, 0.0, 0.0004)
        cpitmfspec = [("longhalf", # mshape
                      1.0, # mscale
                      # Point3(-0.7, 4.6, 0.85), # mpos
                      # Vec3(0.0, 0.0, 0.0), # mphpr
                      # Point3(-0.7, 4.6, 0.85), # mposlt
                      Point3(-0.7, 5.0, 0.65), # mpos
                      Vec3(0.0, 0.0, 0.0), # mphpr
                      Point3(-0.7, 5.0, 0.65), # mposlt
                      )]
        # cpitmfspec = [("square", # mshape
                      # 1.0, # mscale
                      # Point3(-0.7, 5.0, 0.1), # mpos
                      # Vec3(0.0, 0.0, 0.0), # mphpr
                      # Point3(-0.7, 5.0, 0.1), # mposlt
                      # )]
        cpitdownto = Point3(0.0, 5.020, 1.078)
    else:
        raise StandardError("Undefined player aircraft selection '%s'." % acsel)

    texture = mc.player_texture if texture is None else texture
    ac = actype(world=world, name=name, side=side,
                texture=texture,
                fuelfill=(mc.player_fuelfill or 0.50),
                pos=pos, hpr=hpr, speed=speed, onground=onground,
                damage=mc.player_damage,
                faillvl=mc.player_failure_level,
                cnammo=mc.player_ammo_cannons,
                lnammo=mc.player_ammo_launchers)
    if noeject:
        ac.must_eject_time = -1
    #ac.show_state_info(pos=Vec3(-0.5, 0, -0.4))
    player = Player(ac=ac,
                    headpos=headpos,
                    dimpos=dimpos,
                    rvpos=rvpos,
                    cpitpos=cpitpos,
                    cpitmfspec=cpitmfspec,
                    cpitdownto=cpitdownto,
                    mission=mc.mission,
                    mzexitf=zone_exit_player_down)
    world.player = player
    mc.player = player

    if mc.player_mfd_mode:
        player.cockpit.cycle_mfd_mode(mc.player_mfd_mode)

    if mc.prev_zone and mc.player_prev_zone_pos:
        gpos1 = mc.mission.geopos_in_zone(world.georad, mc.prev_zone, mc.player_prev_zone_pos)
        gpos2 = mc.mission.geopos_in_zone(world.georad, mc.zone, pos)
        dfuel = player.ac.subs_fuel_optcruise(gpos1, gpos2, minfuel=0.0)
        dtime = player.ac.get_time_optcruise(gpos1, gpos2)
        if mc.world_day_time is not None:
            world.day_time = mc.world_day_time + dtime
        dbgval(1, "player-zone-travel",
               (mc.prev_zone, "%s", "from-zone"),
               (tuple(mc.player_prev_zone_pos)[:2], "%.0f", "from-pos", "m"),
               (mc.zone, "%s", "to-zone"),
               (tuple(pos)[:2], "%.0f", "to-pos", "m"),
               (great_circle_dist(world.georad, gpos1, gpos2) / 1000.0, "%.0f", "dist", "km"),
               (dtime / 3600.0, "%.2f", "time", "h"),
               (dfuel, "%.0f", "dfuel", "kg"),
               (dfuel / player.ac.maxfuel * 100, "%.1f", "dfuelfill", "%"))
    else:
        if mc.world_day_time is not None:
            world.day_time = mc.world_day_time

    return player


def store_player_state (mc, player):

    mc.player_texture = player.ac.texture
    mc.player_fuelfill = player.ac.fuelfill
    mc.player_ammo_cannons = [x.ammo for x in player.ac.cannons]
    mc.player_ammo_launchers = [1] # 1 indicates direct placement
    mc.player_ammo_launchers.extend(
        (x.mtype, x.points, None) for x in player.ac.launchers)
    mc.player_ammo_launchers.extend(
        (x.ptype, x.points, x.rounds) for x in player.ac.podlaunchers)
    mc.player_ammo_launchers.extend(
        (x.btype, x.points, None) for x in player.ac.droppers)
    mc.player_ammo_launchers.extend(
        (x.ptype, x.points, None) for x in player.ac.jammers)
    mc.player_ammo_launchers.extend(
        (x.stype, x.points, None) for x in player.ac.tankers)
    mc.player_damage = player.ac.damage
    mc.player_failure_level = player.ac.failure_level
    mc.player_prev_zone_pos = player.ac.pos()

    mc.world_day_time = player.ac.world.day_time


def init_wingman (mc, name, side, plane, texture, fuelfill, cnammo, lnammo):

    if not mc.init_wingmen_states:
        mc.init_wingmen_states = dict()
    acstate = AutoProps()
    mc.init_wingmen_states[name] = acstate

    acstate.initial = True
    acstate.side = side
    acstate.plane_type = plane
    acstate.texture = texture
    acstate.fuelfill = fuelfill
    acstate.ammo_cannons = cnammo
    acstate.ammo_launchers = lnammo


def create_wingman (zc, mc, world, player, name, pilotname,
                    pos, hpr, speed, onground=False, texture=None):

    if mc.cross_zone_wingmen_states is None:
        mc.cross_zone_wingmen_states = dict()
    acstate = mc.cross_zone_wingmen_states.get(name)
    if acstate is not None and not acstate.alive:
        return None
    if acstate is None:
        acstate = mc.init_wingmen_states[name]

    ac = acstate.plane_type(
        world=world, name=name, side=acstate.side,
        texture=(texture or acstate.texture),
        fuelfill=acstate.fuelfill,
        pos=pos, hpr=hpr, speed=speed,
        damage=acstate.damage,
        faillvl=acstate.failure_level,
        cnammo=acstate.ammo_cannons,
        lnammo=acstate.ammo_launchers)
    ac.strength = 1e6 #!!!
    ac.maxhitdmg = 1e6 #!!! 

    if mc.prev_zone and not acstate.initial:
        gpos1 = mc.mission.geopos_in_zone(world.georad, mc.prev_zone,
                                          acstate.prev_zone_pos)
        gpos2 = mc.mission.geopos_in_zone(world.georad, mc.zone, pos)
        dfuel = ac.subs_fuel_optcruise(gpos1, gpos2, minfuel=0.0)

    if zc.wingmen is None:
        zc.wingmen = []
    zc.wingmen.append(ac)

    ac.pilot_name = pilotname
    ac.reported_down = False

    return ac


def store_wingman_state (mc, ac):

    if mc.cross_zone_wingmen_states is None:
        mc.cross_zone_wingmen_states = dict()
    acstate = AutoProps()
    mc.cross_zone_wingmen_states[ac.name] = acstate

    acstate.alive = ac.alive
    if ac.alive:
        acstate.plane_type = ac.__class__
        acstate.side = ac.side
        acstate.texture = ac.texture
        acstate.fuelfill = ac.fuelfill
        acstate.ammo_cannons = [x.ammo for x in ac.cannons]
        acstate.ammo_launchers = [1] # 1 indicates direct placement
        acstate.ammo_launchers.extend(
            (x.mtype, x.points, None) for x in ac.launchers)
        acstate.ammo_launchers.extend(
            (x.ptype, x.points, x.rounds) for x in ac.podlaunchers)
        acstate.ammo_launchers.extend(
            (x.btype, x.points, None) for x in ac.droppers)
        acstate.ammo_launchers.extend(
            (x.ptype, x.points, None) for x in ac.jammers)
        acstate.ammo_launchers.extend(
            (x.stype, x.points, None) for x in ac.tankers)
        acstate.damage = ac.damage
        acstate.failure_level = ac.failure_level
        acstate.prev_zone_pos = ac.pos()

    return acstate


def recreate_plane (mc, world, name, pos, hpr=None, speed=None, texture=None):

    acstate = mc.cross_zone_states.get(name)
    if acstate is None:
        return None
    texture = acstate.texture if texture is None else texture
    ac = acstate.plane_type(
        world=world, name=name, side=acstate.side,
        texture=texture,
        fuelfill=acstate.fuelfill,
        pos=pos, hpr=hpr, speed=speed,
        damage=acstate.damage,
        faillvl=acstate.failure_level,
        cnammo=acstate.ammo_cannons,
        lnammo=acstate.ammo_launchers)

    if mc.prev_zone:
        gpos1 = mc.mission.geopos_in_zone(world.georad, mc.prev_zone,
                                          acstate.prev_zone_pos)
        gpos2 = mc.mission.geopos_in_zone(world.georad, mc.zone, pos)
        dfuel = ac.subs_fuel_optcruise(gpos1, gpos2, minfuel=0.0)

    return ac


def store_plane_state (mc, ac):

    if not mc.cross_zone_states:
        mc.cross_zone_states = dict()
    acstate = AutoProps()
    mc.cross_zone_states[ac.name] = acstate

    acstate.plane_type = ac.__class__
    acstate.side = ac.side
    acstate.texture = ac.texture
    acstate.fuelfill = ac.fuelfill
    acstate.ammo_cannons = [x.ammo for x in ac.cannons]
    acstate.ammo_launchers = [1] # 1 indicates direct placement
    acstate.ammo_launchers.extend(
        (x.mtype, x.points, None) for x in ac.launchers)
    acstate.ammo_launchers.extend(
        (x.ptype, x.points, x.rounds) for x in ac.podlaunchers)
    acstate.ammo_launchers.extend(
        (x.btype, x.points, None) for x in ac.droppers)
    acstate.ammo_launchers.extend(
        (x.ptype, x.points, None) for x in ac.jammers)
    acstate.ammo_launchers.extend(
        (x.stype, x.points, None) for x in ac.tankers)
    acstate.damage = ac.damage
    acstate.failure_level = ac.failure_level
    acstate.prev_zone_pos = ac.pos()

    return acstate


def airliner_corridor (zc, mc, gc,
                       ptype, texture, speed,
                       refpoint, heading, width, height, minsep, maxsep,
                       initdist=None,
                       tozone=None, shortdes=None, longdes=None):

    if not zc.world.inside_arena(refpoint):
        raise StandardError("Referent corridor point not inside arena.")

    if isinstance(ptype, (tuple, list)):
        ptypes = ptype
    else:
        ptypes = [ptype]

    if zc.airliner_corridor_num is None:
        zc.airliner_corridor_num = 0
    corrid = chr(ord("a") + zc.airliner_corridor_num)
    zc.airliner_corridor_num += 1

    refdir = hprtovec(Vec3(heading, 0, 0))
    crossdir = hprtovec(Vec3(heading + 90, 0, 0))
    altdir = Vec3(0, 0, 1)
    arena_slack = 10000.0
    awx, awy = zc.world.arena_width()
    length = (awx**2 + awy**2)**0.5 + 2 * arena_slack
    fuelfill = 0.70

    state = AutoProps()
    state.planes = set()
    state.nextsep = uniform(minsep, maxsep)
    state.lasttime = zc.world.time
    if initdist is not None:
        state.lastdist = initdist + state.nextsep
    else:
        state.lastdist = length + uniform(0.0, state.nextsep)
    state.lastplnum = 0
    state.update_period = 4.11
    state.wait_update = 0.0

    def taskf (task):

        if not zc.world.alive:
            return task.done

        state.wait_update -= zc.world.dt
        if state.wait_update > 0.0:
            return task.cont
        state.wait_update += state.update_period

        # Remove planes that exited the arena or are otherwise gone.
        # Fail mission if any shot down.
        for ac in tuple(state.planes):
            pos = ac.pos()
            if ac.shotdown and not mc.mission_failed:
                mission_failed(zc, mc, gc, reason=_("Oops."))
            if not ac.alive or not zc.world.inside_arena(pos, arena_slack):
                state.planes.remove(ac)
                if ac.alive:
                    hdg = ac.hpr()[0]
                    dbgval(1, "airliner-corridor-remove",
                           (corrid, "%s", "id"),
                           ("%s(%s)" % (ac.name, ac.species), "%s", "this"),
                           (pos, "%.0f", "pos", "m"),
                           (hdg, "%.1f", "hdg", "deg"),
                           (len(state.planes), "%d", "total"),
                           (zc.world.time, "%.0f", "time", "s"))
                    ac.destroy()

        # Update last distance along the corridor.
        # NOTE: Do not actually check where last existing plane is,
        # because that is harder and less realistic anyway.
        state.lastdist += speed * (zc.world.time - state.lasttime)
        state.lasttime = zc.world.time

        # Compute where the new plane would appear,
        # and add it if that position is inside arena.
        dist = state.lastdist
        dist_prev = None
        inside_prev = None
        while True:
            dist -= state.nextsep
            crossoff = uniform(-0.5 * width, 0.5 * width)
            altoff = uniform(-0.5 * height, 0.5 * height)
            pos = (refpoint + refdir * dist +
                   crossdir * crossoff + altdir * altoff)
            if zc.world.inside_arena(pos, arena_slack):
                minoffhdg = degrees(atan2(-0.5 * width + crossoff, length))
                maxoffhdg = degrees(atan2(+0.5 * width - crossoff, length))
                hdg = uniform(heading + minoffhdg, heading + maxoffhdg)
                ptype = choice(ptypes)
                name = "airliner-%s-%d" % (corrid, state.lastplnum)
                ac = ptype(world=zc.world, name=name, side="civilian",
                           texture=texture,
                           pos=pos, hpr=Vec3(hdg, 0, 0), speed=speed,
                           fuelfill=fuelfill)
                if zc.player and zc.player.alive and tozone and longdes and shortdes:
                    zc.player.add_navpoint(name=None, longdes=longdes, shortdes=shortdes,
                                           onbody=ac, aerotow=True, tozone=tozone)
                state.planes.add(ac)
                state.lastdist = dist
                state.nextsep = uniform(minsep, maxsep)
                state.lastplnum += 1
                inside = True
                dbgval(1, "airliner-corridor-add",
                      (corrid, "%s", "id"),
                      ("%s(%s)" % (ac.name, ac.species), "%s", "this"),
                      (pos, "%.0f", "pos", "m"),
                      (hdg, "%.1f", "hdg", "deg"),
                      (len(state.planes), "%d", "total"),
                      (zc.world.time, "%.0f", "time", "s"))
            else:
                inside = False
            if dist_prev is not None:
                if not inside and (inside_prev or dist_prev < 0.0):
                    break
            inside_prev = inside
            dist_prev = dist

        return task.cont

    task = base.taskMgr.add(taskf, "airliner-corridor")
    return task


def formation_pair (acl, acw, compact=1.0, jumpto=False):

    formposw = Point3(350 * compact, -500 * compact, -20)
    if jumpto:
        posl = acl.pos()
        hpr = acl.hpr()
        speed = acl.speed()
        posw = pos_from_point(posl, hpr, formposw)
        acw.jump_to(pos=posw, hpr=hpr, speed=speed)
    acw.set_ap(leader=acl, formpos=formposw)


def formation_twopairs (acl, acw, acl2, acw2, compact=1.0, jumpto=False):

    formposw = Point3(350 * compact, -500 * compact, -20)
    formposl2 = Point3(-700 * compact, -1000 * compact, 200)
    formposw2 = Point3(-350 * compact, -500 * compact, -20)
    if jumpto:
        posl = acl.pos()
        hpr = acl.hpr()
        speed = acl.speed()
        posw = pos_from_point(posl, hpr, formposw)
        posl2 = pos_from_point(posl, hpr, formposl2)
        posw2 = pos_from_point(posl2, hpr, formposw2)
        acw.jump_to(pos=posw, hpr=hpr, speed=speed)
        acl2.jump_to(pos=posl2, hpr=hpr, speed=speed)
        acw2.jump_to(pos=posw2, hpr=hpr, speed=speed)
    acw.set_ap(leader=acl, formpos=formposw)
    acl2.set_ap(leader=acl, formpos=formposl2)
    acw2.set_ap(leader=acl2, formpos=formposw2)


def formation_triplet (act, ace1, ace2, compact=1.0, jumpto=False):

    formpose1 = Point3(-1000 * compact, -500 * compact, 0)
    formpose2 = Point3(1000 * compact, 500 * compact, 0)
    if jumpto:
        post = act.pos()
        hpr = act.hpr()
        speed = act.speed()
        pose1 = pos_from_point(post, hpr, formpose1)
        pose2 = pos_from_point(post, hpr, formpose2)
        ace1.jump_to(pos=pose1, hpr=hpr, speed=speed)
        ace2.jump_to(pos=pose2, hpr=hpr, speed=speed)
    ace1.set_ap(leader=act, formpos=formpose1)
    ace2.set_ap(leader=act, formpos=formpose2)


def circle_route (center, radius, starthdg, npoints):

    points = []
    for i in range(npoints):
        hdg = starthdg + i * (360.0 / npoints)
        if isinstance(radius, tuple):
            radius1 = uniform(*radius)
        else:
            radius1 = radius
        ang = radians(hdg) + 0.5 * pi
        offset = Point2(radius1 * cos(ang), radius1 * sin(ang))
        point = center + offset
        points.append(point)
    return points


def zone_wingmen_loop (zc, mc, gc):

    for ac in zc.wingmen:
        if not ac.reported_down and ac.alive and ac.outofbattle:
            zc.player.show_message("notification", "left", _("%s is shotdown.") % ac.pilot_name, duration=4.0)
            ac.reported_down = True

    return zc.world, 1.0


def zone_flyout (zc):

    if not (zc.player and zc.player.alive):
        return 0.0

    zc.world.player_control_level = 2
    zc.player.ac.set_ap(altitude=max(zc.world.max_elevation() + 100.0, zc.player.ac.pos()[2]), turnrate=0.0, maxg=9.0)
    vx = choice([15,-15])
    if zc.player.ac.speed() < 200:
        vy = 200
    else:
        vy = 400
    chaser_away = TrackChaser(world=zc.world,
                              point=pos_from(zc.player.ac, Point3(vx, vy, 0)),
                              relto=None, rotrel=False,
                              atref=zc.player.ac, upref=Vec3(0,0,1),
                              drift=("instlag", 0.0, 0.25),
                              shake=("dynac-distwake", "atref"))
    zc.world.chaser = chaser_away
    ftime = 4.0
    zc.world.fade_out(ftime)
    return ftime


def zone_exit_flyout (zc, mc, gc):

    zc.visited_before = True

    if zc.player and zc.player.alive:
        store_player_state(mc, zc.player)
        for ac in zc.wingmen or []:
            store_wingman_state(zc, ac)
        yield zc.world, zone_flyout(zc)

    zc.world.destroy()


def zone_exit_flyout_wings (zc, mc, gc):

    if not mc.mission_completed and not mc.mission_failed:
        mission_failed(zc, mc, gc, reason=_("You abandoned the mission."))

    if zc.player and zc.player.alive:
        store_player_state(mc, zc.player)
        for ac in zc.wingmen or []:
            store_wingman_state(zc, ac)
        yield zc.world, zone_flyout(zc) + 3.0

    zc.world.destroy()


def zone_exit_player_down (zc, mc, gc):

    pass
    zc.world.destroy()


def zone_exit_end_mission (zc, mc, gc):

    zc.world.destroy()


def cut_action (zc, mc, gc, sawewingmen=True):

    if zc.player and zc.player.alive:
        zc.player.ac.strength = 1e6
        zc.player.ac.maxhitdmg = 1e6
        zc.player.ac.fuelconsfac = 0.0
    if sawewingmen:
        for ac in zc.wingmen or []:
            if ac.alive:
                ac.strength = 1e6
                ac.maxhitdmg = 1e6
                ac.fuelconsfac = 0.0

    for body in zc.world.iter_bodies("rocket"):
        body.explode()

    for ac in zc.world.iter_bodies("plane"):
        pos = ac.pos()
        maxelev = zc.world.max_elevation(pos)
        if pos[2] < maxelev:
            ac.set_ap(altitude=(maxelev + 100.0), turnrate=0.0)
        else:
            ac.set_ap(climbrate=0.0, turnrate=0.0)


def any_family_tracking (families, target):

    anytr = False
    for b in ac.world.iter_bodies(families):
        if b.target is target:
            anytr = True
            break
    return anytr


def any_tracking (trackers, target):

    anytr = False
    for trk in trackers:
        if trk.alive and trk.target is target:
            anytr = True
            break
    return anytr


def object_under_fire (ac):

    for b in ac.world.iter_bodies(["shell", "rocket"]):
        if ac.alive and ac.dist(b) < 1000:
            return True
    return False


def add_base_waypoint (zc, mc, base, name, longdes, shortdes, active=None):

    if not (zc.player and zc.player.alive):
        return
    if active is None:
        active = lambda: mc.mission_completed or mc.mission_failed
    zc.player.add_waypoint(
        name=name, longdes=longdes, shortdes=shortdes,
        pos=base.pos().getXy(), radius=3000.0, height=1000.0,
        tozone="!end", active=active,
        exitf=zone_exit_end_mission)


def mission_completed (zc, mc, gc):

    if not (zc.player and zc.player.alive):
        return
    zc.player.show_message("notification", "left", _("Mission complete!"), duration=4.0)
    if zc.world.action_music:
        zc.world.action_music.set_context("victory")
    mc.mission_completed = True


def mission_failed (zc, mc, gc, reason="Objectives incomplete"):

    if not (zc.player and zc.player.alive):
        return
    zc.player.show_message("notification", "left", reason, duration=1.0)
    zc.player.show_message("notification", "left", _("Mission failed..."), duration=4.0)
    if zc.world.action_music:
        zc.world.action_music.set_context("failure")
    mc.mission_failed = True


