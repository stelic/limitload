#ifdef _MSC_VER
#define _USE_MATH_DEFINES
#endif
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <sstream>

#include <geomVertexArrayFormat.h>
#include <geomVertexData.h>
#include <geomVertexWriter.h>
#include <geomTriangles.h>
#include <geomNode.h>
#include <lodNode.h>
#include <internalName.h>
#include <lvector2.h>
#include <lvector3.h>
#include <lvector4.h>
#include <triangulator.h>

#include <terrain.h>
#include <table.h>
#include <misc.h>

#ifdef _MSC_VER
#undef min
#undef max
#endif

static void _init_terrain ()
{
    static bool initialized = false;
    if (initialized) {
        return;
    }
    initialized = true;
    INITIALIZE_TYPE(TerrainGeom)
}
DToolConfigure(config_limload_terrain);
DToolConfigureFn(config_limload_terrain) { _init_terrain(); }


class IntCurvePart
{
public:
    IntCurvePart (const LVector3d &pc, const LVector3d &pa, const LVector3d &pb,
                   const std::pair<int, int> &qva, std::pair<int, int> &qvb);
    LVector3d pc;
    LVector3d pa, pb;
    std::pair<int, int> qva, qvb;
};

IntCurvePart::IntCurvePart (
    const LVector3d &pc_, const LVector3d &pa_, const LVector3d &pb_,
    const std::pair<int, int> &qva_, std::pair<int, int> &qvb_)
: pc(pc_), pa(pa_), pb(pb_), qva(qva_), qvb(qvb_)
{
}

class IntQuadChainPart
{
public:
    IntQuadChainPart (int i, int j, int ncl);
    int i, j;
    int ncl;
};

IntQuadChainPart::IntQuadChainPart (int i_, int j_, int ncl_)
: i(i_), j(j_), ncl(ncl_)
{
}

class IntQuadLink
{
public:
    IntQuadLink (int i, int j, int itri1, int itri2);
    int i, j;
    int itri1, itri2;
};

IntQuadLink::IntQuadLink (int i_, int j_, int itri1_, int itri2_)
: i(i_), j(j_), itri1(itri1_), itri2(itri2_)
{
}

INITIALIZE_TYPE_HANDLE(TerrainGeom)

TerrainGeom::TerrainGeom (
    const std::string &name,
    double sizex, double sizey, double offsetx, double offsety,
    const std::string &heightmappath, bool haveheightmappath,
    const std::string &hmdatapath, bool havehmdatapath,
    double maxsizexa, double maxsizexb, bool havemaxsizex,
    double maxsizey, bool havemaxsizey,
    double centerx, bool havecenterx, double centery, bool havecentery,
    int mingray, bool havemingray, int maxgray, bool havemaxgray,
    double minheight, bool haveminheight,
    double maxheight, bool havemaxheight,
    int numtilesx, int numtilesy,
    double celldensity, bool periodic,
    ENC_LST_STRING cutmaskpaths_, ENC_LST_BOOL levints_)
{
    std::vector<string> cutmaskpaths = dec_lst_string(cutmaskpaths_);
    std::vector<bool> levints = dec_lst_bool(levints_);

    bool timeit = false;

    _construct(
        sizex, sizey,
        offsetx, offsety,
        heightmappath, haveheightmappath, hmdatapath, havehmdatapath,
        maxsizexa, maxsizexb, havemaxsizex,
        maxsizey, havemaxsizey,
        centerx, havecenterx,
        centery, havecentery,
        mingray, havemingray,
        maxgray, havemaxgray,
        minheight, haveminheight,
        maxheight, havemaxheight,
        numtilesx, numtilesy,
        celldensity, periodic,
        cutmaskpaths, levints,
        // celldata
        _numquadsx, _numquadsy, _numtilesx, _numtilesy,
        _tilesizex, _tilesizey, _numcuts,
        _centerx, _centery,
        _maxsizexa, _maxsizexb, _maxsizey,
        // elevdata
        _verts, _tris, _quadmap,
        _maxz, _maxqzs,
        // geomdata
        _tileroot);

    _sizex = sizex;
    _sizey = sizey;
    _offsetx = offsetx;
    _offsety = offsety;

    _alive = true;
}

TerrainGeom::~TerrainGeom ()
{
    destroy();
}

void TerrainGeom::destroy ()
{
    if (!_alive) {
        return;
    }
    _tileroot.remove_node();
    _verts.clear();
    _tris.clear();
    _quadmap.clear();
    _maxqzs.clear();
    _alive = false;
}

NodePath TerrainGeom::tile_root ()
{
    return _tileroot;
}

int TerrainGeom::num_quads_x () const
{
    return _numquadsx;
}

int TerrainGeom::num_quads_y () const
{
    return _numquadsy;
}

int TerrainGeom::num_tiles_x () const
{
    return _numtilesx;
}

int TerrainGeom::num_tiles_y () const
{
    return _numtilesy;
}

int TerrainGeom::tile_size_x () const
{
    return _tilesizex;
}

int TerrainGeom::tile_size_y () const
{
    return _tilesizey;
}

int TerrainGeom::num_cuts () const
{
    return _numcuts;
}

double TerrainGeom::max_z () const
{
    return _maxz;
}

void TerrainGeom::update_max_z (double z)
{
    _maxz = fmax(_maxz, z);
}

double TerrainGeom::quad_max_z (int q) const
{
    return _maxqzs[q];
}

void TerrainGeom::update_quad_max_z (int q, double z)
{
    _maxqzs[q] = fmax(_maxqzs[q], z);
}

class Flat
{
public:

    Flat () {};
    virtual ~Flat () {};

    virtual std::string name () const = 0;

    virtual LPoint2d refxy () const = 0;

    virtual double refz () const = 0;

    virtual bool have_refz () const = 0;

    virtual void set_refz (double z, bool havecenterz) = 0;

    virtual void correct_z (double x, double y, double z,
                            double &zmod, bool &havezmod) const = 0;
};

typedef std::vector<Flat*>::iterator FlatsIter;

class FlatCircle : public Flat
{
public:

    FlatCircle (const std::string &name,
                double centerx, double centery, double radius,
                double centerz = 0.0, bool havecenterz = false,
                double radiusout = 0.0)
    {
        _name = name;
        _centerx = centerx;
        _centery = centery;
        _centerz = centerz;
        _havecenterz = havecenterz;
        _radius = radius;
        _radiusout = 0.0;
    }

    std::string name () const
    {
        return _name;
    }

    LPoint2d refxy () const
    {
        return LPoint2d(_centerx, _centery);
    }

    double refz () const
    {
        return _centerz;
    }

    bool have_refz () const
    {
        return _havecenterz;
    }

    void set_refz (double z, bool havecenterz = true)
    {
        _centerz = z;
        _havecenterz = havecenterz;
    }

    void correct_z (double x, double y, double z,
                    double &zmod, bool &havezmod) const
    {
        if (!_havecenterz) {
            havezmod = false;
            return;
        }
        double rdist = sqrt(POW2(x - _centerx) + POW2(y - _centery));
        if (rdist <= _radius) {
            zmod = _centerz;
            havezmod = true;
        } else if (rdist <= _radiusout) {
            double ifc = (rdist - _radius) / (_radiusout - _radius);
            zmod = _centerz + (z - _centerz) * ifc;
            havezmod = true;
        } else {
            havezmod = false;
        }
    }

private:

    std::string _name;
    double _centerx, _centery, _centerz;
    bool _havecenterz;
    double _radius, _radiusout;
};


CPT(GeomVertexFormat) TerrainGeom::_gvformat = NULL;

