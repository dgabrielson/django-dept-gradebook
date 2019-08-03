"""
Purge student roles for student registrations that are not in good standing.
This is required because course list uploads do bulk changes, which bypasses
the signals that normally deal with this change.

NOTE: This is now fairly hacky -- do we even need the Student_Registration
model?  What purpose does it serve??

At the momemnt, Student_Registration objects are forever, and keep a 
record of registrations in sections.

Role(role='st') objects on the other hand are transient, and get purged.
"""
#######################################################################
#######################################################################
from __future__ import print_function, unicode_literals

from classes.models import Section
from django.db import models
from django.utils.timezone import now
from students.models import Student_Registration

from ... import conf
from ...models import Ledger, LedgerViewport, Role

HELP_TEXT = __doc__.strip()
DJANGO_COMMAND = "main"
USE_ARGPARSE = True
OPTION_LIST = (
    (["--no-save"], dict(action="store_false", dest="save", help="Pretend only")),
)

#######################################################################

#######################################################################


def main(options, args):

    save = options.get("save")
    verbosity = int(options.get("verbosity"))

    n = now()
    student_role_qs = Role.objects.filter(role="st", dtstart__lte=n, dtend__gte=n)
    if verbosity > 2:
        print("Considering {} current student roles".format(student_role_qs.count()))
    #     ledger_set = set(student_role_qs.values_list('ledger', flat=True))
    # inverse mapping problem; again.

    student_vl = student_role_qs.values_list("person__student", flat=True)

    if verbosity > 2:
        print("{} corresponding students".format(len(student_vl)))
    #     streg_qs = Student_Registration.objects.filter(section__in=section_set)
    streg_qs = Student_Registration.objects.filter(student__in=student_vl)
    if verbosity > 2:
        print("{} corresponding student registraitons".format(streg_qs.count()))
    streg_qs = streg_qs.exclude(
        models.Q(status__endswith="A") | models.Q(status__endswith="C")
    )
    if verbosity > 0:
        print(
            "{} student registrations are not in good standing".format(streg_qs.count())
        )
    section_id_set = set(streg_qs.values_list("section_id", flat=True))
    viewport_from_section = lambda s: conf.get("viewport_from_section")(
        Ledger, LedgerViewport, s
    )
    if conf.get("viewport_from_section") is None:
        print("[!] automatic section -> viewport mapping is disabled")
        return
    section_set = {Section.objects.get(pk=sid) for sid in section_id_set}
    viewport_map = {s.pk: viewport_from_section(s) for s in section_set}
    deleted_count = 0
    does_not_exist_count = 0

    for streg in streg_qs:
        if verbosity > 2:
            print(streg)
        viewport = viewport_map[streg.section_id]
        try:
            role = Role.objects.get(
                role="st", viewport=viewport, person=streg.student.person_id
            )
        except Role.DoesNotExist:
            does_not_exist_count += 1
            if verbosity > 2:
                print(" -> Corresponding role does not exist")
        else:
            deleted_count += 1
            if save:
                role.delete()
            if verbosity > 2:
                print(" -> Corresponding role DELETED")
    if verbosity > 0:
        print("-> {} roles deleted".format(deleted_count))
    if verbosity > 1:
        print("-> {} roles already deleted".format(does_not_exist_count))
    if not save and verbosity > 0:
        print("(No roles were harmed in the running of this program.)")


#######################################################################
