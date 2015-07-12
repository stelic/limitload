#ifndef TRAIL_H
#define TRAIL_H

#include <deque>

#include <lvector3.h>
#include <lvector4.h>
#include <lpoint3.h>
#include <lquaternion.h>
#include <meshDrawer.h>
#include <nodePath.h>

#include <typeinit.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_TRAIL
            #define EXPORT __declspec(dllexport)
            #define EXTERN
        #else
            #define EXPORT __declspec(dllimport)
            #define EXTERN extern
        #endif
    #endif
    #define TEMPLATE template
#else
    #define EXPORT
    #define EXTERN
    #define TEMPLATE
#endif

class TrailPoint;
class EXPORT PolyTrailGeom : public TypedObject
{
PUBLISHED:

    PolyTrailGeom (
        int numpoly, double randcircle, double segperiod,
        const LPoint3 &apos, const LQuaternion& aquat,
        const NodePath &pnode);
    ~PolyTrailGeom ();

    void update (
        const NodePath &camera, double lifespan, double lodalfac,
        double radius0, double radius1,
        const LVector4 &color_, const LVector4 &endcolor, double tcol,
        const LPoint3 &bpos,
        bool havepq, const LPoint3 &apos_, const LQuaternion& aquat_,
        double adt);

    void clear (
        const NodePath &camera,
        bool havepq, const LPoint3 &apos, const LQuaternion& aquat);

    NodePath node ();
    bool any_visible () const;
    double seg_period () const;
    LPoint3 prev_apos () const;
    LQuaternion prev_aquat () const;
    void set_prev (const LPoint3 &apos, const LQuaternion& aquat);

private:

    double _randcircle;
    double _segperiod;

    int _maxpoly;
    NodePath _node;
    PT(Geom) _geom;
    PT(GeomNode) _geomnode;
    PT(GeomVertexData) _gvdata;
    PT(GeomTriangles) _gtris;
    int _last_clear_index;

    LPoint3 _prev_apos;
    LQuaternion _prev_aquat;

    std::deque<TrailPoint*> _points;
    int _numpoints;

DECLARE_TYPE_HANDLE(PolyTrailGeom)
};

class ExhaustParticle;
class EXPORT PolyExhaustGeom : public TypedObject
{
PUBLISHED:

    PolyExhaustGeom (const NodePath &pnode, int poolsize);
    ~PolyExhaustGeom ();

    bool update (
        const NodePath &camera,
        bool palive, bool sigend, const LVector3 &pdir,
        double lifespan, double speed, double emradius,
        double radius0, double radius1,
        const LVector4 &color0, const LVector4 &color1, double tcol,
        const LVector3 &dbpos, int emskip,
        double adt);

    int num_particles () const;
    LVector3 chord (const LVector3 &pdir) const;

private:

    int _poolsize;
    MeshDrawer _gen;
    double _emittime;
    int _emskip_count;
    std::deque<ExhaustParticle*> _particles;
    int _numparts;

DECLARE_TYPE_HANDLE(PolyExhaustGeom)
};

class BraidStrand;
class EXPORT PolyBraidGeom : public TypedObject
{
PUBLISHED:

    PolyBraidGeom (
        double segperiod, const LVector3 &partvel,
        const LVector3 &emittang, const LVector3 &emitnorm,
        const LPoint3 &apos, const LQuaternion& aquat);
    ~PolyBraidGeom ();

    NodePath add_strand (
        double thickness, double endthickness, double spacing,
        double offang, double offrad, double offtang,
        bool randang, bool randrad,
        const LVector4 &color, const LVector4 &endcolor,
        double tcol, double alphaexp,
        int texsplit, int numframes,
        int maxpoly, const NodePath &pnode);

    void update (
        const NodePath &camera,
        double lifespan, double lodalfac, const LPoint3 &bpos,
        bool havepq, const LPoint3 &apos, const LQuaternion &aquat,
        double adt);

    void clear (
        const NodePath &camera,
        bool havepq, const LPoint3 &apos, const LQuaternion &aquat);

    bool any_visible () const;
    LPoint3 prev_apos () const;
    LQuaternion prev_aquat () const;
    LPoint3 start_point () const;
    LPoint3 end_point () const;
    double seg_period () const;
    void multiply_init_dtang (double spfac);

private:

    std::deque<BraidStrand*> _strands;
    double _segperiod;
    LVector3 _partvel;
    LVector3 _emittang;
    LVector3 _emitnorm;
    LVector3 _emitbnrm;
    LPoint3 _prev_apos;
    LQuaternion _prev_aquat;
    LPoint3 _start_point;
    LPoint3 _end_point;
    bool _any_visible;

DECLARE_TYPE_HANDLE(PolyBraidGeom)
};

class SmokeStrand;
class EXPORT PolyBurnGeom : public TypedObject
{
PUBLISHED:

    PolyBurnGeom (const LPoint3 &apos, const LQuaternion& aquat);
    ~PolyBurnGeom ();

    NodePath add_strand (
        double thickness, double endthickness,
        int emittype, const LVector4 &emitparam1, double emitspeed,
        double spacing, double offtang,
        const LVector4 &color, const LVector4 &endcolor,
        double tcol, double alphaexp,
        int texsplit, int numframes,
        int maxpoly, const NodePath &pnode);

    void update (
        const NodePath &camera,
        double lifespan, const LPoint3 &bpos,
        bool havepq, const LPoint3 &apos, const LQuaternion &aquat,
        double adt);

    void clear (
        const NodePath &camera,
        bool havepq, const LPoint3 &apos, const LQuaternion &aquat);

    bool any_visible () const;
    LPoint3 prev_apos () const;
    LQuaternion prev_aquat () const;

private:

    std::deque<SmokeStrand*> _strands;
    LPoint3 _prev_apos;
    LQuaternion _prev_aquat;
    int _total_particle_count;

DECLARE_TYPE_HANDLE(PolyBurnGeom)
};

#endif
