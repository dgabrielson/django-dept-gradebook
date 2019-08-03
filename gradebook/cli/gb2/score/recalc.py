"""
(Re)Queue everything for re-calculation.
NOTE: This actually queues calculations for the calculation processor.
"""
###############################################################
###############################################################
from __future__ import print_function, unicode_literals

from django.db import models
from gradebook.models import Score

DJANGO_COMMAND = "main"
HELP_TEXT = __doc__.strip()
OPTION_LIST = (
    (["--deps"], dict(action="store_true", help="Also redo all dependencies")),
    (["slug"], dict(nargs="+", help="ledger slugs to recalculate")),
)

###############################################################

###############################################################


def main(options, args):
    verbosity = int(options["verbosity"])
    args = options.get("slug")

    if not args:
        print("Supply one or more ledger slugs for recalculation")

    for slug in args:
        if verbosity > 0:
            print(slug, end=" ")
        score_list = (
            Score.objects.filter(task__ledger__slug=slug).active().has_formula()
        )
        if verbosity > 0:
            print(score_list.count(), "scores", end=" ")
        if options["deps"]:
            score_list.resolve_dependencies(verbosity=verbosity)
        score_list.update_for_recalc()
        if verbosity > 0:
            print()


###############################################################
