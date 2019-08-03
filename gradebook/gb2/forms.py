"""
Gradebook gb2 forms.
"""
#################################################################
from __future__ import print_function, unicode_literals

import json
from datetime import datetime

import spreadsheet
from datetimepicker.widgets import DateTimePicker
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils.html import mark_safe
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django_select2.forms import ModelSelect2Widget
from people.models import Person
from students.forms import ClasslistUploadForm as StudentClasslistUploadForm

from ..models import (
    Category,
    Formula,
    Ledger,
    LedgerViewport,
    Response,
    Role,
    Score,
    Task,
)
from ..utils import bubblesheet
from ..utils import iclicker as iclicker_csv
from ..utils import iclicker_xml, marks_upload, unslugify
from .formulalib import formula_registry
from .utils.export import score_data as export_score_data
from .validators import validate_spreadsheet

#################################################################

SCORE_SIZE = 6

#################################################################

if not hasattr(DateTimePicker, "_format_value"):
    DateTimePicker._format_value = DateTimePicker.format_value

#################################################################


class ScoreForm(forms.ModelForm):
    """
    Score Edit form.
    """

    class Meta:
        model = Score
        fields = ("value",)
        widgets = {"value": forms.widgets.TextInput(attrs={"size": SCORE_SIZE})}

    # dynamic/hybrid form.  If the instance.score.formula exists,
    #   provide an ``override`` checkbox.
    # ``override`` when set, sets the instance.formula to NOOP
    # When ``instance.formula`` is set the default value of
    #   ``override`` is True (otherwise False).

    def __init__(self, *args, **kwargs):
        super(ScoreForm, self).__init__(*args, **kwargs)
        # add in override form field, and set default value.
        if self.instance.task is not None and self.instance.task.formula is not None:
            self.fields["override"] = forms.BooleanField(required=False)
            if self.instance.formula:
                self.fields["override"].initial = True

    def save(self, *args, **kwargs):
        # pull out override form field, and manipulate
        # instance.formula appropriately
        override_field = self.fields.pop("override", None)
        if override_field is not None:
            override = self.cleaned_data.pop("override", False)
            if override:
                self.instance.formula = self.get_override_formula()
                self.instance.old_value = self.cleaned_data["value"]
            else:
                self.instance.formula = None
        return super(ScoreForm, self).save(*args, **kwargs)

    def get_override_formula(self):
        """
        Only called during saving... use a class variable to cache.
        """
        if hasattr(ScoreForm, "_override_formula"):
            return ScoreForm._override_formula
        formula, flag = Formula.objects.get_or_create_by_typeargs(type="noop", args={})
        ScoreForm._override_formula = formula
        return ScoreForm._override_formula


#################################################################


class FormulaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.short_description


#################################################################


