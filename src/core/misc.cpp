#ifdef _MSC_VER
#define _USE_MATH_DEFINES
#endif
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <sstream>

#include <lquaternion.h>

#include <misc.h>

static void _init_misc ()
{
    static bool initialized = false;
    if (initialized) {
        return;
    }
    initialized = true;
    INITIALIZE_TYPE(HaltonDistrib)
    INITIALIZE_TYPE(RandomBase)
    INITIALIZE_TYPE(NumRandom)
}
DToolConfigure(config_limload_misc);
DToolConfigureFn(config_limload_misc) { _init_misc(); }

double clamp (double val, double val0, double val1)
{
    double valmin, valmax;
    if (val0 < val1) {
        valmin = val0;
        valmax = val1;
    } else {
        valmax = val0;
        valmin = val1;
    }

    if (val < valmin) {
        return valmin;
    } else if (val > valmax) {
        return valmax;
    } else {
        return val;
    }
}

LVector3f hprtovec (const LVecBase3f &hpr)
{
    LQuaternionf q;
    q.set_hpr(hpr);
    LVector3f vec = LVector3f(q.xform(LVector3f(0.0, 1.0, 0.0)));
    vec.normalize();
    return vec;
}

bool solve_quad_s (double a, double b, double c, LVecBase2d &x)
{
    bool exist = false;
    if (a != 0.0) {
        double d = POW2(b) - 4 * a * c;
        if (d >= 0.0) {
            exist = true;
            double rd = sqrt(d);
            double x1 = (-b - rd) / (2 * a);
            double x2 = (-b + rd) / (2 * a);
            if (x1 > x2) {
                double tmp = x1; x1 = x2; x2 = tmp;
            }
            x[0] = x1; x[1] = x2;
        }
    } else if (b != 0.0) {
        exist = true;
        double x1 = - c / b;
        x[0] = x[1] = x1;
    }
    return exist;
}

bool solve_quad_minpos_s (double a, double b, double c, LVecBase2d &x)
{
    bool exist = false;
    if (solve_quad_s(a, b, c, x)) {
        // Guaranteed order x[0] <= x[1].
        if (x[0] > 0.0) {
            exist = true;
        } else if (x[1] > 0.0) {
            exist = true;
            x[0] = x[1];
        }
    }
    return exist;
}

bool intercept_time_s (const LPoint3d &tpos, const LVector3d &tvel,
                       const LVector3d &tacc, const LPoint3d &ipos,
                       const LVector3d &ifvel, double idvelp,
                       const LVector3d &ifacc, double idaccp,
                       double finetime, double epstime, int maxiter,
                       LVecBase2d &itime, LPoint3d &cpos, LVector3d &idir)
{
    // Approximate computation.
    LPoint3d dpos = tpos - ipos;
    LVector3d dvel = tvel - ifvel;
    LVector3d dacc = tacc - ifacc;
    double k0 = dpos.length_squared();
    double k1 = 2 * dpos.dot(dvel);
    double k2 = dvel.length_squared() - POW2(idvelp) + dpos.dot(dacc);
    if (!solve_quad_minpos_s(k2, k1, k0, itime)) {
        return false;
    }

    // Accurate computation.
    if (itime[0] < finetime) {
        double k3 = dvel.dot(dacc) - idvelp * idaccp;
        double k4 = 0.25 * (dacc.length_squared() - POW2(idaccp));
        int niter = 0;
        LVecBase2d it = itime;
        // Fix-point with higher-order terms lumped into k0.
        double dit = itime[0] * 1e3;
        double ditp = itime[0] * 2e3; // to detect divergence
        while (dit > epstime && dit < ditp && niter < maxiter) {
            ++niter;
            double itp = it[0];
            ditp = dit;
            double k0u = k0 + POW3(it[0]) * (k3 + k4 * it[0]);
            if (!solve_quad_minpos_s(k2, k1, k0u, it)) {
                dit = ditp + 1.0; // for the check after loop
                break;
            }
            dit = fabs(it[0] - itp);
        }
        if (dit > ditp) { // diverged
            it = itime;
        }
        //print ("--intercept-time  itime0=%.3f[s]  niter=%d  dctime=%.3f[s]"
               //% (itime[0], niter, (itime[0] - it[0])))
        itime = it;
    }

    double itimehsq = 0.5 * POW2(itime[0]);
    cpos = tpos + tvel * itime[0] + tacc * itimehsq;
    LVector3d dcipos = cpos - ipos;
    idir = ((dcipos - ifvel * itime[0] - ifacc * itimehsq) /
            (idvelp * itime[0] + idaccp * itimehsq));
    idir = unitv(idir);

    return true;
}

