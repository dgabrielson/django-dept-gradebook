"""
Signals for student app integration
"""
from __future__ import print_function, unicode_literals

###############################################################


# when a studentregistration is saved/deleted, set student role
#   post_save -- clear old role/set new role
def studentregistration_post_save(sender, instance, raw, *args, **kwargs):
    """
    Does the student/section role exist?
    """
    if raw:
        return
    # student registrations *generally* never change their student/section
    #   foreign keys, so avoid the database hit for this.

    from ..utils.students_app import ensure_student_role

    ensure_student_role(instance)


###############################################################


#   pre_delete -- clear role
def studentregistration_pre_delete(sender, instance, *args, **kwargs):
    """
    Remove the role.
    """
    from ..utils.students_app import remove_student_role

    remove_student_role(instance)


###############################################################
