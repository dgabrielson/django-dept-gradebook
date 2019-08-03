"""
Querysets for the gradebook application.
"""
#######################################################################
from __future__ import print_function, unicode_literals

import operator
from functools import reduce

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from . import conf

#######################################################################
#######################################################################
#######################################################################


class BaseCustomQuerySet(models.query.QuerySet):
    """
    Custom QuerySet.
    """

    def active(self):
        """
        Returns only the active items in this queryset
        """
        return self.filter(active=True)

    def search(self, *criteria):
        """
        Magic search for objects.
        This is heavily modelled after the way the Django Admin handles
        search queries.
        See: django.contrib.admin.views.main.py:ChangeList.get_queryset
        """
        if not hasattr(self, "search_fields"):
            raise ImproperlyConfigured(
                "No search fields.  Provide a "
                "search_fields attribute on the QuerySet."
            )

        if len(criteria) == 0:
            assert False, "Supply search criteria"

        terms = ["{}".format(c) for c in criteria]
        if len(terms) == 1:
            terms = terms[0].split()

        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        qs = self.filter(active=True)
        orm_lookups = [
            construct_search("{}".format(search_field))
            for search_field in self.search_fields
        ]
        for bit in terms:
            or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
            qs = qs.filter(reduce(operator.or_, or_queries))

        return qs.distinct()


#######################################################################
#######################################################################
#######################################################################


class CategoryQuerySet(BaseCustomQuerySet):
    """
    Custom query set methods for Categories.
    """

    def public(self):
        """
        Provided for symmetry with Task.objects.public() and
        Score.objects.public()
        """
        return self.filter(public=True)


#######################################################################


class TaskQuerySet(BaseCustomQuerySet):
    """
    Custom query set methods for Tasks.
    """

    search_fields = ["name"]

    def public(self):
        """
        Filters for public with Category inheritance
        """
        return self.filter(
            public=True | models.Q(public__isnull=True, category__public=True)
        )


#######################################################################


class ScoreQuerySet(BaseCustomQuerySet):
    """
    Custom query set methods for Scores.
    """

    CALC_SENTINEL = "~deadbeef.3735928559~"

    def public(self):
        """
        Filters for public with Task and Category inheritance
        """
        return self.filter(
            public=True
            | models.Q(public__isnull=True, task__public=True)
            | models.Q(
                public__isnull=True,
                task__public__isnull=True,
                task__category__public=True,
            )
        )

    def changed(self):
        """
        Filters the current query set for any scores where the
        current value is not the same as the old value.
        """
        return self.exclude(value=models.F("old_value"))

    def stale_dependencies(self):
        """
        Filters the queryset for those items which need dependency resolution.
        """
        return self.filter(dependencies_resolved=False)

    def set_stale_dependencies(self):
        """
        Update so that these scores will have their dependencies re-done.
        """
        return self.update(dependencies_resolved=False)

    def has_formula(self):
        """
        Filters the current query set for scores (or corresponding tasks)
        which have formulas.
        """
        return self.filter(
            models.Q(formula__isnull=False) | models.Q(task__formula__isnull=False)
        )

    def get_formula_queryset(self):
        """
        Generates a queryset of formulas for these scores (or their
        corresponding tasks).
        """
        score_qs = self.values_list("formula_id", flat=True).distinct()
        task_qs = self.values_list("task__formula_id", flat=True).distinct()
        from .models import Formula

        return Formula.objects.filter(
            models.Q(pk__in=score_qs) | models.Q(pk__in=task_qs)
        ).distinct()

    def formula_filter(self, formula_iter):
        """
        Filters the current query set for scores/tasks
        which have particular formulas.
        ``formula_iter`` - any iterable that query sets can use with the
            ``__in=`` filter.
        """
        return self.filter(
            models.Q(formula__in=formula_iter)
            | models.Q(task__formula__in=formula_iter)
        )

    def calculate(self, verbosity=0):
        """
        Do the calculations of this queryset.
        """
        qs = self.select_related("task", "formula", "task__formula")
        for obj in qs.iterator():
            result = obj.calculate(verbosity=verbosity)

    def resolve_dependencies(self, verbosity=0):
        """
        Do the dependencies resolution for this queryset.
        """
        qs = self.select_related("task", "formula", "task__formula")
        for obj in qs.iterator():
            result = obj.resolve_dependencies(verbosity=verbosity)

    def update_for_recalc(self, exclude_iclickers=True):
        """
        Flags this queryset for recalcuation.
        """
        if exclude_iclickers:
            # Note: exclude scored iclickers from recalcuation as matching
            #   these is dependant on the registrations *at the time*.
            #   Once matched, student iclicker scores should never be
            #   automatically removed.
            qs = self.exclude(
                ~models.Q(value=""),
                models.Q(formula__type="icli") | models.Q(task__formula__type="icli"),
            )
        else:
            qs = self

        # Okay, so this is a magic value, but if this is ever
        #   actually used as a score value, then an instructor
        #   should probably get drawn and quartered.
        # I'd *like* to do value+'~', but F expressions cannot
        #   do string concatenation in a database agnostic way.
        return qs.update(old_value=ScoreQuerySet.CALC_SENTINEL)

    def update_for_redep(self):
        """
        Flags this queryset for resetting each score's dependencies.
        """
        return self.update(dependencies_resolved=False)