class TaskForm(forms.ModelForm):
    formula = FormulaChoiceField(queryset=Formula.objects.none(), required=False)
    """
    Task edit form
    TODO: Figure out superuser vs non-actions.
    """

    class Meta:
        model = Task
        fields = ("category", "name", "full_marks", "public", "formula")
        widgets = {"full_marks": forms.widgets.TextInput(attrs={"size": SCORE_SIZE})}

    class Media:
        css = {"all": ("css/forms.css",)}

    # dynamic/hybrid form.
    # - provide checkboxes for viewports
    # - provide custom options for formula based on name/slug of this task.

    def _setup_formula_field(self):
        if self.instance.slug:
            formula_qs = Formula.objects.active().get_for_task(self.instance)
        else:
            formula_qs = Formula.objects.none()
        if not formula_qs.exists():
            self.fields.pop("formula")
        else:
            self.fields["formula"].queryset = formula_qs

    def _setup_viewport_checkboxes(self):
        if self.instance.pk:
            self._all_viewports = self.instance.ledger.ledgerviewport_set.active()
            self._task_viewports = self.instance.ledgerviewport_set.active()
        else:
            self._all_viewports = LedgerViewport.objects.none()
            self._task_viewports = LedgerViewport.objects.none()

        single_viewport = self._all_viewports.count() == 1
        if single_viewport:
            self._task_viewports = self._all_viewports
        elif self.instance.pk:
            self.fields["_select_all"] = forms.BooleanField(
                required=False,
                label="-- Select all --",
                initial=self._task_viewports.count() == self._all_viewports.count(),
            )

        for v in self._all_viewports:
            self.fields["viewport:" + v.slug] = forms.BooleanField(
                required=False,
                label=v.name,
                initial=v in self._task_viewports,
                widget=forms.CheckboxInput(attrs={"class": "viewport-checkbox"}),
            )
            if single_viewport:
                self.fields["viewport:" + v.slug].widget = forms.HiddenInput()

    def __init__(self, *args, **kwargs):
        result = super(TaskForm, self).__init__(*args, **kwargs)
        self._setup_formula_field()
        self._setup_viewport_checkboxes()
        # if self.instance and self.instance.pk and self.instance.category.name.lower().endswith(' session'):
        #     self.fields['category'].queryset = self.fields['category'].queryset.filter(pk=self.instance.category.pk)
        # else:
        #     self.fields['category'].queryset = self.fields['category'].queryset.exclude(name__iendswith=' session')
        return result

    def clean(self, *args, **kwargs):
        result = super().clean(*args, **kwargs)
        formula = self.cleaned_data.get("formula", None)
        category = self.cleaned_data.get("category")
        if formula is not None:
            # check category
            src_category = formula.args.get("src_category", None)
            if src_category == category.slug:
                raise forms.ValidationError(
                    "This formula and category combination causes a circular reference."
                )
            # check task dependencies
            src_task = formula.args.get("src_task", None)
            src_tasks = formula.args.get("src_tasks", [])
            weights = formula.args.get("weights", [])
            weight_src_tasks = [e[0] for e in weights]
            src_tasks.extend(weight_src_tasks)
            if src_task is not None:
                src_tasks.append(src_task)
            # this is a bit of a cheat: we only get here during an edit
            # so we know that self.instance will be populated.
            ledger_tasks = set(
                self.instance.ledger.task_set.active().values_list("slug", flat=True)
            )
            src_tasks = set(src_tasks)
            not_found = src_tasks.difference(ledger_tasks)
            if not_found:
                names = ['"{}"'.format(unslugify(e)) for e in not_found]
                if len(names) == 1:
                    msg = 'This formula requires a task named "{}", which does not exist.'.format(
                        names[0]
                    )
                else:
                    name_list = ", ".join(names[:-1]) + ", and " + names[-1]
                    msg = (
                        "This formula requires {} tasks which do not exist: ".format(
                            len(names)
                        )
                        + name_list
                    )
                raise forms.ValidationError(msg)
        return result

    def save(self, *args, **kwargs):
        viewport_keys = [k for k in self.fields.keys() if k.startswith("viewport:")]
        viewport_data = {}
        for k in viewport_keys:
            self.fields.pop(k)
            viewport_data[k] = self.cleaned_data.pop(k)
        result = super(TaskForm, self).save(*args, **kwargs)
        viewport_qs = self.instance.ledger.ledgerviewport_set.active()
        single_viewport = viewport_qs.count() == 1
        if single_viewport:
            viewport = viewport_qs.get()
            viewport.tasks.add(self.instance)
        for k in viewport_keys:
            slug = k.split(":", 1)[1]
            value = viewport_data.get(k, False)
            viewport = self._all_viewports.get(slug=slug)
            if value:
                viewport.tasks.add(self.instance)
            else:
                viewport.tasks.remove(self.instance)
        return result


#################################################################


class ConfirmDuplicateTaskForm(TaskForm):
    force = forms.BooleanField(
        required=False, initial=False, label="Yes, create duplicate task"
    )

    def clean_force(self):
        data = self.cleaned_data["force"]
        if data:
            return data
        else:
            raise forms.ValidationError(
                "Please confirm that this {} should be created".format(
                    ContentType.objects.get_for_model(self.Meta.model)
                )
            )


#################################################################


class AdminCreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = "__all__"


#################################################################


class AdminChangeTaskForm(forms.ModelForm):
    """
    This form exposes the reverse m2m relationship between ledgerviewports and
    tasks.
    """

    viewports = forms.ModelMultipleChoiceField(
        queryset=LedgerViewport.objects.none(),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="Viewports", is_stacked=False),
    )

    class Meta:
        model = Task
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AdminChangeTaskForm, self).__init__(*args, **kwargs)

        if self.instance:
            self.fields[
                "viewports"
            ].queryset = self.instance.ledger.ledgerviewport_set.all()
        if self.instance and self.instance.pk:
            self.fields["viewports"].initial = self.instance.ledgerviewport_set.all()

    def save(self, commit=True):
        task = super(AdminChangeTaskForm, self).save(commit=False)
        if commit:
            task.save()
        if task.pk:
            task.ledgerviewport_set.set(self.cleaned_data["viewports"])
            self.save_m2m()
        return task


