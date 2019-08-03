"""
Managers for the gradebook application.
"""
#######################################################################
from __future__ import print_function, unicode_literals

from django.db import models

from .querysets import (
    CategoryQuerySet,
    FormulaQuerySet,
    LedgerQuerySet,
    LedgerViewportQuerySet,
    ResponseQuerySet,
    RoleQuerySet,
    ScoreQuerySet,
    TaskQuerySet,
)

#######################################################################
#######################################################################
#######################################################################


class CustomQuerySetManager(models.Manager):
    """
    Custom Manager for an arbitrary model, just a wrapper for returning
    a custom QuerySet
    """

    queryset_class = models.query.QuerySet
    always_select_related = None

    # use always_select_related when the __str__() method for a model
    #   pull foreign keys.

    def get_queryset(self):
        """
        Return the custom QuerySet
        """
        queryset = self.queryset_class(self.model)
        if self.always_select_related is not None:
            queryset = queryset.select_related(*self.always_select_related)
        return queryset


#######################################################################
#######################################################################
#######################################################################


class CategoryManagerOnly(CustomQuerySetManager):
    queryset_class = CategoryQuerySet


CategoryManager = CategoryManagerOnly.from_queryset(CategoryQuerySet)

#######################################################################


class TaskManagerOnly(CustomQuerySetManager):
    queryset_class = TaskQuerySet
    always_select_related = ["category"]


TaskManager = TaskManagerOnly.from_queryset(TaskQuerySet)

#######################################################################


class ScoreManagerOnly(CustomQuerySetManager):
    queryset_class = ScoreQuerySet
    always_select_related = ["task", "task__category"]


ScoreManager = ScoreManagerOnly.from_queryset(ScoreQuerySet)

#######################################################################


class FormulaManagerOnly(CustomQuerySetManager):
    queryset_class = FormulaQuerySet


FormulaManager = FormulaManagerOnly.from_queryset(FormulaQuerySet)

#######################################################################


class ResponseManagerOnly(CustomQuerySetManager):
    queryset_class = ResponseQuerySet


ResponseManager = ResponseManagerOnly.from_queryset(ResponseQuerySet)

#######################################################################


class RoleManagerOnly(CustomQuerySetManager):
    queryset_class = RoleQuerySet
    always_select_related = ["person", "viewport"]


RoleManager = RoleManagerOnly.from_queryset(RoleQuerySet)

#######################################################################


class LedgerManagerOnly(CustomQuerySetManager):
    queryset_class = LedgerQuerySet


LedgerManager = LedgerManagerOnly.from_queryset(LedgerQuerySet)

#######################################################################


class LedgerViewportManagerOnly(CustomQuerySetManager):
    queryset_class = LedgerViewportQuerySet


LedgerViewportManager = LedgerManagerOnly.from_queryset(LedgerViewportQuerySet)

#######################################################################
