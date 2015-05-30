# -*- coding: UTF-8 -*-

from math import radians, degrees, sqrt, pi, cos, tan, acos, atan2

from pandac.PandaModules import Vec2, Vec3, Point3
from pandac.PandaModules import NodePath

from src.core.misc import SimpleProps, unitv, clamp, intl01r, intl01v
from src.core.misc import uniform


EMISSION = SimpleProps(
    NONE="", # must evaluate to False
    RADIO="radio",
)

SIZEREF = SimpleProps(
    DIAG="diag",
    PROJAREA="projarea",
)


class Contact (object):

    def __init__ (self, body,
                  family=None, species=None, side=None,
                  ray=None, pos=None, vel=None, acc=None,
                  track=False, firsthand=False):

        self.world = body.world

        self.body = body

        self.family = family
        self.species = species
        self.side = side
        self.ray = ray
        self.pos = pos
        self.vel = vel
        self.acc = acc
        self.track = track
        self.firsthand = firsthand

        self.time = self.world.time


    def copy (self, other):

        if other.body is not self.body:
            raise StandardError(
                "Trying to copy contact data for different body.")

        self.family = other.family
        self.species = other.species
        self.side = other.side
        self.ray = other.ray
        self.pos = other.pos
        self.vel = other.vel
        self.acc = other.acc
        self.track = other.track
        self.firsthand = other.firsthand

        self.time = other.time


    def accumulate (self, other):

        if other.body is not self.body:
            raise StandardError(
                "Trying to accumulate contact data for different body.")

        if other.family is not None:
            self.family = other.family
        if other.species is not None:
            self.species = other.species
        if other.side is not None:
            self.side = other.side
        if other.ray is not None:
            self.ray = other.ray
        if other.pos is not None:
            self.pos = other.pos
        if other.vel is not None:
            self.vel = other.vel
        if other.acc is not None:
            self.acc = other.acc
        if other.track:
            self.track = True
        if other.firsthand:
            self.firsthand = True

        self.time = max(self.time, other.time)


    #def established (self):

        #return self.pos is not None or self.ray is not None


    def trackable (self):

        return self.track and self.pos is not None and self.body.alive


    def update_for_motion (self):

        if not self.body.alive:
            return

        if self.ray is not None:
            self.ray = (self.ray[0], unitv(self.body.pos() - self.ray[0]))
        if self.pos is not None:
            self.pos = self.body.pos()
        if self.vel is not None:
            self.vel = self.body.vel()
        if self.acc is not None:
            self.acc = self.body.acc()

        self.time = self.world.time


    def estimate_pos (self):

        pos1 = None
        if self.pos is not None:
            dtime = self.world.time - self.time
            if dtime > 0.0:
                pos1 = Point3(self.pos)
                if self.vel is not None:
                    pos1 += self.vel * dtime
                    if self.acc is not None:
                        pos1 += self.acc * (0.5 * dtime**2)
            else:
                pos1 = self.pos
        return pos1


    def estimate_vel (self):

        vel1 = None
        if self.vel is not None:
            if self.acc is not None:
                dtime = self.world.time - self.time
                if dtime > 0.0:
                    vel1 = self.vel + self.acc * dtime
            else:
                vel1 = self.vel
        return vel1


