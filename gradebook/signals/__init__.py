"""
Signals are for gb2.
"""
from __future__ import print_function, unicode_literals

################################################################
#
# Signals are needed to handle the cases when a task is
#   added or removed from a category for which
#   there is a category dependency.
# In general, it is probably a good strategy to recalculate
#   rather than leave wrong calculations
#
################################################################


def score_post_save(sender, instance, created, raw, *args, **kwargs):
    """
    When a task is created, check it's category against
    all formulas for this ledger -- do any of the formulas
    have that category as a src_category?  
    If so, flag that as an unresolved dependency.
    """
    if raw:
        return
    if not created:
        return
    from gradebook.gb2.utils.category_deps import category_deps

    # Caution: bulk_created, as used in cli.score.pad; does not make this happen.
    category_deps(instance.task.ledger, instance.person, instance.task.category.slug)


################################################################


def score_post_delete(sender, instance, *args, **kwargs):
    """
    When a task is deleted, check it's category against
    all formulas for this ledger -- do any of the formulas
    have that category as a src_category?  
    If so, flag that as an unresolved dependency.
    
    Remember -- this instance is no longer in the database.
    """
    from gradebook.gb2.utils.category_deps import category_deps

    category_deps(instance.task.ledger, instance.person, instance.task.category.slug)


################################################################


def ready():
    """
    Register signals etc.
    """
    from django.db import models
    from ..models import Score

    models.signals.post_delete.connect(score_post_delete, sender=Score)
    models.signals.post_save.connect(score_post_save, sender=Score)


################################################################


def classes_ready():
    """
    Register signals for integration with the classes app.
    """
    from django.db import models
    from classes.models import Section, SectionSchedule
    from . import classes_app

    models.signals.pre_delete.connect(classes_app.section_pre_delete, sender=Section)
    models.signals.pre_save.connect(classes_app.section_pre_save, sender=Section)
    models.signals.pre_delete.connect(
        classes_app.sectionschedule_pre_delete, sender=SectionSchedule
    )
    models.signals.pre_save.connect(
        classes_app.sectionschedule_pre_save, sender=SectionSchedule
    )


################################################################


def students_ready():
    """
    Register signals for integration with the students app.
    """
    from django.db import models
    from students.models import Student_Registration
    from . import students_app

    models.signals.pre_delete.connect(
        students_app.studentregistration_pre_delete, sender=Student_Registration
    )
    models.signals.post_save.connect(
        students_app.studentregistration_post_save, sender=Student_Registration
    )


################################################################
