#ifndef CLOUDS_H
#define CLOUDS_H

#include <map>
#include <vector>

#include <geomVertexFormat.h>
#include <lvector3.h>
#include <lvector4.h>
#include <nodePath.h>

#include <typeinit.h>
#include <table.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_CLOUDS
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

class TexUVParts;

class EXPORT CloudsGeom : public TypedObject
{
PUBLISHED:

    CloudsGeom (
        const std::string &name,
        double sizex, double sizey,
        double wtilesizex, double wtilesizey,
        double minaltitude, double maxaltitude,
        double mincloudwidth, double maxcloudwidth,
        double mincloudheight1, double maxcloudheight1,
        double mincloudheight2, double maxcloudheight2,
        double quaddens, double minquadsize, double maxquadsize,
        const TexUVParts &texuvparts, int cloudshape,
        const std::string &cloudmappath, bool havecloudmappath,
        int mingray, int maxgray,
        double clouddens, int vsortbase, int vsortdivs,
        int numlods, double lodredfac, bool lodaccum,
        int maxnumquads, int randseed);

    ~CloudsGeom ();

    void destroy ();

    int num_tiles_x () const;
    int num_tiles_y () const;
    double tile_size_x () const;
    double tile_size_y () const;
    int num_lods () const;
    double offset_z () const;
    NodePath tile_root ();

    int update_visual_sort_dir_index (
        const LVector3 &camdir, int vsind0) const;

private:

    static std::map<int, CPT(GeomVertexFormat)> *_gvformat;

    bool _alive;
    int _numtilesx, _numtilesy;
    double _tilesizex, _tilesizey;
    int _numlods;
    double _offsetz;
    std::vector<LVector3> _vsortdirs;
    std::vector<double> _vsmaxoffangs;
    std::vector<std::vector<int> > _vsnbinds;
    NodePath _tileroot;

    static void _construct (
        double sizex, double sizey,
        double wtilesizex, double wtilesizey,
        double minaltitude, double maxaltitude,
        double mincloudwidth, double maxcloudwidth,
        double mincloudheight1, double maxcloudheight1,
        double mincloudheight2, double maxcloudheight2,
        double quaddens, double minquadsize, double maxquadsize,
        const std::vector<LVector4> &texuvparts, int cloudshape,
        const std::string &cloudmappath, bool havecloudmappath,
        int mingray, int maxgray,
        double clouddens, int vsortbase, int vsortdivs,
        int numlods, double lodredfac, bool lodaccum,
        int maxnumquads, int randseed,
        // celldata
        int &numtilesx_, int &numtilesy_,
        double &tilesizex_, double &tilesizey_,
        int &numlods_, double &offsetz_,
        // vsortdata
        std::vector<LVector3> &vsortdirs,
        std::vector<double> &vsmaxoffangs,
        std::vector<std::vector<int> > &vsnbinds,
        // geomdata
        NodePath &tileroot_);

    static void _derive_cell_data (double size, double wtilesize,
                                   int &numtiles, double &tilesize);

DECLARE_TYPE_HANDLE(CloudsGeom)
};

class EXPORT GeodesicSphere : public TypedObject
{
PUBLISHED:

    // base: 0 tetrahedron, 1 octahedron, 2 icosahedron
    GeodesicSphere (int base = 2, int numdivs = 0, double radius = 1.0);

    ~GeodesicSphere ();

    int num_vertices () const;
    LVector3 vertex (int i) const;
    LVector3 normal (int i) const;
    double max_offset_angle (int i) const;
    int num_neighbor_vertices (int i) const;
    int neighbor_vertex_index (int i, int j) const;
    int num_tris () const;
    LVector3i tri (int i) const;

private:

    std::vector<LVector3> _verts, _norms;
    std::vector<LVector3i> _tris;
    std::vector<double> _maxoffangs;
    std::vector<std::vector<int> > _nbinds;

    static void _construct (
        int base, int numdivs, double radius,
        std::vector<LVector3> &verts, std::vector<LVector3> &norms,
        std::vector<LVector3i> &tris, std::vector<double> &maxoffangs,
        std::vector<std::vector<int> > &nbinds);

    static void _split_triangle (
        double radius,
        std::vector<LVector3> &verts, std::vector<LVector3> &norms,
        std::vector<LVector3i> &tris,
        std::map<std::pair<int, int>, int> &edgesplits,
        int i1, int i2, int i3,
        const LVector3 &v1, const LVector3 &v2, const LVector3 &v3,
        int numdivs);

DECLARE_TYPE_HANDLE(GeodesicSphere)
};

class EXPORT TexUVParts : public TypedObject
{
PUBLISHED:

    TexUVParts ();

    ~TexUVParts ();

    void add_part (const LVector4 &part);
    int num_parts () const;
    LVector4 part (int i) const;

private:

    std::vector<LVector4> _parts;

DECLARE_TYPE_HANDLE(TexUVParts)
};

#endif
