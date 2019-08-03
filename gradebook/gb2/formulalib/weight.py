"""
Formula: Weight
Arg explaination:
    {
        # A list of weights.
        # Weights are (task slug, value) pairs.
        'weights': [['term-test-1', 25.0],
                    ['term-test-2', 25.0],
                    ['quiz-total', 10.0],
                    ['final-exam', 40.0],],
    }

"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class WeightCalc(FormulaCalc):
    """
    Calculate a weighted score.
    """

    type_code = "wei"
    verbose_name = _("Weighted")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 1:
            return False
        if "weights" not in keys:
            return False
        # TODO: Check weights?
        return True

    ###################################################

    def get_dependencies(self):
        """
        Returns a list of model_type, slug pairs for the dependencies
        of this formula.
        """
        return [("t", slug) for slug, weight in self.args["weights"]]

    ###################################################

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation.
        """
        key_list, weight_list = zip(*self.args["weights"])
        vf_pairs = [
            self.symbol_table.get_value_full(key, transform=self.float0)
            for key in key_list
        ]
        value_list, full_list = zip(*vf_pairs)
        result = 0.0
        for key, weight, value, full in zip(
            key_list, weight_list, value_list, full_list
        ):
            if full == 0.0:
                return "error OoZ:" + key
            result += (weight * value) / full

        full_marks = self.floatNone(score.get_full_marks())
        if full_marks is not None:
            outof = sum(weight_list)
            if outof == 0.0:
                return "error DbZ"
            result = result * full_marks / outof

        return round(result, ndigits)


###############################################################
