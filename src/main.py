#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
import codecs
from ConfigParser import SafeConfigParser
import locale
from multiprocessing import cpu_count
import os
import re
import sys
import traceback

import pygame
from pandac.PandaModules import loadPrcFileData

from src import PACKAGE_NAME, PACKAGE_VERSION, MAX_DT, UI_TEXT_ENC
from src import path_exists, real_path, full_path, join_path
from src import decode_real_path, encode_full_path
from src import get_base_game_root, add_game_root
from src import list_dir_files, list_dir_subdirs
from src.bconf import PYTHON_CMD
from src.core.basestack import BaseStack
from src.core.game import Game
from src.core.interface import NarrowAspect
from src.core.misc import report, warning, error
from src.core.misc import SimpleProps, AutoProps
from src.core.misc import reset_random
from src.core.misc import fx_reset_random
from src.core.misc import rotate_logs
from src.core.transl import *
from src.core.transl import set_tr_language


def main ():

    locale.setlocale(locale.LC_ALL, "")
    enc = locale.getpreferredencoding()

    # Language setting must be parsed manually here from
    # the default configuration file, because translation
    # call are needed before normal configuration loading.
    lang = "system"
    os_def_game_config_path = real_path("config", "config.ini")
    if os.path.exists(os_def_game_config_path):
        cp = SafeConfigParser()
        fl = codecs.open(os_def_game_config_path, "r", "utf8")
        cp.readfp(fl)
        fl.close()
        if cp.has_option("misc", "language"):
            lang = cp.get("misc", "language")
            lang = lang.replace(" ", "")
    set_tr_language(lang)

    description = p_("game description in command-line help",
        "Limit Load -- an arcade cockpit flight game.")
    ap = ArgumentParser(description=description, add_help=True,
                        prog=PACKAGE_NAME)
    ap.add_argument(
        "-m", "--start-mission",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "PACK:MISSION[:ZONE]"),
        default=None,
        help=p_("command-line option description",
                "Start game directly on the given campaign mission. "
                "The mission starts on the mission menu, or in "
                "the mission zone if given. "
                "If empty campaign pack is given (i.e. just leading semicolon), "
                "the mission is looked for through all known campaign packs; "
                "if more than one mission is found, exits with error. "
                "If empty zone is given (i.e. just trailing semicolon), "
                "the mission starts in the default zone."))
    ap.add_argument(
        "-s", "--start-skirmish",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "PACK:MISSION[:ZONE]"),
        default=None,
        help=p_("command-line option description",
                "Start game directly on the given skirmish mission. "
                "The mission starts with the intro dialogue (if any), "
                "or in the mission zone if given. "
                "If empty skirmish pack is given (i.e. just leading semicolon), "
                "the mission is looked for through all known skirmish packs; "
                "if more than one mission is found, exits with error. "
                "If empty zone is given (i.e. just trailing semicolon), "
                "the mission starts in the default zone."))
    ap.add_argument(
        "-t", "--start-test",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "PACK:MISSION[:ZONE|.LOOP]"),
        default=None,
        help=p_("command-line option description",
                "Start game directly on the given test mission. "
                "The mission starts with the intro dialogue (if any), "
                "or in the mission zone if given. "
                "If empty test pack is given (i.e. just leading semicolon), "
                "the mission is looked for through all known test packs; "
                "if more than one mission is found, exits error. "
                "If empty zone is given (i.e. just trailing semicolon), "
                "the mission starts in the default zone. "
                "Instead of the zone, a loop extension can be given "
                "to request a particular mission loop to execute alone."))
    ap.add_argument(
        "-f", "--fixed-time-step",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "SECONDS"),
        default=None,
        help=p_("command-line option description",
                "Use the given fixed time step for game physics, "
                "instead of variable, rendering-dependent time step. "
                "Note that action will not run in real-time "
                "with fixed time step."))
    ap.add_argument(
        "-r", "--random-seed",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "SEED[:FXSEED]"),
        default=None,
        help=p_("command-line option description",
                "Use the given integer number as random seed, "
                "instead of system-derived seed. "
                "If second seed is given, it is used for randomness "
                "in game effects. "
                "If negative number is given, "
                "system-derived seed is used instead."))
    ap.add_argument(
        "-c", "--config-variant",
        action="store",
        metavar=p_("command-line option argument pattern",
                   "VARIANT"),
        default=None,
        help=p_("command-line option description",
                "Read game configuration from config-VARIANT.ini "
                "instead of from config.ini."))
    ap.add_argument(
        "-g", "--game-context",
        action="append",
        metavar=p_("command-line option argument pattern",
                   "ATTR=VALUE"),
        default=[],
        help=p_("command-line option description",
                "Set a game context attribute. "
                "Value will be converted to first possible type of "
                "integer, float, True/False/None, string. "
                "String type can be forced by prepending and appending "
                "either two dots (e.g. foo=..123..), or single or double "
                "quotes (which may need to be escaped for the shell). "
                "Can be repeated to set multiple attributes."))
    ap.add_argument(
        "-V", "--version",
        action="version",
        version=(p_("game name with release string in command-line help",
                    u"Limit Load %s") % PACKAGE_VERSION))
    options = ap.parse_args()

    # Set game configuration and Panda configuration.
    if options.config_variant:
        config_variant_str = options.config_variant.decode(enc)
        game_config_file = "config-%s.ini" % config_variant_str
    else:
        game_config_file = "config.ini"
    gameconf = GameConf()
    if path_exists("config", game_config_file):
        gameconf.read_from_file(game_config_file)
    elif options.config_variant:
        os_game_config_path = real_path("config", game_config_file)
        error(_("Requested game configuration file '%s' does not exist.") %
              os_game_config_path)
    set_panda_config(options, gameconf)
    set_tr_language(gameconf.misc.language)
    for full_path in reversed(gameconf.path.root_path):
        add_game_root(full_path)

    if sum((opv is not None) for opv in (
        options.start_mission,
        options.start_skirmish,
        options.start_test,
    )) > 1:
        error(_("Only one of campaign, skirmish or test mission "
                "can be started directly."))

    # Set input configuration.
    input_config_file = "input.ini"
    inputconf = InputConf()
    if path_exists("config", input_config_file):
        inputconf.read_from_file(input_config_file)

    def find_mission_packs (pack_type, pack_name, mission_name):
        pack_dir = "src/%s" % pack_type
        found_pnames = []
        for pname in list_dir_subdirs("data", pack_dir):
            pack_subdir = join_path(pack_dir, pname)
            for fname in list_dir_files("data", pack_subdir):
                mname = fname.replace(".py", "")
                if mname == mission_name:
                    found_pnames.append(pname)
                    break
        return found_pnames

    # Parse start mission.
    mission_spec = None
    if options.start_mission:
        start_mission_str = options.start_mission
        mission_lst_str = start_mission_str.split(":")
        if not 2 <= len(mission_lst_str) <= 3:
            error(_("Campaign mission must be requested as PACK:MISSION[:ZONE], "
                    "got '%s' instead.") % start_mission_str)
        if len(mission_lst_str) < 3:
            mission_lst_str.append(None)
        pname, mname, zname = mission_lst_str
        if not pname:
            pnames = find_mission_packs("campaigns", pname, mname)
            if len(pnames) == 0:
                error(_("Mission '%s' does not exist in any campaign pack.") %
                      mname)
            elif len(pnames) >= 2:
                error(_("Mission '%(m)s' exists in more than one campaign pack: "
                        "%(lst)s.") %
                      dict(m=mname, lst=(", ".join(pnames))))
            pname = pnames[0]
        mission_spec = (pname, mname, zname)
        if not path_exists("data", "src/campaigns/%s" % pname):
            error(_("There is no campaign '%s'.") % pname)
        if not path_exists("data", "src/campaigns/%s/%s.py" % (pname, mname)):
            error(_("There is no mission '%(m)s' in campaign '%(c)s'.") %
                  dict(m=mname, c=pname))

    # Parse start skirmish.
    skirmish_spec = None
    if options.start_skirmish:
        start_skirmish_str = options.start_skirmish.decode(enc)
        skirmish_lst_str = start_skirmish_str.split(":")
        if not 2 <= len(skirmish_lst_str) <= 3:
            error(_("Skirmish mission must be requested as PACK:MISSION[:ZONE], "
                    "got '%s' instead.") % start_skirmish_str)
        if len(skirmish_lst_str) < 3:
            skirmish_lst_str.append(None)
        pname, mname, zname = skirmish_lst_str
        if not pname:
            pnames = find_mission_packs("skirmish", pname, mname)
            if len(pnames) == 0:
                error(_("Mission '%s' does not exist in any skirmish pack.") %
                      mname)
            elif len(pnames) >= 2:
                error(_("Mission '%(m)s' exists in more than one skirmish pack: "
                        "%(lst)s.") %
                      dict(m=mname, lst=(", ".join(pnames))))
            pname = pnames[0]
        skirmish_spec = (pname, mname, zname)
        if not path_exists("data", "src/skirmish/%s" % pname):
            error(_("There is no skirmish '%s'.") % pname)
        if not path_exists("data", "src/skirmish/%s/%s.py" % (pname, mname)):
            error(_("There is no mission '%(m)s' in skirmish '%(s)s'.") %
                  dict(m=mname, s=pname))

    # Parse start test.
    test_spec = None
    if options.start_test:
        start_test_str = options.start_test.decode(enc)
        test_lst_str_zone = start_test_str.split(":")
        test_lst_str_loop = start_test_str.split(".")
        if not ((len(test_lst_str_zone) == 2 and len(test_lst_str_loop) == 1) or
                (len(test_lst_str_zone) == 3 and len(test_lst_str_loop) == 1) or
                (len(test_lst_str_zone) == 2 and len(test_lst_str_loop) == 2)):
            error(_("Test mission must be requested as PACK:MISSION[:ZONE|.LOOP], "
                    "got '%s' instead.") % (start_test_str))
        if len(test_lst_str_zone) == 3:
            pname, mname, zname = test_lst_str_zone
            lname = None
        elif len(test_lst_str_loop) == 2:
            pname_mname, lname = test_lst_str_loop
            pname, mname_lname = test_lst_str_zone
            mname = mname_lname.split(".")[0]
            zname = None
        else:
            pname, mname = test_lst_str_zone
            zname, lname = None, None
        if not pname:
            pnames = find_mission_packs("test", pname, mname)
            if len(pnames) == 0:
                error(_("Mission '%s' does not exist in any test pack.") %
                      mname)
            elif len(pnames) >= 2:
                error(_("Mission '%(m)s' exists in more than one test pack: "
                        "%(lst)s.") %
                      dict(m=mname, lst=(", ".join(pnames))))
            pname = pnames[0]
        test_spec = (pname, mname, zname, lname)
        if not path_exists("data", "src/test/%s" % pname):
            error(_("There is no test '%s'.") % pname)
        if not path_exists("data", "src/test/%s/%s.py" % (pname, mname)):
            error(_("There is no mission '%(m)s' in test '%(t)s.") %
                  dict(m=mname, t=pname))

    # Parse fixed time step.
    fixdt = None
    if options.fixed_time_step is not None:
        fixed_time_step_str = options.fixed_time_step.decode(enc)
        fixdt_str = fixed_time_step_str
        try:
            fixdt = float(fixdt_str)
        except ValueError:
            error(_("Time step must be a real number, "
                    "got '%s' instead.") % fixdt_str)
        if not 0.0 < fixdt <= MAX_DT:
            error(_("Time step must be in range (0.0, %(num1).3f], "
                    "got '%(num2).3f' instead.") %
                  dict(num1=MAX_DT, num2=fixdt))

    # Parse random seed.
    randseed = None
    if options.random_seed is not None:
        random_seed_str = options.random_seed.decode(enc)
        rsd_lst_str = random_seed_str
        if not 1 <= len(rsd_lst_str) <= 2:
            error(n_("Exactly one or two random seeds can be given, "
                     "got %(num)d instead ('%(fmt)s').",
                     "Exactly one or two random seeds can be given, "
                     "got %(num)d instead ('%(fmt)s').",
                     len(rsd_lst_str)) %
                  dict(num=len(rsd_lst_str), fmt=random_seed_str))
        rsd_lst = []
        for rsd_str in rsd_lst_str:
            try:
                rsd = int(rsd_str)
            except ValueError:
                error(_("Random seed must be an integer number, "
                        "got '%s' instead.") % rsd_str)
            rsd_lst.append(rsd)
        if len(rsd_lst) == 1:
            randseed = rsd_lst[0]
        else:
            randseed = tuple(rsd_lst)

    # Parse game context.
    game_context = []
    for i in range(len(options.game_context)):
        attr_val_str = options.game_context[i].decode(enc)
        attr_val_lst_str = attr_val_str.split("=", 1)
        if len(attr_val_lst_str) != 2:
            error(_("Equal sign not found in game context attribute '%s'.") %
                  attr_val_str)
        attr, val_str = attr_val_lst_str
        if val_str.startswith("..") and val_str.endswith(".."):
            val = val_str[2:-2]
        elif val_str.startswith("'") and val_str.endswith("'"):
            val = val_str[1:-1]
        elif val_str.startswith("\"") and val_str.endswith("\""):
            val = val_str[1:-1]
        else:
            try:
                val = int(val_str)
            except ValueError:
                try:
                    val = float(val_str)
                except ValueError:
                    if val_str == "True":
                        val = True
                    elif val_str == "False":
                        val = False
                    elif val_str == "None":
                        val = None
                    else:
                        val = val_str
        game_context.append((attr, val))

    report(_("Starting game.")) # also initializes logging

    panda_log_real_path = rotate_logs("panda-log", "txt")
    base = BaseStack(gameconf=gameconf, inputconf=inputconf,
                     fixdt=fixdt, randseed=randseed,
                     pandalog=panda_log_real_path)
    # ...also automatically sets __builtin__.base.

    # Random generator initialization happens after BaseStack is created,
    # to be sure that nothing in BaseStack requests randomness.
    # Random generator will be reinitialized on each World creation.
    if isinstance(randseed, tuple):
        rsd, fxrsd = randseed
    elif randseed is not None:
        rsd = fxrsd = randseed
    else:
        rsd = fxrsd = -1
    reset_random(rsd)
    fx_reset_random(fxrsd)

    # Tool for tuning animations to work on narrowest supported screens.
    NarrowAspect()

    # Setup game context.
    gc = AutoProps()
    if game_context:
        ls = []
        for attr, val in game_context:
            gc[attr] = val
            ls.append("  gc.%s = %s" % (attr, repr(val)))
        report(_("Setting game context:\n%s") % ("\n".join(ls)))
        gc.save_disabled = True
    if mission_spec:
        gc.campaign, gc.mission, gc.zone = mission_spec
        gc.save_disabled = True
    elif skirmish_spec:
        gc.skirmish, gc.mission, gc.zone = skirmish_spec
        gc.save_disabled = True
    elif test_spec:
        gc.test, gc.mission, gc.zone, gc.loop = test_spec
        gc.save_disabled = True

    # Make sure user directories exists.
    if not path_exists("config", "."):
        os.makedirs(real_path("config", "."))
    if not path_exists("save", "."):
        os.makedirs(real_path("save", "."))
    if not path_exists("cache", "."):
        os.makedirs(real_path("cache", "."))

    # Start game in task to assure that at least one engine frame has elapsed.
    def startf (task):
        if task.time == 0.0:
            return task.cont
        game = Game(gc)

    try:
        pygame.init()
        base.taskMgr.add(startf, "startf")
        base.run()
        #import cProfile
        #cProfile.run('base.run()', 'prof.out')
        pygame.quit()
    except:
        pass


