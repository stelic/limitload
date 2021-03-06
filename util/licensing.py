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

ignored_by_file_name = frozenset([
    "makefile",
])

recognized_licenses_free = frozenset([
    "public domain",
    "GPL 2", "GPL 3",
    "BSD 3-clause", "BSD 2-clause",
    "CC0", "CC0 1.0",
    "CC-by", "CC-by 2.0", "CC-by 2.5", "CC-by 3.0", "CC-by 4.0",
    "CC-by-SA", "CC-by-SA 2.0", "CC-by-SA 2.5", "CC-by-SA 3.0", "CC-by-SA 4.0",
    "OFL 1.0", "OFL 1.1",
    "LPPL 1.3",
    "custom-free",
])

recognized_licenses_nonfree = frozenset([
    "proprietary",
    "CC-by-NC", "CC-by-NC 2.0", "CC-by-NC 2.5", "CC-by-NC 3.0", "CC-by-NC 4.0",
    "CC-by-ND", "CC-by-ND 2.0", "CC-by-ND 2.5", "CC-by-ND 3.0", "CC-by-ND 4.0",
    "CC-by-NC-ND", "CC-by-NC-ND 2.0", "CC-by-NC-ND 2.5", "CC-by-NC-ND 3.0", "CC-by-NC-ND 4.0",
    "unknown",
])

recognized_licenses_nonfree_minor = frozenset([
    "unknown-minor",
])

recognized_licenses = set()
recognized_licenses.update(recognized_licenses_free)
recognized_licenses.update(recognized_licenses_nonfree)
recognized_licenses.update(recognized_licenses_nonfree_minor)
recognized_licenses = frozenset(recognized_licenses)

license_name_not_covered = "NOT COVERED"


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

    ap_list = subps.add_parser(
        "list",
        help="List licenses for files.")
    ap_list.set_defaults(func=run_list)
    ap_list.add_argument("paths", nargs="*",
        help="File paths for which to list licenses.")
    ap_list_grp_nf = ap_list.add_mutually_exclusive_group()
    ap_list_grp_nf.add_argument(
        "-n", "--non-free",
        action="store_true", default=False,
        help="Only show files with non-free licenses.")
    ap_list_grp_nf.add_argument(
        "-N", "--strict-non-free",
        action="store_true", default=False,
        help="Only show files with non-free licenses, "
             "including those with minor content.")

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
    unrecognized_license_file_paths = []
    any_bad = False
    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            not_covered_file_paths.append(file_path)
            any_bad = True
        else:
            lic_names = [split_with_address(x)[0]
                         for x in comma_sep_string_to_list(lic_spec.license)]
            for lic_name in lic_names:
                if lic_name not in recognized_licenses:
                    unrecognized_license_file_paths.append((file_path, lic_name))
                    any_bad = True
    if not_covered_file_paths:
        report("Files not covered by licensing:\n"
               "%s"
               % "\n".join("  %s" % p for p in not_covered_file_paths))
    if unrecognized_license_file_paths:
        report("Files with unrecognized licenses:\n"
               "%s"
               % "\n".join("  %s: %s" % (p[0], p[1]) for p in unrecognized_license_file_paths))
    if not any_bad:
        report("All files covered by licensing.")


def run_info (options):

    paths = options.paths
    if len(paths) == 0:
        paths.extend(resource_dir_paths)

    lic_specs = get_lic_specs()

    file_paths = collect_file_paths(paths)

    no_lic = LicSpecItem(license=license_name_not_covered)
    file_paths_by_licensing_format = {}
    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            lic_spec = no_lic
        lic_fmt = lic_spec.to_string(exclude_file=True)
        if lic_fmt not in file_paths_by_licensing_format:
            file_paths_by_licensing_format[lic_fmt] = []
        file_paths_by_licensing_format[lic_fmt].append(file_path)

    sorted_items = sorted(file_paths_by_licensing_format.items(),
                          key=lambda x: x[1])
    blocks = []
    for lic_fmt, file_paths in sorted_items:
        file_fmt = "".join(string_list_to_lines("file: ", file_paths))
        blocks.append(file_fmt)
        blocks.append(lic_fmt)
        blocks.append("\n")
    blocks.pop(-1) # last newline
    report("".join(blocks))


