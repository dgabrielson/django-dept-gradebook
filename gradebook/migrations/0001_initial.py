# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classes", "0002_auto_20150611_1109"),
        ("contenttypes", "0001_initial"),
        ("students", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Bin",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "threshold",
                    models.FloatField(
                        help_text=b"Should be a value in the interval (0,100)."
                    ),
                ),
                (
                    "score",
                    models.FloatField(help_text=b"The score that this bin is worth."),
                ),
            ],
            options={"ordering": ["threshold"]},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                (
                    "slug",
                    models.SlugField(max_length=64, serialize=False, primary_key=True),
                ),
                ("ordering", models.PositiveSmallIntegerField(default=100)),
                (
                    "public",
                    models.BooleanField(
                        default=True,
                        help_text="Whether or not students can see their own score",
                    ),
                ),
            ],
            options={
                "ordering": ("ordering", "name"),
                "verbose_name_plural": "Categories",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Delegation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("delegated_by", models.CharField(max_length=16)),
                (
                    "username",
                    models.CharField(help_text=b"The delegates UMnetID", max_length=16),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Formula",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                ("type", models.CharField(max_length=4)),
                ("args", jsonfield.fields.JSONField()),
                ("digest", models.SlugField(max_length=64, blank=True)),
            ],
            options={"abstract": False},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Grade_Category",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("Active", models.BooleanField(default=True)),
                ("Last_Updated", models.DateTimeField(auto_now=True)),
                (
                    "Section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="classes.Section"
                    ),
                ),
            ],
            options={
                "ordering": ["Type", "Section"],
                "verbose_name": "Grade Category",
                "verbose_name_plural": "Grade Categories",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Grade_Type",
            fields=[
                ("Active", models.BooleanField(default=True)),
                ("Last_Updated", models.DateTimeField(auto_now=True)),
                ("Name", models.SlugField(serialize=False, primary_key=True)),
                ("Description", models.CharField(max_length=150, blank=True)),
                ("Visible_To_Student", models.BooleanField(default=True)),
            ],
            options={"ordering": ["Name"], "verbose_name": "Grade Type"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="iclicker_primitive",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("Active", models.BooleanField(default=True)),
                ("Last_Updated", models.DateTimeField(auto_now=True)),
                ("iclicker_ID", models.CharField(max_length=8)),
                ("Score", models.FloatField()),
                ("Responses", models.CharField(max_length=64)),
                ("In_Use", models.BooleanField(default=False)),
            ],
            options={"verbose_name": "i>clicker Primitive"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="LetterGrade",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("letter", models.CharField(unique=True, max_length=8)),
                (
                    "rank",
                    models.FloatField(
                        help_text=b"The GPA for the letter grade.", unique=True
                    ),
                ),
            ],
            options={"ordering": ["-rank"]},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="LetterGradeCutoff",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "threshold",
                    models.FloatField(
                        help_text=b"Should be a value in the interval (0,1)."
                    ),
                ),
                (
                    "grade",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="gradebook.LetterGrade"
                    ),
                ),
            ],
            options={"ordering": ["grade"]},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="LetterGradeForSection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "release_to_students",
                    models.BooleanField(
                        default=False,
                        help_text=b"If this is set, students will be able to see their final letter grades.",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="classes.Section"
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="LetterGradeForStudent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("comments", models.CharField(max_length=64, blank=True)),
                (
                    "lettergrade",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="gradebook.LetterGrade"
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="classes.Section"
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="students.Student"
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.SlugField(unique=True, max_length=64)),
                ("description", models.CharField(max_length=256)),
                (
                    "has_param",
                    models.BooleanField(
                        default=False,
                        help_text=b"Indicates the permission requires a parameter",
                    ),
                ),
                (
                    "advertise",
                    models.BooleanField(
                        default=False,
                        help_text=b"Indicates this permission may be shown in templates",
                    ),
                ),
                (
                    "can_delegate",
                    models.BooleanField(
                        default=False,
                        help_text=b"Indicates that if someone has this permission, they can assign it to somebody else.",
                    ),
                ),
                (
                    "default_perm",
                    models.BooleanField(
                        default=False,
                        help_text=b"Indicates that this is a default permssion, which all delegations will receive.",
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Response",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                (
                    "student_id",
                    models.CharField(
                        help_text="As identified by the response source", max_length=32
                    ),
                ),
                ("score", models.CharField(max_length=32)),
                (
                    "response_string",
                    models.CharField(
                        help_text="As supplied by the response source", max_length=256
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        help_text="A brief indication of what type of response this is (may include task/section hints)",
                        max_length=64,
                        blank=True,
                    ),
                ),
                ("scored", models.BooleanField(default=False)),
            ],
            options={"abstract": False},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Rule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "ordering",
                    models.PositiveSmallIntegerField(
                        help_text=b"A small positive value that determines when this rule is applied."
                    ),
                ),
            ],
            options={"ordering": ["ordering"]},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="DropRule",
            fields=[
                (
                    "rule_ptr",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="gradebook.Rule",
                    ),
                ),
                (
                    "drop_count",
                    models.PositiveSmallIntegerField(
                        help_text=b"How many tasks to drop from the total."
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        help_text=b"The category of tasks for the total.",
                        to="gradebook.Grade_Type",
                    ),
                ),
            ],
            options={
                "verbose_name": "Rule - Drop",
                "verbose_name_plural": "Rules - Drop",
            },
            bases=("gradebook.rule",),
        ),
        migrations.CreateModel(
            name="BinRule",
            fields=[
                (
                    "rule_ptr",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="gradebook.Rule",
                    ),
                )
            ],
            options={
                "verbose_name": "Rule - Bin",
                "verbose_name_plural": "Rules - Bin",
            },
            bases=("gradebook.rule",),
        ),
        migrations.CreateModel(
            name="Score",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                ("value", models.CharField(max_length=32, blank=True)),
                ("old_value", models.CharField(max_length=32, blank=True)),
                ("public", models.NullBooleanField()),
                (
                    "full_marks",
                    models.CharField(
                        help_text="Optional, if not set, the task full marks will be used",
                        max_length=32,
                        blank=True,
                    ),
                ),
                ("dependencies_resolved", models.BooleanField(default=False)),
                (
                    "dependencies",
                    models.ManyToManyField(
                        related_name="reverse_dependencies",
                        to="gradebook.Score",
                        blank=True,
                    ),
                ),
                (
                    "formula",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        blank=True,
                        to="gradebook.Formula",
                        null=True,
                    ),
                ),
                (
                    "student_registration",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to="students.Student_Registration",
                    ),
                ),
            ],
            options={"ordering": ("student_registration", "task")},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Scored_Task",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("Active", models.BooleanField(default=True)),
                ("Last_Updated", models.DateTimeField(auto_now=True)),
                ("Name", models.CharField(max_length=50)),
                ("Full_Marks", models.FloatField()),
                ("Description", models.CharField(max_length=150, blank=True)),
                ("Notes", models.TextField(blank=True)),
                (
                    "export_normalized",
                    models.BooleanField(
                        default=False,
                        help_text=b"If this is checked, spreadsheets will show this task out of 1 point",
                    ),
                ),
            ],
            options={"ordering": ["Category", "Name"], "verbose_name": "Scored Task"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ComputedScoredTask",
            fields=[
                (
                    "scored_task_ptr",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="gradebook.Scored_Task",
                    ),
                )
            ],
            options={},
            bases=("gradebook.scored_task",),
        ),
        migrations.CreateModel(
            name="Student_Score",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("Active", models.BooleanField(default=True)),
                ("Last_Updated", models.DateTimeField(auto_now=True)),
                ("Score", models.FloatField()),
                ("Notes", models.TextField(blank=True)),
                (
                    "Instance",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="gradebook.Scored_Task"
                    ),
                ),
                (
                    "Student",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="students.Student"
                    ),
                ),
            ],
            options={"ordering": ["Instance"], "verbose_name": "Student Score"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="SumRule",
            fields=[
                (
                    "rule_ptr",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="gradebook.Rule",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="gradebook.Grade_Type"
                    ),
                ),
            ],
            options={
                "verbose_name": "Rule - Sum",
                "verbose_name_plural": "Rules - Sum",
            },
            bases=("gradebook.rule",),
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                (
                    "slug",
                    models.SlugField(
                        help_text="The url fragment for accessing this task (must be unique for this section)",
                        max_length=64,
                    ),
                ),
                ("ordering", models.PositiveSmallIntegerField(default=100)),
                ("public", models.NullBooleanField()),
                (
                    "full_marks",
                    models.CharField(
                        help_text="Only makes sense for numeric tasks",
                        max_length=32,
                        blank=True,
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="gradebook.Category"
                    ),
                ),
                (
                    "formula",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        blank=True,
                        to="gradebook.Formula",
                        null=True,
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="classes.Section"
                    ),
                ),
            ],
            options={"ordering": ("ordering", "name")},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Weight",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("weight", models.FloatField()),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="WeightRule",
            fields=[
                (
                    "rule_ptr",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="gradebook.Rule",
                    ),
                )
            ],
            options={
                "verbose_name": "Rule - Weight",
                "verbose_name_plural": "Rules - Weight",
            },
            bases=("gradebook.rule",),
        ),
        migrations.AddField(
            model_name="weight",
            name="rule",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.WeightRule"
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="weight",
            name="task",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.Scored_Task"
            ),
            preserve_default=True,
        ),
        migrations.AlterOrderWithRespectTo(name="weight", order_with_respect_to="rule"),
        migrations.AlterUniqueTogether(
            name="task", unique_together=set([("slug", "section")])
        ),
        migrations.AlterUniqueTogether(
            name="student_score", unique_together=set([("Student", "Instance")])
        ),
        migrations.AddField(
            model_name="scored_task",
            name="Category",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.Grade_Category"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="scored_task", unique_together=set([("Category", "Name")])
        ),
        migrations.AddField(
            model_name="score",
            name="task",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.Task"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="score", unique_together=set([("task", "student_registration")])
        ),
        migrations.AddField(
            model_name="rule",
            name="content_type",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                editable=False,
                to="contenttypes.ContentType",
                null=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="rule",
            name="target",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE, to="gradebook.ComputedScoredTask"
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="response",
            name="task",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                to="gradebook.Task",
                help_text="An associated task, if one can be determined",
                null=True,
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="lettergradeforstudent", unique_together=set([("section", "student")])
        ),
        migrations.AddField(
            model_name="lettergradeforsection",
            name="task",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                help_text=b"Regardless of the full value of the task, enter cutoffs between 0 and 100.",
                to="gradebook.Scored_Task",
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="lettergradecutoff",
            name="parent",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.LetterGradeForSection"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="lettergradecutoff", unique_together=set([("parent", "grade")])
        ),
        migrations.AddField(
            model_name="iclicker_primitive",
            name="Instance",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.Scored_Task"
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="grade_category",
            name="Type",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.Grade_Type"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="grade_category", unique_together=set([("Section", "Type")])
        ),
        migrations.AddField(
            model_name="delegation",
            name="perms",
            field=models.ManyToManyField(
                to="gradebook.Permission", verbose_name=b"permissions"
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="delegation",
            name="section",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="classes.Section"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="delegation", unique_together=set([("section", "username")])
        ),
        migrations.AddField(
            model_name="binrule",
            name="task",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                help_text=b"Regardless of the full value of the task, enter cutoffs between 0 and 100.",
                to="gradebook.Scored_Task",
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="bin",
            name="rule",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="gradebook.BinRule"
            ),
            preserve_default=True,
        ),
        migrations.AlterOrderWithRespectTo(name="bin", order_with_respect_to="rule"),
    ]
