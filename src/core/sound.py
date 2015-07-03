# -*- coding: UTF-8 -*-

from pandac.PandaModules import AudioSound
from pandac.PandaModules import Vec3

from src import full_path
from src.core.misc import AutoProps
from src.core.misc import dbgval


# FIXME: Due to a bug (?) in some sound systems,
# at most one sound can be started or stopped in single frame.
_sound_exec_inited = [False]
_sound_exec_schedule = []

def _exec_sound_method (sndf, args=[]):

    if base.gameconf.audio.sound_system in ("fmod",):
        # NOTE: This is against documented behavior. A bug?
        _sound_exec_schedule.append((sndf, args))
        if not _sound_exec_inited[0]:
            _sound_exec_inited[0] = True
            def taskf (task):
                if _sound_exec_schedule:
                    sndf, args = _sound_exec_schedule.pop(0)
                    sndf(*args)
                return task.cont
            # This loop should take place after sound play loops
            # and before 3D audio manager's loop.
            base.taskMgr.add(taskf, "sound-method-exec", sort=21)
    else:
        # NOTE: This is according to documented behavior.
        sndf(*args)


_track_sounds = False
_sound_track = {}
_sound_nextid = [0]
_sound_play2d = True
_sound_play3d = True

def _sound_load (path, sndmgr=None):

    if sndmgr:
        snd = sndmgr.loadSfx(full_path("data", path))
        is3d = True
    else:
        snd = base.load_sound("data", path)
        is3d = False
    if _track_sounds:
        ident = _sound_nextid[0]
        _sound_nextid[0] += 1
        sndprop = AutoProps(ident=ident, is3d=is3d, playing=False)
        _sound_track[snd] = sndprop
        _sound_report(event="load", sndprop=sndprop)
    return snd


def _sound_unload (snd):

    if _track_sounds:
        if snd not in _sound_track:
            return
        sndprop = _sound_track.pop(snd)
        _sound_report(event="unload", sndprop=sndprop)


def _sound_start (snd, starttime=0.0):

    if _track_sounds:
        if snd not in _sound_track:
            return
        sndprop = _sound_track[snd]
        if ((sndprop.is3d and not _sound_play3d) or
            (not sndprop.is3d and not _sound_play2d)):
            return
        sndprop.playing = True
        _sound_report(event="start", sndprop=sndprop)
    snd.setTime(starttime)
    _exec_sound_method(snd.play)
    #if base.gameconf.audio.sound_system in ("al",):
        ## NOTE: This is against documented behavior. A bug?
        #snd.setTime(starttime)
        #_exec_sound_method(snd.play)
    #else:
        ## NOTE: This is according to documented behavior.
        #_exec_sound_method(snd.setTime, [starttime])


def _sound_stop (snd):

    if _track_sounds:
        if snd not in _sound_track:
            return
        sndprop = _sound_track[snd]
        if ((sndprop.is3d and not _sound_play3d) or
            (not sndprop.is3d and not _sound_play2d)):
            return
        sndprop.playing = False
        _sound_report(event="stop", sndprop=sndprop)
    _exec_sound_method(snd.stop)


def _sound_report (event, sndprop):

    showit = False

    if _track_sounds and showit:
        nload, nplay, nsplay, nsready, nsbad = ([0, 0] for i in range(5))
        for snd, props in _sound_track.iteritems():
            i = int(props.is3d)
            nload[i] += 1
            if props.playing:
                nplay[i] += 1
            st = snd.status()
            if st == AudioSound.BAD:
                nsbad[i] += 1
            elif st == AudioSound.READY:
                nsready[i] += 1
            elif st == AudioSound.PLAYING:
                nsplay[i] += 1
        sp = sndprop
        dbgval(1, "sndtrk",
               (nload[0], "%d", "2D-loaded"),
               (nplay[0], "%d", "2D-playing"),
               ((nsplay[0], nsready[0], nsbad[0]), "%d", "2D-state-prb"),
               (nload[1], "%d", "3D-loaded"),
               (nplay[1], "%d", "3D-playing"),
               ((nsplay[1], nsready[1], nsbad[1]), "%d", "3D-state-prb"),
               (event, "%s", "event"),
               (sp.ident, "%d", "ident"),
               ((sp.is3d and "3d" or "2d"), "%s", "dim"))


