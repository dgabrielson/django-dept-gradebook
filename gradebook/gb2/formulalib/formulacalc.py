"""
FormulaCalc -- formula implementation base object.
"""
###############################################################
from __future__ import print_function, unicode_literals

from django.core.exceptions import ImproperlyConfigured

###############################################################


class SymbolTable(dict):
    """
    Implementation for the symbol table of an formula calculation.
    """

    def add(self, key, type, values):
        self[key] = (type, values)

    def get_cls_value_full(self, key, transform=None, normalize=False, verbosity=0):
        cls, entry = self[key]
        if verbosity > 2:
            print(cls, entry)
        if transform is not None:
            if cls == "c":
                # category:
                entry = [(transform(e[0]), transform(e[1] or e[2])) for e in entry]
            elif cls == "t":
                # single value:
                entry = transform(entry[0]), transform(entry[1] or entry[2])
            else:
                raise RuntimeError('Unknown symbol table type code "{0}"'.format(cls))
            if verbosity > 2:
                print("entry transform:", entry)

        def _normalize_value(entry):
            try:
                return entry[0] / entry[1]
            except ZeroDivisionError:
                return None

        if normalize:
            if cls == "c":
                # category:
                entry = [(_normalize_value(e), transform(1.0)) for e in entry]
            elif cls == "t":
                # single value:
                entry = _normalize_value(entry), transform(1.0)
            else:
                raise RuntimeError('Unknown symbol table type code "{0}"'.format(cls))
            if verbosity > 2:
                print("normalize transform:", entry)

        return cls, entry

    def get_value_full(self, key, transform=None, normalize=False):
        cls, entry = self.get_cls_value_full(key, transform, normalize)
        return entry

    def get_value(self, key, transform=None, normalize=False):
        cls, entry = self.get_cls_value_full(key, transform, normalize)
        if cls == "c":
            # category:
            entry = [e[0] for e in entry]
        elif cls == "t":
            # single value:
            entry = entry[0]
        else:
            raise RuntimeError('Unknown symbol table type code "{0}"'.format(cls))
        return entry


###############################################################


