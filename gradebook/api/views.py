"""
API views for the gradebook.
"""
from __future__ import print_function, unicode_literals

from django.views.decorators.csrf import csrf_exempt

from .utils import handle_api_change_request, process_submitted_grade_data

#######################################################################

#######################################################################


@csrf_exempt
def submit_grades(request):
    return handle_api_change_request(
        request, process_submitted_grade_data, data_key="grade_data"
    )


#######################################################################