#################################################################


class AdminFormulaForm(forms.ModelForm):
    type = forms.ChoiceField(choices=[])

    class Meta:
        model = Formula
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        result = super(AdminFormulaForm, self).__init__(*args, **kwargs)
        type_field = self.fields.get("type", None)
        if type_field is not None:
            self.fields["type"].choices = list(formula_registry.choices)
        applies_to_field = self.fields.get("applies_to", None)
        if applies_to_field and not applies_to_field.initial:
            self.fields["applies_to"].initial = "-none"
        return result


#################################################################


class BulkResponseForm(forms.Form):
    """
    Upload a series of Response objects from a spreadsheet or data file.
    NB: This form must have ``enctype="multipart/form-data"`` in the HTML
    form element.
    """

    description = None
    file = forms.FileField(label="File to Upload")

    class Media:
        css = {"all": ("css/forms.css",)}

    def get_description(self, viewport, data):
        """
        Supply a description class attribute or override this method.
        """
        desc = self.description
        if desc is None:
            raise ImproperlyConfigured(
                "BulkResponseForm subclasses must provide a description attribute."
            )
        return desc

    def get_task(self, viewport, role, data):
        """
        **Override this method in sub-classes.**
        ``viewport`` is the viewport that is currently selected in the gradebook.
        ``role`` is the current role of the uploader in the given ``viewport``.
        ``data`` is the file field.
        """
        raise ImproperlyConfigured(
            "BulkResponseForm subclasses must implement get_task()"
        )

    def file_to_response_data(self, viewport, role, data):
        """
        **Override this method in sub-classes.**
        Use to convert the file into a series of response data dictionaries.
        ``viewport`` is the viewport that is currently selected in the gradebook.
        ``role`` is the current role of the uploader in the given ``viewport``.
        ``data`` is a file field.

        This method must return a list of Response data dictionaries,
        i.e., ``Response(**kwargs)`` should be valid for each element
        of the results.

        At a minimum, this should set the ``student_id``, ``score``, and
        ``response_string`` values.
        """
        raise ImproperlyConfigured(
            "BulkResponseForm subclasses must implement file_to_response_data()"
        )

    def build_responses(self, viewport, role):
        """
        Use to build the responses.
        """
        results = []
        data = self.cleaned_data["file"]
        if not data:
            keys = self.cleaned_data.keys()
            raise RuntimeError("This form is not bound to an uploaded file.")

        task_list = []
        for record in self.file_to_response_data(viewport, role, data):
            if "task" not in record:
                record["task"] = self.get_task(viewport, role, data)
            if "description" not in record:
                record["description"] = self.get_description(viewport, data)
            if record["task"] not in task_list:
                task_list.append(record["task"])
            results.append(record)

        return [Response(**r) for r in results], task_list

    def bulk_create(self, viewport, role):
        """
        Call only when ``form.is_valid()``.
        Call as ``form.bulk_create(section, role)``.
        """
        response_list, task_list = self.build_responses(viewport, role)
        # clear any old responses first:
        # NOTE: This only works when the task is given; but the task
        #   can be None also.
        old_responses = Response.objects.filter(task__in=task_list)
        old_responses.delete()
        # create the new response objects:
        result = Response.objects.bulk_create(response_list)
        # mark all scores for task for recalculation.
        score_list = Score.objects.filter(task__in=task_list)
        score_list.update_for_recalc()
        return result


#################################################################