#######################################################################


class FormulaQuerySet(BaseCustomQuerySet):
    def get_or_create_by_typeargs(self, type, args):
        """
        Specialized get or create.
        """
        digest = self.model.get_digest(args)
        return self.get_or_create(type=type, digest=digest, defaults={"args": args})

    def get_for_task(self, task):
        """
        This pulls the selectable formulas based on a given task slug.
        In the standard interface (not the admin), this means
        they must have either a blank ``applies_to`` field; or the
        ``applies_to`` field must be a substring of the ``task_slug``.
        (This is the reverse logic of django's ``__startswith=`` filter.)
        Also, selectable formulas must have a description.
        """
        if task.formula is not None:
            if (not task.formula.short_description) or (
                task.formula.applies_to == "-dont-show-"
            ):
                # This will prevent the user form from override a set task
                #   that cannot be selected from the dropdown.
                return self.none()
        # superstring search:
        # see https://stackoverflow.com/a/11906048
        return self.extra(
            where=["%s LIKE applies_to||'%%'"], params=[task.slug]
        ).exclude(short_description="")


#######################################################################


class ResponseQuerySet(BaseCustomQuerySet):
    pass


#######################################################################


class RoleQuerySet(BaseCustomQuerySet):
    """
    Provide a custom model API.  Urls, views, etc. should only
    use these methods, never .filter(...).
    """

    search_fields = [
        "person__cn",
        "person__emailaddress__address",
        "person__student__student_number",
    ]

    def get_available(self, person, dt):
        """
        Get the roles available to the given person on the given date+time.
        """
        return (
            self.active()
            .filter(
                person=person,
                person__active=True,
                viewport__active=True,
                viewport__ledger__active=True,
                dtstart__lte=dt,
                dtend__gt=dt,
            )
            .exclude(role="st", viewport__public=False)
        )

    def from_id(self, id_value, hint=None):
        """
        This is like ``search``, but has a bit more flexibility.
        """
        query_list = conf.get("role_from_id")(id_value, hint)
        if query_list is None:
            return qs.none()
        or_queries = [models.Q(**query) for query in query_list]
        qs = self.filter(reduce(operator.or_, or_queries))
        return qs.distinct()


#######################################################################


class LedgerQuerySet(BaseCustomQuerySet):
    pass


#######################################################################


class LedgerViewportQuerySet(BaseCustomQuerySet):
    pass


#######################################################################