class FormulaCalc(object):
    """
    Implementation logic for individual formulas.
    """

    type_code = None  # subclasses must set
    verbose_name = None  # subclasses must set

    def __init__(self, formula, ndigits=2):
        if formula.type != self.get_formula_code():
            raise RuntimeError(
                'Invalid formula type "{0}" for class {1}'.format(
                    formula.type, self.__class__.__name__
                )
            )
        self.args = formula.args
        self.ndigits = ndigits
        self.dependencies = None
        self.symbol_table = None

    @classmethod
    def get_formula_code(cls):
        if not getattr(cls, "type_code", None):
            raise ImproperlyConfigured(
                "FormulaCalc objects must define the formula_code class attribute"
            )
        return cls.type_code

    @classmethod
    def get_verbose_name(cls):
        if not getattr(cls, "verbose_name", None):
            raise ImproperlyConfigured(
                "FormulaCalc objects must define the verbose_name class attribute"
            )
        return cls.verbose_name

    @staticmethod
    def floatNone(x):
        try:
            return float(x)
        except ValueError:
            return None

    @staticmethod
    def float0(x):
        try:
            return float(x)
        except ValueError:
            return 0.0

    def is_valid(self):
        """
        Returns ``True`` if the arguments seem sensical for this formula,
        ``False`` otherwise.
        """
        # subclasses must implement
        raise ImproperlyConfigured(
            "FormulaCalc objects must implement the is_valid method"
        )

    def build_dependencies(self):
        """
        Returns a list of model_type code, slug pairs for the dependencies
        of this formula.
        Model type codes are:
            ``c``: Category
            ``t``: Task
        """
        # subclasses must implement
        raise ImproperlyConfigured(
            "FormulaCalc objects must implement the build_dependencies method"
        )

    def calculate(self, score, ndigits):
        """
        Actually perform the calculation and return the result,
          but do not modify score.
        ``score`` specifies what the target task should be out of,
            for proper scaling of the result.
            Use, e.g, ``score.get_full_marks()`` if needed.
        ``ndigits`` specifies how many digits should be in the result,
            *if* the result is numeric.
            (Non-numeric results should ignore this.)
            Numeric results should end: ``return round(result, ndigits)``
        """
        # subclasses must implement
        raise ImproperlyConfigured(
            "FormulaCalc objects must implement the calculate method"
        )

    def begin_calc(self, dependency_qs):
        """
        Call this at the beginning of every calculate implementation
        """
        self.get_symbol_table(dependency_qs)

    def calculate_formula(self, score, ndigits=None):
        """
        What should be called outside.
        """
        if ndigits is None:
            ndigits = self.ndigits
        self.begin_calc(score.dependencies.active())
        return self.calculate(score, ndigits)

    def get_dependencies(self):
        if self.dependencies is None:
            self.dependencies.set(self.build_dependencies())
        return self.dependencies

    def get_symbol_table(self, dependency_qs):
        """
        A note about the FormulaCalc symbol table:
        Each entry, by dependency slug, is either a type code plus a
        triplet or a list of triplets, depending on whether the
        dependency is a single task, or an entire category.
        The triplets are:
            (score value, score full marks, task full marks)
        as these values are stored in the database (i.e., strings).
        """
        if self.symbol_table is None:
            self.symbol_table = self.build_symbol_table(dependency_qs)
        return self.symbol_table

    def build_symbol_table(self, scoredep_qs, fields=None):
        """
        Dependencies are specified either as category slugs or task slugs.
        """
        fields = ["value", "full_marks", "task__full_marks"]
        dep_list = self.get_dependencies()
        results = SymbolTable()
        for cls, slug in dep_list:
            if cls == "c":
                results.add(
                    slug,
                    "c",
                    scoredep_qs.filter(task__category__slug=slug).values_list(*fields),
                )
            elif cls == "t":
                try:
                    results.add(
                        slug,
                        "t",
                        scoredep_qs.filter(task__slug=slug).values_list(*fields)[0],
                    )
                except IndexError:
                    results.add(slug, "t", "not found")
            else:
                raise RuntimeError("Invalid dependency class {0}".format(cls.__name__))
        return results


###############################################################
###############################################################
# Example Skeleton
###############################################################
#
# from gradebook.gb2.formulalib.formulacalc import FormulaCalc
#
# class MyCalc(FormulaCalc):
#     type_code = None
#     verbose_name = None
#
#     def is_valid(self):
#         """
#         Returns ``True`` if the arguments seem sensical for this formula,
#         ``False`` otherwise.
#         """
#         raise ImproperlyConfigured('FormulaCalc objects must implement the is_valid method')
#
#
#     def build_dependencies(self):
#         """
#         Returns a list of model_type code, slug pairs for the dependencies
#         of this formula.
#         Model type codes are:
#             ``c``: Category
#             ``t``: Task
#         """
#         raise ImproperlyConfigured('FormulaCalc objects must implement the build_dependencies method')
#
#
#     def calculate(self, score, ndigits):
#         """
#         Actually perform the calculation and return the result,
#           but do not modify score.
#         ``score`` specifies what the target task should be out of,
#             for proper scaling of the result.
#             Use, e.g, ``score.get_full_marks()`` if needed.
#         ``ndigits`` specifies how many digits should be in the result,
#             *if* the result is numeric.
#             (Non-numeric results should ignore this.)
#             Numeric results should end: ``return round(result, ndigits)``
#         """
#         raise ImproperlyConfigured('FormulaCalc objects must implement the calculate method')
#
#
# # and register...
# from gradebook.gb2.formulalib import formula_registry
#
# formula_registry.register(MyCalc)
#
#
###############################################################
