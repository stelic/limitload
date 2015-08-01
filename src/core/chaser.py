# -*- coding: UTF-8 -*-

from math import radians, degrees, asin

from pandac.PandaModules import Vec3, Point3, Quat
from pandac.PandaModules import Vec3D, Point3D, QuatD
from pandac.PandaModules import NodePath, TransparencyAttrib

from src import ANIMATION_FOV
from src.core.body import Body
from src.core.misc import sign, unitv, set_hpr_vfu, print_each, hprtovec, clamp
from src.core.misc import vtof, vtod, ptof, ptod
from src.core.misc import update_bounded, rotation_forward_up
from src.core.misc import SimpleProps, randvec, randswivel, as_sequence
from src.core.misc import uniform
from src.core.plane import Plane
from src.core.world import World


#_Vx, _Px, _Qx, _vtox, _ptox = Vec3, Point3, Quat, vtof, ptof
_Vx, _Px, _Qx, _vtox, _ptox = Vec3D, Point3D, QuatD, vtod, ptod


class Drift (object):

    def __init__ (self, world, parent, spec,
                  pos, vel, acc, at_dir, up_dir, ang_vel, ang_acc):
        """
        Parameters:
        - world (World): The world.
        - parent (Chaser): The chaser to which this drift is associated.
        - spec ((string, ...) or string): Drift movement specification,
            a tuple containing the drift mode name followed by any parameters
            needed by that drift mode. If no parameters are needed by
            the given drift mode, it can be given as name string alone.
            Available modes are:
            - ("instlag", trs_lagtime, ang_lagtime): At every moment,
                the translational/angular speed is chosen such as to reach
                the reference point/direction in given translational/angular
                lag time if the speed would remain constant.
            - ("instlag-right", trs_lagtime, ang_lagtime): Like "instlag",
                but lag axis is always the right-vector.
        - *args: Initial kinematics.
        """

        self.world = world
        self.parent = parent

        if isinstance(spec, basestring) and spec in Drift._mode_alias:
            spec = Drift._mode_alias[spec]

        if isinstance(spec, basestring):
            name = spec
            param = []
        elif spec:
            name = spec[0]
            param = spec[1:]
        else:
            name = None
            param = []

        if name is None:
            init_f = self._init_none
            reset_f = self._reset_none
            update_f = self._update_none
        elif name == "instlag":
            init_f = self._init_instlag
            reset_f = self._reset_instlag
            update_f = self._update_instlag
        elif name == "instlag-right":
            init_f = self._init_instlag
            reset_f = self._reset_instlag
            update_f = self._update_instlag_right
        else:
            raise StandardError("Unknown drift type '%s'." % name)

        init_f(param,
               pos, vel, acc,
               at_dir, up_dir, ang_vel, ang_acc)
        self.reset = reset_f
        self.update = update_f


    _mode_alias = {}

    @staticmethod
    def set_alias (name, spec):

        Drift._mode_alias[name] = spec


    def _init_none (self, param, *args, **kwargs):

        assert len(param) == 0


    def _reset_none (self,
                     pos_1, vel_1, acc_1,
                     at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        pass


    def _update_none (self, dt,
                      pos_1, vel_1, acc_1,
                      at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        return pos_1, at_dir_1, up_dir_1


    def _init_instlag (self, param,
                       pos, vel, acc,
                       at_dir, up_dir, ang_vel, ang_acc):

        lag, ang_lag = param

        self._lag = lag
        self._pos = pos

        self._ang_lag = ang_lag
        self._at_dir, self._up_dir = at_dir, up_dir


    def _reset_instlag (self,
                        pos, vel, acc,
                        at_dir, up_dir, ang_vel, ang_acc):

        self._pos = pos
        self._at_dir, self._up_dir = at_dir, up_dir


    def _update_instlag (self, dt,
                         pos_1, vel_1, acc_1,
                         at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        if self._lag > 0.0:
            drift_off = pos_1 - self._pos
            drift_vel_1 = drift_off / max(self._lag, dt)
            self._pos += drift_vel_1 * dt
        else:
            self._pos = pos_1

        if self._ang_lag > 0.0:
            ret = rotation_forward_up(self._at_dir, self._up_dir, at_dir_1, up_dir_1)
            drift_rot_ang, drift_rot_axis = ret
            drift_ang_vel_1 = drift_rot_ang / max(self._ang_lag, dt)
            drift_rot_ang_1 = drift_ang_vel_1 * dt
            drift_rot_1 = _Qx()
            drift_rot_1.setFromAxisAngleRad(drift_rot_ang_1, drift_rot_axis)
            self._at_dir = unitv(_Vx(drift_rot_1.xform(self._at_dir)))
            self._up_dir = unitv(_Vx(drift_rot_1.xform(self._up_dir)))
        else:
            self._at_dir = at_dir_1
            self._up_dir = up_dir_1

        return self._pos, self._at_dir, self._up_dir


    def _update_instlag_right (self, dt,
                               pos_1, vel_1, acc_1,
                               at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        if self._lag > 0.0:
            drift_off = (pos_1 - self._pos).dot(up_dir_1)
            drift_vel_1 = drift_off / max(self._lag, dt)
            self._pos += up_dir_1 * (drift_vel_1 * dt)
        else:
            self._pos = pos_1

        if self._ang_lag > 0.0:
            rt_dir_1 = unitv(at_dir_1.cross(up_dir_1))
            drift_rot_ang = self._at_dir.signedAngleRad(at_dir_1, rt_dir_1)
            drift_ang_vel_1 = drift_rot_ang / max(self._ang_lag, dt)
            drift_rot_ang_1 = drift_ang_vel_1 * dt
            drift_rot_1 = _Qx()
            drift_rot_1.setFromAxisAngleRad(drift_rot_ang_1, rt_dir_1)
            self._at_dir = unitv(_Vx(drift_rot_1.xform(self._at_dir)))
            self._up_dir = unitv(rt_dir_1.cross(self._at_dir))
        else:
            self._at_dir = at_dir_1
            self._up_dir = up_dir_1

        return self._pos, self._at_dir, self._up_dir


class Shake (object):

    def __init__ (self, world, parent, spec,
                  pos, vel, acc, at_dir, up_dir, ang_vel, ang_acc):
        """
        Parameters:
        - world (World): The world.
        - parent (Chaser): The chaser to which this shake is associated.
        - shake ((string, ...) or string): Shake movement specification,
            a tuple containing the shake mode name followed by any parameters
            needed by that shake mode. If no parameters are needed by
            the given shake mode, it can be given as name string alone.
            Available modes are:
            - ("pert", trs_period, trs_amp, ang_period, ang_amp):
                General translational/angular perturbations, occuring
                at given translational/angular periods, and of at most
                given translational/angular amplitude.
            - ("vertpert", trs_period, trs_amp, ang_period, ang_amp, off_vert):
                Like "pert", but perturbations are limited in direction
                to at most given angle off the vertical.
            - ("speed-pert", trs_period, trs_amp, ang_period, ang_amp,
               lim_speed, max_strength,
               exp_period, exp_amp, exp_ang_period, exp_ang_amp,
               max_period, max_ang_period):
                Like "pert", but perturbations depend on chaser speed.
                This dependency is expressed through strength, which
                scales linearly with speed up to given limit speed, at which
                it is given maximum strength and does not increase any more.
                Periods and amplitudes are multiplied with strength
                raised to given corresponding exponents.
                Periods are limited to given maximum values.
            - ("speed-vertpert", trs_period, trs_amp, ang_period, ang_amp,
               off_vert, lim_speed, max_strength,
               exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
               max_period, max_ang_period):
                Like "vertpert", but perturbations depend on chaser speed,
                in the same way as in "speed-pert".
            - ("air", strength): Instance of "pert" with parameters chosen
                to be suitable for chasers mounted on virtual aircraft.
                Parameters can be multiplied with single strength value,
                raised to an internally defined exponent for each parameter.
            - ("ground", strength): Like "air", but for vehicles.
            - ("sea", strength): Like "air", but for ships.
            - ("speed-air", lim_speed, max_strength): Instance of "speed-pert"
                with parameters chosen to be suitable for chasers mounted
                on virtual aircraft. Unlike in "air" where parameters
                can be multiplied with single fixed strength,
                here strength can vary with speed as in "speedpert".
                Only limit speed and maximum strength are selectable,
                while strength exponents are internally defined.
            - ("speed-ground", lim_speed, max_strength): Like "speed-air",
                but for chasers mounted on ground vehicles.
            - ("speed-sea", lim_speed, max_strength): Like "speed-air",
                but for chasers mount on sea vehicles.
        - *args: Initial kinematics.
        """

        self.world = world
        self.parent = parent

        if isinstance(spec, basestring) and spec in Shake._mode_alias:
            spec = Shake._mode_alias[spec]

        if isinstance(spec, basestring):
            name = spec
            param = []
        elif spec:
            name = spec[0]
            param = spec[1:]
        else:
            name = None
            param = []

        if name is None:
            init_f = self._init_none
            reset_f = self._reset_none
            update_f = self._update_none
        elif name == "pert":
            init_f = self._init_pert
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "vertpert":
            init_f = self._init_vertpert
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "speed-pert":
            init_f = self._init_speed_pert
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "speed-vertpert":
            init_f = self._init_speed_vertpert
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "air":
            init_f = self._init_air
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "ground":
            init_f = self._init_ground
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "sea":
            init_f = self._init_sea
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "speed-air":
            init_f = self._init_speed_air
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "speed-ground":
            init_f = self._init_speed_ground
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "speed-sea":
            init_f = self._init_speed_sea
            reset_f = self._reset_all_pert
            update_f = self._update_all_pert
        elif name == "distwake":
            init_f = self._init_distwake
            reset_f = self._reset_distwake
            update_f = self._update_distwake
        elif name == "dynac-distwake":
            init_f = self._init_dynac_distwake
            reset_f = self._reset_distwake
            update_f = self._update_dynac_distwake
        else:
            raise StandardError("Unknown shake type '%s'." % name)

        init_f(param,
               pos, vel, acc,
               at_dir, up_dir, ang_vel, ang_acc)
        self.reset = reset_f
        self.update = update_f


    _mode_alias = {}

    @staticmethod
    def set_alias (name, spec):

        Shake._mode_alias[name] = spec


    def _init_none (self, param, *args, **kwargs):

        assert len(param) == 0


    def _reset_none (self,
                     pos_1, vel_1, acc_1,
                     at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        pass


    def _update_none (self, dt,
                      pos_1, vel_1, acc_1,
                      at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        return pos_1, at_dir_1, up_dir_1


    def _init_all_pert (self, param,
                        pos, vel, acc,
                        at_dir, up_dir, ang_vel, ang_acc):

        (self._period, self._ref_off,
         self._ang_period, self._ang_ref_off,
         self._off_vert,
         self._lim_speed, self._max_strength,
         self._exp_period, self._exp_amp,
         self._exp_ang_period, self._exp_ang_amp,
         self._exp_off_vert,
         self._max_period, self._max_ang_period,
        ) = param

        self._off, self._vel, self._imp_acc = Vec3(), Vec3(), Vec3()
        self._time_since_update = 0.0

        self._ang_off, self._ang_vel, self._imp_ang_acc = _Vx(), _Vx(), _Vx()
        self._ang_time_since_update = 0.0


    def _reset_all_pert (self,
                         pos, vel, acc,
                         at_dir, up_dir, ang_vel, ang_acc):

        self._off, self._vel, self._imp_acc = Vec3(), Vec3(), Vec3()
        self._time_since_update = 0.0

        self._ang_off, self._ang_vel, self._imp_ang_acc = _Vx(), _Vx(), _Vx()
        self._ang_time_since_update = 0.0


    def _update_all_pert (self, dt,
                          pos_1, vel_1, acc_1,
                          at_dir_1, up_dir_1, ang_vel_1, ang_acc_1,
                          strength=None):

        if strength is None and self._lim_speed is not None:
            speed_1 = vel_1.length()
            strength = clamp(speed_1 / self._lim_speed, 1e-6, 1.0) * self._max_strength

        if strength is not None:
            strength = max(strength, 1e-6)
            period = min(self._period * strength**self._exp_period, self._max_period)
            ref_off = self._ref_off * strength**self._exp_amp
            ang_period = min(self._ang_period * strength**self._exp_ang_period, self._max_ang_period)
            ang_ref_off = self._ang_ref_off * strength**self._exp_ang_amp
            if self._off_vert is not None:
                off_vert = self._off_vert * strength**self._exp_off_vert
            else:
                off_vert = None
        else:
            period = self._period
            ref_off = self._ref_off
            ang_period = self._ang_period
            ang_ref_off = self._ang_ref_off
            off_vert = self._off_vert

        if self._period > 0.0:
            shake_off = self._off
            shake_vel = self._vel
            self._time_since_update += dt
            if self._time_since_update > period:
                num_periods = int(self._time_since_update / period)
                self._time_since_update -= num_periods * period
                imp_ref_off = ref_off * uniform(0.0, 1.0)
                if self._off_vert is not None:
                    imp_acc_dir = randswivel(vtof(up_dir_1), 0.0, off_vert)
                else:
                    imp_acc_dir = randvec()
                imp_acc_len = imp_ref_off / (period**2 / 3)
                self._imp_acc = imp_acc_dir * imp_acc_len
            shake_acc_imp_1 = self._imp_acc * (1.0 - self._time_since_update / period)
            shake_acc_att_1 = -((self._off + shake_vel * period) / (0.5 * period**2))
            shake_acc_1 = shake_acc_att_1 + shake_acc_imp_1
            shake_vel_1 = shake_vel + shake_acc_1 * dt
            shake_off_1 = self._off + shake_vel_1 * dt
            shake_pos = pos_1 + shake_off_1
            self._off = shake_off_1
            self._vel = shake_vel_1
        else:
            shake_pos = pos_1

        if self._ang_period > 0.0:
            rt_dir_1 = unitv(at_dir_1.cross(up_dir_1))
            self._ang_time_since_update += dt
            if self._ang_time_since_update > ang_period:
                num_ang_periods = int(self._ang_time_since_update / ang_period)
                self._ang_time_since_update -= num_ang_periods * ang_period
                imp_ang_ref_off = ang_ref_off * uniform(0.0, 1.0)
                if self._off_vert is not None:
                    imp_ang_acc_dir = randswivel(_Vx(0, 0, 1), 0.0, off_vert)
                else:
                    imp_ang_acc_dir = _vtox(randvec())
                imp_ang_acc_len = imp_ang_ref_off / (ang_period**2 / 3)
                self._imp_ang_acc = imp_ang_acc_dir * imp_ang_acc_len
            shake_ang_acc_imp_1 = self._imp_ang_acc * (1.0 - self._ang_time_since_update / ang_period)
            shake_ang_acc_att_1 = -((self._ang_off + self._ang_vel * ang_period) / (0.5 * ang_period**2))
            shake_ang_acc_1 = shake_ang_acc_att_1 + shake_ang_acc_imp_1
            shake_ang_vel_1 = self._ang_vel + shake_ang_acc_1 * dt
            shake_ang_off_1 = self._ang_off + shake_ang_vel_1 * dt
            #if self.parent.name == "outro":
                #print "--shake24", self._ang_vel, shake_ang_acc_1, shake_ang_vel_1
            shake_rot_at_1 = _Qx()
            shake_rot_at_1.setFromAxisAngleRad(shake_ang_off_1[0], at_dir_1)
            shake_rot_up_1 = _Qx()
            shake_rot_up_1.setFromAxisAngleRad(shake_ang_off_1[1], up_dir_1)
            shake_rot_rt_1 = _Qx()
            shake_rot_rt_1.setFromAxisAngleRad(shake_ang_off_1[2], rt_dir_1)
            shake_rot_1 = shake_rot_at_1 * shake_rot_up_1 * shake_rot_rt_1
            shake_at_dir = unitv(_Vx(shake_rot_1.xform(at_dir_1)))
            shake_up_dir = unitv(_Vx(shake_rot_1.xform(up_dir_1)))
            self._ang_off = shake_ang_off_1
            self._ang_vel = shake_ang_vel_1
        else:
            shake_at_dir = at_dir_1
            shake_up_dir = up_dir_1

        return shake_pos, shake_at_dir, shake_up_dir


    def _init_pert (self, param, *args, **kwargs):

        period, amp, ang_period, ang_amp = param
        off_vert = None
        lim_speed, max_strength = [None] * 2
        exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert = [None] * 5
        max_period, max_ang_period = [None] * 2
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_vertpert (self, param, *args, **kwargs):

        period, amp, ang_period, ang_amp, off_vert = param
        lim_speed, max_strength = [None] * 2
        exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert = [None] * 5
        max_period, max_ang_period = [None] * 2
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_speed_pert (self, param, *args, **kwargs):

        (period, amp, ang_period, ang_amp,
         lim_speed, max_strength,
         exp_period, exp_amp, exp_ang_period, exp_ang_amp,
         max_period, max_ang_period) = param
        off_vert = None
        exp_off_vert = None
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_speed_vertpert (self, param, *args, **kwargs):

        (period, amp, ang_period, ang_amp, off_vert,
         lim_speed, max_strength,
         exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
         max_period, max_ang_period) = param
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_air (self, param, *args, **kwargs):

        strength, = param
        period = 0.2 * strength**-0.5
        amp = 0.2 * strength
        ang_period = 0.2 * strength**-0.5
        ang_amp = radians(0.5) * strength
        off_vert = None
        max_period = 0.4
        max_ang_period = 0.4
        lim_speed, max_strength = [None] * 2
        exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert = [None] * 5
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_ground (self, param, *args, **kwargs):

        strength, = param
        period = 0.2 * strength**-0.5
        amp = 0.2 * strength
        ang_period = 0.2 * strength**-0.5
        ang_amp = radians(0.5) * strength
        off_vert = radians(5.0) * strength**0.5
        max_period = 0.4
        max_ang_period = 0.4
        lim_speed, max_strength = [None] * 2
        exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert = [None] * 5
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_sea (self, param, *args, **kwargs):

        strength, = param
        period = 1.0 * strength**-0.5
        amp = 1.0 * strength
        ang_period = 1.0 * strength**-0.5
        ang_amp = radians(1.0) * strength
        off_vert = radians(5.0) * strength**0.5
        max_period = 2.0
        max_ang_period = 2.0
        lim_speed, max_strength = [None] * 2
        exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert = [None] * 5
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_speed_air (self, param, *args, **kwargs):

        lim_speed, max_strength = param

        period = 0.2
        amp = 0.2
        ang_period = 0.2
        ang_amp = radians(0.5)
        off_vert = None
        exp_period = -0.5
        exp_amp = 1
        exp_ang_period = -0.5
        exp_ang_amp = 1
        exp_off_vert = None
        max_period = 0.4
        max_ang_period = 0.4
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_speed_ground (self, param, *args, **kwargs):

        lim_speed, max_strength = param

        period = 0.2
        amp = 0.2
        ang_period = 0.2
        ang_amp = radians(0.5)
        off_vert = radians(5.0)
        exp_period = -0.5
        exp_amp = 1
        exp_ang_period = -0.5
        exp_ang_amp = 1
        exp_off_vert = 0.5
        max_period = 0.4
        max_ang_period = 0.4
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_speed_sea (self, param, *args, **kwargs):

        lim_speed, max_strength = param

        period = 1.0
        amp = 1.0
        ang_period = 1.0
        ang_amp = radians(1.0)
        off_vert = radians(5.0)
        exp_period = -0.5
        exp_amp = 1
        exp_ang_period = -0.5
        exp_ang_amp = 1
        exp_off_vert = 0.5
        max_period = 2.0
        max_ang_period = 2.0
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            *args, **kwargs)


    def _init_distwake (self, param,
                        pos, vel, acc,
                        at_dir, up_dir, ang_vel, ang_acc):

        (self._wake_body,
         self._max_dist, self._att_exp,
         period, amp, ang_period, ang_amp,
         exp_period, exp_amp, exp_ang_period, exp_ang_amp,
         max_period, max_ang_period,
        ) = param

        off_vert, exp_off_vert = [None] * 2
        lim_speed, max_strength = [None] * 2
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            pos, vel, acc,
            at_dir, up_dir, ang_vel, ang_acc)


    def _reset_distwake (self,
                         pos, vel, acc,
                         at_dir, up_dir, ang_vel, ang_acc):

        return self._reset_all_pert(pos, vel, acc,
                                    at_dir, up_dir, ang_vel, ang_acc)


    def _update_distwake (self, dt,
                          pos_1, vel_1, acc_1,
                          at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        strength = 0.0
        wpos = self.parent.pos(self._wake_body)
        wdist = wpos.length()
        if wpos[1] < 0.0 and wdist < self._max_dist:
            strength = 1.0 - (wdist / self._max_dist)**self._att_exp
        return self._update_all_pert(dt,
                                     pos_1, vel_1, acc_1,
                                     at_dir_1, up_dir_1, ang_vel_1, ang_acc_1,
                                     strength=strength)


    def _init_dynac_distwake (self, param,
                              pos, vel, acc,
                              at_dir, up_dir, ang_vel, ang_acc):

        self._wake_body, = param

        if isinstance(self._wake_body, basestring):
            if self._wake_body == "atref":
                self._wake_body = self.parent.observed_body()
            else:
                raise StandardError(
                    "Unknown wake body indirection '%s'." % self._wake_body)
        if not isinstance(self._wake_body, Body):
            raise StandardError(
                "Given wake body not a body.")

        base_time = 3.0
        base_span = 10.0
        wake_body_span = self._wake_body.bbox[1]
        span_fac = wake_body_span / base_span
        self._max_dist_time = base_time * span_fac**0.25
        self._att_exp = 1.0

        period = 0.10
        amp =  0.50 * span_fac**0.5
        ang_period = 0.10
        ang_amp = radians(3.0) * span_fac**0.5
        exp_period = -0.5
        exp_amp = 1
        exp_ang_period = -0.5
        exp_ang_amp = 1
        max_period = 0.50
        max_ang_period = 0.50
        off_vert, exp_off_vert = [None] * 2
        lim_speed, max_strength = [None] * 2
        return self._init_all_pert(
            (period, amp, ang_period, ang_amp, off_vert,
             lim_speed, max_strength,
             exp_period, exp_amp, exp_ang_period, exp_ang_amp, exp_off_vert,
             max_period, max_ang_period),
            pos, vel, acc,
            at_dir, up_dir, ang_vel, ang_acc)


    def _update_dynac_distwake (self, dt,
                                pos_1, vel_1, acc_1,
                                at_dir_1, up_dir_1, ang_vel_1, ang_acc_1):

        strength = 0.0
        if self._wake_body.alive:
            wpos = self.parent.pos(self._wake_body)
            if wpos[1] < 0.0:
                wdist = wpos.length()
                max_dist = self._wake_body.speed() * self._max_dist_time
                if wdist < max_dist:
                    strength = 1.0 - (wdist / max_dist)**self._att_exp
        return self._update_all_pert(dt,
                                     pos_1, vel_1, acc_1,
                                     at_dir_1, up_dir_1, ang_vel_1, ang_acc_1,
                                     strength=strength)


class Chaser (Body):

    family = "chaser"
    species = "inert"

    def __init__ (self, world, fov=ANIMATION_FOV,
                  pos=Point3(), hpr=Vec3(), parent=None,
                  name=""):

        Body.__init__(self,
            world=world, parent=parent,
            pos=pos, hpr=hpr,
            family=self.family, species=self.species, hitforce=0.0,
            name=name, side="")

        self.fov = fov

        self._focus_bodies = None


    def focus_point (self):

        pos = self.manual_focus_point()
        if pos is None:
            pos = self.auto_focus_point()
        return pos


    def auto_focus_point (self):

        return None


    def set_focus (self, body):

        if isinstance(body, (list, tuple)):
            self._focus_bodies = body
        else:
            self._focus_bodies = [body]


    def manual_focus_point (self):

        if self._focus_bodies:
            focus_bodies = []
            sum_pos = Point3(0, 0, 0)
            for body in self._focus_bodies:
                if body.alive:
                    sum_pos += body.pos()
                    focus_bodies.append(body)
            if len(focus_bodies) > 0:
                pos = sum_pos / len(focus_bodies)
            else:
                pos = None
            self._focus_bodies = focus_bodies
        else:
            pos = None
        return pos


    def is_attached_to (self, body):

        return False


class PointChaser (Chaser):
    """
    Chaser fixed at an absolute or relative point.
    """

    species = "point"

    def __init__ (self, world, point,
                  relto=None, rotrel=False,
                  atref=None, upref=None, lookrel=False,
                  distsens=2.0, atsens=4.0, upsens=4.0,
                  fov=ANIMATION_FOV, remdelay=None,
                  pos=None, hpr=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - point (Point3): The fixing point at which the chaser stands
        - relto (Body): the referent body to which the fixing point.
            is relative to. If None, the fixing point is relative to world.
        - rotrel (bool): If the referent body is given by relto, whether
            the fixing point is relative to its rotated axes.
            (otherwise only the distance is relative, and axes are world axes).
        - atref (Vec3|Point3|NodePath|Body): Where should the chaser look at.
            It can be given as a direction, a point, a node, or a body.
        - upref (Vec3|NodePath|Body): The upward direction for the chaser.
            It can be given directly as a direction (e.g. Vec3(0, 0, 1) for
            positive z-axis), or a node or a body whose up vector is going
            to be taken as the direction (e.g. same body as given with relto,
            or same body as given with atref).
        - lookrel (bool): Whether look references by atref and upref are
            relative to the relto's coordinate system (True),
            or to world coordinate system (False). This has effect only
            if relto is given and atref is a direction or a point.
        - distsens (float): The sensitivity with which the chaser follows
            the fixing point (the lower it is, the slower it follows)
        - atsens (float): the sensitivity with which the chaser turns to
            the look reference (the lower it is, the slower it turns)
        - upsens (float): The sensitivity with which the chaser rotates
            to the upward reference (the lower it is, the slower it rotates)
        - fov (float): vertical FOV (in degrees).
        - remdelay (float): The number of seconds after the referent body
            (given by relto) disappears when the chaser will remove itself.
            If not given, the chaser remains at last referent position
            indefinitely.
        - pos (Point3): The inital world position of the chaser at creation.
            If None, the chaser is immediately put at the fixing point (point).
        - hpr (Vec): The initial world direction in which the chaser looks.
            If None, the chaser immediately looks at the assigned reference
            (atref, upref).
        - name (string): The name of the chaser.
        """

        Chaser.__init__(self, world=world, fov=fov, name=name)

        self._point = point
        self._relto = relto
        self._rotrel = rotrel
        self._atref = atref
        self._upref = upref
        self._lookrel = lookrel
        self._distsens = distsens
        self._atsens = atsens
        self._upsens = upsens
        self._remdelay = remdelay

        if pos is None:
            if relto is None:
                pos = point
            else:
                if rotrel:
                    pos = relto.pos(self.parent, point)
                else:
                    pos = relto.pos(self.parent) + point
        self.node.setPos(pos)

        if hpr is None:
            ldir = self._look_to_dir()[0]
            tdir = self._look_up_dir()[0]
            set_hpr_vfu(self.node, ldir, tdir)
        else:
            self.node.setHpr(hpr)

        if relto is None:
            vel = Vec3()
        else:
            bvel0 = relto.vel(self.parent)
            if rotrel:
                bpos0 = relto.pos(self.parent)
                bpos = relto.pos(self.parent, self._point)
                bangvel = relto.angvel(self.parent)
                vel = bvel0 + bangvel.cross(bpos - bpos0)
            else:
                vel = bvel0
        self._vel = vel

        self._moving_to = False
        self._move_speed = 0.0
        self._move_acc = 0.0
        self._rotating_to = False
        self._move_angspeed = 0.0
        self._move_angacc = 0.0
        self._time_to_remove = None
        self._foving_to = False
        self._move_fovspeed = 0.0
        self._move_fovacc = 0.0

        #model = base.load_model("data", "models/aircraft/mig29/mig29.egg")
        #model.setScale(0.06)
        #model.setColor(1.0, 0.0, 0.0, 0.25)
        #model.reparentTo(self.node)
        #model.setTransparency(TransparencyAttrib.MAlpha)

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done

        pos = self.pos(self.parent)
        quat = self.quat(self.parent)

        if self._relto is not None and not self._relto.alive:
            self._point = pos
            self._relto = None
            self._rotrel = False
            self._lookrel = False
            if self._remdelay is not None:
                self._time_to_remove = self._remdelay
        if isinstance(self._atref, Body) and not self._atref.alive:
            self._atref = quat.getForward()
        if isinstance(self._upref, Body) and not self._upref.alive:
            self._upref = quat.getUp()

        dt = self.world.dt
        if dt == 0.0:
            return task.cont

        if self._time_to_remove is not None:
            self._time_to_remove -= dt
            if self._time_to_remove <= 0.0:
                self.destroy()
                return task.done

        # Set up velocity to move to the fixing point.
        tpos, tvel = self._point_pos()
        mdir = tpos - pos
        dist = mdir.length()
        mdir.normalize()
        if not self._moving_to:
            rvel = mdir * (dist * self._distsens)
        else:
            if self._move_speed > 0.0:
                if self._move_acc > 0.0:
                    #bdist = 0.5 * self._move_speed_curr**2 / self._move_acc
                    bdist = (2.0 / 3) * self._move_speed_curr**2 / self._move_acc
                    if bdist < dist:
                        acc = self._move_acc
                        if self._move_speed_curr < self._move_speed:
                            self._move_speed_curr += acc * dt
                            if self._move_speed_curr > self._move_speed:
                                self._move_speed_curr = self._move_speed
                        elif self._move_speed_curr > self._move_speed:
                            self._move_speed_curr -= acc * dt
                            if self._move_speed_curr < self._move_speed:
                                self._move_speed_curr = self._move_speed
                        if self._move_speed_curr * dt > dist:
                            self._move_speed_curr = 0.0
                            self._moving_to = False
                    elif dist > 0.0:
                        #acc = 0.5 * self._move_speed_curr**2 / dist
                        acc = (2.0 / 3) * self._move_speed_curr**2 / dist
                        self._move_speed_curr -= acc * dt
                        if self._move_speed_curr < 0.1:
                            self._move_speed_curr = 0.0
                            self._moving_to = False
                    else:
                        self._move_speed_curr = 0.0
                        self._moving_to = False
                    self._move_speed2_curr -= self._move_acc * dt
                    if self._move_speed2_curr < 0.0:
                        self._move_speed2_curr = 0.0
                else:
                    self._move_speed_curr = self._move_speed
                    if self._move_speed_curr * dt > dist:
                        self._move_speed_curr = dist / dt
                        self._moving_to = False
                    self._move_speed2_curr = 0.0
                rvel = (  mdir * self._move_speed_curr
                        + self._move_speed2_dir * self._move_speed2_curr)
                #print_each(1141, 1.0, "--moving", id(self), dist)
            else:
                rvel = mdir * (dist / dt)
                self._moving_to = False
            #if not self._moving_to:
                #print "--chaser-done-moving"
        vel = tvel + rvel

        if not self._rotating_to:
            # Set up angular velocity to turn to the target point.
            angvel_at = Vec3()
            if self._atref is not None:
                ldir = self._look_to_dir()[0]
                fdir = quat.getForward()
                fdir.normalize()
                axis = fdir.cross(ldir)
                axis.normalize()
                ang = fdir.signedAngleRad(ldir, axis)
                angspeed = ang * self._atsens
                angvel_at = axis * angspeed

            # Set up angular velocity to turn to up direction.
            angvel_up = Vec3()
            if self._upref is not None:
                tdir = self._look_up_dir()[0]
                fdir = quat.getForward()
                fdir.normalize()
                tudir = fdir.cross(tdir.cross(fdir))
                tudir.normalize()
                udir = quat.getUp()
                udir.normalize()
                axis = fdir
                ang = udir.signedAngleRad(tudir, fdir)
                angspeed = ang * self._upsens
                angvel_up = axis * angspeed

            angvel = angvel_at + angvel_up

        else:
            #pos1 = pos + vel * dt
            ldir, langvel = self._look_to_dir()
            tdir1, tangvel = self._look_up_dir()
            tdir = unitv(ldir.cross(tdir1).cross(ldir))
            fdir = quat.getForward()
            udir = quat.getUp()
            axto = unitv(fdir.cross(ldir))
            if axto.length() < 0.5: # i.e. null
                axto = ldir
            axup = unitv(udir.cross(tdir))
            if axup.length() < 0.5: # i.e. null
                axup = tdir
            angto = fdir.signedAngleRad(ldir, axto)
            angup = udir.signedAngleRad(tdir, axup)
            qto = Quat()
            qto.setFromAxisAngleRad(angto, axto)
            qup = Quat()
            qup.setFromAxisAngleRad(angup, axup)
            q = qto * qup
            q.normalize()
            axis = q.getAxis()
            ang = q.getAngleRad()
            if ang < 0.0: # can this happen?
                axis = -axis
                ang = -ang
            if self._move_angspeed > 0.0:
                if self._move_angacc > 0.0:
                    #bang = 0.5 * self._move_angspeed_curr**2 / self._move_angacc
                    bang = (2.0 / 3) * self._move_angspeed_curr**2 / self._move_angacc
                    if bang < ang:
                        angacc = self._move_angacc
                        if self._move_angspeed_curr < self._move_angspeed:
                            self._move_angspeed_curr += angacc * dt
                            if self._move_angspeed_curr > self._move_angspeed:
                                self._move_angspeed_curr = self._move_angspeed
                        elif self._move_angspeed_curr > self._move_angspeed:
                            self._move_angspeed_curr -= angacc * dt
                            if self._move_angspeed_curr < self._move_angspeed:
                                self._move_angspeed_curr = self._move_angspeed
                    elif ang > 0.0:
                        #angacc = 0.5 * self._move_angspeed_curr**2 / ang
                        angacc = (2.0 / 3) * self._move_angspeed_curr**2 / ang
                        self._move_angspeed_curr -= angacc * dt
                        if self._move_angspeed_curr < 0.001:
                            self._move_angspeed_curr = 0.0
                            self._rotating_to = False
                    else:
                        self._move_angspeed_curr = 0.0
                        self._rotating_to = False
                else:
                    self._move_angspeed_curr = self._move_angspeed
                    if self._move_angspeed_curr * dt > ang:
                        self._move_angspeed_curr = ang / dt
                        self._rotating_to = False
                rangvel = axis * self._move_angspeed_curr
                angvel = langvel + tangvel + rangvel
                #print_each(1143, 1.0, "--rotating", ang)
            else:
                angvel = axis * (ang / dt)
                self._rotating_to = False
            #if not self._rotating_to:
                #print "--chaser-done-rotating"

        if not self._foving_to:
            pass
        else:
            dfov = self._set_fov - self.fov
            absdfov = abs(dfov)
            if self._move_fovspeed > 0.0:
                if self._move_fovacc > 0.0:
                    bfov = (2.0 / 3) * self._move_fovspeed_curr**2 / self._move_fovacc
                    if bfov < absdfov:
                        fovacc = self._move_fovacc
                        if self._move_fovspeed_curr < self._move_fovspeed:
                            self._move_fovspeed_curr += fovacc * dt
                            if self._move_fovspeed_curr > self._move_fovspeed:
                                self._move_fovspeed_curr = self._move_fovspeed
                        elif self._move_fovspeed_curr > self._move_fovspeed:
                            self._move_fovspeed_curr -= fovacc * dt
                            if self._move_fovspeed_curr < self._move_fovspeed:
                                self._move_fovspeed_curr = self._move_fovspeed
                        if self._move_fovspeed_curr * dt > absdfov:
                            self._move_fovspeed_curr = 0.0
                            self._foving_to = False
                    elif absdfov > 0.0:
                        fovacc = (2.0 / 3) * self._move_fovspeed_curr**2 / absdfov
                        self._move_fovspeed_curr -= fovacc * dt
                        if self._move_fovspeed_curr < 0.5:
                            self._move_fovspeed_curr = 0.0
                            self._foving_to = False
                    else:
                        self._move_fovspeed_curr = 0.0
                        self._foving_to = False
                else:
                    if self._move_fovspeed * dt > absdfov:
                        self._move_fovspeed = absdfov / dt
                        self._foving_to = False
                self.fov += sign(dfov) * (self._move_fovspeed_curr * dt)
            else:
                # Needed in base class.
                self.fov = self._set_fov
            #if not self._foving_to:
                #print "--chaser-done-foving"

        self.aacc = (vel - self.vel(self.parent)) / dt
        self.aangacc = (angvel - self.angvel(self.parent)) / dt

        return task.cont


    def _point_pos (self, pos=None):

        if pos is None:
            pos = self.pos(self.parent)
        if self._relto is None:
            tvel = self.world.vel(self.parent)
            tpos = self.world.pos(self.parent, self._point)
        else:
            bpos0 = self._relto.pos(self.parent)
            bvel0 = self._relto.vel(self.parent)
            if self._rotrel:
                bpos = self._relto.pos(self.parent, self._point)
                bangvel = self._relto.angvel(self.parent)
                dbpos = bpos - bpos0
                tvel = bvel0 + bangvel.cross(dbpos)
                tpos = bpos
            else:
                tvel = bvel0
                tpos = bpos0 + self._point

        return tpos, tvel


    def _look_to_dir (self, pos=None, vel=None):

        if self._atref is not None:
            if pos is None:
                pos = self.pos(self.parent)
            if vel is None:
                vel = self.vel(self.parent)
            rbody = self._relto if self._relto and self._lookrel else self.world
            if isinstance(self._atref, Point3):
                ldir = rbody.pos(self.parent, self._atref) - pos
                lvel = rbody.vel(self.parent)
            elif isinstance(self._atref, Vec3):
                ldir = rbody.pos(self.parent, self._atref) - rbody.pos(self.parent)
                lvel = rbody.vel(self.parent)
            elif isinstance(self._atref, NodePath):
                ldir = self._atref.getPos(self.parent.node) - pos
                lvel = Vec3()
            elif isinstance(self._atref, Body):
                ldir = self._atref.pos(self.parent, self._atref.center) - pos
                lvel = self._atref.vel(self.parent)
            else:
                raise StandardError(
                    "Unknown type of look-at reference for the chaser.")
            lrad = ldir.length()
            ldir.normalize()
            rvel = lvel - vel
            avdir = unitv(ldir.cross(rvel))
            tvdir = unitv(avdir.cross(ldir))
            langvel = avdir * (rvel.dot(tvdir) / lrad)
        else:
            ldir = self.quat().getForward()
            langvel = Vec3()

        ldir = Vec3(ldir)
        langvel = Vec3(langvel)
        return ldir, langvel


    def _look_up_dir (self, pos=None, vel=None):

        if self._upref is not None:
            if pos is None:
                pos = self.pos(self.parent)
            rbody = self._relto if self._relto and self._lookrel else self.world
            if isinstance(self._upref, Point3):
                tdir = rbody.pos(self.parent, self._upref) - pos
                tangvel = rbody.angvel(self.parent)
            elif isinstance(self._upref, Vec3):
                tdir = rbody.pos(self.parent, self._upref) - rbody.pos(self.parent)
                tangvel = rbody.angvel(self.parent)
            elif isinstance(self._upref, NodePath):
                pnode = self.parent.node
                tdir = pnode.getRelativeVector(self._upref.getParent(),
                                               self._upref.getQuat().getUp())
                tangvel = Vec3()
            elif isinstance(self._upref, Body):
                tdir = self._upref.quat(self.parent).getUp()
                tangvel = self._upref.angvel(self.parent)
            else:
                raise StandardError(
                    "Unknown type of up-direction reference for the chaser.")
            tdir.normalize()
        else:
            tdir = self.quat(self.parent).getUp()
            tangvel = Vec3()

        tdir = Vec3(tdir)
        tangvel = Vec3(tangvel)
        return tdir, tangvel


    def move_to (self, point=None, relto=None, rotrel=None,
                 atref=None, upref=None, lookrel=None,
                 distsens=None, atsens=None, upsens=None,
                 speed=None, acc=None, angspeed=None, angacc=None,
                 fov=None, fovspeed=None, fovacc=None):

        if point is not None:
            self._point = point
        if relto is not None:
            if isinstance(relto, World):
                self._relto = None
            else:
                self._relto = relto
        if rotrel is not None:
            self._rotrel = rotrel
        if atref is not None:
            self._atref = atref
        if upref is not None:
            self._upref = upref
        if lookrel is not None:
            self._lookrel = lookrel
        if distsens is not None:
            self._distsens = distsens
        if atsens is not None:
            self._atsens = atsens
        if upsens is not None:
            self._upsens = upsens
        if speed is not None:
            self._move_speed = speed
        if acc is not None:
            self._move_acc = acc
        if angspeed is not None:
            self._move_angspeed = angspeed
        if angacc is not None:
            self._move_angacc = angacc
        if fov is not None:
            self._set_fov = fov
        if fovspeed is not None:
            self._move_fovspeed = fovspeed
        if fovacc is not None:
            self._move_fovacc = fovacc

        if point is not None and speed is not None:
            tpos, tvel = self._point_pos()
            mdir = tpos - self.pos(self.parent)
            if mdir.length() > 1e-3:
                mdir.normalize()
                vel = self.vel(self.parent)
                rvel = vel - tvel
                self._move_speed_curr = rvel.dot(mdir)
                rvel2 = rvel - mdir * self._move_speed_curr
                self._move_speed2_curr = rvel2.length()
                rvel2.normalize()
                self._move_speed2_dir = rvel2
                self._moving_to = True

        if (atref is not None or upref is not None) and angspeed is not None:
            self._move_angspeed_curr = 0.0
            self._rotating_to = True

        if fov is not None and fovspeed is not None:
            self._move_fovspeed_curr = 0.0
            self._foving_to = True


    def auto_focus_point (self):
        # Base override.

        if isinstance(self._atref, Body):
            if self._atref.alive:
                return self._atref.pos()
        elif isinstance(self._atref, NodePath):
            if not self._atref.isEmpty():
                return self._atref.getPos(self.world.node)
        elif isinstance(self._atref, Point3):
            return Point3(self._atref)
        return None


    def is_attached_to (self, body):
        # Base override.

        return body is self._relto


class TrackChaser (Chaser):
    """
    Chaser that can move around and track objects.
    """

    species = "track"

    def __init__ (self, world, point,
                  relto=None, rotrel=False,
                  atref=None, upref=None, lookrel=False,
                  speed=0.0, acc=0.0,
                  angspeed=0.0, angacc=0.0,
                  fovspeed=0.0, fovacc=0.0,
                  drift=None, shake=None,
                  remdelay=None, minotralt=0.5,
                  pos=None, hpr=None, fov=ANIMATION_FOV,
                  vel=None, angvel=None, fovvel=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - point (Point3): The fixing point at which the chaser stands.
        - relto (Body): The referent body to which the fixing point
            is relative to. If None, the fixing point is relative to world.
        - rotrel (bool): If the referent body is given by relto, whether
            the fixing point is relative to its rotated axes
            (otherwise only the distance is relative, and axes are world axes).
        - atref (Vec3|Point3|NodePath|Body|(Body...)): Where should the chaser
            look at. It can be given as a direction, a point, a node, a body,
            or tuple of bodies.
        - upref (Vec3|NodePath|Body): The upward direction for the chaser.
            It can be given directly as a direction (e.g. Vec3(0, 0, 1) for
            positive z-axis), or a node or a body whose up vector is going
            to be taken as the direction (e.g. same body as given with relto,
            or same body as given with atref).
        - lookrel (bool): Whether look references by atref and upref are
            relative to the relto's coordinate system (True),
            or to world coordinate system (False). This has effect only
            if relto is given and atref is a direction or a point.
        - speed (float): The maximum speed with which the chaser
            will translate to new location. If None, the chaser
            instantly jumps to new location.
        - acc (float): The acceleration which will be used for changes
            in translational speed. If None, the chaser instantly assumes
            maximum translational speed.
        - angspeed (float): The maximum speed with which the chaser
            will rotate to new direction. If None, the chaser
            instantly jumps to new direction.
        - angacc (float): The acceleration which will be used for changes
            in angular speed. If None, the chaser instantly assumes
            maximum angular speed.
        - fovspeed (float): The maximum speed with which the chaser
            will zoom to new FOV. If None, the chaser
            instantly jumps to new FOV.
        - fovacc (float): The acceleration which will be used for changes
            in zooming speed. If None, the chaser instantly assumes
            maximum zooming speed.
        - drift (Drift or spec): See Drift.__init__.
        - shake (Shake or spec): See Shake.__init__.
        - remdelay (float): The number of seconds after the referent body
            (given by relto) disappears when the chaser will remove itself.
            If not given, the chaser remains at last referent position
            indefinitely.
        - minotralt (float): The minimum altitude above terrain under which
            the chaser is not allowed to move.
        - pos (Point3): The inital world position of the chaser at creation.
            If None, the chaser is immediately put at the fixing point (point).
        - hpr (Vec): The initial world direction in which the chaser looks.
            If None, the chaser immediately looks at the assigned reference
            (atref, upref).
        - fov (float): Vertical FOV (in degrees).
        - vel (Vec): The initial velocity of the chaser.
            If None, the chaser immediately gets the velocity of
            the assigned reference (relto, rotrel).
        - angvel (Vec): The initial angular velocity of the chaser.
            If None, the chaser immediately gets the angular velocity of
            the assigned reference (atref, upref, lookrel).
        - fovvel (float): The initial vertical FOV change rate (in degrees).
        - name (string): The name of the chaser.
        """

        Chaser.__init__(self, world=world, fov=fov, name=name)

        self._point = point
        self._referent_body = relto
        self._rotate_relative = rotrel
        self._at_reference = atref
        self._up_reference = upref
        self._look_relative = lookrel
        self._speed = speed
        self._accel = acc
        self._ang_speed = angspeed
        self._ang_accel = angacc
        self._fov_speed = fovspeed
        self._fov_accel = fovacc
        self._remove_delay = remdelay
        self._min_otr_altitude = minotralt

        self._default_speed = speed
        self._default_accel = acc
        self._default_ang_speed = angspeed
        self._default_ang_accel = angacc
        self._default_fov_speed = fovspeed
        self._default_fov_accel = fovacc

        self._target_pos_eval = self._resolve_pos(
            self._point, self._rotate_relative, self._referent_body)
        pos_t, vel_t = self._target_pos_eval()
        if pos is None:
            pos = pos_t
            self.node.setPos(pos_t)
        else:
            self.node.setPos(pos)
        if vel is None:
            vel = vel_t
        acc = Vec3()
        self._vel = vel # needed in base class
        self._acc = acc # needed in base class
        # ...must be updated here, for proper angular velocity readout below.

        self._target_look_eval = self._resolve_look(
            self._at_reference, self._up_reference,
            self._look_relative, self._referent_body)
        at_dir_t, up_dir_t, ang_vel_t = self._target_look_eval()
        if hpr is None:
            set_hpr_vfu(self.node, vtof(at_dir_t), vtof(up_dir_t))
            at_dir = at_dir_t
            up_dir = up_dir_t
        else:
            self.node.setHpr(hpr)
            quat = self.node.quat()
            at_dir = _vtox(quat.getForward())
            up_dir = _vtox(quat.getUp())
        if angvel is None:
            angvel = vtof(ang_vel_t)
        angacc = Vec3()
        self._angvel = angvel # needed in base class
        self._angacc = angacc # needed in base class

        self._target_fov_eval = self._resolve_fov(fov)
        fov_t, fov_vel_t = self._target_fov_eval()
        if fov is None:
            fov = fov_t
        fov_vel = fovvel
        if fov_vel is None:
            fov_vel = fov_vel_t
        self._fov = fov
        self._fov_vel = fov_vel

        self._prev_target_pos = pos_t
        self._prev_target_at_dir = at_dir_t
        self._prev_target_up_dir = up_dir_t
        self._prev_target_fov = fov_t

        ang_vel = _vtox(angvel)
        ang_acc = _vtox(angacc)
        self._curr_blend_time = 0.0
        ret = self._project_move_pos(pos, vel, pos_t, vel_t)
        self._curr_off, self._curr_speed, self._curr_blend_vel = ret
        self._prev_base_pos = (pos, vel, acc)
        ret = self._project_move_look(at_dir, up_dir, ang_vel,
                                      at_dir_t, up_dir_t, ang_vel_t)
        self._curr_ang_off, self._curr_rot_axis, self._curr_ang_speed, self._curr_blend_ang_vel = ret
        self._prev_base_dir = (at_dir, up_dir, ang_vel, ang_acc)
        ret = self._project_move_fov(fov, fov_vel, fov_t, fov_vel_t)
        self._curr_fov_off, self._curr_fov_speed, self._curr_blend_fov_vel = ret
        self._prev_base_fov = (fov, fov_vel)

        self._restore_speed_accel = False
        self._restore_ang_speed_accel = False
        self._restore_fov_speed_accel = False

        self._time_to_remove = None

        if isinstance(drift, Drift):
            self._drift = drift
        else:
            self._drift = Drift(world, self, drift,
                                pos, vel, acc,
                                at_dir, up_dir, ang_vel, ang_acc)
        if isinstance(shake, Shake):
            self._shake = shake
        else:
            self._shake = Shake(world, self, shake,
                                pos, vel, acc,
                                at_dir, up_dir, ang_vel, ang_acc)

        self._skip = False
        self.ignore_flyby = 3

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if self.parent and not self.parent.alive:
            self.destroy()
            return task.done

        if self._time_to_remove is not None:
            self._time_to_remove -= self.world.dt
            if self._time_to_remove <= 0.0:
                self.destroy()
                return task.done

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        # Update references.
        update_target_pos = False
        update_target_look = False
        if self._referent_body and not self._referent_body.alive:
            self._point = self.node.getPos()
            self._referent_body = None
            self._rotate_relative = False
            self._look_relative = False
            if self._remove_delay is not None:
                self._time_to_remove = self._remove_delay
            update_target_pos = True
            update_target_look = True
        at_reference = as_sequence(self._at_reference)
        if at_reference and isinstance(at_reference[0], Body) and not any(r.alive for r in at_reference):
            quat = self.node.getQuat()
            self._at_reference = quat.getForward()
            update_target_look = True
        if isinstance(self._up_reference, Body) and not self._up_reference.alive:
            quat = self.node.getQuat()
            self._up_reference = quat.getUp()
            update_target_look = True
        if update_target_pos:
            ret = self._resolve_pos(self._point,
                                    self._rotate_relative, self._referent_body)
            self._target_pos_eval = ret
            pos_t, vel_t = self._target_pos_eval()
            self._prev_target_pos = pos_t
            self._curr_off = 0.0
            self._curr_speed = 0.0
            self._curr_blend_vel = Vec3()
        if update_target_look:
            self._target_look_eval = self._resolve_look(
                self._at_reference, self._up_reference,
                self._look_relative, self._referent_body)
            at_dir_t, up_dir_t, ang_vel_t = self._target_look_eval()
            self._prev_target_at_dir = at_dir_t
            self._prev_target_up_dir = up_dir_t
            self._curr_ang_off = 0.0
            self._curr_ang_speed = 0.0
            self._curr_blend_ang_vel = _Vx()

        # Update blend time.
        if self._curr_blend_time > 0.0:
            blend_time = self._curr_blend_time
            blend_time_1 = max(blend_time - dt, 0.0)
            self._curr_blend_time = blend_time_1
        else:
            blend_time = 0.0

        # Recover last base values.
        pos, vel, acc = self._prev_base_pos
        self.node.setPos(pos) # for any readouts below
        at_dir, up_dir, ang_vel, ang_acc = self._prev_base_dir
        set_hpr_vfu(self.node, vtof(at_dir), vtof(up_dir)) # for any readouts below
        fov, fov_vel = self._prev_base_fov
        self._fov = fov # for any readouts below

        # Update base position.
        off_eps = 1e-5
        pos_t, vel_t = self._target_pos_eval()
        off = self._curr_off
        #print "--pch2-20a =========="
        if abs(off) > off_eps: #or blend_time > 0.0:
            speed = self._curr_speed
            ret = update_bounded(
                tvalue=0.0, tspeed=0.0,
                value=off, speed=speed,
                maxspeed=self._speed, minaccel=self._accel,
                dt=dt)
            off_1, speed_1 = ret
            if self._restore_speed_accel and abs(off_1) <= off_eps:
                self._speed = self._default_speed
                self._accel = self._default_accel
                self._restore_speed_accel = False
            pos_tp = self._prev_target_pos
            dpos_tp = pos_tp - pos # yes, pos_tp
            dir_tp = unitv(dpos_tp)
            pos_1 = pos_t + dir_tp * off_1 # yes, pos_t
            if blend_time > 0.0:
                blend_vel = self._curr_blend_vel
                blend_vel_1 = blend_vel * (blend_time_1 / blend_time)
                blend_off_1 = blend_vel_1 * dt
                pos_1 += blend_off_1
                self._curr_blend_vel = blend_vel_1
                #print "--pch2-24", blend_vel_1, blend_vel_1.length()
            #print "--pch2-25a", pos_t, pos
            #print "--pch2-25b", off, off_1, speed, speed_1, dir_tp
            self._curr_off = off_1
            self._curr_speed = speed_1
        else:
            pos_1 = pos_t
        if self.world.below_surface(pos_1, self._min_otr_altitude):
            pos_1[2] = self.world.elevation(pos_1) + self._min_otr_altitude
        self._prev_target_pos = pos_t
        self.node.setPos(pos_1)
        # ...must be updated here, for proper directions readout below.

        # Update base rotation.
        ang_off_eps = radians(1e-5)
        at_dir_t, up_dir_t, ang_vel_t = self._target_look_eval()
        ang_off = self._curr_ang_off
        mod_ang_vel = False
        #print "--pch2-30 =========="
        #print "--pch2-31a", at_dir_t, at_dir
        #print "--pch2-31b", up_dir_t, up_dir
        if abs(ang_off) > ang_off_eps: #or blend_time > 0.0:
            ang_speed = self._curr_ang_speed
            ret = update_bounded(
                tvalue=0.0, tspeed=0.0,
                value=ang_off, speed=ang_speed,
                maxspeed=self._ang_speed, minaccel=self._ang_accel,
                dt=dt)
            ang_off_1, ang_speed_1 = ret
            if self._restore_ang_speed_accel and abs(ang_off_1) <= ang_off_eps:
                self._ang_speed = self._default_ang_speed
                self._ang_accel = self._default_ang_accel
                self._restore_ang_speed_accel = False
            at_dir_tp = self._prev_target_at_dir
            up_dir_tp = self._prev_target_up_dir
            ret = rotation_forward_up(at_dir_tp, up_dir_tp, at_dir_t, up_dir_t)
            rot_ang_tpt, rot_axis_tpt = ret
            rot_tpt = _Qx()
            rot_tpt.setFromAxisAngleRad(rot_ang_tpt, rot_axis_tpt)
            rot_axis = self._curr_rot_axis
            at_dir_1p = unitv(_Vx(rot_tpt.xform(at_dir)))
            up_dir_1p = unitv(_Vx(rot_tpt.xform(up_dir)))
            rot_axis_1p = unitv(_Vx(rot_tpt.xform(rot_axis)))
            rot_1p = _Qx()
            rot_ang_1p = ang_off - ang_off_1
            rot_1p.setFromAxisAngleRad(rot_ang_1p, rot_axis_1p)
            #print "--pch2-32a", degrees(rot_ang_1p / dt), degrees(rot_1p.getAngleRad() / dt)
            at_dir_1 = unitv(_Vx(rot_1p.xform(at_dir_1p)))
            up_dir_1 = unitv(_Vx(rot_1p.xform(up_dir_1p)))
            if blend_time > 0.0:
                blend_ang_vel = self._curr_blend_ang_vel
                blend_ang_vel_1 = blend_ang_vel * (blend_time_1 / blend_time)
                blend_ang_speed_1 = blend_ang_vel_1.length()
                if blend_ang_speed_1 > ang_off_eps / dt:
                    blend_ang_off_1 = blend_ang_speed_1 * dt
                    blend_rot_axis = unitv(blend_ang_vel) # yes, not _1
                    blend_rot_1 = _Qx()
                    blend_rot_1.setFromAxisAngleRad(blend_ang_off_1, blend_rot_axis)
                    at_dir_1 = unitv(_Vx(blend_rot_1.xform(at_dir_1)))
                    up_dir_1 = unitv(_Vx(blend_rot_1.xform(up_dir_1)))
                    self._curr_blend_ang_vel = blend_ang_vel_1
                    #print "--pch2-34", blend_ang_vel_1, blend_ang_speed_1
            #print "--pch2-35a", at_dir_t, at_dir, at_dir_1
            #print "--pch2-35b", up_dir_t, up_dir, up_dir_1
            #print "--pch2-35c", ang_off, ang_off_1, ang_speed, ang_speed_1
            self._curr_ang_off = ang_off_1
            self._curr_rot_axis = rot_axis_1p # yes, _1p
            self._curr_ang_speed = ang_speed_1
        else:
            at_dir_1 = at_dir_t
            up_dir_1 = up_dir_t
        self._prev_target_at_dir = at_dir_t
        self._prev_target_up_dir = up_dir_t
        set_hpr_vfu(self.node, vtof(at_dir_1), vtof(up_dir_1))

        # Update base zoom.
        fov_off_eps = 1e-5
        fov_t, fov_vel_t = self._target_fov_eval()
        fov_off = self._curr_fov_off
        if abs(fov_off) > fov_off_eps: #or blend_time > 0.0:
            fov_speed = self._curr_fov_speed
            ret = update_bounded(
                tvalue=0.0, tspeed=0.0,
                value=fov_off, speed=fov_speed,
                maxspeed=self._fov_speed, minaccel=self._fov_accel,
                dt=dt)
            fov_off_1, fov_speed_1 = ret
            if self._restore_fov_speed_accel and abs(fov_off_1) <= fov_off_eps:
                self._fov_speed = self._default_fov_speed
                self._fov_accel = self._default_fov_accel
                self._restore_fov_speed_accel = False
            fov_tp = self._prev_target_fov
            dfov_tp = fov_tp - fov # yes, fov_tp
            fov_dir_tp = sign(dfov_tp)
            fov_1 = fov_t + fov_dir_tp * fov_off_1 # yes, fov_t
            if blend_time > 0.0:
                blend_fov_vel = self._curr_blend_fov_vel
                blend_fov_vel_1 = blend_fov_vel * (blend_time_1 / blend_time)
                blend_fov_off_1 = blend_fov_vel_1 * dt
                fov_1 += blend_fov_off_1
                self._curr_blend_fov_vel = blend_fov_vel_1
            self._curr_fov_off = fov_off_1
            self._curr_fov_speed = fov_speed_1
        else:
            fov_1 = fov_t
        self._prev_target_fov = fov_t
        self._fov = fov_1

        # Update velocities and accelerations excluding drifting and shaking.
        # Store values for retrieval in next move.
        vel_1 = (pos_1 - pos) / dt
        acc_1 = (vel_1 - vel) / dt
        self._prev_base_pos = (pos_1, vel_1, acc_1)
        ret = rotation_forward_up(at_dir, up_dir, at_dir_1, up_dir_1)
        rot_ang_1, rot_axis_1 = ret
        ang_vel_1 = rot_axis_1 * (rot_ang_1 / dt)
        ang_acc_1 = (ang_vel_1 - ang_vel) / dt
        self._prev_base_dir = (at_dir_1, up_dir_1, ang_vel_1, ang_acc_1)
        fov_vel_1 = (fov_1 - fov) / dt
        self._fov_vel = fov_vel_1
        self._prev_base_fov = (fov_1, fov_vel_1)

        # Update drift and shake.
        # Send copies to update functions, not to clobber stored values.
        pos_1 = pos_1 * 1.0
        at_dir_1 = at_dir_1 * 1.0
        up_dir_1 = up_dir_1 * 1.0
        if self._skip:
            self._drift.reset(pos_1, vel_1, acc_1,
                              at_dir_1, up_dir_1, ang_vel_1, ang_acc_1)
        ret = self._drift.update(dt,
                                 pos_1, vel_1, acc_1,
                                 at_dir_1, up_dir_1, ang_vel_1, ang_acc_1)
        pos_1, at_dir_1, up_dir_1 = ret
        if self._skip:
            self._shake.reset(pos_1, vel_1, acc_1,
                              at_dir_1, up_dir_1, ang_vel_1, ang_acc_1)
        ret = self._shake.update(dt,
                                 pos_1, vel_1, acc_1,
                                 at_dir_1, up_dir_1, ang_vel_1, ang_acc_1)
        pos_1, at_dir_1, up_dir_1 = ret
        self.node.setPos(pos_1)
        set_hpr_vfu(self.node, vtof(at_dir_1), vtof(up_dir_1))

        # Needed in base class.
        self.fov = self._fov
        self._vel = vtof(vel_1)
        self._acc = vtof(acc_1)
        self._angvel = vtof(ang_vel_1)
        self._angacc = vtof(ang_acc_1)

        if not base.with_sound_doppler and self.ignore_flyby > 0:
            self.ignore_flyby -= 1

        self._skip = False


    def move_to (self, point=None, relto=None, rotrel=None,
                 atref=None, upref=None, lookrel=None,
                 fov=None,
                 speed=None, acc=None,
                 angspeed=None, angacc=None,
                 fovspeed=None, fovacc=None,
                 blendtime=0.0, skip=False):

        update_target_pos = False
        update_target_look = False
        update_target_fov = False

        if point is not None:
            self._point = point
            update_target_pos = True
        if rotrel is not None:
            self._rotate_relative = rotrel
            update_target_pos = True
        if atref is not None:
            self._at_reference = atref
            update_target_look = True
        if upref is not None:
            self._up_reference = upref
            update_target_look = True
        if lookrel is not None:
            self._look_relative = lookrel
            update_target_look = True
        if relto is not None: # must come after rotrel/lookrel
            if relto is -1:
                relto = None
            self._referent_body = relto
            update_target_pos = True
            if self._look_relative:
                update_target_look = True
        if True:
            update_target_fov = True
        if speed is not None:
            self._speed = speed
            self._restore_speed_accel = True
        else:
            self._speed = self._default_speed
        if acc is not None:
            self._accel = acc
            self._restore_speed_accel = True
        else:
            self._accel = self._default_accel
        if angspeed is not None:
            self._ang_speed = angspeed
            self._restore_ang_speed_accel = True
        else:
            self._ang_speed = self._default_ang_speed
        if angacc is not None:
            self._ang_accel = angacc
            self._restore_ang_speed_accel = True
        else:
            self._ang_accel = self._default_ang_accel
        if fovspeed is not None:
            self._fov_speed = fovspeed
            self._restore_fov_speed_accel = True
        else:
            self._fov_speed = self._default_fov_speed
        if fovacc is not None:
            self._fov_accel = fovacc
            self._restore_fov_speed_accel = True
        else:
            self._fov_accel = self._default_fov_accel

        self._curr_blend_time = blendtime

        if update_target_pos:
            self._target_pos_eval = self._resolve_pos(
                self._point, self._rotate_relative, self._referent_body)
            pos_t, vel_t = self._target_pos_eval()
            self._prev_target_pos = pos_t
            pos, vel, acc = self._prev_base_pos # ignore drift/shake
            ret = self._project_move_pos(pos, vel, pos_t, vel_t)
            self._curr_off, self._curr_speed, self._curr_blend_vel = ret
            if not base.with_sound_doppler:
                self.ignore_flyby = 3
        if update_target_look:
            self._target_look_eval = self._resolve_look(
                self._at_reference, self._up_reference,
                self._look_relative, self._referent_body)
            at_dir_t, up_dir_t, ang_vel_t = self._target_look_eval()
            self._prev_target_at_dir = at_dir_t
            self._prev_target_up_dir = up_dir_t
            at_dir, up_dir, ang_vel, ang_acc = self._prev_base_dir # ignore drift/shake
            ret = self._project_move_look(at_dir, up_dir, ang_vel,
                                          at_dir_t, up_dir_t, ang_vel_t)
            self._curr_ang_off, self._curr_rot_axis, self._curr_ang_speed, self._curr_blend_ang_vel = ret
        if update_target_fov:
            self._target_fov_eval = self._resolve_fov(fov)
            fov_t, fov_vel_t = self._target_fov_eval()
            self._prev_target_fov = fov_t
            fov, fov_vel = self._prev_base_fov # ignore drift/shake
            ret = self._project_move_fov(fov, fov_vel, fov_t, fov_vel_t)
            self._curr_fov_off, self._curr_fov_speed, self._curr_blend_fov_vel = ret

        self._skip = skip


    def _resolve_pos (self, point,
                      rotate_relative, referent_body):

        if referent_body is not None:
            if rotate_relative:
                def pos_eval ():
                    vel_b = referent_body.vel(self.parent)
                    pos_b = referent_body.pos(self.parent)
                    ang_vel_b = referent_body.angvel(self.parent)
                    pos_p = referent_body.pos(self.parent, point)
                    vel_p = vel_b + ang_vel_b.cross(pos_p - pos_b)
                    return pos_p, vel_p
            else:
                def pos_eval ():
                    pos_p = referent_body.pos(self.parent) + point
                    vel_p = referent_body.vel(self.parent)
                    return pos_p, vel_p
        else:
            def pos_eval ():
                pos_p = self.world.pos(self.parent, point)
                vel_p = Vec3()
                return pos_p, vel_p

        return pos_eval


    def _resolve_look (self, at_reference, up_reference,
                       look_relative, referent_body):

        if not look_relative:
            referent_body = None

        def rel_pt_look_eval (pos_p, vel_p):
            pos = _ptox(self.pos(self.parent))
            vel = _vtox(self.vel(self.parent))
            pos_off_p = pos_p - pos
            vel_off_p = vel_p - vel
            ang_vel_p = pos_off_p.cross(vel_off_p) / pos_off_p.lengthSquared()
            at_dir_p = unitv(pos_off_p)
            return at_dir_p, ang_vel_p

        if isinstance(at_reference, Point3):
            if referent_body is not None:
                def at_eval ():
                    pos_b = _ptox(referent_body.pos(self.parent))
                    vel_b = _vtox(referent_body.vel(self.parent))
                    ang_vel_b = _vtox(referent_body.angvel(self.parent))
                    pos_p = _ptox(referent_body.pos(self.parent, at_reference))
                    vel_p = vel_b + ang_vel_b.cross(pos_p - pos_b)
                    return rel_pt_look_eval(pos_p, vel_p)
            else:
                def at_eval ():
                    pos_p = _ptox(at_reference)
                    vel_p = _Vx()
                    return rel_pt_look_eval(pos_p, vel_p)
        elif isinstance(at_reference, Vec3):
            if referent_body is not None:
                def at_eval ():
                    at_dir_v = unitv(_vtox(self.parent.node.getRelativeVector(referent_body.node, at_reference)))
                    ang_vel_b = _vtox(referent_body.angvel(self.parent))
                    ang_vel_v = ang_vel_b - at_dir_v * ang_vel_b.dot(at_dir_v)
                    return at_dir_v, ang_vel_v
            else:
                def at_eval ():
                    at_dir_v = unitv(_vtox(at_reference))
                    ang_vel_v = _Vx()
                    return at_dir_v, ang_vel_v
        elif isinstance(at_reference, Body):
            def at_eval ():
                pos_p = _ptox(at_reference.pos(self.parent, at_reference.center))
                vel_p = _vtox(at_reference.vel(self.parent))
                return rel_pt_look_eval(pos_p, vel_p)
        elif isinstance(at_reference, (tuple, list)) and isinstance(at_reference[0], Body):
            def at_eval ():
                pos_p = _Px(0.0, 0.0, 0.0)
                vel_p = _Vx(0.0, 0.0, 0.0)
                num_alive = 0
                for ref in at_reference:
                    if ref.alive:
                        pos_p += _ptox(ref.pos(self.parent, ref.center))
                        vel_p += _vtox(ref.vel(self.parent))
                        num_alive += 1
                pos_p /= num_alive
                vel_p /= num_alive
                return rel_pt_look_eval(pos_p, vel_p)
        elif at_reference is None:
            def at_eval ():
                at_dir = _vtox(self.quat(self.parent).getForward())
                ang_vel = _vtox(self.angvel(self.parent))
                ang_vel_v = ang_vel - at_dir * ang_vel.dot(at_dir)
                return at_dir, ang_vel_v
        else:
            raise StandardError("Unknown type of at-direction reference.")

        if isinstance(up_reference, Point3):
            if referent_body is not None:
                def up_eval ():
                    pos_b = _ptox(referent_body.pos(self.parent))
                    vel_b = _vtox(referent_body.vel(self.parent))
                    ang_vel_b = _vtox(referent_body.angvel(self.parent))
                    pos_p = _ptox(referent_body.pos(self.parent, up_reference))
                    vel_p = vel_b + ang_vel_b.cross(pos_p - pos_b)
                    return rel_pt_look_eval(pos_p, vel_p)
            else:
                def up_eval ():
                    pos_p = _ptox(up_reference)
                    vel_p = _Vx()
                    return rel_pt_look_eval(pos_p, vel_p)
        elif isinstance(up_reference, Vec3):
            if referent_body is not None:
                def up_eval ():
                    up_dir_v = unitv(_vtox(self.parent.node.getRelativeVector(referent_body.node, up_reference)))
                    ang_vel_b = _vtox(referent_body.angvel(self.parent))
                    ang_vel_v = ang_vel_b - up_dir_v * ang_vel_b.dot(up_dir_v)
                    return up_dir_v, ang_vel_v
            else:
                def up_eval ():
                    up_dir_v = unitv(_vtox(up_reference))
                    ang_vel_v = _Vx()
                    return up_dir_v, ang_vel_v
        elif isinstance(up_reference, Body):
            def up_eval ():
                up_dir_v = _vtox(self.parent.node.getRelativeVector(up_reference.node.getParent(), up_reference.node.getQuat().getUp()))
                ang_vel_b = _vtox(up_reference.angvel(self.parent))
                ang_vel_v = ang_vel_b - up_dir_v * ang_vel_b.dot(up_dir_v)
                return up_dir_v, ang_vel_v
        elif up_reference is None:
            def up_eval ():
                up_dir = _vtox(self.quat(self.parent).getUp())
                ang_vel = _vtox(self.angvel(self.parent))
                ang_vel_v = ang_vel - up_dir * ang_vel.dot(up_dir)
                return up_dir, ang_vel_v
        else:
            raise StandardError("Unknown type of up-direction reference.")

        def look_eval ():
            at_dir, at_ang_vel = at_eval()
            up_dir, up_ang_vel = up_eval()
            up_dir_n = unitv(at_dir.cross(up_dir).cross(at_dir))
            up_ang_vel_t = at_dir * up_ang_vel.dot(at_dir)
            ang_vel = at_ang_vel + up_ang_vel_t
            return at_dir, up_dir_n, ang_vel

        return look_eval


    def _resolve_fov (self, fov_t):

        if fov_t is None:
            fov_t = self._fov

        def fov_eval ():
            return fov_t, 0.0

        return fov_eval


    def _project_move_pos (self, pos, vel, pos_t, vel_t):

        dpos = pos_t - pos
        off = -dpos.length()
        off_eps = 1e-5
        if abs(off) > off_eps:
            vel_off = vel - vel_t
            dir_off = unitv(dpos)
            speed = vel_off.dot(dir_off)
            if speed > 0.0:
                blend_vel = vel_off - dir_off * vel_off.dot(dir_off)
            else:
                speed = 0.0
                blend_vel = vel_off
        else:
            off = 0.0
            speed = 0.0
            blend_vel = Vec3()
        return off, speed, blend_vel


    def _project_move_look (self, at_dir, up_dir, ang_vel, at_dir_t, up_dir_t, ang_vel_t):

        #up_dir = unitv(at_dir.cross(up_dir).cross(at_dir))
        #up_dir_t = unitv(at_dir_t.cross(up_dir_t).cross(at_dir_t))

        ret = rotation_forward_up(at_dir, up_dir, at_dir_t, up_dir_t, neg=True)
        ang_off, rot_axis = ret
        ang_off_eps = radians(1e-5)
        if abs(ang_off) > ang_off_eps:
            ang_vel_off = ang_vel_t - ang_vel
            ang_speed = ang_vel_off.dot(rot_axis)
            if ang_speed > 0.0:
                blend_ang_vel = ang_vel_off - rot_axis * ang_vel_off.dot(rot_axis)
            else:
                ang_speed = 0.0
                blend_ang_vel = ang_vel_off
        else:
            ang_off = 0.0
            ang_speed = 0.0
            blend_ang_vel = type(at_dir)()
        #print "--pch2-pmv-28", ang_off, rot_axis, ang_speed, blend_ang_vel
        return ang_off, rot_axis, ang_speed, blend_ang_vel


    def _project_move_fov (self, fov, fov_vel, fov_t, fov_vel_t):

        dfov = fov_t - fov
        fov_off = -abs(dfov)
        fov_off_eps = 1e-5
        if abs(fov_off) > fov_off_eps:
            fov_vel_off = fov_vel - fov_vel_t
            fov_speed = fov_vel_off * sign(dfov)
            if fov_speed > 0.0:
                fov_blend_vel = 0.0
            else:
                fov_speed = 0.0
                fov_blend_vel = fov_vel_off
        else:
            fov_off = 0.0
            fov_speed = 0.0
            fov_blend_vel = 0.0
        return fov_off, fov_speed, fov_blend_vel


    def observed_body (self):

        if isinstance(self._at_reference, Body):
            if self._at_reference.alive:
                return self._at_reference
        elif isinstance(self._at_reference, (tuple, list)) and isinstance(self._at_reference[0], Body):
            dr = [(self.dist(r), r) for r in self._at_reference if r.alive]
            if dr:
                return min(dr)[1]
        return None


    def auto_focus_point (self):
        # Base override.

        if isinstance(self._at_reference, Body):
            if self._at_reference.alive:
                return self._at_reference.pos()
        elif isinstance(self._at_reference, (tuple, list)) and isinstance(self._at_reference[0], Body):
            pos = Point3(0.0, 0.0, 0.0)
            num_alive = 0
            for ref in self._at_reference:
                if ref.alive:
                    pos += ref.pos()
                    num_alive += 1
            if num_alive > 0:
                pos /= num_alive
                return pos
        elif isinstance(self._at_reference, NodePath):
            if not self._at_reference.isEmpty():
                return self._at_reference.getPos(self.world.node)
        elif isinstance(self._at_reference, Point3):
            return Point3(self._at_reference)
        return None


    def is_attached_to (self, body):
        # Base override.

        return body is self._referent_body


class ElasticChaser (Chaser):
    """
    Chaser elastically following an absolute or relative point.
    """

    species = "elastic"

    def __init__ (self, world, point,
                  relto=None, rotrel=False,
                  atref=None, upref=None, lookrel=False, fov=ANIMATION_FOV,
                  distlag=0.50, atlag=0.25, uplag=0.25, fovlag=0.10,
                  remdelay=None,
                  pos=None, hpr=None, vel=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - point (Point3): The fixing point at which the chaser stands
        - relto (Body): the referent body to which the fixing point.
            is relative to. If None, the fixing point is relative to world.
        - rotrel (bool): If the referent body is given by relto, whether
            the fixing point is relative to its rotated axes.
            (otherwise only the distance is relative, and axes are world axes).
        - atref (Vec3|Point3|NodePath|Body): Where should the chaser look at.
            It can be given as a direction, a point, a node, or a body.
        - upref (Vec3|NodePath|Body): The upward direction for the chaser.
            It can be given directly as a direction (e.g. Vec3(0, 0, 1) for
            positive z-axis), or a node or a body whose up vector is going
            to be taken as the direction (e.g. same body as given with relto,
            or same body as given with atref).
        - lookrel (bool): Whether look references by atref and upref are
            relative to the relto's coordinate system (True),
            or to world coordinate system (False). This has effect only
            if relto is given and atref is a direction or a point.
        - fov (float): vertical FOV (in degrees).
        - distlag (float): The instant time lag with which the chaser
            follows the fixing point.
        - atlag (float): The instant time lag with which the chaser rotates
            towards the look reference.
        - uplag (float): The instant time lag with which the chaser rotates
            towards the upward reference.
        - fovlag (float): The instant time lag with which the chaser zooms
            towards the FOV reference.
        - remdelay (float): The number of seconds after the referent body
            (given by relto) disappears when the chaser will remove itself.
            If not given, the chaser remains at last referent position
            indefinitely.
        - pos (Point3): The inital world position of the chaser at creation.
            If None, the chaser is immediately put at the fixing point (point).
        - hpr (Vec): The initial world direction in which the chaser looks.
            If None, the chaser immediately looks at the assigned reference
            (atref, upref).
        - vel (Vec): The initial velocity of the chaser.
            If None, the chaser immediately gets the velocity of
            the assigned reference (relto, rotrel).
        - name (string): The name of the chaser.
        """

        Chaser.__init__(self, world=world, fov=fov, name=name)

        self._point = point
        self._referent_body = relto
        self._rotate_relative = rotrel
        self._at_reference = atref
        self._up_reference = upref
        self._look_relative = lookrel
        self._fov = fov
        self._dist_lag = distlag
        self._at_lag = atlag
        self._up_lag = uplag
        self._fov_lag = fovlag
        self._remove_delay = remdelay

        self._target_pos_eval = self._resolve_pos(
            self._point, self._rotate_relative, self._referent_body)
        pos_t, vel_t = self._target_pos_eval()
        if pos is None:
            self.node.setPos(pos_t)
        else:
            self.node.setPos(pos)
        if vel is None:
            vel = vel_t

        self._target_look_eval = self._resolve_look(
            self._at_reference, self._up_reference,
            self._look_relative, self._referent_body)
        at_dir_t, up_dir_t = self._target_look_eval()
        if hpr is None:
            set_hpr_vfu(self.node, at_dir_t, up_dir_t)
        else:
            self.node.setHpr(hpr)

        self._target_fov_eval = lambda: fov
        fov_t = self._target_fov_eval()

        self._time_to_remove = None

        self._default_dist_lag = distlag
        self._default_at_lag = atlag
        self._default_up_lag = uplag
        self._default_fov_lag = fovlag

        self._restore_default_lag = False

        # Needed in base class.
        self.fov = fov_t
        self._vel = vel

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if self.parent and not self.parent.alive:
            self.destroy()
            return task.done

        if self._time_to_remove is not None:
            self._time_to_remove -= self.world.dt
            if self._time_to_remove <= 0.0:
                self.destroy()
                return task.done

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        update_target_pos = False
        update_target_look = False
        if self._referent_body and not self._referent_body.alive:
            self._point = self.node.getPos()
            self._referent_body = None
            self._rotate_relative = False
            self._look_relative = False
            if self._remove_delay is not None:
                self._time_to_remove = self._remove_delay
            update_target_pos = True
        if isinstance(self._at_reference, Body) and not self._at_reference.alive:
            quat = self.node.getQuat()
            self._at_reference = quat.getForward()
            update_target_look = True
        if isinstance(self._up_reference, Body) and not self._up_reference.alive:
            quat = self.node.getQuat()
            self._up_reference = quat.getUp()
            update_target_look = True
        if update_target_pos:
            self._target_pos_eval = self._resolve_pos(
                self._point, self._rotate_relative, self._referent_body)
        if update_target_look:
            self._target_look_eval = self._resolve_look(
                self._at_reference, self._up_reference,
                self._look_relative, self._referent_body)

        eps_dist = 1e-5
        pos = self.node.getPos()
        pos_t, vel_t = self._target_pos_eval()
        dpos_t = pos_t - pos
        dist_t = dpos_t.length()
        if dist_t > eps_dist:
            dist_dir = unitv(dpos_t)
            vel_1 = vel_t + dist_dir * (dist_t / self._dist_lag)
            dpos_1 = vel_1 * dt
            dist_1 = dpos_1.length()
            if dist_1 < dist_t:
                pos_1 = pos + dpos_1
            else:
                pos_1 = pos_t
        else:
            pos_1 = pos_t
            vel_1 = vel_t

        self.node.setPos(pos_1)
        # ...must be updated here, for proper directions readout below.

        quat = self.node.getQuat()
        eps_axis = 1e-10

        at_dir_t, up_dir_t = self._target_look_eval()

        at_dir = unitv(quat.getForward())
        at_axis = at_dir.cross(at_dir_t)
        if at_axis.lengthSquared() > eps_axis:
            at_axis.normalize()
            at_dang_t = at_dir.signedAngleRad(at_dir_t, at_axis)
            at_speed_1 = at_dang_t / self._at_lag
            at_dang_1 = at_speed_1 * dt
            if abs(at_dang_1) < abs(at_dang_t):
                at_rot_1 = Quat()
                at_rot_1.setFromAxisAngleRad(at_dang_1, at_axis)
                at_dir_1 = unitv(at_rot_1.xform(at_dir))
            else:
                at_dir_1 = at_dir_t
        else:
            at_dir_1 = at_dir_t

        up_dir = unitv(quat.getUp())
        #up_dir_t = unitv(at_dir_t.cross(up_dir_t).cross(at_dir_t))
        up_axis = up_dir.cross(up_dir_t)
        if up_axis.lengthSquared() > eps_axis:
            up_axis.normalize()
            up_dang_t = up_dir.signedAngleRad(up_dir_t, up_axis)
            up_speed_1 = up_dang_t / self._up_lag
            up_dang_1 = up_speed_1 * dt
            if abs(up_dang_1) < abs(up_dang_t):
                up_rot_1 = Quat()
                up_rot_1.setFromAxisAngleRad(up_dang_1, up_axis)
                up_dir_1 = unitv(up_rot_1.xform(up_dir))
            else:
                up_dir_1 = up_dir_t
        else:
            up_dir_1 = up_dir_t

        set_hpr_vfu(self.node, at_dir_1, up_dir_1)

        fov = self._fov
        fov_t = self._target_fov_eval()
        dfov_t = fov_t - fov
        fov_speed = dfov_t / self._fov_lag
        dfov_1 = fov_speed * dt
        if abs(dfov_1) < abs(dfov_t):
            fov_1 = fov + dfov_1
        else:
            fov_1 = fov_t
        self._fov = fov_1

        # Needed in base class.
        self.fov = fov_1
        vel = self._vel
        acc = (vel_1 - vel) / dt
        self._vel = vel_1
        self._acc = acc
        #angvel = self._ang_vel
        #angacc = (raxis * dang_1 - angvel * dt) / (0.5 * dt**2)
        #angvel_1 = angvel + angacc * dt
        #self._angvel = angvel_1
        #self._angacc = angacc


    def move_to (self, point=None, relto=None, rotrel=None,
                 atref=None, upref=None, lookrel=None, fov=None,
                 distlag=None, atlag=None, uplag=None, fovlag=None):

        update_target_pos = False
        update_target_look = False
        update_target_fov = False

        if point is not None:
            self._point = point
            update_target_pos = True
        if rotrel is not None:
            self._rotate_relative = rotrel
            update_target_pos = True
        if atref is not None:
            self._at_reference = atref
            update_target_look = True
        if upref is not None:
            self._up_reference = upref
            update_target_look = True
        if lookrel is not None:
            self._look_relative = lookrel
            update_target_look = True
        if relto is not None: # must come after rotrel/lookrel
            if relto is -1:
                relto = None
            self._referent_body = relto
            update_target_pos = True
            if self._look_relative:
                update_target_look = True
        if fov is not None:
            update_target_fov = True
        if distlag is not None:
            self._dist_lag = distlag
        else:
            self._dist_lag = self._default_dist_lag
        if atlag is not None:
            self._at_lag = atlag
        else:
            self._at_lag = self._default_at_lag
        if uplag is not None:
            self._up_lag = uplag
        else:
            self._up_lag = self._default_up_lag
        if fovlag is not None:
            self._fov_lag = fovlag
        else:
            self._fov_lag = self._default_fov_lag

        if update_target_pos:
            self._target_pos_eval = self._resolve_pos(
                self._point, self._rotate_relative, self._referent_body)
        if update_target_look:
            self._target_look_eval = self._resolve_look(
                self._at_reference, self._up_reference,
                self._look_relative, self._referent_body)
        if update_target_fov:
            self._target_fov_eval = lambda: fov

        self._restore_default_lag = True


    def _resolve_pos (self, point,
                      rotate_relative, referent_body):

        if referent_body is not None:
            if rotate_relative:
                def pos_eval ():
                    vel_b = referent_body.vel(self.parent)
                    pos_b = referent_body.pos(self.parent)
                    ang_vel_b = referent_body.angvel(self.parent)
                    pos_p = referent_body.pos(self.parent, point)
                    vel_p = vel_b + ang_vel_b.cross(pos_p - pos_b)
                    return pos_p, vel_p
            else:
                def pos_eval ():
                    pos_p = referent_body.pos(self.parent) + point
                    vel_p = referent_body.vel(self.parent)
                    return pos_p, vel_p
        else:
            def pos_eval ():
                pos_p = self.world.pos(self.parent, point)
                vel_p = Vec3()
                return pos_p, vel_p

        return pos_eval


    def _resolve_look (self, at_reference, up_reference,
                       look_relative, referent_body):

        if not look_relative:
            referent_body = None

        if isinstance(at_reference, Point3):
            if referent_body is not None:
                at_dir_f = lambda: unitv(self.parent.node.getRelativePoint(referent_body.node, at_reference) - self.node.getPos())
            else:
                at_dir_f = lambda: unitv(at_reference - self.node.getPos())
        elif isinstance(at_reference, Vec3):
            if referent_body is not None:
                at_dir_f = lambda: unitv(self.parent.node.getRelativeVector(referent_body.node, at_reference))
            else:
                at_dir_f = lambda: unitv(at_reference)
        elif isinstance(at_reference, NodePath):
            at_dir_f = lambda: unitv(at_reference.getPos(self.parent.node) - self.node.getPos())
        elif isinstance(at_reference, Body):
            at_dir_f = lambda: unitv(self.parent.node.getRelativePoint(at_reference.node, at_reference.center) - self.node.getPos())
        elif at_reference is None:
            at_dir_f = lambda: self.node.getQuat().getForward()
        else:
            raise StandardError("Unknown type of at-direction reference.")

        if isinstance(up_reference, Point3):
            if referent_body is not None:
                up_dir_f = lambda: unitv(self.parent.node.getRelativePoint(referent_body.node, uo_reference) - self.node.getPos())
            else:
                up_dir_f = lambda: unitv(up_reference - self.node.getPos())
        elif isinstance(up_reference, Vec3):
            if referent_body is not None:
                up_dir_f = lambda: unitv(self.parent.node.getRelativeVector(referent_body.node, up_reference))
            else:
                up_dir_f = lambda: unitv(up_reference)
        elif isinstance(up_reference, NodePath):
            up_dir_f = lambda: self.parent.node.getRelativeVector(up_reference.getParent(), up_reference.getQuat().getUp())
        elif isinstance(up_reference, Body):
            up_dir_f = lambda: self.parent.node.getRelativeVector(up_reference.node.getParent(), up_reference.node.getQuat().getUp())
        elif up_reference is None:
            up_dir_f = lambda: self.node.getQuat().getUp()
        else:
            raise StandardError("Unknown type of up-direction reference.")

        def eval_look ():
            at_dir = at_dir_f()
            up_dir = up_dir_f()
            up_dir = unitv(at_dir.cross(up_dir).cross(at_dir))
            return at_dir, up_dir

        return eval_look


    def auto_focus_point (self):
        # Base override.

        if isinstance(self._at_reference, Body):
            if self._at_reference.alive:
                return self._at_reference.pos()
        elif isinstance(self._at_reference, NodePath):
            if not self._at_reference.isEmpty():
                return self._at_reference.getPos(self.world.node)
        elif isinstance(self._at_reference, Point3):
            return Point3(self._at_reference)
        return None


    def is_attached_to (self, body):
        # Base override.

        return body is self._referent_body


class SwivelChaser (Chaser):
    """
    Chaser swiveling around an absolute or relative point
    to keep a point or a body in the center of view.
    """

    species = "swivel"

    def __init__ (self, world, point, radius, atref, upref,
                  relto=None, rotrel=False, plref=None,
                  fov=ANIMATION_FOV, remdelay=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - point (Point3): The fixing point around which the chaser swivels.
        - radius (float): The length of the swivel arm.
        - atref (Point3|NodePath|Body): Where should the chaser look at.
            It can be given as a a point, a node, or a body.
        - upref (Vec3|NodePath|Body): The upward direction for the chaser.
            It can be given directly as a direction (e.g. Vec3(0, 0, 1) for
            positive z-axis), or a node or a body whose up vector is going
            to be taken as the direction (e.g. same body as given with relto,
            or same body as given with atref).
        - relto (Body|NodePath): The parent body to which the swiveling point
            is relative to. If None, the fixing point is relative to world.
        - rotrel (bool): If the parent body is given by relto, whether
            the fixing point is relative to its rotated axes
            (otherwise only the distance is relative, and axes are world axes).
        - plref (Vec3): the normal to the plane in which the chaser swivels,
            for limiting the chaser to a plane instead to a sphere.
            If rotrel is True, this vector is relative to relto.
        - fov (float): Vertical FOV (in degrees).
        - remdelay (float): The number of seconds after the parent body
            (given by relto) dissapears when the chaser will remove itself.
            If not given, the chaser remains at last parent position
            indefinitely.
        - name (string): The name of the chaser.
        """

        if isinstance(relto, Body):
            parent = relto
        else:
            parent = world

        Chaser.__init__(self, world=world, fov=fov, parent=parent, name=name)

        self._point = point
        self._radius = radius
        self._atref = atref
        self._upref = upref
        self._relto = relto
        self._rotrel = rotrel
        self._plref = plref
        self._remdelay = remdelay

        self._time_to_remove = None

        self._center = None

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done

        if self._relto is not None and not self._relto.alive:
            self._point = self._relto_last_pos
            self._rotrel = False
            if self._relto is self.parent:
                self.parent = self.world
                self.node.wrtReparentTo(self.world.node)
            self._relto = None
            if self._remdelay is not None:
                self._time_to_remove = self._remdelay
            return task.done

        dt = self.world.dt
        if dt == 0.0:
            return task.cont

        if self._time_to_remove is not None:
            self._time_to_remove -= dt
            if self._time_to_remove <= 0.0:
                self.destroy()
                return task.done

        if ((isinstance(self._atref, Body) and not self._atref.alive) or
            (isinstance(self._atref, NodePath) and self._atref.isEmpty())):
            self._atref = self._atref_last_pos
        if ((isinstance(self._upref, Body) and not self._upref.alive) or
            (isinstance(self._upref, NodePath) and self._upref.isEmpty())):
            self._upref = self.quat(self.parent).getUp()

        if isinstance(self._atref, Body):
            self._atref_last_pos = self._atref.pos(self.world)
        elif isinstance(self._atref, NodePath):
            self._atref_last_pos = self._atref.getPos(self.world.node)

        if self._relto is not None and self._relto.alive:
            self._relto_last_pos = self._relto.pos(self.world)


        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        pos = self.pos(self.parent)
        quat = self.quat(self.parent)
        vel = self.vel(self.parent)
        angvel = self.angvel(self.parent)

        # Compute new swivel center position.
        if self._relto:
            if isinstance(self._relto, Body):
                if not self._relto.alive:
                    return
                if self._rotrel:
                    cpos = self._relto.pos(self.parent, self._point)
                else:
                    cpos = self._relto.pos(self.parent) + self._point
            elif isinstance(self._relto, NodePath):
                if self._relto.isEmpty():
                    return
                if self._rotrel:
                    cpos = self.parent.node.getRelativePoint(self._relto, self._point)
                else:
                    cpos = self._relto.getPos(self.parent.node) + self._point
            else:
                cpos = self.world.pos(self.parent, self._point)
        else:
            cpos = self.world.pos(self.parent, self._point)
        self._center = cpos

        # Compute new look reference position.
        if isinstance(self._atref, Body):
            if not self._atref.alive:
                return
            lpos = self._atref.pos(self.parent)
        elif isinstance(self._atref, NodePath):
            if self._atref.isEmpty():
                return
            lpos = self._atref.getPos(self.parent.node)
        else:
            lpos = self.world.pos(self.parent, self._atref)

        # Compute new up reference direction.
        if isinstance(self._upref, Body):
            if not self._upref.alive:
                return
            if self._rotrel:
                udir = self._upref.quat(self.parent).getUp()
            else:
                udir = self._upref.quat(self.world).getUp()
        elif isinstance(self._upref, NodePath):
            if self._upref.isEmpty():
                return
            if self._rotrel:
                udir = self._upref.getQuat(self.parent.node).getUp()
            else:
                udir = self._upref.getQuat(self.world.node).getUp()
        else:
            if self._rotrel:
                udir = Vec3(self._upref)
            else:
                udir = self.parent.node.getRelativeVector(self.world.node, Vec3(self._upref))

        # Compute new position.
        cpos = Point3(cpos)
        ldir = unitv(lpos - cpos)
        if self._plref is not None:
            rndir = unitv(self._plref)
            if self._rotrel:
                if isinstance(self._relto, Body):
                    ndir = self.parent.node.getRelativeVector(self._relto.node, rndir)
                elif isinstance(self._relto, NodePath):
                    ndir = self.parent.node.getRelativeVector(self._relto, rndir)
            else:
                ndir = rndir
            offp = -(ldir - ndir * ldir.dot(ndir)) * self._radius
        else:
            offp = -ldir * self._radius
        pos1 = cpos + offp
        self.node.setPos(pos1)

        # Compute new rotation.
        self.node.lookAt(lpos, udir)
        quat1 = self.node.getQuat()

        # Update kinematics.
        vel1 = (pos1 - pos) / dt
        acc = (vel1 - vel) / dt
        quat.normalize()
        axis = quat.getAxis(); ang = quat.getAngleRad()
        quat1.normalize()
        axis1 = quat1.getAxis(); ang1 = quat1.getAngleRad()
        angvel1 = (axis1 * ang1  - axis * ang) / dt
        angacc = (angvel1 - angvel) / dt

        # Needed in base class.
        self._vel = vel1
        self._acc = acc
        self._angvel = angvel1
        self._angacc = angacc


    def move_to (self, point=None, radius=None, atref=None, upref=None,
                 relto=None, rotrel=None):

        if point is not None:
            self._point = point
        if radius is not None:
            self._radius = radius
        if atref is not None:
            self._atref = atref
        if upref is not None:
            self._upref = upref
        if relto is not None:
            if isinstance(relto, World):
                self._relto = None
            else:
                self._relto = relto
        if rotrel is not None:
            self._rotrel = rotrel


    def auto_focus_point (self):
        # Base override.

        if isinstance(self._relto, Body):
            if self._relto.alive:
                return self._relto.pos()
        elif isinstance(self._relto, NodePath):
            if not self._relto.isEmpty():
                return self._relto.getPos(self.world.node)
        else:
            return self.parent.pos(offset=self._point)
        return None


    def is_attached_to (self, body):
        # Base override.

        return body is self._relto


class HeadChaser (Chaser):
    """
    Chaser fixed to a body which can turn and zoom.
    """

    species = "head"

    def __init__ (self, world,
                  fov=ANIMATION_FOV,
                  angspeed=radians(180.0), angacc=radians(720.0),
                  fovspeed=40.0, fovacc=160.0, # [deg*]
                  pos=Point3(), hpr=Vec3(),
                  parent=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - fov (float): Vertical FOV (in degrees).
        - angspeed (float): The maximum speed with which the chaser
            will rotate to new direction. If None, the chaser
            instantly jumps to new direction.
        - angacc (float): The acceleration which will be used for changes
            in angular speed. If None, the chaser instantly assumes
            maximum angular speed.
        - fovspeed (float): The maximum speed with which the chaser
            will zoom to new FOV (in degrees). If None, the chaser
            instantly jumps to new FOV.
        - fovacc (float): The acceleration which will be used for changes
            in zooming speed (in degrees). If None, the chaser instantly
            assumes maximum zooming speed.
        - pos (Point3): Position of the chaser relative to the parent.
        - hpr (Point3): Rotation of the chaser relative to the parent.
        - parent (Body): The body to which the chaser is fixed.
        - name (string): The name of the chaser.
        """

        Chaser.__init__(self, world=world, fov=fov,
                        pos=pos, hpr=hpr, parent=parent, name=name)

        self._base_pos = Point3(pos)
        self._base_hpr = Vec3(hpr)
        self._base_fov = fov

        self._pos_offset = Point3()
        self._hpr_offset = Vec3()
        self._fov_offset = 0.0

        self._ang_speed = angspeed
        self._ang_accel = angacc
        self._fov_speed = fovspeed
        self._fov_accel = fovacc

        self._default_ang_speed = angspeed
        self._default_ang_accel = angacc
        self._default_fov_speed = fovspeed
        self._default_fov_accel = fovacc

        self._target_at_dir = self._resolve_look(hprtovec(hpr))
        self._up_dir = self.node.getQuat().getUp()
        self._target_fov = lambda: fov

        self._curr_ang_speed = 0.0
        self._curr_fov_speed = 0.0
        self._prev_target_at_dir = None
        self._prev_target_fov = None

        self._restore_ang_speed_accel = False
        self._restore_fov_speed_accel = False

        # Read-only attributes.
        self.base_fov = self._base_fov

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if self.parent and not self.parent.alive:
            self.destroy()
            return task.done

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        pos_1 = self._base_pos + self._pos_offset
        self.node.setPos(pos_1)

        ang_eps = radians(1e-5)
        at_dir_t = self._target_at_dir()
        ang_speed_t = 0.0
        if self._prev_target_at_dir is not None:
            at_dir_tp = self._prev_target_at_dir
            raxis_t = at_dir_tp.cross(at_dir_t)
            dang_ls = asin(raxis_t.length())
            if abs(dang_ls) > ang_eps:
                raxis_t.normalize()
                dang_l = at_dir_tp.signedAngleRad(at_dir_t, raxis_t)
                ang_speed_t = dang_l / dt
                if self._ang_speed > 0.0:
                    ang_speed_t = clamp(ang_speed_t, -self._ang_speed, self._ang_speed)
        self._prev_target_at_dir = at_dir_t
        at_dir = hprtovec(self._base_hpr)
        raxis = at_dir.cross(at_dir_t)
        dang_ts = asin(raxis.length())
        if abs(dang_ts) > ang_eps:
            raxis.normalize()
            dang_t = at_dir.signedAngleRad(at_dir_t, raxis)
            ret = update_bounded(
                tvalue=dang_t,  tspeed=ang_speed_t,
                value=0.0, speed=self._curr_ang_speed,
                maxspeed=self._ang_speed, minaccel=self._ang_accel,
                dt=dt)
            dang_1, ang_speed_1 = ret
            if self._restore_ang_speed_accel and abs(dang_1 - dang_t) <= ang_eps:
                self._ang_speed = self._default_ang_speed
                self._ang_accel = self._default_ang_accel
                self._restore_ang_speed_accel = False
            rot = Quat()
            rot.setFromAxisAngleRad(dang_1, raxis)
            at_dir_1 = unitv(rot.xform(at_dir))
            set_hpr_vfu(self.node, at_dir_1, self._up_dir)
            self._base_hpr = self.node.getHpr()
            self._curr_ang_speed = ang_speed_1
        else:
            self._curr_ang_speed = 0.0
        hpr_1 = self._base_hpr + self._hpr_offset
        self.node.setHpr(hpr_1)

        fov_eps = 1e-3
        fov_t = self._target_fov()
        fov_speed_t = 0.0
        if self._prev_target_fov is not None:
            fov_tp = self._prev_target_fov
            if abs(fov_t - fov_tp) > fov_eps:
                dfov_l = fov_t - fov_tp
                fov_speed_t = dfov_l / dt
                if self._fov_speed > 0.0:
                    fov_speed_t = clamp(fov_speed_t, -self._fov_speed, self._fov_speed)
        self._prev_target_fov = fov_t
        if abs(self._base_fov - fov_t) > fov_eps:
            dfov_t = fov_t - self._base_fov
            ret = update_bounded(
                tvalue=dfov_t,  tspeed=fov_speed_t,
                value=0.0, speed=self._curr_fov_speed,
                maxspeed=self._fov_speed, minaccel=self._fov_accel,
                dt=dt)
            dfov_1, fov_speed_1 = ret
            if self._restore_fov_speed_accel and abs(dfov_1 - dfov_t) <= fov_eps:
                self._fov_speed = self._default_fov_speed
                self._fov_accel = self._default_fov_accel
                self._restore_fov_speed_accel = False
            self._base_fov += dfov_1
            self._curr_fov_speed = fov_speed_1
        else:
            self._curr_fov_speed = 0.0
        fov_1 = self._base_fov + self._fov_offset

        # Read-only attributes.
        self.fov = fov_1
        self.base_fov = self._base_fov

        ## Needed in base class.
        #pos = self.pos(self.parent)
        #vel = self.vel(self.parent)
        #angvel = self.angvel(self.parent)
        #acc = ((pos_1 - pos) - vel * dt) / (0.5 * dt**2)
        #vel_1 = vel + acc * dt
        #angacc = (raxis * dang_1 - angvel * dt) / (0.5 * dt**2)
        #angvel_1 = angvel + angacc * dt
        #self._vel = vel_1
        #self._acc = acc
        #self._angvel = angvel_1
        #self._angacc = angacc


    def move_to (self, atref=None, angspeed=None, angacc=None,
                 fov=None, fovspeed=None, fovacc=None):

        if atref is not None:
            self._target_at_dir = self._resolve_look(atref)
            self._prev_target_at_dir = None
        if angspeed is not None:
            self._ang_speed = angspeed
            self._restore_ang_speed_accel = True
        else:
            self._ang_speed = self._default_ang_speed
        if angacc is not None:
            self._ang_accel = angacc
            self._restore_ang_speed_accel = True
        else:
            self._ang_accel = self._default_ang_accel
        if fov is not None:
            self._target_fov = lambda: fov
            self._prev_target_fov = None
        if fovspeed is not None:
            self._fov_speed = fovspeed
            self._restore_fov_speed_accel = True
        else:
            self._fov_speed = self._default_fov_speed
        if fovacc is not None:
            self._fov_accel = fovacc
            self._restore_fov_speed_accel = True
        else:
            self._fov_accel = self._default_fov_accel


    def set_offset (self, dpos=None, dhpr=None, dfov=None):

        if dpos is not None:
            self._pos_offset = dpos
            self.node.setPos(self._base_pos + dpos)
        if dhpr is not None:
            self._hpr_offset = dhpr
            self.node.setHpr(self._base_hpr + dhpr)
        if dfov is not None:
            self._fov_offset = dfov

        # Needed in base class.
        self.fov = self._base_fov + dfov


    def _resolve_look (self, atref):

        relto = None
        if isinstance(atref, tuple):
            atref, relto = atref

        if isinstance(atref, Point3):
            if relto is not None:
                at_dir_f = lambda: unitv(self.parent.node.getRelativePoint(relto.node, atref) - self._pos)
            else:
                at_dir_f = lambda: unitv(atref - self._base_pos)
        elif isinstance(atref, Vec3):
            if relto is not None:
                at_dir_f = lambda: unitv(self.parent.node.getRelativeVector(relto.node, atref))
            else:
                at_dir_f = lambda: unitv(atref)
        elif isinstance(atref, NodePath):
            at_dir_f = lambda: unitv(atref.getPos(self.parent.node) - self._base_pos)
        elif isinstance(atref, Body):
            at_dir_f = lambda: unitv(self.parent.node.getRelativePoint(atref.node, atref.center) - self._base_pos)
        else:
            raise StandardError("Unknown type of direction reference.")
        return at_dir_f


    def auto_focus_point (self):

        return self.pos()


class FixedChaser (Chaser):
    """
    Chaser fixed to a body.
    """

    species = "fixed"

    def __init__ (self, world, fov=ANIMATION_FOV,
                  pos=Point3(), hpr=Vec3(), parent=None,
                  name=""):
        """
        Parameters:
        - world (World): The world.
        - fov (float): Vertical FOV (in degrees).
        - parent (Body): The body to which the chaser is fixed.
        - pos (Point3): Position of the chaser relative to the body.
        - hpr (Point3): Rotation of the chaser relative to the body.
        - name (string): The name of the chaser.
        """

        Chaser.__init__(self, world=world, fov=fov,
                        pos=pos, hpr=hpr, parent=parent, name=name)

        base.taskMgr.add(self._loop, "%s-%s-loop" % (self.family, self.species))


    def destroy (self):

        if not self.alive:
            return
        Body.destroy(self)


    def _loop (self, task):

        if not self.alive:
            return task.done
        if self.parent and not self.parent.alive:
            self.destroy()
            return task.done

        return task.cont


    def move (self, dt):
        # Base override.
        # Called by world at end of frame.

        pass


