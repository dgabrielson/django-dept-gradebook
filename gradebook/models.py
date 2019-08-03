# -*- coding: utf-8 -*-
"""
Gradebook Models.
"""
############################################################################
from __future__ import print_function, unicode_literals

import hashlib
import json
from collections import OrderedDict

from autoslug import AutoSlugField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse_lazy
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField

from . import conf
from .gb2.formulalib import NoValueChange, formula_registry
from .managers import (
    CategoryManager,
    FormulaManager,
    LedgerManager,
    LedgerViewportManager,
    ResponseManager,
    RoleManager,
    ScoreManager,
    TaskManager,
)
from .querysets import ScoreQuerySet

############################################################################


class GradebookBaseModel(models.Model):
    """
    An abstract base class.
    """

    active = models.BooleanField(default=True)
    created = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name=_("creation time")
    )
    modified = models.DateTimeField(
        auto_now=True, editable=False, verbose_name=_("last modification time")
    )

    class Meta:
        abstract = True


############################################################################


@python_2_unicode_compatible
class Ledger(GradebookBaseModel):
    """
    Ledger -- collections of tasks.
    """

    name = models.CharField(max_length=128)
    slug = AutoSlugField(max_length=128, populate_from="name")
    ordering = models.PositiveSmallIntegerField(default=100)
    dtstart = models.DateTimeField(
        verbose_name=_("start"), help_text="When the ledger begins"
    )
    dtend = models.DateTimeField(
        verbose_name=_("end"), help_text="When the ledger finishes"
    )

    objects = LedgerManager()

    class Meta:
        ordering = ("ordering", "name")
        base_manager_name = "objects"

    def __str__(self):
        return self.name


############################################################################


@python_2_unicode_compatible
class Category(GradebookBaseModel):
    """
    Categories -- types of Tasks.
    """

    name = models.CharField(max_length=64)
    slug = AutoSlugField(
        max_length=64, primary_key=True, editable=True, populate_from="name"
    )
    ordering = models.PositiveSmallIntegerField(default=100)
    public = models.BooleanField(
        default=True, help_text=_("Whether or not students can see their own score")
    )

    objects = CategoryManager()

    class Meta:
        ordering = ("ordering", "name")
        verbose_name_plural = _("Categories")
        base_manager_name = "objects"

    def __str__(self):
        return self.name

    def is_public(self):
        # this is here for symmetry is Task.is_public() and Score.is_public()
        return self.public


############################################################################


@python_2_unicode_compatible
class Task(GradebookBaseModel):
    """
    Task -- a container for scores -- associated with a section.
    """

    PUBLIC_CHOICES = (
        (None, "Use category setting"),
        (False, "Hide from students"),
        (True, "Show to students"),
    )
    name = models.CharField(max_length=64)
    ordering = models.PositiveSmallIntegerField(default=100)
    public = models.NullBooleanField(
        blank=True,
        help_text=_("Whether or not students can see their own score"),
        choices=PUBLIC_CHOICES,
    )
    full_marks = models.CharField(
        max_length=32, blank=True, help_text=_("Only makes sense for numeric tasks")
    )
    category = models.ForeignKey(
        "gradebook.Category",
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
    )
    ledger = models.ForeignKey(
        Ledger, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )
    slug = AutoSlugField(
        max_length=64, populate_from="name", unique_with="ledger", always_update=True
    )
    formula = models.ForeignKey(
        "gradebook.Formula",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
    )

    objects = TaskManager()

    class Meta:
        ordering = ("ordering", "category", "name")
        unique_together = (("slug", "ledger"),)
        base_manager_name = "objects"

    def __str__(self):
        return self.name

    # Note: Can no longer determine an absolute url -- tasks are shared by
    #   1+ viewports...
    #     def get_absolute_url(self):
    #         return reverse_lazy('gradebook2-task-detail',
    #                             kwargs={'section': self.section.slug,
    #                                     'task': self.slug})

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields", None)
        if update_fields is None:
            # note: no change in kwargs
            update_fields = ["formula", "full_marks"]

        results = super(Task, self).save(*args, **kwargs)
        if "formula" in update_fields:
            self.score_set.update_for_redep()
        if "formula" in update_fields or "full_marks" in update_fields:
            self.score_set.update_for_recalc()

        return results

    def is_public(self):
        if self.public is not None:
            return self.public
        return self.category.is_public()

    def get_formula(self):
        """
        Provided so that scores and tasks can be treated symmetrically
        WRT formula (cascade formulas).
        """
        return self.formula

    def get_ledger_id(self):
        """
        This is used by the utils/depgraph.py module.
        """
        return self.ledger_id

    # TODO: Consider an is_valid() method, which cross checks the
    #   formula & dependencies of this task instance.
    #   (And gives information about what's wrong, if anything.)