class SensorPack (object):

    def __init__ (self, parent,
                  scanperiod=1.0, relspfluct=0.1, maxtracked=1):

        self.world = parent.world
        self.parent = parent

        self._scan_period = scanperiod
        self._scan_period_fluct = scanperiod * relspfluct

        self._sensors = {}
        self._applied_sensors = []
        self._emissive_sensors = ()
        self._emissive_sensors_by_emtype = dict((t, ()) for t in EMISSION.values())
        #self._can_scan_families = set()
        self._req_scan_families = set()
        self._scan_families = ()

        self._test_bodies = []
        self._num_bodies_to_test = 0

        self._contacts = set()
        self._contacts_by_sensor = {}
        self._contacts_by_family = {}
        self._contacts_by_body = {}
        self._sensors_by_contact = {}
        self._new_contacts = set()
        self._new_contacts_by_sensor = {}
        self._new_contacts_by_family = {}
        self._new_contacts_by_body = {}
        self._new_sensors_by_contact = {}

        self._tracked_contacts = []
        self._max_tracked_contacts = maxtracked

        self.emissive = True

        self.alive = True
        # Should come before body loops.
        base.taskMgr.add(self._loop, "sensors-loop", sort=-1)


    def destroy (self):

        if not self.alive:
            return
        for sensor in self._sensors.itervalues():
            sensor.cleanup()
        self.alive = False


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done

        if not self._sensors:
            return task.cont

        for contact in self._tracked_contacts:
            contact.update_for_motion()

        if self._num_bodies_to_test == 0:
            self._test_bodies = self.world.select_bodies(self._scan_families, cache=True)
            self._num_bodies_to_test = len(self._test_bodies)

            self._contacts = self._new_contacts
            self._contacts_by_sensor = self._new_contacts_by_sensor
            self._contacts_by_family = self._new_contacts_by_family
            self._contacts_by_body = self._new_contacts_by_body
            self._sensors_by_contact = self._new_sensors_by_contact
            self._new_contacts = set()
            self._new_contacts_by_sensor = {}
            self._new_contacts_by_family = {}
            self._new_contacts_by_body = {}
            self._new_sensors_by_contact = {}

            pf = uniform(-self._scan_period_fluct, self._scan_period_fluct)
            scan_period = max(self._scan_period + pf, self.world.dt)
            self._scan_speed = self._num_bodies_to_test / scan_period
            self._scan_current = 0.0

            tracked_contacts = []
            for contact in self._tracked_contacts:
                if contact in self._contacts and contact.trackable():
                    tracked_contacts.append(contact)
            self._tracked_contacts = tracked_contacts

        scan_next = self._scan_current + self._scan_speed * self.world.dt
        for k in xrange(int(self._scan_current), int(scan_next)):
            if self._num_bodies_to_test == 0:
                break
            body = self._test_bodies[self._num_bodies_to_test - 1]
            self._num_bodies_to_test -= 1
            if not body.alive or body is self.parent:
                continue

            contact = None
            seen_by_sensors = set()
            for applied_sensors_1 in self._applied_sensors:
                for name, sensor in applied_sensors_1.iteritems():
                    tcontact = sensor.test(body)
                    if tcontact is not None:
                        contacts = self._new_contacts_by_sensor.get(name)
                        if contacts is None:
                            contacts = set()
                            self._new_contacts_by_sensor[name] = contacts
                        contacts.add(tcontact)
                        if contact is None:
                            contact = tcontact
                        else:
                            contact.accumulate(tcontact)
                        seen_by_sensors.add(name)

            if contact is not None:
                old_contact = self._contacts_by_body.get(contact.body)
                if old_contact:
                    old_contact.copy(contact)
                    contact = old_contact
                self._new_contacts.add(contact)

                contacts = self._new_contacts_by_family.get(contact.family)
                if contacts is None:
                    contacts = set()
                    self._new_contacts_by_family[contact.family] = contacts
                contacts.add(contact)
                self._new_contacts_by_body[contact.body] = contact

                for name in seen_by_sensors:
                    names = self._new_sensors_by_contact.get(contact)
                    if names is None:
                        names = set()
                        self._new_sensors_by_contact[contact] = names
                    names.add(name)

                expire = (self._scan_period + self._scan_period_fluct) * 1.5
                for applied_sensors_1 in self._applied_sensors:
                    for sensor in applied_sensors_1.itervalues():
                        sensor.note(contact, expire)

        self._scan_current = scan_next

        return task.cont


    def update (self, scanperiod=None, relspfluct=None, maxtracked=None):

        if scanperiod is not None:
            self._scan_period = scanperiod
        if relspfluct is not None:
            self._scan_period_fluct = self._scan_period * relspfluct
        if maxtracked is not None:
            self._max_tracked_contacts = maxtracked


    def add (self, sensor, name):

        if name in self._sensors:
            raise StandardError(
                "Trying to add a sensor with same name '%s' "
                "as previously added sensor." % name)
        self._sensors[name] = sensor
        #self._can_scan_families.update(sensor.dfamilies)
        if sensor.emissive:
            self._emissive_sensors += (sensor,)
            self._emissive_sensors_by_emtype[sensor.emissive] += (sensor,)
        self._update_for_sensor(name)


    def _update_for_sensor (self, name, sort=0):

        sensor = self._sensors[name]
        napp = len(self._applied_sensors)
        if sort >= napp:
            self._applied_sensors.extend({} for i in range(sort - napp + 1))
        applied_sensors_1 = self._applied_sensors[sort]
        if not sensor.emissive or self.emissive:
            sensor_families = sensor.dfamilies
            scan_families = set(self._scan_families)
            if self._req_scan_families is None:
                scan_families.update(sensor_families)
                applied_sensors_1[name] = sensor
            else:
                sel_families = self._req_scan_families.intersection(sensor_families)
                if sel_families:
                    scan_families.update(sel_families)
                    applied_sensors_1[name] = sensor
                elif name in applied_sensors_1:
                    applied_sensors_1.pop(name)
            self._scan_families = tuple(sorted(scan_families))


    def contacts (self):

        return self._contacts


    def contacts_by_body (self):

        return self._contacts_by_body


    def contacts_by_family (self):

        return self._contacts_by_family


    def contacts_by_sensor (self):

        return self._contacts_by_sensor


    def sensors (self):

        return self._sensors


    def sensors_by_contact (self):

        return self._sensors_by_contact


    def track (self, contact):

        if contact in self._contacts and contact.trackable():
            if len(self._tracked_contacts) >= self._max_tracked_contacts:
                self._tracked_contacts.pop(0)
            self._tracked_contacts.append(contact)


    def untrack (self, contact):

        if contact in self._tracked_contacts:
            self._tracked_contacts.remove(contact)


    def start_scanning (self, families=None):

        self._req_scan_families = None
        if families is not None:
            self._req_scan_families = frozenset(families)
        self._applied_sensors_pass_1 = {}
        self._applied_sensors_pass_2 = {}
        self._scan_families = ()
        for name in self._sensors:
            self._update_for_sensor(name)


    def scanning_families (self):

        return self._scan_families


    #def detectable_families (self):

        #return self._can_scan_families


    def set_emissive (self, active):

        self.emissive = bool(active)
        self.start_scanning(families=self._req_scan_families)


    def get_emitting (self, emtype=None):

        sensors = ()
        if self.emissive:
            if emtype is None:
                sensors = self._emissive_sensors
            else:
                sensors = self._emissive_sensors_by_emtype[emtype]
        return sensors


    def format_contacts (self):

        pconfmts = []
        for sname in sorted(self._sensors.keys()):
            cnames = [c.body.name for c in self._contacts_by_sensor.get(sname, ())]
            cfmt = "(%s)" % (", ".join(sorted(cnames)))
            pconfmts.append("%s=%s" % (sname, cfmt))
        confmt = "  ".join(pconfmts)

        return confmt


