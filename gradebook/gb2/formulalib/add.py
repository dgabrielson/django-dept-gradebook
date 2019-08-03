"""
Formula: Add
Required module interfaces: is_valid(), calculate()
Arg explaination:
    {
        # a list of source task slugs
        'src_tasks': ['midterm2', midterm2-bonus']
    }
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class AddCalc(FormulaCalc):
    """
    Calculate a summed score.
    """

    type_code = "add"
    verbose_name = _("Add")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 1:
            return False
        if "src_tasks" not in keys:
            return False
        # TODO: Check that src_category exists, for this section?
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        return [("t", t) for t in self.args["src_tasks"]]

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation. Straight addition, nothing fancy.
        (This is never rescaled.)
        """
        value_list = [
            self.symbol_table.get_value(t, transform=self.float0)
            for t in self.args["src_tasks"]
        ]
        if value_list:
            result = sum(value_list)
        else:
            # empty task list
            return "NS"

        return round(result, ndigits)


###############################################################
