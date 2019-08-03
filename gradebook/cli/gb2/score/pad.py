"""
Pad Scores so there is an entry for every student in good standing
for every task.
"""
###############################################################
from __future__ import print_function, unicode_literals

import os
import sys
from time import ctime, sleep, time
from traceback import print_exc

from django import db
from django.db import models
from django.utils import autoreload
from django.utils.timezone import now
from gradebook import signals
from gradebook.models import LedgerViewport, Role, Score

DEFAULT_DELAY = 60.0

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

# from course_role.models import Role
# from classes.models import Section

###############################################################


def pad_scores(verbosity):
    if verbosity > 2:
        print("Padding scores as needed...")
        sys.stdout.flush()
    # only pad for the current term:
    dt = now()
    #     role_qs = Role.objects.active().filter(person__active=True,
    #                                     section__active=True,
    #                                     section__course__active=True,
    #                                     section__course__department__active=True,
    #                                     dtstart__lte=dt, dtend__gt=dt)
    role_qs = Role.objects.active().filter(
        person__active=True,
        viewport__active=True,
        viewport__ledger__active=True,
        dtstart__lte=dt,
        dtend__gt=dt,
    )
    #     current_section_ids = role_qs.values_list('section_id', flat=True).distinct()
    current_viewport_ids = role_qs.values_list("viewport_id", flat=True).distinct()
    #     score_qs = Score.objects.filter(task__section_id__in=current_section_ids)
    score_qs = Score.objects.filter(task__ledgerviewport__in=current_viewport_ids)

    tick = time()

    # tr: task, role/person pairs
    #     tr_all = Section.objects.filter(id__in=current_section_ids
    #                         ).values_list('task__id', 'registration_list__id')
    tr_all = LedgerViewport.objects.filter(
        id__in=current_viewport_ids, role__role="st"
    ).values_list("tasks__id", "role__person_id")
    #    tr = set(filter(lambda (t,r): (t is not None) and (r is not None), tr_all))
    tr = set([(t, r) for t, r in tr_all if (t is not None) and (r is not None)])
    s_tr = set(score_qs.values_list("task_id", "person_id"))
    create_tr = tr.difference(s_tr)
    if create_tr:
        #         create_list = [Score(task_id=t, student_registration_id=r,
        #                              value="", old_value="~") for t,r in create_tr]
        create_list = [
            Score(task_id=t, person_id=p, value="", old_value="~") for t, p in create_tr
        ]
        Score.objects.bulk_create(create_list)
        for s in create_list:
            signals.score_post_save(
                sender="gradebook.cli.gb2.score.pad",
                instance=s,
                created=True,
                raw=False,
            )

    tock = time()
    if verbosity > 2:
        print("Pad scores total time {0} sec".format(tock - tick))
        sys.stdout.flush()
    n = len(create_tr)
    if n > 0 and verbosity > 1:
        print("created {0} score objects".format(n))
        sys.stdout.flush()
    return n


###############################################################


def loop_main(verbosity):
    ns = pad_scores(verbosity)
    if verbosity > 2:
        print(ctime(), "+++ {0} scores".format(ns))
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
                print_exc()
                return
            if hasattr(db, "close_connection"):
                db.close_connection()
            else:
                db.close_old_connections()
            print(ctime(), "Unhandled exception in main loop:")
            print_exc()

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
        print(os.getpid(), file=open(options["pidfile"], "w"))

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
