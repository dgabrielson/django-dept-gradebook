"""
Gradebook 2 views.
"""
################################################################
from __future__ import print_function, unicode_literals

import base64
import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from extra_views import ModelFormSetView
from formtools.wizard.views import SessionWizardView
from people.models import Person

from .. import conf
from ..models import Formula, Ledger, LedgerViewport, Role, Score, Task
from ..utils import marks_upload, start_end, statistics
from . import forms

#######################################################################


class LoginRequiredMixin(object):
    """
    View mixin which requires that the user is authenticated.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


#######################################################################


class GradebookAuthMixin(LoginRequiredMixin):
    """
    View mixin which requires that the user is authenticated, also adds
    some auth related variables to the context.
    """

    def _set_person(self):
        """
        Set self.person and self.roles.
        """
        if not hasattr(self, "person"):
            try:
                self.person = Person.objects.get_by_user(self.request.user)
            except Person.DoesNotExist:
                self.person = None

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with the person and their roles.
        """
        context = super(GradebookAuthMixin, self).get_context_data(*args, **kwargs)
        self._set_person()
        context["person"] = self.person
        return context


################################################################


class NamedViewMixin(object):
    """
    Primitive mixin for all gradebook views.
    """

    url_name = None
    url_params = None


################################################################


class ViewClassMixin(object):
    """
    Expose view classes in template context.
    Use this for checking permissions and getting view names.
    E.g., ``View.view_name`` and ``View.role_restrictions``.
    """

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with available sections.
        """
        context = super(ViewClassMixin, self).get_context_data(*args, **kwargs)
        for cls in [
            ViewportLanding,
            StudentRegistrationList,
            TaskList,
            TaskDetail,
            AllTaskList,
            AllTaskDetail,
            TaskCreate,
            TaskUpdate,
            TaskDelete,
            ScoreList,
            ScoreEditList,
            StudentScoreList,
            StudentScoreListDetail,
            StudentScoreEditList,
            ScoreDetail,
            IClickerUploadForm,
            ClasslistUploadForm,
            BubblesheetUploadForm,
            SpreadsheetExportFormView,
            SpreadsheetDownloadView,
            MarksUploadWizardView,
            StudentSearchFormView,
            StudentSearchScoreList,
            StudentSearchScoreEditList,
            AccessSettingsView,
            RoleListView,
            RoleCreateView,
            RoleUpdateView,
            RoleDeleteView,
            FormulaList,
        ]:
            context[cls.__name__] = cls
        return context


################################################################


class GradebookBaseMixin(GradebookAuthMixin, NamedViewMixin, ViewClassMixin):
    """
    Base view
    """


################################################################


class AvailableRoleMixin(GradebookBaseMixin):
    """
    View mixin.
    """

    def _set_available_roles(self):
        """
        Set the class attribute.
        """
        if not hasattr(self, "available_role_list"):
            self._set_person()
            self.available_role_list = Role.objects.get_available(
                self.person, now()
            ).order_by("role")

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with available roles.
        """
        context = super(AvailableRoleMixin, self).get_context_data(*args, **kwargs)
        self._set_available_roles()
        context["available_role_list"] = self.available_role_list
        return context


################################################################


