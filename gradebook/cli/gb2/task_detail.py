#######################################################################
from __future__ import print_function, unicode_literals

from gradebook.models import Task as Model

from . import object_detail

HELP_TEXT = "Get detail on a Task object, including related objects"
USE_ARGPARSE = True
DJANGO_COMMAND = "main"
OPTION_LIST = ((["pk"], dict(nargs="+", help="Primary keys to show details for")),)

#######################################################################

M2M_FIELDS = []
RELATED_ONLY = None  # Specify a list or None; None means introspect for related
RELATED_EXCLUDE = ["score_set"]  # any related fields to skip

#######################################################################


def main(options, args):
    for pk in options["pk"]:
        # get the object
        obj = Model.objects.get(pk=pk)
        print(object_detail(obj, M2M_FIELDS, RELATED_ONLY, RELATED_EXCLUDE))


#######################################################################
