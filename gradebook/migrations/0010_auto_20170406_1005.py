# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-06 15:05
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("gradebook", "0009_auto_20170316_1541")]

    operations = [
        migrations.AlterModelOptions(
            name="role", options={"ordering": ("viewport", "person")}
        ),
        migrations.AddField(
            model_name="formula",
            name="short_description",
            field=models.CharField(
                blank=True,
                help_text="A short, human readable description",
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name="response",
            name="viewport",
            field=models.ForeignKey(
                help_text="An associated viewport, if appropriate",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="gradebook.LedgerViewport",
            ),
        ),
    ]
