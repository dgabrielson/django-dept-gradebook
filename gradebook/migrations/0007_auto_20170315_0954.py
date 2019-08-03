# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-15 14:54
from __future__ import print_function, unicode_literals

from django.db import migrations


def convert_old_role(apps, old_role):
    LedgerViewport = apps.get_model("gradebook", "LedgerViewport")
    Ledger = apps.get_model("gradebook", "Ledger")
    from gradebook import conf

    viewport = conf.get("viewport_from_section")(
        Ledger, LedgerViewport, old_role.section
    )
    if viewport is None:
        return
    Role = apps.get_model("gradebook", "Role")
    role, created = Role.objects.get_or_create(
        person=old_role.person,
        role=old_role.role,
        viewport=viewport,
        dtstart=old_role.dtstart,
        dtend=old_role.dtend,
    )
    return role, old_role.section_id, role.viewport.ledger_id


def forward_data(apps, schema_editor):
    try:
        section_role = apps.get_model("course_role", "Role")
    except LookupError as e:
        print(e, end=" ")  # course_role app not installed... do not migrate old data.
        return
    else:
        from gradebook import conf

        # check that we want migration;
        if conf.get("ledger_from_section") is None:
            return
        if conf.get("viewport_from_section") is None:
            return
        # migrate role data
        role_count = 0
        section_ledger_map = {}
        for old_r in section_role.objects.all():
            role, section_id, ledger_id = convert_old_role(apps, old_r)
            if section_id not in section_ledger_map:
                section_ledger_map[section_id] = ledger_id
            else:
                assert (
                    section_ledger_map[section_id] == ledger_id
                ), "Same section mapping to different ledgers in conversion!"
            role_count += 1
        print(" Converted {} role(s)".format(role_count))
        # add ledger to tasks...
        task_count = 0
        Ledger = apps.get_model("gradebook", "Ledger")
        LedgerViewport = apps.get_model("gradebook", "LedgerViewport")
        Task = apps.get_model("gradebook", "Task")
        for task in Task.objects.all():
            if task.section_id in section_ledger_map:
                # quick way
                task.ledger_id = section_ledger_map[task.section_id]
            else:
                # slow way
                ledger = conf.get("ledger_from_section")(Ledger, task.section)
                if ledger is None:
                    continue
                task.ledger = ledger
            task.save()
            viewport = conf.get("viewport_from_section")(
                Ledger, LedgerViewport, task.section
            )
            if viewport is not None:
                viewport.tasks.add(task)
            task_count += 1
        print(
            "                                            ... Converted {} task(s)".format(
                task_count
            )
        )
        print("                                               ", end="")


def backward_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("gradebook", "0006_auto_20170314_1537")]

    operations = [migrations.RunPython(forward_data, backward_data)]
