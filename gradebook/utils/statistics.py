"""
Statistics helpers.  For a score queryset.
"""
#######################################################################

from __future__ import print_function, unicode_literals

import gnuplot_data

from ..gb2.formulalib.formulacalc import FormulaCalc

#######################################################################


def get_numeric_scores(score_qs):
    values = [
        FormulaCalc.floatNone(s) for s in score_qs.values_list("value", flat=True)
    ]
    count_all = len(values)
    values = [v for v in values if v is not None]
    count = len(values)
    return count, count_all, values


#######################################################################


def statistics(score_qs):
    """
    Calculate statistics for the given score queryset.
    We can't use database aggregation because the value field of a score
    is not necessarily numeric.
    Returns ``None`` if this is not appropriate.
    Otherwise returns a dictionary of statistics.
    """
    count, count_all, values = get_numeric_scores(score_qs)
    if count == 0:
        return

    S = float(sum(values))
    result = {"count": count, "min": min(values), "max": max(values), "avg": S / count}
    if count > 1:
        result["variance"] = sum([(x - result["avg"]) ** 2 for x in values]) / (
            count - 1
        )
        result["stddev"] = result["variance"] ** 0.5

    if count != count_all:
        result["count_all"] = count_all
        result["avg_all"] = S / count_all
        if count_all > 1:
            result["variance_all"] = sum(
                [(x - result["avg_all"]) ** 2 for x in values]
            ) / (count_all - 1)
            result["stddev_all"] = result["variance_all"] ** 0.5

    return result


#######################################################################


def histogram_img(score_qs, size="400,300"):
    """
    Generate a histogram image for a score queryset.
    Returns ``None`` if this is not appropriate (or the image construction fails).
    Otherwise returns a (datastream, content_type) pair.
    """
    count, count_all, values = get_numeric_scores(score_qs)
    if count < 1:
        return
    min_ = min(values)
    max_ = max(values)

    script = """set key off
set style fill solid
set style fill solid border -1
binwidth=(%(max)s-%(min)s)/10
set boxwidth binwidth
set xrange [%(min)s-binwidth : %(max)s+binwidth]
bin(x,width)=width*floor(x/width)
""" % {
        "max": max_,
        "min": min_,
    }
    script += (
        "plot '%(datafile)s' using (bin($1,binwidth)):(1.0) smooth freq with boxes lt 3"
    )

    terminal = "png transparent size " + size
    content_type = "image/png"

    img_data = gnuplot_data.Plot(data=values, script=script, terminal=terminal).plot()
    if not img_data:
        return

    return img_data, content_type


#######################################################################
