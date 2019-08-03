#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from xml.etree import ElementTree

from django.utils import six


class ParseError(Exception):
    pass


def xml_load(input_filename_or_fp):
    """
    This function is designed to be 'the' csv loading code.
    """
    if isinstance(input_filename_or_fp, six.string_types):
        fp = open(input_filename_or_fp)
    else:
        fp = input_filename_or_fp
    contents = fp.read().strip()
    root = ElementTree.fromstring(contents)
    return root


def parse(input_filename_or_fp, use_iclicker_scores=False, debug=0):
    """
    This function parses a file object into iclicker responses.
    """
    root = xml_load(input_filename_or_fp)
    poll_list = [p for p in root if p.tag == "p"]
    if not poll_list:
        raise ParseError("not a valid i>clicker XML data file")
    correct_answer_list = []
    student_results = {}  # maps clicker ids to responses<list>, student_score<numeric>
    for p in poll_list:
        # polls are questions asked.
        if p.attrib["isDel"] not in ["Y", "N"]:
            raise ParseError("Unknown delete marker {0!r}".format(p.attrib["isDel"]))
        if p.attrib["isDel"] == "Y":
            continue
        correct_answer = p.attrib["cans"]
        correct_answer_list.append(correct_answer)
        vote_list = [v for v in p if v.tag == "v"]
        for v in vote_list:
            iclicker = v.attrib["id"][1:]
            while len(iclicker) < 8:
                iclicker = "0" + iclicker
            if iclicker not in student_results:
                student_results[iclicker] = [[], 0]
            student_results[iclicker][0].append(v.attrib["ans"])
            score = 0
            if use_iclicker_scores:
                score = v.attrib["scr"]
            elif v.attrib["ans"]:  # manual scoring.
                if v.attrib["ans"] == correct_answer:
                    score = 2
                else:
                    score = 1
            student_results[iclicker][1] += score
    return correct_answer_list, student_results


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
