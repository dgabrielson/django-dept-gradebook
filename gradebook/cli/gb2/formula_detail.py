#######################################################################
from __future__ import print_function, unicode_literals

import json

from gradebook.models import Formula as Model

from . import object_detail

HELP_TEXT = "Get detail on a Formula object"
DJANGO_COMMAND = "main"
OPTION_LIST = ((["pk"], dict(nargs="+", help="Primary key(s) to show details for")),)

#######################################################################

M2M_FIELDS = []
RELATED_ONLY = None  # Specify a list or None; None means introspect for related
RELATED_EXCLUDE = ["task_set", "score_set"]  # any related fields to skip

#######################################################################


def main(options, args):
    args = options.pop("pk")
    args_format = lambda v: json.dumps(v)
    for pk in args:
        # get the object
        obj = Model.objects.get(pk=pk)
        print(
            object_detail(
                obj,
                M2M_FIELDS,
                RELATED_ONLY,
                RELATED_EXCLUDE,
                formatters={"args": args_format},
            )
        )


#######################################################################
