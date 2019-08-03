# -*- coding: utf-8 -*-
#
# Utility functions
#
from __future__ import print_function, unicode_literals

import datetime

#############################################################################

# def get_grace():
#     """
#     Get the grace period.  This may be more complicated in the future
#     """
#     from .. import conf
#     return conf.get('grace_period_days')

#############################################################################

# def make_instance_name(filename):
#     filename = filename.lower()
#     if filename.endswith('[1].csv'):    # weird MS/FTP fake filesystem stuff.
#         filename = filename[:-7] + '.csv'
#     try:
#         D = datetime.datetime.strptime(filename, 'l%y%m%d%H%M.csv')
#         return 'i>clicker session ' + D.strftime('%Y-%m-%d %H:%M')
#     except ValueError:
#         return 'i>clicker session ' + filename.lower()
#

#############################################################################


def unslugify(value):
    """
    A very basic undoing of slugify
    """
    return value.replace("_", " ").replace("-", " ")


#############################################################################
