"""
These are all the signals necessary for doing the classes <-> gradebook
app synchronization.
"""
from __future__ import print_function, unicode_literals

###############################################################


# when a section is saved, set instructor role
#   pre_save -- clear old role/set new role
def section_pre_save(sender, instance, raw, *args, **kwargs):
    """
    Has the instructor changed?
    """
    if raw:
        return

    from ..utils.classes_app import (
        ensure_ledger_exists,
        ensure_viewport_exists,
        ensure_section_roles_are_correct,
    )

    # Ensure ledger exists
    # Ensure viewport exists.
    ledger = ensure_ledger_exists(instance)
    if ledger is None:
        return
    viewport = ensure_viewport_exists(instance)
    if viewport is None:
        return

    ensure_section_roles_are_correct(viewport, instance)


###############################################################


#   pre_delete -- clear role
def section_pre_delete(sender, instance, *args, **kwargs):
    """
    Remove the roles for the section.
    """
    from ..utils.classes_app import (
        ensure_viewport_exists,
        remove_instructor_role,
        deactivate_viewport,
        deactivate_ledger,
    )

    viewport = ensure_viewport_exists(instance)
    if viewport is None:
        return

    remove_instructor_role(viewport, instance)
    deactivate_viewport(viewport)
    deactivate_ledger(viewport.ledger)


###############################################################


# when a sectionschedule is saved, set appropriate role
# (see conf setting: 'sectionschedule_roles')
#   pre_save -- clear old role/set new role
def sectionschedule_pre_save(sender, instance, raw, *args, **kwargs):
    """
    Has the instructor/type changed?
    """
    if raw:
        return

    from ..utils.classes_app import (
        ensure_viewport_exists,
        ensure_sectionschedule_roles_are_correct,
        redo_ledger_access_times,
    )

    viewport = ensure_viewport_exists(instance.section)
    if viewport is None:
        return
    ensure_sectionschedule_roles_are_correct(viewport, instance)
    redo_ledger_access_times(viewport.ledger, instance.section)


###############################################################


#   pre_delete -- clear role
def sectionschedule_pre_delete(sender, instance, *args, **kwargs):
    """
    Remove the role.
    """
    from ..utils.classes_app import (
        ensure_viewport_exists,
        remove_sectionschedule_role,
        redo_ledger_access_times,
    )

    viewport = ensure_viewport_exists(instance.section)
    if viewport is None:
        return
    remove_sectionschedule_role(viewport, instance)
    redo_ledger_access_times(viewport.ledger, instance.section)


###############################################################
