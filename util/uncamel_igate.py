#!/usr/bin/env python

import re
import sys


def main ():

    file_paths = sys.argv[1:]

    for file_path in file_paths:
        fh = open(file_path, "r")
        code_str = fh.read()
        fh.close()
        mod_code_str = uncamel_igate(code_str)
        if mod_code_str != code_str:
            fh = open(file_path, "w")
            fh.write(mod_code_str)
            fh.close()


def uncamel_igate (code_str):

    # Fetch camelled method and function identifiers.
    parse_rx = re.compile(r'"([a-zA-Z0-9]+)",\s*\(\s*PyCFunction\s*\)')
    camel_idents = re.findall(parse_rx, code_str)

    mod_code_str = code_str
    for camel_ident in camel_idents:
        repl_rx = re.compile(r'\b%s\b' % camel_ident)
        luscore_ident = camel_to_luscore_ident(camel_ident)
        mod_code_str = repl_rx.sub(luscore_ident, mod_code_str)

    return mod_code_str


def camel_to_luscore_ident (camel_ident):

    segs = []
    pos = 0
    while pos < len(camel_ident):
        if camel_ident[pos].isupper():
            if pos > 0:
                segs.append("_")
            segs.append(camel_ident[pos].lower())
        else:
            segs.append(camel_ident[pos])
        pos += 1
    luscore_ident = "".join(segs)
    return luscore_ident


if __name__ == "__main__":
    main()