class GameConfError (Exception):
    def __init__ (self, message=""):
        self.message = message
    def __str__ (self):
        return self.message.encode(locale.getpreferredencoding())
    def __unicode__ (self):
        return self.message


class GameConf (SimpleProps):

    def __init__ (self):

        self.reset_to_default()


    def reset_to_default (self):

        pset = GameConf._make_parse_from_set

        self.cpu = SimpleProps(
            use_cores=2, _use_cores_p=pset([1, 2, 3], keyw=["auto"]),
        )
        self.video = SimpleProps(
            api="gl", _api_p=pset(["gl", "dx8", "dx9"]),
            resolution="desktop", _resolution_p=GameConf._parse_resolution,
            full_screen=True, _full_screen_p=pset([True, False]),
            multi_sampling_antialiasing=4, _multi_sampling_antialiasing_p=pset([0, 2, 4]),
            anisotropic_filtering=16, _anisotropic_filtering_p=pset([0, 4, 8, 16]),
            preload_textures=2, _preload_textures_p=pset([0, 1, 2]),
            vertical_sync=False, _vertical_sync_p=pset([True, False]),
        )
        self.audio = SimpleProps(
            sound_system="al", _sound_system_p=pset(["none", "al", "fmod"]),
        )
        avail_langs = [item[:-len(".po")]
                       for item in list_dir_files("data", "language/po/limload")
                       if item.endswith(".po")]
        avail_langs.append("system")
        avail_langs.append("en_US")
        if "sr" in avail_langs:
            avail_langs.append("sr@latin") # build-time transliteration
        avail_langs.sort()
        self.misc = SimpleProps(
            language="system", _language_p=pset(avail_langs),
            frame_rate_meter=False, _frame_rate_meter_p=pset([True, False]),
        )
        self.path = SimpleProps(
            root_path=[], _root_path_p=GameConf._parse_full_paths,
        )
        self.debug = SimpleProps(
            output_level=0, _output_level_p=pset([0, 1, 2]),
            panda_output_level="fatal", _panda_output_level_p=pset([
                "fatal", "error", "warning", "info", "debug", "spam"]),
            panda_pstats=False, _panda_pstats_p=pset([True, False]),
            panda_verbose_timer=False, _panda_verbose_timer_p=pset([True, False]),
        )
        self.cheat = SimpleProps(
            _silent=True,
            adamantium_bath=False, _adamantium_bath_p=pset([True, False]),
            flying_dutchman=False, _flying_dutchman_p=pset([True, False]),
            guards_tanksman=False, _guards_tanksman_p=pset([True, False]),
            chernobyl_liquidator=False, _chernobyl_liquidator_p=pset([True, False]),
        )


    @staticmethod
    def _convert_type (field, valstr, valtyp):

        try:
            if valtyp is unicode:
                value = valstr
            elif valtyp is str:
                enc = locale.getpreferredencoding()
                value = valstr.decode(enc)
            elif valtyp is bool:
                if valstr.lower() == "true":
                    value = True
                elif valstr.lower() == "false":
                    value = False
                else:
                    raise ValueError
            else:
                value = valtyp(valstr)
        except ValueError:
            if valtyp is int:
                valtyp_fmt = "int"
            elif valtyp is float:
                valtyp_fmt = "float"
            elif valtyp is bool:
                valtyp_fmt = "bool"
            else:
                raise StandardError("Cannot derive name for type %s." % valtyp)
            raise GameConfError(
                _("Game configuration field '%(fld)s' value '%(val)s' "
                  "cannot be converted to type '%(typ)s'.") %
                dict(fld=field, val=valstr, typ=valtyp_fmt))
        return value


    @staticmethod
    def _format_value (value):

        if isinstance(value, bool):
            if value == True:
                valfmt = "true"
            else:
                valfmt = "false"
        else:
            valfmt = "%s" % value
        return valfmt


    @staticmethod
    def _make_parse_from_set (values, keyw=()):

        valtyp = type(values[0])
        values_str = map(GameConf._format_value, values) + list(keyw)
        valkeyw_fmt = ", ".join(values_str)

        def parsef (field, valstr):
            if valstr not in values_str:
                raise GameConfError(
                    _("Game configuration field '%(fld)s' set to "
                      "inadmissible value '%(val)s' "
                      "(admissible values: %(lst)s).") %
                    dict(fld=field, val=valstr, lst=valkeyw_fmt))
            if valstr in keyw:
                value = valstr
            else:
                value = GameConf._convert_type(field, valstr, valtyp)
            return value

        return parsef


    @staticmethod
    def _parse_full_paths (field, valstr):

        if not valstr:
            return []
        valstr_lst = valstr.split(":")
        full_paths = []
        for os_full_path in valstr_lst:
            os_full_path = os.path.normpath(os_full_path)
            full_path = decode_real_path(os_full_path)
            full_paths.append(full_path)
        return full_paths


    @staticmethod
    def _parse_resolution (field, valstr):

        valstr_desktop = "desktop"
        if valstr == valstr_desktop:
            value = valstr_desktop
        else:
            valstr_lst = valstr.split()
            if len(valstr_lst) != 2:
                raise GameConfError(
                _("Game configuration field '%(fld)s' "
                  "must have value '%(specval)s' "
                  "or width and height in pixels as '<width> <height>', "
                  "got '%(val)s' instead.") %
                dict(fld=field, specval=valstr_desktop, val=valstr))
            width_str, height_str = valstr_lst
            width = GameConf._convert_type(field, width_str, int)
            height = GameConf._convert_type(field, height_str, int)
            if width > 0 and height > 0:
                value = (width, height)
            else:
                value = valstr_desktop
        return value


    def read_from_file (self, path):

        conf_var = {}
        conf_var["base"] = encode_full_path(get_base_game_root())
        real_home_dir_path = os.environ.get("HOME")
        if real_home_dir_path is None:
            real_home_dir_path = conf_var["base"]
        conf_var["home"] = decode_real_path(real_home_dir_path)

        cp = SafeConfigParser()
        os_path = real_path("config", path)
        fl = codecs.open(os_path, "r", "utf8")
        cp.readfp(fl)
        fl.close()

        rp = lambda s: s.replace("-", "_")

        for raw_sec_name in cp.sections():
            sec_name = rp(raw_sec_name)
            section = self.get(sec_name)
            if section is None:
                warning(
                    _("Unknown game configuration section '%s'.") % raw_sec_name)
                continue
            for raw_opt_name in cp.options(sec_name):
                opt_name = rp(raw_opt_name)
                option_defval = section.get(opt_name)
                if option_defval is None:
                    warning(
                        _("Unknown game configuration field '%(fld)s' "
                          "in section '%(sec)s'.") %
                        dict(fld=raw_opt_name, sec=raw_sec_name))
                    continue
                option_parse = section.get("_%s_p" % opt_name)
                raw_val_str = cp.get(raw_sec_name, raw_opt_name, raw=True)
                val_str = self._interp_value(raw_opt_name, raw_val_str, conf_var)
                try:
                    opt_val = option_parse(raw_opt_name, val_str)
                except GameConfError as e:
                    warning(e.message)
                    continue
                section[opt_name] = opt_val


    _interp_rx = re.compile(r"%([\w-]+)%", re.U)

    def _interp_value (self, raw_opt_name, raw_val_str, conf_var):

        val_str = raw_val_str
        val_els = []
        pos = 0
        while True:
            m = GameConf._interp_rx.search(val_str, pos)
            if m is None:
                val_els.append(val_str[pos:])
                break
            val_els.append(val_str[pos:m.start()])
            var_name = m.group(1)
            var_value = conf_var.get(var_name)
            if var_value is not None:
                val_els.append(var_value)
            else:
                warning(
                    _("Game configuration field '%(fld)s' "
                      "contains unknown variable '%(var)s'.") %
                    dict(fld=raw_opt_name, var=var_name))
                val_els.append(val_str[m.start():m.end()])
            pos = m.end()
        val_str = "".join(val_els)
        return val_str


