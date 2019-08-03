"""
Formula: bubblesheet
Arg explaination:
   {}
   (no arguments)
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class BubbleSheetCalc(FormulaCalc):
    """
    Pull bubble sheet responses.
    """

    type_code = "bbl"
    verbose_name = _("Bubblesheet Response")

    ###################################################

    def is_valid(self):
        return not self.args

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        return []

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation. 
        This is not actually a calculation, but is in fact a matching
        of Responses.
        """
        from students.models import Student

        try:
            student = score.person.student
        except Student.DoesNotExist:
            # right now; bubblesheets must work through a student record...
            return None

        from gradebook.models import Response

        response_list = Response.objects.active().filter(task=score.task)
        #         student_id = score.student_registration.student.student_number
        student_id = student.student_number
        student_responses = response_list.filter(student_id=student_id)
        if student_responses.count() == 1:
            response = student_responses.get()
            response.scored = True
            response.save()
            return response.score

        return None


###############################################################