# NOTE: Sensor objects should only contain parameters and testing methods.
# Operation and state is handled by SensorPack.

class Sensor (object):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies):

        self.parent = parent
        self.world = parent.world

        self.dfamilies = frozenset(dfamilies)


    def cleanup (self):

        pass


    def test (self, body):

        return None


    def note (self, contact, expire):

        pass


    # For emissive sensors, the relative amount of emission
    # that the given body is receiving.
    # Equal to 1 for body on sensor's axis and at sensor's referent range.
    # Greater than 1 if body is closer, smaller than 1 if body is farther.
    # 0 if body is outside of the emission cone.
    def wash (self, body):

        return 0.0


class Radar (Sensor):

    emissive = EMISSION.RADIO

    def __init__ (self, parent, dfamilies,
                  refrange, downangle, upangle, topangle,
                  hpr=Vec3(), subnode=None):

        Sensor.__init__(self, parent, dfamilies)

        self.refrange = refrange
        self.downangle = downangle
        self.upangle = upangle
        self.topangle = topangle

        pnode = subnode if subnode is not None else parent.node
        self._platform = pnode.attachNewNode("radar-platform")
        self._platform.setHpr(hpr)
        self._ref_range = refrange
        self._down_angle = downangle
        self._up_angle = upangle
        self._top_angle = topangle


    def cleanup (self):

        self._platform.removeNode()
        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies) or self.parent.jammed:
            return contact
        rbpos = body.node.getPos(self._platform)
        detrange = self.detection_range(rcs=body.rcs)
        bdist = rbpos.length()
        if bdist < detrange and self.inside_angles(rbpos):
            acc = body.acc() if bdist < 0.2 * detrange else None
            contact = Contact(body=body,
                              family=body.family,
                              species=body.species,
                              side=body.side,
                              pos=body.pos(),
                              vel=body.vel(),
                              acc=acc,
                              track=True,
                              firsthand=True)
        return contact


    _refrcs = 5.0
    # ...of a medium-size non-stealth fighter.

    def detection_range (self, rcs):

        detrange = self._ref_range

        # Correct for emission-reflection scatter.
        rcsfac = (rcs / Radar._refrcs)**0.25
        detrange *= rcsfac

        return detrange


    def inside_angles (self, rbpos):

        inside = False
        bx, by, bz = rbpos[0], rbpos[1], rbpos[2]
        top_angle = atan2(abs(bx), by)
        if top_angle <= self._top_angle:
            updw_angle = atan2(bz, sqrt(bx**2 + by**2))
            inside = (-self._down_angle <= updw_angle <= self._up_angle)
        return inside


    def wash (self, body):

        rbpos = body.node.getPos(self._platform)
        if self.inside_angles(rbpos):
            # Correct for emission scatter.
            bdist = rbpos.length()
            wfac = (self._ref_range / max(bdist, 1e-3))**2
        else:
            wfac = 0.0
        return wfac


