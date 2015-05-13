# -*- coding: UTF-8 -*-

from math import degrees, pi, acos

from pandac.PandaModules import VBase2, VBase3, Vec3, Vec4, Point2, Point3, Quat
from pandac.PandaModules import NodePath
from pandac.PandaModules import CollisionNode
from pandac.PandaModules import CollisionSphere, CollisionSegment, CollisionBox

from src.core.debris import Debris, FlowDebris
from src.core.fire import MuzzleFlash
from src.core.light import AutoPointLight
from src.core.misc import rgba, sign, next_pos, next_quat
from src.core.misc import load_model, load_model_lod_chain, extract_model_lod_chain
from src.core.misc import report, dbgval
from src.core.sensor import SensorPack
from src.core.shader import make_shader, SHADOWBLUR
from src.core.transl import *


class Body (object):

    def __init__ (self, world,
                  family, species, hitforce,
                  name, side,
                  mass=None,
                  pos=Point3(), hpr=Vec3(),
                  vel=Vec3(), angvel=Vec3(),
                  acc=Vec3(), angacc=Vec3(),
                  modeldata=None,
                  hitboxdata=[], hitboxcritdata=[],
                  hitinto=True, hitfrom=True,
                  sensordata=None,
                  center=None, bbox=None, bboxcenter=None,
                  hitlight=None, hitdebris=None, hitflash=None,
                  passhitfx=False,
                  amblit=False, dirlit=False, pntlit=0, fogblend=False,
                  obright=False, ltrefl=False,
                  shdshow=False, shdmodind=None,
                  parent=None):

        self.alive = True

        self.world = world
        self.family = family
        self.species = species
        self.name = name
        self.side = side
        self.parent = parent or world
        self.mass = mass
        self.hitforce = hitforce
        self.hitlight = hitlight
        self.hitdebris = hitdebris
        self.hitflash = hitflash
        self.passhitfx = passhitfx

        self.racc = Vec3()
        self.aacc = Vec3()
        self.rangacc = Vec3()
        self.aangacc = Vec3()

        if isinstance(vel, (float, int)):
            q = Quat()
            q.setHpr(hpr)
            vel = q.xform(Vec3(0, vel, 0))

        self._acc = Vec3(acc)
        self._angacc = Vec3(angacc)
        self._vel = Vec3(vel)
        self._prev_vel = Vec3(vel)
        self._angvel = Vec3(angvel)
        self._prev_angvel = Vec3(angvel)

        self.birth_time = world.time

        self.initiator = None

        arg_bbox = bbox
        arg_bboxcenter = bboxcenter

        self.node = self.parent.node.attachNewNode(self.name)
        if modeldata and modeldata.path:
            if ltrefl:
                glossmap = modeldata.glossmap
                if not glossmap:
                    glossmap = "images/_glossmap_none.png"
            else:
                glossmap = None
            if isinstance(modeldata.glowmap, Vec4):
                glowcol = modeldata.glowmap
                glowmap = None
            else:
                glowcol = None
                glowmap = modeldata.glowmap
            if modeldata.clamp is not None:
                clamp = modeldata.clamp
            else:
                clamp = True
            shadowmap = base.world_shadow_texture if shdshow else None
            if isinstance(modeldata.path, (tuple, list)):
                if (len(modeldata.path) == 2 and
                    isinstance(modeldata.path[0], NodePath) and
                    isinstance(modeldata.path[1], str)):
                    pnode, tname = modeldata.path
                    ret = extract_model_lod_chain(pnode, tname,
                        texture=modeldata.texture, normalmap=modeldata.normalmap,
                        glowmap=glowmap, glossmap=glossmap,
                        shadowmap=shadowmap,
                        clamp=clamp)
                    lnode, models, fardists, bbox, bcen, ppos, phpr = ret
                    if pos is None:
                        pos = ppos
                    if hpr is None:
                        hpr = phpr
                    for model in models:
                        model.setPos(Point3())
                        model.setHpr(Vec3())
                else:
                    ret = load_model_lod_chain(
                        world.vfov, modeldata.path,
                        texture=modeldata.texture, normalmap=modeldata.normalmap,
                        glowmap=glowmap, glossmap=glossmap,
                        shadowmap=shadowmap,
                        clamp=clamp, scale=modeldata.scale,
                        pos=modeldata.offset, hpr=modeldata.rot)
                    lnode, models, fardists, bbox, bcen = ret
                self.modelnode = lnode
                self.models = models
                self.fardists = fardists
                self.bbox = bbox
                self.bboxcenter = bcen
                lnode.reparentTo(self.node)
            else:
                model = load_model(
                    modeldata.path,
                    texture=modeldata.texture, normalmap=modeldata.normalmap,
                    glowmap=glowmap, glossmap=glossmap,
                    shadowmap=shadowmap,
                    clamp=clamp, scale=modeldata.scale,
                    pos=modeldata.offset, hpr=modeldata.rot)
                self.modelnode = model
                self.models = [model]
                self.fardists = [-1.0]
                model.reparentTo(self.node)
                if not modeldata.nobbox:
                    bmin, bmax = model.getTightBounds()
                    self.bbox = bmax - bmin
                    self.bboxcenter = (bmin + bmax) * 0.5
                else:
                    self.bbox = Vec3()
                    self.bboxcenter = Vec3()
        else:
            self.modelnode = None
            self.models = []
            self.fardists = []
            self.bbox = Vec3()
            self.bboxcenter = Vec3()
        if arg_bbox is not None:
            self.bbox = arg_bbox
            if arg_bboxcenter is not None:
                self.bboxcenter = arg_bboxcenter
            else:
                self.bboxcenter = Vec3()
        elif arg_bboxcenter is not None:
            self.bboxcenter = arg_bboxcenter
        self.update_bbox(bbox=self.bbox, bboxcenter=self.bboxcenter)
        self.node.setPos(pos)
        self.node.setHpr(hpr)

        self.hitboxes = []
        self.set_hitboxes(hitboxdata, hitboxcritdata, hitinto, hitfrom)
        #for hbx in self.hitboxes:
            #hbx.cnode.show()
        self.inert_collide = False
        self.hits_critical = False

        if center is not None:
            self.center = center
        elif self.hitboxes:
            self.center = Point3()
            volume = 0.0
            for hbx in self.hitboxes:
                self.center += hbx.center * hbx.volume
                volume += hbx.volume
            self.center /= volume
        else:
            self.center = self.bboxcenter

        if self.hitlight:
            self._init_hitlight()
        if self.hitdebris:
            self._init_hitdebris()
        if self.hitflash:
            self._init_hitflash()

        # Before shader is set.
        if base.with_world_shadows:
            if modeldata and modeldata.shadowpath:
                model = load_model(
                    modeldata.shadowpath,
                    scale=modeldata.scale,
                    pos=modeldata.offset, hpr=modeldata.rot)
                model.reparentTo(world.shadow_node)
                self.shadow_node = model
            elif self.models and shdmodind is not None:
                model = self.models[shdmodind]
                self.shadow_node = model.copyTo(world.shadow_node)
            else:
                self.shadow_node = None

        if self.models:
            shdinp = world.shdinp
            ambln = shdinp.ambln if amblit else None
            dirlns = shdinp.dirlns if dirlit else []
            #pntlit = 0
            pntlns = shdinp.pntlns[:pntlit]
            fogn = shdinp.fogn if fogblend else None
            camn = shdinp.camn
            pntobrn = shdinp.pntobrn if obright else None
            normal = modeldata.normalmap is not None
            gloss = ltrefl
            glow = glowcol if glowcol is not None else (glowmap is not None)
            shadowrefn = shdinp.shadowrefn if shdshow else None
            shadowdirlin = shdinp.shadowdirlin if shdshow else None
            shadowblendn = shdinp.shadowblendn if shdshow else None
            shadowpush = 0.003 if shdshow else None
            shadowblur = SHADOWBLUR.NONE if shdshow else None
            showas = False
            #showas = "%s-shader" % (self.family)
            ret = make_shader(
                ambln=ambln, dirlns=dirlns, pntlns=pntlns,
                fogn=fogn, camn=camn, pntobrn=pntobrn,
                normal=normal, gloss=gloss, glow=glow,
                shadowrefn=shadowrefn, shadowdirlin=shadowdirlin,
                shadowblendn=shadowblendn, shadowpush=shadowpush,
                shadowblur=shadowblur,
                showas=showas, getargs=True)
            self.shader, self.shader_kwargs = ret
            self.modelnode.setShader(self.shader)
        self.pntlit = pntlit

        if sensordata is not None:
            self.sensorpack = SensorPack(parent=self,
                                         scanperiod=sensordata.scanperiod,
                                         relspfluct=sensordata.relspfluct,
                                         maxtracked=sensordata.maxtracked)
        else:
            self.sensorpack = None

        self.shotdown = False
        self.retreating = False
        self.outofbattle = False
        self.controlout = False

        self._last_collide_body = None
        self._recorded_as_kill = False

        if not base.with_sound_doppler:
            self.ignore_flyby = 0

        world.register_body(self)

        base.taskMgr.add(self._loop_fx, "body-effects-%s" % self.name)


    def destroy (self):

        if not self.alive:
            return
        self.alive = False
        self.outofbattle = True


    def cleanup (self):

        if self.alive:
            self.destroy()

        for hbx in self.hitboxes:
            hbx.destroy()
        if self.hitdebris:
            self._hitdb.destroy()
        if self.sensorpack is not None:
            self.sensorpack.destroy()
        if self.hitflash:
            self._hitfl.destroy()
        if base.with_world_shadows and self.shadow_node is not None:
            self.shadow_node.removeNode()
        self.node.removeNode()


    def set_hitboxes (self, hitboxdata, hitboxcritdata=None,
                      hitinto=True, hitfrom=True):

        # Remove any old hitboxes.
        for hbx in self.hitboxes:
            self.__dict__[self._name_to_attr(hbx.name)] = None
            hbx.destroy()

        self.hitboxes = []
        self.hitboxmap = {}
        for hbxd, critical in ((hitboxdata, False), (hitboxcritdata, True)):
            if hbxd:
                if isinstance(hbxd, HitboxData):
                    hbxd = [hbxd]
                elif (isinstance(hbxd, (tuple, list)) and
                    isinstance(hbxd[0], tuple)):
                    name = "crit" if critical else "main"
                    hbxd = [HitboxData(name=name, colldata=hbxd)]
            else:
                hbxd = []
            for hbxd1 in hbxd:
                hbx = Hitbox(self, hbxd1, hitinto, hitfrom, critical)
                self.hitboxes.append(hbx)
                self.hitboxmap[hbx.name] = hbx
                self.__dict__[self._name_to_attr(hbx.name)] = hbx


    def _name_to_attr (self, name):

        return "_hbx_%s" % name.replace("-", "_")


    def collide (self, obody, chbx, cpos, silent=False):

        if self.hitflash:
            self._hitfl_time = self.world.time
            self._hitfl.active = True
            self._hitfl.node.setPos(cpos)
            if hasattr(obody, "caliber"):
                sfac = (obody.caliber / self._hitfl_ref_caliber)**1.0
                self._hitfl.update(scale=(self._hitfl_scale * sfac))

        if obody.passhitfx:
            # Do not use cpos, may be zero for some collision types.
            opos = obody.pos(self)
            if self.hitlight:
                self._hitlt_cscale = 1.0
                self._hitlt.update(color=self._hitlt_color, pos=opos)
            if self.hitdebris:
                #createf = lambda: Debris(
                            #world=self.world, pnode=self.node, pos=opos,
                            #firetex=self.hitdebris.firetex,
                            #smoketex=self.hitdebris.smoketex,
                            #debristex=self.hitdebris.debristex,
                            #sizefac=1.0, timefac=1.0, amplfac=1.0)
                #isdonef = lambda db: not db.alive
                #self.world.single_action(self.node, "hitdebris", createf, isdonef)
                self._hitdb.node.setPos(opos)
                self._hitdb.duration = 0.2
            if self.hitflash:
                self._hitfl.node.setPos(opos)

        inert = (self.inert_collide or
                 (chbx.critical and not obody.hits_critical))
        if not silent:
            dbgval(1, "%s-hit" % self.family,
                   (self.world.time, "%.2f", "time", "s"),
                   ("%s(%s)" % (self.name, self.species), "%s", "into"),
                   ("%s(%s)" % (obody.name, obody.species), "%s", "from"),
                   (obody.hitforce, "%.1f", "force"),
                   (chbx.name, "%s", "hitbox"),
                   (inert, "%s", "inert"))
        if not inert:
            self._last_collide_body = obody
        return inert


    def _init_hitlight (self):

        self._hitlt_color = self.hitlight.color or (rgba(255, 235, 140, 0.0) * 2)
        self._hitlt_radmin = self.hitlight.radmin or 0.5
        self._hitlt_radmax = self.hitlight.radmax or 4.0
        self._hitlt_cspeed = self.hitlight.cspeed or 8.0

        self._hitlt = AutoPointLight(
            parent=self, color=Vec4(),
            radius=self._hitlt_radmax, halfat=0.8,
            name="hitlight")
        self._hitlt_drad = self._hitlt_radmax - self._hitlt_radmin
        self._hitlt_cscale = 0.0


    def _init_hitdebris (self):

        self._hitdb = FlowDebris(
            world=self.world, pnode=self.node, pos=Point3(),
            firetex=self.hitdebris.firetex,
            smoketex=self.hitdebris.smoketex,
            debristex=self.hitdebris.debristex,
            sizefac=1.0, timefac=1.0, amplfac=1.0,
            keepready=self.hitdebris.keepready)


    def _init_hitflash (self):

        self._hitfl_rate = 0.05
        self._hitfl_end_time = 0.10
        self._hitfl_scale = 3.0
        self._hitfl = MuzzleFlash(parent=self, pos=Point3(), hpr=Vec3(),
                                  ltpos=None, rate=self._hitfl_rate,
                                  shape="hit", scale=self._hitfl_scale)
        self._hitfl_time = 0.0
        self._hitfl_ref_caliber = 0.030


    def _loop_fx (self, task):

        if not self.alive:
            return task.done

        if self.hitlight:
            if self._hitlt_cscale > 0.0:
                dt = self.world.dt
                self._hitlt_cscale -= self._hitlt_cspeed * dt
                self._hitlt_cscale = max(self._hitlt_cscale, 0.0)
                rad = self._hitlt_radmin + self._hitlt_drad * self._hitlt_cscale
                col = self._hitlt_color * self._hitlt_cscale
                self._hitlt.update(radius=rad, color=col)

        if self.hitflash:
            if self.world.time > self._hitfl_time + self._hitfl_end_time:
                self._hitfl.active = False

        return task.cont


    def move (self, dt):

        # NOTE: Absolute frame is the parent, not the world.

        # Update translational motion.
        if self.racc.length() > 1e-5:
            aracc = self.parent.getRelativeVector(self.node, self.racc)
            self._acc = self.aacc + aracc
        else:
            self._acc = self.aacc
        if self._vel.length() > 1e-5:
            pos = self.node.getPos()
            pos1 = next_pos(pos, self._vel, self._acc, dt)
            self.node.setPos(pos1)
        self._prev_vel = Vec3(self._vel)
        self._vel += self._acc * dt

        # Update rotational motion.
        if self.rangacc.length() > 1e-5:
            arangacc = self.parent.node.getRelativeVector(self.node,
                                                          self.rangacc)
            self._angacc = self.aangacc + self.arangacc
        else:
            self._angacc = self.aangacc
        if self._angvel.length() > 1e-5:
            quat = self.node.getQuat()
            quat1 = next_quat(quat, self._angvel, self._angacc, dt)
            self.node.setQuat(quat1)
        self._prev_angvel = Vec3(self._angvel)
        self._angvel += self._angacc * dt


    def after_move (self):

        if base.with_world_shadows and self.shadow_node is not None:
            self.shadow_node.setPos(self.pos())
            self.shadow_node.setQuat(self.quat())


    def jump_to (self, pos=None, hpr=None, speed=None):

        if pos is None:
            pos = self.pos(refbody=self.parent)
        if hpr is None:
            hpr = self.hpr(refbody=self.parent)
        if speed is None:
            speed = self.speed(refbody=self.parent)

        self.node.setPos(pos)
        self.node.setHpr(hpr)
        q = Quat()
        q.setHpr(hpr)
        self._vel = Vec3(q.xform(Vec3(0, speed, 0)))
        self._acc = Vec3()
        self._angvel = Vec3()
        self._angacc = Vec3()
        self._prev_vel = Vec3(self._vel)
        self._prev_angvel = Vec3(self._angvel)


    def _res_refnode (self, refbody):

        if refbody is None:
            refnode = self.world.node
        elif isinstance(refbody, NodePath):
            refnode = refbody
        else:
            refnode = refbody.node
        return refnode


    def pos (self, refbody=None, offset=None, dt=None):

        refnode = self._res_refnode(refbody)
        if offset is None:
            if dt is None:
                if refnode is self.parent.node:
                    return self.node.getPos()
                else:
                    return self.node.getPos(refnode)
            else:
                pos1 = next_pos(self.node.getPos(), self._vel, self._acc, dt)
                if refnode is self.parent.node:
                    return pos1
                else:
                    return refnode.getRelativePoint(self.parent.node, pos1)
        else:
            if dt is None:
                return refnode.getRelativePoint(self.node, offset)
            else:
                offpos = self.parent.node.getRelativePoint(self.node, offset)
                offpos1 = next_pos(offpos, self._vel, self._acc, dt)
                return refnode.getRelativePoint(self.parent.node, offpos1)


    def quat (self, refbody=None, dt=None):

        refnode = self._res_refnode(refbody)
        if dt is None:
            if refnode is self.parent.node:
                return self.node.getQuat()
            else:
                return self.node.getQuat(refnode)
        else:
            # No NodePath.getRelativeQuat(), do it the hard way.
            quat0 = self.node.getQuat()
            self.node.setQuat(next_quat(quat0, self._angvel, self._angacc, dt))
            quat1 = self.node.getQuat(refnode)
            self.node.setQuat(quat0)
            return quat1


    def hpr (self, refbody=None, dt=None):

        return self.quat(refbody, dt).getHpr()


    def vel (self, refbody=None):

        refnode = self._res_refnode(refbody)
        if refnode is self.parent.node:
            return Vec3(self._vel)
        else:
            return (self.parent.vel(refnode) +
                    refnode.getRelativeVector(self.parent.node, self._vel))


    def angvel (self, refbody=None):

        refnode = self._res_refnode(refbody)
        if refnode is self.parent.node:
            return Vec3(self._angvel)
        else:
            return (self.parent.angvel(refnode) +
                    refnode.getRelativeVector(self.parent.node, self._angvel))


    def speed (self, refbody=None):

        return self.vel(refbody).length()


    def angspeed (self, refbody=None):

        return self.angvel(refbody).length()


    def climbrate (self, refbody=None):

        return self.vel(refbody)[2]


    def turnrate (self, refbody=None):

        v0 = Vec3(self._prev_vel)
        v0.normalize()
        v1 = Vec3(self._vel)
        v1.normalize()
        nv = v0.cross(v1)
        if nv.normalize() > 0.0:
            da = v0.signedAngleRad(v1, nv)
            pangvel = nv * (da / self.world.dt)
            refnode = self._res_refnode(refbody)
            if refnode is not self.parent.node:
                pangvel = refnode.getRelativeVector(self.parent.node, pangvel)
            turnrate = pangvel[2]
            #print "--wbtr", degrees(turnrate), pangvel, degrees(da), self.world.dt, v0, v1
        else:
            turnrate = 0.0
        # vel = self.vel(refbody)
        # speed = vel.length()
        # if speed > 1e-3:
            # acc = self.acc(refbody)
            # vdir = Vec3(vel)
            # vdir.normalize()
            # tacc = vdir * vdir.dot(acc)
            # nacc = acc - tacc
            # ndir = Vec3(nacc)
            # bdir = vdir.cross(ndir)
            # bdir.normalize()
            # absnacc = nacc.length()
            # pomg = absnacc / speed
            # turnrate = bdir[2] * pomg
            # #print "--wbtr", degrees(turnrate), absnacc
        # else:
            # turnrate = 0.0
        return turnrate


    def rollrate (self, refbody=None):

        vdir = Vec3(self._vel)
        vdir.normalize()
        rollrate = self.angvel().dot(vdir)
        return rollrate


    def acc (self, refbody=None):

        refnode = self._res_refnode(refbody)
        if refnode is self.parent.node:
            return Vec3(self._acc)
        else:
            return (self.parent.acc(refnode) +
                    refnode.getRelativeVector(self.parent.node, self._acc))


    def angacc (self, refbody=None):

        refnode = self._res_refnode(refbody)
        if refnode is self.parent.node:
            return Vec3(self._angacc)
        else:
            return (self.parent.angacc(refnode) +
                    refnode.getRelativeVector(self.parent.node, self._angacc))


    def gfactor (self):

        ndir = self.node.getQuat().getRight().cross(self._vel)
        ndir.normalize()
        absgravacc = self.world.absgravacc
        if absgravacc > 1e-5:
            accmg = ndir.dot(self._acc - self.world.gravacc)
            return accmg / absgravacc
        else:
            return 0.0


    def ppitch (self, refbody=None):

        zdir = Vec3(0, 0, 1)
        zdir.normalize()
        vdir = self.vel(refbody)
        vdir.normalize()
        rdir = vdir.cross(zdir)
        rdir.normalize()
        if rdir.length() < 1e-5:
            ppitch = sign(zdir.dot(vdir)) * (0.5 * pi)
        else:
            ppitch = 0.5 * pi - vdir.signedAngleRad(zdir, rdir)
        return ppitch


    def dist (self, other, offset=None):

        if isinstance(other, Body):
            return (self.pos() - other.pos(offset=offset)).length()
        elif isinstance(other, VBase3):
            return (self.pos() - (other + (offset or Point3()))).length()
        elif isinstance(other, VBase2):
            return (self.pos().getXy() - (other + (offset or Point2()))).length()
        else:
            raise StandardError(
                "Unknown type %s in distance computation." % type(other))


    def offbore (self, other):

        odir = other.pos(self)
        odir.normalize()
        return acos(odir[1])


    def update_bbox (self, bbox=None, bboxcenter=None):

        if bbox is not None:
            self.bbox = bbox
            self.bboxdiag = bbox.length()
            self.bboxarea = Vec3(bbox[1] * bbox[2], # side
                                 bbox[2] * bbox[0], # front
                                 bbox[0] * bbox[1]) # top
            #print ("--bbox-update  species=%s  bboxdiag=%.3f  "
                   #"bboxarea=(side=%.1f, front=%.1f, top=%.1f)"
                   #% (self.species, self.bboxdiag,
                      #self.bboxarea[0], self.bboxarea[1], self.bboxarea[2]))
        if bboxcenter is not None:
            self.bboxcenter = bboxcenter


    def project_bbox_area (self, vdir, refbody=None):

        refnode = self._res_refnode(refbody)
        rvdir = self.node.getRelativeVector(refnode, vdir)
        pbbarea = Vec3(*map(abs, rvdir)).dot(self.bboxarea)
        return pbbarea


    def set_crashed (self):

        self._record_shotdown()
        self.inert_collide = True


    def set_shotdown (self, delay=0.0):

        if delay > 0.0:
            def taskf (task):
                task.wait_time -= self.world.dt
                if task.wait_time <= 0.0:
                    self._record_shotdown()
                    return task.done
                return task.cont
            task = base.taskMgr.add(taskf, "delay-set-shotdown")
            task.wait_time = delay
        else:
            self._record_shotdown()

        self.inert_collide = True
        self.controlout = True


    def _record_shotdown (self):

        self.shotdown = True
        self.outofbattle = True

        if (self._last_collide_body and self.controlout and
            not self._recorded_as_kill):
            lcbody = self._last_collide_body
            player = self.world.player
            if player and lcbody.initiator is player.ac:
                player.record_kill(self)
                self._recorded_as_kill = True


