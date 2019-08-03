"""
Formula: Sum
Required module interfaces: is_valid(), calculate()
Arg explaination:
    {
        # a source category slug
        'src_category': 'iclicker',
    }
"""
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################

###############################################################


class SumCalc(FormulaCalc):
    """
    Calculate a summed score.
    """

    type_code = "sum"
    verbose_name = _("Sum")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 1:
            return False
        if "src_category" not in keys:
            return False
        # TODO: Check that src_category exists, for this section?
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        return (("c", self.args["src_category"]),)

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation. 
        """
        vf_pairs = self.symbol_table.get_value_full(
            self.args["src_category"], transform=self.float0
        )
        if vf_pairs:
            value_list, full_list = zip(*vf_pairs)
            result = sum(value_list)
        else:
            # empty category
            return "NS"

        full_marks = self.floatNone(score.get_full_marks())
        if full_marks is not None:
            outof = sum(full_list)
            result = result * full_marks / outof

        return round(result, ndigits)


###############################################################
