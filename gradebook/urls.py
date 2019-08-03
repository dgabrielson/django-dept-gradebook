from __future__ import print_function, unicode_literals

from django.conf.urls import include, url

from . import conf
from .gb2.urls import urlpatterns

if conf.get("api_v1:enabled"):
    urlpatterns += [url(r"^api/", include("gradebook.api.urls"))]
