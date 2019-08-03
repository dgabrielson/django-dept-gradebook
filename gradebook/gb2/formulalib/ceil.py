"""
Formula: Sum
Required module interfaces: is_valid(), calculate()
Arg explaination:
    {
        # a source task slug
        'src_task': 'quiz-total',
    }
"""
###############################################################
from __future__ import print_function, unicode_literals

from math import ceil

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class CeilCalc(FormulaCalc):
    """
    Calculate a summed score.
    """

    type_code = "ceil"
    verbose_name = _("Ceiling")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 1:
            return False
        if "src_task" not in keys:
            return False
        # TODO: Check that src_category exists, for this section?
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
        result = ceil(src_value)
        return round(result, ndigits)


###############################################################
