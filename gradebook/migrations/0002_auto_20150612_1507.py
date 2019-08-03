# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("gradebook", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="score",
            name="public",
            field=models.NullBooleanField(
                help_text='Whether or not students can see their own score.  "Unknown" means the value is inherited from the task setting.'
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="public",
            field=models.NullBooleanField(
                help_text='Whether or not students can see their own score.  "Unknown" means the value is inherited from the category of this task.'
            ),
        ),
    ]
