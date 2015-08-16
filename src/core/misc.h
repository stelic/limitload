#ifndef MISC_H
#define MISC_H

#include <lvector2.h>
#include <lvector3.h>
#include <lvector4.h>
#include <lpoint2.h>
#include <lpoint3.h>
#include <geomVertexWriter.h>

#include <typeinit.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_MISC
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

BEGIN_PUBLISH

/**
 * Clamp a scalar value to an interval.
 *
 * If the value is inside the interval, it is returned as-is.
 * If it is outside, the nearest boundary value is returned instead.
 * Boundary values do not have to be in particular order.
 */
double EXPORT clamp (double val, double val0, double val1);

/**
 * Compute unit vector.
 *
 * If length of the input is zero, zero-vector is returned.
 */
#define UNITV3(T1, T2) \
inline T1 unitv (const T2 &v) \
{ \
    double lv = v.length(); \
    return lv != 0.0 ? T1(v[0] / lv, v[1] / lv, v[2] / lv) : T1(0.0, 0.0, 0.0); \
}
UNITV3(LVector3f, LVecBase3f)
UNITV3(LVector3f, LVector3f)
UNITV3(LVector3f, LPoint3f)
UNITV3(LVector3d, LVecBase3d)
UNITV3(LVector3d, LVector3d)
UNITV3(LVector3d, LPoint3d)
#define UNITV2(T1, T2) \
inline T1 unitv (const T2 &v) \
{ \
    double lv = v.length(); \
    return lv != 0.0 ? T1(v[0] / lv, v[1] / lv) : T1(0.0, 0.0); \
}
UNITV2(LVector2f, LVecBase2f)
UNITV2(LVector2f, LVector2f)
UNITV2(LVector2f, LPoint2f)
UNITV2(LVector2d, LVecBase2d)
UNITV2(LVector2d, LVector2d)
UNITV2(LVector2d, LPoint2d)

/**
 * Convert heading-pitch-roll to unit vector.
 *
 * Roll value is ignored.
 */
LVector3f EXPORT hprtovec (const LVecBase3f &hpr);

/**
 * Solve quadratic equation.
 *
 * The equation is in the form
 *     a * x**2 + b * x + c = 0.
 *
 * If roots are real, returns true and sets x such that x[0] <= x[1].
 * If roots are complex or a == b == 0, returns false.
 */
bool EXPORT solve_quad_s (double a, double b, double c, LVecBase2d &x);

/**
 * Get smallest positive root of quadratic equation.
 *
 * Like solve_quad_s, but computes only the smallest positive real root,
 * if it exists, and sets x[0] to it and returns true.
 * Otherwise returns false.
 */
bool EXPORT solve_quad_minpos_s (double a, double b, double c, LVecBase2d &x);

/**
 * Compute time to intercept.
 *
 * Object T is initially at tpos, has velocity tvel,
 * and accelerates at constant rate tacc.
 * Object I starts from ipos to intercept T, with initial velocity which is
 * the sum of the fixed component ifvel and the component of magnitude idvelp
 * in the unknown direction idir, and with constant acceleration which is
 * the sum of the fixed component ifacc and the component of magnitude idaccp
 * in the same unknown direction idir.
 * First an approximate time to intercept is computed, such that
 * higher order terms are neglected, but no iterative solving is needed.
 * If the approximate time itime is smaller than finetime, iterative solving
 * is performed to get a more accurate answer, either to within epstime
 * or until maxiter iterations have been performed, whichever happens first.
 * If I can intercept T according to approximate time computation,
 * true is returned, itime[0] is set to time to intercept,
 * cpos is set to the collision point, and idir is set to
 * the unknown initial velocity/acceleration component direction.
 * If I cannot intercept T, false is returned.
 */
bool EXPORT intercept_time_s (const LPoint3d &tpos, const LVector3d &tvel,
                              const LVector3d &tacc, const LPoint3d &ipos,
                              const LVector3d &ifvel, double idvelp,
                              const LVector3d &ifacc, double idaccp,
                              double finetime, double epstime, int maxiter,
                              LVecBase2d &itime, LPoint3d &cpos, LVector3d &idir);

/**
 * Compute texture frame data (u_offset, v_offset, u_span, v_span)
 * for texsplit x texsplit grid of frames and given frame index frind.
 * Frame indexing is row-wise, starting from top left corner.
 */
LVector4f EXPORT texture_frame (int texsplit, int frind);

/**
 * Reset quasi-random number generation using given seed.
 * If seed is negative, system time is taken instead.
 **/
#define RESET_RANDOM(reset_random) \
void EXPORT reset_random (int seed = -1);
RESET_RANDOM(reset_random)
RESET_RANDOM(fx_reset_random)

/**
 * Compute quasi-random real number in [0, 1) with uniform distribution.
 **/
#define RANDUNIT(randunit) \
double EXPORT randunit ();
RANDUNIT(randunit)
RANDUNIT(fx_randunit)

/**
 * Produce random unit vector.
 *
 * Ranges for heading (minh, maxh) and pitch (minp, maxp)
 * can be given to limit the direction.
 */
#define RANDVEC(randvec) \
LVector3f EXPORT randvec (double minh = -180.0, double maxh = 180.0, \
                          double minp = -90.0, double maxp = 90.0);
RANDVEC(randvec)
RANDVEC(fx_randvec)