LVector4f texture_frame (int texsplit, int frind)
{
    double dcoord = 1.0 / texsplit;
    double uind = frind % texsplit;
    double vind = frind / texsplit;
    double uoff = uind * dcoord;
    double voff = 1.0 - (vind + 1) * dcoord;
    LVector4f frame(uoff, voff, dcoord, dcoord);
    return frame;
}

LVector3f vrot (const LVector3f &e1, const LVector3f &e2,
                double rad, double ang)
{
    return e1 * (rad * cos(ang)) + e2 * (rad * sin(ang));
}

void add_tri (
    GeomVertexWriter *gvwvertex, GeomVertexWriter *gvwcolor,
    GeomVertexWriter *gvwtexcoord, GeomVertexWriter *gvwnormal,
    const P3f &p1, const V3f &n1, const V4f &c1, const V2f &t1,
    const P3f &p2, const V3f &n2, const V4f &c2, const V2f &t2,
    const P3f &p3, const V3f &n3, const V4f &c3, const V2f &t3)
{
    gvwvertex->add_data3(p1);
    gvwcolor->add_data4(c1);
    gvwtexcoord->add_data2(t1);
    gvwnormal->add_data3(n1);

    gvwvertex->add_data3(p2);
    gvwcolor->add_data4(c2);
    gvwtexcoord->add_data2(t2);
    gvwnormal->add_data3(n2);

    gvwvertex->add_data3(p3);
    gvwcolor->add_data4(c3);
    gvwtexcoord->add_data2(t3);
    gvwnormal->add_data3(n3);
}

#ifdef _MSC_VER
double fmax (double a, double b)
{
    return a < b ? b : a;
}
#endif

double torad (double a)
{
    return a * (M_PI / 180.0);
}

double todeg (double a)
{
    return a * (180.0 / M_PI);
}

double stime ()
{
    return double(clock()) / CLOCKS_PER_SEC;
}

INITIALIZE_TYPE_HANDLE(RandomBase)

// According to random.WichmannHill from Python standard library.
RandomBase::RandomBase (int seed)
{
    long long a = seed;
    if (a < 0) {
        a = time(NULL);
    }
    a *= 256;

    _x = a % 30268; a /= 30268;
    _y = a % 30306; a /= 30306;
    _z = a % 30322; a /= 30322;
    _x += 1;
    _y += 1;
    _z += 1;
}

double RandomBase::random ()
{
    _x = (171 * _x) % 30269;
    _y = (172 * _y) % 30307;
    _z = (170 * _z) % 30323;

    double r = _x / 30269.0 + _y / 30307.0 + _z / 30323.0;
    r -= int(r);
    return r;
}

#define DEFINE_RAND(_global_rb, _random_generator_initialized, \
                    reset_random, randunit, \
                    uniform0, uniform1, uniform2, \
                    randrange1, randrange2, \
                    randvec) \
