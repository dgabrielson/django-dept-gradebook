"""
Anything specific to the classes app integration goes here.
(These functions are typically called by signal handlers.)
"""
###############################################################
from __future__ import print_function, unicode_literals

from .. import conf

###############################################################


def ensure_ledger_exists(section):
    ledger_from_section = conf.get("ledger_from_section")
    if ledger_from_section is None:
        return
    from ..models import Ledger

    return ledger_from_section(Ledger, section)


###############################################################


def ensure_viewport_exists(section):
    viewport_from_section = conf.get("viewport_from_section")
    if viewport_from_section is None:
        return
    from ..models import Ledger, LedgerViewport

    return viewport_from_section(Ledger, LedgerViewport, section)


###############################################################


def ensure_section_roles_are_correct(viewport, section):
    """
    NB: ``viewport`` can be ``None``
    """
    # Ensure roles are correct
    if hasattr(section, "id") and section.id is not None:
        # existing object ... get the old one:
        from classes.models import Section
        from .role import schedule_list_for_role

        original = Section.objects.get(id=section.id)
        # check to see if this instructor is still an instructor
        #   for an associated sectionschedule.
        schedule_list = schedule_list_for_role("in")
        schedule_instructor_ids = (
            original.sectionschedule_set.all()
            .filter(type__name__in=schedule_list)
            .values_list("instructor_id", flat=True)
        )
        if (
            (original.instructor_id is not None)
            and (original.instructor_id != section.instructor_id)
            and (original.instructor_id not in schedule_instructor_ids)
        ):
            # remove original coordinator role for all sections.
            from .role import safe_delete

            original_viewport = ensure_viewport_exists(original)
            if original_viewport is not None:
                safe_delete(original.instructor_id, original_viewport)

    # Ensure the main instructor role has been set
    if viewport is not None and section.instructor_id is not None:
        from .role import safe_create_update

        safe_create_update(section.instructor_id, viewport, "in", semester=section.term)


###############################################################


def remove_instructor_role(viewport, section):
    if section.instructor_id is not None:
        from .role import safe_delete

        safe_delete(section.instructor_id, viewport)


###############################################################


def deactivate_viewport(viewport):
    if viewport.active:
        viewport.active = False
        viewport.save()


###############################################################


def deactivate_ledger(ledger):
    """
    Only deactivate a ledger if all of it's viewports are not active.
    """
    if not ledger.active:
        return
    if not ledger.ledgerviewport_set.all().exists():
        ledger.active = False
        ledger.save()


###############################################################


def ensure_sectionschedule_roles_are_correct(viewport, sectionschedule):

    if hasattr(sectionschedule, "id") and sectionschedule.id is not None:
        # existing object ... get the old one:
        from classes.models import SectionSchedule

        original = SectionSchedule.objects.get(id=sectionschedule.id)
        if original.instructor_id is not None:
            if (original.instructor_id != sectionschedule.instructor_id) or (
                original.type_id != sectionschedule.type_id
            ):
                # remove original schedule role.
                original_viewport = ensure_viewport_exists(original.section)
                if original_viewport:
                    from .role import safe_delete

                    safe_delete(original.instructor_id, original_viewport)

    if viewport is not None and sectionschedule.instructor_id is not None:
        from .role import safe_create_update

        role_code = conf.get("sectionschedule_roles").get(
            sectionschedule.type.name, None
        )
        if role_code is not None:
            safe_create_update(
                sectionschedule.instructor_id,
                viewport,
                role_code,
                semester=sectionschedule.section.term,
            )


###############################################################


def redo_ledger_access_times(ledger, section):
    ledger_from_section = conf.get("ledger_from_section")
    if ledger_from_section is None:
        return
    from ..models import Ledger

    return ledger_from_section(Ledger, section, update_access_times=True)


###############################################################


def remove_sectionschedule_role(viewport, sectionschedule):

    # check to see if this role should exist for any other part of the section,
    #   if not, then remove it.
    if sectionschedule.instructor_id is not None:
        role_code = conf.get("sectionschedule_roles").get(
            sectionschedule.type.name, None
        )
        if role_code is not None:
            from .role import safe_delete

            safe_delete(sectionschedule.instructor_id, viewport, role=role_code)


###############################################################