class Irst (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies,
                  refrange, downangle, upangle, topangle,
                  hpr=Vec3(), subnode=None):

        Sensor.__init__(self, parent, dfamilies)

        self.refrange = refrange
        self.downangle = downangle
        self.upangle = upangle
        self.topangle = topangle

        pnode = subnode if subnode is not None else parent.node
        self._platform = pnode.attachNewNode("irst-platform")
        self._platform.setHpr(hpr)
        self._ref_range = refrange
        self._down_angle = downangle
        self._up_angle = upangle
        self._top_angle = topangle


    def cleanup (self):

        self._platform.removeNode()


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact
        rbhpr = body.node.getHpr(self._platform)
        detrange = self.detection_range(ireqpower=body.ireqpower,
                                        iraspect=body.iraspect,
                                        hpr=rbhpr)
        rbpos = body.node.getPos(self._platform)
        bdist = rbpos.length()
        if bdist < detrange and self.inside_angles(rbpos):
            acc = body.acc() if bdist < 0.2 * detrange else None
            contact = Contact(body=body,
                              family=body.family,
                              pos=body.pos(),
                              vel=body.vel(),
                              acc=acc,
                              track=True,
                              firsthand=True)
        return contact


    _refireqpower = 250.0 * 40e3
     # ...of fighter flying 250 m/s with 40 kN thrust.

    def detection_range (self, ireqpower, iraspect, hpr):

        detrange = self._ref_range

        # Correct for emission power.
        pwrfac = sqrt(ireqpower / Irst._refireqpower)
        detrange *= pwrfac

        # Correct for emission aspect.
        hdg, pch = hpr[0], hpr[1]
        aspfac = 1.0 + iraspect * (1.0 - (abs(hdg) / 90.0)) * (1.0 - abs(pch) / 90.0)
        detrange *= aspfac

        #if mon:
            #print "--irst-detrng", pwrfac, hdg, pch, aspfac, pwrfac * aspfac, detrange
        return detrange


    def inside_angles (self, rbpos):

        inside = False
        bx, by, bz = rbpos[0], rbpos[1], rbpos[2]
        top_angle = atan2(abs(bx), by)
        if top_angle <= self._top_angle:
            updw_angle = atan2(bz, sqrt(bx**2 + by**2))
            inside = (-self._down_angle <= updw_angle <= self._up_angle)
        return inside