END_PUBLISH

#define POW2(x) ((x) * (x))
#define POW3(x) ((x) * (x) * (x))

double EXPORT stime ();

class EXPORT RandomBase : public TypedObject
{
PUBLISHED:
    RandomBase (int seed = -1);
    double random ();

private:
    int _x, _y, _z;

DECLARE_TYPE_HANDLE(RandomBase)
};

class EXPORT NumRandom : public TypedObject
{
PUBLISHED:
    NumRandom (int seed = -1);
    double randunit ();
    double uniform (double a, double b);
    int randrange (int a);
    int randrange (int a, int b);
    LVector3f randvec (double minh = -180.0, double maxh = 180.0,
                       double minp = -90.0, double maxp = 90.0);

private:
    RandomBase _rb;

DECLARE_TYPE_HANDLE(NumRandom)
};

class EXPORT HaltonDistrib : public TypedObject
{
PUBLISHED:
    HaltonDistrib (int startind);

    double next1 ();
    LVecBase2 next2 ();
    LVecBase3 next3 ();

private:
    static double _get_r (int base, int i);

    int _index;

DECLARE_TYPE_HANDLE(HaltonDistrib)
};

#ifdef _MSC_VER
/**
 * fmax from C99.
 */
double EXPORT fmax (double a, double b);
#endif

/**
 * Convert angle from degrees to radians.
 */
double EXPORT torad (double a);

/**
 * Convert angle from radians to degrees.
 */
double EXPORT todeg (double a);

/**
 * Compute quasi-random real number in [0, 1) with uniform distribution.
 */
#define UNIFORM0(uniform0) \
double EXPORT uniform0 ();
UNIFORM0(uniform0)
UNIFORM0(fx_uniform0)

/**
 * Compute quasi-random real number in [0, a) with uniform distribution.
 */
#define UNIFORM1(uniform1) \
double EXPORT uniform1 (double a);
UNIFORM1(uniform1)
UNIFORM1(fx_uniform1)

/**
 * Compute quasi-random real number in [a, b) with uniform distribution.
 */
#define UNIFORM2(uniform2) \
double EXPORT uniform2 (double a, double b);
UNIFORM2(uniform2)
UNIFORM2(fx_uniform2)

/**
 * Compute quasi-random integer number in [0, a) with uniform distribution.
 */
#define RANDRANGE1(randrange1) \
int EXPORT randrange1 (int a);
RANDRANGE1(randrange1)
RANDRANGE1(fx_randrange1)

/**
 * Compute quasi-random integer number in [a, b) with uniform distribution.
 */
#define RANDRANGE2(randrange2) \
int EXPORT randrange2 (int a, int b);
RANDRANGE2(randrange2)
RANDRANGE2(fx_randrange2)

LVector3f EXPORT vrot (const LVector3f &e1, const LVector3f &e2,
                       double rad, double ang);

#define V2f LVector2f
#define V3f LVector3f
#define V4f LVector4f
#define P3f LPoint3f
void EXPORT add_tri (GeomVertexWriter *gvwvertex, GeomVertexWriter *gvwcolor,
                     GeomVertexWriter *gvwtexcoord, GeomVertexWriter *gvwnormal,
                     const P3f &p1, const V3f &n1, const V4f &c1, const V2f &t1,
                     const P3f &p2, const V3f &n2, const V4f &c2, const V2f &t2,
                     const P3f &p3, const V3f &n3, const V4f &c3, const V2f &t3);

class EXPORT MiniConfigParser
{
public:

    MiniConfigParser (const std::string &fpath);
    ~MiniConfigParser ();

    std::string file_path () const;

    bool has_section (const std::string &section) const;
    bool has_option (const std::string &section, const std::string &option) const;
    std::vector<std::string> sections () const;
    std::vector<std::string> options (const std::string &section) const;

    std::string get_string (const std::string &section, const std::string &option) const;
    std::string get_string (const std::string &section, const std::string &option,
                            const std::string &defval) const;

    int get_int (const std::string &section, const std::string &option) const;
    int get_int (const std::string &section, const std::string &option,
                 int defval) const;

    double get_real (const std::string &section, const std::string &option) const;
    double get_real (const std::string &section, const std::string &option,
                     double defval) const;

private:

    std::string _path;
    std::map<std::string, std::map<std::string, std::string> > _section_map;

    static void _parse_file (
        const std::string &fpath,
        std::map<std::string, std::map<std::string, std::string> > &section_map);

    void _get_string (const std::string &section, const std::string &option,
                      bool mustexist, std::string &value, bool &exists) const;

    int _get_int (const std::string &section, const std::string &option,
                  int *defval) const;

    double _get_real (const std::string &section, const std::string &option,
                      double *defval) const;
};

#include <vector>
#include <pta_int.h>
typedef PTA_int ENC_LST_INT;
std::vector<int> EXPORT dec_lst_int (ENC_LST_INT enc_lst);

#include <vector>
#include <pta_int.h>
typedef PTA_int ENC_LST_BOOL;
std::vector<bool> EXPORT dec_lst_bool (ENC_LST_BOOL enc_lst);

#include <vector>
#include <string>
typedef const std::string & ENC_LST_STRING;
std::vector<std::string> EXPORT dec_lst_string (ENC_LST_STRING enc_lst);

#endif