class Sound3D (object):

    _id_cnt = [0l]

    _singleat_groups = {}
    _singleat_cframes = {}
    _singleat_cvols = {}
    _singleat_ptimes = {}

    _limnum_maxs = {}
    _limnum_groups = {}
    _limnum_cframes = {}
    _limnum_byords = {}

    def __init__ (self, path, parent, subnode=None,
                  mindist=None, maxdist=None, limnum=None, singleat=False,
                  volume=1.0, loop=False, fadetime=0.0,
                  play=False):

        self._id = self._id_cnt[0]
        self._id_cnt[0] += 1

        self._path = path
        self._parent = parent
        self._mindist = mindist
        self._maxdist = maxdist
        self._limnum = limnum
        self._singleat = singleat
        self._volume = volume
        self._fadetime = fadetime

        if subnode is not None:
            self._pnode = subnode
        else:
            self._pnode = parent.node

        if singleat:
            skey = (self._pnode, self._path)
            if skey not in self._singleat_groups:
                self._singleat_groups[skey] = []
                self._singleat_cframes[skey] = None
            self._singleat_group = self._singleat_groups[skey]
            self._singleat_group.append(self)

        if limnum is not None:
            if limnum not in self._limnum_groups:
                raise StandardError(
                    "Sound number limiting group '%s' not set." % limnum)
            self._limnum_group = self._limnum_groups[limnum]
            self._nearord = None

        if not singleat or self._singleat_group[0] is self:
            self._world = parent.world
            self._sndmgr = base.audio3d_manager
            self._sound = _sound_load(path, self._sndmgr)
            dist_scale = base.sound_distance_scale
            min_dist = self._mindist
            if min_dist is None:
                min_dist = (getattr(parent, "bboxdiag", 1.0) * 0.5) * 6.0 #2.0
            self._sound.set3dMinDistance(min_dist / dist_scale)
            max_dist = self._maxdist
            if max_dist is None:
                max_dist = 10000.0
            self._sound.set3dMaxDistance(max_dist / dist_scale)
            self._sound.setLoop(True)
            self._snode = None
        else:
            self._world = self._singleat_group[0]._world
            self._sndmgr = self._singleat_group[0]._sndmgr
            self._sound = self._singleat_group[0]._sound
            self._snode = self._singleat_group[0]._snode

        if loop is False:
            self._duration = self._sound.length()
        elif loop is True:
            self._duration = None
        elif isinstance(loop, (float, int)):
            self._duration = loop

        self._playing = False
        self._stopping = False
        self._paused = False
        self._current_volume = 0.0
        self._current_volume_mod = 0.0
        self._playtime = 0.0
        self._set_fading(fadetime)
        self._last_pos = self._pnode.getPos(self._world.node)

        self._init_frame = self._world.frame
        self._inloop = False

        if play:
            self.play()


    def _loop (self, task):

        if self._init_frame == self._world.frame:
            dt = 0.0
        else:
            dt = base.global_clock.getDt() # not world time

        if not self._world.alive:
            target_volume = 0.0
            self._stopping = True
            self._current_volume = 0.0
        elif self._snode is None:
            if self._pnode.isEmpty():
                self._stopping = True
                # Attach sound to a temporary node, to stop properly.
                if not self._singleat or self._singleat_group[0] is self:
                    #print "--sound-switch-to-snode", self._id, self._path, getattr(self._parent, "name", None), self._world.time, self._world.frame
                    self._snode = self._world.node.attachNewNode("sound-temp")
                    self._snode.setPos(self._last_pos)
                    self._sndmgr.attachSoundToObject(self._sound, self._snode)
                    if self._singleat:
                        for sound in self._singleat_group[1:]:
                            sound._snode = self._snode
            else:
                if self._first_inloop:
                    if not self._singleat or self._singleat_group[0] is self:
                        self._sndmgr.attachSoundToObject(self._sound, self._pnode)
                self._last_pos = self._pnode.getPos(self._world.node)
                if base.with_sound_doppler:
                    # Set sound velocity for Doppler effect.
                    if not self._singleat or self._singleat_group[0] is self:
                        if hasattr(self._parent, "vel"):
                            svel = self._parent.vel()
                        else:
                            svel = Vec3()
                        self._sndmgr.setSoundVelocity(self._sound, svel)
        else:
            self._stopping = True

        if (self._duration is not None and
            self._playtime > self._duration - self._fadetime):
            self._stopping = True

        if self._world.chaser and not self._stopping:
            ch = self._world.chaser
            target_volume = self._volume
            if self._maxdist is not None:
                dist = self._pnode.getDistance(ch.node)
                if dist > self._maxdist:
                    target_volume = 0.0
            if self._limnum is not None:
                byord = self._limnum_byords[self._limnum]
                nmax = self._limnum_maxs[self._limnum]
                if not byord:
                    cframe = self._limnum_cframes.get(self._limnum)
                    if cframe != self._world.frame:
                        self._limnum_cframes[self._limnum] = self._world.frame
                        sounds_by_dist = []
                        for sound in self._limnum_group:
                            onode = sound._parent.node
                            if onode.isEmpty():
                                onode = sound._snode
                            if onode is not None and not onode.isEmpty():
                                dist = ch.node.getDistance(onode)
                            else:
                                dist = 1e30
                            sounds_by_dist.append((dist, sound))
                        sounds_by_dist.sort()
                        for i, (dist, sound) in enumerate(sounds_by_dist):
                            sound._nearord = i
                    if self._nearord is None or self._nearord >= nmax:
                        target_volume = 0.0
                else:
                    if self._limnum_group.index(self) >= nmax:
                        target_volume = 0.0
                        self._stopping = True
                        self._current_volume = 0.0
        else:
            target_volume = 0.0

        if self._current_volume != target_volume:
            if self._fadespeed:
                absdvol = self._fadespeed * dt
                if self._current_volume < target_volume:
                    next_volume = self._current_volume + absdvol
                    if next_volume > target_volume:
                        next_volume = target_volume
                else:
                    next_volume = self._current_volume - absdvol
                    if next_volume < target_volume:
                        next_volume = target_volume
            else:
                next_volume = target_volume
        else:
            next_volume = self._current_volume

        if not self._singleat or self._singleat_group[0] is self:
            if self._singleat:
                skey = (self._pnode, self._path)
                if self._singleat_cframes.get(skey) != self._world.frame:
                    self._singleat_cframes[skey] = self._world.frame
                    cvol = max(s._current_volume for s in self._singleat_group)
                    ptime = max(s._playtime for s in self._singleat_group)
                    self._singleat_cvols[skey] = cvol
                    self._singleat_ptimes[skey] = ptime
                next_volume_mod = max(next_volume, self._singleat_cvols[skey])
                playtime_mod = max(self._playtime, self._singleat_ptimes[skey])
            else:
                next_volume_mod = next_volume
                playtime_mod = self._playtime

            #print "--sound-volume", self._id, self._path, getattr(self._parent, "name", None), next_volume_mod, playtime_mod, self._world.time, self._world.frame
            if self._current_volume_mod != next_volume_mod:
                self._current_volume_mod = next_volume_mod
                if next_volume_mod > 0.0:
                    self._sound.setVolume(next_volume_mod)
                    if not self._playing:
                        #print "--sound-starting", self._id, self._path, getattr(self._parent, "name", None), next_volume_mod, playtime_mod, self._world.time, self._world.frame
                        _sound_start(self._sound, playtime_mod)
                        self._playing = True
                else:
                    if self._playing:
                        #print "--sound-stopping", self._id, self._path, getattr(self._parent, "name", None), next_volume_mod, playtime_mod, self._world.time, self._world.frame
                        _sound_stop(self._sound)
                        self._playing = False
        else:
            self._playing = self._singleat_group[0]._playing
            self._snode = self._singleat_group[0]._snode
        self._current_volume = next_volume

        self._playtime += dt

        if next_volume == 0.0 and self._stopping:
            #print "--sound-end-loop", self._id, self._path, getattr(self._parent, "name", None), self._world.time, self._world.frame
            if self._singleat:
                self._singleat_group.remove(self)
                if not self._singleat_group:
                    self._singleat_groups.pop((self._pnode, self._path))
            if self._limnum is not None:
                self._limnum_group.remove(self)
            if not self._singleat or not self._singleat_group:
                if self._playing:
                    #print "--sound-stopping-outside", self._id, getattr(self._parent, "name", None), next_volume_mod, self._world.time, self._world.frame
                    _sound_stop(self._sound)
                self._sndmgr.detachSound(self._sound)
                if self._snode is not None:
                    self._snode.removeNode()
            self._stopping = False
            self._inloop = False
            return task.done

        self._first_inloop = False
        return task.cont


    def play (self, fadetime=None):

        self._set_fading(fadetime)
        if not self._paused:
            self._playtime = 0.0
        self._paused = False
        # The loop should run after world's post-loop,
        # and before 3D audio manager's update loop,
        # in order to detach sounds from removed bodies before
        # the audio manager triples on removed nodes.
        if not self._inloop:
            self._inloop = True
            self._first_inloop = True
            if self._limnum:
                self._limnum_group.append(self)
            base.taskMgr.add(self._loop, "sound3d-playloop", sort=20)
            #print "--sound-start-loop", self._id, self._path, getattr(self._parent, "name", None), self._world.time, self._world.frame


    def stop (self, fadetime=None):

        self._stopping = True
        self._paused = False
        self._set_fading(fadetime)


    def pause (self, fadetime=None):

        self._stopping = True
        self._paused = True
        self._set_fading(fadetime)


    def set_state (self, state, fadetime=None):
        """
        Set the sound state.

        Possible states: 0/False stopped, 1/True playing, 2 paused.

        If already in the given state, no effect.
        """

        if state in (0, False):
            if self._playing and not self._stopping:
                self.stop(fadetime=fadetime)
        elif state in (1, True):
            if not self._playing or self._stopping:
                self.play(fadetime=fadetime)
        elif state in (2,):
            if self._playing and not self._stopping:
                self.pause(fadetime=fadetime)
        else:
            raise StandardError(
                "Requested unknown sound state '%s'." % state)


    def set_volume (self, volume, fadetime=None):

        self._set_fading(fadetime, dvolume=(volume - self._volume))
        self._volume = volume


    def _set_fading (self, fadetime, dvolume=None):

        if dvolume is None:
            dvolume = self._volume
        if fadetime is not None:
            self._fadetime = fadetime
            if self._fadetime > 0.0:
                self._fadespeed = abs(dvolume) / self._fadetime
            else:
                self._fadespeed = None


    def length (self):

        return self._sound.length()


    def pnode (self):

        if not self._pnode.isEmpty() or self._snode is None:
            return self._pnode
        else:
            return self._snode


    if _track_sounds:
        def __del__ (self):

            if not self._singleat or not self._singleat_group:
                _sound_unload(self._sound)


    @staticmethod
    def set_limnum_group (name, nmax, byord=False):

        if name not in Sound3D._limnum_groups:
            Sound3D._limnum_groups[name] = []
            Sound3D._limnum_cframes[name] = None
        Sound3D._limnum_maxs[name] = nmax
        Sound3D._limnum_byords[name] = byord