class Visual (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies,
                  refsizetype=SIZEREF.DIAG, relsight=1.0, considersun=False,
                  subnode=None):

        Sensor.__init__(self, parent, dfamilies)

        self._pnode = subnode if subnode is not None else parent.node
        self._rel_sight = relsight
        self._consider_sun = considersun
        self._ref_size_type = refsizetype


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact

        rbpos = body.node.getPos(self._pnode)
        rbdir = unitv(rbpos)

        if self._ref_size_type == SIZEREF.DIAG:
            refsize = body.bboxdiag
        elif self._ref_size_type == SIZEREF.PROJAREA:
            refsize = body.project_bbox_area(rbdir, refbody=self.parent)
        if self._consider_sun:
            psdir = self._pnode.getRelativeVector(self.world.node, self.world.sky.sun_dir)
            offsun = acos(clamp(psdir.dot(rbdir), -1.0, 1.0))
            detrange = self.detection_range(refsize=refsize, offsun=offsun)
        else:
            detrange = self.detection_range(refsize=refsize)

        bdist = rbpos.length()
        if bdist <= detrange and self.inside_angles(rbpos):
            acc = body.acc() if bdist < 0.5 * detrange else None
            side = body.side if bdist < 0.8 * detrange else None
            species = body.species if bdist < 0.8 * detrange else None
            contact = Contact(body=body,
                              family=body.family,
                              species=species,
                              side=side,
                              pos=body.pos(),
                              vel=body.vel(),
                              acc=acc,
                              firsthand=True)

        #if self.parent.name == "red1":
            #print ("--vis-30  self=%s  other=%s  "
                   #"detrange=%.0f  dist=%.0f  contact=%s  "
                   #% (self.parent.name, body.name,
                      #detrange, bdist, bool(contact)))
        return contact


    def inside_angles (self, rbpos):

        return True


    _refdetrange = 15e3
    _refdiaglen = 20.0
    _refprojarea = 200.0
    # ...of a medium-size fighter.
    _refinoffsun = radians(5.0)
    _refoutoffsun = radians(25.0)

    def detection_range (self, refsize, offsun=None):

        detrange = Visual._refdetrange

        # Correct for size.
        if self._ref_size_type == SIZEREF.DIAG:
            sizefac = refsize / Visual._refdiaglen
        elif self._ref_size_type == SIZEREF.PROJAREA:
            sizefac = sqrt(refsize / Visual._refprojarea)
        detrange *= sizefac

        # Correct for visibility.
        relvis = self.world.sky.relative_visibility
        if offsun is not None and offsun < Visual._refoutoffsun:
            sunfac = intl01r(offsun, Visual._refinoffsun, Visual._refoutoffsun)
            relvis *= intl01v(self.world.sky.sun_strength, 1.0, sunfac)
        detrange *= relvis

        # Correct for sight accuity.
        detrange *= self._rel_sight

        return detrange


class FighterVisual (Visual):

    def __init__ (self, parent, dfamilies,
                  frontangle, rearangle, sideangle,
                  refsizetype=SIZEREF.DIAG, relsight=1.0, considersun=False,
                  subnode=None):

        Visual.__init__(self, parent=parent, dfamilies=dfamilies,
                        refsizetype=refsizetype, relsight=relsight,
                        considersun=considersun, subnode=subnode)

        self._tan_compfront_angle = tan(0.5 * pi - frontangle)
        self._tan_comprear_angle = tan(0.5 * pi - rearangle)
        self._side_angle = sideangle


    def inside_angles (self, rbpos):

        bx, by, bz = rbpos[0], rbpos[1], rbpos[2]
        if by > 0.0: # front hemisphere
            pz = by * self._tan_compfront_angle
        else: # rear hemisphere
            pz = -by * self._tan_comprear_angle
        side_angle = atan2(abs(bx), bz - pz)
        inside = (side_angle <= self._side_angle)
        return inside


class TransportVisual (Visual):

    def __init__ (self, parent, dfamilies,
                  downangle, upangle, topangle,
                  refsizetype=SIZEREF.DIAG, relsight=1.0, considersun=False,
                  subnode=None):

        Visual.__init__(self, parent=parent, dfamilies=dfamilies,
                        refsizetype=refsizetype, relsight=relsight,
                        considersun=considersun, subnode=subnode)

        self._down_angle = downangle
        self._up_angle = upangle
        self._top_angle = topangle


    def inside_angles (self, rbpos):

        inside = False
        bx, by, bz = rbpos[0], rbpos[1], rbpos[2]
        top_angle = atan2(abs(bx), by)
        if top_angle <= self._top_angle:
            updw_angle = atan2(bz, sqrt(bx**2 + by**2))
            inside = (-self._down_angle <= updw_angle <= self._up_angle)
        return inside


