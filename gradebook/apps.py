#########################################################################
from __future__ import print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

#########################################################################


class GradebookConfig(AppConfig):
    name = "gradebook"
    verbose_name = _("Gradebook")

    def ready(self):
        """
        Any app specific startup code, e.g., register signals,
        should go here.
        """
        # register formulas:
        from .gb2 import formulalib

        formulalib.ready()

        # connect signals:
        from . import signals

        signals.ready()


#########################################################################


class GradebookClassesStudentsConfig(GradebookConfig):
    """
    This app config enables integration with the students and classes apps.
    """

    def ready(self):
        super(GradebookClassesStudentsConfig, self).ready()
        from . import signals

        signals.classes_ready()
        signals.students_ready()


#########################################################################