class IClickerResponseForm(BulkResponseForm):
    """
    For uploading i>clicker results.
    """

    description = "i>clicker"

    def _format_filename(self, filename):
        filename = filename.lower()
        base, ext = filename.rsplit(".", 1)
        if ext not in ["csv", "xml"]:
            return None, None
        if filename.endswith("[1]." + ext):  # weird MS/FTP fake filesystem stuff.
            filename = filename[:-7] + "." + ext
        try:
            D = datetime.strptime(filename, "l%y%m%d%H%M." + ext)
            name = "i>clicker session " + D.strftime("%Y-%m-%d %H:%M")
            return name, "iclicker"
        except ValueError:
            pass
        if filename.startswith("iclicker_"):
            format = "moodle"
            name = None
            try:
                D = datetime.strptime(
                    filename, "iclicker_gradebookexport_%m%d%y_moodle.csv"
                )
            except ValueError:
                pass
            else:
                name = "i>clicker moodle gradebook " + D.strftime("%Y-%m-%d")
            if name is None:
                parts = filename.split("-")
                if len(parts) == 2:
                    s = parts[-1]
                    try:
                        D = datetime.strptime(s, "%m_%d_%y.csv")
                    except ValueError:
                        pass
                    else:
                        name = "i>clicker moodle session " + D.strftime("%Y-%m-%d")
            if name is not None:
                return name, format
        return None, None

    def _parse_iclicker(self, data):
        if getattr(self, "_parse_complete", False):
            return self._correct_responses, self._results
        # autoselect iclicker_csv or iclicker_xml parse:
        iclicker = None
        base, ext = data.name.lower().rsplit(".", 1)
        if ext == "csv":
            iclicker = iclicker_csv
        if ext == "xml":
            iclicker = iclicker_xml
        if iclicker is None:
            raise RuntimeError("Validation should have failed before this.")
        correct_responses, results = iclicker.parse(data)
        self._correct_responses = correct_responses
        self._results = results
        self._parse_complete = True
        return self._correct_responses, self._results

    def _parse_moodle(self, data):
        if getattr(self, "_parse_complete", False):
            return self._correct_responses, self._results
        # load as a spreadsheet of marks...
        id_field = "student id"
        id_list, taskname_list = marks_upload.probe_file(data)
        if id_field not in id_list:
            raise forms.ValidationError(
                'Unrecognized i>clicker moodle file [no "student id" field]'
            )
        if "total" in taskname_list:
            taskname_list.pop(taskname_list.index("total"))
        data.seek(0)
        score_data = marks_upload._load_scores(
            data, id_field, taskname_list, duplicate_action="zero score"
        )
        self._correct_responses = None
        self._results = score_data
        self._parse_complete = True
        return self._correct_responses, self._results

    def get_description(self, viewport, data):
        return self._format_filename(data.name)[0]

    def get_task(self, viewport, role, data, name=None, format=None, full_marks=None):
        """
        ``viewport`` is the viewport that is currently selected in the gradebook.
        ``role`` is the current role of the uploader in the given ``viewport``.
        ``data`` is the file field.
        """
        if name is None:
            name, format = self._format_filename(data.name)
        elif format is None:
            raise RuntimeError("If name is given, format must also be given")
        if format == "moodle" and name is None:
            raise RuntimeError("Moodle needs to specify task names")

        if hasattr(self, "_task"):
            if format == "iclicker":
                return self._task
            if format == "moodle" and name in self._task:
                return self._task[name]
        elif format == "moodle":
            self._task = {}

        slug = slugify(name)
        category, cflag = Category.objects.get_or_create(
            name="i>clicker Session", slug="iclicker-session"
        )
        if format == "iclicker":
            formula, fflag = Formula.objects.get_or_create_by_typeargs("icli", {})
        if format == "moodle":
            formula, fflag = Formula.objects.get_or_create_by_typeargs("iclm", {})

        if full_marks is None and format == "iclicker":
            full_marks = max([s for r, s in self._parse(data)[1].values()])

        # CAREFUL: i-clicker tasks are always unique to a particular viewport;
        #   so names can potentially collide over the entire ledger; but
        #   still need unique tasks...

        # Fake a modified get_or_create...
        qs = viewport.tasks.all().filter(name=name)
        if qs:
            task = qs[0]
            tflag = False
        else:
            task = Task.objects.create(
                name=name,
                ledger=viewport.ledger,
                category=category,
                formula=formula,
                full_marks=full_marks,
            )
            tflag = True
            viewport.tasks.add(task)

        if not tflag:
            # task already existed...
            # update other task values:
            update_fields = []
            if not task.active:
                task.active = True
                update_fields.append("active")
            if task.category != category:
                task.category = category
                update_fields.append("category")
            if task.formula != formula:
                task.formula = formula
                update_fields.append("formula")
            if task.full_marks != full_marks:
                task.full_marks = full_marks
                update_fields.append("full_marks")
            if update_fields:
                task.save(update_fields=update_fields)

            # remove existing response set.
            task.response_set.all().delete()
            # We can get away this because this code block only runs once
            #   for the lifetime of the form; afterwards it uses
            #   the _task cached attribute.
        if format == "iclicker":
            self._task = task
        if format == "moodle":
            self._task[name] = task
        return task

    def iclicker_to_response_data(self, viewport, role, correct_responses, results):
        response_data = []
        for iclicker_id, values in results.items():
            responses, score = values
            response_data.append(
                {
                    "student_id": iclicker_id.lower(),
                    "response_string": "".join([e or "." for e in responses]),
                    "score": score,
                }
            )
        return response_data

    def moodle_to_response_data(self, viewport, role, correct_responses, results):

        assert correct_responses is None, "We don't have access to this for moodle"
        taskname_list = list(next(iter(results.values())).keys())
        totals = {
            name: max((v.get(name) for v in results.values())) for name in taskname_list
        }
        response_data = []

        for student_id in results:
            for taskname in results[student_id]:
                response_data.append(
                    {
                        "student_id": student_id.lower(),
                        "response_string": "",
                        "score": results[student_id][taskname],
                        "task": self.get_task(
                            viewport,
                            role,
                            data=None,
                            name=taskname,
                            format="moodle",
                            full_marks=totals[taskname],
                        ),
                    }
                )
        return response_data

    def file_to_response_data(self, viewport, role, data):
        """
        Use to convert the file into a series of response data dictionaries.

        ``viewport`` is the viewport that is currently selected in the gradebook.
        ``role`` is the current role of the uploader in the given ``viewport``.
        ``data`` is the file field.

        This method must return a list of Response data dictionaries,
        i.e., ``Response(**kwargs)`` should be valid for each element
        of the results.

        At a minimum, this should set the ``student_id``, ``score``, and
        ``response_string`` values.
        """
        response_data = []
        correct_responses, results, format = self._parse(data)
        get_response_data = getattr(self, format + "_to_response_data")
        return get_response_data(viewport, role, correct_responses, results)

    def _parse(self, *args, **kwargs):
        # parse dispatcher
        data = self.cleaned_data["file"]
        if not data:
            raise forms.ValidationError(
                _("Uploading a file is required"), code="missing file"
            )

        name, format = self._format_filename(data.name)
        if name is None:
            raise forms.ValidationError(
                _("Not a recognized i>clicker data file"), code="invalid file"
            )

        try:
            parser = getattr(self, "_parse_" + format, None)
            if parser is not None:
                parsed_data = parser(data)
            else:
                assert False, "Unimplemented i>clicker data format: {!r}".format(format)
        except (iclicker_csv.ParseError, iclicker_xml.ParseError) as e:
            raise forms.ValidationError(
                _(
                    "There was an error processing the i>clicker data.  (The file may be corrupt.) %(parse_error)s"
                ),
                code="invalid data",
                params={"parse_error": e},
            )
        parsed_data += (format,)
        return parsed_data

    def clean_file(self):
        """
        Make sure the data file is valid.
        """
        self._parse()
        return self.cleaned_data["file"]