############################################################################


@python_2_unicode_compatible
class LedgerViewport(GradebookBaseModel):
    """
    LedgerViewport -- collection of roles; and some subset of the corresponding
    ledger's tasks.
    """

    ledger = models.ForeignKey(
        Ledger, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )

    name = models.CharField(max_length=128)
    slug = AutoSlugField(max_length=128, populate_from="name")
    ordering = models.PositiveSmallIntegerField(default=100)
    public = models.BooleanField(
        default=True, help_text=_("Whether or not this viewport is visible to students")
    )

    tasks = models.ManyToManyField(Task, blank=True)

    objects = LedgerViewportManager()

    class Meta:
        ordering = ("ordering", "name")
        base_manager_name = "objects"

    def __str__(self):
        return self.name


############################################################################


@python_2_unicode_compatible
class Role(GradebookBaseModel):
    """
    A person with a designated role in a viewport.
    """

    CHOICES = (
        ("su", _("Superuser")),
        ("co", _("Course Coordinator")),
        ("in", _("Instructor")),
        ("ta", _("Teaching Assistant")),
        ("mk", _("Marker")),
        ("ld", _("Lab Demonstrator")),
        ("ob", _("Observer")),
        ("st", _("Student")),
    )

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="gradebook_role"
    )
    role = models.CharField(max_length=2, default="st", choices=CHOICES)
    viewport = models.ForeignKey(LedgerViewport, on_delete=models.CASCADE)
    dtstart = models.DateTimeField(
        verbose_name=_("start"), help_text="When the role begins"
    )
    dtend = models.DateTimeField(
        verbose_name=_("end"), help_text="When the role finishes"
    )

    objects = RoleManager()

    class Meta:
        unique_together = (("person", "viewport"),)
        ordering = ("viewport", "person")
        base_manager_name = "objects"

    def __str__(self):
        return "{} - {} for {}".format(
            self.person, self.get_role_display(), self.viewport
        )

    @property
    def label(self):
        return self.get_role_display().lower()

    def upgrade_role(self, new_role_type):
        """
        Potentially upgrade this role.
        Return ``True`` if the new role type is being used, ``False`` otherwise.
        (``True`` indicates a save would be required.)
        """
        code_list = list(zip(*self.CHOICES))[0]
        if code_list.index(new_role_type) < code_list.index(self.role):
            self.role = new_role_type
            return True
        else:
            return False


############################################################################


@python_2_unicode_compatible
class Response(GradebookBaseModel):
    """
    A student response that has not yet been scored.
    """

    student_id = models.CharField(
        max_length=32, help_text=_("As identified by the response source")
    )
    score = models.CharField(max_length=32)
    response_string = models.CharField(
        max_length=256, help_text=_("As supplied by the response source")
    )
    description = models.CharField(
        max_length=64,
        blank=True,
        help_text=_(
            "A brief indication of what type of response this is (may include task/section hints)"
        ),
    )
    task = models.ForeignKey(
        "gradebook.Task",
        null=True,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
        help_text=_("An associated task, if one can be determined"),
    )
    # NB: viewport is set for responses uploaded to a particular viewport
    #   but course coordinators may upload to all associated viewports,
    #   in which case this will be null.
    viewport = models.ForeignKey(
        "gradebook.LedgerViewport",
        null=True,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
        help_text=_("An associated viewport, if appropriate"),
    )
    scored = models.BooleanField(default=False)

    objects = ResponseManager()

    class Meta:
        base_manager_name = "objects"

    def __str__(self):
        return self.response_string


