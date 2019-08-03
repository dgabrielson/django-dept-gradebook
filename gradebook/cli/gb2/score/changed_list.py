"""
Score list -- changed scores only.
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.db import models
from gradebook.models import Score

DJANGO_COMMAND = "main"
HELP_TEXT = __doc__.strip()
OPTION_LIST = ()
USE_ARGPARSE = True

###############################################################

###############################################################


def main(options, args):
    verbosity = int(options["verbosity"])

    for calc in (
        Score.objects.active()
        .changed()
        .values_list(
            "pk", "person__student__student_number", "task__name", "task__ledger"
        )
    ):
        print("\t".join(["{}".format(e) for e in calc]))


###############################################################
