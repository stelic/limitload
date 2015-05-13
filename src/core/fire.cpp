#ifdef _MSC_VER
#define _USE_MATH_DEFINES
#endif
#include <cmath>

#include <boundingSphere.h>
#include <geomVertexFormat.h>
#include <geomVertexArrayFormat.h>
#include <geomVertexData.h>
#include <geomVertexWriter.h>
#include <geomVertexRewriter.h>
#include <lvector2.h>
#include <lvector3.h>
#include <transparencyAttrib.h>

#include <fire.h>
#include <misc.h>

static void _init_fire ()
{
    static bool initialized = false;
    if (initialized) {
        return;
    }
    initialized = true;
    INITIALIZE_TYPE(PolyExplosionGeom)
}
DToolConfigure(config_limload_fire);
DToolConfigureFn(config_limload_fire) { _init_fire(); }


class ExplosionParticle
{
public:
    LPoint3 pos;
    LVector3 vel;
    LVector4 frame;
    double size;
    LVector4 color;
};
typedef std::deque<ExplosionParticle*>::iterator ExpPartsIter;

INITIALIZE_TYPE_HANDLE(PolyExplosionGeom)

PolyExplosionGeom::PolyExplosionGeom (
    const NodePath &pnode,
    int texsplit, int numframes, bool animated,
    double size1, double size2,
    const LVector4& color1, const LVector4& color2, const LVector4& color3,
    double colpeak1, double colpeak2,
    const LPoint3& pos, double radius, double amplitude,
    double lifespan, int poolsize,
    NumRandom &randgen)
: _texsplit(texsplit), _numframes(numframes), _animated(animated)
, _size1(size1), _size2(size2)
, _color1(color1), _color2(color2), _color3(color3)
, _colpeak1(colpeak1), _colpeak2(colpeak2)
, _radius(radius), _amplitude(amplitude)
, _lifespan(lifespan), _poolsize(poolsize)
, _rg(randgen)
{
    _node = pnode.attach_new_node("explosion-part");
    _node.set_pos(pos);

    _started = false;
}

void PolyExplosionGeom::start (const NodePath &camera)
{
    if (_started) {
        return;
    }

    _gvdata = new GeomVertexData("explosion", GeomVertexFormat::get_v3n3c4t2(), Geom::UH_static);//UH_dynamic);
    GeomVertexWriter *gvwvertex = new GeomVertexWriter(_gvdata, "vertex");
    GeomVertexWriter *gvwnormal = new GeomVertexWriter(_gvdata, "normal");
    GeomVertexWriter *gvwtexcoord = new GeomVertexWriter(_gvdata, "texcoord");
    GeomVertexWriter *gvwcolor = new GeomVertexWriter(_gvdata, "color");
    _gtris = new GeomTriangles(Geom::UH_static);
    for (int i = 0; i < _poolsize * 2; ++i) {
        for (int j = 0; j < 3; ++j) {
            LVector2 v2 = LVector2(0.0, _rg.randunit());
            LVector3 v3 = LVector3(0.0, 0.0, _rg.randunit());
            LVector4 v4 = LVector4(1.0, 1.0, 1.0, _rg.randunit());
            gvwvertex->add_data3(v3);
            gvwnormal->add_data3(v3);
            gvwtexcoord->add_data2(v2);
            gvwcolor->add_data4(v4);
        }
        _gtris->add_vertices(i * 3, i * 3 + 1, i * 3 + 2);
    }
    _gtris->close_primitive();
    _geom = new Geom(_gvdata);
    _geom->add_primitive(_gtris);
    _geomnode = new GeomNode("explosion-geom");
    _geomnode->add_geom(_geom);
    _node.attach_new_node(_geomnode);
    delete gvwvertex;
    delete gvwnormal;
    delete gvwtexcoord;
    delete gvwcolor;

    _node.set_depth_write(0);
    _node.set_transparency(TransparencyAttrib::M_alpha);

    int frind = _animated ? 0 : _rg.randrange(_numframes);
    LVector4 frame = texture_frame(_texsplit, frind);
    _frame1 = frame;

    double size = _size1;

    LVector4 color = _color1;

    //HaltonDistrib distrib(1);
    HaltonDistrib distrib(_rg.randrange(10) * 100);
    for (int i = 0; i < _poolsize; ++i) {
        //double rad = _rg.uniform(0.0, _radius);
        //LPoint3 pos = _rg.randvec() * rad;
        LVector3 d3 = distrib.next3();
        LVector3 hpr = LVector3(todeg((2 * M_PI) * d3[0]), todeg(asin(2 * d3[1] - 1)), 0.0);
        double rad = _radius * pow(double(d3[2]), 0.333);
        LPoint3 pos = hprtovec(hpr) * rad;
        LVector3 vel = unitv(pos) * _amplitude;
        _particles.push_back(new ExplosionParticle());
        ExplosionParticle &p = *_particles.back();
        p.pos = pos; p.vel = vel;
        p.frame = frame; p.size = size; p.color = color;
    }

    _draw_particles(camera);

    _time = 0.0;
    _started = true;
    _done = false;
}

