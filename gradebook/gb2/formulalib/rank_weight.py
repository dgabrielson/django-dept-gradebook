"""
Formula: RankWeight
Arg explaination:
    {
        src_category: 'term-test',
        # A list of rank weights -- simple numeric values.
        'rank_weights': [30, 20, 0],
    }

In this example, the best score in the 'term-test' category would be
given weight 30; the next highest rank 20; and all remaining weight 0.

The last weight always applies to all remaining.

N.B. the key is ``rank_weights`` rather than ``weights`` so as to not
interfere with the dependency checking in TaskForm.clean()
"""
###############################################################
from __future__ import print_function, unicode_literals

from itertools import zip_longest

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class RankWeightCalc(FormulaCalc):
    """
    Calculate a weighted score.
    """

    type_code = "rwt"
    verbose_name = _("Rank Weighted")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 2:
            return False
        if "rank_weights" not in keys:
            return False
        if "src_category" not in keys:
            return False
        # TODO: Check weights?
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type code, slug pairs for the dependencies
        of this formula.
        """
        return (("c", self.args["src_category"]),)

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation.
        """
        outof = self.floatNone(score.get_full_marks())
        normalize = outof is not None
        value_list = self.symbol_table.get_value(
            self.args["src_category"], transform=self.float0, normalize=normalize
        )
        weight_list = self.args["rank_weights"]
        ranked_values = sorted(value_list, reverse=True)

        ranked_len = len(ranked_values)
        weight_len = len(weight_list)
        diff = ranked_len - weight_len
        if diff > 0:
            # there are more values than weights -- pad weight_list with
            # ``diff`` copies of the last value.
            weight_list += [weight_list[-1]] * diff
        result = sum(
            [w * v for w, v in zip_longest(weight_list, ranked_values, fillvalue=0.0)]
        )

        full_marks = self.floatNone(score.get_full_marks())
        if full_marks is not None:
            outof = sum(weight_list)
            if outof == 0.0:
                return "error ZwS"
            result = result * full_marks / outof

        return round(result, ndigits)


###############################################################
