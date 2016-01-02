#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
import glob
import os
import re
import sys


lic_spec_file_path = "LICENSE.resources"

resource_dir_paths = [
    "audio",
    "fonts",
    "images",
    "models",
]

ignored_by_file_name = set([
    "makefile",
])


def main ():

    ap = ArgumentParser()
    subps = ap.add_subparsers()

    ap_cov = subps.add_parser(
        "coverage",
        help="Check licensing coverage for files. [default]")
    ap_cov.set_defaults(func=run_coverage)
    ap_cov.add_argument("paths", nargs="*",
        help="File paths for which to check coverage.")

    ap_info = subps.add_parser(
        "info",
        help="Show licensing information for files.")
    ap_info.set_defaults(func=run_info)
    ap_info.add_argument("paths", nargs="*",
        help="File paths for which to show licensing information.")

    args = sys.argv[1:]
    if len(args) == 0:
        args.append("coverage")
    options = ap.parse_args(args)
    options.func(options)


def run_coverage (options):

    paths = options.paths
    if len(paths) == 0:
        paths.extend(resource_dir_paths)

    lic_specs = get_lic_specs()

    file_paths = collect_file_paths(paths)

    not_covered_file_paths = []
    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            not_covered_file_paths.append(file_path)
    if not_covered_file_paths:
        report("Files not covered by licensing:\n"
               "%s"
               % "\n".join("  %s" % p for p in not_covered_file_paths))


def run_info (options):

    paths = options.paths
    if len(paths) == 0:
        paths.extend(resource_dir_paths)

    lic_specs = get_lic_specs()

    file_paths = collect_file_paths(paths)

    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is not None:
            pass
        else:
            pass


def report (msg):

    sys.stdout.write("%s\n" % msg)


def find_spec_for_file (file_path, lic_specs):

    ref_lic_spec = None
    for lic_spec in lic_specs:
        if file_path in lic_spec.file_paths:
            ref_lic_spec = lic_spec
            # No break, because last wins in case of duplicates.
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


def is_file_ignored (file_path):

    file_name = os.path.basename(file_path)
    if file_name in ignored_by_file_name:
        return True
    return False


def get_lic_specs ():

    if os.path.isfile(lic_spec_file_path):
        lic_specs = parse_lic_spec_file(lic_spec_file_path)
    else:
        lic_specs = []
    return lic_specs


def parse_lic_spec_file (file_path):

    lines = open(file_path).readlines()

    def finalize_item (item, lno):
        try:
            item.validate()
        except LicSpecError as e:
            raise StandardError(
                "Bad specification item at %s:%d: %s"
                % (file_path, lno, str(e)))
        item.simplify_fields()
        item.expand_glob()

    lic_specs = []
    last_lic_spec_lno = None
    last_lic_spec = None
    last_lic_key = None
    for i, line in enumerate(lines):
        lno = i + 1
        pos = line.find("#")
        if pos >= 0:
            line = line[:pos]
        line = line.rstrip()
        if not line:
            continue

        if not line[0].isspace():
            lst = line.split(":", 2)
            if len(lst) != 2:
                raise StandardError(
                    "Missing colon in specification line at %s:%d."
                    % (file_path, lno))
            new_key = True
            key, value = [el.strip() for el in lst]
            last_lic_key = key
        else:
            if last_lic_key is None:
                raise StandardError(
                    "No specification item started yet at %s:%d."
                    % (file_path, lno))
            new_key = False
            key = last_lic_key
            value = line

        if key == "file":
            if new_key:
                if last_lic_spec is not None:
                    finalize_item(last_lic_spec, last_lic_spec_lno)
                # Start new item.
                last_lic_spec_lno = lno
                last_lic_spec = LicSpecItem()
                lic_specs.append(last_lic_spec)
            last_lic_spec.file_path_glob += " " + value
        elif key == "copyright":
            last_lic_spec.copyright += " " + value
        elif key == "author":
            last_lic_spec.author += " " + value
        elif key == "license":
            last_lic_spec.license += " " + value
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

    def __init__ (self, file_path_glob="", copyright="",
                  author="", license=""):

        self.file_path_glob = file_path_glob
        self.copyright = copyright
        self.author = author
        self.license = license

        self.file_paths = None


    def simplify_fields (self):

        self.file_path_glob = simplify(self.file_path_glob)
        self.copyright = simplify(self.copyright)
        self.author = simplify(self.author)
        self.license = simplify(self.license)


    def validate (self):

        if self.file_path_glob == "":
            raise LicSpecError("File path glob not set.")
        if self.copyright == "":
            pass
        if self.author == "":
            pass
        if self.license == "":
            raise LicSpecError("License list not set.")


    def expand_glob (self):

        self.file_paths = set()
        path_globs = [x.strip() for x in self.file_path_glob.split(",")]
        for path_glob in path_globs:
            for path in glob.glob(path_glob):
                if os.path.isdir(path):
                    for sub_path in collect_file_paths([path]):
                        self.file_paths.add(sub_path)
                else:
                    self.file_paths.add(path)


class LicSpecError (Exception):

    pass


if __name__ == "__main__":
    main()