def run_list (options):

    paths = options.paths
    if len(paths) == 0:
        paths.extend(resource_dir_paths)

    lic_specs = get_lic_specs()

    file_paths = collect_file_paths(paths)

    no_lic = LicSpecItem(license=license_name_not_covered)
    for file_path in file_paths:
        lic_spec = find_spec_for_file(file_path, lic_specs)
        if lic_spec is None:
            lic_spec = no_lic
        lic_names = [split_with_address(x)[0]
                     for x in comma_sep_string_to_list(lic_spec.license)]
        if options.strict_non_free:
            show = all((x in recognized_licenses_nonfree or
                        x in recognized_licenses_nonfree_minor) for x in lic_names)
        elif options.non_free:
            show = all(x in recognized_licenses_nonfree for x in lic_names)
        else:
            show = True
        if show:
            report("%s: %s" % (file_path, lic_spec.license))


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
    file_paths = map(norm_path_sep, file_paths)
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
                "Bad licensing item at %s:%d: %s"
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
            lst = line.split(":", 1)
            if len(lst) != 2:
                raise StandardError(
                    "Missing colon in licensing field at %s:%d."
                    % (file_path, lno))
            new_key = True
            key, value = [el.strip() for el in lst]
            last_lic_key = key
        else:
            if last_lic_key is None:
                raise StandardError(
                    "No licensing field started yet at %s:%d."
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
                "Unknown licensing field '%s:' at %s:%d."
                % (key, file_path, lno))
    if last_lic_spec is not None:
        finalize_item(last_lic_spec, last_lic_spec_lno)

    return lic_specs


def norm_path_sep (path):

    path = path.replace("\\", "/")
    return path


simplify_whitespace_rx = re.compile(r"[ \t]+")

def simplify (s):

    s = s.strip()
    s = simplify_whitespace_rx.sub(s, " ")
    return s


def comma_sep_string_to_list (s):

    items = [x.strip() for x in s.split(",")]
    items = [x for x in items if x]
    return items


def string_list_to_lines (head, items):

    lines = []
    if len(items) >= 2:
        indent = " " * len(head)
        lines.append(head + items[0] + "," + "\n")
        for file_path in items[1:-1]:
            lines.append(indent + file_path + "," + "\n")
        lines.append(indent + items[-1] + "\n")
    elif len(items) == 1:
        lines.append(head + items[0] + "\n")
    return lines


split_address_rx = re.compile(r"[<\[](.*?)[>\]]")

def split_with_address (s):

    addresses = split_address_rx.findall(s)
    if addresses:
        m = split_address_rx.search(s)
        name = s[:m.start()].strip()
    else:
        name = s.strip()
    return name, addresses


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
            raise LicSpecError("File path not set.")
        if self.copyright == "":
            pass
        if self.author == "":
            pass
        if self.license == "":
            raise LicSpecError("License not set.")


    def expand_glob (self):

        if self.file_paths is not None:
            return
        self.file_paths = set()
        path_globs = comma_sep_string_to_list(self.file_path_glob)
        for path_glob in path_globs:
            for path in glob.glob(path_glob):
                path = norm_path_sep(path)
                if os.path.isdir(path):
                    for sub_path in collect_file_paths([path]):
                        self.file_paths.add(sub_path)
                else:
                    self.file_paths.add(path)


    def to_string (self, exclude_file=False):

        lines = []

        if not exclude_file:
            if self.file_paths is None:
                self.expand_glob()
            file_paths = sorted(self.file_paths)
            lines.extend(string_list_to_lines("file: ", file_paths))

        if True:
            copyrights = comma_sep_string_to_list(self.copyright)
            lines.extend(string_list_to_lines("copyright: ", copyrights))

        if True:
            authors = comma_sep_string_to_list(self.author)
            lines.extend(string_list_to_lines("author: ", authors))

        if True:
            licenses = comma_sep_string_to_list(self.license)
            lines.extend(string_list_to_lines("license: ", licenses))

        return "".join(lines)


class LicSpecError (Exception):

    pass


if __name__ == "__main__":
    main()
