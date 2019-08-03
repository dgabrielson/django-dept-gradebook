from __future__ import print_function, unicode_literals

from gradebook.models import Score, Task

# Gradebook CSV export:


def score_data(
    viewport,
    good_standing=True,
    task_label=None,
    task_list=None,
    streg_pre_fields=None,
    streg_post_fields=None,
):
    """
    Returns a data array for use in dumping to a spreadsheet.
    """

    def _safe_student_number(r):
        from students.models import Student

        try:
            return r.person.student.student_number
        except Student.DoesNotExist:
            return "(no student number)"

    if task_label is None:
        task_label = lambda t: t.name
    if streg_pre_fields is None:
        streg_pre_fields = [
            ("Surname", lambda r: r.person.sn),
            ("Given name", lambda r: r.person.given_name),
            ("Student number", lambda r: _safe_student_number(r)),
        ]
    if streg_post_fields is None:
        streg_post_fields = []

    st_role_list = viewport.role_set.filter(role="st").select_related(
        "person", "person__student"
    )
    if good_standing:
        st_role_list = st_role_list.active()

    if task_list is None:
        task_list = viewport.tasks.active()
    data = [[f[0] for f in streg_pre_fields]]
    for task in task_list:
        data[0].append("{}".format(task_label(task)))
    data[0] += [f[0] for f in streg_post_fields]

    for st_role in st_role_list:
        row = ["{}".format(f[1](st_role)) for f in streg_pre_fields]
        for task in task_list:
            try:
                score = Score.objects.get(person_id=st_role.person_id, task=task)
            except Score.DoesNotExist:
                value = "<error>"
            else:
                value = score.value
            row.append(value)
        row += ["{}".format(f[1](st_role)) for f in streg_post_fields]
        data.append(row)

    return data
