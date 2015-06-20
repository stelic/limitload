# -*- coding: UTF-8 -*-

from math import radians, degrees, cos
import os

from pandac.PandaModules import ClockObject

from src.core import join_path, path_exists, real_path
from src.core.misc import AutoProps, as_sequence
from src.core.misc import report
from src.core.transl import *


class Mission (object):

    def __init__ (self, gamectxt=None):

        if gamectxt is None:
            gamectxt = AutoProps()
        self._game_context = gamectxt
        self._mission_context = AutoProps()
        self._zone_contexts = {}

        self._init_loadfs = []

        self._zone_enterfs = {}
        self._zone_exitfs = {}
        self._zone_loopfs = {}
        self._zone_coords = {}

        self._zone_enterfs_base = {}
        self._zone_exitfs_base = {}
        #self._zone_loopfs_base = {} -- no rewinding for loop functions
        self._zonef_waitspecs = {}

        self._mission_context.mission = self
        self._mission_context.zone = None
        self._mission_context.prev_zone = None
        self._mission_context.next_zone = None

        self.zone_switch_pause = 2.0

        self._mission_stage = "iload0"

        self._loading_info = None

        self.context = self._mission_context

        self._zone_frozen = False

        self._player_kills = []
        self._player_releases = []
        self._player_releases_by_family = {}
        self._player_releases_by_species = {}

        self._end_state = (None, ())

        self.in_sequence = False

        self.ident = None

        self.alive = True
        base.taskMgr.add(self._post_loop, "mission-post-loop", sort=15)
        # ...should come after zone world's post loop.


    def destroy (self):

        if not self.alive:
            return

        # Main loop must call and wait for completion
        # of current zone end function.
        self._mission_stage = "mend"


    def _cleanup (self):

        pass


    def _post_loop (self, task):

        if not self.alive:
            return task.done

        # Within zone.
        if self._mission_stage == "zloop":
            if self._mission_context.next_zone is None:
                # Step zone loop function.
                self._step_zonef(self._mission_context.zone,
                                 self._zone_loopfs)
            else:
                self._mission_stage = "zexit0"

        if self._mission_stage == "zloop0":
            # Wait one frame per core to load stuff from cache.
            if self._switch_dframe < base.gameconf.cpu.use_cores:
                self._switch_dframe += 1
            else:
                self._mission_stage = "zloop"

        # Set up exiting zone.
        if self._mission_stage == "zexit0":
            self._mission_stage = "zexit"

        # Exiting zone.
        if self._mission_stage == "zexit":
            # Wait for completion of zone exit function.
            done = self._step_zonef(self._mission_context.zone,
                                    self._zone_exitfs, self._zone_exitfs_base)
            if done:
                self._mission_stage = "zvoid"
                self._switch_dframe = 0
                self._switch_dtime = 0

        # Pause between zones.
        if self._mission_stage == "zvoid":
            if not self.zone_switch_pause:
                # Wait a few frames to clean up everything from the old zone.
                if self._switch_dframe < 5:
                    self._switch_dframe += 1
                else:
                    self._mission_stage = "zenter0"
            else:
                if self._switch_dtime < self.zone_switch_pause:
                    self._switch_dtime += base.global_clock.getDt()
                else:
                    self._mission_stage = "zenter0"

        # Set up entering zone.
        if self._mission_stage == "zenter0":
            # Setup mission context for exit function.
            self._mission_context.prev_zone = self._mission_context.zone
            self._mission_context.zone = self._mission_context.next_zone
            self._mission_context.next_zone = None
            self._mission_stage = "zenter0b"
            self._switch_dframe = 0
            self._loading_info = ["", ""]
            self._loading_info[0] = _("Loading zone...")
            if not self._zone_started_once(self.ident,
                                           self._mission_context.zone):
                self._loading_info[1] = (
                    _("First entry into this zone, "
                      "generating data may take several minutes."))
            report(_("Switching to zone: %s") % self._mission_context.zone)

        if self._mission_stage == "zenter0b":
            if self._switch_dframe < 2: # for loading screen to update
                self._switch_dframe += 1
            else:
                self._mission_stage = "zenter"
                self._switch_dframe = 0

        # Entering zone.
        if self._mission_stage == "zenter":
            # Wait for completion of zone enter function.
            done = self._step_zonef(self._mission_context.zone,
                                    self._zone_enterfs, self._zone_enterfs_base)
            if self._switch_dframe == 0:
                zc = self._zone_contexts[self._mission_context.zone]
                if zc.world:
                    zc.world.reset_clock()
                #else:
                    #base.global_clock.reset()
                self._loading_info = False
            if done:
                self._mission_context.prev_zone = None
                self._mission_stage = "zloop0"
                self._switch_dframe = 0
                self._store_zone_started_once(self.ident,
                                              self._mission_context.zone)
            else:
                self._switch_dframe += 1

        # Mission has been ordered to end.
        if self._mission_stage == "mend":
            # Wait for completion of zone exit function.
            done = self._step_zonef(self._mission_context.zone,
                                    self._zone_exitfs, self._zone_exitfs_base)
            if done:
                self.alive = False
                self._cleanup()
                return task.done

        # Setup mission data loading.
        if self._mission_stage == "iload0":
            self._loading_info = ["", ""]
            self._loading_info[0] = _("Loading mission...")
            if not self._mission_started_once(self.ident):
                self._loading_info[1] = (
                    _("First start of this mission, "
                      "generating data may take several minutes."))
            self._mission_stage = "iload0b"
            self._switch_dframe = 0

        if self._mission_stage == "iload0b":
            if self._switch_dframe < 2: # for loading screen to update
                self._switch_dframe += 1
            else:
                self._mission_stage = "iload"
                self._switch_dframe = 0

        # Mission is loading data.
        if self._mission_stage == "iload":
            # Wait for completion of mission loading function.
            done = self._step_initf(self._init_loadfs)
            if done:
                self._mission_stage = "idone"

        # Mission initialization completed.
        if self._mission_stage == "idone":
            self._store_mission_started_once(self.ident)
            if self._mission_context.next_zone:
                self._mission_stage = "zenter0"
            else:
                # This can happen only if no zones were added.
                self._mission_stage = "mend"

        return task.cont


    def _step_zonef (self, name, zonefs, bzonefs=None):

        if name is None:
            return True

        if self._zone_frozen:
            return False

        done = True
        lzfs = len(zonefs[name])
        for i in range(lzfs):
            zonef = zonefs[name][i]
            if zonef is None:
                continue
            wclock, wtime = self._zonef_waitspecs.get(zonef, (None, 0.0))
            if wtime <= 0.0:
                if callable(zonef):
                    mc = self._mission_context
                    zc = self._zone_contexts[name]
                    gc = self._game_context
                    res = zonef(zc, mc, gc)
                    if hasattr(res, "next"):
                        if bzonefs is not None:
                            bzonefs[res] = zonef
                        zonefs[name][i] = zonef = res
                        waitspec = (None, 0.0)
                    elif isinstance(res, (float, int)):
                        waitspec = (base.global_clock, res)
                    elif isinstance(res, tuple) and len(res) == 2:
                        waitspec = res
                    elif res is None:
                        waitspec = (None, 0.0)
                    else:
                        raise StandardError(
                            "Bad return value '%s' from one of "
                            "the functions of zone '%s'." % (res, name))
                elif not hasattr(zonef, "next"):
                    raise StandardError(
                        "Expected zone function, got '%s'." % zonef)
                if hasattr(zonef, "next"): # not elif
                    try:
                        res = zonef.next()
                    except StopIteration:
                        if bzonefs is not None:
                            zonefs[name][i] = bzonefs.pop(zonef)
                        else:
                            zonefs[name][i] = None
                        waitspec = None
                    else:
                        if isinstance(res, (float, int)):
                            waitspec = (base.global_clock, res)
                        elif isinstance(res, tuple) and len(res) == 2:
                            waitspec = res
                        elif res is None:
                            waitspec = (None, 0.0)
                        else:
                            raise StandardError(
                                "Bad generator value from one of "
                                "the functions of zone '%s'." % name)
                        done = False
                if waitspec:
                    self._zonef_waitspecs[zonef] = waitspec
                else:
                    self._zonef_waitspecs.pop(zonef)
            else:
                if isinstance(wclock, ClockObject):
                    wtime -= wclock.getDt()
                else:
                    wtime -= wclock.dt
                self._zonef_waitspecs[zonef] = (wclock, wtime)
                done = False

        return done


    def add_zone (self, name, clat, clon,
                  enterf=None, exitf=None, loopf=None):

        if name in self._zone_contexts:
            raise StandardError(
                "Trying to add the already added zone '%s'." % name)
        self._zone_contexts[name] = AutoProps()
        self._zone_enterfs[name] = list(as_sequence(enterf))
        self._zone_exitfs[name] = list(as_sequence(exitf))
        self._zone_loopfs[name] = list(as_sequence(loopf))
        self._zone_coords[name] = (radians(clat), radians(clon))

        # If this is the first added zone,
        # set it to activate unless overridden by switch_zone.
        if self._mission_context.zone is None:
            self._mission_context.next_zone = name


    def switch_zone (self, name, exitf=None):

        if name not in self._zone_contexts and name != "!end":
            raise StandardError(
                "Trying to switch to an undefined zone '%s'." % name)

        if exitf and self._mission_context.zone:
            cname = self._mission_context.zone
            self._zone_exitfs[cname] = [exitf]

        if name != "!end":
            self._mission_context.next_zone = name
        else:
            self.end()


    def switching_zones (self):

        return self._mission_stage != "zloop"


    def _step_initf (self, initfs):

        done = True
        lifs = len(initfs)
        for i in range(lifs):
            initf = initfs[i]
            if initf is None:
                continue

            if callable(initf):
                mc = self._mission_context
                gc = self._game_context
                res = initf(mc, gc)
                if hasattr(res, "next"):
                    initfs[i] = initf = res
                elif isinstance(res, bool):
                    done = res
                elif res is None:
                    done = True
                else:
                    raise StandardError(
                        "Bad return value '%s' from one of "
                        "the mission initialization functions." % res)
            elif not hasattr(zonef, "next"):
                raise StandardError(
                    "Expected initialization function, got '%s'." % initf)

            if hasattr(initf, "next"): # not elif
                try:
                    res = initf.next()
                except StopIteration:
                    initfs[i] = None
                else:
                    if res is None:
                        pass
                    else:
                        raise StandardError(
                            "Bad generator value '%s' from one of "
                            "the mission initialization functions." % res)
                    done = False

        return done


    def add_init (self, loadf=None):

        self._init_loadfs = list(as_sequence(loadf))


    def take_loading_info (self):

        info = self._loading_info
        self._loading_info = None
        return info


    def geopos_in_zone (self, georad, name, pos=None):

        nc, ec = self._zone_coords[name]
        if pos is not None:
            x, y, z = pos
            n = nc + y / georad
            e = ec + x / (georad * cos(n))
        else:
            n = nc
            e = ec
            z = 0.0
        return n, e, z


    def zone_clat_clon (self, name):

        nc, ec = self._zone_coords[name]
        return degrees(nc), degrees(ec)


    def set_zone_frozen (self, frozen):

        self._zone_frozen = frozen


    def record_player_kill (self, kill):

        self._player_kills.append(kill)


    def player_kills (self):

        return self._player_kills


    def record_player_release (self, release):

        self._player_releases.append(release)

        releases = self._player_releases_by_family.get(release.family)
        if releases is None:
            releases = []
            self._player_releases_by_family[release.family] = releases
        releases.append(release)

        releases = self._player_releases_by_species.get(release.species)
        if releases is None:
            releases = []
            self._player_releases_by_species[release.species] = releases
        releases.append(release)


    def player_releases (self, family=None, species=None):

        if species is not None:
            return self._player_releases_by_species.get(species, [])
        elif family is not None:
            return self._player_releases_by_family.get(family, [])
        else:
            return self._player_releases


    def end (self, exitf=None, state="proceed", args=()):

        if exitf is not None and self._mission_context.zone:
            cname = self._mission_context.zone
            if exitf:
                self._zone_exitfs[cname] = [exitf]
            else:
                self._zone_exitfs[cname] = []
        self._end_state = (state, args)
        self.set_zone_frozen(False)
        self.destroy()


    def end_state (self):

        return self._end_state


    @staticmethod
    def _mission_started_once (mname):

        if mname is None:
            return True

        stamp_path = Mission._mission_stamp_path(mname)
        started_once = path_exists("cache", stamp_path)

        return started_once


    @staticmethod
    def _store_mission_started_once (mname):

        if mname is None:
            return

        stamp_path = Mission._mission_stamp_path(mname)
        real_stamp_path = real_path("cache", stamp_path)
        real_stamp_parent_path = os.path.dirname(real_stamp_path)
        if not os.path.exists(real_stamp_parent_path):
            os.makedirs(real_stamp_parent_path)
        if not os.path.exists(real_stamp_path):
            with open(real_stamp_path, "w") as fh:
                pass


    @staticmethod
    def _mission_stamp_path (mname):

        path = join_path("stamp", "%s.stamp" % mname)
        return path


    @staticmethod
    def _zone_started_once (mname, zname):

        if mname is None or zname is None:
            return True

        stamp_path = Mission._zone_stamp_path(mname, zname)
        started_once = path_exists("cache", stamp_path)

        return started_once


    @staticmethod
    def _store_zone_started_once (mname, zname):

        if mname is None or zname is None:
            return

        stamp_path = Mission._zone_stamp_path(mname, zname)
        real_stamp_path = real_path("cache", stamp_path)
        real_stamp_parent_path = os.path.dirname(real_stamp_path)
        if not os.path.exists(real_stamp_parent_path):
            os.makedirs(real_stamp_parent_path)
        if not os.path.exists(real_stamp_path):
            with open(real_stamp_path, "w") as fh:
                pass


    @staticmethod
    def _zone_stamp_path (mname, zname):

        path = join_path("stamp", "%s--%s.stamp" % (mname, zname))
        return path


