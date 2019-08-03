"""
CLI list for Formulas
"""
#######################################################################
#######################################################################
from __future__ import print_function, unicode_literals

from gradebook.models import Formula

from . import resolve_fields

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
    (["--types"], dict(action="store_true", help="List only type codes for formulas")),
)

#######################################################################

#######################################################################


def main(options, args):

    if options["types"]:
        from ...gb2.formulalib import formula_registry

        for code, name in formula_registry.choices:
            print("{}\t{}".format(code, name))
    else:
        qs = Formula.objects.active()
        for item in qs:
            value_list = ["{}".format(item.pk), "{}".format(item)]
            if options["field_list"]:
                value_list += resolve_fields(item, options["field_list"].split(","))
            print("\t".join(value_list))


#######################################################################
