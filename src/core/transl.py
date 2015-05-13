# -*- coding: UTF-8 -*-

import codecs
from ConfigParser import SafeConfigParser
import gettext
import os

from src import PACKAGE_NAME
from src import get_base_game_root, join_path, encode_full_path


def d_ (domain, text):

    if domain is not None:
        gtf = domain.ugettext
        trans = gtf(text)
    else:
        trans = text
    return trans


def dp_ (domain, context, text):

    if domain is not None:
        gtf = domain.ugettext
        trans = gtf("%s\x04%s" % (context, text))
        if "\x04" in trans:
            trans = text
    else:
        trans = text
    return trans


def dn_ (domain, singular, plural, num):

    if domain is not None:
        gtf = domain.ungettext
        trans = gtf(singular, plural, num)
    else:
        trans = (singular if n == 1 else plural)
    return trans


def dpn_ (domain, context, singular, plural, num):

    if domain is not None:
        gtf = domain.ungettext
        trans = gtf("%s\x04%s" % (context, text), plural, num)
        if "\x04" in trans:
            trans = text
    else:
        trans = (singular if n == 1 else plural)
    return trans


class _TrDomain (object):

    def __init__ (self, domainname, localedir):

        self._domainname = domainname
        self._localedir = localedir
        self.reload()


    def reload (self):

        domainname = self._domainname
        localedir = self._localedir

        if domainname:
            try:
                domain = gettext.translation(domainname,
                                             encode_full_path(localedir))
            except IOError:
                domain = None
        else:
            domain = None

        self._domain = domain


    def _ (self, text):
        return d_(self._domain, text)

    def p_ (self, context, text):
        return dp_(self._domain, context, text)

    def n_ (self, singular, plural, num):
        return dn_(self._domain, singular, plural, num)

    def pn_ (self, context, singular, plural, num):
        return dn_(self._domain, context, singular, plural, num)


_tr_domains = {}

def make_tr_calls (domainname, localedir):

    ckey = (domainname, localedir)
    td = _tr_domains.get(ckey)
    if td is None:
        td = _TrDomain(domainname, localedir)
        _tr_domains[ckey] = td

    return td._, td.p_, td.n_, td.pn_


def _make_tr_calls_srcpack (pack_type, os_init_path):

    pack_name = os.path.basename(os.path.dirname(os_init_path))

    pack_root = os.path.dirname(os_init_path)
    pack_depth = 3
    for i in range(pack_depth):
        pack_root = os.path.dirname(pack_root)

    domainname = "%s-%s" % (PACKAGE_NAME, pack_name)
    localedir = join_path(pack_root, "language", "mo")
    return make_tr_calls(domainname, localedir)


def make_tr_calls_campaign (os_init_path):

    return _make_tr_calls_srcpack("campaigns", os_init_path)


def make_tr_calls_skirmish (os_init_path):

    return _make_tr_calls_srcpack("skirmish", os_init_path)


def make_tr_calls_test (os_init_path):

    return _make_tr_calls_srcpack("test", os_init_path)


_orig_env_lang = []

def set_tr_language (lang):

    if not _orig_env_lang:
        _orig_env_lang.append(os.environ.get("LANGUAGE"))

    if lang != "system":
        os.environ["LANGUAGE"] = lang
    else:
        if _orig_env_lang[0] is not None:
            os.environ["LANGUAGE"] = _orig_env_lang[0]
        elif "LANGUAGE" in os.environ:
            os.environ.pop("LANGUAGE")

    for td in _tr_domains.values():
        td.reload()


_core_domainname = "limload"
_core_localedir = join_path(get_base_game_root(), "language", "mo")
_, p_, n_, pn_ = make_tr_calls(_core_domainname, _core_localedir)
__all__ = ["make_tr_calls_campaign", "make_tr_calls_skirmish",
           "make_tr_calls_test",
           "_", "p_", "n_", "pn_"]