class Tv (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies,
                  refrange, minupangle, maxupangle, topangle,
                  refsizetype=SIZEREF.DIAG, subnode=None):

        Sensor.__init__(self, parent, dfamilies)

        self._pnode = subnode if subnode is not None else parent.node
        self._ref_range = refrange
        self._ref_size_type = refsizetype
        self._min_up_angle = minupangle
        self._max_up_angle = maxupangle
        self._top_angle = topangle


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact

        rbpos = body.node.getPos(self._pnode)
        if self._ref_size_type == SIZEREF.DIAG:
            refsize = body.bboxdiag
        elif self._ref_size_type == SIZEREF.PROJAREA:
            rbdir = unitv(rbpos)
            refsize = body.project_bbox_area(rbdir, refbody=self.parent)
        detrange = self.detection_range(refsize=refsize)

        bdist = rbpos.length()
        if bdist <= detrange:
            bx, by, bz = rbpos[0], rbpos[1], rbpos[2]
            top_angle = atan2(abs(bx), by)
            if top_angle <= self._top_angle:
                updw_angle = atan2(bz, sqrt(bx**2 + by**2))
                if self._min_up_angle <= updw_angle <= self._max_up_angle:
                    contact = Contact(body=body,
                                      family=body.family,
                                      species=body.species,
                                      side=body.side,
                                      pos=body.pos(),
                                      vel=body.vel(),
                                      track=True,
                                      firsthand=True)

        #if self.parent.name == "red1":
            #print ("--tv-30  self=%s  other=%s  "
                   #"detrange=%.0f  dist=%.0f  contact=%s  "
                   #% (self.parent.name, body.name,
                      #detrange, bdist, bool(contact)))
        return contact


    _refdiaglen = 8.0
    _refprojarea = 28.0
    # ...of an MBT.

    def detection_range (self, refsize):

        detrange = self._ref_range

        # Correct for size.
        if self._ref_size_type == SIZEREF.DIAG:
            sizefac = refsize / Tv._refdiaglen
        elif self._ref_size_type == SIZEREF.PROJAREA:
            sizefac = sqrt(refsize / Tv._refprojarea)
        detrange *= sizefac

        # Correct for maximum range.
        detrange = min(detrange, self._ref_range * 3.0)

        # Correct for ground clutter and blending.
        if detrange > 0.0:
            gcbfac = (self._ref_range / detrange)**0.5
            detrange *= gcbfac

        return detrange


class Rwr (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies, minwash=1.0):

        Sensor.__init__(self, parent, dfamilies)

        self._min_wash = minwash


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies and
                body.sensorpack is not None):
            return contact

        sensors = body.sensorpack.get_emitting(emtype=EMISSION.RADIO)
        wash = 0.0
        for sensor in sensors:
            wash = sensor.wash(self.parent)
            if wash > self._min_wash:
                ppos = self.parent.pos()
                ray = (ppos, unitv(body.pos() - ppos))
                contact = Contact(body=body,
                                  family=body.family,
                                  side=body.side, # by radar fingerprint
                                  ray=ray,
                                  firsthand=True)
                break

        #if self.parent.name == "red1":
            #print ("--rwr-30  self=%s  other=%s  "
                   #"wash=%.2f  contact=%s  "
                   #% (self.parent.name, body.name,
                      #wash, bool(contact)))
        return contact


class CollisionWarning (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies,
                  insidedist, insidetime):

        Sensor.__init__(self, parent, dfamilies)

        self._inside_dist = insidedist
        self._inside_time = insidetime


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact

        body1 = self.parent
        body2 = body

        # Compute nearest approach assuming constant velocity.
        dpos = body2.pos() - body1.pos()
        dvel = body2.vel() - body1.vel()
        dpos_dot_dvel = dpos.dot(dvel)
        time_to_nearest = - dpos.dot(dvel) / max(dvel.dot(dvel), 1e-6)
        if 0.0 < time_to_nearest < self._inside_time:
            nearest_dist = (dpos + dvel * time_to_nearest).length()
            body2_radius = body2.bboxdiag * 0.5
            if nearest_dist - body2_radius < self._inside_dist:
                # Collision imminent.
                # Check whether detection sensor sees the contact.
                contact = self.detect(body)

        return contact


    def detect (self, body):

        contact = Contact(body=body,
                          family=body.family,
                          pos=body.pos(),
                          vel=body.vel(),
                          firsthand=True)
        return contact


class FighterVisualCollisionWarning (CollisionWarning):

    def __init__ (self, parent, dfamilies,
                  insidedist, insidetime, frontangle, rearangle, sideangle,
                  refsizetype=SIZEREF.DIAG, relsight=1.0, considersun=False):

        CollisionWarning.__init__(self, parent=parent, dfamilies=dfamilies,
                                  insidedist=insidedist, insidetime=insidetime)

        sensor = FighterVisual(parent=parent, dfamilies=dfamilies,
                               frontangle=frontangle, rearangle=rearangle,
                               sideangle=sideangle,
                               refsizetype=refsizetype, relsight=relsight,
                               considersun=considersun)
        self._detection_sensor = sensor


    def cleanup (self):

        self._detection_sensor.cleanup()
        CollisionWarning.cleanup(self)


    def detect (self, body):

        return self._detection_sensor.test(body)