def set_panda_config (options, gameconf):

    gc = gameconf

    bfmt = lambda b: ("#t" if b else "#f")
    ifmt = lambda i: ("%d" % i)

    pc = {}

    if gc.cpu.use_cores == "auto":
        use_cores = min(cpu_count(), 3)
    else:
        use_cores = gc.cpu.use_cores
    pc["threading-model"] = {
        1: "",
        2: "/thread3",
        3: "thread2/thread3",
        }[use_cores]

    pc["load-display"] = {
        "gl": "pandagl",
        "dx8": "pandadx8",
        "dx9": "pandadx9",
        }[gc.video.api]

    pc["fullscreen"] = bfmt(gc.video.full_screen)

    if gc.video.resolution == "desktop":
        resolution = desktop_resolution()
    else:
        resolution = gc.video.resolution
    pc["win-size"] = "%d %d" % resolution

    pc["sync-video"] = bfmt(gc.video.vertical_sync)

    pc["framebuffer-object-multisample"] = ifmt(0)
    pc["framebuffer-multisample"] = bfmt(gc.video.multi_sampling_antialiasing > 0)
    pc["multisamples"] = ifmt(gc.video.multi_sampling_antialiasing)

    pc["texture-anisotropic-degree"] = ifmt(gc.video.anisotropic_filtering)
    pc["textures-power-2"] = "none"
    pc["compressed-textures"] = bfmt(True)
    pc["preload-simple-textures"] = bfmt(True)
    # NOTE: preload-textures does not seem to work.

    pc["audio-library-name"] = {
        "none": "p3fmod_none",
        "al": "p3openal_audio",
        "fmod": "p3fmod_audio",
        }[gc.audio.sound_system]

    pc["show-frame-rate-meter"] = bfmt(gc.misc.frame_rate_meter)

    pc["text-encoding"] = UI_TEXT_ENC

    pc["cursor-hidden"] = bfmt(True)
    pc["notify-level"] = gc.debug.panda_output_level
    #pc["notify-level-glxdisplay"] = "debug"
    #pc["notify-level-display"] = "debug"

    # Disable all caching, it is handled manually.
    pc["model-cache-dir"] = full_path("cache", "panda3d") # for stragglers
    pc["model-cache-models"] = bfmt(False)
    pc["model-cache-textures"] = bfmt(False)
    pc["model-cache-compressed-textures"] = bfmt(False)

    #title = _("Limit Load") # crashes with UnicodeEncodeError
    title = ""
    pc["window-title"] = title
    #pc["icon-filename"] = full_path("data", "src/limload.ico")

    pc["want-pstats"] = bfmt(gc.debug.panda_pstats)
    pc["task-timer-verbose"] = bfmt(gc.debug.panda_verbose_timer)

    pc["gl-debug"] = bfmt(True)

    pcstr = "".join("%s %s\n" % pv for pv in sorted(pc.items()))
    loadPrcFileData("main", pcstr)


