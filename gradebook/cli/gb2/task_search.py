#######################################################################
from __future__ import print_function, unicode_literals

from . import get_task_queryset, object_detail

HELP_TEXT = "Search for Task objects"
DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (
        ["--no-detail"],
        dict(
            action="store_false",
            dest="detail",
            default=True,
            help="By default, when only one result is returned, details will be printed also.  Giving this flag supresses this behaviour",
        ),
    ),
    # get_task_queryset options:
    (
        ["--no-current"],
        dict(
            action="store_false",
            dest="current",
            default=True,
            help="By default, restrict to current sections",
        ),
    ),
    (["--term"], dict(help="Restrict to a specific term (by slug)")),
    (["--course"], dict(help="Restrict to a specific course (by slug)")),
    (["--section"], dict(help="Restrict to a specific section (by slug)")),
    (["--category"], dict(help="Restrict to a specific category (by slug)")),
    (["args"], dict(nargs="+", help="Search terms")),
)

#######################################################################

#######################################################################


def main(options, args):
    args = options.pop("args")
    obj_list = get_task_queryset(options)
    if args:
        obj_list = obj_list.search(*args)
    if options["detail"] and obj_list.count() == 1:
        obj = obj_list.get()
        object_detail.main(obj)
    else:
        for obj in obj_list:
            print("{}".format(obj.pk) + "\t" + "{}".format(obj))


#######################################################################
