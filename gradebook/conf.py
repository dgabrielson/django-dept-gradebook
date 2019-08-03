"""
The DEFAULT configuration is loaded when the named _CONFIG dictionary
is not present in your settings.
"""
#########################################################################
from __future__ import print_function, unicode_literals

from django.conf import settings
from gradebook.utils.gradebook_ledger import (
    default_ledger_from_section,
    default_role_from_id,
    default_viewport_from_section,
)

#########################################################################

CONFIG_NAME = "GRADEBOOK_CONFIG"  # must be uppercase!

#########################################################################

#########################################################################

DEFAULT = {
    # Grace period for current sections:
    "grace_period_days": 21,
    # Use the cache framework for (computed) scores.
    #    "cache:enabled": True,
    # Default timeout for cached score values (in seconds)
    #    "cache:timeout": 600,
    # These callables allow automatic creation of ledgers and viewports
    #   from the classes.Section model; if you do not want this; you
    #   can specify ``None`` for these values (disabling automatic creation)
    # These callables should return the relevant model instance;
    #   ledger_from_section(LedgerModel, section_obj) -> ledger_obj
    #   viewport_from_section(LedgerModel, LedgerViewportModel, section_obj) -> viewport_obj
    # Or, they may also return ``None``, indicated that this section does not get an
    #   (automatically created) model instance.
    # NOTE: use GRADEBOOK_CONFIG_PROTECTED dictionary in settings
    #   to override these values.
    "ledger_from_section": default_ledger_from_section,
    "viewport_from_section": default_viewport_from_section,
    "role_from_id": default_role_from_id,
    # role extents: how many days to buffer around the sectionschedule date range
    "role_extents_by_term": {
        "1": {"default": (-3, +25), "in": (-10, +30), "co": (-10, +30)},
        "2": {"default": (-3, +5), "in": (-10, +10), "co": (-10, +10)},
        "3": {"default": (-3, +25), "in": (-10, +30), "co": (-10, +30)},
    },
    # roles for sectionschedule instructors, by type of schedule:
    "sectionschedule_roles": {"Lecture": "in", "Laboratory": "ld", "Tutorial": "ta"},
    # The label of the i-clicker requirement flag.
    "iclicker_requirement_label": "i-clicker",
    # The indicator for a score for which calculation in progress/pending
    #   used in place of a score
    "calc_indicator": "#",
    # The indicator for an empty score (distinct from 0)
    #   used in place of a score
    "no_score_indicator": "NS",
    # The indicator for when an override is active on a score
    #   used as a score suffix
    "override_indicator": "*",
    # FileSystemStorage location argument when uploading
    #   spreadsheet of marks.
    "spreadsheet-upload:file-storage-kwargs": {
        "location": "/dev/null",
        "base_url": None,
    },
    # Set the True to enable the v1 api. (Used by statsportal only.)
    "api_v1:enabled": False,
    # By default, the gradebook API will mail_admins() on processing
    # failures.  If this is ``True``, then mail_admins() is done for
    # every request.
    "api:report": False,
    # The gradebook API can fail do to a processing success; in which
    # case we may still want a report.
    # (The "errors" list is non-empty; but still a 2xx response.)
    "api:report-errors": False,
    # By default, when sending API report/error emails, POST input
    # is not included, as it can be fairly verbose.  If this is
    # ``True``, then request.POST will be included.
    "api:report:show-input": False,
    # Should be a function such as, round, math.ceil, math.floor, or None for
    #    identity.  Note: Set this to a function, not a function name!
    # Further note: any function mapping a single float to a single float
    #    is allowable. (In math-ese, any f: R -> R, where None is the identity).
    "api:grade-import-fix": None,
}

#########################################################################


def get(setting):
    """
    get(setting) -> value

    setting should be a string representing the application settings to
    retrieve.
    """
    assert setting in DEFAULT, "the setting %r has no default value" % setting
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    protected_name = CONFIG_NAME + "_PROTECTED"
    protected_settings = getattr(settings, protected_name, {})
    app_settings.update(protected_settings)
    return app_settings.get(setting, DEFAULT[setting])


def get_all():
    """
    Return all current settings as a dictionary.
    """
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    return dict(
        [(setting, app_settings.get(setting, DEFAULT[setting])) for setting in DEFAULT]
    )


#########################################################################
