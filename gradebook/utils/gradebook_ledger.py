from __future__ import print_function, unicode_literals

import datetime

from django.conf import settings
from django.db import models
from django.utils.timezone import is_naive, make_aware


def get_name_from_section(section):
    return "{} {} {}, {} {}".format(
        section.course.department.code,
        section.course.code,
        section.section_name,
        section.term.get_term_display(),
        section.term.year,
    )


def get_start_finish_dates_from_semester(section):
    """
    [NB: Copied from classes/models.py:class Semester
    Retrieves the earliest start and the latest finish from all
    associated SemesterDateRange's.

    This is robust: if there are no SemesterDateRange's
    associated with this instance, than the return value will still
    be (relatively) meaningful based on the term,
    i.e., Jan - Apr; May - Aug; Sep - Dec.
    """
    results = section.semesterdaterange_set.aggregate(
        min=models.Min("start"), max=models.Max("finish")
    )
    start = results["min"]
    finish = results["max"]

    term_int = int(section.term[0])
    if start is None:
        month = 4 * (term_int - 1) + 1
        start = datetime.date(section.year, month, 1)
    if finish is None:
        month = 4 * term_int + 1
        year = section.year
        if month > 12:
            month -= 12
            year += 1
        finish = datetime.date(year, month, 1) - datetime.timedelta(days=1)

    # promote to datetime... [added from model method]
    start = datetime.datetime.combine(start, datetime.time(0, 0))
    finish = datetime.datetime.combine(finish, datetime.time(23, 59, 59))

    # add timezone info [added from model method]
    if getattr(settings, "USE_TZ", False):
        if is_naive(start):
            start = make_aware(start)
        if is_naive(finish):
            finish = make_aware(finish)

    # add "grace_period_days" to the end:
    # TODO: Cross check this against the course_role code...
    from gradebook import conf

    finish += datetime.timedelta(days=conf.get("grace_period_days"))

    return start, finish


def default_ledger_from_section(Ledger, section, update_access_times=False):
    """
    Reference implementation for the ``conf.get('ledger_from_section')`` callable.
    Note that this function can be called during a migration; so we need to
    assume a mimimum of model functionality.
    """
    dtstart, dtend = get_start_finish_dates_from_semester(section.term)
    obj, created = Ledger.objects.get_or_create(
        slug=section.slug,
        defaults={
            "name": get_name_from_section(section),
            "dtstart": dtstart,
            "dtend": dtend,
        },
    )
    if not created and update_access_times:
        update_fields = []
        if obj.dtstart != dtstart:
            obj.dtstart = dtstart
            update_fields.append("dtstart")
        if obj.dtend != dtend:
            obj.dtend = dtend
            update_fields.append("dtend")
        if update_fields:
            obj.save(update_fields=update_fields)

    return obj


def default_viewport_from_section(Ledger, LedgerViewport, section):
    """
    Reference implementation for the ``conf.get('viewport_from_section')`` callable.
    Note that this function can be called during a migration; so we need to
    assume a mimimum of model functionality.
    """
    try:
        f = float("{}.{}".format(section.term.year, section.term.term))
    except ValueError:
        ordering = 100
    else:
        # From the Django docs for PositiveSmallIntegerField::
        # "Values from 0 to 32767 are safe in all databases supported by Django"
        # hacky Y2K-ish ordering.  Winter 2017 = 171; Fall 2018 = 183
        # this relies on the Semester Term codes being numeric character values.
        ordering = int(round((f - 2000) * 10))
    obj, created = LedgerViewport.objects.get_or_create(
        slug=section.slug,
        defaults={
            "name": get_name_from_section(section),
            "ledger": default_ledger_from_section(Ledger, section),
            "ordering": ordering,
            "public": section.section_type in ["cl", "on"],
        },
    )
    return obj


def default_role_from_id(id_value, hint=None):
    """
    Reference implementation for the ``conf.get('role_from_id')`` callable.
    This should return a list of dictionaries suitable for "double star" expansion
    in a Role queryset filter.
    """
    try:
        id_numeric = int(id_value)
    except ValueError:
        id_numeric = None
    username = {"person__username__iexact": id_value}
    email = {"person__emailaddress__address__iexact": id_value}
    student = {"person__student__student_number": id_numeric}
    queries = []
    if hint is not None:
        if hint == "username":
            queries = [username]
        if hint == "email" or hint.startswith("email "):
            queries = [email]
        if hint == "student" or hint.startswith("student "):
            queries = [student]
    # default queries:
    if not queries:
        queries = [username, email, student]
    return queries