class SelectedViewportMixin(AvailableRoleMixin):
    """
    View mixin url patterns should have the 'viewport' named argument (a slug).
    """

    role_restrictions = ["superuser", "course coordinator", "instructor"]

    def _set_requesting_role(self):
        """
        set the class attributes:
            ``self._selected_role``: The actual role object loading this view.
        """
        self._set_available_roles()
        if not hasattr(self, "selected_role"):
            self._selected_role = None
            self._current_role = None
            L = [
                r
                for r in self.available_role_list
                if r.viewport.slug == self.kwargs["viewport"]
            ]
            if len(L) == 1:
                self._selected_role = L[0]

    def get_viewport(self):
        """
        Returns the currently active viewport
        """
        self._set_requesting_role()
        return self._selected_role.viewport

    def get_all_viewports_queryset(self):
        """
        A queryset for all viewports in the ledger this viewport
        belongs in.
        """
        viewport = self.get_viewport()
        qs = viewport.ledger.ledgerviewport_set.active()
        return qs

    def get_requesting_role(self):
        """
        Returns the ``self._selected_role`` attribute
        """
        self._set_requesting_role()
        return self._selected_role

    def get_effective_role(self):
        # print('get_effective_role()')
        if hasattr(self, "_effective_role"):
            # print('\tusing cached value', getattr(self, '_effective_role'))
            return getattr(self, "_effective_role")
        role = self.get_requesting_role()
        # print('\trequesting role:', role)
        if role is not None and role.role == "in":
            # a new copy... so effective != requesting
            # print('\tconsidering instructor role...')
            role = Role(
                active=role.active,
                role=role.role,
                person=role.person,
                viewport=role.viewport,
                dtstart=role.dtstart,
                dtend=role.dtend,
            )
            viewport_qs = self.get_all_viewports_queryset()
            count = viewport_qs.count()
            if count == 1:
                # single viewport promotion
                role.role = "co"
            elif count > 1:
                role_qs = Role.objects.active().filter(viewport__in=viewport_qs)
                in_qs = role_qs.filter(role__in=["co", "in"])
                in_set = set(in_qs.values_list("person_id", flat=True))
                if len(in_set) == 1:
                    in_person_id = in_set.pop()
                    if in_person_id == role.person_id:
                        # solitary instructor promotion
                        role.role = "co"
        self._effective_role = role
        return self._effective_role

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        role = self.get_effective_role()
        if role is None:
            raise PermissionDenied(
                "If you are expecting this to work, your course is probably now finished."
            )
        if role.label not in self.role_restrictions:
            raise PermissionDenied(
                "You do not have access with your current role level [{0}]".format(
                    self._selected_role.label
                )
            )
        # self._set_requesting_role()
        # if self._selected_role is None:
        #     raise PermissionDenied("If you are expecting this to work, your course is probably now finished.")
        # if self._selected_role.label not in self.role_restrictions:
        #     raise PermissionDenied("You do not have access with your current role level [{0}]".format(self._selected_role.label))
        result = super(SelectedViewportMixin, self).dispatch(*args, **kwargs)
        return result

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with available sections.
        """
        context = super(SelectedViewportMixin, self).get_context_data(*args, **kwargs)
        context["selected_role"] = self.get_requesting_role()
        context["effective_role"] = self.get_effective_role()
        context["selected_viewport"] = self.get_viewport()
        context["current_role"] = self.get_effective_role().label
        context["kwargs"] = self.kwargs
        return context

    # Provide standard get_BLAH_queryset() methods, so that we don't have to
    #   continually construct complex queries for individual things...
    def get_student_role_queryset(self):
        """
        Get all student roles for this viewport
        """
        return Role.objects.filter(
            role="st", viewport=self.get_viewport()
        ).select_related("person", "person__student")

    def get_task_queryset(self):
        """
        Get all tasks for this viewport
        """
        viewport = self.get_viewport()
        return viewport.tasks.active().select_related("category")

    def get_score_queryset(self, active_only=False):
        """
        Get all scores for this viewport
        """
        student_role_qs = self.get_student_role_queryset()
        if active_only:
            student_role_qs = student_role_qs.active()
        task_qs = self.get_task_queryset()
        qs = (
            Score.objects.active()
            .filter(
                task__in=task_qs,
                person__in=student_role_qs.values_list("person_id", flat=True),
            )
            .select_related(
                "person",
                "person__student",
                "task",
                "task__category",
                "formula",
                "task__formula",
            )
        )
        return qs


################################################################


class CoordinatorToolsMixin(SelectedViewportMixin):
    """
    Always restricted to course coordinators;

    Note that there is some special additional logic here:
    If an instructor role is present; BUT there is only a single
    viewport in the ledger (or that instructor is the only instructor role
    present for all viewports); then the instructor is equivalent
    to a course coordinator.
    """

    role_restrictions = ["superuser", "course coordinator"]

    def get_student_role_queryset(self):
        """
        Get all student roles for this ledger
        """
        if self.get_effective_role().role == "in":
            return super(CoordinatorToolsMixin, self).get_student_role_queryset()
        return Role.objects.filter(
            role="st", viewport__in=self.get_all_viewports_queryset()
        ).select_related("person", "person__student")

    def get_task_queryset(self):
        """
        Get all tasks for this ledger; optionally restricted by the
        url parameter ``role_viewport_id``.
        """
        if self.get_effective_role().role == "in":
            return super(CoordinatorToolsMixin, self).get_task_queryset()
        viewport = self.get_viewport()
        ledger = viewport.ledger
        qs = ledger.task_set.active()
        role_viewport_id = self.kwargs.get("role_viewport_id", None)
        if role_viewport_id is not None:
            qs = qs.filter(ledgerviewport__id=role_viewport_id)
        return qs.select_related("category")


################################################################


class GradebookMain(AvailableRoleMixin, TemplateView):
    """
    Landing page for the gradebook.
    """

    template_name = "gradebook/main.html"
    url_name = "gradebook2-main"
    url_params = None


################################################################


class ViewportLanding(CoordinatorToolsMixin, TemplateView):
    """
    Landing page for the gradebook.
    """

    template_name = "gradebook/section_landing.html"
    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
        "marker",
        "student",
    ]
    url_name = "gradebook2-viewport-home"
    url_params = ("viewport",)


################################################################


class StudentRegistrationList(SelectedViewportMixin, ListView):
    """
    List of student (role)s in this viewport.
    """

    template_name = "gradebook/studentregistration_list.html"
    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
    ]
    url_name = "gradebook2-studentregistration-list"
    url_params = ("viewport",)

    def get_queryset(self, *args, **kwargs):
        # NB: Student roles exist even in non-public viewports.
        return self.get_student_role_queryset()


################################################################


class TaskMixin(SelectedViewportMixin):
    """
    Mixin for tasks views for this viewport.
    """

    slug_url_kwarg = "task"
    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
    ]

    def get_queryset(self, *args, **kwargs):
        return self.get_task_queryset()


################################################################


class TaskEditMixin(CoordinatorToolsMixin, TaskMixin):
    """
    Task edit mixin
    """

    form_class = forms.TaskForm
    role_restrictions = ["superuser", "course coordinator"]

    def get_success_url(self):
        """success_url for create/update"""
        return reverse(
            TaskUpdate.url_name,
            kwargs={"viewport": self.get_viewport().slug, "task": self.object.slug},
        )


################################################################


class TaskList(TaskMixin, ListView):
    """
    List of tasks for this viewport.
    """

    role_restrictions = TaskMixin.role_restrictions + ["marker"]
    url_name = "gradebook2-task-list"
    url_params = ("viewport",)


################################################################


class AllTaskList(TaskEditMixin, ListView):
    """
    List of tasks for the ledger (coordinator view)
    """

    url_name = "gradebook2-task-list-all"
    url_params = ("viewport",)
    template_name = "gradebook/task_list_edit.html"


################################################################


class TaskDetail(TaskMixin, DetailView):
    """
    Detail for a  tasks for this viewport.
    """

    url_name = "gradebook2-task-detail"
    url_params = ("viewport", "task")


################################################################


class AllTaskDetail(TaskEditMixin, DetailView):
    """
    Detail for tasks for the ledger (coordinator view).
    """

    url_name = "gradebook2-task-detail-all"
    url_params = ("viewport", "task")
    template_name = "gradebook/task_detail_edit.html"


################################################################


class TaskCreate(TaskEditMixin, CreateView):
    """
    Create a new task.
    Includes an "Are you sure you want to do this?" style of form.
        - Based on: https://stackoverflow.com/a/11883268
    """

    template_name = "gradebook/task_create.html"
    url_name = "gradebook2-task-create"
    url_params = ("viewport",)

    def form_valid(self, form):
        # ensure the ledger and viewport is set correctly
        form.instance.ledger = self.get_viewport().ledger
        result = super(TaskCreate, self).form_valid(form)
        messages.success(self.request, _("Task created."), fail_silently=True)
        return result

    def dispatch(self, request, *args, **kwargs):
        self.duplicate = False
        self.task_dups = None
        if request.POST and "name" in request.POST:
            task_name = request.POST["name"]
            task_qs = Task.objects.active().filter(ledger=self.get_viewport().ledger)
            self.task_dups = task_qs.filter(name__iexact=task_name)
            if self.task_dups.exists():
                self.duplicate = True
                if not request.POST.get("force", False):
                    messages.warning(
                        request,
                        _("A task with this name already exists."),
                        fail_silently=True,
                    )
        result = super().dispatch(request, *args, **kwargs)
        return result

    def get_form_class(self):
        cls = forms.ConfirmDuplicateTaskForm if self.duplicate else forms.TaskForm
        return cls

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["duplicate"] = self.duplicate
        context["task_duplicates"] = self.task_dups
        return context


################################################################


class TaskUpdate(TaskEditMixin, UpdateView):
    """
    Update a new task
    """

    template_name = "gradebook/task_update.html"
    url_name = "gradebook2-task-update"
    url_params = ("viewport", "task")

    def form_valid(self, form):
        result = super(TaskUpdate, self).form_valid(form)
        messages.success(self.request, _("Task saved."), fail_silently=True)
        return result


#######################################################################


class TaskDelete(TaskEditMixin, DeleteView):
    """
    Delete an existing Appointment
    """

    url_name = "gradebook2-task-delete"
    url_params = ("viewport", "task")

    def get_success_url(self):
        return reverse(
            AllTaskList.url_name, kwargs={"viewport": self.get_viewport().slug}
        )


################################################################


class ScoreMixin(SelectedViewportMixin):
    """
    Mixin for score views for this section.
    """

    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
        "marker",
    ]

    def get_queryset(self, *args, **kwargs):
        task_slug = self.kwargs.get("task", None)
        qs = self.get_score_queryset().filter(task__slug=task_slug)
        return qs

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with the task slug being viewed.
        TODO: Do we need the whole task?
        """
        context = super(ScoreMixin, self).get_context_data(*args, **kwargs)
        task_slug = self.kwargs.get("task", None)
        context["task"] = task_slug
        if task_slug is not None:
            context["task_object"] = get_object_or_404(
                Task, ledger=self.get_viewport().ledger, slug=task_slug
            )
        # we do not generally raise a 404 b/c some views have several tasks
        #   e.g., StudentScoreList
        context["CALC_INDICATOR"] = Score.CALC_INDICATOR
        context["NS_INDICATOR"] = Score.NS_INDICATOR
        context["OVERRIDE_INDICATOR"] = Score.OVERRIDE_INDICATOR

        stats = statistics.statistics(self.get_queryset())
        if stats:
            context["statistics"] = stats
        histogram = statistics.histogram_img(self.get_queryset(), size="500,350")
        if histogram is not None:
            data, mimetype = histogram
            context["histogram"] = {
                "base64": base64.b64encode(data).decode("utf-8"),
                "mimetype": mimetype,
            }

        return context


