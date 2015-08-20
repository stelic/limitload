#ifndef TERRAIN_H
#define TERRAIN_H

#include <map>
#include <string>
#include <utility>
#include <vector>

#include <geomVertexFormat.h>
#include <nodePath.h>
#include <lvector2.h>
#include <lvector3.h>
#include <lvector4.h>

#include <typeinit.h>
#include <misc.h>
#include <table.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_TERRAIN
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

class Flat;
class IntCurvePart;
class IntQuadChainPart;
class IntQuadLink;

class EXPORT TerrainGeom : public TypedObject
{
PUBLISHED:

    TerrainGeom (
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
        ENC_LST_STRING cutmaskpaths, ENC_LST_BOOL levints);

    ~TerrainGeom ();

    void destroy ();

    LVector3d heightmap_size () const;

    LVector2d to_unit_trap (
        double maxsizexa, double maxsizexb, double maxsizey,
        double x, double y) const;

    int quad_index_for_xy (double x, double y) const;

    void interpolate_z (
        double x1, double y1, const LPoint3 &ref1,
        LVector3d &pcz,
        LVector3d &norm, bool wnorm,
        LVector3i &tvinds, bool wtvinds) const;

    NodePath tile_root ();
    int num_quads_x () const;
    int num_quads_y () const;
    int num_tiles_x () const;
    int num_tiles_y () const;
    int tile_size_x () const;
    int tile_size_y () const;
    int num_cuts () const;
    double max_z () const;
    void update_max_z (double z);
    double quad_max_z (int q) const;
    void update_quad_max_z (int q, double z);

private:

    bool _alive;

    double _sizex, _sizey;
    double _offsetx, _offsety;
    int _numquadsx, _numquadsy;
    int _numtilesx, _numtilesy;
    int _tilesizex, _tilesizey;
    int _numcuts;
    double _centerx, _centery;
    double _maxsizexa, _maxsizexb, _maxsizey;
    // elevdata
    std::vector<LVector3d> _verts;
    std::vector<LVector4i> _tris;
    std::vector<LVector2i> _quadmap;
    double _maxz;
    std::vector<double> _maxqzs;
    NodePath _tileroot;

    static CPT(GeomVertexFormat) _gvformat;

    static void _construct(
        double sizex, double sizey,
        double offsetx, double offsety,
        const std::string &heightmap, bool haveheightmap,
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
        NodePath &tileroot_);

    static void _derive_cell_data (
        double celldensity,
        double size, double hmapsize, int numtiles,
        int &numquads, double &tilesize, int &numtilequads);

    static void _read_heightmap_data (
        const std::string &fpath,
        double &sxa, double &sxb, double &sy,
        double &mnz, double &mxz, int &mng, int &mxg,
        std::vector<Flat*> &flats);

    static void _triangulate (
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
        double &lasttime);

    static double _get_z_at_world_xy (
        const UnitGrid2 &heightmap,
        double maxsizexa, double maxsizexb, double maxsizey,
        double sizex, double sizey, double offsetx, double offsety,
        double centerx, double centery,
        int mingray, int maxgray, double minheight, double maxheight,
        double usqtol, bool periodic,
        double x, double y);

    static LVector2d _to_unit_trap (
        double sizex, double sizey, double offsetx, double offsety,
        double maxsizexa, double maxsizexb, double maxsizey,
        double centerx, double centery,
        double x, double y);

    static void _split_interface_quads (
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
        std::vector<bool> &intcurves_closed);

    static void _extract_interface_quads (
        const std::vector<std::vector<int> > &cutmap,
        int i0, int j0, int cl, int cr,
        std::vector<std::vector<int> > &freemap,
        std::vector<IntQuadChainPart> &intquadchain,
        bool &closed);

    static void _extract_interface_quads_1 (
        const std::vector<std::vector<int> > &cutmap,
        int i0, int j0, int cl, int cr,
        std::vector<std::vector<int> > &freemap,
        std::vector<IntQuadChainPart> &intquadchain,
        bool &cutbdry);

    static void _init_interface_curve (
        const std::vector<std::vector<int> > &cutmap,
        const std::vector<IntQuadChainPart> &intquadchain,
        bool closed,
        double quadsizex, double quadsizey, double offsetx, double offsety,
        int subdiv, double fromcut,
        std::vector<IntCurvePart> &intcurve);

    static void _smooth_interface_curve (
        std::vector<IntCurvePart> &intcurve,
        bool closed, int subdiv,
        double tbslam, double tbsmu, int tbsiter);

    static void _level_curve_to_left (
        double sizex, double sizey, double offsetx, double offsety,
        int numquadsx, int numquadsy,
        std::vector<LVector3d> &verts,
        const std::vector<LVector4i> &tris,
        const std::vector<LVector2i> &quadmap,
        const std::vector<int> &cvinds, bool closed, int lcut);

    static void _triangulate_interface_quads (
        const std::vector<std::vector<int> > &cutmap,
        double quadsizex, double quadsizey, double offsetx, double offsety,
        const std::vector<IntQuadChainPart> &intquadchain,
        const std::vector<IntCurvePart> &intcurve, int subdiv,
        int nverts0, int ntris0,
        std::vector<LVector3d> &verts,
        std::vector<LVector4i> &tris,
        std::vector<IntQuadLink> &links);

    static std::map<std::pair<int, int>, std::pair<int, int> > *_dij_ptfwlf;
    static std::map<std::pair<int, int>, std::pair<int, int> > *_dij_ptfwrg;

    static void _interface_cut_levels (
        const std::vector<std::vector<int> > &cutmap,
        const std::vector<IntQuadChainPart> &intquadchain,
        int &cl, int &cr);

    static void _make_tiles (
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
        std::vector<std::vector<LPoint2d> > &tilexys);

    static NodePath _make_tile (
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
        int cut, int it, int jt, double xt, double yt);

    static int _quad_index_for_xy (
        double sizex, double sizey,
        double offsetx, double offsety,
        int numquadsx, int numquadsy,
        double x, double y);

    static void _interpolate_z (
        double sizex, double sizey,
        double offsetx, double offsety,
        int numquadsx, int numquadsy,
        const std::vector<LVector3d> &verts,
        const std::vector<LVector4i> &tris,
        const std::vector<LVector2i> &quadmap,
        double x1, double y1, const LPoint3 &ref1,
        LVector3d &pcz,
        LVector3d &norm, bool wnorm,
        LVector3i &tvinds, bool wtvinds);

    static void _interpolate_tri_z (
        const std::vector<LVector3d> &verts,
        const std::vector<LVector4i> &tris,
        int k, double x, double y,
        LVector2d &pz,
        LVector3d &norm, bool wnorm,
        LVector3i &tvinds, bool wtvinds);

DECLARE_TYPE_HANDLE(TerrainGeom)
};

#endif