class Sound2D (object):

    def __init__ (self, path, pnode=None, world=None,
                  volume=1.0, loop=False, fadetime=0.0,
                  play=False):

        self._path = path
        self._pnode = pnode
        self._world = world
        self._volume = volume
        self._fadetime = fadetime

        self._sound = _sound_load(path)
        self._sound.setLoop(True)

        if loop is False:
            self._duration = self._sound.length()
        elif loop is True:
            self._duration = None
        elif isinstance(loop, (float, int)):
            self._duration = loop

        self._playing = False
        self._stopping = False
        self._paused = False
        self._current_volume = 0.0
        self._playtime = 0.0
        self._set_fading(fadetime)

        self._inloop = False
        if play:
            self.play()


    def _loop (self, task):

        if ((self._pnode is not None and self._pnode.isEmpty()) or
            (self._world is not None and not self._world.alive) or
            (self._duration is not None and
             self._playtime > self._duration - self._fadetime)):
            self._stopping = True

        if (self._pnode is not None and self._pnode.isHidden()) or self._stopping:
            target_volume = 0.0
        else:
            target_volume = self._volume

        if self._world is not None:
            if self._world.alive:
                dt = base.global_clock.getDt() # not world time
            else:
                dt = 0.0
                self._stopping = True
                target_volume = 0.0
                self._fadespeed = None
        else:
            dt = base.global_clock.getDt()

        if self._current_volume != target_volume:
            if self._fadespeed:
                absdvol = self._fadespeed * dt
                if self._current_volume < target_volume:
                    next_volume = self._current_volume + absdvol
                    if next_volume > target_volume:
                        next_volume = target_volume
                else:
                    next_volume = self._current_volume - absdvol
                    if next_volume < target_volume:
                        next_volume = target_volume
            else:
                next_volume = target_volume
        else:
            next_volume = self._current_volume

        if self._current_volume != next_volume:
            self._current_volume = next_volume
            if next_volume > 0.0:
                self._sound.setVolume(next_volume)
                if not self._playing:
                    _sound_start(self._sound, self._playtime)
                    self._playing = True
            else:
                if self._playing:
                    _sound_stop(self._sound)
                    self._playing = False

        self._playtime += dt

        if next_volume == 0.0 and self._stopping:
            self._stopping = False
            self._inloop = False
            return task.done

        return task.cont


    def play (self, fadetime=None):

        self._set_fading(fadetime)
        if not self._paused:
            self._playtime = 0.0
        self._stopping = False
        self._paused = False
        if not self._inloop:
            self._inloop = True
            base.taskMgr.add(self._loop, "sound2d-playloop", sort=20)


    def stop (self, fadetime=None):

        self._set_fading(fadetime)
        self._stopping = True
        self._paused = False


    def pause (self, fadetime=None):

        self._stopping = True
        self._paused = True
        self._set_fading(fadetime)


    def set_state (self, state, fadetime=None):
        """
        Set the sound state.

        Possible states: 0/False stopped, 1/True playing, 2 paused.

        If already in the given state, no effect.
        """

        if state in (0, False):
            if self._playing and not self._stopping:
                self.stop(fadetime=fadetime)
        elif state in (1, True):
            if not self._playing or self._stopping:
                self.play(fadetime=fadetime)
        elif state in (2,):
            if self._playing and not self._stopping:
                self.pause(fadetime=fadetime)
        else:
            raise StandardError(
                "Requested unknown sound state '%s'." % state)


    def set_volume (self, volume, fadetime=None):

        self._set_fading(fadetime, dvolume=(volume - self._volume))
        self._volume = volume


    def _set_fading (self, fadetime, dvolume=None):

        if dvolume is None:
            dvolume = self._volume
        if fadetime is not None:
            self._fadetime = fadetime
            if self._fadetime > 0.0:
                self._fadespeed = abs(dvolume) / self._fadetime
            else:
                self._fadespeed = None


    def length (self):

        return self._sound.length()


    if _track_sounds:
        def __del__ (self):

            _sound_unload(self._sound)