\
static RandomBase *_global_rb = NULL; \
static bool _random_generator_initialized = false; /* for nicer assertion */ \
\
void reset_random (int seed) \
{ \
    delete _global_rb; \
    _global_rb = new RandomBase(seed); \
    _random_generator_initialized = true; \
} \
\
double randunit () \
{ \
    nassertr(_random_generator_initialized, 0.0); \
    double r = _global_rb->random(); \
    return r; \
} \
\
double uniform0 () \
{ \
    double r = randunit(); \
    return r; \
} \
\
double uniform1 (double a) \
{ \
    double r = a * randunit(); \
    return r; \
} \
\
double uniform2 (double a, double b) \
{ \
    double r = a + (b - a) * randunit(); \
    return r; \
} \
\
int randrange1 (int a) \
{ \
    int r = int(a * randunit()); \
    return r; \
} \
\
int randrange2 (int a, int b) \
{ \
    int r = int(a + (b - a) * randunit()); \
    return r; \
} \
\
LVector3f randvec (double minh, double maxh, double minp, double maxp) \
{ \
    double h = uniform2(minh, maxh); \
    double minz = sin(torad(minp)); \
    double maxz = sin(torad(maxp)); \
    double z = uniform2(minz, maxz); \
    double p = todeg(asin(z)); \
    LVector3f vec = hprtovec(LVector3f(h, p, 0.0)); \
    return vec; \
}

DEFINE_RAND(_global_rb, _random_generator_initialized,
            reset_random, randunit,
            uniform0, uniform1, uniform2,
            randrange1, randrange2,
            randvec)
DEFINE_RAND(_fx_global_rb, _fx_random_generator_initialized,
            fx_reset_random, fx_randunit,
            fx_uniform0, fx_uniform1, fx_uniform2,
            fx_randrange1, fx_randrange2,
            fx_randvec)

INITIALIZE_TYPE_HANDLE(NumRandom)

NumRandom::NumRandom (int seed)
: _rb(seed)
{}

double NumRandom::randunit ()
{
    double r = _rb.random();
    return r;
}

double NumRandom::uniform (double a, double b)
{
    double r = a + (b - a) * randunit();
    return r;
}

int NumRandom::randrange (int a)
{
    int r = int(a * randunit());
    return r;
}

int NumRandom::randrange (int a, int b)
{
    int r = int(a + (b - a) * randunit());
    return r;
}

LVector3f NumRandom::randvec (double minh, double maxh,
                              double minp, double maxp)
{
    double h = uniform2(minh, maxh);
    double minz = sin(torad(minp));
    double maxz = sin(torad(maxp));
    double z = uniform2(minz, maxz);
    double p = todeg(asin(z));
    LVector3f vec = hprtovec(LVector3f(h, p, 0.0));
    return vec;
}

INITIALIZE_TYPE_HANDLE(HaltonDistrib)

HaltonDistrib::HaltonDistrib (int startind)
: _index(startind)
{
}

double HaltonDistrib::_get_r (int base, int i)
{
    double r = 0.0;
    double f = 1.0 / base;
    while (i > 0) {
        r += f * (i % base);
        i /= base;
        f /= base;
    }
    return r;
}

double HaltonDistrib::next1 ()
{
    double r1 = _get_r(2, _index);
    _index += 1;
    return r1;
}

LVecBase2 HaltonDistrib::next2 ()
{
    double r1 = _get_r(2, _index);
    double r2 = _get_r(3, _index);
    _index += 1;
    return LVecBase2(r1, r2);
}

LVecBase3 HaltonDistrib::next3 ()
{
    double r1 = _get_r(2, _index);
    double r2 = _get_r(3, _index);
    double r3 = _get_r(5, _index);
    _index += 1;
    return LVecBase3(r1, r2, r3);
}

MiniConfigParser::MiniConfigParser (const std::string &fpath)
: _path(fpath)
{
    _parse_file(fpath, _section_map);
}

MiniConfigParser::~MiniConfigParser ()
{
}

static std::string trim (const std::string &s)
{
    const char *ws = " \t\r\n";
    int pos1 = s.find_first_not_of(ws);
    if (pos1 == std::string::npos) {
        return "";
    }
    int pos2 = s.find_last_not_of(ws);
    if (pos2 == std::string::npos) {
        pos2 = s.length() - 1;
    }
    return s.substr(pos1, pos2 - pos1 + 1);
}

