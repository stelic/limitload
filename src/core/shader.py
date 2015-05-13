# -*- coding: UTF-8 -*-

from math import pi, sqrt, exp, sin, cos

from pandac.PandaModules import Shader, Vec3, Vec4

from src import GLSL_PROLOGUE, GLSL_VERSION
from src.core.misc import SimpleProps
from src.core.misc import debug


_shader_cache = {}

def make_shader (ambln=None, dirlns=[], pntlns=[],
                 fogn=None, fogsbl=(), camn=None,
                 uvscrn=None, uvoffscn=None, pntobrn=None, obrthr=0.0,
                 color=True, normal=False, glow=False, gloss=False,
                 modcol=False, selfalpha=False,
                 glowfacn=None, glowaddn=None, glowzerodist=None,
                 sunposn=None, sunbcoln=None, sunstr=0.0, sunopq=1.0,
                 shadowrefn=False, shadowdirlin=None, shadowblendn=None,
                 shadowpush=0.0, shadowblur=None,
                 showas=None, getargs=False):

    if not dirlns and not pntlns:
        normal = False
        gloss = False
    if not fogn:
        fogsbl = ()

    glow_orig = glow
    if isinstance(glow, Vec4):
        glow = tuple(glow)
    elif not glow:
        glowfacn = None
        glowaddn = None
        glowzerodist = None

    if not dirlns or not shadowrefn:
        shadowrefn = None
        shadowdirlin = None
        shadowblendn = None
        shadowpush = 0.0
        shadowblur = None

    shdkey = (ambln, tuple(sorted(dirlns)), tuple(sorted(pntlns)),
              fogn, tuple(fogsbl), camn,
              uvscrn, uvoffscn, pntobrn, obrthr, color, normal, glow, gloss,
              modcol, selfalpha, glowfacn, glowaddn,
              sunposn, sunbcoln, sunstr, sunopq,
              shadowrefn, shadowdirlin, shadowblendn, shadowpush, shadowblur)
    ret = _shader_cache.get(shdkey)
    if ret is not None:
        shader, kwargs = ret
        if getargs:
            return shader, kwargs
        else:
            return shader

    if not camn and (fogn or gloss or glowzerodist):
        raise StandardError(
            "Shader input for camera must be present if "
            "fog or gloss is activated.")
    if not (sunposn and sunbcoln) and fogsbl:
        raise StandardError(
            "Shader input for sun position and sun color must be present if "
            "fog-sun blending is activated.")

    vshstr = GLSL_PROLOGUE

    need_texcoord = (color or normal or
                     (glow and not isinstance(glow, tuple)) or gloss)

    if ambln:
        vshstr += make_shdfunc_amblit()
    if dirlns and not (gloss or normal or shadowrefn):
        vshstr += make_shdfunc_dirlit(gloss=gloss)
    if fogn:
        if fogsbl:
            vshstr += make_shdfunc_sunbln(sunblend=fogsbl)
        vshstr += make_shdfunc_fogbln(sunblend=fogsbl)
    if shadowrefn:
        vshstr += make_shdfunc_shdcrd(push=shadowpush)

    if ambln:
        vshstr += """
uniform AmbLight %(ambln)s;
""" % locals()
    if not (gloss or normal or shadowrefn):
        for dirln in dirlns:
            vshstr += """
uniform DirLight %(dirln)s;
""" % locals()
    if ambln or dirlns or pntlns or glow:
        vshstr += """
out vec4 l_lit;
"""
    if pntlns or pntobrn or gloss:
        vshstr += """
out vec4 l_vertpos;
"""
    if dirlns or pntlns:
        vshstr += """
in vec3 p3d_Normal;
"""
    if normal:
        vshstr += """
in vec3 p3d_Tangent;
"""
    if pntlns or gloss or normal or shadowrefn:
        vshstr += """
out vec3 l_vertnrm;
"""
    if normal:
        vshstr += """
out vec3 l_verttng;
"""
    if modcol:
        vshstr += """
in vec4 p3d_Color;
out vec4 l_color;
"""
    if fogn:
        vshstr += """
uniform mat4 p3d_ModelMatrix;
uniform vec4 wspos_%(camn)s;
uniform FogSpec %(fogn)s;
""" % locals()
        if fogsbl:
            vshstr += """
uniform vec4 wspos_%(sunposn)s;
uniform SunBlendSpec %(sunbcoln)s;
""" % locals()
        vshstr += """
out vec4 l_fog;
""" % locals()
    # FIXME: Passing glowfac through vertex shader to fragment shader
    # because, if sent directly to fragment shader, Cg won't compile it.
    # FIXME: Check again with GLSL.
    if glowfacn:
        vshstr += """
uniform float %(glowfacn)s;
out float l_%(glowfacn)s;
""" % locals()
    if glowaddn:
        vshstr += """
uniform float %(glowaddn)s;
out float l_%(glowaddn)s;
""" % locals()
    if glowzerodist:
        vshstr += """
uniform vec4 vspos_%(camn)s;
out float l_glwfac;
""" % locals()
    if shadowrefn:
        vshstr += """
uniform mat4 trans_model_to_clip_of_%(shadowrefn)s;
uniform int %(shadowdirlin)s;
uniform float %(shadowblendn)s;
out vec4 l_shdcoord;
flat out int l_shddirli;
""" % locals()
    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
"""
    if pntlns or pntobrn or gloss or glowzerodist:
        vshstr += """
uniform mat4 p3d_ModelViewMatrix;
"""
    if dirlns or pntlns or gloss or normal or shadowrefn:
        vshstr += """
uniform mat3 p3d_NormalMatrix;
"""
    if need_texcoord:
        vshstr += """
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;
"""
    vshstr += """
in vec4 p3d_Vertex;

