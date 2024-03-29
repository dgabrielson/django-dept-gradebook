# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-24 16:13
from __future__ import unicode_literals

from django.db import migrations


def forward_data(apps, schema_editor):
    """
    Data migration - populate score.person from score.student_registration.student.person
    """
    Task = apps.get_model("gradebook", "Task")
    for task in Task.objects.all():
        # re-slug all tasks for new uniqueness contraint.
        if task.ledgerviewport_set.count() == 1:
            task.slug += "-{}".format(task.ledgerviewport_set.get().pk)
            task.save()


def backward_data(apps, schema_editor):
    """
    Reverse data migration; not actually implemented.
    """
    Task = apps.get_model("gradebook", "Task")
    for task in Task.objects.all():
        # re-slug all tasks for new uniqueness contraint.
        if task.ledgerviewport_set.count() == 1:
            if task.slug.endswith("-{}".format(task.ledgerviewport_set.get().pk)):
                task.slug = task.slug.rsplit("-", 1)[0]
                task.save()


class Migration(migrations.Migration):

    dependencies = [("gradebook", "0011_auto_20170406_1050")]

    operations = [migrations.RunPython(forward_data, backward_data)]
