# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-29 19:15
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("gradebook", "0015_auto_20170515_0949")]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="ledger",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="gradebook.Ledger"
            ),
        )
    ]