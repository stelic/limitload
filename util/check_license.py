#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
import glob
import os
import re
import sys


def main ():

    ap = ArgumentParser()
    ap.add_argument("paths", nargs="*",
        help="The file paths for which to print the licensing information.")
    arg = ap.parse_args()

    lic_specs = parse_spec_file("LICENSE.resources")

    if arg.paths:
        print_licensing_info(lic_specs, arg.paths)
    else:
        check_licensing_coverage(lic_specs, dir_paths=[
            "audio",
            "fonts",
            "images",
            "models",
        ])


def report (msg):

    sys.stdout.write("%s\n" % msg)


def check_licensing_coverage (lic_specs, dir_paths):

    file_paths = collect_file_paths(dir_paths)
    not_covered_file_paths = []
    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            not_covered_file_paths.append(file_path)
    if not_covered_file_paths:
        report("Files not covered by licensing:\n"
               "%s"
               % "\n".join("  %s" % p for p in not_covered_file_paths))


def print_licensing_info (lic_specs, paths):

    file_paths = collect_file_paths(paths)

    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            report("File '%s' not covered by licensing." % file_path)


def find_spec_for_file (file_path, lic_specs):

    ref_lic_spec = None
    for lic_spec in lic_specs:
        if file_path in lic_spec.file_paths:
            ref_lic_spec = lic_spec
            break
    return ref_lic_spec


def collect_file_paths (paths):

    file_paths = []
    for path in paths:
        if os.path.isdir(path):
            for root, dir_names, file_names in os.walk(path):
                for file_name in file_names:
                    file_path = os.path.join(root, file_name)
                    if not is_file_ignored(file_path):
                        file_paths.append(file_path)
        elif os.path.isfile(path):
            if not is_file_ignored(path):
                file_paths.append(path)
        else:
            raise StandardError("File '%s' does not exist." % path)
    file_paths.sort()
    return file_paths


_ignored_by_file_name = set([
    "makefile",
])

def is_file_ignored (file_path):

    file_name = os.path.basename(file_path)
    if file_name in _ignored_by_file_name:
        return True
    return False


def parse_spec_file (file_path):

    lines = open(file_path).readlines()

    def finalize_item (item, lno):
        try:
            item.validate()
        except LicSpecError as e:
            raise StandardError(
                "Bad specification item at %s:%d: %s"
                % (file_path, lno, str(e)))
        item.expand_glob()

    lic_specs = []
    last_lic_spec_lno = None
    last_lic_spec = None
    for i, line in enumerate(lines):
        lno = i + 1
        pos = line.find("#")
        if pos >= 0:
            line = line[:pos]
        line = line.strip()
        if not line:
            continue
        lst = line.split(":", 2)
        if len(lst) != 2:
            raise StandardError(
                "Missing colon in specification line at %s:%d."
                % (file_path, lno))
        key, value = [el.strip() for el in lst]
        if key == "file":
            if last_lic_spec is not None:
                finalize_item(last_lic_spec, last_lic_spec_lno)
            # Start new item.
            last_lic_spec_lno = lno
            last_lic_spec = LicSpecItem()
            lic_specs.append(last_lic_spec)
            last_lic_spec.file_path_glob = value
        elif key == "copyright":
            last_lic_spec.copyright_list = simplify(value)
        elif key == "author":
            last_lic_spec.author_list = simplify(value)
        elif key == "license":
            last_lic_spec.license_list = simplify(value)
        else:
            raise StandardError(
                "Unknown specification line type '%s' at %s:%d."
                % (key, file_path, lno))
    if last_lic_spec is not None:
        finalize_item(last_lic_spec, last_lic_spec_lno)

    return lic_specs


_simplify_whitespace_rx = re.compile("[ \t]+")

def simplify (s):

    s = s.strip()
    s = _simplify_whitespace_rx.sub(s, " ")
    return s


class LicSpecItem (object):

    def __init__ (self, file_path_glob=None, copyright_list=None,
                  author_list=None, license_list=None):

        self.file_path_glob = file_path_glob
        self.copyright_list = copyright_list
        self.author_list = author_list
        self.license_list = license_list

        self.file_paths = None


    def validate (self):

        if self.file_path_glob is None:
            raise LicSpecError("File path glob not set.")
        if self.copyright_list is None:
            raise LicSpecError("Copyright list not set.")
        if self.author_list is None:
            pass
        if self.license_list is None:
            raise LicSpecError("License list not set.")


    def expand_glob (self):

        self.file_paths = set()
        for path in glob.glob(self.file_path_glob):
            if not os.path.isfile(path):
                raise StandardError(
                    "Path '%s' obtained from glob '%s' is not a file."
                    % (path, self.file_path_glob))
            self.file_paths.add(path)


class LicSpecError (Exception):

    pass


if __name__ == "__main__":
    main()
