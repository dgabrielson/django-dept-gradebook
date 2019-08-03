"""
Score count -- changed scores only.
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

    print(Score.objects.active().changed().count())


###############################################################
