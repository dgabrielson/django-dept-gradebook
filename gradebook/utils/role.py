"""
Role utilities.
"""
from __future__ import print_function, unicode_literals

import logging

from people.models import Person

from .. import conf
from ..models import LedgerViewport, Role
from .start_end import get_start_end

###############################################################

###############################################################

logger = logging.getLogger(__name__)

###############################################################


def _resolve_pks(person, viewport):
    if isinstance(person, Person):
        person_id = person.pk
    else:
        person_id = person
    if isinstance(viewport, LedgerViewport):
        viewport_id = viewport.pk
    else:
        viewport_id = viewport
    return person_id, viewport_id


###############################################################


def schedule_list_for_role(role):
    """
    Given a role code, return the list of schedule names that
    have that role.  Reverse operation of doing a 
    ``conf.get('sectionschedule_roles')[schedule_name] -> role_code``
    lookup.
    """
    reverse_map = {}
    for key, value in conf.get("sectionschedule_roles").items():
        if value in reverse_map:
            reverse_map[value].append(key)
        else:
            reverse_map[value] = [key]
    return reverse_map.get(role, [])


###############################################################


def safe_delete(person, viewport, role=None):
    """
    """
    person_id, viewport_id = _resolve_pks(person, viewport)
    kwargs = {"person_id": person_id, "viewport_id": viewport_id}
    if role is not None:
        kwargs["role"] = role
    try:
        role = Role.objects.get(**kwargs)
    except Role.DoesNotExist:
        pass
    else:
        role.delete()


###############################################################


def safe_deactivate(person, viewport, role=None):
    """
    """
    person_id, viewport_id = _resolve_pks(person, viewport)
    kwargs = {"person_id": person_id, "viewport_id": viewport_id}
    if role is not None:
        kwargs["role"] = role
    try:
        role = Role.objects.get(**kwargs)
    except Role.DoesNotExist:
        pass
    else:
        if role.active:
            role.active = False
            role.save()


###############################################################


def _get_viewport_start_end(dtstart, dtend, role_code, viewport, semester):
    if dtstart is None or dtend is None:
        # Note: get_start_end() takes an optional Semester object...
        #   TODO: Do we need this?
        sdtstart, sdtend = get_start_end(role_code, viewport, semester)
        if dtstart is None:
            dtstart = sdtstart
        if dtend is None:
            dtend = sdtend
    return dtstart, dtend


###############################################################


def safe_create_update(
    person,
    viewport,
    role_code,
    dtstart=None,
    dtend=None,
    change_start_end=True,
    semester=None,
):
    """
    """
    person_id, viewport_id = _resolve_pks(person, viewport)
    if not isinstance(viewport, LedgerViewport):
        viewport = LedgerViewport.objects.get(pk=viewport_id)
    dtstart, dtend = _get_viewport_start_end(
        dtstart, dtend, role_code, viewport, semester
    )
    if dtstart is None or dtend is None:
        # cannot create role without start and end times.
        logger.warning(
            "Cannot create role without start/end times. "
            + "safe_create_update(person= {0}, viewport= {1}, role_code= {2}, ...)".format(
                person, viewport, role_code
            )
        )
        return

    role, created = Role.objects.get_or_create(
        person_id=person_id,
        viewport_id=viewport_id,
        defaults={"role": role_code, "dtstart": dtstart, "dtend": dtend},
    )
    if not created:
        changed = []
        if role.role != role_code:
            if role.upgrade_role(role_code):
                changed.append("role")
        if change_start_end:
            if role.role != role_code:
                dtstart, dtend = _get_viewport_start_end(
                    dtstart, dtend, role.role, viewport, semester
                )
            # if start moves backwards, update it
            if role.dtstart > dtstart:
                role.dtstart = dtstart
                changed.append("dtstart")
            # if end moves forwards, update it.
            if role.dtend < dtend:
                role.dtend = dtend
                changed.append("dtend")
        if changed:
            role.save(update_fields=changed)

    return role


###############################################################