################################################################


class ScoreList(ScoreMixin, ListView):
    """
    List of scored tasks for this section.
    """

    url_name = "gradebook2-score-list"
    url_params = ("viewport", "task")


################################################################


class ScoreFormSetMixin(ScoreMixin):
    form_class = forms.ScoreForm
    model = Score
    factory_kwargs = {"extra": 0, "can_order": False, "can_delete": False}
    fields = ["value"]


################################################################


class ScoreEditList(ScoreFormSetMixin, ModelFormSetView):
    """
    Edit all the scores for a task.
    """

    template_name = "gradebook/score_editlist.html"
    url_name = "gradebook2-score-editlist"
    url_params = ("viewport", "task")

    def get_success_url(self):
        return reverse(
            ScoreList.url_name,
            kwargs={
                "viewport": self.get_viewport().slug,
                "task": self.kwargs.get("task", None),
            },
        )


################################################################


class StudentScoreMixin(ScoreMixin):
    """
    List of student scores for this section.
    """

    template_name = "gradebook/studentscore_list.html"
    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
        "marker",
        "student",
    ]

    def _set_student_role(self):
        """
        set the class attribute ``self.student_role`` -- the role of the
        student being looked at.
        """
        requesting_role = self.get_requesting_role()
        if not hasattr(self, "student_role"):
            self.student_role = None
            if requesting_role is None:
                return
            if requesting_role.label == "student":
                # the selected role is this student
                #   i.e., the student is viewing their own scores.
                if requesting_role.active:
                    # It should always be active, but just in case...
                    self.student_role = requesting_role
                return
            # by the PK in the url
            pk = self.kwargs.get("pk", None)
            qs = self.get_student_role_queryset().filter(person_id=pk)
            role_viewport_id = self.kwargs.get("role_viewport_id", None)
            if role_viewport_id is not None:
                qs = qs.filter(viewport_id=role_viewport_id)
            if qs and len(qs) == 1:
                self.student_role = qs.get()

    def get_queryset(self, *args, **kwargs):
        self._set_student_role()
        # this list should only have the good standing students...
        if self.student_role is None:
            raise Http404()
        qs = self.get_score_queryset(active_only=True).filter(
            person_id=self.student_role.person_id
        )
        return qs

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with the student registration being viewed.
        """
        context = super(StudentScoreMixin, self).get_context_data(*args, **kwargs)
        self._set_student_role()
        context["student_role"] = self.student_role
        return context


################################################################


class StudentScoreList(StudentScoreMixin, ListView):
    """
    Scores for a single student.
    This is the view that individual students will use to see *their own*
    scores.
    """

    url_name = "gradebook2-student-score-list"
    url_params = ("viewport",)


################################################################


class StudentScoreListDetail(StudentScoreList):
    """
    Scores for a single student.
    This is the view that *other people* will use to see scores for
    a signle student.
    """

    url_name = "gradebook2-studentscore-list"
    url_params = ("viewport", "pk")
    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
        "marker",
    ]


################################################################


class StudentScoreEditList(StudentScoreMixin, ScoreFormSetMixin, ModelFormSetView):
    """
    Edit all the scores for a student.
    """

    template_name = "gradebook/studentscore_editlist.html"
    url_name = "gradebook2-studentscore-editlist"
    url_params = ("viewport", "pk")

    def get_success_url(self):
        self._set_student_role()
        return reverse(
            StudentScoreListDetail.url_name,
            kwargs={
                "viewport": self.get_viewport().slug,
                "pk": self.student_role.person_id,
            },
        )


################################################################


class ScoreDetail(ScoreMixin, DetailView):
    """
    Detail for a scored tasks for this section.
    """

    url_name = "gradebook2-studentscore-detail"
    url_params = ("viewport", "task", "pk")


################################################################
################################################################
################################################################
################################################################


class BulkResponseFormMixin(object):
    """
    Base class for BulkResponseForm views.
    You will need to specify ``template_name``, ``form_class``, and
    ``response_description`` class attributes.
    """

    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
    ]
    template_name = None
    form_class = None
    response_description = ""

    def get_success_url(self):
        return reverse(
            ViewportLanding.url_name, kwargs={"viewport": self.get_viewport().slug}
        )

    def form_valid(self, form):
        """
        If the form is valid, create responses
        """
        results = form.bulk_create(self.get_viewport(), self.get_effective_role())
        messages.success(
            self.request,
            _("Saved %(count)d %(desc)s responses")
            % {"count": len(results), "desc": self.response_description},
            fail_silently=True,
        )
        return HttpResponseRedirect(self.get_success_url())


################################################################


class BulkResponseFormView(SelectedViewportMixin, BulkResponseFormMixin, FormView):
    """
    For bulk response uploads
    """

    role_restrictions = BulkResponseFormMixin.role_restrictions


################################################################


class CoordinatorBulkResponseFormView(
    CoordinatorToolsMixin, BulkResponseFormMixin, FormView
):
    """
    For bulk response uploads by a coordinator
    """

    role_restrictions = ["superuser", "course coordinator"]


################################################################


class IClickerUploadForm(BulkResponseFormView):
    """
    Upload i>clicker data files to a section.
    """

    template_name = "gradebook/iclicker_upload_form.html"
    form_class = forms.IClickerResponseForm
    response_description = "i>clicker"
    url_name = "gradebook2-iclicker-upload"
    url_params = ("viewport",)


################################################################


class ClasslistUploadForm(SelectedViewportMixin, FormView):
    """
    Upload classlist for to a section.
    """

    role_restrictions = [
        "superuser",
        "course coordinator",
        "instructor",
        "teaching assistant",
    ]
    template_name = "gradebook/classlist_upload_form.html"
    form_class = forms.GradebookClasslistUploadForm
    url_name = "gradebook2-classlist-upload"
    url_params = ("viewport",)

    def get_form_kwargs(self):
        kwargs = super(ClasslistUploadForm, self).get_form_kwargs()
        kwargs["viewport"] = self.get_viewport()
        kwargs["request_user"] = getattr(self.request, "user", None)
        return kwargs

    def get_success_url(self):
        return reverse(
            ViewportLanding.url_name, kwargs={"viewport": self.get_viewport().slug}
        )

    def form_valid(self, form):
        """
        If the form is valid, create responses
        """
        error_list = form.save()
        if error_list:
            messages.warning(
                self.request,
                _("Some students may not be able to login: ")
                + _(", ").join(error_list),
                fail_silently=True,
            )
        else:
            messages.success(
                self.request, _("Classlist uploaded successfully."), fail_silently=True
            )
        return super(ClasslistUploadForm, self).form_valid(form)


################################################################


class SessionFileMixin(object):
    """
    Use this mixin for stashing a generated file in the user session.
    """

    session_prefix = None

    def _get_session_prefix(self):
        if self.session_prefix is None:
            raise ImproperlyConfigured(
                "session_prefix is required for SessionFileMixin"
            )
        return self.session_prefix + "-"

    def _get_session_basekey(self):
        base = self._get_session_prefix() + self.get_viewport().slug + "-"
        return base

    def set_session_keyval(self, key, value):
        base = self._get_session_basekey()
        session_key = base + key
        self.request.session[session_key] = value

    def get_session_keyval(self, key):
        base = self._get_session_basekey()
        session_key = base + key
        return self.request.session.get(session_key, None)

    def pop_session_keyval(self, key):
        base = self._get_session_basekey()
        session_key = base + key
        return self.request.session.pop(session_key, None)

    def set_session_result(self, format, data):
        base = self._get_session_basekey()
        self.request.session[base + "filename"] = (
            self.get_viewport().slug + "." + format
        )
        if isinstance(data, bytes):
            data = base64.b64encode(data).decode("utf-8")
            self.request.session[base + "b64"] = True
        self.request.session[base + "data"] = data

    def _pop_session_result(self):
        base = self._get_session_basekey()
        filename = self.request.session.pop(base + "filename", None)
        data = self.request.session.pop(base + "data", None)
        if self.request.session.pop(base + "b64", False):
            data = base64.b64decode(data)
        return filename, data

    def has_session_result(self):
        base = self._get_session_basekey()
        return (
            base + "filename" in self.request.session
            and base + "data" in self.request.session
        )

    def data_response(self, disposition_type=None):
        """
        ``disposition_type`` may be ``attachment``; which forces
        the view to download a file.
        """
        if not self.has_session_result():
            raise Http404("already downloaded")
        filename, data = self._pop_session_result()
        contenttype, encoding = mimetypes.guess_type(filename)
        if contenttype == "text/csv" and isinstance(data, bytes):
            # for dealing with the UTF-8 BOM
            contenttype = "application/octect-stream"
        response = HttpResponse(content_type=contenttype)
        content_disposition = ""
        if disposition_type is not None:
            content_disposition += disposition_type + "; "
        content_disposition += "filename=" + filename
        response["Content-Disposition"] = content_disposition
        response.content = data
        return response


################################################################


class SpreadsheetExportFormView(SelectedViewportMixin, SessionFileMixin, FormView):
    """
    Export a spreadsheet of marks.
    NOTE:
    - See the following::
    https://github.com/johnculviner/jquery.fileDownload

    """

    role_restrictions = ["superuser", "course coordinator", "instructor"]
    template_name = "gradebook/spreadsheet_export_form.html"
    form_class = forms.SpreadsheetExportForm
    url_name = "gradebook2-marks-download"
    url_params = ("viewport",)
    session_prefix = url_name

    def get_form_kwargs(self):
        kwargs = super(SpreadsheetExportFormView, self).get_form_kwargs()
        kwargs["viewport"] = self.get_viewport()
        return kwargs

    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(*args, **kwargs)
        prev = self.get_session_keyval("form-initial")
        if prev is not None:
            initial.update(prev)
        return initial

    def get_success_url(self):
        return reverse(self.url_name, kwargs={"viewport": self.get_viewport().slug})

    def form_valid(self, form):
        """
        If the form is valid, create responses
        """
        self.set_session_keyval("form-initial", form.cleaned_data)
        format, data = form.response_data()
        filename = self.get_viewport().slug + "." + format
        self.set_session_result(format, data)
        return super().form_valid(form)
        contenttype, encoding = mimetypes.guess_type(filename)
        response = HttpResponse(content_type=contenttype)
        response["Content-Disposition"] = "attachment; filename=" + filename
        response.write(data)
        return response

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["allow_download"] = self.has_session_result()
        return context


################################################################


class SpreadsheetDownloadView(SelectedViewportMixin, SessionFileMixin, View):
    role_restrictions = SpreadsheetExportFormView.role_restrictions
    url_name = "gradebook2-marks-download-data"
    url_params = ("viewport",)
    session_prefix = SpreadsheetExportFormView.url_name

    def get(self, *args, **kwargs):
        return self.data_response(disposition_type="attachment")


################################################################
################################################################
################################################################
################################################################


class BubblesheetUploadForm(CoordinatorBulkResponseFormView):
    """
    Upload classlist for to a section.
    """

    template_name = "gradebook/bubblesheet_upload_form.html"
    form_class = forms.BubblesheetResponseForm
    response_description = "bubblesheet"
    url_name = "gradebook2-bubblesheet-upload"
    url_params = ("viewport",)

    def get_form_kwargs(self):
        kwargs = super(BubblesheetUploadForm, self).get_form_kwargs()
        kwargs["role"] = self.get_effective_role()
        kwargs["task_viewport"] = self.get_viewport()
        return kwargs


################################################################


class StudentSearchFormView(CoordinatorToolsMixin, FormView):
    template_name = "gradebook/student_search.html"
    form_class = forms.StudentSearchForm
    url_name = "gradebook2-student-search"
    url_params = ("viewport",)

    def form_valid(self, form):
        search = form.cleaned_data.get("search")
        role_qs = self.get_student_role_queryset()
        role_qs = role_qs.search(search)
        return self.render_to_response(
            self.get_context_data(form=form, search_results=role_qs, search_done=True)
        )


################################################################


class StudentSearchScoreList(CoordinatorToolsMixin, StudentScoreListDetail):
    url_name = "gradebook2-student-search-score-list"
    url_params = ("viewport", "role_viewport_id", "pk")
    template_name = "gradebook/search_studentscore_list.html"


class StudentSearchScoreEditList(CoordinatorToolsMixin, StudentScoreEditList):
    url_name = "gradebook2-student-search-score-edit"
    url_params = ("viewport", "role_viewport_id", "pk")
    template_name = "gradebook/search_studentscore_editlist.html"

    def get_success_url(self):
        self._set_student_role()
        return reverse(
            StudentSearchScoreList.url_name,
            kwargs={
                "viewport": self.get_viewport().slug,
                "role_viewport_id": self.student_role.viewport_id,
                "pk": self.student_role.person_id,
            },
        )


################################################################


class ModelFormAndFormsetUpdateView(UpdateView):
    """
    Descendant classes should specify the ``form_class`` and ``queryset``
    attributes as well as the ``get_object`` and ``get_formset_class`` methods.
    """

    form_class = None
    queryset = None
    formset_initial = {}
    formset_prefix = None
    slug_field = "url"

    def get_object(self, queryset=None):
        raise ImproperlyConfigured(
            "Descendant classes must implement get_object() appropriately"
        )

    def get_formset_class(self):
        raise ImproperlyConfigured(
            "Descendant classes must implement get_formset_class() appropriately"
        )

    def get_formset_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        return self.formset_initial.copy()

    def get_formset_prefix(self):
        """
        Returns the prefix to use for forms on this view
        """
        return self.formset_prefix

    def get_formset_kwargs(self):
        kwargs = {
            "initial": self.get_formset_initial(),
            "prefix": self.get_formset_prefix(),
            "instance": self.object,
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return kwargs

    def get_formset(self, formset_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if formset_class is None:
            formset_class = self.get_formset_class()
        return formset_class(**self.get_formset_kwargs())

    def get_context_data(self, **kwargs):
        """
        Insert the form into the context dict.
        """
        context = super(ModelFormAndFormsetUpdateView, self).get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def form_valid(self, form, formset):
        """
        If the form is valid, save the associated model.
        """
        # descendant classes *may* do additional processing here.
        result = super(ModelFormAndFormsetUpdateView, self).form_valid(form)
        formset.save()
        return result

    def form_invalid(self, form, formset):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        self.object = self.get_object()
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)


################################################################


class AccessSettingsView(CoordinatorToolsMixin, ModelFormAndFormsetUpdateView):
    template_name = "gradebook/access_settings.html"
    form_class = forms.LedgerAccessForm
    queryset = Ledger.objects.none()
    url_name = "gradebook2-access-settings"
    url_params = ("viewport",)
    role_restrictions = ["superuser", "course coordinator", "instructor"]

    def get_object(self, queryset=None):
        return self.get_viewport().ledger

    def get_formset_queryset(self):
        qs = self.get_all_viewports_queryset()
        if self.get_effective_role().label == "instructor":
            qs = qs.filter(pk=self.get_viewport().pk)
        return qs

    def get_formset_class(self):
        qs = self.get_formset_queryset()
        count = qs.count()
        kwargs = {"min_num": count, "max_num": count}
        return forms.get_ledgerviewport_access_formset(**kwargs)

    def get_formset_kwargs(self, *args, **kwargs):
        kwargs = super(AccessSettingsView, self).get_formset_kwargs(*args, **kwargs)
        kwargs["queryset"] = self.get_formset_queryset()
        return kwargs

    def form_valid(self, *args, **kwargs):
        messages.success(
            self.request, _("Access settings updated."), fail_silently=True
        )
        return super(AccessSettingsView, self).form_valid(*args, **kwargs)

    def get_success_url(self):
        return reverse(self.url_name, kwargs={"viewport": self.get_viewport().slug})


################################################################


class RoleMixin(object):
    url_params = ("viewport", "role_viewport")
    model = Role

    def get_role_viewport(self):
        return get_object_or_404(
            LedgerViewport, active=True, slug=self.kwargs.get("role_viewport", None)
        )

    def get_queryset(self, queryset=None, exclude_students=True):
        if queryset is None:
            queryset = self.model.objects.active()
        viewport = self.get_role_viewport()
        queryset = queryset.filter(active=True, viewport=viewport).exclude(role="su")
        if exclude_students:
            queryset = queryset.exclude(role="st")
        # # exclude any of your own roles; lest you break yourself.
        # my_role = self.get_requesting_role()
        # queryset = queryset.exclude(person_id=my_role.person_id)
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super(RoleMixin, self).get_context_data(*args, **kwargs)
        context["role_viewport"] = self.kwargs.get("role_viewport", None)
        if context["role_viewport"] is not None:
            context["role_viewport_object"] = self.get_role_viewport()
        context["editable_roles"] = self.editable_roles
        return context

    @property
    def editable_roles(self):
        role_list = [c for c, d in Role.CHOICES]
        effective = self.get_requesting_role().role
        if effective not in role_list:
            # this should never happen, but just in case...
            return []
        idx = role_list.index(effective)
        return role_list[idx + 1 :]

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(RoleMixin, self).get_form_kwargs(*args, **kwargs)
        kwargs["editable_roles"] = self.editable_roles
        return kwargs

    def get_success_url(self):
        return reverse(
            RoleListView.url_name,
            kwargs={
                "viewport": self.get_viewport().slug,
                "role_viewport": self.kwargs.get("role_viewport"),
            },
        )


################################################################


class RoleDetailMixin(RoleMixin):
    url_params = ("viewport", "role_viewport", "pk")


################################################################


class RoleListView(CoordinatorToolsMixin, RoleMixin, ListView):
    url_name = "gradebook2-role-list"
    role_restrictions = ["superuser", "course coordinator", "instructor"]


class RoleCreateView(CoordinatorToolsMixin, RoleMixin, CreateView):
    url_name = "gradebook2-role-add"
    form_class = forms.RoleCreateForm
    template_name = "gradebook/role_create_form.html"
    role_restrictions = ["superuser", "course coordinator", "instructor"]

    def get_initial(self, *args, **kwargs):
        initial = super(RoleCreateView, self).get_initial(*args, **kwargs)
        start, end = start_end.get_start_end("mk", self.get_role_viewport())
        if "dtstart" not in initial:
            initial["dtstart"] = start
        if "dtend" not in initial:
            initial["dtend"] = end
        return initial

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.viewport = self.get_role_viewport()
        return super(RoleCreateView, self).form_valid(form)


class RoleUpdateView(CoordinatorToolsMixin, RoleDetailMixin, UpdateView):
    url_name = "gradebook2-role-edit"
    form_class = forms.RoleUpdateForm
    template_name = "gradebook/role_update_form.html"
    role_restrictions = ["superuser", "course coordinator", "instructor"]


class RoleDeleteView(CoordinatorToolsMixin, RoleDetailMixin, DeleteView):
    url_name = "gradebook2-role-delete"
    role_restrictions = ["superuser", "course coordinator", "instructor"]


################################################################


class FormulaList(CoordinatorToolsMixin, ListView):
    """
    List of available formulas
    """

    role_restrictions = ["superuser", "course coordinator", "instructor"]
    url_name = "gradebook2-formula-list"
    url_params = ("viewport",)
    queryset = (
        Formula.objects.active()
        .exclude(short_description="")
        .exclude(applies_to="-dont-show-")
        .order_by("applies_to")
    )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if "task" in self.kwargs:
            context["task"] = get_object_or_404(
                self.get_task_queryset(), slug=self.kwargs["task"]
            )
        return context


################################################################


def coordinator_conditional(wizard):
    """
    Used to skip the ``MarksUploadCoordinatorForm`` step of
    ``MarksUploadWizardView``.
    """
    if wizard.get_effective_role().label not in ["superuser", "coordinator"]:
        # not a coordinator
        return False
    if wizard.get_all_viewports_queryset().count() <= 1:
        # not a multi-viewport ledger
        return False
    return True


################################################################


class MarksUploadWizardView(SelectedViewportMixin, SessionWizardView):
    role_restrictions = ["superuser", "course coordinator", "instructor"]
    url_name = "gradebook2-spreadsheet-upload"
    url_params = ("viewport",)
    form_list = [
        forms.MarksUploadFileForm,
        forms.MarksUploadColumnSelectForm,
        forms.MarksUploadConfirmActionsForm,
        forms.MarksUploadCoordinatorForm,
    ]
    template_name = "gradebook/upload_marks_wizard.html"
    file_storage = FileSystemStorage(
        **conf.get("spreadsheet-upload:file-storage-kwargs")
    )

    def get_context_data(self, *args, **kwargs):
        context = super(MarksUploadWizardView, self).get_context_data(*args, **kwargs)
        context["wizard_step"] = self.steps.current
        return context

    def get_can_create(self):
        if self.get_all_viewports_queryset().count() == 1:
            return True
        if self.get_effective_role().label in ["superuser", "course coordinator"]:
            # a coordinator
            return True
        return False

    def get_done_url(self):
        return reverse(
            ViewportLanding.url_name, kwargs={"viewport": self.get_viewport().slug}
        )

    def done(self, form_list, **kwargs):
        # collect data::
        data = self.get_all_cleaned_data()
        f = data.get("file")
        id_field = data.get("id_field")
        column_names = [
            k.split(":", 1)[1]
            for k in data.keys()
            if k.startswith("save:") and data.get(k)
        ]
        column_actions = [data.get("action:" + f) for f in column_names]
        all_viewports = data.get("all_viewports")
        if self.get_effective_role().label not in ["superuser", "coordinator"]:
            # do not entirely trust user input.
            all_viewports = False
        ignore_unknown_ids = data.get("ignore_unknown_ids")
        can_create = self.get_can_create()

        # save::
        try:
            score_count, id_errors = marks_upload.marks_upload(
                f,
                self.get_viewport(),
                all_viewports,
                id_field,
                column_names,
                dict(zip(column_names, column_actions)),
                ignore_unknown_ids,
                can_create,
            )
        except forms.forms.ValidationError as e:
            messages.error(self.request, e.message, fail_silently=True)
            return self.render_goto_step("0")
        else:
            save_msg = _("Saved %(score_count)s student scores") % {
                "score_count": score_count
            }
            if id_errors:
                warn_msg = _(
                    "The following student ID%(plural)s could not be matched: "
                ) % {"plural": "s" if len(id_errors) != 1 else ""}
                warn_msg += ", ".join(id_errors)
                messages.warning(self.request, warn_msg, fail_silently=True)
            messages.success(self.request, save_msg, fail_silently=True)
            return HttpResponseRedirect(self.get_done_url())

    def process_step_files(self, form):
        files = self.get_form_step_files(form)
        if self.steps.current == "0" and files:
            # extract what's necessary for next step; save in storage.
            f = files["0-file"]
            id_list, task_list = marks_upload.probe_file(f)
            f.seek(0)
            data = {"id_list": id_list, "task_list": task_list}
            self.storage.set_step_data(self.steps.current, data)
        return files

    def get_form(self, step=None, data=None, files=None):
        form = super().get_form(step, data, files)
        # determine the step if not given
        if step is None:
            step = self.steps.current

        if step == "1":  # SpreadsheetColumnSelectForm
            # Augument form with possible fields...
            prev_data = self.storage.get_step_data("0")
            id_list = prev_data.getlist("id_list")
            task_list = prev_data.getlist("task_list")
            form.augment_fields(id_list, task_list)

        if step == "2":
            prev_data = self.storage.get_step_data("1")
            column_names = [
                k.split(":", 1)[1]
                for k in prev_data.keys()
                if k.startswith("1-save:") and prev_data.get(k)
            ]
            can_create = self.get_can_create()
            form.augment_fields(self.get_viewport(), column_names, can_create)
        return form


################################################################