void main ()
{
"""
    if ambln or dirlns or pntlns or glow:
        vshstr += """
    l_lit = vec4(0.0, 0.0, 0.0, 0.0);
"""
    if dirlns or pntlns:
        vshstr += """
    vec3 normal = normalize(p3d_NormalMatrix * p3d_Normal);
"""
        if normal:
            vshstr += """
    vec3 tangent = normalize(p3d_NormalMatrix * p3d_Tangent);
"""
    if ambln:
        vshstr += """
    amblit(%(ambln)s, 1.0, l_lit);
""" % locals()
    if not (gloss or normal or shadowrefn):
        for dirln in dirlns:
            vshstr += """
    dirlit(%(dirln)s, normal, 1.0, l_lit);
""" % locals()
    if pntlns or pntobrn or gloss:
        vshstr += """
    l_vertpos = p3d_ModelViewMatrix * p3d_Vertex;
"""
    if pntlns or gloss or normal or shadowrefn:
        vshstr += """
    l_vertnrm = normal;
"""
    if normal:
        vshstr += """
    l_verttng = tangent;
"""
    if fogn:
        vshstr += """
    vec4 pw = p3d_ModelMatrix * p3d_Vertex;
    l_fog = vec4(0.0, 0.0, 0.0, 0.0);
"""
        if fogsbl:
            vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw,
           wspos_%(sunposn)s, %(sunbcoln)s.ambient,
           l_fog);
""" % locals()
        else:
            vshstr += """
    fogbln(%(fogn)s, wspos_%(camn)s, pw, l_fog);
""" % locals()
    vshstr += """
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
"""
    if need_texcoord:
        vshstr += """
    l_texcoord0 = p3d_MultiTexCoord0;
"""
    if modcol:
        vshstr += """
    l_color = p3d_Color;
""" % locals()
    if glowfacn:
        vshstr += """
    l_%(glowfacn)s = %(glowfacn)s;
""" % locals()
    if glowaddn:
        vshstr += """
    l_%(glowaddn)s = %(glowaddn)s;
""" % locals()
    if glowzerodist:
        vshstr += """
    float4 vertpos = p3d_ModelViewMatrix * p3d_Vertex;
    float cdist = length(vspos_%(camn)s.xyz - vertpos.xyz);
    l_glwfac = 1.0 - clamp(cdist / %(glowzerodist)f, 0.0, 1.0);
""" % locals()
    if shadowrefn:
        vshstr += """
    l_shdcoord = shdcrd(trans_model_to_clip_of_%(shadowrefn)s, p3d_Vertex,
                        %(shadowblendn)s);
    l_shddirli = %(shadowdirlin)s;
""" % locals()
    vshstr += """
}
"""

    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
    odeclstr, ocolorn, osunvisn = ret[:3]
    if base.with_bloom:
        obloomn = ret[3]
    if dirlns and (gloss or normal or shadowrefn):
        fshstr += make_shdfunc_dirlit(gloss=gloss)
    if pntlns:
        fshstr += make_shdfunc_pntlit(gloss=gloss)
    if fogn:
        fshstr += make_shdfunc_fogapl()
    if pntobrn:
        fshstr += make_shdfunc_pntobr()
    if shadowrefn:
        fshstr += make_shdfunc_shdfac(blur=shadowblur)

    if ambln or dirlns or pntlns or glow:
        fshstr += """
in vec4 l_lit;
""" % locals()
    if pntlns or pntobrn or gloss:
        fshstr += """
in vec4 l_vertpos;
"""
    if pntlns or gloss or normal or shadowrefn:
        fshstr += """
in vec3 l_vertnrm;
"""
    if normal:
        fshstr += """
in vec3 l_verttng;
"""
    if modcol:
        fshstr += """
in vec4 l_color;
""" % locals()
    if gloss or normal or shadowrefn:
        for dirln in dirlns:
            fshstr += """
uniform DirLight %(dirln)s;
""" % locals()
    for pntln in pntlns:
        fshstr += """
uniform PntLight %(pntln)s;
""" % locals()
    if gloss:
        fshstr += """
uniform vec4 vspos_%(camn)s;
""" % locals()
    if fogn:
        fshstr += """
in vec4 l_fog;
""" % locals()
    if pntobrn:
        fshstr += """
uniform PntLight %(pntobrn)s;
""" % locals()
    if glowfacn:
        fshstr += """
in float l_%(glowfacn)s;
""" % locals()
    if glowaddn:
        fshstr += """
in float l_%(glowaddn)s;
""" % locals()
    if glowzerodist:
        fshstr += """
in float l_glwfac;
""" % locals()
    if uvscrn:
        fshstr += """
struct UvScrollSpec {
    vec4 ambient;
};
uniform UvScrollSpec %(uvscrn)s;
""" % locals()
    if uvoffscn:
        fshstr += """
uniform vec4 %(uvoffscn)s;
""" % locals()
    if shadowrefn:
        fshstr += """
in vec4 l_shdcoord;
flat in int l_shddirli;
""" % locals()
    if need_texcoord:
        fshstr += """
in vec2 l_texcoord0;
"""
    tind = 0
    if color:
        tind_col = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_col)d;
""" % locals()
        tind += 1
    if normal:
        tind_nrm = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_nrm)d;
""" % locals()
        tind += 1
    if glow and not isinstance(glow, tuple):
        tind_glw = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_glw)d;
""" % locals()
        tind += 1
    if gloss:
        tind_gls = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_gls)d;
""" % locals()
        tind += 1
    if shadowrefn:
        tind_shd = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_shd)d;
""" % locals()
        tind += 1
    fshstr += """
uniform vec4 p3d_Color;
uniform vec4 p3d_ColorScale;
"""
    fshstr += odeclstr
    fshstr += """
