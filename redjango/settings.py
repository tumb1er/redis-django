# coding: utf-8

# $Id: $
from django.conf import settings
try:
    REDJANGO_DEFAULT_DATABASE = settings.REDJANGO_DEFAULT_DATABASE
except AttributeError:
    REDJANGO_DEFAULT_DATABASE = 'redis'
