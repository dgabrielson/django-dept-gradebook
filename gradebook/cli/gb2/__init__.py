"""
Utility functions for command line interface management scripts.
"""
################################################################
from __future__ import print_function, unicode_literals

from django.conf import settings
from django.utils import six
from django.utils.encoding import force_text
from gradebook.models import Task

################################################################


def _resolve_lookup(object, name, formatter=None):
    """
    This function originally found in django.templates.base.py, modified
    for arbitrary nested field lookups from the command line -F argument.
    
    Performs resolution of a real variable (i.e. not a literal) against the
    given context.

    As indicated by the method's name, this method is an implementation
    detail and shouldn't be called by external code. Use Variable.resolve()
    instead.
    """
    current = object
    try:  # catch-all for silent variable failures
        for bit in name.split("."):
            if current is None:
                return ""
            try:  # dictionary lookup
                current = current[bit]
            except (TypeError, AttributeError, KeyError, ValueError):
                try:  # attribute lookup
                    current = getattr(current, bit)
                except (TypeError, AttributeError):
                    try:  # list-index lookup
                        current = current[int(bit)]
                    except (
                        IndexError,  # list index out of range
                        ValueError,  # invalid literal for int()
                        KeyError,  # current is a dict without `int(bit)` key
                        TypeError,
                    ):  # unsubscriptable object
                        return "Failed lookup for [{0}]".format(
                            bit
                        )  # missing attribute
            if callable(current):
                if getattr(current, "do_not_call_in_templates", False):
                    pass
                elif getattr(current, "alters_data", False):
                    current = "<< invalid -- no data alteration >>"
                else:
                    try:  # method call (assuming no args required)
                        current = current()
                    except TypeError:  # arguments *were* required
                        # GOTCHA: This will also catch any TypeError
                        # raised in the function itself.
                        current = (
                            settings.TEMPLATE_STRING_IF_INVALID
                        )  # invalid method call
    except Exception as e:
        if getattr(e, "silent_variable_failure", False):
            current = "<< invalid -- exception >>"
        else:
            raise

    if formatter is None:
        return force_text(current)
    else:
        return formatter(current)


################################################################


def resolve_fields(object, field_list, formatters):
    """
    Resolve the field_list into an iterator of values.
    """
    if isinstance(field_list, six.string_types):
        field_list = [field_list]
    return (
        _resolve_lookup(object, field, formatters.get(field, None))
        for field in field_list
    )


################################################################


def object_with_fields(object, formatters, fields=None):
    """
    Return a list of tab delimited strings of the object and its fields.
    """
    if fields is None:
        fields = [f.name for f in object.__class__._meta.fields]
    lines = ["{0}\t{1}".format(object.__class__.__name__, object)]
    values = resolve_fields(object, fields, formatters)
    lines += ["\t" + f + "\t" + v for f, v in zip(fields, values)]
    return "\n".join(lines)


################################################################


def object_detail(
    object, m2m_fields=None, related_only=None, related_exclude=None, formatters=None
):
    """
    Print details of an object.
    """
    if formatters is None:
        formatters = {}
    if m2m_fields is None:
        m2m_fields = []
    if related_exclude is None:
        related_exclude = []
    result = object_with_fields(object, formatters) + "\n"
    # m2m fields:
    for field in m2m_fields:
        result += (
            "\t"
            + field
            + "\t"
            + ", ".join(["{}".format(o) for o in getattr(object, field).all()])
            + "\n"
        )
    if related_only is None:
        related_sets = [attr for attr in dir(object) if attr.endswith("_set")]
    else:
        related_sets = related_only
    for attr in related_sets:
        if attr in related_exclude:
            continue
        related = getattr(object, attr)
        for rel_obj in related.all():
            result += object_with_fields(rel_obj, formatters) + "\n"
    return result


################################################################


################################################################


def get_task_queryset(options):
    qs = Task.objects.active()
    #     if options.get('term', None):
    #         qs = qs.filter(section__term__slug=options['term'])
    #     elif options.get('current', None):
    #         from classes.models import Semester
    #         current_term = Semester.objects.get_current()
    #         qs = qs.filter(section__term=current_term)
    if options.get("viewport", None):
        qs = qs.filter(ledgerviewport__slug=options["viewport"])
    if options.get("ledger", None):
        qs = qs.filter(ledger__slug=options["ledger"])
    if options.get("category", None):
        qs = qs.filter(category__slug=options["category"])
    if options.get("task", None):
        qs = qs.filter(slug=options["task"])
    return qs


################################################################
