"""
Formula: Bin
Required module interfaces: is_valid(), calculate()
Arg explaination:
    {
        # a source task slug:
        'src_task': 'i-clicker-total',
        # a list of bins: bins are (threshold, score) pairs; 
        #   the pair (0, 0) is implied.
        'bins': [[50., 3.0], [75., 5.0], ], 
    }
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils import six
from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

NUMERIC_TYPES = six.integer_types + (float, complex)

###############################################################


class BinCalc(FormulaCalc):
    """
    Calculate a binned score.
    """

    type_code = "bin"
    verbose_name = _("Binned")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 2:
            return False
        if "src_task" not in keys:
            return False
        # TODO: Check that src_task exists, for this section?
        if "bins" not in keys:
            return False
        # TODO: Check that bins is a list of numeric pairs.
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        return (("t", self.args["src_task"]),)

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation.  
        """
        src_value = self.symbol_table.get_value(
            self.args["src_task"], transform=self.float0
        )
        result = 0
        for threshold, value in self.args["bins"]:
            if src_value >= threshold:
                result = value

        full_marks = self.floatNone(score.get_full_marks())
        if full_marks is not None:
            outof = self.args["bins"][-1][1]
            if isinstance(outof, NUMERIC_TYPES):
                result = result * full_marks / outof

        if isinstance(result, NUMERIC_TYPES):
            return round(result, ndigits)
        else:
            return result


###############################################################
