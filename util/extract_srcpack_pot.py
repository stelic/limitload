#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
import ast
import os
import subprocess
import sys


_gettext_calls = {
    "_": "",
    "p_": "1c,2",
    "n_": "1,2",
    "pn_": "1c,2,3",
}


def main ():

    ap = ArgumentParser()
    ap.add_argument("campaign_directory", action="store")
    ap.add_argument("pot_file", action="store")
    opts = ap.parse_args()

    dir_path = opts.campaign_directory
    pot_path = opts.pot_file
    
    try:
        subprocess.call(["xgettext",  "--version"], stdout=subprocess.PIPE)
    except Exception, e:
        error("Cannot execute command '%s'." % "xgettext", exc=e)

    cntl_path = os.path.join(dir_path, "__init__.py")
    cntl_tree = get_parse_tree(cntl_path)
    cntl_select_node = get_function_node(cntl_tree, "select_next_mission")
    if cntl_select_node is not None:
        mission_paths = collect_campaign_mission_paths(dir_path, cntl_select_node)
    else:
        mission_paths = collect_directory_mission_paths(dir_path)

    baseopts = ["--no-wrap", "--force-po", "-o", "-"]
    kwopts = ["-k%s:%s" % x for x in sorted(_gettext_calls.items())]
    #trcmntopts = ["-c%s:" % x for x in sorted(["translators", "scene"])]
    # ...can have only one comment keyword!
    trcmntopts = ["-cSCENE:"]
    #print "xgettext options: %s" % " ".join(baseopts + kwopts + trcmntopts)
    p = subprocess.Popen(["xgettext"] + baseopts + kwopts + trcmntopts
                                      + [cntl_path] + mission_paths,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pout, perr = p.communicate()
    pret = p.returncode
    if pret != 0:
        error("PO template extraction failed:\n%s" % perr)
    if not pout:
        error("Nothing to extract into the PO template.")
    if perr:
        warning("There were some warnings while extracting the PO template:\n%s"
                % perr)

    encoding = "UTF-8" # fetch from POT?
    pout = pout.decode(encoding)
    pout = pout.replace("\r", "")
    pot_messages = parse_po_messages(pout)
    pot_messages_by_key = dict(((x.msgctxt, x.msgid), x) for x in pot_messages)
    for mpath in mission_paths:
        mtree = get_parse_tree(mpath)
        add_context_comments(mpath, mtree, pot_messages_by_key)
    write_po_messages(pot_messages, pot_path, encoding)


def message (msg):

    sys.stdout.write("%s\n" % msg)


def warning (msg):

    sys.stderr.write("[warning] %s\n" % msg)


def error (msg, code=1, exc=None):

    sys.stderr.write("[error] %s\n" % msg)
    if exc is not None:
        errfmt = str(exc)
        sys.stderr.write("[error] Reason:\n%s\n" % errfmt)
    exit(code)


def get_parse_tree (pypath):

    try:
        pysource = open(pypath).read()
    except Exception, e:
        error("Cannot read file '%s'." % pypath, exc=e)
    try:
        pytree = ast.parse(pysource, pypath)
    except Exception, e:
        error("Cannot parse Python file '%s'." % pypath, exc=e)
    return pytree


def get_function_node (topnd, fname):

    fnode = None
    for nd in ast.iter_child_nodes(topnd): # only at top level
        if isinstance(nd, ast.FunctionDef) and nd.name == fname:
            fnode = nd
            # Don't break, can be redefined later.
    return fnode


def collect_campaign_mission_paths (parpath, topnd):

    # NOTE: Must preserve order of appearance, depth first.
    mpaths = []
    for nd in ast.iter_child_nodes(topnd):
        if isinstance(nd, ast.Return) and isinstance(nd.value, ast.Str):
            mname = nd.value.s
            mpath = os.path.join(parpath, mname + ".py")
            mpath = mpath.replace("\\", "/")
            mpaths1 = [mpath]
        else:
            mpaths1 = collect_campaign_mission_paths(parpath, nd)
        for mpath in mpaths1:
            if mpath not in mpaths:
                if not os.path.isfile(mpath):
                    warning("Expected mission file '%s' does not exist." % mpath)
                else:
                    mpaths.append(mpath)
    return mpaths


def collect_directory_mission_paths (dirpath):

    mpaths = []
    for item in os.listdir(dirpath):
        itempath = os.path.join(dirpath, item)
        if os.path.isfile(itempath) and itempath.endswith(".py"):
            mpaths.append(itempath)
    mpaths.sort()
    return mpaths


# Very raw and lossy parsing of PO messages, sufficient for the purpose.
# Only PO content as output by Gettext tools expected.
class POMsg (object):

    def __init__ (self, lines, baselno=1):

        self.translator_comment_lines = []
        self.extracted_comment_lines = []
        self.source_comment_lines = []
        self.flag_comment_lines = []
        self.previous_field_lines = []
        self.field_lines = []
        self.lineno = None

        for i, line in enumerate(lines):
            if line.startswith("#."):
                self.extracted_comment_lines.append(line[2:].lstrip())
            elif line.startswith("#:"):
                self.source_comment_lines.append(line[2:].lstrip())
            elif line.startswith("#,"):
                self.flag_comment_lines.append(line[2:].lstrip())
            elif line.startswith("#|"):
                self.previous_field_lines.append(line[2:].lstrip())
            elif line.startswith("#"):
                self.translator_comment_lines.append(line[1:].lstrip())
            else:
                if self.lineno is None:
                    self.lineno = baselno + i
                self.field_lines.append(line.strip())

        self.source_references = sum([[t.split(":", 1) for t in l.split()]
                                     for l in self.source_comment_lines], [])
        self.source_references = [(fp.replace("\\", "/"), fl)
                                  for fp, fl in self.source_references]

        in_context = None
        self.msgctxt = None
        self.msgid = None
        for line in self.field_lines:
            s = extract_c_string(line)
            if line.startswith("msgctxt "):
                self.msgctxt = s
                in_context = "msgctxt"
            elif line.startswith("msgid "):
                self.msgid = s
                in_context = "msgid"
            elif line.startswith("\""):
                if in_context == "msgctxt":
                    self.msgcxt += s
                elif in_context == "msgid":
                    self.msgid += s
            elif line:
                in_context = None


    def to_string (self):

        lines = []
        lines += ["# " + l for l in self.translator_comment_lines]
        lines += ["#. " + l for l in self.extracted_comment_lines]
        lines += ["#: " + l for l in self.source_comment_lines]
        lines += ["#, " + l for l in self.flag_comment_lines]
        lines += ["#| " + l for l in self.previous_field_lines]
        lines += [""  + l for l in self.field_lines]
        return "\n".join(lines) + "\n"


def extract_c_string (line):

    p0 = line.find("\"")
    p1 = line.rfind("\"")
    if 0 <= p0 < p1:
        s = line[p0 + 1:p1]
        s = s.replace("\\\"", "\"")
        s = s.replace("\\n", "\n")
        s = s.replace("\\t", "\t")
        return s
    else:
        return None


def parse_po_messages (postr):

    lines = postr.split("\n")
    nlines = len(lines)
    messages = []
    i = 0
    while i < nlines:
        lines1 = []
        baselno = i + 1
        while i < nlines and lines[i]:
            lines1.append(lines[i])
            i += 1
        if lines1:
            messages.append(POMsg(lines1, baselno))
            lines1 = []
        while i < nlines and not lines[i]:
            i += 1
    return messages


def write_po_messages (pomsgs, popath, encoding):

    cnt = "\n".join(m.to_string() for m in pomsgs)
    fh = open(popath, "w")
    fh.write(cnt.encode(encoding))
    fh.close()


def add_context_comments (path, topnd, msgbykey, treectxt=[]):

    gtxspec = None
    if isinstance(topnd, ast.Call) and isinstance(topnd.func, ast.Name):
        call = topnd
        callname = call.func.id
        gtxspec = _gettext_calls.get(callname)
        if gtxspec is not None:
            msgctxt, msgid = get_call_msg_key(call, gtxspec)
            msg = msgbykey.get((msgctxt, msgid))
            if msg is not None:
                cmnt = None
                def mc (expctxt):
                    return match_tree_context(treectxt, expctxt)
                if mc(("convfunc", "dialog", "speech", "line")):
                    if len(msg.source_references) <= 3: # or else too generic
                        convfunc = treectxt[-4][1]
                        speaker, ischoice = treectxt[-2][1]
                        if ischoice:
                            cmnt = ("dialog: name=%s; speaker=%s; choice;"
                                    % (convfunc, speaker))
                        else:
                            cmnt = ("dialog: name=%s; speaker=%s;"
                                    % (convfunc, speaker))
                elif mc(("speech", "line")):
                    if len(msg.source_references) <= 3: # or else too generic
                        speaker, ischoice = treectxt[-2][1]
                        if ischoice:
                            cmnt = ("dialog: speaker=%s; choice;" % (speaker))
                        else:
                            cmnt = ("dialog: speaker=%s;" % (speaker))
                if cmnt:
                    #print "======cmnt {%s}" % cmnt
                    #print "======msgkey ctxt={%s} id={%s}" % (msgctxt, msgid)
                    if cmnt not in msg.extracted_comment_lines:
                        msg.extracted_comment_lines.append(cmnt)
            else:
                warning("Message at %s:%d not extracted." % (path, call.lineno))
    if gtxspec is None:
        for nd in ast.iter_child_nodes(topnd):
            cfield = None
            if isinstance(nd, ast.FunctionDef):
                if nd.name.startswith("conv") or nd.name.endswith("conv"):
                    cfield = "convfunc"
                    cval = nd.name
            elif isinstance(nd, ast.Call):
                call = nd
                if isinstance(call.func, ast.Name):
                    callname = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    callname = call.func.attr
                else:
                    callname = None
                if callname == "Dialog":
                    cfield = "dialog"
                    cval = None
                elif callname == "Speech":
                    cfield = "speech"
                    a = get_call_arg(call, 0, "speaker", ast.Str)
                    speaker = a.s if a else "(unknown)"
                    a = get_call_arg(call, 1, "line")
                    ischoice = isinstance(a, (ast.List, ast.Tuple))
                    cval = (speaker, ischoice)
                elif callname == "Line":
                    cfield = "line"
                    cval = None
            if cfield is not None:
                treectxt1 = treectxt + [(cfield, cval)]
            else:
                treectxt1 = treectxt
            add_context_comments(path, nd, msgbykey, treectxt1)


def match_tree_context (treectxt, expctxt):

    i = 0
    lentc = len(treectxt)
    lenec = len(expctxt)
    while i < lenec and i < lentc:
        if treectxt[-(i + 1)][0] != expctxt[-(i + 1)]:
            break
        i += 1
    return i == lenec


def get_call_arg (callnode, pos, name=None, typ=None):

    tval = None
    for kw in callnode.keywords:
        if kw.arg == name:
            tval = kw.value
    if tval is None:
        if pos < len(callnode.args):
            tval = callnode.args[pos]
    if tval is not None and (not typ or isinstance(tval, typ)):
        val = tval
    else:
        val = None
    return val


def get_call_msg_key (callnode, gtxspec):

    if not gtxspec:
        gtxspec = "1"
    posctxt = None
    posid = None
    for el in gtxspec.split(","):
        if el.endswith("c"):
            if posctxt is None:
                posctxt = int(el[:-1]) - 1
        else:
            if posid is None:
                posid = int(el) - 1

    # Must take into account that either argument may not be a string,
    # in which case the complete key should be reported as empty.
    cancel = False

    argctxt = get_call_arg(callnode, posctxt) if posctxt is not None else None
    if argctxt is not None:
        if isinstance(argctxt, ast.Str):
            msgctxt = argctxt.s
        else:
            cancel = True
    else:
        msgctxt = None

    argid = get_call_arg(callnode, posid) if posid is not None else None
    if argid is not None and isinstance(argid, ast.Str):
        msgid = argid.s
    else:
        cancel = True

    if cancel:
        msgid = None
        msgctxt = None

    return msgctxt, msgid


if __name__ == "__main__":
    main()

