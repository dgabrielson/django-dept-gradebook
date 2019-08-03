#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from spreadsheet import sheetReader


class ParseError(Exception):
    pass


# def csv_load(input_filename_or_fp, delimiter=None, skip_blanks=True):
#     """
#     This function is designed to be 'the' csv loading code.
#     """
#     if callable(getattr(input_filename_or_fp, 'read', None)):
#         fp = input_filename_or_fp
#     else:
#         fp = open(input_filename_or_fp)
#
#
#     txt = fp.read().replace('\r', '\n') # deal with either line-ending.
#     # warning: skip_blanks set False may interfer!
#
#     if delimiter is None:
#         # autodetect delimiter: tabs, commas, semicolons
#         possible_delimiters = [',', '\t', ';', ]
#         count_dict = {}
#         for d in possible_delimiters:
#             count_dict[d] = txt.count(d)
#         delimiter = ''
#         score = -1
#         for d in possible_delimiters:
#             if count_dict[d] > score:
#                 score = count_dict[d]
#                 delimiter = d
#         #print('csv_load() delimiter autodetected as %d %r' % (ord(delimiter), delimiter))
#
#     results = []
#     for row in csv.reader(txt.split('\n'), delimiter=delimiter):
#         if row or not skip_blanks:
#             results.append(row)
#
#     return results
#


def parse(data, debug=0):
    """
    This function parses a file object into iclicker responses.
    """
    rows = sheetReader(
        data.name, fileobj=data, input_format="csv", subargs={"encoding": "utf-8"}
    )
    try:
        if rows[0][0] != "Scoring":
            raise ParseError(
                "not a valid i>clicker data file" + " :[0,0] = %r" % rows[0][0]
            )
    except IndexError:
        raise ParseError("not a valid i>clicker data file: no [0,0] element")

    def _header_parts(h):
        """
        The bar (pipe) is used to split individual question headers.
        Various meanings are still not fully known.
        """
        header = h.strip().strip('"').strip("'").lower()
        parts = header.split("|")
        return parts

    # end _header_parts()

    def _is_deleted(h):
        """
        Check for questions marked for deletion.

        Question headers seen, which mark questions for deletion:
            'QUESTION 4|Y ', "Question 12|MC|16|YY"
        """
        parts = _header_parts(h)
        # check deletion mark in the last part -- multipart only.
        if len(parts) > 1 and parts[-1] in ["y", "yy"]:
            return True
        return False

    # end _is_deleted()

    question_indices = None
    student_results = {}  # maps clicker ids to responses
    for row in rows:
        if row[0] == "Question":
            if debug > 2:
                print(row)
            if debug > 4:
                print("len(row) =", len(row))
            num_questions = (len(row) - 3) / 6
            if 6 * num_questions + 3 != len(row):  # sanity check
                raise ParseError("unexpected i>clicker data file format")
            question_indices = range(3, len(row), 6)
            if debug:
                print("question_indices:", question_indices)
            question_headers = [row[i] for i in question_indices]
            if debug:
                print("question_headers:", question_headers)
            # Observed [2011-May-11], another way to mark questions for deletion
            #   ['QUESTION 1 ', 'QUESTION 2 ', 'QUESTION 3 ', 'QUESTION 4|Y ']
            #   (q4 marked for deletion)
            # filter out questions with the |y mark at the end of the header
            # or |YY.
            qfilter = [
                (i, h)
                for i, h in zip(question_indices, question_headers)
                if not _is_deleted(h)
            ]
            if qfilter:
                question_indices, question_headers = zip(*qfilter)
            else:
                raise ParseError(
                    "No non-deleted questions found in valid i>clicker data file"
                )

        if row[0] == "Correct Answer":
            if debug > 2:
                print(row)
            try:
                numeric_correct_answers = [int(row[idx]) for idx in question_indices]
                alpha_correct_answers = [
                    chr(e + ord("A") - 1) if e != 0 else ""
                    for e in numeric_correct_answers
                ]

            except ValueError:
                # this occurs from older software: the answers are already alpha
                numeric_correct_answers = None
                alpha_correct_answers = [row[idx].strip() for idx in question_indices]

            if debug:
                print("numeric_correct_answers:", numeric_correct_answers)
                print("alpha_correct_answers:", alpha_correct_answers)

        if row[0][0] == "#":  # student record
            iclicker = row[0][1:]
            while len(iclicker) < 8:
                iclicker = "0" + iclicker
            responses = [row[idx].strip() for idx in question_indices]
            student_score = mark_student_responses(alpha_correct_answers, responses)
            student_results[iclicker] = responses, student_score
            if debug:
                print(iclicker, responses, student_score)

    # print(num_questions)
    return alpha_correct_answers, student_results


VALID_VOTES = ("A", "B", "C", "D", "E")
NO_CORRECT_ANSWER = ("", "?")


def mark_student_responses(C, R):
    """
        C is the list of correct responses
        R is the list of student responses

        Questions may be marked as either deleted or having no correct answer
        by any non- 'A' through 'E' mark occuring in C.
        Observed deletion marks are:
            'deleted_?', '@',

        Observed no correct answer marks are:
            '', '?'

        Unless something has been observed as a no correct answer, treat it
        as a deleted mark.

        This implementation is perhaps not as clever or fast as some kind of functional
        programming solution, but is easier to see *exactly* what is going on.
    """
    n = len(C)
    score = 0
    for i in range(n):

        if C[i] in NO_CORRECT_ANSWER:
            if R[i] in VALID_VOTES:
                score += 1  # a response with no correct answer

        elif C[i] in VALID_VOTES:  # a correct answer has been set.
            if C[i] == R[i]:
                score += 2  # a correct response
            elif R[i] in VALID_VOTES:
                score += 1  # an incorrect response

    return score


def get_high_score(results):
    return max([score for responses, score in results.values()])


###########################################
# Driver stuff: for testing.


def main(arg):
    correct_responses, results = parse(open(arg), debug=1)
    import pprint

    pprint.pprint(results)
    print("Highest Mark: ", get_high_score(results))


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        main(arg)

#