void main ()
{
"""
    if need_texcoord:
        fshstr += """
    vec2 texcoord0 = l_texcoord0;
    vec2 texcoord0b = l_texcoord0;
"""
    if uvscrn and need_texcoord:
        fshstr += """
    texcoord0 += %(uvscrn)s.ambient.xy;
    vec2 uvmax = %(uvscrn)s.ambient.zw;
    if (uvmax.x > 0.0 || uvmax.y > 0.0) { // uv-range [0, uvmax]
        texcoord0 = mod(texcoord0, uvmax);
    } else { // uv-range [0, 1]
        texcoord0 = mod(texcoord0, 1.0);
    }
    texcoord0b = texcoord0;
""" % locals()
    if uvoffscn and need_texcoord:
        fshstr += """
    float uoff = %(uvoffscn)s.x;
    float voff = %(uvoffscn)s.y;
    float usc = %(uvoffscn)s.z;
    float vsc = %(uvoffscn)s.w;
    texcoord0.x = texcoord0.x * usc + uoff;
    texcoord0.y = texcoord0.y * vsc + voff;
""" % locals()
    fshstr += """
    vec4 color;
"""
    if color:
        fshstr += """
    color = texture(p3d_Texture%(tind_col)d, texcoord0);
""" % locals()
    else:
        fshstr += """
    color = vec4(1.0, 1.0, 1.0, 1.0);
"""
    if modcol:
        fshstr += """
    color *= l_color;
"""
    fshstr += """
    color *= p3d_Color * p3d_ColorScale;
"""
    if pntlns or gloss or shadowrefn:
        fshstr += """
    vec3 vertnrm = l_vertnrm;
    vertnrm = normalize(vertnrm); // due to interpolation
"""
    if normal:
        fshstr += """
    vec3 verttng = l_verttng;
    verttng = normalize(verttng); // also
    vec3 vertbnr = cross(verttng, vertnrm);
    vec3 dn = texture(p3d_Texture%(tind_nrm)d, texcoord0b).xyz * 2.0 - 1.0;
    vertnrm = normalize(vertnrm * dn.z + verttng * dn.x + vertbnr * dn.y);
""" % locals()
    if ambln or dirlns or pntlns or glow:
        fshstr += """
    vec4 lit = l_lit;
"""
    if isinstance(glow, tuple):
        gr, gg, gb, ga = glow
        fshstr += """
    vec4 glwm = vec4(%(gr)f, %(gg)f, %(gb)f, %(ga)f);
""" % locals()
    elif glow:
        fshstr += """
    vec4 glwm = texture(p3d_Texture%(tind_glw)d, texcoord0b);
""" % locals()
    if glow:
        if glowfacn:
            fshstr += """
    glwm *= l_%(glowfacn)s;
""" % locals()
        if glowaddn:
            fshstr += """
    color.rgb += glwm.rgb * (glwm.a * l_%(glowaddn)s);
"""  % locals()
        fshstr += """
    lit.rgb += glwm.rgb;
"""
    if gloss:
        fshstr += """
    vec4 gls = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 glsm = texture(p3d_Texture%(tind_gls)d, texcoord0b);
    vec3 cdir = normalize(vspos_%(camn)s.xyz - l_vertpos.xyz);
""" % locals()
    fshstr += """
    float kshd = 1.0;
"""
    if shadowrefn:
        fshstr += """
    float kshdb = shdfac(p3d_Texture%(tind_shd)d, l_shdcoord);
""" % locals()
    for li, dirln in enumerate(dirlns):
        if shadowrefn:
            fshstr += """
    kshd = l_shddirli == %(li)s ? kshdb : 1.0;
""" % locals()
        if gloss:
            fshstr += """
    dirlit(%(dirln)s, vertnrm, kshd, cdir, glsm, gls, lit);
""" % locals()
        elif normal or shadowrefn:
            fshstr += """
    dirlit(%(dirln)s, vertnrm, kshd, lit);
""" % locals()
    for pntln in pntlns:
        if gloss:
            fshstr += """
    pntlit(%(pntln)s, l_vertpos, vertnrm, cdir, glsm, gls, lit);
""" % locals()
        else:
            fshstr += """
    pntlit(%(pntln)s, l_vertpos, vertnrm, lit);
""" % locals()
    if ambln or dirlns or pntlns or glow:
        fshstr += """
    //color.rgb *= clamp(lit.rgb, 0.0, 1.0);
    color.rgb *= lit.rgb; // no cutoff
"""
    if gloss:
        fshstr += """
    color.rgb = clamp(color.rgb + gls.rgb, 0.0, 1.0);
    //color = clamp(color + gls, 0.0, 1.0); // opaque reflection
"""
    if pntobrn:
        fshstr += """
    float br = 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;
    if (br > %(obrthr)s) {
        vec4 obr = vec4(1.0, 1.0, 1.0, 0.0);
        pntobr(%(pntobrn)s, l_vertpos, obr);
        color.rgb *= obr.rgb; // no cutoff
    }
""" % locals()
    if fogn:
        fshstr += """
    fogapl(color, l_fog, color);
""" % locals()
    if selfalpha:
        fshstr += """
    color.rgb *= color.a;
"""
    if glow:
        fshstr += """
    vec4 bloom;
    bloom.a = glwm.a * color.a;
    bloom.rgb = color.rgb * bloom.a;
"""
        if glowzerodist:
            fshstr += """
    bloom *= l_glwfac;
""" % locals()
    else:
        fshstr += """
    vec4 bloom = vec4(0.0, 0.0, 0.0, color.a);
"""
    if base.with_glow_add and not base.with_bloom:
        fshstr += """
    color.rgb += bloom.rgb;
"""
    fshstr += """
    %(ocolorn)s = color;
    %(osunvisn)s = vec4(%(sunstr)f, %(sunstr)f, %(sunstr)f, color.a * %(sunopq)f);
""" % locals()
    if base.with_bloom:
        fshstr += """
    %(obloomn)s = bloom;
""" % locals()
    fshstr += """
}
"""

    if showas:
        printsh((vshstr, fshstr), showas)

    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)

    kwargs = dict( # only the arguments influencing creation
        ambln=ambln, dirlns=dirlns, pntlns=pntlns, fogn=fogn, camn=camn,
        uvscrn=uvscrn, uvoffscn=uvoffscn, pntobrn=pntobrn, obrthr=obrthr,
        normal=normal, gloss=gloss, glow=glow_orig,
        modcol=modcol, selfalpha=selfalpha)

    _shader_cache[shdkey] = (shader, kwargs)

    if getargs:
        return shader, kwargs
    else:
        return shader


def make_frag_outputs (wcolor=False, wsunvis=False, wbloom=False):

    if GLSL_VERSION >= 330:
        declstr = ""
        ret = [""]
        if wcolor:
            ocolorn = "o_color"
            declstr += """
