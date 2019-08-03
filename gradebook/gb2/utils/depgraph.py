"""
Generate/Update the dependency fields on either a queryset or an item.

The dependencies fields will form a directed acyclic graph of dependencies,
which is then used to determine execution order of calculations.
"""
###############################################################
from __future__ import print_function, unicode_literals

import operator
from functools import reduce

from django.db import models

from ...models import Category, Score, Task
from ..formulalib import formula_registry

###############################################################


def update_instance(obj, verbosity=0, propogate_task_deps=True):
    """
    Set the dependencies for a single object (which might be either a
    Task or a Score).
    """
    # clear any existing dependencies
    obj.dependencies.clear()

    formula = obj.get_formula()
    if formula is None:
        if verbosity > 2:
            print(
                "{0}: No formula means no dependencies... nothing for this object".format(
                    obj.id
                )
            )
        return

    dep_primitives = formula_registry.get_dependencies(formula)
    if verbosity > 2:
        print("{0}: dep_primitives = {1}".format(obj.id, dep_primitives))
    # resolve primitives based on the current obj.
    dep_task_slugs = [slug for depmodel, slug in dep_primitives if depmodel == "t"]
    if verbosity > 2:
        print("{0}: dep_task_slugs = {1}".format(obj.id, dep_task_slugs))
    dep_category_slugs = [slug for depmodel, slug in dep_primitives if depmodel == "c"]
    if verbosity > 2:
        print("{0}: dep_category_slugs = {1}".format(obj.id, dep_category_slugs))
    # convert primitives to query dictionaries
    query_list = []
    if dep_task_slugs:
        query_list.append({"slug__in": dep_task_slugs})
    if dep_category_slugs:
        query_list.append({"category__slug__in": dep_category_slugs})
    if verbosity > 2:
        print("{0}: query_list = {1}".format(obj.id, query_list))

    if not query_list:
        if verbosity > 2:
            print(
                "{0}: No queries means no dependencies... nothing for this object".format(
                    obj.id
                )
            )
        return

    #     main_query = {'section_id': obj.get_section_id()}       # UPDATE
    main_query = {"ledger_id": obj.get_ledger_id()}
    if verbosity > 2:
        print("{0}: main_query = {1}".format(obj.id, main_query))
    # modify queries for corresponding score objects, if needed
    model_class = type(obj)
    if model_class == Score:
        if verbosity > 2:
            print("{0}: rewriting queries for score object".format(obj.id))
        main_query = {"task__" + k: v for k, v in main_query.items()}
        #         main_query['student_registration'] = obj.student_registration   # UPDATE
        main_query["person_id"] = obj.person_id
        query_list = [{"task__" + k: v for k, v in q.items()} for q in query_list]

    if verbosity > 2:
        print("{0}: exc. main_query = {1}".format(obj.id, main_query))
    if verbosity > 2:
        print("{0}: exc. query_list = {1}".format(obj.id, query_list))

    # Set dependencies
    or_queries = [models.Q(**query) for query in query_list]
    obj.dependencies.set(
        model_class.objects.filter(**main_query)
        .filter(reduce(operator.or_, or_queries))
        .values_list("pk", flat=True)
    )
    if verbosity > 2:
        print(
            "{0}: object has {1} dependencies".format(
                obj.id, obj.dependencies.all().count()
            )
        )

    if verbosity > 1:
        print(obj.dependencies.all())

    if model_class == Task and propogate_task_deps:
        score_qs = obj.score_set.active().filter(formula__isnull=True)
        for score in score_qs.iterator():
            # map task deps to score deps:
            score.update_deps_from_task()


###############################################################


def update_queryset(queryset, verbosity=0):
    """
    Set the dependencies for a queryset of either Tasks or Scores.
    Applies some sanity to the incoming queryset, just in case it's necessary.
    """
    for obj in queryset.filter(formula__isnull=False).select_related("rule").iterator():
        update_instance(obj, verbosity=verbosity)


###############################################################
