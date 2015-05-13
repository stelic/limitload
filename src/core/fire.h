#ifndef FIRE_H
#define FIRE_H

#include <deque>

#include <lvector4.h>
#include <lpoint3.h>
#include <nodePath.h>
#include <geom.h>
#include <geomNode.h>
#include <geomVertexData.h>
#include <geomTriangles.h>

#include <typeinit.h>
#include <misc.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_FIRE
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

class ExplosionParticle;
class EXPORT PolyExplosionGeom : public TypedObject
{
PUBLISHED:

    PolyExplosionGeom (
        const NodePath &pnode,
        int texsplit, int numframes, bool animated,
        double size1, double size2,
        const LVector4& color1, const LVector4& color2, const LVector4& color3,
        double colpeak1, double colpeak2,
        const LPoint3& pos, double radius, double amplitude,
        double lifespan, int poolsize,
        NumRandom &randgen);
    ~PolyExplosionGeom ();

    void start (const NodePath &camera);
    bool update (const NodePath &camera, double adt);

    NodePath root () const;

private:

    int _texsplit;
    int _numframes;
    bool _animated;
    double _size1, _size2;
    LVector4 _color1, _color2, _color3;
    double _colpeak1, _colpeak2;
    double _radius;
    double _amplitude;
    double _lifespan;
    int _poolsize;

    NumRandom &_rg;

    NodePath _node;
    PT(Geom) _geom;
    PT(GeomNode) _geomnode;
    PT(GeomVertexData) _gvdata;
    PT(GeomTriangles) _gtris;

    std::deque<ExplosionParticle*> _particles;

    double _time;
    bool _started, _done;
    LVector4 _frame1;

    void _draw_particles (const NodePath &camera);
    void _clear ();

DECLARE_TYPE_HANDLE(PolyExplosionGeom)
};

#endif