layout(location = 0) out vec4 %(ocolorn)s;
""" % locals()
            ret.append(ocolorn)
        if wsunvis:
            osunvisn = "o_sunvis"
            declstr += """
layout(location = 1) out vec4 %(osunvisn)s;
""" % locals()
            ret.append(osunvisn)
        if wbloom:
            obloomn = "o_bloom"
            declstr += """
layout(location = 2) out vec4 %(obloomn)s;
""" % locals()
            ret.append(obloomn)
        ret[0] = declstr

    else:
        declstr = ""
        ret = [declstr]
        if wcolor:
            ocolorn = "gl_FragData[0]"
            ret.append(ocolorn)
        if wsunvis:
            osunvisn = "gl_FragData[1]"
            ret.append(osunvisn)
        if wbloom:
            obloomn = "gl_FragData[2]"
            ret.append(obloomn)

    return ret


def make_shdfunc_amblit ():

    shstr = """
struct AmbLight {
  vec4 ambient;
};

void amblit (AmbLight lspc, float lfac, inout vec4 lit)
{
    vec4 lcol = lspc.ambient * lfac;
    lit += lcol;
}
"""
    return shstr


def make_shdfunc_dirlit (gloss=False, extname=""):

    shstr = """
struct DirLight {
  vec4 diffuse;
  //vec4 specular;
  vec4 position;
};

void dirlit%s (DirLight lspc, vec3 vnrm, float kshd,
""" % (extname,)
    if gloss:
        shstr += """
             vec3 cdir, vec4 glsm, inout vec4 gls,
"""
    shstr += """
             inout vec4 lit)
{
    vec4 lcol = lspc.diffuse;
    vec3 ldir = lspc.position.xyz;
    lit += lcol * clamp(dot(vnrm, ldir), 0.0, 1.0) * kshd;
"""
    if gloss:
        shstr += """
    //vec4 lspl = lspc.specular;
    vec4 lspl = lcol; // keep same as light color
    vec3 lref = reflect(-ldir, vnrm);
    float lshn = glsm.r * 128;
    gls += lspl * (pow(clamp(dot(lref, cdir), 0.0, 1.0), lshn) * glsm.a) * kshd;
"""
    shstr += """
}
"""
    return shstr


def make_shdfunc_pntlit (gloss=False, extname=""):

    shstr = """
struct PntLight {
  vec4 diffuse;
  //vec4 specular;
  vec4 position;
  float constantAttenuation;
  float linearAttenuation;
  float quadraticAttenuation;
};

void pntlit%s (PntLight lspc, vec4 vpos, vec3 vnrm,
""" % (extname,)
    if gloss:
        shstr += """
             vec3 cdir, vec4 glsm, inout vec4 gls,
"""
    shstr += """
             inout vec4 lit)
{
    vec4 lcol = lspc.diffuse;
    vec4 lpos = lspc.position;
    vec4 latn = vec4(lspc.constantAttenuation, lspc.linearAttenuation,
                     lspc.quadraticAttenuation, 0.0);

    vec3 loff = (lpos - vpos).xyz;
    vec3 ldir = normalize(loff);
    float linc = clamp(dot(vnrm, ldir), 0.0, 1.0);

    float r = length(loff);
    //float latt = 1.0 / (latn.x + (latn.y + latn.z * r) * r);
    float rout = latn.x;
    //float rmid = latn.y;
    //float rpow = log(0.5) / log(rmid / rout);
    float rpow = latn.y;
    float latt = 1.0 - pow(clamp(r / rout, 0.0, 1.0), rpow);

    lit += lcol * (linc * latt);
"""
    if gloss:
        shstr += """
    //vec4 lspl = lspc.specular;
    vec4 lspl = lcol; // keep same as light color
    vec3 lref = reflect(-ldir, vnrm);
    float lshn = glsm.r * 128;
    gls += lspl * (pow(clamp(dot(lref, cdir), 0.0, 1.0), lshn) * glsm.a * latt);
"""
    shstr += """
}
"""
    return shstr


def make_shdfunc_fogbln (sunblend=None):

    shstr = """
struct FogSpec {
    vec4 diffuse;
    vec4 specular;
};

void fogbln (FogSpec fspc, vec4 cpos, vec4 vpos,
"""
    if sunblend:
        shstr += """
             vec4 spos, vec4 scol,
"""
    shstr += """
             inout vec4 sbln)
{
    vec4 fcol = fspc.diffuse;
    vec4 fvis = fspc.specular;
    vec4 bln;
    bln.xyz = fcol.xyz;
    float fm = fvis.x;
    //float dw1 = dot(vpos - cpos, cdir);
    float dw1 = length(vpos.xy - cpos.xy);
    if (fm < 0.0) { // no fog
        bln.a = 0.0;
    } else if (fm < 1.0) { // linear fog
        float fsd = fvis.y;
        float fed = fvis.z;
        bln.a = clamp((dw1 - fsd) / (fed - fsd), 0.0, 1.0);
    } else if (fm < 2.0) { // exponential fog
        float fdf = fvis.y;
        float fep = fvis.z;
        bln.a = 1.0 - clamp(exp(-pow(dw1 * fdf, fep)), 0.0, 1.0);
    }
"""
    if sunblend:
        shstr += """
    sunbln(vpos, spos, cpos, bln, scol, bln);
""" % locals()
    shstr += """
    sbln += bln;
}
"""
    return shstr


def make_shdfunc_fogapl ():

    shstr = """
void fogapl (vec4 ocol, vec4 fbln, out vec4 col)
{
    ocol.xyz = mix(ocol.xyz, fbln.xyz, fbln.a);
    //ocol.a = mix(ocol.a, 0.0, fbln.a);
    ocol.a = mix(ocol.a, 0.0, fbln.a * fbln.a);
    col = ocol;
}
"""
    return shstr


def make_shdfunc_sunbln (sunblend):

    sundexp, zfacexp, maxzwfac = sunblend
    shstr = """
struct SunBlendSpec {
    vec4 ambient;
};

