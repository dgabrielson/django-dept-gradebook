from __future__ import print_function, unicode_literals

from django.contrib import admin
from django.db import models
from django.forms import CheckboxSelectMultiple
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from .gb2.forms import (
    AdminChangeTaskForm,
    AdminCreateTaskForm,
    AdminFormulaForm,
    LedgerViewportForm,
)
from .models import Category, Formula, Ledger, LedgerViewport, Role, Score, Task

###############################################################
##############################################################


def mark_inactive(modeladmin, request, queryset):
    queryset.update(Active=False)


mark_inactive.short_description = "Mark selected items as inactive"

##############################################################


def mark_not_inuse(modeladmin, request, queryset):
    queryset.update(In_Use=False)


mark_not_inuse.short_description = "Mark selected items as not in use"

##############################################################


class CategoryAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "ordering", "public"]
    list_editable = ["ordering", "public"]


admin.site.register(Category, CategoryAdmin)

###############################################################


class TaskAdmin(admin.ModelAdmin):
    form = AdminChangeTaskForm  # see get_form() below
    list_display = ["name", "category", "ledger"]
    list_select_related = ["category", "ledger"]
    # TODO: Improve filters so only current and used sections are shown.
    list_filter = ["category"]
    list_search = ["name"]
    autocomplete_fields = ["ledger", "formula"]
    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            self.form = AdminCreateTaskForm
        else:
            self.form = AdminChangeTaskForm
        return super(TaskAdmin, self).get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(TaskAdmin, self).get_readonly_fields(request, obj))
        if obj is not None and obj.pk:
            if "slug" not in readonly_fields:
                readonly_fields.append("slug")
            if "ledger" not in readonly_fields:
                readonly_fields.append("ledger")
        return readonly_fields

    def get_fields(self, request, obj=None):
        fields = super(TaskAdmin, self).get_fields(request, obj)
        if obj is None or not obj.pk:
            if "slug" in fields:
                fields.remove("slug")
        return fields


admin.site.register(Task, TaskAdmin)

###############################################################


class FormulaAdmin(admin.ModelAdmin):
    form = AdminFormulaForm
    readonly_fields = ["digest"]
    search_fields = ["short_description", "applies_to"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(FormulaAdmin, self).get_readonly_fields(request, obj)
        if "type" in readonly_fields:
            readonly_fields.remove("type")
        if obj is not None and obj.pk:
            readonly_fields += ["type"]
        return readonly_fields


admin.site.register(Formula, FormulaAdmin)

#######################################################################


class LedgerViewportInline(admin.TabularInline):
    model = LedgerViewport
    fields = ["name", "changelist_buttons"]
    readonly_fields = ["changelist_buttons"]
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_buttons(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">Edit Details &raquo;</a>',
                reverse("admin:gradebook_ledgerviewport_change", args=[obj.pk]),
            )
        return ""

    changelist_buttons.short_description = "Actions"
    changelist_buttons.allow_tags = True


class TaskInline(admin.TabularInline):
    model = Task
    fields = ["name", "changelist_buttons"]
    readonly_fields = ["changelist_buttons"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_buttons(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">Edit Details &raquo;</a>',
                reverse("admin:gradebook_task_change", args=[obj.pk]),
            )
        return ""

    changelist_buttons.short_description = "Actions"
    changelist_buttons.allow_tags = True


class LedgerAdmin(admin.ModelAdmin):
    date_hierarchy = "dtstart"
    inlines = [LedgerViewportInline, TaskInline]
    list_display = ["name", "dtstart", "dtend"]
    list_filter = ["active", "dtstart", "dtend"]
    readonly_fields = ["slug"]
    save_on_top = True
    search_fields = ["name"]

    def merge_ledgers(self, request, queryset):
        count = queryset.count()
        merge_into = queryset.first()
        qs_others = queryset[1:]
        # update viewports
        for ledger in qs_others:
            ledger.ledgerviewport_set.update(ledger=merge_into)
            ledger.task_set.update(ledger=merge_into)
            ledger.delete()
        self.message_user(request, "%d ledgers merged." % count)

    merge_ledgers.short_description = "Merge selected ledgers (CAUTION)"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.user.is_superuser and "merge_ledgers" not in actions:
            actions["merge_ledgers"] = (
                LedgerAdmin.merge_ledgers,
                "merge_ledgers",
                LedgerAdmin.merge_ledgers.short_description,
            )
        return actions


admin.site.register(Ledger, LedgerAdmin)

#######################################################################


class LedgerViewportAdmin(admin.ModelAdmin):
    fields = [
        ("ledger", "ledger_change_button"),
        "active",
        ("name", "ordering"),
        "public",
        "tasks",
    ]
    form = LedgerViewportForm
    filter_horizontal = ["tasks"]
    list_display = ["name"]
    list_filter = ["active", "ledger__dtstart", "ledger__dtend"]
    autocomplete_fields = ["ledger"]
    readonly_fields = ["ledger_change_button"]
    save_on_top = True
    search_fields = ["name", "ledger__name"]

    def get_readonly_fields(self, request, obj=None):
        """
        Dynamic readonly fields
        """
        readonly_dynamic = list()
        if obj:  # editing an existing object
            readonly_dynamic += ["ledger"]
        return self.readonly_fields + readonly_dynamic

    def ledger_change_button(self, obj):
        if obj.pk and obj.ledger.pk:
            return format_html(
                '<a class="button" href="{}">Edit Details &raquo;</a>',
                reverse("admin:gradebook_ledger_change", args=[obj.ledger.pk]),
            )
        return ""

    ledger_change_button.short_description = ""
    ledger_change_button.allow_tags = True


admin.site.register(LedgerViewport, LedgerViewportAdmin)

#######################################################################


class RoleAdmin(admin.ModelAdmin):
    date_hierarchy = "dtstart"
    list_display = ["role", "person", "viewport", "dtstart", "dtend"]
    list_filter = ["role", "active", "modified", "created"]  # TermFilter, CourseFilter,
    autocomplete_fields = ["person", "viewport"]
    save_on_top = True
    search_fields = [
        "person__cn",
        "person__username",
        "viewport__name",
        "viewport__ledger__name",
    ]


admin.site.register(Role, RoleAdmin)

###############################################################
###############################################################
###############################################################
###############################################################
