#ifdef _MSC_VER
#define _USE_MATH_DEFINES
#endif
#include <algorithm>
#include <cmath>
#include <numeric>

#include <geomVertexArrayFormat.h>
#include <geomVertexData.h>
#include <geomVertexWriter.h>
#include <geomTriangles.h>
#include <geomNode.h>
#include <lodNode.h>
#include <internalName.h>
#include <lvector3.h>
#include <lvector4.h>

#include <clouds.h>
#include <table.h>
#include <misc.h>

#ifdef _MSC_VER
#undef min
#undef max
#endif

static void _init_clouds ()
{
    static bool initialized = false;
    if (initialized) {
        return;
    }
    initialized = true;
    INITIALIZE_TYPE(CloudsGeom)
    INITIALIZE_TYPE(GeodesicSphere)
    INITIALIZE_TYPE(TexUVParts)
}
DToolConfigure(config_limload_clouds);
DToolConfigureFn(config_limload_clouds) { _init_clouds(); }


INITIALIZE_TYPE_HANDLE(CloudsGeom)

class CloudSpec
{
public:
    LPoint3 pos;
    double width, height1, height2;
    std::vector<int> nquads;
};

class QVSpec
{
public:
    LPoint3 qtpos;
    int nverts;

    void set_view_dir (const LVector3 vd) {
        _vd = vd;
    }

    bool operator< (const QVSpec &other) const
    {
        return -(qtpos.dot(_vd)) < -(other.qtpos.dot(other._vd));
    }

private:
    LVector3 _vd;
};

class TileSpec
{
public:
    LPoint3 pos;
    PT(GeomVertexData) gvdata;
    GeomVertexWriter *gvwvertex, *gvwtexcoord;
    GeomVertexWriter *gvwoffcenter, *gvwgrpoffcenter, *gvwhaxislen;
    std::vector<std::vector<PT(GeomTriangles)> > gtris;
    std::vector<std::vector<QVSpec> > qvspecs;
    int nverts;

    std::vector<LVector3> verts;
    std::vector<LVector2> texuvs;
    std::vector<LVector3> offcs;
    std::vector<LVector3> grpoffcs;
    std::vector<LVector4> hxyz12s;
};

class CQSpec
{
public:
    LPoint3 qoff;
    int qsz;
};

CloudsGeom::CloudsGeom (
    const std::string &name,
    double sizex, double sizey,
    double wtilesizex, double wtilesizey,
    double minaltitude, double maxaltitude,
    double mincloudwidth, double maxcloudwidth,
    double mincloudheight1, double maxcloudheight1,
    double mincloudheight2, double maxcloudheight2,
    double quaddens, double minquadsize, double maxquadsize,
    const TexUVParts &texuvparts_, int cloudshape,
    const std::string &cloudmappath, bool havecloudmappath,
    int mingray, int maxgray,
    double clouddens, int vsortbase, int vsortdivs,
    int numlods, double lodredfac, bool lodaccum,
    int maxnumquads, int randseed)
{

    std::vector<LVector4> texuvparts;
    for (int i = 0; i < texuvparts_.num_parts(); ++i) {
        texuvparts.push_back(texuvparts_.part(i));
    }

    _construct(
        sizex, sizey,
        wtilesizex, wtilesizey,
        minaltitude, maxaltitude,
        mincloudwidth, maxcloudwidth,
        mincloudheight1, maxcloudheight1,
        mincloudheight2, maxcloudheight2,
        quaddens, minquadsize, maxquadsize,
        texuvparts, cloudshape,
        cloudmappath, havecloudmappath,
        mingray, maxgray,
        clouddens, vsortbase, vsortdivs,
        numlods, lodredfac, lodaccum,
        maxnumquads, randseed,
        // celldata
        _numtilesx, _numtilesy, _tilesizex, _tilesizey,
        _numlods, _offsetz,
        // vsortdata
        _vsortdirs, _vsmaxoffangs, _vsnbinds,
        // geomdata
        _tileroot);

    _alive = true;
}

CloudsGeom::~CloudsGeom ()
{
    destroy();
}

void CloudsGeom::destroy ()
{
    if (!_alive) {
        return;
    }
    _tileroot.remove_node();
    _vsortdirs.clear();
    _vsmaxoffangs.clear();
    _vsnbinds.clear();
    _alive = false;
}


std::map<int, CPT(GeomVertexFormat)> *CloudsGeom::_gvformat = NULL;

