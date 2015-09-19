#ifdef _MSC_VER
#define _USE_MATH_DEFINES
#endif
#include <cmath>

#include <lpoint2.h>

#include <table.h>

static void _init_table ()
{
    static bool initialized = false;
    if (initialized) {
        return;
    }
    initialized = true;
    INITIALIZE_TYPE(UnitGrid2)
}
DToolConfigure(config_limload_table);
DToolConfigureFn(config_limload_table) { _init_table(); }


INITIALIZE_TYPE_HANDLE(UnitGrid2)

UnitGrid2::UnitGrid2 (const std::string &pnm_path)
{
    PNMImage img(pnm_path);
    if (!img.is_valid()) {
        fprintf(stderr,
            "Cannot read image file '%s'.\n", pnm_path.c_str());
        std::exit(1);
    }
    _grid = _grid_from_pnm(img);
    _init_rest();
}

UnitGrid2::UnitGrid2 (const PNMImage &pnm)
{
    _grid = _grid_from_pnm(pnm);
    _init_rest();
}

UnitGrid2::UnitGrid2 (double v)
{
    _grid.push_back(std::vector<double>(1));
    _grid[0][0] = v;
    _init_rest();
}

void UnitGrid2::_init_rest ()
{
    _num_x = _grid.size();
    _num_y = _grid[0].size();
}

std::vector<std::vector<double> > UnitGrid2::_grid_from_pnm (const PNMImage &pnm)
{
    int sx = pnm.get_read_x_size();
    int sy = pnm.get_read_y_size();
    std::vector<std::vector<double> > grid;
    for (int i = 0; i < sx; ++i) {
        grid.push_back(std::vector<double>(sy));
        for (int j = 0; j < sy; ++j) {
            grid[i][j] = pnm.get_gray(i, sy - j - 1);
        }
    }
    return grid;
}

UnitGrid2::~UnitGrid2 ()
{
}

int UnitGrid2::num_x () const
{
    return _num_x;
}

int UnitGrid2::num_y () const
{
    return _num_y;
}

double UnitGrid2::operator() (double xr, double yr,
                              double tol, bool periodic) const
{
    return _interpolate_unit(_grid, _num_x, _num_y, xr, yr, tol, periodic);
}

double UnitGrid2::_interpolate_unit (const std::vector<std::vector<double> > &grid,
                                     int numx, int numy, double xr, double yr,
                                     double tol, bool periodic)
{
    #define Pt LPoint2d

    int i1, j1;
    _unit_to_index2(numx, numy, xr, yr, tol, periodic,
                    i1, j1, xr, yr);
    if (i1 < 0 || j1 < 0) { // not valid
        return 0.0;
    }
    double x1 = (i1 + 0.5) / numx;
    double y1 = (j1 + 0.5) / numy;
    int di = xr > x1 ? 1 : -1;
    int dj = yr > y1 ? 1 : -1;
    int di2 = di, dj2 = 0;
    int i2, j2;
    _shift_index2(numx, numy, i1, j1, di2, dj2, periodic,
                  i2, j2);
    int di3 = di, dj3 = dj;
    int i3, j3;
    _shift_index2(numx, numy, i1, j1, di3, dj3, periodic,
                  i3, j3);
    int di4 = 0, dj4 = dj;
    int i4, j4;
    _shift_index2(numx, numy, i1, j1, di4, dj4, periodic,
                  i4, j4);
    // NOTE: Must not use iN, jN below when computing relative coordinates,
    // in case there was wrap due to periodicity.

    double v;
    if (i2 >= 0 && i3 >= 0 && i4 >= 0) { // three neighbors
        // Bilinear interpolation.
        double x3 = (i1 + di3 + 0.5) / numx;
        double y3 = (j1 + dj3 + 0.5) / numy;
        double fd = (x3 - x1) * (y3 - y1);
        double f1 = (x3 - xr) * (y3 - yr);
        double f2 = (xr - x1) * (y3 - yr);
        double f3 = (xr - x1) * (yr - y1);
        double f4 = (x3 - xr) * (yr - y1);
        double v1 = grid[i1][j1];
        double v2 = grid[i2][j2];
        double v3 = grid[i3][j3];
        double v4 = grid[i4][j4];
        v = (v1 * f1 + v2 * f2 + v3 * f3 + v4 * f4) / fd;

    } else if (i2 >= 0 || i3 >= 0 || i4 >= 0) { // one neighbor
        // Linear interpolation.
        if (i2 >= 0) {
            i2 = i2; j2 = j2; di2 = di2; dj2 = dj2;
        } else if (i3 >= 0) {
            i2 = i3; j2 = j3; di2 = di3; dj2 = dj3;
        } else if (i4 >= 0) {
            i2 = i4; j2 = j4; di2 = di4; dj2 = dj4;
        }
        Pt r(xr, yr);
        double x2 = (i1 + di2 + 0.5) / numx;
        double y2 = (j1 + dj2 + 0.5) / numy;
        Pt r1(x1, y1);
        Pt r2(x2, y2);
        Pt udr = r2 - r1;
        udr.normalize();
        double l1 = (r - r1).dot(udr);
        double l2 = (r2 - r).dot(udr);
        double v1 = grid[i1][j1];
        double v2 = grid[i2][j2];
        v = (v1 * l2 + v2 * l1) / (l1 + l2);

    } else { // no neighbors (two neighbors not possible)
        v = grid[i1][j1];
    }

    return v;
}

void UnitGrid2::_unit_to_index (int num, double u, double tol, bool periodic,
                                int &k, double &umod)
{
    k = int(u * num);
    if (k < 0) {
        if (periodic) {
            while (k < 0) {
                k += num;
                u += 1.0;
            }
        } else if (u > -tol / num) {
            k = 0;
            u = 0.0;
        } else { // not valid
            k = -1;
            u = -1.0;
        }
    } else if (k >= num) {
        if (periodic) {
            while (k >= num) {
                k -= num;
                u -= 1.0;
            }
        } else if (u < 1.0 + tol / num) {
            k = num - 1;
            u = 1.0;
        } else { // not valid
            k = -1;
            u = -1.0;
        }
    }
    umod = u;
}

void UnitGrid2::_unit_to_index2 (int numx, int numy, double xr, double yr,
                                 double tol, bool periodic,
                                 int &i, int &j, double &xrmod, double &yrmod)
{
    _unit_to_index(numx, xr, tol, periodic, i, xrmod);
    _unit_to_index(numy, yr, tol, periodic, j, yrmod);
    if (i < 0 || j < 0) { // not valid
        i = -1; j = -1;
    }
}

void UnitGrid2::_shift_index (int num, int k, int dk, bool periodic,
                              int &kmod)
{
    k += dk;
    if (k < 0) {
        if (periodic) {
            while (k < 0) {
                k += num;
            }
        } else { // not valid
            k = -1;
        }
    } else if (k >= num) {
        if (periodic) {
            while (k >= num) {
                k -= num;
            }
        } else { // not valid
            k = -1;
        }
    }
    kmod = k;
}

void UnitGrid2::_shift_index2 (int numx, int numy,
                               int i, int j, int di, int dj,
                               bool periodic,
                               int &imod, int &jmod)
{
    _shift_index(numx, i, di, periodic, imod);
    _shift_index(numy, j, dj, periodic, jmod);
    if (imod < 0 || jmod < 0) { // not valid
        imod = -1; jmod = -1;
    }
}

