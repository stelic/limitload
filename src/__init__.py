# -*- coding: UTF-8 -*-

import locale
import os
import sys

from pandac.PandaModules import Filename


PACKAGE_NAME = "limload"
PACKAGE_VERSION = "0.20"

USE_COMPILED = True

OUTSIDE_FOV = 55
COCKPIT_FOV = 55
ANIMATION_FOV = 45

MAX_DT = 1.0 / 20

UI_TEXT_ENC = "utf8"

GLSL_VERSION = 130
GLSL_PROLOGUE = """
#version %d
""" % GLSL_VERSION


_path_sep = "/" # of internal paths


def decode_real_path (real_path):

    abs_real_path = os.path.abspath(real_path)
    enc_full_path = Filename.fromOsSpecific(abs_real_path).getFullpath()
    enc = locale.getpreferredencoding()
    full_path = enc_full_path.decode(enc)
    return full_path


def encode_full_path (full_path):

    enc = locale.getpreferredencoding()
    enc_full_path = full_path.encode(enc)
    real_path = Filename(enc_full_path).toOsSpecific()
    return real_path


def join_path (*els):

    raw_path = os.path.join(*els)
    path = raw_path.replace(os.path.sep, _path_sep)
    return path


def split_path (path):

    mod_path = path.replace(os.path.sep, _path_sep)
    els = mod_path.split(_path_sep)
    return els


def _get_game_root ():

    raw_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = decode_real_path(raw_root)
    return root


def _get_user_root (xdg_envar, xdg_pdir, loc_pdir, sdir=()):

    if not isinstance(sdir, tuple):
        sdir = (sdir,)

    if os.name == "posix":
        pdir = os.environ.get(xdg_envar) if xdg_envar else None
        if pdir is None:
            if not isinstance(xdg_pdir, tuple):
                xdg_pdir = (xdg_pdir,)
            pdir = join_path(os.environ.get("HOME"), *xdg_pdir)
        tdir = join_path(pdir, PACKAGE_NAME, *sdir)
    else:
        pdir = _get_game_root()
        if not isinstance(loc_pdir, tuple):
            loc_pdir = (loc_pdir,)
        tdir = join_path(pdir, *(loc_pdir + sdir))

    return tdir


def get_base_game_root ():

    return _get_game_root()


_game_roots = []

def add_game_root (full_root_path):

    _game_roots.insert(0, full_root_path)

    # Add source subdirectories from which modules and subpackages need
    # to be importable directly (without src.subpackage.submodule notation).
    # This is crucial for accessing campaigns, etc. from multiple roots.
    for sub_src_path in ("campaigns", "skirmish", "test"):
        full_src_path = join_path(full_root_path, "src", sub_src_path)
        real_src_path = encode_full_path(full_src_path)
        sys.path.insert(0, real_src_path)
        # TODO: Verify there are no collisions in names of
        # campaigns, skirmishes, or tests.

add_game_root(get_base_game_root())
if os.name == "posix":
    add_game_root(_get_user_root("XDG_DATA_HOME", (".local", "share"), ()))


def _get_data_roots ():

    return _game_roots # must not return a copy


_category_roots = {
    "cache": [_get_user_root("XDG_CACHE_HOME", ".cache", "cache")],
    "config": [_get_user_root("XDG_CONFIG_HOME", ".config", "config")],
    "data": _get_data_roots(),
    "save": [_get_user_root("XDG_DATA_HOME", (".local", "share"), (), "save")],
    "log": [_get_user_root("XDG_DATA_HOME", (".local", "share"), (), "log")],
}
def _get_category_roots (category):

    paths = _category_roots.get(category)
    if paths is None:
        raise StandardError("Unknown data category '%s'." % category)
    return paths


def full_path (category, path):

    cat_roots = _get_category_roots(category)
    for cat_root in cat_roots:
        in_full_path = join_path(cat_root, path)
        os_full_path = encode_full_path(in_full_path)
        if os.path.exists(os_full_path):
            break
    return in_full_path


def real_path (category, path):

    in_full_path = full_path(category, path)
    os_full_path = encode_full_path(in_full_path)
    return os_full_path


def _internal_path_single (cat_root, full_path):

    if cat_root:
        prefix = cat_root + _path_sep
    else:
        prefix = ""
    if full_path.startswith(prefix):
        path = full_path[len(prefix):]
    else:
        path = None
    return path


def internal_path (category, real_path):

    full_path = decode_real_path(real_path)
    cat_roots = _get_category_roots(category)
    for cat_root in cat_roots:
        path = _internal_path_single(cat_root, full_path)
        if path is not None:
            break
    if path is None:
        raise StandardError(
            "Real path '%s' cannot be converted to internal path "
            "in category '%s'." % (real_path, category))
    return path


def path_exists (category, path):

    os_path = real_path(category, path)
    return os.path.exists(os_path)


def path_isfile (category, path):

    os_path = real_path(category, path)
    return os.path.isfile(os_path)


def path_isdir (category, path):

    os_path = real_path(category, path)
    return os.path.isdir(os_path)


def path_dirname (path):

    pos = path.rfind(_path_sep)
    if pos >= 0:
        dirname = path[:pos]
    else:
        dirname = ""
    return dirname


def path_basename (path):

    pos = path.rfind(_path_sep)
    if pos >= 0:
        basename = path[pos + len(_path_sep):]
    else:
        basename = ""
    return basename


def walk_dir_files (category, path):

    cat_roots = _get_category_roots(category)
    filelists_by_root = {}
    for cat_root in cat_roots:
        in_full_path = join_path(cat_root, path)
        os_full_path = encode_full_path(in_full_path)
        if os.path.exists(os_full_path):
            for os_full_root, dirlist, filelist in os.walk(os_full_path):
                in_full_root = decode_real_path(os_full_root)
                in_root = _internal_path_single(cat_root, in_full_root)
                assert in_root is not None
                # Exclude files seen in higher priority roots.
                root_filelist = filelists_by_root.get(in_root)
                if root_filelist is None:
                    root_filelist = set()
                    filelists_by_root[in_root] = root_filelist
                mod_filelist = [] # preserve order
                for item in filelist:
                    if item not in root_filelist:
                        mod_filelist.append(item)
                        root_filelist.add(item)
                if mod_filelist:
                    yield in_root, mod_filelist


def _list_dir (category, path, files=True):

    cat_roots = _get_category_roots(category)
    items = []
    seen_items = set()
    is_wanted_type = os.path.isfile if files else os.path.isdir
    for cat_root in cat_roots:
        in_full_path = join_path(cat_root, path)
        os_full_path = encode_full_path(in_full_path)
        if os.path.exists(os_full_path):
            for os_item in os.listdir(os_full_path):
                os_item_full_path = os.path.join(os_full_path, os_item)
                if is_wanted_type(os_item_full_path):
                    in_item_full_path = decode_real_path(os_item_full_path)
                    in_item_path = _internal_path_single(cat_root,
                                                         in_item_full_path)
                    assert in_item_path is not None
                    if path not in ("", "."):
                        prefix = path + _path_sep
                    else:
                        prefix = ""
                    item = in_item_path[len(prefix):]
                    if item not in seen_items:
                        items.append(item)
                        seen_items.add(item)
    return items


def list_dir_files (category, path):

    return _list_dir(category, path, files=True)


def list_dir_subdirs (category, path):

    return _list_dir(category, path, files=False)


def pycv (py, c):

    return c if USE_COMPILED else py


