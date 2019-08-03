#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This utility module provides routines for interfacing with a spreadsheet for
mark uploads.
"""
################################################################

from __future__ import print_function, unicode_literals

import os

import spreadsheet
from django.db import transaction
from django.db.models import Q
from django.forms import ValidationError
from django.utils import six
from django.utils.text import slugify

from ..models import Category, Role, Score, Task

################################################################

ID_FIELD_NAMES = [
    "student number",
    "student id",
    "student #",
    "student no.",
    "student num",
    "umnetid",
    "username",
    "id",
    "orgdefinedid",  # d2l
    "email",
    "email address",
]

IGNORE_FIELD_NAMES = [
    "name",
    "first name",
    "last name",
    "family name",
    "surname",
    "given name",
    "student name",
    "record no",
    "record number",
    "record #",
    "level",
    "degree",
    "program",
    "major",
    "telephone",
    "email",
]

################################################################

# def guess_id_header(headers):
#     """
#     headers is assumed to be lowercase.
#     """
#     for name in ID_FIELD_NAMES:
#         if name in headers:
#             return name
#     assert False, 'Could not determine the student ID header from this list: ' + repr(headers)

################################################################


def _safe_data(f):
    """
    Convert a value to a float (if numeric),
    or as a string, or None.
    """
    if isinstance(f, float):
        return f
    if isinstance(f, six.integer_types):
        return float(f)
    if isinstance(f, six.string_types):
        if f.strip():
            try:
                return float(f)
            except ValueError:
                return f.strip()
    return None  # just to be explicit


################################################################


def probe_file(fileobj):
    """
    This function returns two lists:
    1.  A priority list of possible ID fields which will be used to match students.
    2.  A list of potential assignment score columns.
    """
    rows = spreadsheet.sheetReader(fileobj.name, fileobj)

    headers = [
        e.strip().lower() if isinstance(e, six.string_types) else e for e in rows[0]
    ]
    id_fields = []
    for h in ID_FIELD_NAMES:
        if h in headers:
            id_fields.append(h)

    ignore_list = ID_FIELD_NAMES + IGNORE_FIELD_NAMES
    an_list = []
    for h in (
        e.strip().lower() if isinstance(e, six.string_types) else e
        for e in rows[0]
        if e
    ):

        if h not in ignore_list:
            an_list.append(h)

    return id_fields, an_list


################################################################


def _load_scores(fileobj, id_fieldname, assignment_list, duplicate_action="error"):
    """
    This is the function which actually processes the CSV file.
    """
    if duplicate_action not in ["error", "zero score"]:
        raise NotImplementedError(
            'The duplicate_action "{}" not implmented'.format(duplicate_action)
        )
    rows = spreadsheet.sheetReader(fileobj.name, fileobj)
    headers = [
        e.strip().lower() if isinstance(e, six.string_types) else e for e in rows[0]
    ]

    # get id index
    student_number_idx = headers.index(id_fieldname)

    # get header indices
    assignment_idxs = [
        headers.index(assignment_name.lower()) for assignment_name in assignment_list
    ]

    # get scores
    D = {}
    for row in rows[1:]:
        try:
            st_id = row[student_number_idx]
        except IndexError:
            continue  # skip blank ids
        if not st_id:
            continue  # skip blank ids

        if st_id in D and duplicate_action == "error":
            raise ValidationError("duplicate student number! [%s]" % st_id)

        scores = [
            row[assignment_idx] if assignment_idx < len(row) else ""
            for assignment_idx in assignment_idxs
        ]
        fscores = [_safe_data(score) for score in scores]
        if st_id in D and duplicate_action == "zero score":
            fscores = [0 for score in scores]
        mscores = dict(zip(assignment_list, fscores))

        D[st_id] = mscores

    return D


################################################################


def _guess_category(name):
    category_qs = Category.objects.active()
    first_part = name.split()[0]
    match_qs = category_qs.filter(name__istartswith=first_part)
    if match_qs.count() == 1:
        return match_qs.get()
    if name.lower().startswith("final "):
        category, created = Category.objects.get_or_create(
            name="Final Exam", public=False
        )
    else:
        category, created = Category.objects.get_or_create(name="Homework", public=True)
    return category


