from __future__ import print_function, unicode_literals

import students.utils.find_student
from django.utils.timezone import now
from gradebook.models import Response, Role, Score
from people.models import Person

###############################################################

DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (["--task-pk"], {"help": "Restrict to a particular task by primary key"}),
    (["--viewport"], {"help": "Restrict to a particular viewport by slug"}),
    (
        ["--alive"],
        {
            "help": "Restrict to sections that have at least one active role",
            "action": "store_true",
        },
    ),
    (["iclicker_id"], {"nargs": "*", "help": "i>clicker IDs to rescore"}),
)
HELP_TEXT = "Rescore i>clicker responses"

###############################################################

# enable iclicker.com websync:
students.utils.find_student.by_iclicker.use_websync = True

###############################################################


def alive_ledgers(dt=None):
    if dt is None:
        dt = now()
    role_qs = Role.objects.active().filter(
        person__active=True,
        viewport__active=True,
        viewport__ledger__active=True,
        dtstart__lte=dt,
        dtend__gt=dt,
    )
    return set(role_qs.values_list("viewport__ledger_id", flat=True))


###############################################################


def print_tabs(*args):
    print("\t".join(["{}".format(a) for a in args]))


###############################################################


def main(options, args):
    args = options["iclicker_id"]
    verbosity = int(options["verbosity"])
    task = options["task_pk"]
    #     section = options['section']
    viewport = options["viewport"]
    alive = options["alive"]

    dtnow = now()

    qs = Response.objects.active().filter(
        scored=False, description__startswith="i>clicker session "
    )
    if alive:
        qs = qs.filter(task__ledger_id__in=alive_ledgers(dtnow))
    #     if section:
    #         qs = qs.filter(task__section__slug=section)
    if viewport:
        qs = qs.filter(task__ledgerviewport__slug=viewport)
    if task:
        qs = qs.filter(task__pk=task)
    if args:
        qs = qs.filter(student_id__in=args)
    iclicker_list = set(qs.values_list("student_id", flat=True))
    for iclicker in iclicker_list:
        # force a websync for registrations that do not exist...
        try:
            students.utils.find_student.by_iclicker(iclicker_id)
        except:
            pass
    task_list = qs.values_list("task_id", flat=True)
    person_list = Person.objects.filter(
        student__iclicker__iclicker_id__in=iclicker_list
    )
    score_list = Score.objects.filter(task__in=task_list, person_id__in=person_list)

    # TODO: consider a --force-all-no-really flag which sets
    #   ``exclude_iclickers=False``:
    score_list.update_for_recalc()
    if verbosity > 0:
        print(score_list.count(), "scores set for recalculation")


###############################################################
