#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
from glob import fnmatch, glob
import os
from StringIO import StringIO
from subprocess import Popen, PIPE
import sys
from tarfile import TarFile, TarInfo
from tarfile import open as open_tarfile
from zipfile import ZipFile, ZIP_DEFLATED

from src import PACKAGE_NAME, PACKAGE_VERSION


def main ():

    ap = ArgumentParser()
    ap.add_argument("build_env")
    ap.add_argument("pkg_dir")
    ap.add_argument("root_dir")
    ap.add_argument("panda_dir")
    ap.add_argument("python_dir")
    arg = ap.parse_args()

    pkg_dir_path = arg.pkg_dir
    if not os.path.isdir(pkg_dir_path):
        os.mkdir(pkg_dir_path)

    build_env = arg.build_env

    pkg_name = "%s-%s" % (PACKAGE_NAME, PACKAGE_VERSION)

    version_data = "%s\n" % PACKAGE_VERSION
    version_filename = "VERSION.txt"

    root_dir_path = arg.root_dir
    panda_dir_path = arg.panda_dir
    python_dir_path = arg.python_dir

    abs_pkg_dir_path = os.path.abspath(pkg_dir_path)
    abs_root_dir_path = os.path.abspath(root_dir_path)
    if abs_pkg_dir_path.startswith(abs_root_dir_path + os.path.sep):
        error("Package parent directory cannot be "
              "inside source root directory.")

    if build_env == "winmsvc":
        pack_zip_winmsvc(pkg_dir_path, pkg_name,
                         root_dir_path, panda_dir_path, python_dir_path,
                         version_data, version_filename)
    elif build_env == "lingcc":
        pack_zip_lingcc(pkg_dir_path, pkg_name,
                        root_dir_path,
                        version_data, version_filename)
    else:
        error("Archive packing not supported for environment '%s'." % build_env)


def report (msg):

    sys.stdout.write("%s\n" % msg)


def error (msg):

    sys.stderr.write("*** %s\n" % msg)
    exit(1)


def unix2dos (text):

    mod_text = text
    mod_text = mod_text.replace("\r", "") # normalize
    mod_text = mod_text.replace("\n", "\r\n")
    return mod_text


def pack_zip_winmsvc (pkg_dir_path, pkg_name,
                      root_dir_path, panda_dir_path, python_dir_path,
                      version_data, version_filename):

    zip_basename = pkg_name + "-windows_x64" + ".zip"
    zip_path = os.path.join(pkg_dir_path, zip_basename)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    zip_file = ZipFile(zip_path, "w",
                       compression=ZIP_DEFLATED, allowZip64=True)

    root_exclude_glob = [
        ".??*",
        "_*",
        "*.ini",
        os.path.join("save", "*"),
        os.path.join("cache", "*"),
        os.path.join("log", "*"),
    ]
    root_unix2dos_glob = [
        "README*.rst",
        "README*.txt",
        "*.ini.default",
    ]
    root_rename = [
        #("foo", "bar"),
    ]
    root_rename.extend(
        (fp, fp.replace(".rst", ".txt")) for fp in
            (glob("*.rst") + glob(os.path.join("doc", "*", "*.rst")))
    )
    zip_add_dir(zip_file, root_dir_path,
                strip_parent=True,
                add_parent=pkg_name,
                exclude_glob=root_exclude_glob,
                unix2dos_glob=root_unix2dos_glob,
                rename=root_rename)

    zip_add_dir(zip_file, panda_dir_path,
                strip_parent=True,
                add_parent=os.path.join(pkg_name, "panda3d"),
                exclude_glob=[os.path.join("python", "*"),
                              os.path.join("util", "build_setup")])

    arc_python_dir = os.path.join(pkg_name, "python")
    zip_add_dir(zip_file, python_dir_path,
                strip_parent=True,
                add_parent=arc_python_dir)

    arc_version_path = os.path.join(pkg_name, version_filename)
    version_data = unix2dos(version_data)
    zip_add_bytes(zip_file, version_data, arc_version_path)

    arc_pth_path = os.path.join(arc_python_dir, "panda.pth")
    pth_data = """
../panda3d
../panda3d/bin
"""
    zip_add_bytes(zip_file, pth_data, arc_pth_path)

    zip_file.close()


