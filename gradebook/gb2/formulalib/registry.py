"""
FormulaRegistry -- the place formulas get registered to.
"""
###############################################################
from __future__ import print_function, unicode_literals

import json

from django.core.exceptions import ImproperlyConfigured
from django.utils import six

if six.PY2:
    from exceptions import Exception

###############################################################


class NoValueChange(Exception):
    """
    Formulas that DO NOT change the score value should
    raise this as a signal.
    """


###############################################################


class FormulaRegistry(object):
    """
    Registry for formula tyes.
    """

    def __init__(self):
        self._registry = {}

    def register(self, formula_calc_class):
        # if type(formula_calc) == type(object):
        #    formula_calc = formula_calc()
        key = formula_calc_class.get_formula_code()
        self._registry[key] = formula_calc_class

    def _get_obj(self, formula):
        formula_calc_class = self._registry.get(formula.type, None)
        if formula_calc_class is None:
            raise ImproperlyConfigured(
                'FormulaCalc for type "{0}" not registered.'.format(formula.type)
            )
        obj = formula_calc_class(formula)
        if isinstance(obj.args, str):
            if obj.args:
                obj.args = json.loads(obj.args)
            else:
                obj.args = {}
        return obj

    @property
    def type_list(self):
        """
        Returns the list of registered types
        """
        return self._registry.keys()

    @property
    def choices(self):
        """
        Returns the list of type codes and verbose names.
        """
        keys = sorted(self.type_list)
        return zip(
            keys, ["{}".format(self._registry[k].get_verbose_name()) for k in keys]
        )

    def is_valid(self, formula):
        """
        Returns True if this is valid formula, and False otherwise.
        """
        # check that the type is valid and known.
        if formula.type not in self.type_list:
            return False
        # check that the args are appropriate for this type.
        formula_calc = self._get_obj(formula)
        return formula_calc.is_valid()

    def get_dependencies(self, formula):
        formula_calc = self._get_obj(formula)
        return formula_calc.get_dependencies()

    def calculate(self, score):
        formula = score.get_formula()
        if formula is None:
            raise NoValueChange
        formula_calc = self._get_obj(formula)
        value = formula_calc.calculate_formula(score)
        if value is None:
            value = ""
        return value


###############################################################

formula_registry = FormulaRegistry()

###############################################################
