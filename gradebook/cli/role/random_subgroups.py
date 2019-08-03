"""
Randomly distribute all students(roles) into groups (other viewports).
"""

#######################################################################
#######################################################################
from __future__ import print_function, unicode_literals

import random

from gradebook.models import Role

HELP_TEXT = __doc__.strip()
DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (["--no-save"], dict(action="store_false", dest="save", help="Pretend only")),
    (
        ["--no-delete"],
        dict(
            action="store_false",
            dest="delete",
            help="Do not delete exiting student roles in the destination viewports",
        ),
    ),
    (["--src"], dict(nargs="+", help="Source viewports by primary key")),
    (["--dst"], dict(nargs="+", help="Destination viewports by primary key")),
)

#######################################################################

#######################################################################


def rand_part(lst, n):
    random.shuffle(lst)
    division = len(lst) / float(n)
    return [
        lst[int(round(division * i)) : int(round(division * (i + 1)))] for i in range(n)
    ]


#######################################################################


def main(options, args):
    dst_viewports = options["dst"]
    src_viewports = options["src"]
    verbosity = int(options["verbosity"])
    save = options["save"]
    delete = options["delete"]

    dst_qs = Role.objects.filter(viewport_id__in=dst_viewports, role="st")
    if save and delete and dst_qs.exists():
        if verbosity > 0:
            print("Deleting {} existing roles...".format(dst_qs.count()))
        dst_qs.delete()

    role_qs = Role.objects.filter(viewport_id__in=src_viewports, role="st")
    if verbosity > 1:
        print(
            "Shuffling {} student roles into {} destination viewports...".format(
                role_qs.count(), len(dst_viewports)
            )
        )

    P = rand_part(list(role_qs), len(dst_viewports))

    for dst_viewport, role_list in zip(dst_viewports, P):
        if verbosity > 2:
            print("{}: {}".format(dst_viewport, role_list))
        for r in role_list:
            r.pk = None
            r.viewport_id = dst_viewport
        if save:
            Role.objects.bulk_create(role_list)
        if verbosity > 0:
            msg = "Added {} student roles to viewport.pk = {}".format(
                len(role_list), dst_viewport
            )
            if not save:
                msg += " (not really, because --no-save)"
            print(msg)
