"""
Formula: i>clicker
Arg explaination:
   {}
   (no arguments)
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class IClickerCalc(FormulaCalc):
    """
    Calculate a weighted score.
    """

    type_code = "icli"
    verbose_name = _("i>clicker Response")

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
        debug = False
        from students.models import Student

        try:
            student = score.person.student
        except Student.DoesNotExist:
            if debug:
                print("Person has no associated student; bailing!")
            # right now; i>clickers must work through a student record...
            return None
        if debug:
            print("task =", score.task)

        from gradebook.models import Response

        response_list = Response.objects.active().filter(task=score.task)
        if debug:
            print("response_list count() is", response_list.count())
        iclicker_list = student.iclicker_set.active()
        if debug:
            print("iclicker_list count() is", iclicker_list.count())
        iclicker_ids = iclicker_list.values_list("iclicker_id", flat=True)
        if debug:
            print("\t", list(iclicker_ids))
        student_responses = response_list.filter(student_id__in=iclicker_ids)
        if debug:
            print("sutdent_reponses count() is", student_responses.count())
        if student_responses.count() == 1:
            response = student_responses.get()
            response.scored = True
            response.save()
            if debug:
                print("responses scored; student score =", response.score)
            return response.score

        if debug:
            print("NO SCORE")
        return None


###############################################################


class IClickerMoodleCalc(FormulaCalc):
    """
    Calculate a weighted score.
    """

    type_code = "iclm"
    verbose_name = _("i>clicker scores")

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
            # right now; i>clickers must work through a student record...
            return None

        from gradebook.models import Response

        response_list = Response.objects.active().filter(task=score.task)
        student_responses = response_list.filter(student_id=student.student_number)
        if student_responses.count() == 1:
            response = student_responses.get()
            response.scored = True
            response.save()
            return response.score

        return None


###############################################################