############################################################################


@python_2_unicode_compatible
class Score(GradebookBaseModel):
    """
    An individual score.
    """

    CALC_INDICATOR = conf.get("calc_indicator")
    NS_INDICATOR = conf.get("no_score_indicator")
    OVERRIDE_INDICATOR = conf.get("override_indicator")
    CALC_SENTINEL = "~"
    PUBLIC_CHOICES = (
        (None, "Use task setting"),
        (False, "Hide from student"),
        (True, "Show to student"),
    )

    value = models.CharField(max_length=32, blank=True)
    old_value = models.CharField(max_length=32, blank=True)
    public = models.NullBooleanField(
        blank=True,
        help_text=_("Whether or not students can see their own score"),
        choices=PUBLIC_CHOICES,
    )
    full_marks = models.CharField(
        max_length=32,
        blank=True,
        help_text=_("Optional, if not set, the task full marks will be used"),
    )
    task = models.ForeignKey(
        "gradebook.Task", on_delete=models.CASCADE, limit_choices_to={"active": True}
    )
    person = models.ForeignKey(
        "people.Person",
        null=True,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
    )
    formula = models.ForeignKey(
        "gradebook.Formula",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
    )
    dependencies = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="reverse_dependencies",
        limit_choices_to={"active": True},
    )
    dependencies_resolved = models.BooleanField(default=False)

    objects = ScoreManager()

    class Meta:
        unique_together = (("task", "person"),)
        ordering = ("person", "task")
        base_manager_name = "objects"

    def __str__(self):
        if self.value != self.old_value:
            return "{}".format(Score.CALC_INDICATOR)
        return "{}".format("{0}".format(self.value) or Score.NS_INDICATOR)

    def save(self, *args, **kwargs):
        """
        If the formula, or the full_marks has changed; then flag
        for recalculation.
        """
        result = super(Score, self).save(*args, **kwargs)
        update_fields = kwargs.get("update_fields", None)
        if update_fields is None:
            # note: no change in kwargs
            update_fields = ["formula", "full_marks"]

        if "formula" in update_fields:
            self.dependencies_resolved = False
        if "formula" in update_fields or "full_marks" in update_fields:
            if "old_value" not in update_fields:
                self.old_value = "{}".format(self) + Score.CALC_SENTINEL
        if self.value != self.old_value:
            self.dirty_reverse_deps()
        return result

    def dirty_reverse_deps(self):
        """
        This score has been changed -- any reverse dependencies on this
        score will also change!

        Note that this is recursive.
        """

        def _rdep_pks(score):
            result = []
            result.extend(score.reverse_dependencies.values_list("pk", flat=True))
            for s in score.reverse_dependencies.all():
                result.extend(_rdep_pks(s))
            return result

        rdeps_list = _rdep_pks(self)
        if rdeps_list:
            Score.objects.filter(pk__in=rdeps_list).update(
                old_value=ScoreQuerySet.CALC_SENTINEL
            )

    dirty_reverse_deps.alters_data = True
    dirty_reverse_deps.do_not_call_in_templates = True

    def is_public(self):
        if self.public is not None:
            return self.public
        return self.task.is_public()

    def get_full_marks(self):
        return self.full_marks or self.task.full_marks

    def get_formula(self):
        """
        Provided so that scores and tasks can be treated symmetrically
        WRT formula (cascade formulas).
        """
        return self.formula or self.task.formula

    def get_ledger_id(self):
        """
        This is used by the utils/depgraph.py module.
        """
        return self.task.ledger_id

    def update_deps_from_task(self):
        """
        Update this scores dependencies from the corresponding task.
        """
        if self.formula:
            # don't do it!
            return
        task_id_list = self.task.dependencies.active().values_list("id", flat=True)
        self.dependencies.set(
            Score.objects.filter(
                person_id=self.person_id, task_id__in=task_id_list
            ).values_list("id", flat=True)
        )

    update_deps_from_task.alters_data = True
    update_deps_from_task.do_not_call_in_templates = True

    def resolve_dependencies(self, verbosity=0):
        """
        Triggered when **something something**.
        This method should never, ever be called during the regular
        request-response cycle, as it can be very time consuming
        (for an entire task).
        """
        formula = self.get_formula()
        if formula is None:
            self.dependencies.clear()
        else:
            from .gb2.utils.depgraph import update_instance

            update_instance(self, verbosity=verbosity)

        self.dependencies_resolved = True
        self.save(update_fields=["dependencies_resolved"])

    resolve_dependencies.alters_data = True
    resolve_dependencies.do_not_call_in_templates = True

    def calculate(self, verbosity=0, cascade=True, commit=True):
        """
        Triggered when ``self.value != self.old_value``.
        This method should never, ever be called during the regular
        request-response cycle, as it can be very time consuming.
        """
        updated = False
        if self.get_formula() is None:
            # this score has no formula
            updated = True
        else:
            # this score *has* a formula
            try:
                value = formula_registry.calculate(self)
                if verbosity > 3:
                    print(
                        'Score#{self.pk} got calculate value "{value}"'.format(
                            self=self, value=value
                        )
                    )
            except NoValueChange:
                pass
            else:
                if value != self.value:
                    self.value = value
                    updated = True

        self.old_value = self.value
        if verbosity > 2:
            print('Score "{self.task.slug}#{self.pk}" = {self.value}'.format(self=self))
        if commit:
            self.save(update_fields=["value", "old_value"])

        if updated and cascade:
            from .gb2.utils.topsort import topsort

            cascade_list = topsort(self)
            top = cascade_list.pop(0)  # the current score -- already changed/calculated
            assert (
                top == self
            ), "TopSort returned something totally unexpected -- first element is not reference object"
            for score in cascade_list:
                if verbosity > 2:
                    print(
                        'Next score is cascaded from change in score "{self.task.slug}#{self.pk}"'.format(
                            self=self
                        )
                    )
                score.calculate(verbosity=verbosity, cascade=False, commit=commit)
        return self.value

    calculate.alters_data = True
    calculate.do_not_call_in_templates = True

    # TODO: Consider an is_valid() method, which cross checks the
    #   formula & dependencies of this score instance.
    #   (And gives information about what's wrong, if anything.)