class TransportVisualCollisionWarning (CollisionWarning):

    def __init__ (self, parent, dfamilies,
                  insidedist, insidetime, downangle, upangle, topangle,
                  refsizetype=SIZEREF.DIAG, relsight=1.0, considersun=False):

        CollisionWarning.__init__(self, parent=parent, dfamilies=dfamilies,
                                  insidedist=insidedist, insidetime=insidetime)

        sensor = TransportVisual(parent=parent, dfamilies=dfamilies,
                                 downangle=downangle, upangle=upangle,
                                 topangle=topangle,
                                 refsizetype=refsizetype, relsight=relsight,
                                 considersun=considersun)
        self._detection_sensor = sensor


    def cleanup (self):

        self._detection_sensor.cleanup()
        CollisionWarning.cleanup(self)


    def detect (self, body):

        return self._detection_sensor.test(body)


class DataLink (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies, sfamilies, canrecv, cansend):

        Sensor.__init__(self, parent, dfamilies=dfamilies)

        self._sfamilies = frozenset(sfamilies)
        self._can_recv = canrecv
        self._can_send = cansend

        self._side_tag = DataLink.side_tag(self.parent.side)
        self._name_tag = DataLink.name_tag(self.parent.name)
        self._recv_tags = (self._side_tag, self._name_tag)


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (self._can_recv and body.alive and body.family in self.dfamilies):
            return contact

        for tag in self._recv_tags:
            bodies = self.world.tagged_bodies(tag=tag)
            if body in bodies:
                ocontact = self.world.tagged_body_info(tag=tag, body=body)
                if ocontact is not None:
                    contact = Contact(body=body)
                    contact.copy(ocontact)
                    contact.firsthand = False
                    break

        return contact


    def note (self, contact, expire):

        if (contact.firsthand and self._can_send and contact.trackable() and
            contact.family in self._sfamilies):
            ocontact = self.world.tagged_body_info(tag=self._side_tag,
                                                   body=contact.body)
            if ocontact is None:
                ocontact = Contact(contact.body)
                ocontact.copy(contact)
                ocontact.firsthand = False
            else:
                ocontact.accumulate(contact)
            self.world.tag_body(tag=self._side_tag, body=contact.body,
                                info=ocontact, expire=expire)


    @staticmethod
    def side_tag (side):

        return "contacts-datalink-side-%s" % side


    @staticmethod
    def name_tag (name):

        return "contacts-datalink-name-%s" % name


class Comm (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies):

        Sensor.__init__(self, parent, dfamilies)

        self._comm_tag = "contacts-comm-side-%s" % self.parent.side


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact

        bodies = self.world.tagged_bodies(tag=self._comm_tag)
        if body in bodies:
            ocontact = self.world.tagged_body_info(tag=self._comm_tag, body=body)
            if ocontact is not None:
                contact = Contact(body=body)
                contact.copy(ocontact)
                contact.firsthand = False

        return contact


    def note (self, contact, expire):

        if contact.firsthand:
            ocontact = self.world.tagged_body_info(tag=self._comm_tag,
                                                   body=contact.body)
            if ocontact is None:
                ocontact = Contact(contact.body)
                ocontact.copy(contact)
            else:
                ocontact.accumulate(contact)
            ocontact.acc = None
            ocontact.track = False
            ocontact.firsthand = False
            self.world.tag_body(tag=self._comm_tag, body=contact.body,
                                info=ocontact, expire=expire)


class MagicTargeted (Sensor):

    emissive = EMISSION.NONE

    def __init__ (self, parent, dfamilies):

        Sensor.__init__(self, parent, dfamilies)


    def cleanup (self):

        Sensor.cleanup(self)


    def test (self, body):

        contact = None
        if not (body.alive and body.family in self.dfamilies):
            return contact

        if body.target is self.parent:
            ppos = self.parent.pos()
            ray = (ppos, unitv(body.pos() - ppos))
            contact = Contact(body=body,
                              family=body.family,
                              ray=ray)

        return contact


