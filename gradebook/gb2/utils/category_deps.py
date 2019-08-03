############################################################################
from __future__ import print_function, unicode_literals

from ...models import Formula, Score
from ..formulalib import formula_registry

############################################################################


# def category_deps(section, st_reg, category_slug, verbosity=0):
def category_deps(ledger, person, category_slug, verbosity=0):
    """
    When a task is created or deleted, check it's category against
    all formulas for this section -- do any of the formulas
    have that category as a src_category?  
    If so, flag that as an unresolved dependency.
    """
    #     score_list = Score.objects.filter(task__section=section).active().has_formula()
    score_list = Score.objects.filter(task__ledger=ledger).active().has_formula()
    if person is not None:
        score_list = score_list.filter(person=person)
    formula_list = score_list.get_formula_queryset()
    dep_set = set()  # set of category dependency formulas.
    for f in formula_list:
        for t, s in formula_registry.get_dependencies(f):
            if t == "c" and s == category_slug:
                dep_set.add(f)
    if verbosity > 2:
        print("dep_set = {}".format(dep_set))
    affected_scores = score_list.formula_filter(dep_set)
    if affected_scores.exists():
        if verbosity > 2:
            print(
                "setting stale dependencies for {} scores".format(
                    affected_scores.count()
                )
            )
        affected_scores.set_stale_dependencies()
        affected_scores.update_for_recalc()


############################################################################