############################################################################


@python_2_unicode_compatible
class Formula(GradebookBaseModel):
    """
    Encapsulate the logic for a computation/calculated score.
    """

    type = models.CharField(max_length=4, choices=formula_registry.choices)
    short_description = models.CharField(
        max_length=128, blank=True, help_text=_("A short, human readable description")
    )
    applies_to = models.SlugField(
        blank=True,
        default="-dont-show-",
        help_text=_("A slug for which this formula may apply, leave blank for any"),
    )
    args = JSONField(load_kwargs={"object_pairs_hook": OrderedDict}, blank=True)
    digest = models.SlugField(max_length=64, blank=True)

    objects = FormulaManager()

    class Meta:
        base_manager_name = "objects"

    def __str__(self):
        if self.short_description:
            if self.applies_to:
                return "{self.applies_to}: {self.short_description}".format(self=self)
            return self.short_description
        return self.get_type_display() + " - " + self.digest

    def get_type_display(self):
        """
        DCG/2015-Jul-29 for whatever reason, this is not happening
        using the automatic Django majick.  Maybe b/c choices
        is dynamic?
        """
        d = dict(formula_registry.choices)
        return d.get(self.type, None)

    @staticmethod
    def get_digest(args):
        # remember: hashes work on bytes, not characters.
        return hashlib.sha224(json.dumps(args).encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.digest = self.get_digest(self.args)
        return super(Formula, self).save(*args, **kwargs)

    def clean_fields(self, *args, **kwargs):
        """
        NB: Called in ModelForms only.
        """
        errors = super(Formula, self).clean_fields(*args, **kwargs)
        exclude = kwargs.get("exclude", None)
        if exclude is not None and "args" in exclude:
            if not formula_registry.is_valid(self):
                if errors is None:
                    errors = {}
                errors["args"] = _(
                    "Inappropriate or invalid args for this formula type."
                )
        if errors:
            raise ValidationError(errors)
        return


############################################################################
