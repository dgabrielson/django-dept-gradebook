"""
Create/Update Tasks, including associated formula.
"""
###############################################################
from __future__ import print_function, unicode_literals

from pprint import pprint

from django.db import models
from django.utils.text import slugify
from gradebook.models import Ledger, LedgerViewport, Task

from . import get_task_queryset, resolve_fields

DJANGO_COMMAND = "main"
USE_ARGPARSE = True
HELP_TEXT = __doc__.strip()
OPTION_LIST = (
    (
        ["--create"],
        dict(
            action="store_true", help="Give this flag to allow creation of a new task"
        ),
    ),
    (
        ["--all"],
        dict(
            action="store_true",
            help="By default, only one task can be created or updated at a time.  With this option, all matching tasks will have changes applied.",
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
    (["--ledger"], dict(help="Restrict to a specific ledger (by slug)")),
    (["--viewport"], dict(help="Restrict to a specific viewport (by slug)")),
)

###############################################################

###############################################################

# Trickery to dynamically create --new-{{value}} options:
for f in Task._meta.fields[4:]:
    # the 4: slice is to ignore: id, active, created, modified
    OPTION_LIST += (
        (["--new-" + f.name], dict(help="Set a new value for " + f.verbose_name)),
    )
OPTION_LIST += (
    (["--new-viewport"], dict(nargs="*", help="Set a new value for viewports")),
)

###############################################################

###############################################################


def get_new_values(options, resolvers=None):
    """
    Retrieve the new values from the given options.
    """
    results = {}
    if resolvers is None:
        resolvers = {}
    for key in options:
        if key.startswith("new_"):
            name = key[4:]
            item = options[key]
            if item is None:
                continue
            value = resolvers.get(name, lambda x: x)(item)
            if value is not None:
                results[name] = value
    if "name" in results and "slug" not in results:
        results["slug"] = slugify(results["name"])
    return results


###############################################################


def get_changelist(options):
    """
    Get the queryset to act on.
    """
    qs = get_task_queryset(options)
    count = qs.count()
    if count == 1:
        # good for updates:
        return qs, count
    if count == 0 and not options["create"]:
        print("No tasks for updating and --create flag not given")
        return None, count
    if count > 1 and not options["all"]:
        print("Too many tasks, and --all flag not given")
        return None, count
    return qs, count


###############################################################


def viewport_resolver(slug_list):
    if slug_list is None:
        return None
    from gradebook.models import LedgerViewport

    # from classes.models import Section
    qs = LedgerViewport.objects.filter(slug__in=slug_list)
    return qs


def formula_resolver(typedigest):
    if typedigest is None:
        return None
    type, digest = typedigest.split(",", 1)
    from gradebook.models import Formula

    return Formula.objects.get(type=type, digest=digest)


def category_resolver(slug):
    if slug is None:
        return None
    from gradebook.models import Category

    return Category.objects.get(slug=slug)


def public_resolver(s):
    if s.lower() in ["0", "n", "no", "false", "hide"]:
        return False
    if s.lower() in ["1", "y", "yes", "true", "show"]:
        return False
    return None


###############################################################


def main(options, args):
    verbosity = int(options["verbosity"])
    task_qs, count = get_changelist(options)
    updates = get_new_values(
        options,
        resolvers={
            "viewport": viewport_resolver,
            "formula": formula_resolver,
            "category": category_resolver,
            "public": public_resolver,
        },
    )
    if not updates:
        print("No updates given")
        return

    if task_qs is None:
        return
    viewport_m2m = updates.pop("viewport", None)
    if viewport_m2m:
        ledger_id_list = viewport_m2m.values_list("ledger_id", flat=True)
        if len(ledger_id_list) == 1:
            updates["ledger"] = Ledger.objects.get(pk=ledger_id_list[0])
        else:
            raise RuntimeError("Cannot add/update viewports from multiple ledgers")

    if verbosity > 2:
        pprint(updates)

    if count == 0:
        if "ledger" not in updates:
            raise RuntimeError("Cannot create a task without a ledger!")
        task = Task.objects.create(**updates)
        for viewport in viewport_m2m:
            viewport.tasks.add(task)
        if verbosity > 0:
            print("Task created", task.pk, task)
    else:
        for task in task_qs.iterator():
            for key, value in updates.items():
                setattr(task, key, value)
            task.save()
            for viewport in viewport_m2m:
                viewport.tasks.add(task)
            if verbosity > 0:
                print("Task updated", task.pk, task)


###############################################################