#################################################################


class MultisectionMixin(object):
    """
    A form mixin that, when initialized with a course coordinator
    or a super user role, allows operations for all valid sections
    simultaneously.
    """

    def _multisection(self, role, dt=None):
        """
        Activate multisection for the given role. At the given time.
        """
        if dt is None:
            dt = now()
        if role.role == "su":
            self.viewport_qs = role.viewport.ledger.ledgerviewport_set.active()
        elif role.role == "co":
            self.viewport_qs = role.viewport.ledger.ledgerviewport_set.active()
        else:
            self.viewport_qs = LedgerViewport.objects.filter(pk=role.viewport_id)

    def __init__(self, *args, **kwargs):
        self.viewport_qs = None
        self.role = kwargs.pop("role", None)
        self.effective_dt = kwargs.pop("effective_dt", None)
        result = super(MultisectionMixin, self).__init__(*args, **kwargs)
        if self.role is not None:
            self._multisection(self.role, self.effective_dt)


#################################################################


class BubblesheetResponseForm(MultisectionMixin, BulkResponseForm):
    """
    For uploading bubblesheet/scantron results.

    NB: course coordinators need to be able to populate in all sections
        they coordinate.
    """

    description = "bubblesheet"
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(), help_text=_("Where the results will be saved. ")
    )

    def __init__(self, *args, **kwargs):
        """
        Special handling for task selection.
        """
        self.viewport = kwargs.pop("task_viewport", None)
        if self.viewport is None:
            raise ImproperlyConfigured(
                'This form class requires a "task_viewport" keyword argument.'
            )
        result = super(BubblesheetResponseForm, self).__init__(*args, **kwargs)
        # update queryset
        self.fields["task"].queryset = self.viewport.tasks.active().filter(
            formula__type="bbl"
        )
        if self.role.role in ["su", "co"]:
            self.fields["task"].help_text += "{}".format(
                self.role.get_role_display()
            ) + "{}".format(_(" will save to all appropriate sections."))
        return result

    def _record_to_response(self, record):
        """
        For an individual record, return the response dictionary:
        ``student_id``, ``score``, ``response_string``, ``task``, ``description``

        """
        try:
            stnum = int(record["student_number"])
        except ValueError:
            stnum = record["student_number"]
        # Note the assumption the student_number data is actually numeric
        task = self.cleaned_data["task"]

        if task is None:
            return

        return {
            "student_id": record["student_number"],
            "score": record["score"],
            "response_string": record["responses"],
            "task": task,
            "description": "bubblesheet:{0}".format(self.task_name),
        }

    def _parse(self, data):
        """
        Parse the file, save results.
        """
        if getattr(self, "_parse_complete", False):
            return self._course_info, self._score_records
        #         print("{!r} {!r}".format(data.name, data))
        course_info, score_records = bubblesheet.parse_file(
            data.name, data, verbosity=0, solution=None, check=False
        )
        self._course_info = course_info
        self.course_info_json = json.dumps(course_info)
        self._score_records = score_records
        self._parse_complete = True
        return self._course_info, self._score_records

    def file_to_response_data(self, viewport, role, data):
        """
        Used to convert the file into a series of response data dictionaries.
        ``viewport`` is the viewport that is currently selected in the gradebook.
            -- note that this may be a multi-section form
                (check ``self.viewport_qs``)
        ``role`` is the current role of the uploader in the given ``viewport``.
        ``data`` is a file field.

        This method must return a list of Response data dictionaries,
        i.e., ``Response(**kwargs)`` should be valid for each element
        of the results.

        At a minimum, this should set the ``student_id``, ``score``, and
        ``response_string`` values.
        This should return ``task`` also. (BubblesheetResponseForm)
        """
        self.task_name = self.cleaned_data["task"].name
        data = self.cleaned_data["file"]
        course_info, score_records = self._parse(data)
        result = [self._record_to_response(r) for r in score_records]
        return [r for r in result if r is not None]

    def clean_file(self):
        """
        Make sure the data file is valid.
        """
        data = self.cleaned_data["file"]
        if not data:
            raise forms.ValidationError(
                _("Uploading a file is required"), code="missing file"
            )

        try:
            self._parse(data)
        except Exception as e:
            raise forms.ValidationError(
                _("There was an error with your file. %(parse_error)s"),
                code="invalid data",
                params={"parse_error": e},
            )

        return data