void MiniConfigParser::_parse_file (
    const std::string &fpath,
    std::map<std::string, std::map<std::string, std::string> > &section_map)
{
    std::ifstream ifs(fpath.c_str());
    std::string line;
    const char *cmcs = ";#";
    int lno = 0;
    int pos;
    std::string current_section;
    while (std::getline(ifs, line)) {
        ++lno;
        // Strip comment.
        pos = line.find_first_of(cmcs);
        if (pos != std::string::npos) {
            line.erase(pos);
        }
        // Skip empty line.
        line = trim(line);
        if (line.length() == 0) {
            continue;
        }
        if (line[0] == '[') {
            // Parse section.
            if (line[line.length() - 1] != ']') {
                fprintf(stderr,
                    "Invalid section syntax in file '%s' line %d.\n",
                    fpath.c_str(), lno);
                std::exit(1);
            }
            std::string section = trim(line.substr(1, line.length() - 2));
            if (section.length() == 0) {
                fprintf(stderr,
                    "Empty section name in file '%s' line %d.\n",
                    fpath.c_str(), lno);
                std::exit(1);
            }
            if (section_map.find(section) != section_map.end()) {
                fprintf(stderr,
                    "Repeated section name '%s' in file '%s' line %d.\n",
                    section.c_str(), fpath.c_str(), lno);
                std::exit(1);
            }
            section_map[section] = std::map<std::string, std::string>();
            current_section = section;
        } else {
            // Parse option.
            if (current_section.length() == 0) {
                fprintf(stderr,
                    "Option before section in file '%s' line %d.\n",
                    fpath.c_str(), lno);
                std::exit(1);
            }
            pos = line.find("=");
            if (pos == std::string::npos) {
                fprintf(stderr,
                    "Invalid option syntax in file '%s' line %d.\n",
                    fpath.c_str(), lno);
                std::exit(1);
            }
            std::string option = trim(line.substr(0, pos));
            std::string value = trim(line.substr(pos + 1));
            if (option.length() == 0) {
                fprintf(stderr,
                    "Empty option name in file '%s' line %d.\n",
                    fpath.c_str(), lno);
                std::exit(1);
            }
            std::map<std::string, std::string> &option_map = section_map[current_section];
            if (option_map.find(option) != option_map.end()) {
                fprintf(stderr,
                    "Repeated option name '%s' in file '%s' line %d.\n",
                    option.c_str(), fpath.c_str(), lno);
                std::exit(1);
            }
            option_map[option] = value;
        }
    }
}

std::string MiniConfigParser::file_path () const
{
    return _path;
}

bool MiniConfigParser::has_section (const std::string &section) const
{
    bool exists = false;
    std::map<std::string, std::map<std::string, std::string> >::const_iterator
        option_map_it = _section_map.find(section);
    if (option_map_it != _section_map.end()) {
        exists = true;
    }
    return exists;
}

bool MiniConfigParser::has_option (const std::string &section, const std::string &option) const
{
    bool exists = false;
    std::map<std::string, std::map<std::string, std::string> >::const_iterator
        option_map_it = _section_map.find(section);
    if (option_map_it != _section_map.end()) {
        const std::map<std::string, std::string> &option_map = option_map_it->second;
        std::map<std::string, std::string>::const_iterator
            value_it = option_map.find(option);
        if (value_it != option_map.end()) {
            exists = true;
        }
    }
    return exists;
}

std::vector<std::string> MiniConfigParser::sections () const
{
    std::vector<std::string> keys;
    for (std::map<std::string, std::map<std::string, std::string> >::const_iterator
        it = _section_map.begin(); it != _section_map.end(); ++it) {
        keys.push_back(it->first);
    }
    return keys;
}

std::vector<std::string> MiniConfigParser::options (const std::string &section) const
{
    std::vector<std::string> keys;
    std::map<std::string, std::map<std::string, std::string> >::const_iterator
        option_map_it = _section_map.find(section);
    if (option_map_it != _section_map.end()) {
        const std::map<std::string, std::string> &option_map = option_map_it->second;
        for (std::map<std::string, std::string>::const_iterator
            it = option_map.begin(); it != option_map.end(); ++it) {
            keys.push_back(it->first);
        }
    } else {
        fprintf(stderr,
            "Missing section '%s' in file '%s'.\n",
            section.c_str(), _path.c_str());
        std::exit(1);
    }
    return keys;
}