################################################################


def _task_create(ledger, viewport, name):
    category = _guess_category(name)
    task = Task.objects.create(category=category, name=name, ledger=ledger)
    assert task.pk, "no task primary key"
    viewport.tasks.add(task)
    return task


################################################################


def task_name_search(viewport, name, action, can_create):
    if action not in ["update", "search", "create", "no_save", "link_update"]:
        raise NotImplementedError("The task action '{}' is unknown".format(action))

    if action == "no_save":
        return None
    if action == "create" and not can_create:
        return None
    slug = slugify(name)

    ledger = viewport.ledger
    ledger_task_qs = ledger.task_set.active()
    viewport_tasks = viewport.tasks  # need m2m accessor; not queryset

    ledger_match = ledger_task_qs.filter(Q(name__iexact=name) | Q(slug=slug)).distinct()
    if ledger_match.count() == 1:
        task = ledger_match.get()
        if task in viewport_tasks.active():
            if action == "search":
                return True, True
            if action == "update":
                return task
            raise NotImplementedError(
                "Invalid execution path for action '{}'".format(action)
            )
        else:
            if action == "search":
                return True, False
            if action == "link_update":
                viewport_tasks.add(task)
                return task
            if action == "create":
                return _task_create(ledger, viewport, name)
            raise NotImplementedError(
                "Invalid execution path for action '{}'".format(action)
            )
    else:
        if action == "search":
            return False, False
        if action == "create":
            return _task_create(ledger, viewport, name)
        raise NotImplementedError(
            "Invalid execution path for action '{}'".format(action)
        )

    raise NotImplementedError(
        "Invalid execution path in function task_name_search".format(action)
    )


################################################################


def _setup_tasks(viewport, save_column_headers, save_action_map, can_create):

    result = {}
    for name in save_column_headers:
        action = save_action_map[name]
        result[name] = task_name_search(viewport, name, action, can_create)
    return result


################################################################


def _get_student_person(st_id, id_field, viewport, all_sections):
    role_qs = Role.objects.active().filter(role="st")
    if all_sections:
        viewport_qs = viewport.ledger.ledgerviewport_set.active()
        role_qs = role_qs.filter(viewport__in=viewport_qs)
    else:
        role_qs = role_qs.filter(viewport=viewport)
    if type(st_id) == int:
        id_field = "student id"
    role_qs = role_qs.from_id(st_id, hint=id_field)
    role_count = role_qs.count()
    if role_count == 1:
        role = role_qs.get()
        return role.person
    elif role_count == 0:
        return None
    # more than one role... could be only one person...
    person_set = set(role_qs.values_list("person_id", flat=True))
    if len(person_set) == 1:
        return role_qs[0].person
    else:
        raise ValidationError("More than one person returned for id = {}".format(st_id))


################################################################


def _save_student_scores(person, score_value_map, task_map):
    count = 0
    for name in score_value_map:
        task = task_map.get(name, None)
        # print(name, task)
        if task is None:
            continue
        value = score_value_map.get(name)
        if value is None:
            value = ""
        score, created = Score.objects.update_or_create(
            person=person, task=task, defaults={"value": value}
        )
        # print(person, score, created)
        count += 1
    return count


################################################################


@transaction.atomic
def marks_upload(
    fileobj,
    viewport,
    all_sections,
    id_field,
    save_column_headers,
    save_action_map,
    ignore_unknown_ids,
    can_create,
):

    mark_data = _load_scores(fileobj, id_field, save_column_headers)
    task_map = _setup_tasks(viewport, save_column_headers, save_action_map, can_create)
    count = 0
    errors = []
    for st_id in mark_data:
        person = _get_student_person(st_id, id_field, viewport, all_sections)
        if person is None:
            if ignore_unknown_ids:
                errors.append(str(st_id))
            else:
                # roll back entire transaction.
                raise ValidationError(
                    "Could not find student with id = {}".format(st_id)
                )
        else:
            count += _save_student_scores(person, mark_data[st_id], task_map)
    return count, errors


################################################################