#################################################################


class GradebookClasslistUploadForm(StudentClasslistUploadForm):
    """
    Gradebook classlist upload form.
    """

    create_all_students = forms.BooleanField(
        required=False, initial=True, help_text="Even students without a valid username"
    )

    class Media(StudentClasslistUploadForm.Media):
        pass

    def __init__(self, *args, **kwargs):
        viewport = kwargs.pop("viewport", None)
        if viewport is not None:
            override_values = kwargs.pop("override_values", {})
            override_values["viewport"] = viewport
            kwargs["override_values"] = override_values
        value = super(GradebookClasslistUploadForm, self).__init__(*args, **kwargs)
        del self.fields["section"]
        self._section = None
        return value

    def clean(self, *args, **kwargs):
        section = self.get_section()
        if section is None:
            raise forms.ValidationError(
                _("Could not determine section for student registration"),
                code="no section",
            )
        self.override_values["section"] = section
        return super(GradebookClasslistUploadForm, self).clean(*args, **kwargs)

    def clean_file(self):
        """
        Make sure the data file is valid.
        (This should be the default, not sure why this is not getting caught.
        """
        data = self.cleaned_data["classlist_file"]
        if not data:
            raise forms.ValidationError(
                _("Uploading a file is required"), code="missing file"
            )

        return data

    def get_section(self):
        """
        Here we need to map the viewport back to a section;
        """
        if self._section is None:
            # This will only work int the common case; however it's
            #   enough to get started.
            # Generally; we may need some kind of logic hook to go
            #   ledger -> section; however this could go very strange
            #   in e.g., crosslisted courses.  May need to override
            #   save() and just do our own thing with Roles;
            #   rather than relying on signals.
            from classes.models import Section

            try:
                self._section = Section.objects.get(
                    slug=self.override_values["viewport"].slug
                )
            except Section.DoesNotExist:
                pass

        if self._section is None:
            # This is an attempt to cover the non-common case,
            # specifically cross-listed courses.
            viewport_slug = self.override_values["viewport"].slug
            # get section from the classlist file.
            fileobj = self.cleaned_data.get("classlist_file", None)
            from students.utils.aurora2 import read_classlist

            section_qs, student_list = read_classlist(fileobj)
            fileobj.seek(0)  # reset read ptr
            # relies on slug format ending with -term-year as per sections
            viewport_termslug = "-" + "-".join(viewport_slug.rsplit("-", 2)[-2:])
            section_qs = section_qs.filter(slug__iendswith=viewport_termslug)
            for section in section_qs:
                if section.course.slug in viewport_slug:
                    self._section = section
                    # also need to inject this section for the classlist

                    break

        return self._section


