"""
Anything specific to the students app integration goes here.
"""
from __future__ import print_function, unicode_literals

###############################################################


def ensure_student_role(studentregistration):
    from .classes_app import ensure_viewport_exists

    viewport = ensure_viewport_exists(studentregistration.section)
    if viewport is None:
        return

    if studentregistration.good_standing():
        from .role import safe_create_update

        safe_create_update(studentregistration.student.person_id, viewport, "st")
    else:
        from .role import safe_deactivate

        safe_deactivate(studentregistration.student.person_id, viewport)


###############################################################


def remove_student_role(studentregistration):
    from .classes_app import ensure_viewport_exists

    viewport = ensure_viewport_exists(studentregistration.section)
    if viewport is None:
        return

    from .role import safe_delete

    safe_delete(studentregistration.student.person_id, viewport)


###############################################################