void MiniConfigParser::_get_string (
    const std::string &section, const std::string &option, bool mustexist,
    std::string &value, bool &exists) const
{
    exists = false;
    std::map<std::string, std::map<std::string, std::string> >::const_iterator
        option_map_it = _section_map.find(section);
    if (option_map_it != _section_map.end()) {
        const std::map<std::string, std::string> &option_map = option_map_it->second;
        std::map<std::string, std::string>::const_iterator
            value_it = option_map.find(option);
        if (value_it != option_map.end()) {
            value = value_it->second;
            exists = true;
        } else if (mustexist) {
            fprintf(stderr,
                "Missing option '%s' in section '%s' in file '%s'.\n",
                option.c_str(), section.c_str(), _path.c_str());
            std::exit(1);
        }
    } else if (mustexist) {
        fprintf(stderr,
            "Missing section '%s' in file '%s'.\n",
            section.c_str(), _path.c_str());
        std::exit(1);
    }
}

std::string MiniConfigParser::get_string (const std::string &section,
                                          const std::string &option) const
{
    std::string value; bool exists;
    _get_string(section, option, true, value, exists);
    return value;
}

std::string MiniConfigParser::get_string (const std::string &section,
                                          const std::string &option,
                                          const std::string &defval) const
{
    std::string value; bool exists;
    _get_string(section, option, false, value, exists);
    if (exists) {
        return value;
    } else {
        return defval;
    }
}

int MiniConfigParser::get_int (
    const std::string &section, const std::string &option) const
{
    return _get_int(section, option, NULL);
}

int MiniConfigParser::get_int (
    const std::string &section, const std::string &option,
    int defval) const
{
    return _get_int(section, option, &defval);
}

int MiniConfigParser::_get_int (
    const std::string &section, const std::string &option,
    int *defval) const
{
    bool mustexist = (defval == NULL);
    std::string str_value; bool exists;
    _get_string(section, option, mustexist, str_value, exists);
    if (exists) {
        int value;
        std::istringstream iss(str_value);
        iss >> value;
        if (iss.good() || !iss.eof()) {
            fprintf(stderr,
                "Cannot convert option '%s' value '%s' to integer "
                "in section '%s' in file '%s'.\n",
                option.c_str(), str_value.c_str(), section.c_str(),
                _path.c_str());
            std::exit(1);
        }
        return value;
    } else {
        return *defval;
    }
}

double MiniConfigParser::get_real (
    const std::string &section, const std::string &option) const
{
    return _get_real(section, option, NULL);
}

double MiniConfigParser::get_real (
    const std::string &section, const std::string &option,
    double defval) const
{
    return _get_real(section, option, &defval);
}

double MiniConfigParser::_get_real (
    const std::string &section, const std::string &option,
    double *defval) const
{
    bool mustexist = (defval == NULL);
    std::string str_value; bool exists;
    _get_string(section, option, mustexist, str_value, exists);
    if (exists) {
        double value;
        std::istringstream iss(str_value);
        iss >> value;
        if (iss.good() || !iss.eof()) {
            fprintf(stderr,
                "Cannot convert option '%s' value '%s' to real "
                "in section '%s' in file '%s'.\n",
                option.c_str(), str_value.c_str(), section.c_str(),
                _path.c_str());
            std::exit(1);
        }
        return value;
    } else {
        return *defval;
    }
}

std::vector<int> dec_lst_int (ENC_LST_INT enc_lst)
{
    std::vector<int> lst(enc_lst.size());
    for (int i = 0; i < lst.size(); ++i) {
        lst[i] = enc_lst[i];
    }
    return lst;
}

std::vector<bool> dec_lst_bool (ENC_LST_BOOL enc_lst)
{
    std::vector<bool> lst(enc_lst.size());
    for (int i = 0; i < lst.size(); ++i) {
        lst[i] = (enc_lst[i] == 0 ? false : true);
    }
    return lst;
}

#include <sstream>
std::vector<std::string> dec_lst_string (ENC_LST_STRING enc_lst)
{
    std::vector<std::string> lst;
    std::istringstream iss(enc_lst);
    std::string el;
    while (std::getline(iss, el, '\x04')) {
        lst.push_back(el);
    }
    return lst;
}