class HitboxData (object):

    def __init__ (self, colldata, name="",
                  longdes=_("(unknown)"), shortdes=_("n/k"),
                  selectable=False):

        self.colldata = colldata
        self.name = name
        self.longdes = longdes
        self.shortdes = shortdes
        self.selectable = selectable


class Hitbox (object):

    def __init__ (self, pbody, hbxdata,
                  isinto=True, isfrom=True, critical=False):

        self.pbody = pbody

        self.name = hbxdata.name
        self.colldata = hbxdata.colldata
        self.longdes = hbxdata.longdes
        self.shortdes = hbxdata.shortdes
        self.selectable = hbxdata.selectable

        self.isinto = isinto
        self.isfrom = isfrom
        self.critical = critical

        self.center = Point3()
        self.volume = 0.0
        for csd in self.colldata:
            cst = Hitbox._csd_type(csd)
            if cst == "sphere":
                c, r = csd
                v = (4.0 / 3.0) * pi * r**3
            elif cst == "segment":
                p1, p2 = csd
                v = (p2 - p1).length()
                c = (p1 + p2) * 0.5
            elif cst == "box":
                c, hwx, hwy, hwz = csd
                v = hwx * hwy * hwz * 8
            self.volume += v
            self.center += c * v
        self.center /= self.volume

        cnd = CollisionNode("cnode-%s" % self.name)
        for csd in self.colldata:
            cst = Hitbox._csd_type(csd)
            if cst == "sphere":
                c, r = csd
                coff = Point3(c - self.center)
                cs = CollisionSphere(coff, r)
            elif cst == "segment":
                p1, p2 = csd
                p1off = Point3(p1 - self.center)
                p2off = Point3(p2 - self.center)
                cs = CollisionSegment(p1off, p2off)
            elif cst == "box":
                c, hwx, hwy, hwz = csd
                coff = Point3(c - self.center)
                cs = CollisionBox(coff, hwx, hwy, hwz)
            cnd.addSolid(cs)
        self.cnode = pbody.node.attachNewNode(cnd)
        self.cnode.setPos(self.center)
        self.cnode.setPythonTag("hitbox", self)

        if self.isinto:
            self._cmask_into = 0x0001
        else:
            self._cmask_into = 0x0000
        cnd.setIntoCollideMask(self._cmask_into)

        if self.isfrom:
            world = self.pbody.world
            world.ctrav.addCollider(self.cnode, world.cqueue)
            self._cmask_from = 0x0001
        else:
            self._cmask_from = 0x0000
        cnd.setFromCollideMask(self._cmask_from)

        self._cnd = cnd
        self.active = True


    def set_active (self, active):

        self.active = active
        if self.active:
            if self.isinto:
                self._cnd.setIntoCollideMask(self._cmask_into)
            if self.isfrom:
                self._cnd.setFromCollideMask(self._cmask_from)
        else:
            if self.isinto:
                self._cnd.setIntoCollideMask(0x0000)
            if self.isfrom:
                self._cnd.setFromCollideMask(0x0000)


    def destroy (self):

        world = self.pbody.world
        world.ctrav.removeCollider(self.cnode)
        self.cnode.clearPythonTag("hitbox")
        self.cnode.removeNode()


    @staticmethod
    def _csd_type (csd):

        if (len(csd) == 2 and
            isinstance(csd[0], Point3) and isinstance(csd[1], float)):
            return "sphere"
        elif (len(csd) == 2 and
              isinstance(csd[0], Point3) and isinstance(csd[1], Point3)):
            return "segment"
        elif (len(csd) == 4 and
              isinstance(csd[0], Point3) and
              all(isinstance(e, float) for e in csd[1:])):
            return "box"
        else:
            raise StandardError(
                "Unknown collision solid data composition '%s'." % csd)


class EnhancedVisual (Body):

    def __init__ (self, parent, bbox):

        Body.__init__(self,
            world=parent.world,
            family=("%s-v" % parent.family), species=("%s-v" % parent.species),
            hitforce=0.0,
            name=parent.name, side=parent.side,
            pos=parent.center,
            parent=parent)

        bboxcenter = bbox * 0.5
        self.update_bbox(bbox=bbox, bboxcenter=bboxcenter)

        base.taskMgr.add(self._loop, "%s_v-loop-%s" % (self.species, self.name))


    def _loop (self, task):

        if not self.alive:
            return task.done
        if not self.parent.alive:
            self.destroy()
            return task.done
        return task.cont


    def move (self, dt):

        pass


    def destroy (self):

        if not self.alive:
            return

        Body.destroy(self)


