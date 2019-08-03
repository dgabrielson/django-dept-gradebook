"""
CLI list for Tasks
"""
#######################################################################
#######################################################################
from __future__ import print_function, unicode_literals

from . import get_task_queryset, resolve_fields

HELP_TEXT = __doc__.strip()
DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (
        ["-f", "--fields"],
        dict(
            dest="field_list",
            help="Specify a comma delimited list of fields to include, e.g., -f PROVIDE,EXAMPLE",
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
    (["--task"], dict(help="Specify task (by slug)")),
    (["--category"], dict(help="Specify task category (by slug)")),
    (["--term"], dict(help="Restrict to a specific term (by slug)")),
    (["--course"], dict(help="Restrict to a specific course (by slug)")),
    (["--section"], dict(help="Restrict to a specific section (by slug)")),
)

#######################################################################

#######################################################################


def main(options, args):

    qs = get_task_queryset(options)
    for item in qs:
        value_list = ["{}".format(item.pk), "{}".format(item)]
        if options["field_list"]:
            value_list += resolve_fields(item, options["field_list"].split(","), {})
        print("\t".join(value_list))


#######################################################################
