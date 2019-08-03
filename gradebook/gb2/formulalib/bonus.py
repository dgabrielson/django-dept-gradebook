"""
Formula: bonus
Arg explaination:
    {
        # number of bonus points
        'points': 1,
         # a source task slug
        'src_task': 'quiz-total',
    }
   - add one bonus point to "quiz-total"
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class BonusCalc(FormulaCalc):
    """
    Pull bubble sheet responses.
    """

    type_code = "bon"
    verbose_name = _("Bonus points")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 2:
            return False
        if "src_task" not in keys:
            return False
        # TODO: Check that src_category exists, for this section?
        if "points" not in keys:
            return False
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        # remember, 't' for tasks, 'c' for categories.
        return (("t", self.args["src_task"]),)

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation. 
        Note that this function **does not** rescale the result.
        """
        src_value = self.symbol_table.get_value(
            self.args["src_task"], transform=self.float0
        )
        result = src_value + self.args["points"]
        return round(result, ndigits)


###############################################################