void TerrainGeom::_construct(
    double sizex, double sizey,
    double offsetx, double offsety,
    const std::string &heightmappath, bool haveheightmappath,
    const std::string &hmdatapath, bool havehmdatapath,
    double maxsizexa, double maxsizexb, bool havemaxsizex,
    double maxsizey, bool havemaxsizey,
    double centerx, bool havecenterx,
    double centery, bool havecentery,
    int mingray, bool havemingray,
    int maxgray, bool havemaxgray,
    double minheight, bool haveminheight,
    double maxheight, bool havemaxheight,
    int numtilesx, int numtilesy,
    double celldensity, bool periodic,
    const std::vector<std::string> &cutmaskpaths,
    const std::vector<bool> &levints,
    // celldata
    int &numquadsx_, int &numquadsy_, int &numtilesx_, int &numtilesy_,
    int &tilesizex_, int &tilesizey_, int &numcuts_,
    double &centerx_, double &centery_,
    double &maxsizexa_, double &maxsizexb_, double &maxsizey_,
    // elevdata
    std::vector<LVector3d> &verts,
    std::vector<LVector4i> &tris,
    std::vector<LVector2i> &quadmap,
    double &maxz, std::vector<double> &maxqzs,
    // geomdata
    NodePath &tileroot_)
{
    bool timeit = false;
    bool memit = false;

    double t0, t1, t2;
    if (timeit) {
        t0 = stime();
        t1 = t0;
    }

    // Load the height map.
    std::vector<Flat*> flats;
    UnitGrid2 heightmap(0.0);
    if (haveheightmappath) {
        if (havehmdatapath) {
            double sxa, sxb, sy, mnz, mxz;
            int mng, mxg;
            _read_heightmap_data(hmdatapath,
                                 sxa, sxb, sy, mnz, mxz, mng, mxg, flats);
            // Conctructor arguments override read data.
            if (!havemaxsizex) {
                maxsizexa = sxa;
                maxsizexb = sxb;
                havemaxsizex = true;
            }
            if (!havemaxsizey) {
                maxsizey = sy;
                havemaxsizey = true;
            }
            if (!havemingray) {
                mingray = mng;
                havemingray = true;
            }
            if (!havemaxgray) {
                maxgray = mxg;
                havemaxgray = true;
            }
            if (!haveminheight) {
                minheight = mnz;
                haveminheight = true;
            }
            if (!havemaxheight) {
                maxheight = mxz;
                havemaxheight = true;
            }
        }
        heightmap = UnitGrid2(heightmappath);
    }

    // Derive any non-initialized heightmap data.
    if (!havemaxsizex) {
        maxsizexa = sizex;
        maxsizexb = sizex;
    }
    if (!havemaxsizey) {
        maxsizey = sizey;
    }
    if (!havemingray) {
        mingray = 0;
    }
    if (!havemaxgray) {
        maxgray = 255;
    }
    if (!haveminheight) {
        minheight = 0.0;
    }
    if (!haveminheight && !havemaxheight) {
        minheight = 0.0;
        maxheight = 0.0;
    } else if (!haveminheight) {
        minheight = maxheight;
    } else if (!havemaxheight) {
        maxheight = minheight;
    }
    if (!havecenterx) {
        centerx = 0.0;
    }
    if (!havecentery) {
        centery = 0.0;
    }

    // Derive cell data.
    double maxsizexr = (maxsizexa + maxsizexb) * 0.5;
    double hmapsizex = heightmap.num_x() * (sizex / maxsizexr);
    int numquadsx; double tilesizex; int numtilequadsx;
    _derive_cell_data(celldensity, sizex, hmapsizex, numtilesx,
                      numquadsx, tilesizex, numtilequadsx);
    double hmapsizey = heightmap.num_y() * (sizey / maxsizey);
    int numquadsy; double tilesizey; int numtilequadsy;
    _derive_cell_data(celldensity, sizey, hmapsizey, numtilesy,
                      numquadsy, tilesizey, numtilequadsy);
    /*
    printf("--terrain-construct-celldata  "
           "nqx=%d  nqy=%d  ntx=%d  nty=%d  tszx=%.1f  tszy=%.1f  "
           "estnp=%d  \n",
           numquadsx, numquadsy, numtilesx, numtilesy,
           tilesizex, tilesizey,
           (numquadsx * numquadsy * 2));
    */

    // Load cut masks.
    std::vector<UnitGrid2> cutmasks;
    for (int i = 0; i < cutmaskpaths.size(); ++i) {
        const std::string &cutmaskpath = cutmaskpaths[i];
        UnitGrid2 cutmask(cutmaskpath);
        cutmasks.push_back(cutmask);
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-collect-maps:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    int cintdiv = 2; double cintlam = 0.8, cintmu = -0.2; int cintiter = 10;
    double lasttime;
    _triangulate(
        heightmap, cutmasks, levints,
        maxsizexa, maxsizexb, maxsizey, centerx, centery,
        sizex, sizey, offsetx, offsety, numquadsx, numquadsy,
        mingray, maxgray, minheight, maxheight, flats,
        cintdiv, cintlam, cintmu, cintiter,
        periodic, timeit, memit,
        verts, tris, quadmap,
        lasttime);
    if (timeit) {
        t1 = lasttime;
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-categorize-polygons:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Construct vertex format for tile textures.
    if (_gvformat == NULL) {
        PT(GeomVertexArrayFormat) gvarray = new GeomVertexArrayFormat();
        gvarray->add_column(InternalName::get_vertex(), 3,
                            Geom::NT_float32, Geom::C_point);
        gvarray->add_column(InternalName::get_normal(), 3,
                            Geom::NT_float32, Geom::C_vector);
        gvarray->add_column(InternalName::get_tangent(), 3,
                            Geom::NT_float32, Geom::C_vector);
        gvarray->add_column(InternalName::get_binormal(), 3,
                            Geom::NT_float32, Geom::C_vector);
        gvarray->add_column(InternalName::get_color(), 4,
                            Geom::NT_float32, Geom::C_color);
        gvarray->add_column(InternalName::get_texcoord(), 2,
                            Geom::NT_float32, Geom::C_texcoord);
        PT(GeomVertexFormat) gvformat = new GeomVertexFormat();
        gvformat->add_array(gvarray);
        _gvformat = GeomVertexFormat::register_format(gvformat);
    }

    // Create tiles.
    std::vector<std::vector<std::vector<NodePath> > > tiles;
    std::vector<std::vector<std::vector<LPoint2d> > > tilexys;
    int numcuts = cutmasks.size() + 1;
    for (int cut = 0; cut < numcuts; ++cut) {
        tiles.push_back(std::vector<std::vector<NodePath> >());
        tilexys.push_back(std::vector<std::vector<LPoint2d> >());
        std::vector<std::vector<NodePath> > &tiles1 = tiles[cut];
        std::vector<std::vector<LPoint2d> > &tilexys1 = tilexys[cut];
        _make_tiles(
            offsetx, offsety, numquadsx, numquadsy,
            numtilesx, numtilesy, tilesizex, tilesizey,
            numtilequadsx, numtilequadsy,
            _gvformat,
            verts, tris, quadmap, levints,
            cut,
            tiles1, tilexys1);
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-create-tiles:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Assemble tiles into final terrain.
    NodePath tileroot("terrain");
    double dummyoutvisradius = (0.5 * sqrt(POW2(tilesizex) + POW2(tilesizey))) * 4;
    for (int it = 0; it < numtilesx; ++it) {
        for (int jt = 0; jt < numtilesy; ++jt) {
            std::ostringstream oss;
            oss << "tile" << "-i" << it << "-j" << jt;
            NodePath ijtile(oss.str());
            double x, y;
            for (int cut = 0; cut < numcuts; ++cut) {
                NodePath &ctile = tiles[cut][it][jt];
                const LPoint2d &cxy = tilexys[cut][it][jt];
                x = cxy[0]; y = cxy[1];
                ctile.reparent_to(ijtile);
            }
            PT(LODNode) ijtlod = new LODNode("lod-visradius");
            NodePath ijtlnp(ijtlod);
            ijtlnp.reparent_to(tileroot);
            ijtlnp.set_pos(x, y, 0.0); // all cuts have same (x, y)
            ijtlod->add_switch(dummyoutvisradius, 0.0);
            ijtile.reparent_to(ijtlnp);
        }
    }

    // Derive maximum heights for faster terrain collision check.
    maxz = -1e30;
    maxqzs = std::vector<double>(numquadsx * numquadsy, 0.0);
    for (int i = 0; i < numquadsx; ++i) {
        for (int j = 0; j < numquadsy; ++j) {
            int q = i * numquadsy + j;
            double maxqz = -1e30;
            for (int k = quadmap[q][0]; k < quadmap[q][1]; ++k) {
                for (int d = 0; d < 3; ++d) {
                    int l = tris[k][d];
                    maxqz = std::max(maxqz, verts[l][2]);
                }
            }
            maxqzs[q] = maxqz;
            maxz = std::max(maxz, maxqz);
        }
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-cumulative:  time=%.3f[s]\n", t2 - t0);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    numquadsx_ = numquadsx; numquadsy_ = numquadsy;
    numtilesx_ = numtilesx; numtilesy_ = numtilesy;
    tilesizex_ = tilesizex; tilesizey_ = tilesizey;
    numcuts_ = numcuts;
    centerx_ = centerx; centery_ = centery;
    maxsizexa_ = maxsizexa; maxsizexb_ = maxsizexb; maxsizey_ = maxsizey;

    tileroot_ = tileroot;

    for (FlatsIter it = flats.begin(); it != flats.end(); ++it) {
        delete *it;
    }
}

void TerrainGeom::_derive_cell_data (
    double celldensity,
    double size, double hmapsize, int numtiles,
    int &numquads, double &tilesize, int &numtilequads)
{
    tilesize = size / numtiles;
    double wquadsize = (size / hmapsize) / sqrt(celldensity);
    numtilequads = int(ceil(tilesize / wquadsize));
    numquads = numtiles * numtilequads;
}

void TerrainGeom::_read_heightmap_data (
    const std::string &fpath,
    double &sxa, double &sxb, double &sy,
    double &mnz, double &mxz, int &mng, int &mxg,
    std::vector<Flat*> &flats)
{
    MiniConfigParser mhdat(fpath);
    std::string extsec("extents");
    if (!mhdat.has_section(extsec)) {
        fprintf(stderr,
            "No '%s' section in heightmap data file '%s'.\n",
            extsec.c_str(), fpath.c_str());
        std::exit(1);
    }
    std::string sxfld("sizex"), sxafld("sizexs"), sxbfld("sizexn");
    double xymult = 1000.0;
    if (mhdat.has_option(extsec, sxafld) && mhdat.has_option(extsec, sxbfld)) {
        sxa = mhdat.get_real(extsec, sxafld) * xymult;
        sxb = mhdat.get_real(extsec, sxbfld) * xymult;
    } else if (mhdat.has_option(extsec, sxfld)) {
        sxa = mhdat.get_real(extsec, sxfld) * xymult;
        sxb = sxa;
    } else {
        fprintf(stderr,
            "No field '%s' nor fields '%s' and '%s' in section '%s' "
            "in file '%s'.\n",
            sxfld.c_str(), sxafld.c_str(), sxbfld.c_str(),
            extsec.c_str(), fpath.c_str());
        std::exit(1);
    }
    sy = mhdat.get_real(extsec, "sizey") * xymult;
    mnz = mhdat.get_real(extsec, "minz");
    mxz = mhdat.get_real(extsec, "maxz");
    mng = mhdat.get_int(extsec, "ming", 0);
    mxg = mhdat.get_int(extsec, "maxg", 255);

    std::string flatpref("flat-");
    std::vector<std::string> secs = mhdat.sections();
    for (std::vector<std::string>::const_iterator it = secs.begin(); it != secs.end(); ++it) {
        const std::string &flatsec = *it;
        if (flatsec.find(flatpref) == 0) {
            std::string name = flatsec.substr(flatpref.size());
            double cx = mhdat.get_real(flatsec, "centerx") * xymult;
            double cy = mhdat.get_real(flatsec, "centery") * xymult;
            double cz; bool havecz;
            if (mhdat.has_option(flatsec, "centerz")) {
                cz = mhdat.get_real(flatsec, "centerz");
                havecz = true;
            } else {
                cz = 0.0;
                havecz = false;
            }
            Flat *flat;
            if (mhdat.has_option(flatsec, "radius")) {
                double rad = mhdat.get_real(flatsec, "radius") * xymult;
                double radout = mhdat.get_real(flatsec, "radiusout", 0.0) * xymult;
                flat = new FlatCircle(name, cx, cy, rad, cz, havecz, radout);
            } else {
                fprintf(stderr,
                    "Unknown flat section type '%s' in file '%s'.\n",
                    flatsec.c_str(), mhdat.file_path().c_str());
                std::exit(1);
            }
            flats.push_back(flat);
        }
    }
}

void TerrainGeom::_triangulate (
    const UnitGrid2 &heightmap,
    const std::vector<UnitGrid2> &cutmasks,
    const std::vector<bool> &levints,
    double maxsizexa, double maxsizexb, double maxsizey,
    double centerx, double centery,
    double sizex, double sizey, double offsetx, double offsety,
    int numquadsx, int numquadsy,
    int mingray, int maxgray, double minheight, double maxheight,
    std::vector<Flat*> &flats,
    int cintdiv, double cintlam, double cintmu, int cintiter,
    bool periodic, bool timeit, bool memit,
    std::vector<LVector3d> &verts,
    std::vector<LVector4i> &tris,
    std::vector<LVector2i> &quadmap,
    double &lasttime)
{
    double t0, t1, t2;
    if (timeit) {
        t0 = stime();
        t1 = t0;
    }

    double quadsizex = sizex / numquadsx;
    double quadsizey = sizey / numquadsy;

    // When converting coordinates to non-periodic unit square,
    // they may fall slightly out of range due to rounding.
    // This is the tolerance to accept that and move to nearest boundary.
    // The value should work for single precision too.
    double usqtol = 1e-4;

    // Assemble the cut map.
    std::vector<std::vector<int> > cutmap;
    for (int i = 0; i < numquadsx + 1; ++i) {
        cutmap.push_back(std::vector<int>(numquadsy + 1, 0));
    }
    for (int k = 0; k < cutmasks.size(); ++k) {
        const UnitGrid2 &cutmask = cutmasks[k];
        int c = k + 1;
        for (int i = 0; i < numquadsx + 1; ++i) {
            double x = i * quadsizex + offsetx;
            for (int j = 0; j < numquadsy + 1; ++j) {
                double y = j * quadsizey + offsety;
                LVector2d xyu = _to_unit_trap(
                    sizex, sizey, offsetx, offsety, maxsizexa, maxsizexb,
                    maxsizey, centerx, centery,
                    x, y);
                double xu = xyu[0], yu = xyu[1];
                double cval = cutmask(xu, yu, usqtol, periodic);
                if (cval > 0.5) {
                    cutmap[i][j] = c;
                }
            }
        }
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-assemble-cut-map:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Split cut interface quads into triangles.
    // NOTE: May modify the cut map, to repair problematic areas.
    std::vector<std::vector<IntQuadChainPart> > intquadchains;
    std::vector<bool> intquadchains_closed;
    std::vector<LVector3d> intquadverts;
    std::vector<LVector4i> intquadtris;
    std::vector<IntQuadLink> intquadlinks;
    std::vector<std::vector<IntCurvePart> > intcurves;
    std::vector<bool> intcurves_closed;
    _split_interface_quads(cutmap, quadsizex, quadsizey,
                           offsetx, offsety, cintdiv,
                           cintlam, cintmu, cintiter,
                           intquadchains, intquadchains_closed,
                           intquadverts, intquadtris, intquadlinks,
                           intcurves, intcurves_closed);

    if (timeit) {
        t2 = stime();
        printf("terrain-compute-cut-interfaces:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Compute quad vertices.
    int niqverts = intquadverts.size();
    int nverts = (numquadsx + 1) * (numquadsy + 1) + niqverts;
    verts = std::vector<LVector3d>(nverts);
    for (int i = 0; i < numquadsx + 1; ++i) {
        double x = i * quadsizex + offsetx;
        int j0 = i * (numquadsy + 1);
        for (int j = 0; j < numquadsy + 1; ++j) {
            double y = j * quadsizey + offsety;
            verts[j0 + j][0] = x;
            verts[j0 + j][1] = y;
        }
    }

    // Add cut interface vertices.
    int i0 = (numquadsx + 1) * (numquadsy + 1);
    for (int i = 0; i < niqverts; ++i) {
        verts[i0 + i][0] = intquadverts[i][0];
        verts[i0 + i][1] = intquadverts[i][1];
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-compute-quad-vertices:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Add global links for cut interface triangles.
    int nquads = numquadsx * numquadsy;
    quadmap = std::vector<LVector2i>(nquads, LVector2i(-1, -1));
    for (int k = 0; k < intquadlinks.size(); ++k) {
        const IntQuadLink &iql = intquadlinks[k];
        int i = iql.i, j = iql.j;
        int itri1 = iql.itri1, itri2 = iql.itri2;
        int q = i * numquadsy + j;
        quadmap[q][0] = itri1; quadmap[q][1] = itri2;
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-add-quad-links:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Split non-interface quads into triangles and add global links.
    int niqtris = intquadtris.size();
    int ntris = 2 * (numquadsx * numquadsy - intquadlinks.size()) + niqtris;
    tris = std::vector<LVector4i>(ntris);
    int k = 0;
    for (int i = 0; i < numquadsx; ++i) {
        for (int j = 0; j < numquadsy; ++j) {
            int q = i * numquadsy + j;
            if (quadmap[q][0] >= 0) { // interface quad
                continue;
            }
            // Indices of vertices.
            int k1 = i * (numquadsy + 1) + j;
            int k2 = (i + 1) * (numquadsy + 1) + j;
            int k3 = (i + 1) * (numquadsy + 1) + (j + 1);
            int k4 = i * (numquadsy + 1) + (j + 1);
            // All four points from same cut (not interface quad).
            int c = cutmap[i][j];
            // Whether to split this quad bottom-left top-right.
            int bltr = (i % 2 + j) % 2;
            LVector4i &tri1 = tris[k], &tri2 = tris[k + 1];
            if (bltr) {
                tri1[0] = k1; tri1[1] = k2; tri1[2] = k3; tri1[3] = c;
                tri2[0] = k1; tri2[1] = k3; tri2[2] = k4; tri2[3] = c;
            } else {
                tri1[0] = k2; tri1[1] = k3; tri1[2] = k4; tri1[3] = c;
                tri2[0] = k2; tri2[1] = k4; tri2[2] = k1; tri2[3] = c;
            }
            // Quad to triangle links.
            quadmap[q][0] = k;
            quadmap[q][1] = k + 2;
            k += 2;
        }
    }

    // Add cut interface triangles.
    int k0 = ntris - niqtris;
    for (int k = 0; k < niqtris; ++k) {
        tris[k0 + k] = intquadtris[k];
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-assemble-triangulation:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Equip flats with heights.
    for (int i = 0; i < flats.size(); ++i) {
        Flat *flat = flats[i];
        if (!flat->have_refz()) {
            LVector2d fxy = flat->refxy();
            double fx = fxy[0], fy = fxy[1];
            double fz = _get_z_at_world_xy(
                heightmap,
                maxsizexa, maxsizexb, maxsizey,
                sizex, sizey, offsetx, offsety, centerx, centery,
                mingray, maxgray, minheight, maxheight,
                usqtol, periodic,
                fx, fy);
            flat->set_refz(fz, true);
        }
    }

    // Equip vertices with heights.
    for (int i = 0; i < nverts; ++i) {
        double x = verts[i][0], y = verts[i][1];
        double z = _get_z_at_world_xy(
            heightmap,
            maxsizexa, maxsizexb, maxsizey,
            sizex, sizey, offsetx, offsety, centerx, centery,
            mingray, maxgray, minheight, maxheight,
            usqtol, periodic,
            x, y);
        for (int j = 0; j < flats.size(); ++j) {
            const Flat *flat = flats[j];
            double zc; bool havezc;
            flat->correct_z(x, y, z, zc, havezc);
            if (havezc) {
                z = zc;
                break;
            }
        }
        verts[i][2] = z;
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-compute-per-vertex-heights:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }

    // Level heights at interface vertices.
    int l0 = nverts - niqverts;
    for (int ic = 0; ic < intquadchains.size(); ++ic) {
        const std::vector<IntCurvePart> &intcurve = intcurves[ic];
        const std::vector<IntQuadChainPart> &intquadchain = intquadchains[ic];
        bool closed = intquadchains_closed[ic];
        int cl, cr;
        _interface_cut_levels(cutmap, intquadchain, cl, cr);
        if (levints[cl] || levints[cr]) {
            int l1 = l0 + intcurve.size();
            std::vector<int> cvinds(l1 - l0);
            for (int l = l0; l < l1; ++l) {
                cvinds[l - l0] = l;
            }
            _level_curve_to_left(sizex, sizey, offsetx, offsety,
                                 numquadsx, numquadsy,
                                 verts, tris, quadmap,
                                 cvinds, closed, cl);
        }
        l0 += intcurve.size();
    }

    if (timeit) {
        t2 = stime();
        printf("terrain-level-interface-vertices:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }
    if (memit) {
        std::system("echo mem `free -m | grep rs/ca | sed 's/  */ /g' | cut -d ' ' -f 3`");
    }
    if (timeit) {
        lasttime = t1;
    }
}

double TerrainGeom::_get_z_at_world_xy (
    const UnitGrid2 &heightmap,
    double maxsizexa, double maxsizexb, double maxsizey,
    double sizex, double sizey, double offsetx, double offsety,
    double centerx, double centery,
    int mingray, int maxgray, double minheight, double maxheight,
    double usqtol, bool periodic,
    double x, double y)
{
    LVector2d xyu = _to_unit_trap(sizex, sizey, offsetx, offsety,
                                    maxsizexa, maxsizexb, maxsizey,
                                    centerx, centery,
                                    x, y);
    double xu = xyu[0], yu = xyu[1];
    double hval = heightmap(xu, yu, usqtol, periodic);
    double hpv = (maxheight - minheight) / ((maxgray - mingray) / 255.0);
    double z = minheight + (hval - mingray / 255.0) * hpv;
    return z;
}

LVector2d TerrainGeom::_to_unit_trap (
    double sizex, double sizey, double offsetx, double offsety,
    double maxsizexa, double maxsizexb, double maxsizey,
    double centerx, double centery,
    double x, double y)
{
    double x1 = (x - offsetx) + centerx;
    double y1 = (y - offsety) + centery;
    double y1u = y1 / maxsizey + 0.5 * (1.0 - sizey / maxsizey);
    double maxsizex = maxsizexa + (maxsizexb - maxsizexa) * y1u;
    double x1u = x1 / maxsizex + 0.5 * (1.0 - sizex / maxsizex);
    return LVector2d(x1u, y1u);
}

void TerrainGeom::_split_interface_quads (
    std::vector<std::vector<int> > &cutmap,
    double quadsizex, double quadsizey,
    double offsetx, double offsety,
    int subdiv,
    double tbslam, double tbsmu, int tbsiter,
    std::vector<std::vector<IntQuadChainPart> > &intquadchains,
    std::vector<bool> &intquadchains_closed,
    std::vector<LVector3d> &intquadverts,
    std::vector<LVector4i> &intquadtris,
    std::vector<IntQuadLink> &intquadlinks,
    std::vector<std::vector<IntCurvePart> > &intcurves,
    std::vector<bool> &intcurves_closed)
{
    int numquadsx = cutmap.size() - 1;
    int numquadsy = cutmap[0].size() - 1;

    // Correct thin diagonal cuts.
    double anythin = true;
    while (anythin) {
        anythin = false;
        for (int i = 0; i < numquadsx; ++i) {
            for (int j = 0; j < numquadsy; ++j) {
                int c1 = cutmap[i][j];
                int c2 = cutmap[i + 1][j];
                int c3 = cutmap[i + 1][j + 1];
                int c4 = cutmap[i][j + 1];
                if (c1 == c3 && c2 == c4 && c1 != c2) {
                    if (c1 > c2) {
                        cutmap[i][j + 1] = c1;
                    } else {
                        cutmap[i][j] = c2;
                    }
                    anythin = true;
                }
            }
        }
    }

    // Collect interface quad chains.
    std::vector<std::vector<int> > freemap;
    for (int i = 0; i < numquadsx; ++i) {
        freemap.push_back(std::vector<int>(numquadsy, 1));
    }
    for (int i = 0; i < numquadsx; ++i) {
        for (int j = 0; j < numquadsy; ++j) {
            if (freemap[i][j]) {
                int c1 = cutmap[i][j];
                int c2 = cutmap[i + 1][j];
                int c3 = cutmap[i + 1][j + 1];
                int c4 = cutmap[i][j + 1];
                std::set<int> cset;
                cset.insert(c1); cset.insert(c2); cset.insert(c3); cset.insert(c4);
                if (cset.size() == 2) {
                    std::vector<int> ocset(cset.begin(), cset.end());
                    std::sort(ocset.begin(), ocset.end());
                    // ...std::set is sorted, but for changing to std::unordered_set later.
                    int cr = ocset[0], cl = ocset[1];
                    // ...this order places the higher cut on the left of
                    // the oriented interface curve.
                    std::vector<IntQuadChainPart> intquadchain;
                    bool closed;
                    _extract_interface_quads(
                        cutmap, i, j, cl, cr, freemap,
                        intquadchain, closed);
                    intquadchains.push_back(intquadchain);
                    intquadchains_closed.push_back(closed);
                    //printf("--chain %d %d\n", intquadchain.size(), closed);
                } else if (cset.size() > 2) {
                    fprintf(stderr,
                        "Neighboring points from more than two cuts "
                        "at (%d, %d).\n", i, j);
                    std::exit(1);
                }
            }
        }
    }

    // Construct interface curves.
    for (int q = 0; q < intquadchains.size(); ++q) {
        const std::vector<IntQuadChainPart> &intquadchain = intquadchains[q];
        bool closed = intquadchains_closed[q];
        std::vector<IntCurvePart> intcurve;
        double fromcut = 0.5;
        _init_interface_curve(
            cutmap, intquadchain, closed,
            quadsizex, quadsizey, offsetx, offsety,
            subdiv, fromcut,
            intcurve);
        _smooth_interface_curve(intcurve, closed,
                                subdiv, tbslam, tbsmu, tbsiter);
        intcurves.push_back(intcurve);
        intcurves_closed.push_back(closed);
    }

    // Number of quad vertices and triangles in non-interface quads,
    // which are added in front of interface-related vertices and triangles.
    int nverts0 = (numquadsx + 1) * (numquadsy + 1);
    int ntris0 = 2 * numquadsx * numquadsy;
    for (int q = 0; q < intquadchains.size(); ++q) {
        ntris0 -= 2 * intquadchains[q].size();
    }

    // Triangulate interface quads.
    for (int q = 0; q < intquadchains.size(); ++q) {
        const std::vector<IntQuadChainPart> &intquadchain = intquadchains[q];
        const std::vector<IntCurvePart> &intcurve = intcurves[q];
        std::vector<LVector3d> cverts;
        std::vector<LVector4i> ctris;
        std::vector<IntQuadLink> clinks;
        _triangulate_interface_quads(
            cutmap, quadsizex, quadsizey, offsetx, offsety,
            intquadchain, intcurve, subdiv, nverts0, ntris0,
            cverts, ctris, clinks);
        intquadverts.insert(intquadverts.end(), cverts.begin(), cverts.end());
        intquadtris.insert(intquadtris.end(), ctris.begin(), ctris.end());
        intquadlinks.insert(intquadlinks.end(), clinks.begin(), clinks.end());
        nverts0 += cverts.size();
        ntris0 += ctris.size();
    }
}

void TerrainGeom::_extract_interface_quads (
    const std::vector<std::vector<int> > &cutmap,
    int i0, int j0, int cl, int cr,
    std::vector<std::vector<int> > &freemap,
    std::vector<IntQuadChainPart> &intquadchain,
    bool &closed)
{

    // Collect and join the two chain segments split by the given point.
    closed = true;
    for (int i = 0; i < 2; ++i) {
        std::vector<IntQuadChainPart> qcpart;
        bool cutbdry;
        _extract_interface_quads_1(
            cutmap, i0, j0, cl, cr, freemap,
            qcpart, cutbdry);
        closed = closed && !cutbdry;
        if (i == 0) {
            intquadchain.insert(intquadchain.end(), qcpart.rbegin(), qcpart.rend());
        } else { // i == 1
            intquadchain.insert(intquadchain.end(), qcpart.begin() + 1, qcpart.end());
        }
    }

    // Orient the chain so that it runs counter-clockwise around the cut.
    int c0l, c0r;
    _interface_cut_levels(cutmap, intquadchain, c0l, c0r);
    if (c0l != cl) {
        std::reverse(intquadchain.begin(), intquadchain.end());
    }
}

void TerrainGeom::_extract_interface_quads_1 (
    const std::vector<std::vector<int> > &cutmap,
    int i0, int j0, int cl, int cr,
    std::vector<std::vector<int> > &freemap,
    std::vector<IntQuadChainPart> &intquadchain,
    bool &cutbdry)
{
    int numquadsx = cutmap.size() - 1;
    int numquadsy = cutmap[0].size() - 1;

    int i = i0, j = j0;
    while (true) {
        freemap[i][j] = 0;
        int seli = -1, selj = -1;
        cutbdry = false;
        int ncl = 0;
        int dis[] = {1, 0, -1, 0};
        int djs[] = {0, 1, 0, -1};
        int di1s[] = {1, 1, 0, 0};
        int dj1s[] = {0, 1, 1, 0};
        int di2s[] = {1, 0, 0, 1};
        int dj2s[] = {1, 1, 0, 0};
        for (int w = 0; w < 4; ++w) {
            int di = dis[w], dj = djs[w];
            int di1 = di1s[w], dj1 = dj1s[w];
            int di2 = di2s[w], dj2 = dj2s[w];
            int c1 = cutmap[i + di1][j + dj1];
            int c2 = cutmap[i + di2][j + dj2];
            if (c1 == cl) {
                ncl += 1;
                if (i + di1 == 0 || i + di1 == numquadsx ||
                    j + dj1 == 0 || j + dj1 == numquadsy) {
                    cutbdry = true;
                }
            }
            if (seli < 0 &&
                0 <= i + di && i + di < numquadsx &&
                0 <= j + dj && j + dj < numquadsy &&
                freemap[i + di][j + dj] &&
                (c1 == cl || c2 == cl) &&
                c1 != c2) {
                seli = i + di; selj = j + dj;
            }
        }
        IntQuadChainPart iqcl(i, j, ncl);
        intquadchain.push_back(iqcl);
        if (seli >= 0) {
            i = seli; j = selj;
        } else {
            break;
        }
    }
}

void TerrainGeom::_init_interface_curve (
    const std::vector<std::vector<int> > &cutmap,
    const std::vector<IntQuadChainPart> &intquadchain,
    bool closed,
    double quadsizex, double quadsizey, double offsetx, double offsety,
    int subdiv, double fromcut,
    std::vector<IntCurvePart> &intcurve)
{
    #undef Vt
    #define Vt LVector3d

    double qsx = quadsizex, qsy = quadsizey;
    int subdivc = subdiv % 2 == 0 ? subdiv : subdiv + 1;
    int subdivch = subdivc / 2;
    double dx = qsx / subdivc, dy = qsy / subdivc;
    double dxc = dx * 2, dyc = dy * 2;
    double ka = 1.0 - fromcut, kb = fromcut;
    int cl, cr;
    _interface_cut_levels(cutmap, intquadchain, cl, cr);

    // NOTE: The assumption is that the chain is oriented counter-clockwise
    // around the higher cut, i.e. that the higher cut is always on the left.
    int lenqc = intquadchain.size();
    std::pair<int, int> gvnull(-1, -1);
    Vt pa, pb;
    std::pair<int, int> qva, qvb;
    for (int k = 0; k < lenqc; ++k) {
        const IntQuadChainPart &iqcl = intquadchain[k];
        int i = iqcl.i, j = iqcl.j;
        int ncl = iqcl.ncl;
        int c1 = cutmap[i][j];
        int c2 = cutmap[i + 1][j];
        int c3 = cutmap[i + 1][j + 1];
        int c4 = cutmap[i][j + 1];
        double x0 = i * qsx + offsetx, y0 = j * qsy + offsety;
        int sf = (closed || k + 1 < lenqc) ? 0 : 1;
        if (ncl == 1) {
            for (int s = 0; s < subdivch; ++s) {
                if (c1 == cl) {
                    pa = Vt(x0, y0, 0.0);
                    pb = Vt(x0 + qsx, y0 + dyc * s, 0.0);
                    qva = std::make_pair(0, 0);
                    qvb = s == 0 ? std::make_pair(1, 0) : gvnull;
                } else if (c2 == cl) {
                    pa = Vt(x0 + qsx, y0, 0.0);
                    pb = Vt(x0 + qsx - dxc * s, y0 + qsy, 0.0);
                    qva = std::make_pair(1, 0);
                    qvb = s == 0 ? std::make_pair(1, 1) : gvnull;
                } else if (c3 == cl) {
                    pa = Vt(x0 + qsx, y0 + qsy, 0.0);
                    pb = Vt(x0, y0 + qsy - dyc * s, 0.0);
                    qva = std::make_pair(1, 1);
                    qvb = s == 0 ? std::make_pair(0, 1) : gvnull;
                } else if (c4 == cl) {
                    pa = Vt(x0, y0 + qsy, 0.0);
                    pb = Vt(x0 + dxc * s, y0, 0.0);
                    qva = std::make_pair(0, 1);
                    qvb = s == 0 ? std::make_pair(0, 0) : gvnull;
                }
                IntCurvePart icp(pa * ka + pb * kb, pa, pb, qva, qvb);
                intcurve.push_back(icp);
            }
            for (int s = 0; s < subdivch + sf; ++s) {
                if (c1 == cl) {
                    pa = Vt(x0, y0, 0.0);
                    pb = Vt(x0 + qsx - dxc * s, y0 + qsy, 0.0);
                    qva = std::make_pair(0, 0);
                    qvb = s == 0 ? std::make_pair(1, 1) :
                          s == subdivch ? std::make_pair(0, 1) : gvnull;
                } else if (c2 == cl) {
                    pa = Vt(x0 + qsx, y0, 0.0);
                    pb = Vt(x0, y0 + qsy - dyc * s, 0.0);
                    qva = std::make_pair(1, 0);
                    qvb = s == 0 ? std::make_pair(0, 1) :
                          s == subdivch ? std::make_pair(0, 0) : gvnull;
                } else if (c3 == cl) {
                    pa = Vt(x0 + qsx, y0 + qsy, 0.0);
                    pb = Vt(x0 + dxc * s, y0, 0.0);
                    qva = std::make_pair(1, 1);
                    qvb = s == 0 ? std::make_pair(0, 0) :
                          s == subdivch ? std::make_pair(1, 0) : gvnull;
                } else if (c4 == cl) {
                    pa = Vt(x0, y0 + qsy, 0.0);
                    pb = Vt(x0 + qsx, y0 + dyc * s, 0.0);
                    qva = std::make_pair(0, 1);
                    qvb = s == 0 ? std::make_pair(1, 0) :
                          s == subdivch ? std::make_pair(1, 1) : gvnull;
                }
                IntCurvePart icp(pa * ka + pb * kb, pa, pb, qva, qvb);
                intcurve.push_back(icp);
            }
        } else if (ncl == 2) {
            for (int s = 0; s < subdivc + sf; ++s) {
                if (c1 == cl && c2 == cl) {
                    pa = Vt(x0 + qsx - dx * s, y0, 0.0);
                    pb = Vt(x0 + qsx - dx * s, y0 + qsy, 0.0);
                    qva = s == 0 ? std::make_pair(1, 0) :
                          s == subdivc ? std::make_pair(0, 0) : gvnull;
                    qvb = s == 0 ? std::make_pair(1, 1) :
                          s == subdivc ? std::make_pair(0, 1) : gvnull;
                } else if (c2 == cl && c3 == cl) {
                    pa = Vt(x0 + qsx, y0 + qsy - dy * s, 0.0);
                    pb = Vt(x0, y0 + qsy - dy * s, 0.0);
                    qva = s == 0 ? std::make_pair(1, 1) :
                          s == subdivc ? std::make_pair(1, 0) : gvnull;
                    qvb = s == 0 ? std::make_pair(0, 1) :
                          s == subdivc ? std::make_pair(0, 0) : gvnull;
                } else if (c3 == cl && c4 == cl) {
                    pa = Vt(x0 + dx * s, y0 + qsy, 0.0);
                    pb = Vt(x0 + dx * s, y0, 0.0);
                    qva = s == 0 ? std::make_pair(0, 1) :
                          s == subdivc ? std::make_pair(1, 1) : gvnull;
                    qvb = s == 0 ? std::make_pair(0, 0) :
                          s == subdivc ? std::make_pair(1, 0) : gvnull;
                } else if (c4 == cl && c1 == cl) {
                    pa = Vt(x0, y0 + dy * s, 0.0);
                    pb = Vt(x0 + qsx, y0 + dy * s, 0.0);
                    qva = s == 0 ? std::make_pair(0, 0) :
                          s == subdivc ? std::make_pair(0, 1) : gvnull;
                    qvb = s == 0 ? std::make_pair(1, 0) :
                          s == subdivc ? std::make_pair(1, 1) : gvnull;
                }
                IntCurvePart icp(pa * ka + pb * kb, pa, pb, qva, qvb);
                intcurve.push_back(icp);
            }
        } else if (ncl == 3) {
            for (int s = 0; s < subdivc / 2; ++s) {
                if (c1 == cr) {
                    pa = Vt(x0 + dxc * s, y0 + qsy, 0.0);
                    pb = Vt(x0, y0, 0.0);
                    qva = s == 0 ? std::make_pair(0, 1) : gvnull;
                    qvb = std::make_pair(0, 0);
                } else if (c2 == cr) {
                    pa = Vt(x0, y0 + dyc * s, 0.0);
                    pb = Vt(x0 + qsx, y0, 0.0);
                    qva = s == 0 ? std::make_pair(0, 0) : gvnull;
                    qvb = std::make_pair(1, 0);
                } else if (c3 == cr) {
                    pa = Vt(x0 + qsx - dxc * s, y0, 0.0);
                    pb = Vt(x0 + qsx, y0 + qsy, 0.0);
                    qva = s == 0 ? std::make_pair(1, 0) : gvnull;
                    qvb = std::make_pair(1, 1);
                } else if (c4 == cr) {
                    pa = Vt(x0 + qsx, y0 + qsy - dyc * s, 0.0);
                    pb = Vt(x0, y0 + qsy, 0.0);
                    qva = s == 0 ? std::make_pair(1, 1) : gvnull;
                    qvb = std::make_pair(0, 1);
                }
                IntCurvePart icp(pa * ka + pb * kb, pa, pb, qva, qvb);
                intcurve.push_back(icp);
            }
            for (int s = 0; s < subdivc / 2 + sf; ++s) {
                if (c1 == cr) {
                    pa = Vt(x0 + qsx, y0 + qsy - dyc * s, 0.0);
                    pb = Vt(x0, y0, 0.0);
                    qva = s == 0 ? std::make_pair(1, 1) :
                          s == subdivch ? std::make_pair(0, 1) : gvnull;
                    qvb = std::make_pair(0, 0);
                } else if (c2 == cr) {
                    pa = Vt(x0 + dxc * s, y0 + qsy, 0.0);
                    pb = Vt(x0 + qsx, y0, 0.0);
                    qva = s == 0 ? std::make_pair(0, 1) :
                          s == subdivch ? std::make_pair(1, 1) : gvnull;
                    qvb = std::make_pair(1, 0);
                } else if (c3 == cr) {
                    pa = Vt(x0, y0 + dyc * s, 0.0);
                    pb = Vt(x0 + qsx, y0 + qsy, 0.0);
                    qva = s == 0 ? std::make_pair(0, 0) :
                          s == subdivch ? std::make_pair(0, 1) : gvnull;
                    qvb = std::make_pair(1, 1);
                } else if (c4 == cr) {
                    pa = Vt(x0 + qsx - dxc * s, y0, 0.0);
                    pb = Vt(x0, y0 + qsy, 0.0);
                    qva = s == 0 ? std::make_pair(1, 0) :
                          s == subdivch ? std::make_pair(0, 0) : gvnull;
                    qvb = std::make_pair(0, 1);
                }
                IntCurvePart icp(pa * ka + pb * kb, pa, pb, qva, qvb);
                intcurve.push_back(icp);
            }
        }
    }
}

void TerrainGeom::_smooth_interface_curve (
    std::vector<IntCurvePart> &intcurve,
    bool closed, int subdiv,
    double tbslam, double tbsmu, int tbsiter)
{
    #undef Pt
    #define Pt LVector3d

    double mindf = 0.05; // minimum distance from segment start
    double maxdf = 0.95; // maximum distance from segment start

    // NOTE: Taubin smoothing algorithm.
    for (int p = 0; p < tbsiter; ++p) {
        double scfs[] = {tbslam, tbsmu};
        for (int w = 0; w < 2; ++w) {
            double scf = scfs[w];
            if (scf == 0.0) {
                continue;
            }
            int lenic = intcurve.size();

            /*
            // Jacobi iteration.
            std::vector<IntCurvePart> intcurve1;
            for (int k = 0; k < lenic; ++k) {
                const IntCurvePart &icp = intcurve[k];
                const Pt &pc = icp.pc, &pa = icp.pa, &pb = icp.pb;
                Pt pc2(pc);
                if ((0 < k && k < lenic - 1) || closed) {
                    int km = k > 0 ? k - 1 : lenic - 1;
                    int kp = k < lenic - 1 ? k + 1 : 0;
                    Pt pc1(pc);
                    int ks[] = {km, kp};
                    double ws[] = {0.5, 0.5};
                    for (int o = 0; o < 2; ++o) {
                        int k1 = ks[o];
                        double w1 = ws[o];
                        Pt dp1 = intcurve[k1].pc - pc;
                        pc1 += dp1 * (w1 * scf);
                    }
                    // Limit back to originating segment.
                    Pt ab = pb - pa;
                    double mab = ab.length();
                    Pt abu = ab / mab;
                    Pt ac = pc1 - pa;
                    double acabu = ac.dot(abu);
                    if (acabu < mindf * mab) {
                        acabu = mindf * mab;
                    } else if (acabu > maxdf * mab) {
                        acabu = maxdf * mab;
                    }
                    pc2 = pa + abu * acabu;
                }
                IntCurvePart icp2 = icp;
                icp2.pc = pc2;
                intcurve1.push_back(icp2);
            }
            intcurve = intcurve1;
            */

            // Gauss iteration.
            for (int k = 0; k < lenic; ++k) {
                IntCurvePart &icp = intcurve[k];
                Pt &pc = icp.pc;
                const Pt &pa = icp.pa, &pb = icp.pb;
                if ((0 < k && k < lenic - 1) || closed) {
                    int km = k > 0 ? k - 1 : lenic - 1;
                    int kp = k < lenic - 1 ? k + 1 : 0;
                    Pt pc1(pc);
                    int ks[] = {km, kp};
                    double ws[] = {0.5, 0.5};
                    for (int o = 0; o < 2; ++o) {
                        int k1 = ks[o];
                        double w1 = ws[o];
                        Pt dp1 = intcurve[k1].pc - pc;
                        pc1 += dp1 * (w1 * scf);
                    }
                    // Limit back to originating segment.
                    Pt ab = pb - pa;
                    double mab = ab.length();
                    Pt abu = ab / mab;
                    Pt ac = pc1 - pa;
                    double acabu = ac.dot(abu);
                    if (acabu < mindf * mab) {
                        acabu = mindf * mab;
                    } else if (acabu > maxdf * mab) {
                        acabu = maxdf * mab;
                    }
                    Pt pc2 = pa + abu * acabu;
                    pc = pc2;
                }
            }
        }
    }

    /*
    double mind = 1e30;
    for (int k = 0; k < intcurve_pc.size(); ++k) {
        const Pt &pa = intcurve[k].pa, &pb = intcurve[k].pb;
        mind = std::min(mind, std::min((pc - pa).length(), (pc - pb).length()));
    }
    printf("--curve-mindist-ab %f\n", mind);
    */
}

void TerrainGeom::_level_curve_to_left (
    double sizex, double sizey, double offsetx, double offsety,
    int numquadsx, int numquadsy,
    std::vector<LVector3d> &verts,
    const std::vector<LVector4i> &tris,
    const std::vector<LVector2i> &quadmap,
    const std::vector<int> &cvinds, bool closed, int lcut)
{
    #undef Vt
    #define Vt LVector3d

    double quadsizex = sizex / numquadsx;
    double quadsizey = sizey / numquadsy;
    double rhlen0 = 2 * sqrt(POW2(quadsizex) + POW2(quadsizey));
    double dhrlen = 0.11 * rhlen0;

    LPoint3 refpt(0.0, 0.0, 0.0);

    int lenv = cvinds.size();
    for (int k = 0; k < lenv; ++k) {
        if (!((0 < k && k < lenv - 1) || closed)) {
            continue;
        }
        int km = k > 0 ? k - 1 : lenv - 1;
        int kp = k < lenv - 1 ? k + 1 : 0;
        int l = cvinds[k], lm = cvinds[km], lp = cvinds[kp];
        // Compute right-hand xy-projected normal at this vertex.
        Vt v(verts[l][0], verts[l][1], 0.0);
        Vt vm(verts[lm][0], verts[lm][1], 0.0);
        Vt vp(verts[lp][0], verts[lp][1], 0.0);
        Vt dvm = v - vm; Vt nm(-dvm[1], dvm[0], 0.0); double lenm = dvm.length();
        Vt dvp = vp - v; Vt np(-dvp[1], dvp[0], 0.0); double lenp = dvp.length();
        Vt n = unitv((nm * lenp + np * lenm) / (lenm + lenp));
        // Take minimum height from a segment along the normal.
        double rhlen = rhlen0;
        double zmin; bool have_zmin = false;
        std::vector<int> atvinds;
        while (rhlen > 0.0) {
            Vt ph = v + n * rhlen;
            LVector3d pcz;
            LVector3d norm; bool wnorm = false;
            LVector3i tvinds; bool wtvinds = true;
            _interpolate_z(
                sizex, sizey, offsetx, offsety, numquadsx, numquadsy,
                verts, tris, quadmap, ph[0], ph[1], refpt,
                pcz, norm, wnorm, tvinds, wtvinds);
            double p = pcz[0], z = pcz[2]; int c = pcz[1];
            if (c == lcut) {
                for (int d = 0; d < 3; ++d) {
                    atvinds.push_back(tvinds[d]);
                }
                if (!have_zmin || zmin > z) {
                    have_zmin = true;
                    zmin = z;
                }
            }
            rhlen -= dhrlen;
        }
        if (have_zmin) {
            verts[l][2] = zmin;
            for (int w = 0; w < atvinds.size(); ++w) {
                int la = atvinds[w];
                verts[la][2] = zmin;
            }
        }
    }
}

void TerrainGeom::_triangulate_interface_quads (
    const std::vector<std::vector<int> > &cutmap,
    double quadsizex, double quadsizey, double offsetx, double offsety,
    const std::vector<IntQuadChainPart> &intquadchain,
    const std::vector<IntCurvePart> &intcurve, int subdiv,
    int nverts0, int ntris0,
    std::vector<LVector3d> &verts,
    std::vector<LVector4i> &tris,
    std::vector<IntQuadLink> &links)
{
    int numquadsx = cutmap.size() - 1;
    int numquadsy = cutmap[0].size() - 1;

    int subdivc = subdiv % 2 == 0 ? subdiv : subdiv + 1;
    int cl, cr;
    _interface_cut_levels(cutmap, intquadchain, cl, cr);

    int lenqc = intquadchain.size();
    int lenic = intcurve.size();

    // Collect interface vertices, assign them indices.
    // Collect associated quad corner point coordinates.
    std::vector<std::pair<int, int> > vqvas, vqvbs;
    std::vector<int> vinds;
    int nverts1 = nverts0;
    int kc = 0;
    for (int kq = 0; kq < lenqc; ++kq) {
        const IntQuadChainPart &iqcl = intquadchain[kq];
        int i = iqcl.i, j = iqcl.j;
        int ncl = iqcl.ncl;
        int sf = 0;
        if (kq == lenqc - 1 && kc + subdivc == lenic - 1) { // open curve
            sf = 1;
        }
        for (int lc = 0; lc < subdivc + sf; ++lc) {
            int kc1 = kc + lc;
            const IntCurvePart &icp = intcurve[kc1];
            const LVector3d &pc = icp.pc;
            const std::pair<int, int> &qva = icp.qva, &qvb = icp.qvb;
            verts.push_back(pc);
            vqvas.push_back(qva.first >= 0 ? make_pair(i + qva.first, j + qva.second) : make_pair(-1, -1));
            vqvbs.push_back(qvb.first >= 0 ? make_pair(i + qvb.first, j + qvb.second) : make_pair(-1, -1));
            vinds.push_back(nverts1);
            nverts1 += 1;
        }
        kc += subdivc;
    }

    // Triangulate left and right of curve in each interface quad.
    int ntris1 = ntris0;
    kc = 0;
    for (int kq = 0; kq < lenqc; ++kq) {
        const IntQuadChainPart &iqcl = intquadchain[kq];
        int i = iqcl.i, j = iqcl.j;
        int ncl = iqcl.ncl;

        // Collect interface vertex data in this quad.
        std::vector<int> iqvdata1_l;
        std::vector<double> iqvdata1_x, iqvdata1_y;
        for (int lc = 0; lc < subdivc + 1; ++lc) {
            int kc1 = (kc + lc) % lenic;
            double xp = verts[kc1][0], yp = verts[kc1][1];
            int lp = vinds[kc1];
            iqvdata1_l.push_back(lp);
            iqvdata1_x.push_back(xp);
            iqvdata1_y.push_back(yp);
        }

        // Order global offsets of quad corner points per side,
        // left-winding for left side, right-winding for right side.
        int kc1 = kc;
        int kcm = kc + subdivc / 2;
        int kc2 = (kc + subdivc) % lenic;
        std::vector<std::pair<int, int> > gvels, gvers;
        if (ncl == 1) {
            gvels.push_back(vqvas[kc1]);
            gvers.push_back(vqvbs[kc2]); gvers.push_back(vqvbs[kcm]); gvers.push_back(vqvbs[kc1]);
        } else if (ncl == 2) {
            gvels.push_back(vqvas[kc2]); gvels.push_back(vqvas[kc1]);
            gvers.push_back(vqvbs[kc2]); gvers.push_back(vqvbs[kc1]);
        } else if (ncl == 3) {
            gvels.push_back(vqvas[kc2]); gvels.push_back(vqvas[kcm]); gvels.push_back(vqvas[kc1]);
            gvers.push_back(vqvbs[kc1]);
        } else {
            fprintf(stderr, "Impossible number of left cut points.\n");
            std::exit(1);
        }

        // Triangulate left and right.
        int cntris = 0;
        int sides[] = {1, -1};
        std::vector<std::pair<int, int> > *gvess[] = {&gvels, &gvers};
        int cs[] = {cl, cr};
        for (int o = 0; o < 2; ++o) {
            int side = sides[o];
            const std::vector<std::pair<int, int> > &gves = *gvess[o];
            int c = cs[o];

            // Collect quad corner vertex data on this side.
            std::vector<int> iqvdata2_l;
            std::vector<double> iqvdata2_x, iqvdata2_y;
            for (int w = 0; w < gves.size(); ++w) { // left winding for left side
                int ie = gves[w].first, je = gves[w].second;
                double xe = ie * quadsizex + offsetx;
                double ye = je * quadsizey + offsety;
                int le = ie * (numquadsy + 1) + je;
                iqvdata2_l.push_back(le);
                iqvdata2_x.push_back(xe);
                iqvdata2_y.push_back(ye);
            }

            // Complete side polygon.
            std::vector<int> iqvdata_l;
            std::vector<double> iqvdata_x, iqvdata_y;
            iqvdata_l.insert(iqvdata_l.end(), iqvdata1_l.begin(), iqvdata1_l.end());
            iqvdata_l.insert(iqvdata_l.end(), iqvdata2_l.begin(), iqvdata2_l.end());
            iqvdata_x.insert(iqvdata_x.end(), iqvdata1_x.begin(), iqvdata1_x.end());
            iqvdata_x.insert(iqvdata_x.end(), iqvdata2_x.begin(), iqvdata2_x.end());
            iqvdata_y.insert(iqvdata_y.end(), iqvdata1_y.begin(), iqvdata1_y.end());
            iqvdata_y.insert(iqvdata_y.end(), iqvdata2_y.begin(), iqvdata2_y.end());
            if (side == -1) { // # right polygon
                std::reverse(iqvdata_l.begin(), iqvdata_l.end());
                std::reverse(iqvdata_x.begin(), iqvdata_x.end());
                std::reverse(iqvdata_y.begin(), iqvdata_y.end());
            }

            // Triangulate the polygon and collect triangles.
            int leniqvd = iqvdata_l.size();
            double avgx = 0.0, avgy = 0.0;
            for (int lq = 0; lq < leniqvd; ++lq) {
                avgx += iqvdata_x[lq]; avgy += iqvdata_y[lq];
            }
            avgx /= leniqvd; avgy /= leniqvd;
            Triangulator tgl;
            //bool showdat = false;
            for (int lq = 0; lq < iqvdata_l.size(); ++lq) {
                int l = iqvdata_l[lq];
                double x = iqvdata_x[lq], y = iqvdata_y[lq];
                //if (l == 1061963) {
                    //showdat = true;
                //}
                // Subtract average coordinates to have numbers
                // as small as possible to avoid roundoff problems.
                int lqt = tgl.add_vertex(x - avgx, y - avgy);
                if (lq != lqt) {
                    fprintf(stderr,
                        "Unexpected behavior of the triangulator, "
                        "changed indices (quad %d, %d).\n", i, j);
                    std::exit(1);
                }
                tgl.add_polygon_vertex(lqt); // Wtf?
            }
            if (!tgl.is_left_winding()) {
                fprintf(stderr,
                    "Unexpected behavior of the triangulator, "
                    "changed winding (quad %d, %d).\n", i, j);
                std::exit(1);
            }
            tgl.triangulate();
            int nqstris = tgl.get_num_triangles();
            for (int t = 0; t < nqstris; ++t) {
                int lq1 = tgl.get_triangle_v0(t);
                int lq2 = tgl.get_triangle_v1(t);
                int lq3 = tgl.get_triangle_v2(t);
                LVector4i tri(iqvdata_l[lq1], iqvdata_l[lq2], iqvdata_l[lq3], c);
                tris.push_back(tri);
                //if (showdat) {
                    //printf("--side-polygon-vertex %d %d %d\n", iqvdata[lq1][0], iqvdata[lq2][0], iqvdata[lq3][0]);
                //}
            }
            cntris += nqstris;
        }

        kc += subdivc;
        IntQuadLink link(i, j, ntris1, ntris1 + cntris);
        links.push_back(link);
        ntris1 += cntris;
    }
}

std::map<std::pair<int, int>, std::pair<int, int> > *TerrainGeom::_dij_ptfwlf = NULL;
std::map<std::pair<int, int>, std::pair<int, int> > *TerrainGeom::_dij_ptfwrg = NULL;

void TerrainGeom::_interface_cut_levels (
    const std::vector<std::vector<int> > &cutmap,
    const std::vector<IntQuadChainPart> &intquadchain,
    int &cl, int &cr)
{
    if (_dij_ptfwlf == NULL) {
         // Forward left point direction for quad-to-quad direction.
        _dij_ptfwlf = new std::map<std::pair<int, int>, std::pair<int, int> >();
        _dij_ptfwlf->insert(std::make_pair(std::make_pair(1, 0), std::make_pair(1, 1)));
        _dij_ptfwlf->insert(std::make_pair(std::make_pair(0, 1), std::make_pair(0, 1)));
        _dij_ptfwlf->insert(std::make_pair(std::make_pair(-1, 0), std::make_pair(0, 0)));
        _dij_ptfwlf->insert(std::make_pair(std::make_pair(0, -1), std::make_pair(1, 0)));

        // Forward right point direction for quad-to-quad direction.
        _dij_ptfwrg = new std::map<std::pair<int, int>, std::pair<int, int> >();
        _dij_ptfwrg->insert(std::make_pair(std::make_pair(1, 0), std::make_pair(1, 0)));
        _dij_ptfwrg->insert(std::make_pair(std::make_pair(0, 1), std::make_pair(1, 1)));
        _dij_ptfwrg->insert(std::make_pair(std::make_pair(-1, 0), std::make_pair(0, 1)));
        _dij_ptfwrg->insert(std::make_pair(std::make_pair(0, -1), std::make_pair(0, 0)));
    }

    int i1, j1, i2, j2;
    const IntQuadChainPart &iqcl1 = intquadchain[0];
    i1 = iqcl1.i; j1 = iqcl1.j;
    if (intquadchain.size() > 1) {
        const IntQuadChainPart &iqcl2 = intquadchain[1];
        i2 = iqcl2.i; j2 = iqcl2.j;
    } else { // the single quad must be in corner
        if (i1 == 0) {
            if (j1 == 0) { // bottom left
                i2 = i1 - 1; j2 = j1;
            } else { // top left
                i2 = i1; j2 = j1 + 1;
            }
        } else {
            if (j1 == 0) { // bottom right
                i2 = i1; j2 = j1 - 1;
            } else { // top right
                i2 = i1 + 1; j2 = j1;
            }
        }
    }
    const std::pair<int, int> &dijl = (*_dij_ptfwlf)[std::make_pair(i2 - i1, j2 - j1)];
    int dil = dijl.first, djl = dijl.second;
    cl = cutmap[i1 + dil][j1 + djl];
    const std::pair<int, int> &dijr = (*_dij_ptfwrg)[std::make_pair(i2 - i1, j2 - j1)];
    int dir = dijr.first, djr = dijr.second;
    cr = cutmap[i1 + dir][j1 + djr];
}

void TerrainGeom::_make_tiles (
    double offsetx, double offsety,
    int numquadsx, int numquadsy,
    int numtilesx, int numtilesy, double tilesizex, double tilesizey,
    int numtilequadsx, int numtilequadsy,
    const GeomVertexFormat *gvformat,
    const std::vector<LVector3d> &verts,
    const std::vector<LVector4i> &tris,
    const std::vector<LVector2i> &quadmap,
    const std::vector<bool> &levints,
    int cut,
    std::vector<std::vector<NodePath> > &tiles,
    std::vector<std::vector<LPoint2d> > &tilexys)
{
    #undef Vt
    #define Vt LVector3d

    int nverts = verts.size();

    // Compute vertex normals and tangents,
    // as area-weighted averages of adjoining triangles.
    // Loop over triangles, adding contributions to their vertices.
    std::vector<double> vareas(nverts, 0.0);
    std::vector<LVector3d> vnorms(nverts, LVector3d(0.0, 0.0, 0.0));
    std::vector<LVector3d> vtangs(nverts, LVector3d(0.0, 0.0, 0.0));
    //Vt zdir = Vt(0.0, 0.0, 1.0);
    Vt xdir(1.0, 0.0, 0.0);
    for (int k = 0; k < tris.size(); ++k) {
        int c = tris[k][3];
        if (c != cut && (levints[cut] || levints[c])) {
            continue;
        }
        int l1 = tris[k][0], l2 = tris[k][1], l3 = tris[k][2];
        const Vt &v1 = verts[l1], &v2 = verts[l2], &v3 = verts[l3];
        Vt v12 = v2 - v1, v13 = v3 - v1;
        Vt tnorm = v12.cross(v13);
        double tarea = 0.5 * tnorm.length();
        tnorm.normalize();
        //Vt ttang = tnorm.cross(zdir).cross(tnorm); # steepest ascent (gradient)
        Vt ttang = tnorm.cross(xdir).cross(tnorm);
        ttang.normalize();
        int ls[] = {l1, l2, l3};
        for (int w = 0; w < 3; ++w) {
            int l = ls[w];
            vareas[l] += tarea;
            vnorms[l] += tnorm * tarea;
            vtangs[l] += ttang * tarea;
        }
    }
    for (int l = 0; l < nverts; ++l) {
        double va = vareas[l];
        if (va == 0.0) {
            // May happen if the vertex does not belong to this cut,
            // or triangulation left some hanging vertices.
            //printf("--zero-area-vertex %d %f %f %f\n", l, verts[l][0], verts[l][0], verts[l][0]);
            continue;
        }
        vnorms[l] /= va;
        vnorms[l].normalize();
        vtangs[l] /= va;
        vtangs[l].normalize();
    }

    // Construct tiles.
    std::vector<int> tilevertmap(nverts, 0); // for use inside _make_tile()
    for (int it = 0; it < numtilesx; ++it) {
        tiles.push_back(std::vector<NodePath>());
        tilexys.push_back(std::vector<LPoint2d>());
        std::vector<NodePath> &tiles1 = tiles[it];
        std::vector<LPoint2d> &tilexys1 = tilexys[it];
        double xt = (it + 0.5) * tilesizex + offsetx;
        for (int jt = 0; jt < numtilesy; ++jt) {
            double yt = (jt + 0.5) * tilesizey + offsety;
            NodePath tile = _make_tile(
                offsetx, offsety,
                numtilesx, numtilesy, tilesizex, tilesizey,
                numquadsx, numquadsy, numtilequadsx, numtilequadsy,
                verts, vnorms, vtangs, tris, quadmap, tilevertmap,
                gvformat,
                cut, it, jt, xt, yt);
            tiles1.push_back(tile);
            tilexys1.push_back(LPoint2d(xt, yt));
        }
    }
}

NodePath TerrainGeom::_make_tile (
    double offsetx, double offsety,
    int numtilesx, int numtilesy,
    double tilesizex, double tilesizey,
    int numquadsx, int numquadsy, int numtilequadsx, int numtilequadsy,
    const std::vector<LVector3d> &verts,
    const std::vector<LVector3d> &vnorms,
    const std::vector<LVector3d> &vtangs,
    const std::vector<LVector4i> &tris,
    const std::vector<LVector2i> &quadmap,
    std::vector<int> &tilevertmap,
    const GeomVertexFormat *gvformat,
    int cut, int it, int jt, double xt, double yt)
{
    #undef Vt
    #define Vt LVector3d
    bool timeit = false;
    double t0, t1, t2;
    if (timeit) {t0 = stime(); printf("--mktl10 ----- %d %d %d\n", cut, it, jt); t1 = t0;}

    int i0 = it * numtilequadsx;
    int j0 = jt * numtilequadsy;

    std::ostringstream tnamess;
    tnamess << "tile" << "-i" << it << "-j" << jt << "-c" << cut;
    std::string tname(tnamess.str());

    // Link global vertex and triangle indices to indices for this tile.
    std::vector<int> tilevinds;
    std::vector<int> tiletinds;
    for (int i = i0; i < i0 + numtilequadsx; ++i) {
        for (int j = j0; j < j0 + numtilequadsy; ++j) {
            int q = i * numquadsy + j;
            for (int k = quadmap[q][0]; k < quadmap[q][1]; ++k) {
                int c = tris[k][3];
                if (c == cut) {
                    tilevinds.push_back(tris[k][0]);
                    tilevinds.push_back(tris[k][1]);
                    tilevinds.push_back(tris[k][2]);
                    tiletinds.push_back(k);
                }
            }
        }
    }
    if (tilevinds.size() == 0) {
        // There is nothing from this cut on this tile.
        return NodePath(tname);
    }
    if (timeit) {t2 = stime(); printf("--mktl30 %.3f\n", t2 - t1); t1 = t2;}
    std::set<int> sortuniq1(tilevinds.begin(), tilevinds.end());
    tilevinds.assign(sortuniq1.begin(), sortuniq1.end());
    int nvinds = tilevinds.size();
    int ntinds = tiletinds.size();
    for (int lt = 0; lt < nvinds; ++lt) {
        int l = tilevinds[lt];
        tilevertmap[l] = lt;
    }
    if (timeit) {t2 = stime(); printf("--mktl40 %.3f\n", t2 - t1); t1 = t2;}

    // Compute texture coordinates.
    std::vector<LVector2d> texcs(nvinds);
    double x0 = offsetx;
    double y0 = offsety;
    double sx = tilesizex * numtilesx;
    double sy = tilesizey * numtilesy;
    for (int w = 0; w < nvinds; ++w) {
        int l = tilevinds[w];
        double x = verts[l][0], y = verts[l][1];
        double u = clamp((x - x0) / sx, 0.0, 1.0);
        double v = clamp((y - y0) / sy, 0.0, 1.0);
        texcs[w] = LVector2d(u, v);
    }
    if (timeit) {t2 = stime(); printf("--mktl50 %.3f\n", t2 - t1); t1 = t2;}

    // Construct graphics vertices.
    PT(GeomVertexData) gvdata = new GeomVertexData("data", gvformat, Geom::UH_static);
    gvdata->unclean_set_num_rows(nvinds);
    GeomVertexWriter *gvwvertex = new GeomVertexWriter(gvdata, InternalName::get_vertex());
    GeomVertexWriter *gvwnormal = new GeomVertexWriter(gvdata, InternalName::get_normal());
    GeomVertexWriter *gvwtangent = new GeomVertexWriter(gvdata, InternalName::get_tangent());
    GeomVertexWriter *gvwbinormal = new GeomVertexWriter(gvdata, InternalName::get_binormal());
    GeomVertexWriter *gvwcolor = new GeomVertexWriter(gvdata, InternalName::get_color());
    GeomVertexWriter *gvwtexcoord = new GeomVertexWriter(gvdata, InternalName::get_texcoord());
    for (int w = 0; w < nvinds; ++w) {
        int l = tilevinds[w];
        int lt = tilevertmap[l];
        gvwvertex->add_data3(verts[l][0] - xt, verts[l][1] - yt, verts[l][2]);
        gvwnormal->add_data3(vnorms[l][0], vnorms[l][1], vnorms[l][2]);
        gvwtangent->add_data3(vtangs[l][0], vtangs[l][1], vtangs[l][2]);
        Vt vb = vnorms[l].cross(vtangs[l]);
        vb.normalize();
        gvwbinormal->add_data3(vb[0], vb[1], vb[2]);
        gvwcolor->add_data4(1.0, 1.0, 1.0, 1.0);
        gvwtexcoord->add_data2(texcs[lt][0], texcs[lt][1]);
    }
    if (timeit) {t2 = stime(); printf("--mktl60 %.3f\n", t2 - t1); t1 = t2;}

    // Construct graphics triangles.
    PT(GeomTriangles) gtris = new GeomTriangles(Geom::UH_static);
    // Default index column type is NT_uint16, and add_vertices()
    // would change it automatically if needed. Since it is not used,
    // change manually.
    if (nvinds >= 1 << 16) {
        gtris->set_index_type(Geom::NT_uint32);
    }
    GeomVertexArrayData *gvdtris = gtris->modify_vertices();
    gvdtris->unclean_set_num_rows(ntinds * 3);
    GeomVertexWriter *gvwtris = new GeomVertexWriter(gvdtris, 0);
    for (int w = 0; w < ntinds; ++w) {
        int k = tiletinds[w];
        int l1 = tris[k][0], l2 = tris[k][1], l3 = tris[k][2];
        int lt1 = tilevertmap[l1], lt2 = tilevertmap[l2], lt3 = tilevertmap[l3];
        //gtris->add_vertices(lt1, lt2, lt3);
        gvwtris->add_data1i(lt1);
        gvwtris->add_data1i(lt2);
        gvwtris->add_data1i(lt3);
        //gtris->close_primitive();
    }
    if (timeit) {t2 = stime(); printf("--mktl70 %.3f\n", t2 - t1); t1 = t2;}

    // Construct tile skirt.
    if (true) {
        //printf("------tile-skirt  it=%d  jt=%d  cut=%d\n", it, jt, cut);
        double xb0 = it * tilesizex + offsetx;
        double yb0 = jt * tilesizey + offsety;
        double xb1 = (it + 1) * tilesizex + offsetx;
        double yb1 = (jt + 1) * tilesizey + offsety;
        double quadsizex = tilesizex / numtilequadsx;
        double quadsizey = tilesizey / numtilequadsy;
        double incang = torad(10.0);
        double incrlen = 0.1;
        LVector3d incvz(0.0, 0.0, -((quadsizex + quadsizey) * 0.5) * incrlen);
        double epsx = quadsizex * 1e-5;
        double epsy = quadsizey * 1e-5;
        int ltc = nvinds;
        int kus[] = {0, 0, 1, 1};
        double ues[] = {xb0, xb1, yb0, yb1};
        double epsus[] = {epsx, epsx, epsy, epsy};
        int ias[] = {i0, i0 + numtilequadsx - 1, i0, i0};
        int ibs[] = {i0, i0 + numtilequadsx - 1, i0 + numtilequadsx, i0 + numtilequadsx};
        int jas[] = {j0, j0, j0, j0 + numtilequadsy - 1};
        int jbs[] = {j0 + numtilequadsy, j0 + numtilequadsy, j0, j0 + numtilequadsy - 1};
        for (int w = 0; w < 4; ++w) {
            int ku = kus[w];
            double ue = ues[w];
            double epsu = epsus[w];
            int ia = ias[w], ib = ibs[w], ja = jas[w], jb = jbs[w];
            //printf("----tile-skirt  ku=%d  ue=%.1f\n", ku, ue);
            LQuaterniond rot;
            LVector3d ez(0.0, 0.0, 1.0);
            for (int i = ia, j = ja; i < ib || j < jb; i = std::min(i + 1, ib), j = std::min(j + 1, jb)) {
                int q = i * numquadsy + j;
                for (int k = quadmap[q][0]; k < quadmap[q][1]; ++k) {
                    int c = tris[k][3];
                    if (c == cut) {
                        int l1 = tris[k][0], l2 = tris[k][1], l3 = tris[k][2];
                        double u1 = verts[l1][ku], u2 = verts[l2][ku], u3 = verts[l3][ku];
                        int la = -1, lb = -1;
                        if (fabs(u1 - ue) < epsu && fabs(u2 - ue) < epsu) {
                            la = l1; lb = l2;
                        } else if (fabs(u2 - ue) < epsu && abs(u3 - ue) < epsu) {
                            la = l2; lb = l3;
                        } else if (fabs(u3 - ue) < epsu && abs(u1 - ue) < epsu) {
                            la = l3; lb = l1;
                        }
                        if (la >= 0) {
                            // Compute lower skirt points.
                            double xa = verts[la][0], ya = verts[la][1], za = verts[la][2];
                            double xb = verts[lb][0], yb = verts[lb][1], zb = verts[lb][2];
                            //printf("--tile-skirt  "
                                   //"xa=%.1f  ya=%.1f  xb=%.1f  yb=%.1f\n",
                                   //xa, ya, xb, yb);
                            LVector3d pa(xa, ya, 0.0);
                            LVector3d pb(xb, yb, 0.0);
                            LVector3d ra = unitv(pa - pb);
                            rot.set_from_axis_angle_rad(incang, ra);
                            LVector3d incv(rot.xform(incvz));
                            LVector3d pc = pa + incv;
                            LVector3d pd = pb + incv;
                            pa[2] += za; pc[2] += za;
                            pb[2] += zb; pd[2] += zb;
                            double xc = pc[0], yc = pc[1], zc = pc[2];
                            double xd = pd[0], yd = pd[1], zd = pd[2];
                            int lta = tilevertmap[la], ltb = tilevertmap[lb];
                            // Add vertices.
                            //LVector3d vnc = unitv((pa - pb).cross(pc - pb));
                            //LVector3d vnd = unitv((pc - pb).cross(pd - pb));
                            const LVector3d &vnc = vnorms[la];
                            const LVector3d &vnd = vnorms[lb];
                            const LVector3d *ps[] = {&pc, &pd};
                            const LVector3d *vns[] = {&vnc, &vnd};
                            for (int o = 0; o < 2; ++o) {
                                const LVector3d &p = *ps[o];
                                const LVector3d &vn = *vns[o];
                                LVector3d vt = vn.cross(ez).cross(vt); // steepest ascent
                                LVector3d vb = vn.cross(vt);
                                gvwvertex->add_data3(p[0] - xt, p[1] - yt, p[2]);
                                gvwnormal->add_data3(vn[0], vn[1], vn[2]);
                                gvwtangent->add_data3(vt[0], vt[1], vt[2]);
                                gvwbinormal->add_data3(vb[0], vb[1], vb[2]);
                                gvwcolor->add_data4(1.0, 1.0, 1.0, 1.0);
                                double x = p[0], y = p[1];
                                double u = clamp((x - x0) / sx, 0.0, 1.0);
                                double v = clamp((y - y0) / sy, 0.0, 1.0);
                                gvwtexcoord->add_data2(u, v);
                            }
                            // Add triangles.
                            int ltd = ltc + 1;
                            //gtris->add_vertices(ltb, lta, ltc);
                            gvwtris->add_data1i(ltb);
                            gvwtris->add_data1i(lta);
                            gvwtris->add_data1i(ltc);
                            //gtris->close_primitive();
                            //gtris->add_vertices(ltb, ltc, ltd);
                            gvwtris->add_data1i(ltb);
                            gvwtris->add_data1i(ltc);
                            gvwtris->add_data1i(ltd);
                            //gtris->close_primitive();
                            ltc += 2;
                        }
                    }
                }
            }
        }
    }
    if (timeit) {t2 = stime(); printf("--mktl80 %.3f\n", t2 - t1); t1 = t2;}

    // Construct the mesh.
    PT(Geom) geom = new Geom(gvdata);
    geom->add_primitive(gtris);
    PT(GeomNode) gnode = new GeomNode(tname);
    gnode->add_geom(geom);
    NodePath node(gnode);
    //node.flatten_strong();
    if (timeit) {t2 = stime(); printf("--mktl90 %.3f\n", t2 - t1); t1 = t2;}

    delete gvwvertex;
    delete gvwnormal;
    delete gvwtangent;
    delete gvwbinormal;
    delete gvwcolor;
    delete gvwtexcoord;
    delete gvwtris;
    if (timeit) {t2 = stime(); printf("--mktl99-cml %.3f\n", t2 - t0); t1 = t2;}

    if (timeit && cut == 0 && it == 0 && jt == 2) {printf("--mktl99-stop\n"); std::exit(1);}
    return node;
}

int TerrainGeom::_quad_index_for_xy (
    double sizex, double sizey,
    double offsetx, double offsety,
    int numquadsx, int numquadsy,
    double x, double y)
{
    double dx = sizex / numquadsx;
    double dy = sizey / numquadsy;
    int i = static_cast<int>((x - offsetx) / dx);
    int j = static_cast<int>((y - offsety) / dy);
    if (0 <= i && i < numquadsx && 0 <= j && j < numquadsy) {
        return i * numquadsy + j;
    } else {
        return -1;
    }
}

void TerrainGeom::_interpolate_z (
    double sizex, double sizey,
    double offsetx, double offsety,
    int numquadsx, int numquadsy,
    const std::vector<LVector3d> &verts,
    const std::vector<LVector4i> &tris,
    const std::vector<LVector2i> &quadmap,
    double x1, double y1, const LPoint3 &ref1,
    LVector3d &pcz,
    LVector3d &norm, bool wnorm,
    LVector3i &tvinds, bool wtvinds)
{
    double xr1 = ref1[0], yr1 = ref1[1], zr1 = ref1[2];
    double x = x1 - xr1, y = y1 - yr1;

    int q = _quad_index_for_xy(sizex, sizey, offsetx, offsety,
                               numquadsx, numquadsy,
                               x, y);
    if (q < 0) {
        pcz[0] = 1.0; pcz[1] = -1; pcz[2] = 0.0;
        if (wnorm) {
            norm = LVector3d(0.0, 0.0, 0.0);
        }
        if (wtvinds) {
            tvinds = LVector3i(0, 0, 0);
        }
        return;
    }
    bool first = true;
    LVector3d pczmin;
    LVector3d normmin;
    LVector3i tvindspmin;
    for (int k = quadmap[q][0]; k < quadmap[q][1]; ++k) {
        LVector2d pz1;
        LVector3d norm1;
        LVector3i tvinds1;
        _interpolate_tri_z(verts, tris, k, x, y,
                           pz1, norm1, wnorm, tvinds1, wtvinds);
        if (first || pczmin[0] > pz1[0]) {
            first = false;
            pczmin = LVector3d(pz1[0], tris[k][3], pz1[1]);
            if (wnorm) {
                normmin = norm1;
            }
            if (wtvinds) {
                tvindspmin = tvinds1;
            }
        }
        if (pz1[0] == 0.0) {
            break;
        }
    }
    pczmin[2] += zr1;

    pcz = pczmin;
    if (wnorm) {
        norm = normmin;
    }
    if (wtvinds) {
        tvinds = tvindspmin;
    }
}

void TerrainGeom::_interpolate_tri_z (
    const std::vector<LVector3d> &verts,
    const std::vector<LVector4i> &tris,
    int k, double x, double y,
    LVector2d &pz,
    LVector3d &norm, bool wnorm,
    LVector3i &tvinds, bool wtvinds)
{
    #undef Pt2
    #define Pt2 LVector2d
    #undef Pt3
    #define Pt3 LVector3d

    Pt2 pf(x, y);
    const LVector4i &tri = tris[k];
    const Pt3 &v1 = verts[tri[0]], &v2 = verts[tri[1]], &v3 = verts[tri[2]];
    Pt2 v1f = v1.get_xy(), v2f = v2.get_xy(), v3f = v3.get_xy();

    Pt2 v12f = v2f - v1f;
    Pt2 v13f = v3f - v1f;
    Pt2 v1pf = pf - v1f;
    double d1212 = v12f.dot(v12f);
    double d1213 = v12f.dot(v13f);
    double d1313 = v13f.dot(v13f);
    double den = d1313 * d1212 - d1213 * d1213;
    if (den == 0.0) { // can happen due to roundoff
        pz = LVector2d(1.0, v1[2]);
        if (wnorm) {
            norm = LVector3d(0.0, 0.0, 1.0);
        }
        if (wtvinds) {
            tvinds = LVector3i(tri[0], tri[1], tri[2]);
        }
        return;
    }
    double d131p = v13f.dot(v1pf);
    double d121p = v12f.dot(v1pf);
    double b2 = (d1313 * d121p - d1213 * d131p) / den;
    double b3 = (d1212 * d131p - d1213 * d121p) / den;
    double b1 = 1.0 - (b2 + b3);

    double p = 0.0; // outsideness penalty
    LVector3d bv(b1, b2, b3);
    for (int i = 0; i < 3; ++i) {
        double b = bv[i];
        if (b < 0.0) {
            p += POW2(b);
        } else if (b > 1.0) {
            p += POW2(b - 1.0);
        }
    }

    double z1 = v1[2], z2 = v2[2], z3 = v3[2];
    double z = b1 * z1 + b2 * z2 + b3 * z3;
    LVector3d n;
    if (wnorm) {
        n = unitv((v2 - v1).cross(v3 - v1));
    }

    pz = LVector2d(p, z);
    if (wnorm) {
        norm = n;
    }
    if (wtvinds) {
        tvinds = LVector3i(tri[0], tri[1], tri[2]);
    }
}

LVector3d TerrainGeom::heightmap_size () const
{
    return LVector3d(_maxsizexa, _maxsizexb, _maxsizey);
}

LVector2d TerrainGeom::to_unit_trap (
    double maxsizexa, double maxsizexb, double maxsizey,
    double x, double y) const
{
    return _to_unit_trap(_sizex, _sizey, _offsetx, _offsety,
                         maxsizexa, maxsizexb, maxsizey,
                         _centerx, _centery,
                         x, y);
}

int TerrainGeom::quad_index_for_xy (double x, double y) const
{
    return _quad_index_for_xy(_sizex, _sizey, _offsetx, _offsety,
                              _numquadsx, _numquadsy,
                              x, y);
}

void TerrainGeom::interpolate_z (
    double x1, double y1, const LPoint3 &ref1,
    LVector3d &pcz,
    LVector3d &norm, bool wnorm,
    LVector3i &tvinds, bool wtvinds) const
{
    _interpolate_z(_sizex, _sizey, _offsetx, _offsety,
                   _numquadsx, _numquadsy,
                   _verts, _tris, _quadmap,
                   x1, y1, ref1,
                   pcz, norm, wnorm, tvinds, wtvinds);
}