void sunbln (vec4 vpos, vec4 spos, vec4 cpos,
             vec4 vcol, vec4 scol, out vec4 bcol)
{
    vec3 dvc = normalize(vpos.xyz - cpos.xyz);
    vec3 dsc = normalize(spos.xyz - cpos.xyz);
    float sdfac;
    vec3 dvcg = normalize(vpos.xyz - vec3(cpos.xy, 0.0));
    float zfac = pow(1.0 - clamp(dvcg.z, 0.001, 1.0), %(zfacexp)f);
    float wfac = 1.0 - 1.0 / %(maxzwfac)f;
    sdfac = clamp(dot(dvc, dsc), 0.0, 1.0);
    vec3 dvcm = normalize(dvc + (dsc - dvc) * (zfac * wfac * sdfac));
    sdfac = clamp(dot(dvcm, dsc), 0.0, 1.0);
    float sbfac = pow(sdfac, %(sundexp)f);
    bcol.rgb = max(mix(vcol.rgb, scol.rgb, sbfac), vcol.rgb);
    bcol.a = vcol.a;
}
""" % locals()
    return shstr


def make_shdfunc_pntobr ():

    shstr = """
void pntobr (PntLight ospc, vec4 vpos, inout vec4 obr)
{
    vec4 ocol = ospc.diffuse;
    vec4 opos = ospc.position;
    vec4 oatn = vec4(ospc.constantAttenuation, ospc.linearAttenuation,
                     ospc.quadraticAttenuation, 0.0);

    vec3 ooff = (opos - vpos).xyz;
    float r = length(ooff);
    //float oatt = 1.0 / (oatn.x + (oatn.y + oatn.z * r) * r);
    float rout = oatn.x;
    //float rmid = oatn.y;
    //float rpow = log(0.5) / log(rmid / rout);
    float rpow = oatn.y;
    float oatt = 1.0 - pow(clamp(r / rout, 0.0, 1.0), rpow);

    obr += ocol * oatt;
}
"""
    return shstr


SHADOWBLUR = SimpleProps(
    NONE="", # must evaluate to False
    POISSONDISK4="poissondisk",
)


def make_shdfunc_shdcrd (push=0.0):

    shstr = """
vec4 shdcrd (mat4 clipmat, vec4 vpos, float shdbl)
{
    mat4 bm = mat4(0.5, 0.0, 0.0, 0.0,
                   0.0, 0.5, 0.0, 0.0,
                   0.0, 0.0, 0.5, 0.0,
                   0.5, 0.5, 0.5, 1.0);
    vec4 shdcoord = bm * (clipmat * vpos);
    shdcoord /= shdcoord.w;
    shdcoord.z -= %(push)f;
    shdcoord.w = shdbl;
    return shdcoord;
}
""" % locals()
    return shstr


def make_shdfunc_shdfac (blur=None):

    shstr = """
float shdfac (sampler2D shdtex, vec4 shdcoord)
{
    """
    if blur == SHADOWBLUR.POISSONDISK4:
        numsamples = 4
        pdmult = 0.001
        shstr += """
    mat4x2 pd = mat4x2(-0.94201624, -0.39906216,
                        0.94558609, -0.76890725,
                       -0.09418410, -0.92938870,
                        0.34495938,  0.29387760);
"""
    elif not blur:
        numsamples = 0
    else:
        raise StandardError("Unknown shadow averaging type '%s'" % blur)
    shstr += """
    float kshd = 0.0;
"""
    if numsamples > 0:
        shstr += """
    for (int i = 0; i < %(numsamples)d; i++) {
""" % locals()
    # NOTE: Using if (...) because raw texture sampling
    # with wrap mode set to border-color does not work properly.
    # FIXME: Check again with GLSL.
    shstr += """
        if (shdcoord.x < 0.0 || shdcoord.x > 1.0 || shdcoord.y < 0.0 || shdcoord.y > 1.0) {
            kshd += 1.0;
        } else {
"""
    if numsamples > 0:
        shstr += """
            float zf = texture(shdtex, shdcoord.xy + pd[i] * %(pdmult)f).z;
""" % locals()
    else:
        shstr += """
            float zf = texture(shdtex, shdcoord.xy).z;
"""
    shstr += """
            kshd += zf < min(shdcoord.z, 1.0) ? shdcoord.w : 1.0;
        }
"""
    if numsamples > 0:
        avgfac = 1.0 / numsamples
        shstr += """
    }
    kshd *= %(avgfac)f;
""" % locals()
    shstr += """
    return kshd;
}
"""
    return shstr


def make_stores_shader (world, normal=False, glow=False, gloss=False):

    si = world.shdinp
    shader = make_shader(ambln=si.ambln, dirlns=si.dirlns,
                         normal=normal, glow=glow, gloss=gloss,
                         shadowrefn=si.shadowrefn,
                         shadowdirlin=si.shadowdirlin,
                         shadowblendn=si.shadowblendn,
                         camn=(si.camn if gloss else None))
    return shader


_blur_shader_cache = {}

def make_blur_shader (dir, size, numsamples, randrot=False,
                      hfac=1.0, desat=0.0, showas=False):

    shdkey = (dir, size, numsamples, hfac, desat)
    ret = _blur_shader_cache.get(shdkey)
    if ret is not None:
        shader = ret
        return shader

    vshstr = GLSL_PROLOGUE

    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    l_texcoord0 = p3d_MultiTexCoord0;
}
"""
    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True)
    odeclstr, ocolorn = ret

    if desat:
        dfr, dfg, dfb = 0.30, 0.59, 0.11
        fshstr += """
const vec3 desatfac = vec3(%(dfr)f, %(dfg)f, %(dfb)f);
""" % locals()
    fshstr += """
const float pi2 = 6.2832;
"""
    tind = 0
    tind_col = tind
    fshstr += """
uniform sampler2D p3d_Texture%(tind_col)d;
""" % locals()
    tind += 1
    if randrot:
        tind_rrt = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_rrt)d;
""" % locals()
        tind += 1
    fshstr += """
in vec2 l_texcoord0;
"""
    fshstr += odeclstr
    fshstr += """
