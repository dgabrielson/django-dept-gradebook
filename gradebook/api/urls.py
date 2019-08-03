"""
Urls for the gradebook api
"""
from __future__ import print_function, unicode_literals

from django.conf.urls import url

urlpatterns = [
    url(
        r"^submit-grades/$",
        "gradebook.api.views.submit_grades",
        name="gradebook-api-submit-grades",
    )
]