def pack_zip_lingcc (pkg_dir_path, pkg_name,
                     root_dir_path,
                     version_data, version_filename):

    zip_basename = pkg_name + "-linux_x64" + ".tar.gz"
    zip_path = os.path.join(pkg_dir_path, zip_basename)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    zip_file = open_tarfile(zip_path, "w:gz", dereference=True)

    lib_exclude_glob = [
        "*/limload/*",
        "*/limload",
        "/dev/*",
        "/sys/*",
        "/proc/*",
        "/run/*",
        "/etc/*",
        "/home/*",
        "*/locale/*",
        "*/gconv/*",
        "*/bin/xrandr",
        "*/libc.so*",
        "*/libdl.so*",
        "*/libGL.so*",
        "*/lib/*/dri/*",
        "*/libdrm.so*", "*/libdrm_*.so*",
        "*fglrx*", "*/libatiadlxx.so*", "*/libatiuki.so*",
    ]
    lib_include_glob = [
        "/etc/Conf*.prc",
    ]
    cmd = ["tracefile", "-e", "-u",
           os.path.join(root_dir_path, "limload"),
           "-s", ":incoming", "-g", "quick_exit=1"]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    ret = proc.communicate()
    if proc.returncode != 0:
        raise StandardError("Failed to run '%s'." % cmd)
    stdout, stderr = ret
    lib_file_paths = set()
    fnm = fnmatch.fnmatch
    for line in stdout.split("\n"):
        file_path = line
        if (file_path and os.path.isfile(file_path) and
            not any(fnm(file_path, p) for p in lib_exclude_glob) or
            any(fnm(file_path, p) for p in lib_include_glob)):
            lib_file_paths.add(file_path)
    lib_file_paths = sorted(lib_file_paths)
    lib_file_manifest_path = os.path.join(pkg_dir_path, "binroot-manifest.out")
    with open(lib_file_manifest_path, "w") as f:
        f.writelines(l + "\n" for l in lib_file_paths)
    for file_path in lib_file_paths:
        arc_path = os.path.join(pkg_name, "binroot",
                                file_path.lstrip(os.path.sep))
        zip_add_file(zip_file, file_path, arc_path)

    root_exclude_glob = [
        ".??*",
        "_*",
        "*.ini",
    ]
    root_rename = [
        #("foo", "bar"),
    ]
    root_rename.extend(
        (fp, fp.replace(".rst", ".txt")) for fp in
            (glob("*.rst") + glob(os.path.join("doc", "*", "*.rst")))
    )
    zip_add_dir(zip_file, root_dir_path,
                strip_parent=True,
                add_parent=pkg_name,
                exclude_glob=root_exclude_glob,
                rename=root_rename)

    arc_version_path = os.path.join(pkg_name, version_filename)
    zip_add_bytes(zip_file, version_data, arc_version_path)

    zip_file.close()


def zip_add_dir (zip_file, dir_path,
                 strip_parent=False, add_parent=None,
                 exclude_glob=(), unix2dos_glob=(), rename=()):

    excm = fnmatch.fnmatch
    dir_path = os.path.normpath(dir_path)
    rename_map = dict(rename)
    for root, dirlist, filelist in os.walk(dir_path):

        # Construct the parent directory for the files in this directory,
        # as they will appear in the archive.
        if strip_parent:
            if root == dir_path:
                arc_root = ""
            elif root.startswith(dir_path + os.path.sep):
                arc_root = root[len(dir_path + os.path.sep):]
            else:
                assert not "reached"
        else:
            arc_root = root
        pos = arc_root.rfind(":")
        if pos >= 0:
            arc_root = arc_root[pos + 1:]
        arc_root = arc_root.lstrip(os.path.sep)
        arc_root_nopref = arc_root
        if add_parent:
            arc_root = os.path.join(add_parent, arc_root)

        # Add files to archive.
        for basename in sorted(filelist):
            file_path = os.path.join(root, basename)
            nopref_arc_path = os.path.join(arc_root_nopref, basename)
            mod_nopref_arc_path = rename_map.get(nopref_arc_path)
            if mod_nopref_arc_path:
                if add_parent:
                    arc_path = os.path.join(add_parent, mod_nopref_arc_path)
                else:
                    arc_path = mod_nopref_arc_path
            elif arc_root:
                arc_path = os.path.join(arc_root, basename)
            else:
                arc_path = basename
            if not any(excm(nopref_arc_path, p) for p in exclude_glob):
                if any(excm(nopref_arc_path, p) for p in unix2dos_glob):
                    file_str = unix2dos(open(file_path, "rb").read())
                    zip_add_bytes(zip_file, file_str, arc_path)
                else:
                    zip_add_file(zip_file, file_path, arc_path)
            else:
                report("skipped: %s" % (file_path,))


def zip_add_file (zip_file, file_path, arc_path):

    if isinstance(zip_file, ZipFile):
        zip_file.write(file_path, arc_path)
    elif isinstance(zip_file, TarFile):
        zip_file.add(file_path, arc_path)
    else:
        raise StandardError("Unknown archive format.")
    cr = zip_get_stats(zip_file, arc_path)
    if cr is not None:
        report("packed: %s -> %s [%.1f%%]" %
               (file_path, arc_path, cr * 100))
    else:
        report("packed: %s -> %s" %
               (file_path, arc_path))


def zip_add_bytes (zip_file, data, arc_path):

    if isinstance(zip_file, ZipFile):
        zip_file.writestr(arc_path, data)
    elif isinstance(zip_file, TarFile):
        sio = StringIO()
        sio.write(data)
        sio.seek(0)
        ti = TarInfo(name=arc_path)
        ti.size = len(sio.buf)
        zip_file.addfile(ti, sio)
    else:
        raise StandardError("Unknown archive format.")
    report("packed: %s [created]" % (arc_path,))


def zip_get_stats (zip_file, arc_path):

    if isinstance(zip_file, ZipFile):
        zi = zip_file.getinfo(arc_path.replace(os.path.sep, "/"))
        if zi.file_size > 0:
            cr = zi.compress_size / float(zi.file_size)
        else:
            cr = 1.0
    elif isinstance(zip_file, TarFile):
        cr = None
    else:
        raise StandardError("Unknown archive format.")
    return cr


if __name__ == "__main__":
    main()

