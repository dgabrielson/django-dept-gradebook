"""
Formula: Drop
Required module interfaces: is_valid(), calculate()
Arg explaination:
    {
        # a source category slug
        'src_category': 'quiz',
        # the number of items to drop
        'drop_count': 2,
    }
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from .formulacalc import FormulaCalc

###############################################################


class DropCalc(FormulaCalc):
    """
    Calculate a score where the lowest N are dropped.
    """

    type_code = "dro"
    verbose_name = _("Drop lowest N")

    ###################################################

    def is_valid(self):
        keys = self.args.keys()
        if len(keys) != 2:
            return False
        if "src_category" not in keys:
            return False
        # TODO: Check that src_category exists, for this section?
        if "drop_count" not in keys:
            return False
        # Check the drop count is a non-negative integer
        value = self.args["drop_count"]
        try:
            value = int(value)
        except ValueError:
            return False
        if value < 0:
            return False
        # TODO: Check that drop_count is less than the total number of items in the category?
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
        for i in range(self.args["drop_count"]):
            if not value_list:
                break
            v = min(value_list)
            value_list.remove(v)

        # in the above, it's possible for everything to get removed...
        if not value_list:
            return 0.0
            # return 'error EL:{0}'.format(len(self.symbol_table.get_value(
            #                 self.args['src_category'],
            #                 transform=self.float0, normalize=normalize)))

        result = sum(value_list)

        if normalize:
            result = result * outof / len(value_list)

        return round(result, ndigits)


###############################################################
