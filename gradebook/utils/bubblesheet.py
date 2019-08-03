"""
Bubblesheet utilities
"""
################################################################

from __future__ import print_function, unicode_literals

import os
import sys
from pprint import pprint

import spreadsheet

################################################################
#
# INPUT ROUTINES: reading bubblesheet data files
#


def record_load(fp, verbosity):
    """
    src: http://umanitoba.ca/computing/ist/teaching/exam_scoring/examscoring-output.html
    date: 2010-Apr-14

    POSITIONS 	 LENGTH 	 DESCRIPTIONS
    001 - 001 	 1 	 Record Type
    002 - 013 	 12 	 Student/Sheet ID
    014 - 025 	 12 	 Sheet Serial Number
    026 - 056 	 31 	 Student Name
    057 - 110 	 9X6 	 Score per Section (format - 9 scores given as 9999.99)
    111 - 116 	 6 	 Total Score (format - 9999.99)
    117 - 170 	 18x3 	 Correct/Incorrect Totals per Section (C1,I1,C2,I2...C9,I9)
    171 - 173 	 3 	 Total Correct Responses
    174 - 176 	 3 	 Total Incorrect Responses
    177 - 192 	 16 	 Gobsrid Sourced Id
    193 - 196 	 4 	 Not used
    197 - 1156 	 960 	 Responses (1-960)
    """

    def split_at(string, positions):
        old_p = 0
        result = []
        for p in positions:
            result.append(string[old_p:p])
            old_p = p
        result.append(string[positions[-1] :])
        return result

    positions = [1, 13, 25, 56, 110, 116, 170, 173, 176, 192, 196]
    lines = fp.read().replace("\r", "\n").replace("\n\n", "\n").split("\n")
    results = [[e.strip() for e in split_at(line, positions)] for line in lines]
    if verbosity == 3:
        for row in results:
            pprint(dict(zip(record_headers(), row)))
    return results


################################################################


def record_headers():
    return [
        "Record Type",
        "Student ID",
        "Sheet Serial Number",
        "Student Name",
        "Score per Section",
        "Total Score",
        "Correct/Incorrect Totals per Section",
        "Total Correct Responses",
        "Total Incorrect Responses",
        "Gobsrid Sourced Id",
        "Not used",
        "Responses",
    ]


################################################################


def parse_course_info(course_info):
    """
    course_info == rows[1][3]
    RETURNS (e.g.):
        {
            'course': '2000',
            'section': 'a02',
            'crn': '10196',
            'subject': 'stat'
        }
    """
    return dict(
        [
            [f.lower().strip() for f in e.split(":")]
            for e in course_info.split("  ")
            if ":" in e
        ]
    )


################################################################


def parse_student_row(
    record,
    serial_number_idx,
    score_column_idx,
    responses_idx,
    solution,
    check,
    verbosity,
):
    if record[0] != "N":
        return None
    st_id = record[1].lstrip("0").strip()
    name = ", ".join(record[3].split(None, 1))
    score_text = record[score_column_idx].lstrip("0")
    if not score_text:
        score_text = "0"
    responses = record[responses_idx]  # DO NOT strip() responses!
    serial_number = record[serial_number_idx]
    try:
        wrong = float(record[score_column_idx + 1].lstrip("0"))
    except ValueError:
        wrong = 0.0
    num_responses = float(score_text) + wrong
    if solution:
        marked_score = sum((r in s for r, s in zip(responses, solution)))
        if check:
            score = int(score_text)
            if verbosity >= 2:
                print("{0}\t{1}\t{2}".format(st_id, score, marked_score))
            if score != marked_score and verbosity > 0:
                print(
                    st_id,
                    "\tbubblesheet score:",
                    score,
                    "\tmarked score:",
                    marked_score,
                )
        score_text = "{}".format(marked_score)
    result = {
        "name": name,
        "student_number": st_id,
        "score": score_text,
        "responses": responses,
        "num_responses": int(num_responses),
        "serial_number": serial_number,
    }
    if verbosity == 3:
        pprint(result)
    return result


################################################################


def parse_file(filename, fp, verbosity, solution, check):
    if filename.endswith(".csv"):
        opt_scores = spreadsheet.sheetReader(
            filename=filename, fileobj=fp, subargs={"encoding": "latin-1"}
        )
        headers = [e.lower() for e in opt_scores[0]]
        course_info = parse_course_info(opt_scores[1][3])
        record_start_row = 2

    elif filename.endswith(".txt"):
        opt_scores = record_load(fp, verbosity)
        headers = [e.lower() for e in record_headers()]
        course_info = parse_course_info(opt_scores[0][3])
        record_start_row = 1

    else:
        assert False, (
            "Cannot load this data... bubblesheet data is either .csv or .txt files; not "
            + os.path.splitext(filename)[-1]
        )

    score_column_idx = headers.index("total correct responses")
    responses_idx = headers.index("responses")
    serial_number_idx = headers.index("sheet serial number")
    # full_marks = len(opt_scores[1][-1].replace('0', '').strip())
    # course_info['full_marks'] = full_marks

    # two passes: 1st pass, check for duplicate student numbers
    seen_ids = []
    duplicate_ids = []
    for row in opt_scores[record_start_row:]:
        d = parse_student_row(
            row,
            serial_number_idx,
            score_column_idx,
            responses_idx,
            solution,
            check,
            verbosity,
        )
        if d is not None and d["student_number"]:
            if d["student_number"] not in seen_ids:
                seen_ids.append(d["student_number"])
            else:
                duplicate_ids.append(d["student_number"])

    if duplicate_ids:
        print(
            "!!!",
            "the following student numbers have more than one sheet in the dataset",
        )
        print("   ", ", ".join(duplicate_ids))
        print("!!!", "no action will be taken for these student numbers.")

    results = []
    for row in opt_scores[record_start_row:]:
        d = parse_student_row(
            row,
            serial_number_idx,
            score_column_idx,
            responses_idx,
            solution,
            check,
            verbosity,
        )
        if (
            d is not None
            and d["student_number"]
            and d["student_number"] not in duplicate_ids
        ):
            results.append(d)

    return course_info, results


################################################################