class ActionMusic (object):

    def __init__ (self, world, volume=1.0,
                  cruisingpath=None, cruisingvolume=None,
                  attackedpath=None, attackedvolume=None,
                  shotdownpath=None, shotdownvolume=None,
                  victorypath=None, victoryvolume=None,
                  failurepath=None, failurevolume=None,
                  bosspath=None, bossvolume=None,
                  permattack=False, parent=None):

        self._world = world
        self._parent = parent
        self._always_attacked = permattack

        if cruisingvolume is None:
            cruisingvolume = volume
        if attackedvolume is None:
            attackedvolume = volume
        if shotdownvolume is None:
            shotdownvolume = volume
        if victoryvolume is None:
            victoryvolume = volume
        if failurevolume is None:
            failurevolume = volume

        self._musics = {}
        self._music_volumes = {}
        for context, muspath, vol, loop in (
            ("silence", None, 0.0, False),
            ("cruising", cruisingpath, cruisingvolume, True),
            ("attacked", attackedpath, attackedvolume, True),
            ("shotdown", shotdownpath, shotdownvolume, True),
            ("victory", victorypath, victoryvolume, False),
            ("failure", failurepath, failurevolume, False),
            ("boss", bosspath, bossvolume, True),
        ):
            if muspath is not None:
                mus = Sound2D(path=muspath,
                              world=self._world, pnode=self._world.node2d,
                              volume=vol, loop=loop)
            else:
                mus = None
            self._musics[context] = mus
            self._music_volumes[context] = vol

        self._switchspec = {
            ("silence", "cruising"):
                AutoProps(wait=0.0, fade2=2.0),
            ("silence", "attacked"):
                AutoProps(wait=0.0, fade2=0.0),
            ("silence", "shotdown"):
                AutoProps(wait=0.0, fade2=0.0),
            ("silence", "victory"):
                AutoProps(wait=0.0, fade2=0.0),
            ("silence", "failure"):
                AutoProps(wait=0.0, fade2=0.0),
            ("silence", "boss"):
                AutoProps(wait=0.0, fade2=0.0),
            ("silence", "shotdown"):
                AutoProps(wait=0.0, fade2=0.0),
            ("cruising", "silence"):
                AutoProps(wait=0.0, fade1=1.0, pause1=True),
            ("attacked", "silence"):
                AutoProps(wait=0.0, fade1=1.0),
            ("boss", "silence"):
                AutoProps(wait=0.0, fade1=1.0),
            ("victory", "silence"):
                AutoProps(wait=0.0, fade1=1.0),
            ("failure", "silence"):
                AutoProps(wait=0.0, fade1=1.0),
            ("boss", "silence"):
                AutoProps(wait=0.0, fade1=1.0),
            ("cruising", "attacked"):
                AutoProps(wait=3.0, fade1=0.0, fade2=0.0, pause1=True),
            ("attacked", "cruising"):
                AutoProps(wait=3.0, fade1=2.0, fade2=0.0, pause1=False),
            ("cruising", "boss"):
                AutoProps(wait=3.0, fade1=0.0, fade2=0.0, pause1=True),
            ("boss", "cruising"):
                AutoProps(wait=3.0, fade1=2.0, fade2=0.0, pause1=False),
            ("cruising", "shotdown"):
                AutoProps(wait=0.0, fade1=0.0, fade2=0.0, pause1=False),
            ("attacked", "shotdown"):
                AutoProps(wait=0.0, fade1=0.0, fade2=0.0, pause1=False),
            ("boss", "shotdown"):
                AutoProps(wait=0.0, fade1=0.0, fade2=0.0, pause1=False),
            ("victory", "shotdown"):
                AutoProps(wait=0.0, fade1=0.0, fade2=0.0, pause1=False),
            ("failure", "shotdown"):
                AutoProps(wait=0.0, fade1=0.0, fade2=0.0, pause1=False),
            ("cruising", "victory"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("attacked", "victory"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("boss", "victory"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("victory", "cruising"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("victory", "attacked"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("victory", "boss"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("cruising", "failure"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("attacked", "failure"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("boss", "failure"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=True, revctx=True),
            ("failure", "cruising"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("failure", "attacked"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("failure", "boss"):
                AutoProps(wait=0.0, fade1=0.1, fade2=0.0, pause1=False),
            ("boss", "attacked"):
                AutoProps(wait=0.0, fade1=0.5, fade2=0.5, pause1=False),
            ("attacked", "boss"):
                AutoProps(wait=0.0, fade1=0.5, fade2=0.5, pause1=False),
        }

        self._attacked_families = (
            "plane",
        )
        self._attacking_families = (
            "plane",
            "rocket",
        )

        self._current_context = "silence"
        self._pending_context = "silence"
        self._pending_switch = None
        self._force_context = None

        self._paused = False
        self._wait_test = 0.0
        self._test_period = 0.47
        self._wait_delay_switch = None
        self._wait_delay_switch2 = None

        self._wait_revert_context = None
        self._revert_force_context = None

        self._current_music = None

        self._wait_silence = 0.0

        self.alive = True
        base.taskMgr.add(self._loop, "action-music-loop")


    def destroy (self):

        if not self.alive:
            return
        self.alive = False


    def _loop (self, task):

        if task.time == 0.0:
            return task.cont

        if not self.alive:
            return task.done
        if not self._world.alive:
            self.destroy()
            return task.done

        dt = self._world.dt

        if self._wait_revert_context is not None:
            self._wait_revert_context -= dt
            if self._wait_revert_context <= 0.0:
                self._wait_revert_context = None
                self._force_context = self._revert_force_context
                self._wait_test = 0.0 # prevent starting second loop

        self._wait_test -= dt
        if self._wait_test <= 0.0:
            self._wait_test = self._test_period

            self._pending_context = self._get_context()
            if (self._current_context != self._pending_context and
                self._wait_delay_switch is None and
                self._wait_delay_switch2 is None):
                switch = (self._current_context, self._pending_context)
                self._current_context = self._pending_context
                if switch != self._pending_switch:
                    self._pending_switch = switch
                    swp = self._switchspec.get(switch)
                    if swp is not None:
                        #print "--action-music-switch-delay", switch, swp.wait
                        self._wait_delay_switch = swp.wait or 0.0

        if self._wait_delay_switch is not None:
            self._wait_delay_switch -= dt
            if self._wait_delay_switch <= 0.0:
                #print "--action-music-switch-do1", self._pending_switch
                self._wait_delay_switch = None
                ctx1 = self._pending_switch[0]
                swp = self._switchspec.get(self._pending_switch)
                mus1 = self._musics[ctx1]
                fade1 = swp.fade1 or 0.0
                if mus1 is not None:
                    if swp.pause1:
                        mus1.pause(fadetime=fade1)
                    else:
                        mus1.stop(fadetime=fade1)
                    self._current_music = None
                self._wait_delay_switch2 = fade1

        if self._wait_delay_switch2 is not None:
            self._wait_delay_switch2 -= dt
            if self._wait_delay_switch2 <= 0.0:
                #print "--action-music-switch-do2", self._pending_switch
                self._wait_delay_switch2 = None
                ctx2 = self._pending_switch[1]
                swp = self._switchspec.get(self._pending_switch)
                mus2 = self._musics[ctx2]
                if mus2 is not None:
                    mus2.play(fadetime=(swp.fade2 or 0.0))
                    if swp.revctx:
                        self._wait_revert_context = mus2.length()
                        self._wait_revert_context -= 0.5 # due to buggy length
                        self._revert_force_context = self._pending_switch[0]
                    self._current_music = mus2
                else:
                    self._current_music = None

        if self._wait_silence > 0.0:
            self._wait_silence -= dt
            if self._wait_silence <= 0.0:
                for ctx, mus in self._musics.items():
                    if mus is not None:
                        mus.set_volume(volume=self._music_volumes[ctx],
                                       fadetime=self._silence_fadetime)

        return task.cont


    def _get_context (self):

        player_shotdown = (self._world.player and
                           (self._world.player.ac.controlout or
                            self._world.player.ac.shotdown))
        if player_shotdown:
            return "shotdown"

        if self._paused:
            return "silence"

        if self._force_context is not None:
            return self._force_context

        parent = (self._parent or
                  (self._world.player and self._world.player.alive and
                   self._world.player.ac))
        if parent:
            if not self._always_attacked:
                # Select all bodies friendly to parent (including parent).
                friendlies = self._world.get_friendlies(self._attacked_families,
                                                        parent.side)
                # Check if any friendly under attack.
                for body in parent.world.iter_bodies(self._attacking_families):
                    if body not in friendlies and body.target in friendlies:
                        if body.family == "rocket":
                            visdist = 20000.0
                            if getattr(body.target, "radarrange", None):
                                raddist = body.target.radarrange * 0.5
                                outdist = max(raddist, visdist)
                            else:
                                outdist = visdist
                            if body.dist(body.target) < outdist:
                                return "attacked"
                        else:
                            return "attacked"
            else:
                return "attacked"

        return "cruising"


    def pause (self):

        self._paused = True
        self._wait_test = 0.0


    def play (self):

        self._paused = False
        self._wait_test = 0.0


    def silence (self, duration, volume=0.0, fadetime=None):

        self._silence_fadetime = fadetime or 0.01
        self._wait_silence = duration - self._silence_fadetime
        for mus in self._musics.values():
            if mus is not None:
                mus.set_volume(volume=volume,
                               fadetime=self._silence_fadetime)


    def set_context (self, context=None):

        if context is not None:
            if context not in self._musics:
                raise StandardError(
                    "Trying to set unknown context '%s'." % context)
            self._force_context = context
        else:
            self._force_context = None


    def set_volume (self, volume, fadetime=1.0):

        if self._current_music is not None:
            fadetime = fadetime or 0.01
            self._current_music.set_volume(volume=volume, fadetime=fadetime)