def desktop_resolution ():

    # NOTE: In case of multiple monitors, this should return the resolution
    # of the primary monitor, and not some aggregation of all monitors.

    if os.name == "posix":
        from subprocess import Popen, PIPE
        cmd = ["xrandr", "-q"]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        ret = proc.communicate()
        if proc.returncode != 0:
            raise StandardError("Failed to run '%s'." % "xrandr")
        stdout, stderr = ret
        w, h = None, None
        for line in stdout.split("\n"):
            m = re.search(r"(\d+)x(\d+).*\*", line)
            if m is not None:
                w_test, h_test = map(int, m.groups())
                if w is None or w * h < w_test * h_test:
                    w, h = w_test, h_test
        if w is None:
            raise StandardError("Unexpected output from '%s'." % "xrandr")

    elif os.name == "nt":
        import ctypes
        user32 = ctypes.windll.user32
        w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    return w, h


class InputConfError (Exception):
    def __init__ (self, message=""):
        self.message = message
    def __str__ (self):
        return self.message.encode(locale.getpreferredencoding())
    def __unicode__ (self):
        return self.message


class InputConf (object):

    def __init__ (self):

        ret = InputConf._default_bindings()
        self.bindings, self.jsdevs = ret


    @staticmethod
    def _default_bindings ():

        bindings = [
            AutoProps(
                name="pitch",
                desc=p_("input command description",
                        "rotate plane around pitch axis"),
                note=p_("input command note",
                        "Needed when using joystick for rotation."),
                seqs=["axis2"], isaxis=True,
                exponent=2.0, deadzone=0.05, minval=-1.0, maxval=1.0,
                inverted=False),
            AutoProps(
                name="pitch-up",
                desc=p_("input command description",
                        "rotate plane in pitch upwards"),
                note=p_("input command note",
                        "Needed only when using keyboard for rotation, "
                        "which is not recommended."),
                seqs=["arrow_up"]),
            AutoProps(
                name="pitch-down",
                desc=p_("input command description",
                        "rotate plane in pitch downwards"),
                note=p_("input command note",
                        "Needed only when using keyboard for rotation, "
                        "which is not recommended."),
                seqs=["arrow_down"]),
            AutoProps(
                name="roll",
                desc=p_("input command description",
                        "rotate plane around roll axis"),
                note=p_("input command note",
                        "Needed when using joystick for rotation."),
                seqs=["axis1"], isaxis=True,
                exponent=2.0, deadzone=0.05, minval=-1.0, maxval=1.0,
                inverted=False),
            AutoProps(
                name="roll-left",
                desc=p_("input command description",
                        "rotate plane in roll to the left"),
                note=p_("input command note",
                        "Needed only when using keyboard for rotation, "
                        "which is not recommended."),
                seqs=["arrow_left"]),
            AutoProps(
                name="roll-right",
                desc=p_("input command description",
                        "rotate plane in roll to the right"),
                note=p_("input command note",
                        "Needed only when using keyboard for rotation, "
                        "which is not recommended."),
                seqs=["arrow_right"]),
            AutoProps(
                name="throttle",
                desc=p_("input command description",
                        "set engine throttle"),
                note=p_("input command note",
                        "Needed when using a hardware throttle, "
                        "on joystick or standalone."),
                seqs=[], isaxis=True,
                exponent=1.0, deadzone=0.0, minval=-1.0, maxval=1.0,
                inverted=False),
            AutoProps(
                name="throttle-up",
                desc=p_("input command description",
                        "increase engine throttle"),
                note=p_("input command note",
                        "Needed when using keyboard for engine control."),
                seqs=["="]),
            AutoProps(
                name="throttle-down",
                desc=p_("input command description",
                        "decrease engine throttle"),
                note=p_("input command note",
                        "Needed when using keyboard for engine control."),
                seqs=["-"]),
            AutoProps(
                name="air-brake",
                desc=p_("input command description",
                        "deploy or retract air brake"),
                note=p_("input command note",
                        "Use for quick airspeed decreases, such as in "
                        "maneuvering combat or on landing, without or "
                        "in addition to throttle setting."),
                seqs=["b", "joy5"]),
            AutoProps(
                name="landing-gear",
                desc=p_("input command description",
                        "lower or raise landing gear"),
                note=p_("input command note",
                        "Do not forget this when landing."),
                seqs=["g"]),
            AutoProps(
                name="next-waypoint-target",
                desc=p_("input command description",
                        "switch to next waypoint or next target"),
                note=p_("input command note",
                        "Waypoints are switched in the HUD navigation mode, "
                        "and targets in the HUD weapon modes. "
                        "When a target is selected, the selection can be "
                        "cancelled either by holding this input pressed for "
                        "a little while longer or by pressing "
                        "the dedicated target deselection input."),
                seqs=["tab", "joy2"]),
            AutoProps(
                name="deselect-target",
                desc=p_("input command description",
                        "cancel target selection"),
                note=p_("input command note",
                        "This can be useful to recover rotation through "
                        "all HUD modes, and not only through "
                        "weapons with which the target can be attacked."),
                seqs=["z"]),
            AutoProps(
                name="fire-weapon",
                desc=p_("input command description",
                        "fire currently selected weapon"),
                note=p_("input command note",
                        "Guns and rocket pods keep firing while "
                        "the input is pressed."),
                seqs=["space", "joy1"]),
            AutoProps(
                name="next-target-section",
                desc=p_("input command description",
                        "switch to next target section"),
                note=p_("input command note",
                        "Big targets have multiple sections which can be "
                        "acquired."),
                seqs=["s"]),
            AutoProps(
                name="next-weapon",
                desc=p_("input command description",
                        "switch to next weapon or to navigation"),
                note=p_("input command note",
                        "Rotates through all weapon and navigation modes "
                        "when target is not acquired. "
                        "If a target is acquired, rotates only through "
                        "weapons with which the target can be attacked."),
                seqs=["w", "joy4"]),
            AutoProps(
                name="previous-weapon",
                desc=p_("input command description",
                        "switch to previous weapon or to navigation"),
                #note=p_("input command note",
                        #"n/a"),
                seqs=["q"]),
            AutoProps(
                name="radar-on-off",
                desc=p_("input command description",
                        "turn on or off the radar"),
                note=p_("input command note",
                        "Turning the radar off can be used sometimes "
                        "to sneak behind the enemies. "
                        "Passive sensors (such as IRST) keep working."),
                seqs=["alt-r"]),
            AutoProps(
                name="radar-scale-up",
                desc=p_("input command description",
                        "increase the scale on the radar screen"),
                note=p_("input command note",
                        "Higher scales are useful for search and "
                        "engagement beyond visual range."),
                seqs=["shift-r"]),
            AutoProps(
                name="radar-scale-down",
                desc=p_("input command description",
                        "decrease the scale on the radar screen"),
                note=p_("input command note",
                        "Lower scales are useful for close combat."),
                seqs=["r"]),
            AutoProps(
                name="next-mfd-mode",
                desc=p_("input command description",
                        "switch to next MFD mode"),
                note=p_("input command note",
                        "Sometimes the MFD mode will switch automatically "
                        "to support a weapon, and then it cannot be changed "
                        "as long as the weapon is selected."),
                seqs=["m"]),
            AutoProps(
                name="previous-mfd-mode",
                desc=p_("input command description",
                        "switch to previous MFD mode"),
                #note=p_("input command note",
                        #"n/a"),
                seqs=["shift-m"]),
            AutoProps(
                name="fire-decoy",
                desc=p_("input command description",
                        "launch missile decoys"),
                note=p_("input command note",
                        "Launch decoys only when the missile is one-two "
                        "seconds away, or else they may be ineffective."),
                seqs=["d", "joy3"]),
            AutoProps(
                name="cockpit-light-on-off",
                desc=p_("input command description",
                        "turn on or off the instrument panel lights"),
                note=p_("input command note",
                        "Lights will normally be on or off automatically, "
                        "depending on the time of day in the current zone."),
                seqs=["shift-l"]),
            AutoProps(
                name="eject",
                desc=p_("input command description",
                        "eject from the plane"),
                note=p_("input command note",
                        "Use in case of panic."),
                seqs=["control-e"]),
            AutoProps(
                name="view-lock-on-off",
                desc=p_("input command description",
                        "enable or disable visual target tracking"),
                note=p_("input command note",
                        "Useful to quickly switch sights between "
                        "the target and the HUD and instruments, "
                        "which is crucial in maneuvering combat."),
                seqs=["f", "joy6"]),
            AutoProps(
                name="cockpit-view",
                desc=p_("input command description",
                        "switch to cockpit view"),
                #note=p_("input command note",
                        #"n/a"),
                seqs=["f1"]),
            AutoProps(
                name="external-view",
                desc=p_("input command description",
                        "switch to world-oriented external view"),
                note=p_("input command note",
                        "This view keeps north-front upwards orientation "
                        "independently of the plane attitude."),
                seqs=["f2"]),
            AutoProps(
                name="rear-view",
                desc=p_("input command description",
                        "switch to chase external view"),
                note=p_("input command note",
                        "This view is following and rotating with the plane "
                        "from behind."),
                seqs=["f3"]),
            AutoProps(
                name="target-view",
                desc=p_("input command description",
                        "switch to target view"),
                note=p_("input command note",
                        "This view can be activated when a target "
                        "is acquired."),
                seqs=["f4"]),
            AutoProps(
                name="fire-chaser-on-off",
                desc=p_("input command description",
                        "enable or disable the missile view"),
                note=p_("input command note",
                        "If enabled, when a missile (or bomb) is launched, "
                        "the view will follow the missile to destruction."),
                seqs=["f5"]),
            AutoProps(
                name="head-look",
                desc=p_("input command description",
                        "look around in the cockpit"),
                note=p_("input command note",
                        "Needed when using a digital joystick hat "
                        "to look around."),
                seqs=["hat1"]),
            AutoProps(
                name="head-turn",
                desc=p_("input command description",
                        "rotate cockpit view left or right"),
                note=p_("input command note",
                        "Needed when using an analog joystick hat "
                        "to look around."),
                seqs=[], isaxis=True,
                exponent=1.0, deadzone=0.05, minval=-1.0, maxval=1.0,
                inverted=False),
            AutoProps(
                name="head-turn-left",
                desc=p_("input command description",
                        "rotate cockpit view to the left"),
                note=p_("input command note",
                        "Needed when using the keyboard "
                        "to look around."),
                seqs=[]),
            AutoProps(
                name="head-turn-right",
                desc=p_("input command description",
                        "rotate cockpit view to the right"),
                note=p_("input command note",
                        "Needed when using the keyboard "
                        "to look around."),
                seqs=[]),
            AutoProps(
                name="head-pitch",
                desc=p_("input command description",
                        "rotate cockpit view up or down"),
                note=p_("input command note",
                        "Needed when using an analog joystick hat "
                        "to look around."),
                seqs=[], isaxis=True,
                exponent=1.0, deadzone=0.05, minval=-1.0, maxval=1.0,
                inverted=False),
            AutoProps(
                name="head-pitch-up",
                desc=p_("input command description",
                        "rotate cockpit view upwards"),
                note=p_("input command note",
                        "Needed when using the keyboard "
                        "to look around."),
                seqs=[]),
            AutoProps(
                name="head-pitch-down",
                desc=p_("input command description",
                        "rotate cockpit view downwards"),
                note=p_("input command note",
                        "Needed when using the keyboard "
                        "to look around."),
                seqs=[]),
            AutoProps(
                name="zoom-view-in",
                desc=p_("input command description",
                        "zoom in current view"),
                note=p_("input command note",
                        "Decrease the FOV of the current view."),
                seqs=["wheel_up", "p"]),
            AutoProps(
                name="zoom-view-out",
                desc=p_("input command description",
                        "zoom out current view"),
                note=p_("input command note",
                        "Increases the FOV of the current view."),
                seqs=["wheel_down", "o"]),
            AutoProps(
                name="virtual-cockpit-on-off",
                desc=p_("input command description",
                        "enable or disable virtual cockpit"),
                note=p_("input command note",
                        "A limited set of virtual cockpit indicators "
                        "appear by default in some external views, "
                        "and this can be used to turned them on or off."),
                seqs=["alt-v"]),
        ]
        # Assert that all binding names are unique.
        assert len(bindings) == len(set(b.name for b in bindings))

        jsdevs = [
            AutoProps(num=1, ext=""),
            AutoProps(num=2, ext="b"),
            AutoProps(num=3, ext="c"),
        ]

        return bindings, jsdevs


    def read_from_file (self, path):

        bindings = self.bindings
        jsdevs = self.jsdevs

        cfg = SafeConfigParser()
        fh = codecs.open(real_path("config", path), "r", "utf8")
        cfg.readfp(fh)
        fh.close()
        seen_fields = set()
        missing_fields = set()
        # Read selected devices.
        devsec = "devices"
        if cfg.has_section(devsec):
            for jsdev in jsdevs:
                jext = ""
                if jsdev.ext:
                    jext = "-" + jsdev.ext
                fljoy = "joystick%s-id" % jext
                if cfg.has_option(devsec, fljoy):
                    seen_fields.add((devsec, fljoy))
                    jsdev.num = cfg.getint(devsec, fljoy)
                else:
                    missing_fields.add((devsec, fljoy, bindg))
        # Read action bindings.
        actsec = "actions"
        if cfg.has_section(actsec):
            read_bindings = {}
            for bindg in bindings:
                if bindg.internal:
                    continue
                if cfg.has_option(actsec, bindg.name):
                    seen_fields.add((actsec, bindg.name))
                    fmtbseqs = cfg.get(actsec, bindg.name).lower()
                    seqs = [x.strip() for x in fmtbseqs.split(",")]
                    bindg.seqs = seqs
                else:
                    missing_fields.add((actsec, bindg.name, bindg))
        # Read axes settings.
        axsec = "axes"
        if cfg.has_section(axsec):
            for bindg in bindings:
                if bindg.internal:
                    continue
                if bindg.isaxis:
                    flexp = bindg.name + "-exponent"
                    if cfg.has_option(axsec, flexp):
                        seen_fields.add((axsec, flexp))
                        bindg.exponent = cfg.getfloat(axsec, flexp)
                    else:
                        missing_fields.add((axsec, flexp, bindg))
                    fldzn = bindg.name + "-deadzone"
                    if cfg.has_option(axsec, fldzn):
                        seen_fields.add((axsec, fldzn))
                        bindg.deadzone = cfg.getfloat(axsec, fldzn)
                    else:
                        missing_fields.add((axsec, fldzn, bindg))
                    flmin = bindg.name + "-min"
                    if cfg.has_option(axsec, flmin):
                        seen_fields.add((axsec, flmin))
                        bindg.minval = cfg.getfloat(axsec, flmin)
                    else:
                        missing_fields.add((axsec, flmin, bindg))
                    flmax = bindg.name + "-max"
                    if cfg.has_option(axsec, flmax):
                        seen_fields.add((axsec, flmax))
                        bindg.maxval = cfg.getfloat(axsec, flmax)
                    else:
                        missing_fields.add((axsec, flmax, bindg))
                    flinv = bindg.name + "-inverted"
                    if cfg.has_option(axsec, flinv):
                        seen_fields.add((axsec, flinv))
                        bindg.inverted = cfg.getboolean(axsec, flinv)
                    else:
                        missing_fields.add((axsec, flinv, bindg))
        # Report seen and missing fields.
        for secname in cfg.sections():
            for flname in cfg.options(secname):
                if (secname, flname) not in seen_fields:
                    warning(
                        _("Unknown input configuration field '%(fld)s' "
                          "in section '%(sec)s'.") %
                        dict(fld=flname, sec=secname))
        for secname, flname, bindg in sorted(missing_fields):
            fmtseq = InputConf.format_binding_sequence(bindg.seqs)
            warning(
                _("Missing input configuration field '%(fld)s' "
                  "in section '%(sec)s', using default '%(val)s'.") %
                dict(fld=flname, sec=secname, val=fmtseq))


    @staticmethod
    def format_binding_sequence (seqs):

        fmt = ", ".join(seqs)
        return fmt


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error(_("Aborting, backtrace follows:\n%s") % traceback.format_exc())

