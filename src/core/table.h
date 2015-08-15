#ifndef TABLE_H
#define TABLE_H

#include <pnmImage.h>

#include <typeinit.h>

#undef EXPORT
#undef EXTERN
#undef TEMPLATE
#if !defined(CPPPARSER)
    #if defined(LINGCC)
        #define EXPORT
        #define EXTERN
    #elif defined(WINMSVC)
        #ifdef BUILDING_TABLE
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

class EXPORT UnitGrid2 : public TypedObject
{
PUBLISHED:

    UnitGrid2 (const std::string &pnm_path);
    UnitGrid2 (const PNMImage &pnm);
    UnitGrid2 (double v);
    ~UnitGrid2 ();

    int num_x () const;
    int num_y () const;

    double operator() (double xr, double yr,
                       double tol = 0.0, bool periodic = false) const;

private:

    std::vector<std::vector<double> > _grid;
    int _num_x;
    int _num_y;

    void _init_rest ();

    static std::vector<std::vector<double> > _grid_from_pnm (const PNMImage &pnm);

    static double _interpolate_unit (const std::vector<std::vector<double> > &grid,
                                     int numx, int numy, double xr, double yr,
                                     double tol, bool periodic);

    static void _unit_to_index (int num, double u, double tol, bool periodic,
                                int &k, double &umod);

    static void _unit_to_index2 (int numx, int numy, double xr, double yr,
                                 double tol, bool periodic,
                                 int &i, int &j, double &xrmod, double &yrmod);

    static void _shift_index (int num, int k, int dk, bool periodic,
                              int &kmod);

    static void _shift_index2 (int numx, int numy,
                               int i, int j, int di, int dj,
                               bool periodic,
                               int &imod, int &jmod);

DECLARE_TYPE_HANDLE(UnitGrid2)
};

#endif