void CloudsGeom::_construct (
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
    NodePath &tileroot_)
{
    bool timeit = false;

    double t0, t1, t2;
    if (timeit) {
        t0 = stime();
        t1 = t0;
    }

    if (cloudshape != 0 && cloudshape != 1) {
        fprintf(stderr,
            "Unknown cloud shape '%d'.\n", cloudshape);
        std::exit(1);
    }

    NumRandom randgen(randseed);

    // Derive cell data.
    int numtilesx; double tilesizex;
    _derive_cell_data(sizex, wtilesizex, numtilesx, tilesizex);
    int numtilesy; double tilesizey;
    _derive_cell_data(sizey, wtilesizey, numtilesy, tilesizey);

    // Load cloud map.
    UnitGrid2 cloudmap(0.0);
    if (havecloudmappath) {
        cloudmap = UnitGrid2(cloudmappath);
    }

    // Distribute clouds.
    double mingu = static_cast<double>(mingray) / 255;
    double maxgu = static_cast<double>(maxgray) / 255;
    double fgu0 = 1.0 / (maxgu - mingu);
    double fgu1 = -mingu * fgu0;
    double midsize = 0.5 * (sizex + sizey);
    int ntc = static_cast<int>(POW2((midsize / maxcloudwidth) * clouddens));
    int nsmpxy = 5;
    double dxypu = (maxcloudwidth / midsize) / nsmpxy;
    double dxypu0 = -0.5 * (dxypu * nsmpxy);
    std::vector<CloudSpec> cloudspecs;
    std::vector<double> cloudvol;
    double minavggu = 0.1;
    double offsetx = -0.5 * sizex;
    double offsety = -0.5 * sizey;
    double offsetz = 0.5 * (minaltitude + maxaltitude);
    // ...+ offsetz will be set at top node, for proper altitude binning.
    double dz1 = minaltitude - offsetz;
    double dz2 = maxaltitude - offsetz;
    for (int kc = 0; kc < ntc; ++kc) {
        double xcu = randgen.uniform(0.0, 1.0);
        double ycu = randgen.uniform(0.0, 1.0);
        // Quick check to avoid POW2(nsmpxy) samplings on coarser cloud maps.
        if (cloudmap(xcu, ycu, 0.0, true) == 0.0) {
            continue;
        }
        double avggu = 0.0;
        for (int ip = 0; ip < nsmpxy; ++ip) {
            double xpu = xcu + dxypu0 + dxypu * ip;
            for (int jp = 0; jp < nsmpxy; ++jp) {
                double ypu = ycu + dxypu0 + dxypu * jp;
                double gu = cloudmap(xpu, ypu, 0.0, true);
                avggu += std::min(std::max(gu * fgu0 + fgu1, 0.0), 1.0);
            }
        }
        avggu /= POW2(nsmpxy);
        if (avggu < minavggu) {
            continue;
        }
        double cwidth = randgen.uniform(mincloudwidth, maxcloudwidth) * avggu;
        double cheight1 = randgen.uniform(mincloudheight1, maxcloudheight1) * avggu;
        double cheight2 = randgen.uniform(mincloudheight2, maxcloudheight2) * avggu;
        double xc = xcu * sizex + offsetx;
        double yc = ycu * sizey + offsety;
        double zc = randgen.uniform(dz1, dz2) * avggu;
        CloudSpec cs;
        cs.pos = LPoint3(xc, yc, zc);
        cs.width = cwidth; cs.height1 = cheight1; cs.height2 = cheight2;
        cs.nquads = std::vector<int>(numlods, 0);
        cloudspecs.push_back(cs);
        double cvol = 0.0;
        if (cloudshape == 0) {
            cvol = (1.333 * M_PI) * POW2(0.5 * cwidth) * (0.5 * (cheight2 - cheight1));
        } else if (cloudshape == 1) {
            cvol = M_PI * POW2(0.5 * cwidth) * (cheight2 - cheight1);
        }
        cloudvol.push_back(cvol);
    }
    int numclouds = cloudspecs.size();
    if (timeit) {
        t2 = stime();
        printf("clouds-distribute:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }

    // Number of quads per LOD level.
    double sumcloudvol = std::accumulate(cloudvol.begin(), cloudvol.end(), 0.0);
    int numquads1;
    if (quaddens > 0.0) {
        numquads1 = static_cast<int>(quaddens * sumcloudvol);
    } else {
        numquads1 = static_cast<int>(-quaddens);
    }
    if (maxnumquads > 0) {
        numquads1 = std::min(numquads1, maxnumquads);
    }
    double quaddens1 = sumcloudvol > 0.0 ? numquads1 / sumcloudvol : 0.0;
    std::vector<int> numquads(numlods);
    if (lodaccum) {
        std::vector<double> plrfac(numlods);
        for (int kl = 0; kl < numlods; ++kl) {
            plrfac[kl] = pow(lodredfac, kl);
        }
        double sumplrfac = std::accumulate(plrfac.begin(), plrfac.end(), 0.0);
        for (int kl = 0; kl < numlods; ++kl) {
            double plqfac = plrfac[kl] / sumplrfac;
            numquads[kl] = static_cast<int>(numquads1 * plqfac);
        }
    } else {
        numquads[0] = numquads1;
        for (int kl = 1; kl < numlods; ++kl) {
            numquads[kl] = static_cast<int>(numquads[kl - 1] * lodredfac);
        }
    }

    // Distribute quads among clouds.
    for (int kl = 0; kl < numlods; ++kl) {
        std::vector<double> cloudvol_m(cloudvol);
        int numquads_m = numquads[kl];
        while (true) {
            if (numquads_m <= 0) {
                break;
            }
            double sumcloudvol = std::accumulate(cloudvol_m.begin(), cloudvol_m.end(), 0.0);
            double midcloudvol = 0.9 * (  *std::min_element(cloudvol_m.begin(), cloudvol_m.end())
                                        + *std::max_element(cloudvol_m.begin(), cloudvol_m.end()));
            int numquads_ms = 0;
            for (int kc = 0; kc < numclouds; ++kc) {
                int cq = static_cast<int>(numquads_m * (cloudvol_m[kc] / sumcloudvol));
                if (cq == 0 && cloudvol_m[kc] > midcloudvol) {
                    cq += 1;
                }
                cq = std::min(cq, numquads_m - numquads_ms);
                cloudspecs[kc].nquads[kl] += cq;
                numquads_ms += cq;
                if (numquads_ms == numquads_m) {
                    break;
                }
                cloudvol_m[kc] -= (cq * sumcloudvol) / numquads_m;
                cloudvol_m[kc] = std::max(cloudvol_m[kc], 0.0);
            }
            numquads_m -= numquads_ms;
        }
    }
    // Eliminate zero-quad clouds.
    std::vector<CloudSpec> cloudspecs_m;
    int refkl = numlods - 1;
    for (int kc = 0; kc < numclouds; ++kc) {
        const CloudSpec &cloudspec = cloudspecs[kc];
        if (cloudspec.nquads[refkl] > 0) {
            cloudspecs_m.push_back(cloudspec);
        } else {
            for (int kl = 0; kl < numlods; ++kl) {
                numquads[kl] -= cloudspec.nquads[kl];
            }
        }
    }
    cloudspecs = cloudspecs_m;
    numclouds = cloudspecs.size();
    if (timeit) {
        std::vector<int> cqs1;
        if (lodaccum) {
            cqs1 = std::vector<int>(numclouds, 0);
        }
        for (int kl = numlods - 1; kl >= 0; --kl) {
            std::vector<int> cqs1na(numclouds);
            for (int kc = 0; kc < numclouds; ++kc) {
                cqs1na[kc] = cloudspecs[kc].nquads[kl];
            }
            int nqs1na = std::accumulate(cqs1na.begin(), cqs1na.end(), 0);
            if (lodaccum) {
                for (int kc = 0; kc < numclouds; ++kc) {
                    cqs1[kc] += cqs1na[kc];
                }
            } else {
                cqs1 = cqs1na;
            }
            int nqs1 = std::accumulate(cqs1.begin(), cqs1.end(), 0);
            printf("clouds-quads-in-lod:  "
                   "lod=%d  quaddens=%.1f[1/km^3]  "
                   "numquads=%d  numquads1=%d  minqpc=%d  maxqpc=%d  "
                   "avgqpc=%.2f  "
                   "\n",
                   kl, quaddens1 * 1e9, nqs1, nqs1na,
                   *std::min_element(cqs1.begin(), cqs1.end()),
                   *std::max_element(cqs1.begin(), cqs1.end()),
                   static_cast<double>(nqs1) / numclouds);
        }
    }
    if (timeit) {
        t2 = stime();
        printf("clouds-distribute-quads:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }

    // Create view direction sorting data.
    GeodesicSphere gds(vsortbase, vsortdivs, 1.0);
    for (int i = 0; i < gds.num_vertices(); ++i) {
        vsortdirs.push_back(gds.normal(i));
        vsmaxoffangs.push_back(gds.max_offset_angle(i));
        std::vector<int> vsnbinds1;
        for (int j = 0; j < gds.num_neighbor_vertices(i); ++j) {
            vsnbinds1.push_back(gds.neighbor_vertex_index(i, j));
        }
        vsnbinds.push_back(vsnbinds1);
    }
    int numvsortdirs = vsortdirs.size();
    if (timeit) {
        double vsavgmaxoffang =
            std::accumulate(vsmaxoffangs.begin(), vsmaxoffangs.end(), 0.0)
            / numvsortdirs;
        double vsmaxoffangsd = 0.0;
        for (int i = 0; i < numvsortdirs; ++i) {
            vsmaxoffangsd += POW2(vsmaxoffangs[i] - vsavgmaxoffang);
        }
        vsmaxoffangsd = sqrt(vsmaxoffangsd / (numvsortdirs - 1));
        printf("clouds-view-sorting:  "
               "numvsortdirs=%d  "
               "maxmaxoffang=%.1f[deg]  minmaxoffang=%.1f[deg]  "
               "avgmaxoffang=%.1f[deg]  maxoffangsd=%.2f[deg]  "
               "\n",
               numvsortdirs,
               todeg(*std::max_element(vsmaxoffangs.begin(), vsmaxoffangs.end())),
               todeg(*std::min_element(vsmaxoffangs.begin(), vsmaxoffangs.end())),
               todeg(vsavgmaxoffang), todeg(vsmaxoffangsd));
    }

    // Vertex format for cloud textures.
    if (_gvformat == NULL) {
        _gvformat = new std::map<int, CPT(GeomVertexFormat)>();
    }
    std::map<int, CPT(GeomVertexFormat)>::const_iterator
        gvformat_it = _gvformat->find(cloudshape);
    CPT(GeomVertexFormat) gvformat;
    if (gvformat_it != _gvformat->end()) {
        gvformat = gvformat_it->second;
    } else {
        PT(GeomVertexArrayFormat) gvarray = new GeomVertexArrayFormat();
        gvarray->add_column(InternalName::get_vertex(), 3,
                            Geom::NT_float32, Geom::C_point);
        gvarray->add_column(InternalName::get_texcoord(), 2,
                            Geom::NT_float32, Geom::C_texcoord);
        if (cloudshape == 0) {
            gvarray->add_column(InternalName::make("offcenter"), 3,
                                Geom::NT_float32, Geom::C_vector);
            gvarray->add_column(InternalName::make("grpoffcenter"), 3,
                                Geom::NT_float32, Geom::C_vector);
            gvarray->add_column(InternalName::make("haxislen"), 4,
                                Geom::NT_float32, Geom::C_vector);
        }
        PT(GeomVertexFormat) gvformat1 = new GeomVertexFormat();
        gvformat1->add_array(gvarray);
        gvformat = GeomVertexFormat::register_format(gvformat1);
        _gvformat->insert(std::make_pair(cloudshape, gvformat));
    }

    // Initialize tiles.
    std::vector<std::vector<TileSpec> > tilespecs;
    for (int it = 0; it < numtilesx; ++it) {
        std::vector<TileSpec> tilespecs1(numtilesy);
        for (int jt = 0; jt < numtilesy; ++jt) {
            TileSpec ts;
            ts.pos = LPoint3(offsetx + (it + 0.5) * tilesizex,
                             offsety + (jt + 0.5) * tilesizey,
                             0.0);
            ts.gvdata = new GeomVertexData("cloud", gvformat, Geom::UH_static);
            ts.gvwvertex = new GeomVertexWriter(ts.gvdata, InternalName::get_vertex());
            ts.gvwtexcoord = new GeomVertexWriter(ts.gvdata, InternalName::get_texcoord());
            if (cloudshape == 0) {
                ts.gvwoffcenter = new GeomVertexWriter(ts.gvdata, "offcenter");
                ts.gvwgrpoffcenter = new GeomVertexWriter(ts.gvdata, "grpoffcenter");
                ts.gvwhaxislen = new GeomVertexWriter(ts.gvdata, "haxislen");
            }
            for (int kv = 0; kv < numvsortdirs; ++kv) {
                std::vector<PT(GeomTriangles)> gtris1(numlods);
                for (int kl = 0; kl < numlods; ++kl) {
                    gtris1[kl] = new GeomTriangles(Geom::UH_static);
                }
                ts.gtris.push_back(gtris1);
            }
            for (int kl = 0; kl < numlods; ++kl) {
                std::vector<QVSpec> qvspecs1;
                ts.qvspecs.push_back(qvspecs1);
            }
            ts.nverts = 0;
            tilespecs1[jt] = ts;
        }
        tilespecs.push_back(tilespecs1);
    }

    // Create quads.
    std::vector<double> minquadsizes(numlods), maxquadsizes(numlods);
    double qszplod = (maxquadsize - minquadsize) / (numlods / 2 + 1);
    for (int kl = 0; kl < numlods; ++kl) {
        minquadsizes[kl] = minquadsize + qszplod * kl;
        maxquadsizes[kl] = maxquadsize;
    }
    LVector3 vfw, vup;
    if (cloudshape == 0) {
        vfw = LVector3(0.0, 1.0, 0.0);
        vup = LVector3(0.0, 0.0, 1.0);
    } else if (cloudshape == 1) {
        vfw = LVector3(0.0, 0.0, 1.0);
        vup = LVector3(0.0, 1.0, 0.0);
    }
    LVector3 vrt = vfw.cross(vup);
    LQuaternion rot;
    int krts[] = {+1, -1, -1, +1};
    int kups[] = {-1, -1, +1, +1};
    for (int ic = 0; ic < numclouds; ++ic) {
        const CloudSpec &cs = cloudspecs[ic];
        const LPoint3 &cpos = cs.pos;
        double cwidth = cs.width, cheight1 = cs.height1, cheight2 = cs.height2;
        const std::vector<int> &cnquads = cs.nquads;
        assert(cheight1 < 0.0 && cheight2 > 0.0);
        double hx = 0.5 * cwidth;
        double hy = 0.5 * cwidth;
        double hz1 = -cheight1;
        double hz2 = cheight2;
        for (int kl = 0; kl < numlods; ++kl) {
            int lminquadsize = minquadsizes[kl];
            int lmaxquadsize = maxquadsizes[kl];
            double dhsz = 0.5 * (lminquadsize - minquadsize);
            double lhx = std::max(hx + dhsz, 0.0);
            double lhy = std::max(hy + dhsz, 0.0);
            double lhz1 = std::max(hz1 + dhsz, 0.0);
            double lhz2 = std::max(hz2 + dhsz, 0.0);
            std::vector<CQSpec> lcqspecs;
            int kq = 0;
            while (kq < cnquads[kl]) {
                LPoint3 qoff(randgen.uniform(-lhx, lhx),
                             randgen.uniform(-lhy, lhy),
                             randgen.uniform(-lhz1, lhz2));
                bool inside = false;
                if (cloudshape == 0) {
                    double rad = qoff.length();
                    double tht = atan2(qoff[1], qoff[0]);
                    double phi = acos(qoff[2] / rad);
                    double stht = sin(tht), ctht = cos(tht);
                    double sphi = sin(phi), cphi = cos(phi);
                    double hz = qoff[2] < 0.0 ? hz1 : hz2;
                    double rad0 = 1.0 / sqrt(POW2(ctht * sphi / hx) +
                                             POW2(stht * sphi / hy) +
                                             POW2(cphi / hz));
                    inside = (rad <= rad0);
                } else if (cloudshape == 1) {
                    double rad = qoff.get_xy().length();
                    double rad0 = sqrt(POW2(hx) + POW2(hy));
                    inside = (rad <= rad0);
                }
                if (inside) {
                    CQSpec cqs;
                    cqs.qoff = qoff;
                    cqs.qsz = randgen.uniform(lminquadsize, lmaxquadsize);
                    lcqspecs.push_back(cqs);
                    kq += 1;
                }
            }
            for (int kcq = 0; kcq < lcqspecs.size(); ++kcq) {
                const LPoint3 &qoff = lcqspecs[kcq].qoff;
                double qsz = lcqspecs[kcq].qsz;
                LPoint3 qpos = cpos + qoff;
                int it = std::min(std::max(static_cast<int>((qpos[0] - offsetx) / tilesizex), 0), numtilesx - 1);
                int jt = std::min(std::max(static_cast<int>((qpos[1] - offsety) / tilesizey), 0), numtilesy - 1);
                TileSpec &ts = tilespecs[it][jt];
                LPoint3 qtpos = qpos - ts.pos;
                double ang = randgen.uniform(-M_PI, M_PI);
                rot.set_from_axis_angle_rad(ang, vfw);
                LVector3 drt = rot.xform(vrt) * (0.5 * qsz);
                LVector3 dup = rot.xform(vup) * (0.5 * qsz);
                int ipt = randgen.randrange(texuvparts.size());
                const LVector4 &tuvp = texuvparts[ipt];
                double uoff = tuvp[0], voff = tuvp[1];
                double ulen = tuvp[2], vlen = tuvp[3];
                for (int w = 0; w < 4; ++w) {
                    int krt = krts[w], kup = kups[w];
                    LVector3 poff = drt * krt + dup * kup;
                    LPoint3 tpos = qtpos + poff;
                    ts.verts.push_back(tpos);
                    int klu = (1 - krt) / 2, klv = (1 + kup) / 2;
                    ts.texuvs.push_back(LVector2(uoff + ulen * klu, voff + vlen * klv));
                    if (cloudshape == 0) {
                        ts.offcs.push_back(poff);
                        ts.grpoffcs.push_back(qoff);
                        ts.hxyz12s.push_back(LVector4(hx, hy, hz1, hz2));
                    }
                }
                QVSpec qvs;
                qvs.qtpos = qtpos; qvs.nverts = ts.nverts;
                ts.qvspecs[kl].push_back(qvs);
                ts.nverts += 4;
            }
        }
    }
    for (int it = 0; it < numtilesx; ++it) {
        for (int jt = 0; jt < numtilesy; ++jt) {
            TileSpec &ts = tilespecs[it][jt];
            ts.gvdata->unclean_set_num_rows(ts.nverts);
            for (int kx = 0; kx < ts.nverts; ++kx) {
                const LPoint3 &vert = ts.verts[kx];
                ts.gvwvertex->add_data3f(vert[0], vert[1], vert[2]);
                const LVector2 &texuv = ts.texuvs[kx];
                ts.gvwtexcoord->add_data2f(texuv[0], texuv[1]);
                if (cloudshape == 0) {
                    const LVector3 &offc = ts.offcs[kx];
                    ts.gvwoffcenter->add_data3f(offc[0], offc[1], offc[2]);
                    const LVector3 &grpoffc = ts.grpoffcs[kx];
                    ts.gvwgrpoffcenter->add_data3f(grpoffc[0], grpoffc[1], grpoffc[2]);
                    const LVector4 &hxyz12 = ts.hxyz12s[kx];
                    ts.gvwhaxislen->add_data4f(hxyz12[0], hxyz12[1], hxyz12[2], hxyz12[3]);
                }
            }
        }
    }
    if (timeit) {
        t2 = stime();
        printf("clouds-create-vertices:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }

    // Create tiles.
    for (int it = 0; it < numtilesx; ++it) {
        for (int jt = 0; jt < numtilesy; ++jt) {
            TileSpec &ts = tilespecs[it][jt];
            for (int kv = 0; kv < numvsortdirs; ++kv) {
                const LVector3 &vd = vsortdirs[kv];
                std::vector<PT(GeomTriangles)> &gtris = ts.gtris[kv];
                for (int iq1 = 0; iq1 < ts.qvspecs.size(); ++iq1) {
                    std::vector<QVSpec> &qvspecs = ts.qvspecs[iq1];
                    for (int iq2 = 0; iq2 < qvspecs.size(); ++iq2) {
                        qvspecs[iq2].set_view_dir(vd);
                    }
                    std::sort(qvspecs.begin(), qvspecs.end());
                }
                for (int kl = 0; kl < numlods; ++kl) {
                    std::vector<std::vector<QVSpec> > qvspecs;
                    if (lodaccum) {
                        for (int w = kl; w < ts.qvspecs.size(); ++w) {
                            qvspecs.push_back(ts.qvspecs[w]);
                        }
                    } else {
                        qvspecs.push_back(ts.qvspecs[kl]);
                    }
                    PT(GeomTriangles) gtris1 = gtris[kl];
                    // Default index column type is NT_uint16, and
                    // add_vertices() would change it automatically
                    // if needed. Since it is not used, change manually.
                    if (ts.nverts >= 1 << 16) {
                        gtris1->set_index_type(Geom::NT_uint32);
                    }
                    int ntinds1 = 0;
                    for (int w1 = 0; w1 < qvspecs.size(); ++w1) {
                        std::vector<QVSpec> &qvspecs1 = qvspecs[w1];
                        for (int w2 = 0; w2 < qvspecs1.size(); ++w2) {
                            ntinds1 += 2;
                        }
                    }
                    GeomVertexArrayData *gvdtris1 = gtris1->modify_vertices();
                    gvdtris1->unclean_set_num_rows(ntinds1 * 3);
                    GeomVertexWriter *gvwtris1 = new GeomVertexWriter(gvdtris1, 0);
                    for (int w1 = 0; w1 < qvspecs.size(); ++w1) {
                        std::vector<QVSpec> &qvspecs1 = qvspecs[w1];
                        for (int w2 = 0; w2 < qvspecs1.size(); ++w2) {
                            int kv0 = qvspecs1[w2].nverts;
                            //gtris1->add_vertices(kv0 + 0, kv0 + 1, kv0 + 2);
                            gvwtris1->add_data1i(kv0 + 0);
                            gvwtris1->add_data1i(kv0 + 1);
                            gvwtris1->add_data1i(kv0 + 2);
                            //gtris1->close_primitive();
                            //gtris1->add_vertices(kv0 + 0, kv0 + 2, kv0 + 3);
                            gvwtris1->add_data1i(kv0 + 0);
                            gvwtris1->add_data1i(kv0 + 2);
                            gvwtris1->add_data1i(kv0 + 3);
                            //gtris1->close_primitive();
                        }
                    }
                    delete gvwtris1;
                }
            }
        }
    }
    if (timeit) {
        t2 = stime();
        printf("clouds-create-triangles:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }

    // Finalize tiles.
    NodePath tileroot("clouds");
    double tileradius = 0.5 * sqrt(POW2(tilesizex) + POW2(tilesizey));
    for (int kv = 0; kv < numvsortdirs; ++kv) {
        std::ostringstream oss;
        oss << "tiling" << "-v" << kv;
        NodePath vtiling = tileroot.attach_new_node(oss.str());
        for (int it = 0; it < numtilesx; ++it) {
            for (int jt = 0; jt < numtilesy; ++jt) {
                TileSpec &ts = tilespecs[it][jt];
                std::ostringstream oss;
                oss << "tile" << "-v" << kv << "-i" << it << "-j" << jt;
                PT(LODNode) tlod = new LODNode(oss.str());
                NodePath ijtile = vtiling.attach_new_node(tlod);
                ijtile.set_pos(ts.pos);
                for (int kl = 0; kl < numlods; ++kl) {
                    GeomTriangles *gtris = ts.gtris[kv][kl];
                    PT(Geom) tgeom = new Geom(ts.gvdata);
                    tgeom->add_primitive(gtris);
                    std::ostringstream oss;
                    oss << "tile" << "-v" << kv << "-i" << it << "-j" << jt << "-l" << kl;
                    PT(GeomNode) tnode = new GeomNode(oss.str());
                    tnode->add_geom(tgeom);
                    NodePath ltile(tnode);
                    tlod->add_switch(tileradius * (kl + 1), tileradius * kl);
                    ltile.reparent_to(ijtile);
                }
            }
        }
    }
    if (timeit) {
        t2 = stime();
        printf("clouds-create-tiles:  time=%.3f[s]\n", t2 - t1);
        t1 = t2;
    }

    if (timeit) {
        t2 = stime();
        printf("clouds-cumulative:  time=%.3f[s]\n", t2 - t0);
        t1 = t2;
    }

    numtilesx_ = numtilesx; numtilesy_ = numtilesy;
    tilesizex_ = tilesizex; tilesizey_ = tilesizey;
    numlods_ = numlods; offsetz_ = offsetz;

    tileroot_ = tileroot;

    for (int it = 0; it < numtilesx; ++it) {
        for (int jt = 0; jt < numtilesy; ++jt) {
            TileSpec &ts = tilespecs[it][jt];
            delete ts.gvwvertex;
            delete ts.gvwtexcoord;
            if (cloudshape == 0) {
                delete ts.gvwoffcenter;
                delete ts.gvwgrpoffcenter;
                delete ts.gvwhaxislen;
            }
        }
    }
}

void CloudsGeom::_derive_cell_data (double size, double wtilesize,
                                    int &numtiles, double &tilesize)
{
    numtiles = static_cast<int>(ceil(size / wtilesize));
    tilesize = size / numtiles;
}

int CloudsGeom::num_tiles_x () const
{
    return _numtilesx;
}

int CloudsGeom::num_tiles_y () const
{
    return _numtilesy;
}

double CloudsGeom::tile_size_x () const
{
    return _tilesizex;
}

double CloudsGeom::tile_size_y () const
{
    return _tilesizey;
}

int CloudsGeom::num_lods () const
{
    return _numlods;
}

double CloudsGeom::offset_z () const
{
    return _offsetz;
}

NodePath CloudsGeom::tile_root ()
{
    return _tileroot;
}

int CloudsGeom::update_visual_sort_dir_index (
    const LVector3 &camdir, int vsind0) const
{
    int vsind = vsind0;
    // Quick search, only among neighbors of current direction.
    const std::vector<int> &vsnbinds0 = _vsnbinds[vsind0];
    double vsmaxoffang0 = _vsmaxoffangs[vsind0];
    const LVector3 &vsortdir0 = _vsortdirs[vsind0];
    double maxdotp = camdir.dot(vsortdir0);
    for (int j = 0; j < vsnbinds0.size(); ++j) {
        int vsind1 = vsnbinds0[j];
        double dotp = camdir.dot(_vsortdirs[vsind1]);
        if (maxdotp < dotp) {
            maxdotp = dotp;
            vsind = vsind1;
        }
    }
    // Slow search if needed, among all directions.
    double vsoffang = acos(std::min(std::max(maxdotp, -1.0), 1.0));
    if (vsoffang > 2 * vsmaxoffang0) {
        for (int i = 0; i < _vsortdirs.size(); ++i) {
            double dotp = camdir.dot(_vsortdirs[i]);
            if (maxdotp < dotp) {
                maxdotp = dotp;
                vsind = i;
            }
        }
    }
    return vsind;
}


INITIALIZE_TYPE_HANDLE(GeodesicSphere)

GeodesicSphere::GeodesicSphere (int base, int numdivs, double radius)
{
    if (base >= 0) {
        _construct(base, numdivs, radius,
                   _verts, _norms, _tris, _maxoffangs, _nbinds);
    } else {
        _verts.push_back(LVector3(0.0, 1.0, 0.0));
        _norms.push_back(LVector3(0.0, 1.0, 0.0));
        _maxoffangs.push_back(M_PI + 1e-6);
        _nbinds.push_back(std::vector<int>());
    }
}

GeodesicSphere::~GeodesicSphere ()
{
}

void GeodesicSphere::_construct (
    int base, int numdivs, double radius,
    std::vector<LVector3> &verts, std::vector<LVector3> &norms,
    std::vector<LVector3i> &tris, std::vector<double> &maxoffangs,
    std::vector<std::vector<int> > &nbinds)
{
    std::map<std::pair<int, int>, int> edgesplits;

    // Create canonical polyhedron points.
    std::vector<LPoint3> ps;
    if (base == 0) { // tetrahedron
        double phi = 1.0 / sqrt(2.0);
        int k1s[] = {-1, 1};
        for (int i = 0; i < 2; ++i) {
            int k1 = k1s[i];
            LPoint3 p1(k1 * 1.0, 0.0, -phi);
            LPoint3 p2(0.0, k1 * 1.0, phi);
            ps.push_back(p1); ps.push_back(p2);
        }
    } else if (base == 1) { // octahedron
        int k1s[] = {-1, 1};
        for (int i = 0; i < 2; ++i) {
            int k1 = k1s[i];
            LPoint3 p1(k1 * 1.0, 0.0, 0.0);
            LPoint3 p2(0.0, k1 * 1.0, 0.0);
            LPoint3 p3(0.0, 0.0, k1 * 1.0);
            ps.push_back(p1); ps.push_back(p2); ps.push_back(p3);
        }
    } else if (base == 2) { // icosahedron
        double phi = 0.5 * (1.0 + sqrt(5.0));
        int k1s[] = {-1, 1, 1, -1};
        int k2s[] = {-1, -1, 1, 1};
        for (int i = 0; i < 4; ++i) {
            int k1 = k1s[i], k2 = k2s[i];
            LPoint3 p1(0.0, k1 * 1.0, k2 * phi);
            LPoint3 p2(k1 * 1.0, k2 * phi, 0.0);
            LPoint3 p3(k2 * phi, 0.0, k1 * 1.0);
            ps.push_back(p1); ps.push_back(p2); ps.push_back(p3);
        }
    } else {
        fprintf(stderr,
            "Expected base in (0, 1, 2), got %d.\n", base);
        std::exit(1);
    }

    // Create base vertices and normals from canonical points.
    for (int i = 0; i < ps.size(); ++i) {
        const LPoint3 &p = ps[i];
        LVector3 n(p);
        n.normalize();
        LPoint3 v = n * radius;
        verts.push_back(v);
        norms.push_back(n);
    }

    // Brute force assembly of triangle-faced regular polyhedron.
    // Determine edge length as minimum distance between two vertices.
    // Go through each vertex, collecting all neighboring vertices as those
    // at edge lenght distance, and making all combinations of triangles
    // between the center vertex and neighboring verticess at edge lenght
    // from one another. Accept only triangles whose normal dot product
    // with center vertex normal is positive. First vertex index
    // of triangle must be the smallest. Add such triangles to a set,
    // so that non-unique triangles are ignored.
    int nbvs = norms.size();
    double l = radius * 2;
    for (int i = 0; i < nbvs - 1; ++i) {
        for (int j = i + 1; j < nbvs; ++j) {
            double d = (verts[i] - verts[j]).length();
            l = std::min(l, d);
        }
    }
    std::set<LVector3i> btris;
    for (int ic = 0; ic < verts.size(); ++ic) {
        const LPoint3 &vc = verts[ic];
        std::vector<int> ins;
        for (int i = 0; i < verts.size(); ++i) {
            const LPoint3 &v = verts[i];
            if (i != ic && (v - vc).length() < l * 1.001) {
                ins.push_back(i);
            }
        }
        int nins = ins.size();
        const LVector3 &nc = norms[ic];
        for (int k1 = 0; k1 < nins - 1; ++k1) {
            int i1 = ins[k1];
            const LVector3 &v1 = verts[i1];
            for (int k2 = k1 + 1; k2 < nins; ++k2) {
                int i2 = ins[k2];
                const LVector3 &v2 = verts[i2];
                if ((v1 - v2).length() < l * 1.001) {
                    std::vector<int> btri1;
                    btri1.push_back(ic); btri1.push_back(i1); btri1.push_back(i2);
                    std::sort(btri1.begin(), btri1.end());
                    LVector3i btri(btri1[0], btri1[1], btri1[2]);
                    const LVector3 &v1s = verts[btri[0]], &v2s = verts[btri[1]], &v3s = verts[btri[2]];
                    LVector3 nt = (v2s - v1s).cross(v3s - v1s);
                    nt.normalize();
                    if (nt.dot(nc) < 0.0) {
                        std::swap(btri[1], btri[2]);
                    }
                    btris.insert(btri);
                }
            }
        }
    }

    // Subdivide basic triangles.
    std::vector<LVector3i> obtris(btris.begin(), btris.end());
    std::sort(obtris.begin(), obtris.end());
    for (int i = 0; i < obtris.size(); ++i) {
        const LVector3i &btri = obtris[i];
        int i1 = btri[0], i2 = btri[1], i3 = btri[2];
        _split_triangle(radius, verts, norms, tris, edgesplits,
                        i1, i2, i3, verts[i1], verts[i2], verts[i3], numdivs);
    }

    // For each vertex, compute maximum half-angle between its normal and
    // neighboring normals. To this end, for each vertex nearest
    // neighbors must be determined.
    for (int ic = 0; ic < norms.size(); ++ic) {
        const LVector3 &nc = norms[ic];
        std::set<int> ins;
        int nt1 = 0;
        for (int i = 0; i < tris.size(); ++i) {
            const LVector3i &tri = tris[i];
            if (ic == tri[0] || ic == tri[1] || ic == tri[2]) {
                nt1 += 1;
                ins.insert(tri[0]); ins.insert(tri[1]); ins.insert(tri[2]);
            }
        }
        ins.erase(ic);
        std::vector<int> oins(ins.begin(), ins.end());
        std::sort(oins.begin(), oins.end());
        nbinds.push_back(oins);
        double maxoffang = 0.0;
        for (int k = 0; k < oins.size(); ++k) {
            int i = oins[k];
            const LVector3 &n = norms[i];
            double offang = 0.5 * acos(std::min(std::max(static_cast<double>(nc.dot(n)), -1.0), 1.0));
            maxoffang = std::max(maxoffang, offang);
        }
        maxoffangs.push_back(maxoffang);
    }
}

void GeodesicSphere::_split_triangle (
    double radius,
    std::vector<LVector3> &verts, std::vector<LVector3> &norms,
    std::vector<LVector3i> &tris,
    std::map<std::pair<int, int>, int> &edgesplits,
    int i1, int i2, int i3,
    const LVector3 &v1, const LVector3 &v2, const LVector3 &v3,
    int numdivs)
{
    if (numdivs == 0) {
        tris.push_back(LVector3i(i1, i2, i3));
    } else {
        LVector3 n12 = (v1 + v2) * 0.5;
        n12.normalize();
        LVector3 n23 = (v2 + v3) * 0.5;
        n23.normalize();
        LVector3 n31 = (v3 + v1) * 0.5;
        n31.normalize();

        LVector3 v12 = n12 * radius;
        LVector3 v23 = n23 * radius;
        LVector3 v31 = n31 * radius;

        int ias[] = {i1, i2, i3};
        int ibs[] = {i2, i3, i1};
        const LVector3 *vs[] = {&v12, &v23, &v31};
        const LVector3 *ns[] = {&n12, &n23, &n31};
        std::vector<int> eis(3);
        for (int k = 0; k < 3; ++k) {
            int ia = ias[k], ib = ibs[k];
            const LVector3 &v = *vs[k], &n = *ns[k];
            if (ia > ib) {
                std::swap(ia, ib);
            }
            int iab;
            std::map<std::pair<int, int>, int>::const_iterator
                iab_it = edgesplits.find(std::make_pair(ia, ib));
            if (iab_it != edgesplits.end()) {
                iab = iab_it->second;
            } else {
                iab = verts.size();
                edgesplits[std::make_pair(ia, ib)] = iab;
                verts.push_back(v);
                norms.push_back(n);
            }
            eis[k] = iab;
        }
        int i12 = eis[0], i23 = eis[1], i31 = eis[2];

        _split_triangle(radius, verts, norms, tris, edgesplits,
                        i1, i12, i31, v1, v12, v31, numdivs - 1);
        _split_triangle(radius, verts, norms, tris, edgesplits,
                        i2, i23, i12, v2, v23, v12, numdivs - 1);
        _split_triangle(radius, verts, norms, tris, edgesplits,
                        i3, i31, i23, v3, v31, v23, numdivs - 1);
        _split_triangle(radius, verts, norms, tris, edgesplits,
                        i12, i23, i31, v12, v23, v31, numdivs - 1);
    }
}

int GeodesicSphere::num_vertices () const
{
    return _verts.size();
}

LVector3 GeodesicSphere::vertex (int i) const
{
    return _verts[i];
}

LVector3 GeodesicSphere::normal (int i) const
{
    return _norms[i];
}

double GeodesicSphere::max_offset_angle (int i) const
{
    return _maxoffangs[i];
}

int GeodesicSphere::num_neighbor_vertices (int i) const
{
    return _nbinds[i].size();
}

int GeodesicSphere::neighbor_vertex_index (int i, int j) const
{
    return _nbinds[i][j];
}

int GeodesicSphere::num_tris () const
{
    return _tris.size();
}

LVector3i GeodesicSphere::tri (int i) const
{
    return _tris[i];
}


INITIALIZE_TYPE_HANDLE(TexUVParts)

TexUVParts::TexUVParts ()
{
}

TexUVParts::~TexUVParts ()
{
}

void TexUVParts::add_part (const LVector4 &part)
{
    _parts.push_back(part);
}

int TexUVParts::num_parts () const
{
    return _parts.size();
}

LVector4 TexUVParts::part (int i) const
{
    return _parts[i];
}