void main ()
{
    vec4 col = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 col_1;
    float xc, yc, x, y;
    xc = l_texcoord0.x;
    yc = l_texcoord0.y;
"""
    if randrot:
        fshstr += """
    float ra;
    ra = texture(p3d_Texture%(tind_rrt)d, vec2(xc, yc)).x * pi2;
    float sra = sin(ra);
    float cra = cos(ra);
""" % locals()
    eff_hfac = hfac if dir == "u" else 1.0
    #eff_hfac = 1.0
    sampling = _blur_sampling(size, numsamples, eff_hfac)
    for o, c in sampling:
        if dir == "u":
            if randrot:
                fshstr += """
    x = xc + %(o)s * cra;
    y = yc + %(o)s * sra;
""" % locals()
            else:
                fshstr += """
    x = xc + %(o)s;
    y = yc;
""" % locals()
        elif dir == "v":
            if randrot:
                fshstr += """
    x = xc - %(o)s * sra;
    y = yc + %(o)s * cra;
""" % locals()
            else:
                fshstr += """
    x = xc;
    y = yc + %(o)s;
""" % locals()
        elif dir == "uv":
            raise StandardError("Blur direction '%s' not implemented yet." % dir)
        else:
            raise StandardError("Unknown blur direction '%s'." % dir)
        fshstr += """
    col_1 = texture(p3d_Texture%(tind_col)d, vec2(x, y));
""" % locals()
        fshstr += """
    col += col_1 * %(c)s;
""" % locals()
    if desat:
        fshstr += """
    float g = dot(col.rgb, desatfac);
    col = mix(col, vec4(g, g, g, col.a), %(desat)f);
""" % locals()
    fshstr += """
    %(ocolorn)s = col;
""" % locals()
    fshstr += """
}
"""

    if showas:
        printsh((vshstr, fshstr), showas)

    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)

    _blur_shader_cache[shdkey] = shader
    return shader


def _blur_sampling (size, numsamples, hfac):

    coeff = []
    coord = []
    dx = size / (numsamples * 0.5)
    for i in range(numsamples):
        x = (i - (numsamples - 1) * 0.5) * dx
        coord.append(x / hfac)
        c = _blur_distrib(x, size)
        coeff.append(c)
    sum_c = sum(coeff)
    k_n = 1.0 / sum_c
    k_n *= 2 # because there are two blur passes
    for i in range(numsamples):
        coeff[i] *= k_n
    sampling = zip(coord, coeff)
    return sampling


def _blur_distrib (x, size):

    sigma = size * 0.33
    k_1 = 1 / sqrt(2 * pi * sigma**2)
    k_2 = -1 / (2 * sigma**2)
    c = k_1 * exp(k_2 * x**2)
    return c


_desat_shader_cache = {}

def make_desat_shader (avgfac=Vec3(0.30, 0.59, 0.11), desfacn=None,
                       raddesn=None, raddarkn=None,
                       sunblindn=None,
                       sunbrpnum=0, sunberad=0.9,
                       sunbmaxout=5.0, sunboexp=1.0, sunbdexp=2.0,
                       hfac=1.0,
                       showas=False):

    shdkey = (tuple(avgfac), desfacn, raddesn, raddarkn,
              sunblindn,
              sunbrpnum, sunberad,
              sunbmaxout, sunboexp, sunbdexp,
              hfac)
    ret = _desat_shader_cache.get(shdkey)
    if ret is not None:
        shader = ret
        return shader

    ihfac = 1.0 / hfac

    vshstr = GLSL_PROLOGUE

    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    l_texcoord0 = p3d_MultiTexCoord0;
}
"""

    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True)
    odeclstr, ocolorn = ret

    dfr, dfg, dfb = avgfac
    fshstr += """
vec3 desatfac = vec3(%(dfr)f, %(dfg)f, %(dfb)f);
""" % locals()
    fshstr += """
void desat (inout vec4 color, float desfac)
{
    float g = dot(color.rgb, desatfac);
    vec4 color_fd = vec4(g, g, g, color.a);
    color = mix(color, color_fd, desfac);
}
"""
    if raddesn:
        fshstr += """
struct RadDesSpec {
    vec4 ambient;
};

void rdesat (inout vec4 color, RadDesSpec rdesspc, float rad, float ang)
{
    float outrad = rdesspc.ambient.x;
    float ifac0 = rdesspc.ambient.y;
    float ifac1 = rdesspc.ambient.z;
    float ifac = mix(ifac0, ifac1, clamp(rad / outrad, 0.0, 1.0));
    desat(color, ifac);
}
"""
    if raddarkn:
        fshstr += """
struct RadDarkSpec {
  vec4 diffuse;
  vec4 specular;
};

void rdarken (inout vec4 color, RadDarkSpec rdarkspc, float rad, float ang)
{
    vec4 radspc = rdarkspc.diffuse;
    vec4 angspc = rdarkspc.specular;
    float outrad0 = radspc.x;
    float ifac0 = radspc.y;
    float ifac1 = radspc.z;
    float colr = radspc.w;
    float drampl = angspc.x;
    float drfreq = angspc.y;
    float drphase = angspc.z;
    float outrad = outrad0 * (1.0 + drampl * sin(drfreq * ang + drphase));
    float ifac = mix(ifac0, ifac1, clamp(rad / outrad, 0.0, 1.0));
    color.rgb = mix(color.rgb, vec3(colr, 0.0, 0.0), ifac);
}
"""
    if sunblindn:
        fshstr += """
void sunblind (inout vec4 color, vec4 spblspc0, vec4 spblspc1,
               sampler2D vtex, vec2 tc)
{
    vec2 sctc = spblspc0.xy;
    float svrad = spblspc0.z;
    float sstr = spblspc0.w;
    vec3 scol = spblspc1.xyz;
    float outdist = spblspc1.w;
"""
        fshstr += """
    float vstr = texture(vtex, sctc).r;
    vec2 stc;
    //float mintd = length(tc - sctc); float td = 0.0;
"""
        pi2 = pi * 0.5
        pi4 = pi * 0.25
        if isinstance(sunbrpnum, int):
            rptotnum = sunbrpnum
            rpcircnum = 1
        else:
            rptotnum, rpcircnum = sunbrpnum
        # FIXME: Replace this with Poisson disk distribution.
        # rpcircnum will then not be needed anymore.
        if rptotnum > 0:
            off_uv = []
            drad = sunberad / rpcircnum
            totperim = 0.0
            for i in range(rpcircnum):
                rad = drad * (i + 1)
                perim = 2 * rad * pi
                totperim += perim
            rpnums = []
            for i in range(rpcircnum):
                rad = drad * (i + 1)
                perim = 2 * rad * pi
                rpnum = int(rptotnum * (perim / totperim) + 0.5)
                rpnums.append(rpnum)
            while sum(rpnums) > rptotnum:
                for j in reversed(range(rpcircnum)):
                    if rpnums[j] > 0:
                        rpnums[j] -= 1
                        if sum(rpnums) == rptotnum:
                            break
            for i in range(rpcircnum):
                rpnum = rpnums[i]
                if rpnum == 0:
                    continue
                rad = drad * (i + 1)
                dang = 2 * pi / rpnum
                dang0 = (i + 0.5) * dang
                for j in range(rpnum):
                    ang = dang * j + dang0
                    du = cos(ang) * rad * ihfac
                    dv = sin(ang) * rad
                    off_uv.append((du, dv))
            for du, dv in off_uv:
                fshstr += """
    stc = sctc + vec2(%(du)f, %(dv)f) * svrad;
    vstr += texture(vtex, stc).r;
    //td = length(tc - stc); if (mintd > td) { mintd = td; }
""" % locals()
            sumfac = 1.0 / (rptotnum + 1)
            fshstr += """
    vstr *= %(sumfac)f;
""" % locals()
        epsdiv = 1.0 / sunbmaxout
        fshstr += """
    //color.rgb = mix(color.rgb, vec3(1.0, 0.0, 0.0), pow(clamp(1.0 - mintd, 0.0, 1.0), 600));
    vec2 spos = vec2((sctc.x - 0.5) * %(hfac)f, sctc.y - 0.5) * 2;
    float srad = svrad * 2;
    vec2 pos = vec2((tc.x - 0.5) * %(hfac)f, tc.y - 0.5) * 2;
    float cstr = clamp(1.0 - clamp(length(spos) / outdist, 0.0, 1.0), 0.0, 1.0);
    float estr = pow(cstr, 2.0) * pow(sstr, 0.5) * pow(vstr, 0.5);
    vec2 dpos = pos - spos;
    float dist = length(dpos);
    vec3 tcol = color.rgb;
    float ofac = sin(pow(clamp((dist - srad) / (outdist - srad), 0.0, 1.0), 0.75) * %(pi2)f);
    float cfac = tan((estr + 1.0) * %(pi4)f);
    tcol = clamp((tcol - 0.5) * mix(1.0, cfac, ofac) + 0.5, 0.0, 1.0);
    tcol = tcol * (1.0 + mix(0.0, -estr, ofac));
    //color.rgb = tcol;
    float scrdist = 1.0 / (pow(clamp(1.0 - estr, 0.0, 1.0), %(sunboexp)f) + %(epsdiv)f);
    vec3 ecol = mix(scol, vec3(1.0, 1.0, 1.0), estr);
    float dfac = clamp((1.0 - clamp(dist / scrdist, 0.0, 1.0)) * estr, 0.0, 1.0);
    color.rgb = mix(tcol, ecol, pow(dfac, %(sunbdexp)f));
}
""" % locals()

    fshstr += """
uniform sampler2D p3d_Texture0;
in vec2 l_texcoord0;
"""
    if desfacn:
        fshstr += """
uniform float %(desfacn)s;
""" % locals()
    if raddesn:
        fshstr += """
uniform RadDesSpec %(raddesn)s;
""" % locals()
    if raddarkn:
        fshstr += """
uniform RadDarkSpec %(raddarkn)s;
""" % locals()
    if sunblindn:
        sunblind1n, sunblind2n = sunblindn
        fshstr += """
uniform sampler2D p3d_Texture1;
struct SunBlindSpec {
    vec4 ambient;
};
uniform SunBlindSpec %(sunblind1n)s;
uniform SunBlindSpec %(sunblind2n)s;
""" % locals()
    fshstr += odeclstr
    fshstr += """
void main ()
{
    vec4 color;
    color = texture(p3d_Texture0, l_texcoord0);
    //color = textureLod(p3d_Texture0, vec2(l_texcoord0.x, l_texcoord0.y), 3);
"""
    if sunblindn:
        fshstr += """
    // Sun blind.
    sunblind(color, %(sunblind1n)s.ambient, %(sunblind2n)s.ambient,
             p3d_Texture1, l_texcoord0);
""" % locals()
    if raddesn or raddarkn:
        fshstr += """
    vec2 uvcen = l_texcoord0 - 0.5;
    float uvrad = length(uvcen);
    float uvang = atan(uvcen.y, uvcen.x);
""" % locals()
    if raddesn:
        fshstr += """
    // Radially desaturate.
    rdesat(color, %(raddesn)s, uvrad, uvang);
""" % locals()
    if raddarkn:
        fshstr += """
    // Radially darken.
    rdarken(color, %(raddarkn)s, uvrad, uvang);
""" % locals()
    dfovr = ("%(desfacn)s" % locals()) if desfacn else "1.0"
    fshstr += """
    // Overally desaturate.
    desat(color, %(dfovr)s);
""" % locals()
    fshstr += """
    %(ocolorn)s = color;
""" % locals()
    fshstr += """
}
"""

    if showas:
        printsh((vshstr, fshstr), showas)

    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)

    _desat_shader_cache[shdkey] = shader
    return shader