#################################################################


class SpreadsheetExportForm(forms.Form):
    """
    Form for downloading a spreadsheet of marks for a single section.
    """

    style = forms.ChoiceField(
        choices=(("std", _("Standard")), ("d2l", _("Desire2Learn"))),
        help_text=_("Select the style of the resulting spreadsheet"),
    )
    good_standing = forms.BooleanField(
        initial=True,
        required=False,
        help_text=_("Download only students in good standing"),
    )

    # Format?
    # TODO: Consider allowing the choice of which tasks to download.

    class Media:
        css = {"all": ("css/forms.css",)}

    def __init__(self, *args, **kwargs):
        self.viewport = kwargs.pop("viewport", None)
        value = super(SpreadsheetExportForm, self).__init__(*args, **kwargs)
        return value

    def clean(self, *args, **kwargs):
        if self.viewport is None:
            raise forms.ValidationError(
                _("There is no selected viewport"), code="invalid usage"
            )
        return super(SpreadsheetExportForm, self).clean(*args, **kwargs)

    def response_data(self):
        """
        Called only after form.is_valid() by views.
        Returns a format/data pair.
        """
        style = self.cleaned_data["style"]
        good_standing = self.cleaned_data["good_standing"]
        task_list = None
        format = "csv"

        # this is the 'std' style
        streg_pre_fields = None
        streg_post_fields = None
        task_label = None

        if style == "d2l":
            streg_pre_fields = [
                (
                    "OrgDefinedId",
                    lambda r: "#00{}".format(r.person.student.student_number),
                ),
                ("Username", lambda r: r.person.username),
            ]
            streg_post_fields = [("End-of-Line Indicator", lambda r: "#")]

            def task_label(t):
                bad_d2l_chars = "<>"
                bad_d2l_replace = "-"
                if t.category.slug == "letter-grade":
                    return "Final Adjusted Grade"
                name = t.name
                for c in bad_d2l_chars:
                    name = name.replace(c, bad_d2l_replace)
                return name + " Points Grade"

        data = export_score_data(
            self.viewport,
            good_standing=good_standing,
            task_label=task_label,
            task_list=task_list,
            streg_pre_fields=streg_pre_fields,
            streg_post_fields=streg_post_fields,
        )
        return format, spreadsheet.sheetWriter(data, format)


#################################################################


class LedgerViewportForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(LedgerViewportForm, self).__init__(*args, **kwargs)
        if "instance" in kwargs:
            qs = Task.objects.filter(ledger=kwargs["instance"].ledger)
        else:
            qs = Task.objects.none()
        self.fields["tasks"].queryset = qs


#################################################################


class LedgerAccessForm(forms.ModelForm):
    class Meta:
        model = Ledger
        fields = []


#################################################################


class LedgerViewportAccessForm(forms.ModelForm):
    name = forms.CharField(disabled=True)

    class Meta:
        model = LedgerViewport
        fields = ["public", "name"]

    class Media:
        css = {"all": (staticfiles_storage.url("css/forms.css"),)}
        js = (staticfiles_storage.url("js/jquery.formset.js"),)


#################################################################


