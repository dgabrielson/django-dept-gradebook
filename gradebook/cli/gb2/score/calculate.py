"""
Score calculator.
"""
from __future__ import print_function, unicode_literals

import os
import sys
from time import ctime, sleep, time
from traceback import print_exc

from django import db
from django.db import models
from django.utils import autoreload
from gradebook.models import Score

###############################################################

DEFAULT_DELAY = 1.0

###############################################################

###############################################################

DJANGO_COMMAND = "main"
USE_ARGPARSE = True
HELP_TEXT = __doc__.strip()
OPTION_LIST = (
    (
        ["--repeat"],
        dict(action="store_true", help="Repeat the polling forever (daemon mode)"),
    ),
    (["--autoreload"], dict(action="store_true", help="Autoreload on code changes")),
    (
        ["--delay"],
        dict(
            type=float, default=DEFAULT_DELAY, help="Number of seconds between cycles"
        ),
    ),
    (
        ["--background"],
        dict(
            action="store_true",
            help="Run the process in the background.  Requires --repeat, --logfile, and --pidfile.",
        ),
    ),
    (["--logfile"], dict(help="Log messages to a file, instead of standard output.")),
    (["--pidfile"], dict(help="Store the pid of the process in the named file.")),
)

###############################################################

###############################################################


def resolve_stale_dependencies(verbosity):
    qs = Score.objects.active().stale_dependencies()
    n = qs.count()
    if n > 0:
        if verbosity > 1:
            print(ctime(), "resolving {0} dependencies...".format(n), end=" ")
            sys.stdout.flush()
        tick = time()
        qs.resolve_dependencies()
        tock = time()
        if verbosity > 1:
            print("depedency resolution took {0} sec".format(tock - tick))
            sys.stdout.flush()
    return n


###############################################################


def do_changed_calculations(verbosity):
    # do calculations
    qs = Score.objects.active().changed()
    n = qs.count()
    if n > 0:
        if verbosity > 1:
            print(ctime(), "starting {0} calculations...".format(n), end=" ")
            sys.stdout.flush()
        tick = time()
        qs.calculate(verbosity)
        tock = time()
        if verbosity > 1:
            print("took {0} sec".format(tock - tick))
            sys.stdout.flush()
    return n


###############################################################


def loop_main(verbosity):
    nd = resolve_stale_dependencies(verbosity)
    nc = do_changed_calculations(verbosity)
    if verbosity > 2:
        print(ctime(), "+++ {1} dependencies; {1} calculations".format(nd, nc))
        sys.stdout.flush()


###############################################################


def daemon_main(verbosity=1, delay=DEFAULT_DELAY, traceback=False):
    if verbosity > 0:
        print(ctime(), "=== (Re)Starting daemon mode ===")
    while True:
        try:
            loop_main(verbosity)
        except:
            if traceback:
                print_exc(file=sys.stdout)
                return
            if hasattr(db, "close_connection"):
                db.close_connection()
            else:
                db.close_old_connections()
            print(ctime(), "Unhandled exception in main loop:")
            print_exc(file=sys.stdout)

        sleep(delay)
        if verbosity > 3:
            print(ctime(), "BEAT")
        sys.stdout.flush()


###############################################################


def main(options, args):
    verbosity = int(options["verbosity"])
    use_reloader = options["autoreload"]
    daemon_mode = options["repeat"]

    if options["background"] and not (
        options["repeat"] and options["logfile"] and options["pidfile"]
    ):
        print(
            "Will not run in the background without --repeat, --logfile, and --pidfile"
        )
        return

    if options["pidfile"]:
        if options["autoreload"]:
            print("Cannot run with both autoreload and pidfile")
            return
        if os.path.exists(options["pidfile"]):
            print("Not running with an existing pidfile.")
            return

    if options["logfile"]:
        sys.stdout = open(options["logfile"], "a+")

    if options["background"]:
        if os.fork() != 0:  # parent
            return
        if os.fork() != 0:  # parent
            return

    if options["pidfile"]:
        open(options["pidfile"], "w").write("{0}".format(os.getpid()))

    try:
        if daemon_mode:
            args = ()
            kwargs = {
                "verbosity": verbosity,
                "delay": options["delay"],
                "traceback": options["traceback"],
            }
            if use_reloader:
                autoreload.main(daemon_main, args, kwargs)
            else:
                daemon_main(*args, **kwargs)
        else:
            loop_main(verbosity)
    finally:
        if options["pidfile"] and os.path.exists(options["pidfile"]):
            if int(open(options["pidfile"]).read()) == os.getpid():
                os.remove(options["pidfile"])


###############################################################