_bloom_shader_cache = {}

def make_bloom_shader (limbrthr=1.0, limbrfac=1.0, visiblen=None,
                       showas=False):

    shdkey = (limbrthr, limbrfac, visiblen)
    ret = _bloom_shader_cache.get(shdkey)
    if ret is not None:
        shader = ret
        return shader

    vshstr = GLSL_PROLOGUE

    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    l_texcoord0 = p3d_MultiTexCoord0;
}
"""

    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True)
    odeclstr, ocolorn = ret

    fshstr += """
uniform sampler2D p3d_Texture0;
uniform sampler2D p3d_Texture1;
in vec2 l_texcoord0;
"""
    if visiblen:
        fshstr += """
uniform bool %(visiblen)s;
""" % locals()
    fshstr += odeclstr
    fshstr += """
void main ()
{
    vec4 color_0 = texture(p3d_Texture0, l_texcoord0);
    vec4 color = color_0;
"""
    if visiblen:
        fshstr += """
    if (%(visiblen)s) {
""" % locals()
    fshstr += """
        vec4 color_1 = texture(p3d_Texture1, l_texcoord0);
        float bfac;
        float br = 0.2126 * color_0.r + 0.7152 * color_0.g + 0.0722 * color_0.b;
        br = clamp(br, 0.0, 1.0);
        if (br > %(limbrthr)s) {
            bfac = mix(1.0, %(limbrfac)s, (br - %(limbrthr)s) / (1.0 - %(limbrthr)s));
        } else {
            bfac = 1.0;
        }
        color += color_1 * bfac;
""" % locals()
    if visiblen:
        fshstr += """
    }
"""
    fshstr += """
    %(ocolorn)s = color;
""" % locals()
    fshstr += """
}
"""

    if showas:
        printsh((vshstr, fshstr), showas)

    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)

    _bloom_shader_cache[shdkey] = shader
    return shader


_text_shader_cache = {}

def make_text_shader (shadow=False, glow=False, showas=None):

    if isinstance(glow, Vec4):
        glow = tuple(glow)
    elif not glow:
        pass

    shdkey = (shadow, glow)
    shader = _text_shader_cache.get(shdkey)
    if shader is not None:
        return shader

    vshstr = GLSL_PROLOGUE

    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;

in vec2 p3d_MultiTexCoord0;
out vec2 l_texcoord0;
"""
    if shadow:
        vshstr += """
in vec4 p3d_Color;
out vec4 l_color;
"""
    vshstr += """
in vec4 p3d_Vertex;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    l_texcoord0 = p3d_MultiTexCoord0;
"""
    if shadow:
        vshstr += """
    l_color = p3d_Color;
"""
    vshstr += """
}
"""

    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True, wsunvis=True, wbloom=base.with_bloom)
    odeclstr, ocolorn, osunvisn = ret[:3]
    if base.with_bloom:
        obloomn = ret[3]

    fshstr += """
in vec2 l_texcoord0;
"""
    if shadow:
        fshstr += """
in vec4 l_color;
"""
    else:
        fshstr += """
uniform vec4 p3d_Color;
"""
    tind = 0
    tind_col = tind
    fshstr += """
uniform sampler2D p3d_Texture%(tind_col)d;
""" % locals()
    tind += 1
    if glow and not isinstance(glow, tuple):
        tind_glw = tind
        fshstr += """
uniform sampler2D p3d_Texture%(tind_glw)d;
""" % locals()
        tind += 1
    fshstr += """
uniform vec4 p3d_ColorScale;
"""
    fshstr += odeclstr
    fshstr += """
void main ()
{
    vec4 color;
    vec4 t_color = texture(p3d_Texture%(tind_col)d, l_texcoord0);
""" % locals()
    if shadow:
        fshstr += """
    color = l_color * t_color.a;
"""
    else:
        fshstr += """
    color = p3d_Color * t_color.a;
"""
    fshstr += """
    color *= p3d_ColorScale;
"""
    if isinstance(glow, tuple):
        gr, gg, gb, ga = glow
        fshstr += """
    vec4 glwm = vec4(%(gr)f, %(gg)f, %(gb)f, %(ga)f);
""" % locals()
    elif glow:
        fshstr += """
    vec4 glwm = texture(p3d_Texture%(tind_glw)d, l_texcoord0);
""" % locals()
    if glow:
        fshstr += """
    //color.rgb *= clamp(glwm.rgb, 0.0, 1.0);
    color.rgb *= glwm.rgb; // no cutoff
"""
    if glow:
        fshstr += """
    vec4 bloom;
    bloom.a = glwm.a * color.a;
    bloom.rgb = color.rgb * bloom.a;
"""
    else:
        fshstr += """
    vec4 bloom = vec4(0.0, 0.0, 0.0, color.a);
"""
    if base.with_glow_add and not base.with_bloom:
        fshstr += """
    color.rgb += bloom.rgb;
"""
    fshstr += """
    %(ocolorn)s = color;
    %(osunvisn)s = vec4(0.0, 0.0, 0.0, 0.0);
""" % locals()
    if base.with_bloom:
        fshstr += """
    %(obloomn)s = bloom;
""" % locals()
    fshstr += """
}
"""

    if showas:
        printsh((vshstr, fshstr), showas)
    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)
    _text_shader_cache[shdkey] = shader
    return shader