def get_ledgerviewport_access_formset(
    form=LedgerViewportAccessForm, formset=forms.BaseInlineFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    return inlineformset_factory(Ledger, LedgerViewport, form, formset, **kwargs)


#################################################################


class RoleFormMixin(object):
    def __init__(self, *args, **kwargs):
        if "editable_roles" in kwargs:
            editable_roles = kwargs.pop("editable_roles")
        else:
            editable_roles = [(c, d) for c, d in Roles.CHOICES][1:]
        result = super(RoleFormMixin, self).__init__(*args, **kwargs)
        if "role" in self.fields:
            choices = self.fields["role"].choices
            restricted_choices = [(c, d) for c, d in choices if c in editable_roles]
            self.fields["role"].choices = restricted_choices
            self.fields["role"].initial = "mk"
        return result


#################################################################


class PersonSelect2Widget(ModelSelect2Widget):
    model = Person
    queryset = Person.objects.filter(active=True, username__isnull=False).exclude(
        username=""
    )
    search_fields = [
        "cn__icontains",
        "username__icontains",
        "emailaddress__address__icontains",
    ]

    def label_from_instance(self, obj):
        if obj.username:
            return "{obj.cn} [{obj.username}]".format(obj=obj)
        return str(obj)


class RoleCreateForm(RoleFormMixin, forms.ModelForm):
    class Meta:
        model = Role
        fields = ["person", "role", "dtstart", "dtend"]
        widgets = {
            "dtstart": DateTimePicker(options={"format": "%Y-%m-%d %H:%M"}),
            "dtend": DateTimePicker(options={"format": "%Y-%m-%d %H:%M"}),
            "person": PersonSelect2Widget(
                attrs={"style": "width:300px;", "data-minimum-input-length": 3}
            ),
        }

    class Media:
        css = {"all": (staticfiles_storage.url("css/forms.css"),)}


#################################################################


class RoleUpdateForm(RoleFormMixin, forms.ModelForm):
    class Meta:
        model = Role
        fields = ["role", "dtstart", "dtend"]
        widgets = {
            "dtstart": DateTimePicker(options={"format": "%Y-%m-%d %H:%M"}),
            "dtend": DateTimePicker(options={"format": "%Y-%m-%d %H:%M"}),
        }

    class Media:
        css = {"all": (staticfiles_storage.url("css/forms.css"),)}


#################################################################


class StudentSearchForm(forms.Form):
    search = forms.CharField(
        required=True, help_text="Student number, name or partial name, email address"
    )

    class Media:
        css = {"all": ("css/forms.css",)}


#################################################################


class MarksUploadFileForm(forms.Form):
    """
    """

    file = forms.FileField(label="File to Upload", validators=[validate_spreadsheet])

    class Media:
        css = {"all": ("css/forms.css",)}


#################################################################


class MarksUploadColumnSelectForm(forms.Form):
    class Media:
        css = {"all": ("css/forms.css",)}

    def augment_fields(self, id_list, task_list):
        self.task_list = task_list
        id_choices = zip(id_list, id_list)
        self.fields["id_field"] = forms.ChoiceField(
            choices=id_choices, label="ID Field"
        )
        for f in task_list:
            self.fields["save:" + f] = forms.BooleanField(
                label="Save: " + f, required=False, initial=False
            )

    def clean(self, *args, **kwargs):
        result = super().clean(*args, **kwargs)
        if not any([self.cleaned_data["save:" + f] for f in self.task_list]):
            raise forms.ValidationError(
                "You need to select at least one column to save"
            )
        return result


#################################################################


class MarksUploadConfirmActionsForm(forms.Form):
    ignore_unknown_ids = forms.BooleanField(
        required=False, initial=True, label=_("Ignore unknown IDs")
    )

    class Media:
        css = {"all": ("css/forms.css",)}

    def _column_choices(self, viewport, name, can_create):
        ledger_match, viewport_match = marks_upload.task_name_search(
            viewport, name, "search", can_create
        )
        options = [("no_save", "Do not save")]
        initial = "no_save"
        if ledger_match:
            if viewport_match:
                options.append(("update", "Update existing task"))
                initial = "update"
            else:
                if can_create:
                    options.append(("create", "Create"))
                options.append(
                    ("link_update", "Link existing task to this section and update")
                )
                initial = "link_update"
        else:
            if can_create:
                options.append(("create", "Create"))
                initial = "create"
            else:
                initial = "no_save"
        return initial, options

    def augment_fields(self, viewport, column_list, can_create):
        for f in column_list:
            initial, choices = self._column_choices(viewport, f, can_create)
            self.fields["action:" + f] = forms.ChoiceField(
                label=f, choices=choices, required=True, initial=initial
            )


#################################################################


class MarksUploadCoordinatorForm(forms.Form):
    class Media:
        css = {"all": ("css/forms.css",)}

    all_viewports = forms.BooleanField(
        required=False, initial=False, label=_("Upload to all sections")
    )


#################################################################
