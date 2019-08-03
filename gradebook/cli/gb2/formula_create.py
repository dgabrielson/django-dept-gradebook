#######################################################################
from __future__ import print_function, unicode_literals

import json

from django.core.exceptions import ValidationError
from gradebook.gb2.formulalib import formula_registry
from gradebook.models import Formula

from . import object_detail

#######################################################################

HELP_TEXT = "Create or update a single Formula object"
DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (
        ["-t", "--type"],
        dict(help='Specify the type of the new formula.  Use "?" to list types.'),
    ),
    (
        ["-a", "--args"],
        dict(
            dest="args_json",
            help="Specify the args of the new formula (a JSON string).",
        ),
    ),
)

#######################################################################

#######################################################################


def main(options, args):
    verbosity = int(options["verbosity"])
    if verbosity > 2:
        print("options = {}".format(options))
    type_codes = list(zip(*formula_registry.choices))[0]
    if verbosity > 2:
        print("type_codes = {}".format(type_codes))
    if options["type"] not in type_codes or not options["args_json"]:
        if options["type"] == "?":
            for code, desc in formula_registry.choices:
                print("{0}\t{1}".format(code, "{}".format(desc)))
        elif options["type"] and options["type"] not in type_codes:
            print("* Invalid type code")
        print("You must specify both a type and args.")
        return

    args = json.loads(options["args_json"])
    formula = Formula(type=options["type"], args=args)
    try:
        formula.clean()
    except ValidationError as e:
        print(e)
        return

    formula, flag = Formula.objects.get_or_create_by_typeargs(
        type=options["type"], args=args
    )
    action = "created" if flag else "already exists"
    if verbosity > 0:
        print("OK\t{0}\t{1}\t{2}".format(formula.pk, formula, action))
    else:
        print(formula.type + "," + formula.digest)


#######################################################################