_shadow_shader_cache = {}

def make_shadow_shader (showas=False):

    shdkey = ()
    ret = _shadow_shader_cache.get(shdkey)
    if ret is not None:
        shader = ret
        return shader

    vshstr = GLSL_PROLOGUE
    vshstr += """
uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;

out vec4 m_vertpos;

void main ()
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    m_vertpos = gl_Position;
}
"""

    fshstr = GLSL_PROLOGUE

    ret = make_frag_outputs(wcolor=True)
    odeclstr, ocolorn = ret

    fshstr += """
in vec4 m_vertpos;
"""
    fshstr += odeclstr
    fshstr += """
void main ()
{
    float d = (m_vertpos.z / m_vertpos.w) * 0.5 + 0.5;
    %(ocolorn)s = vec4(d, d, d, 1.0);
}
""" % locals()

    if showas:
        printsh((vshstr, fshstr), showas)

    shader = Shader.make(Shader.SLGLSL, vshstr, fshstr)

    _shadow_shader_cache[shdkey] = shader
    return shader


def printsh (shstr, shname):

    if not isinstance(shstr, tuple):
        shstr = (shstr,)

    ls = []
    ls.append(">>>>>>>>>> %s" % shname)
    for k, shstr1 in enumerate(shstr):
        if k >= 1:
            ls.append("==========")
        ls.extend("%4d|  %s" % (i + 1, l)
                  for i, l in enumerate(shstr1.split("\n")))
    ls.append("<<<<<<<<<<")
    debug(0, "\n".join(ls))


