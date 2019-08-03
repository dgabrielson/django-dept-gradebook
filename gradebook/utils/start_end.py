"""
Determine (with the help of the current app config), the start and
end times for role/viewport combinations.
"""
################################################################
from __future__ import print_function, unicode_literals

from datetime import timedelta

from .. import conf

################################################################


def get_start_end(role_type, viewport, semester=None):
    """
    get_start_end(role_type, viewport, semester=None) -> dtstart, dtend
    
    Returns the adjusted start and end (TZ aware) datetimes for the given
    role and viewport.
    """
    extents = conf.get("role_extents_by_term")
    term_extents = None
    if semester is not None:
        term_extents = extents.get(semester.term, None)

    if term_extents is not None:
        default_extents = term_extents.get("default", (0, 0))
        role_extents = term_extents.get(role_type, default_extents)
    else:
        role_extents = (0, 0)

    start_days = role_extents[0]
    end_days = role_extents[1]

    start = viewport.ledger.dtstart + timedelta(days=start_days)
    end = viewport.ledger.dtend + timedelta(days=end_days)

    return start, end


################################################################