PolyExplosionGeom::~PolyExplosionGeom ()
{
    for (ExpPartsIter it = _particles.begin(); it != _particles.end(); ++it) {
        delete *it;
    }
}

bool PolyExplosionGeom::update (const NodePath &camera, double adt)
{
    if (!_started) {
        return true;
    }
    else if (_done) {
        return false;
    }

    _time += adt;
    if (_time >= _lifespan) {
        if (!_done) {
            _clear();
            _done = true;
        }
        return false;
    }

    double ifac = _time / _lifespan;

    LVector4 frame;
    if (_animated) {
        int frind = int(_numframes * ifac);
        frame = texture_frame(_texsplit, frind);
    } else {
        frame = _frame1;
    }

    double size = _size1 + (_size2 - _size1) * ifac;

    LVector4 color;
    if (_colpeak1 < 1.0) {
        double time_c = _time;
        double time_p = _lifespan * _colpeak1;
        double time_e = _lifespan * _colpeak2;
        if (time_c < time_p) {
            double ifac1 = time_c / time_p;
            color = _color1 + (_color2 - _color1) * ifac1;
        } else if (time_c < time_e) {
            double ifac2 = (time_c - time_p) / (time_e - time_p);
            color = _color2 + (_color3 - _color2) * ifac2;
        } else {
            color = _color3;
        }
    } else {
        color = _color1;
    }
    color = LVector4(color); // match Python code
    color[3] *= (1.0 - ifac);

    for (ExpPartsIter it = _particles.begin(); it != _particles.end(); ++it) {
        ExplosionParticle &p = **it;
        p.pos += p.vel * adt;
        p.size = size; p.frame = frame; p.color = color;
    }

    _draw_particles(camera);

    return true;
}

void PolyExplosionGeom::_draw_particles (const NodePath &camera)
{
    LVector3 up = _node.get_relative_vector(camera, LVector3(0.0, 0.0, 1.0));
    LVector3 rt = _node.get_relative_vector(camera, LVector3(1.0, 0.0, 0.0));
    LVector3 oc1 = -rt - up;
    LVector3 oc2 =  rt - up;
    LVector3 oc3 =  rt + up;
    LVector3 oc4 = -rt + up;
    LVector3 nrm = unitv(rt.cross(up)); // -fw
    LVector3 nrm1 = unitv(oc1 + nrm * 0.05);
    LVector3 nrm2 = unitv(oc2 + nrm * 0.05);
    LVector3 nrm3 = unitv(oc3 + nrm * 0.05);
    LVector3 nrm4 = unitv(oc4 + nrm * 0.05);

    GeomVertexRewriter *gvwvertex = new GeomVertexRewriter(_gvdata, "vertex");
    GeomVertexRewriter *gvwnormal = new GeomVertexRewriter(_gvdata, "normal");
    GeomVertexRewriter *gvwtexcoord = new GeomVertexRewriter(_gvdata, "texcoord");
    GeomVertexRewriter *gvwcolor = new GeomVertexRewriter(_gvdata, "color");
    _gtris->decompose();
    for (ExpPartsIter it = _particles.begin(); it != _particles.end(); ++it) {
        ExplosionParticle &p = **it;
        double hsize = p.size * 0.5;
        LVector3 qp1 = p.pos + oc1 * hsize;
        LVector3 qp2 = p.pos + oc2 * hsize;
        LVector3 qp3 = p.pos + oc3 * hsize;
        LVector3 qp4 = p.pos + oc4 * hsize;
        double u0 = p.frame[0];
        double v0 = p.frame[1];
        double du = p.frame[2];
        double dv = p.frame[3];
        LVector4 col = p.color;
        add_tri(gvwvertex, gvwcolor, gvwtexcoord, gvwnormal,
                qp1, nrm1, col, LVector2(u0, v0),
                qp2, nrm2, col, LVector2(u0 + du, v0),
                qp3, nrm3, col, LVector2(u0 + du, v0 + dv));
        add_tri(gvwvertex, gvwcolor, gvwtexcoord, gvwnormal,
                qp1, nrm1, col, LVector2(u0, v0),
                qp3, nrm3, col, LVector2(u0 + du, v0 + dv),
                qp4, nrm4, col, LVector2(u0, v0 + dv));
    }
    delete gvwvertex;
    delete gvwnormal;
    delete gvwtexcoord;
    delete gvwcolor;

    LPoint3 center(0.0, 0.0, 0.0);
    double maxreach = _radius;
    PT(BoundingSphere) bnd = new BoundingSphere(center, maxreach);
    _node.node()->set_bounds(bnd);
    _node.node()->set_final(1);
}

void PolyExplosionGeom::_clear ()
{
    GeomVertexRewriter *gvwvertex = new GeomVertexRewriter(_gvdata, "vertex");
    _gtris->decompose();
    for(int i = 0; i < _poolsize * 2; ++i) {
        for (int j = 0; j < 3; ++j) {
            gvwvertex->add_data3(0.0, 0.0, 0.0);
        }
    }
    delete gvwvertex;
}

NodePath PolyExplosionGeom::root () const
{
    return _node;
}

