################################################################
from __future__ import print_function, unicode_literals

from django.conf.urls import url

from . import views

################################################################

urlpatterns = [
    url(r"^$", views.GradebookMain.as_view(), name=views.GradebookMain.url_name),
    url(
        r"^(?P<viewport>[\w-]+)/$",
        views.ViewportLanding.as_view(),
        name=views.ViewportLanding.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-list/$",
        views.StudentRegistrationList.as_view(),
        name=views.StudentRegistrationList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/tasks/$",
        views.TaskList.as_view(),
        name=views.TaskList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/tasks/(?P<task>[\w-]+)/scores/$",
        views.ScoreList.as_view(),
        name=views.ScoreList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/tasks/(?P<task>[\w-]+)/scores/edit/$",
        views.ScoreEditList.as_view(),
        name=views.ScoreEditList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-scores/$",
        views.StudentScoreList.as_view(),
        name=views.StudentScoreList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-scores/(?P<pk>\d+)/$",
        views.StudentScoreList.as_view(),
        name=views.StudentScoreListDetail.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-scores/(?P<pk>\d+)/edit/$",
        views.StudentScoreEditList.as_view(),
        name=views.StudentScoreEditList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/tasks/(?P<task>[\w-]+)/scores/(?P<pk>\d+)$",
        views.ScoreDetail.as_view(),
        name=views.ScoreDetail.url_name,
    ),
    ###########################################################
    url(
        r"^(?P<viewport>[\w-]+)/iclicker-upload/$",
        views.IClickerUploadForm.as_view(),
        name=views.IClickerUploadForm.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/classlist-upload/$",
        views.ClasslistUploadForm.as_view(),
        name=views.ClasslistUploadForm.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/bubblesheet-upload/$",
        views.BubblesheetUploadForm.as_view(),
        name=views.BubblesheetUploadForm.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/marks-download/$",
        views.SpreadsheetExportFormView.as_view(),
        name=views.SpreadsheetExportFormView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/marks-download/data$",
        views.SpreadsheetDownloadView.as_view(),
        name=views.SpreadsheetDownloadView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/marks-upload/$",
        views.MarksUploadWizardView.as_view(
            condition_dict={"3": views.coordinator_conditional}
        ),
        name=views.MarksUploadWizardView.url_name,
    ),
    ###########################################################
    url(
        r"^(?P<viewport>[\w-]+)/student-search/$",
        views.StudentSearchFormView.as_view(),
        name=views.StudentSearchFormView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-search/(?P<role_viewport_id>\d+)/(?P<pk>\d+)/$",
        views.StudentSearchScoreList.as_view(),
        name=views.StudentSearchScoreList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/student-search/(?P<role_viewport_id>\d+)/(?P<pk>\d+)/edit/$",
        views.StudentSearchScoreEditList.as_view(),
        name=views.StudentSearchScoreEditList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/access-settings/$",
        views.AccessSettingsView.as_view(),
        name=views.AccessSettingsView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/access-settings/(?P<role_viewport>[\w-]+)/roles/$",
        views.RoleListView.as_view(),
        name=views.RoleListView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/access-settings/(?P<role_viewport>[\w-]+)/roles/create/$",
        views.RoleCreateView.as_view(),
        name=views.RoleCreateView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/access-settings/(?P<role_viewport>[\w-]+)/roles/(?P<pk>[\d]+)/update$",
        views.RoleUpdateView.as_view(),
        name=views.RoleUpdateView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/access-settings/(?P<role_viewport>[\w-]+)/roles/(?P<pk>[\d]+)/delete$",
        views.RoleDeleteView.as_view(),
        name=views.RoleDeleteView.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/$",
        views.AllTaskList.as_view(),
        name=views.AllTaskList.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/create/$",
        views.TaskCreate.as_view(),
        name=views.TaskCreate.url_name,
    ),
    # url(r'^(?P<viewport>[\w-]+)/task-settings/(?P<task>[\w-]+)/$',
    #     views.AllTaskDetail.as_view(), name=views.AllTaskDetail.url_name,
    #     ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/(?P<task>[\w-]+)/update/$",
        views.TaskUpdate.as_view(),
        name=views.TaskUpdate.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/(?P<task>[\w-]+)/delete/$",
        views.TaskDelete.as_view(),
        name=views.TaskDelete.url_name,
    ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/formulas/$",
        views.FormulaList.as_view(),
        name=views.FormulaList.url_name + "-create",
    ),
    url(
        r"^(?P<viewport>[\w-]+)/task-settings/(?P<task>[\w-]+)/formulas/$",
        views.FormulaList.as_view(),
        name=views.FormulaList.url_name,
    ),
]

################################################################
