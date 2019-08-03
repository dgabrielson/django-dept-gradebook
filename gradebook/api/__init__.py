"""
The Gradebook application does not require lmslink as a standalone,
however the lmslink application is required for the Gradebook API.
"""
from __future__ import print_function, unicode_literals

from django.core.exceptions import ImproperlyConfigured

try:
    import lmslink  # make sure this is available.
except ImportError:
    raise ImproperlyConfigured(
        "The lmslink application is required for the gradebook.api."
    )
