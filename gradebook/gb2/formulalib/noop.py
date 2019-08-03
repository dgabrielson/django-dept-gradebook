"""
Formula: Static override
Required module interfaces: is_valid(), calculate()
Arg explaination:
   -- args must be empty.
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc
from .registry import NoValueChange

###############################################################


class NoopCalc(FormulaCalc):
    """
    Do nothing
    """

    type_code = "noop"
    verbose_name = _("Static override")

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
        Actually perform the calculation with the given symbol table values
        and return the result.
        Note that the symbol table contains strings, not floats or ints.
        """
        raise NoValueChange


###############################################################
