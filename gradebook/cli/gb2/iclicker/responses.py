from __future__ import print_function, unicode_literals

from gradebook.models import Response

###############################################################

DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (["--task-pk"], {"help": "Restrict to a particular task by primary key"}),
    (["--section"], {"help": "Restrict to a particular section by slug"}),
    (["iclicker_id"], {"nargs": "*", "help": "i>clicker IDs to search for"}),
)
HELP_TEXT = "View raw iclicker responses (fields are iclicker_id, score, response_string, description, scored)"

###############################################################

###############################################################


def print_tabs(*args):
    print("\t".join(["{}".format(a) for a in args]))


###############################################################


def main(options, args):
    args = options["iclicker_id"]
    verbosity = int(options["verbosity"])
    task = options["task_pk"]
    section = options["section"]

    qs = Response.objects.active().filter(description__startswith="i>clicker session ")
    if section:
        qs = qs.filter(task__section__slug=section)
    if task:
        qs = qs.filter(task__pk=task)
    if args:
        qs = qs.filter(student_id__in=args)
    qs = qs.order_by("student_id")
    for resp in qs:
        print_tabs(
            resp.student_id,
            resp.score,
            resp.response_string,
            resp.description,
            # resp.task, # skip task b/c it's the same as the description
            resp.scored,
        )


###############################################################
