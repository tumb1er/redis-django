# coding: utf-8

# $Id: $
from django.conf import settings
try:
    REDJANGO_DEFAULT_DATABASE = settings.REDJANGO_DEFAULT_DATABASE
except AttributeError:
    REDJANGO_DEFAULT_DATABASE = 'redis'

from redjango.backend.base import DatabaseWrapper
from django.db import connections
from django.core.exceptions import ImproperlyConfigured

try:
    connection = connections[REDJANGO_DEFAULT_DATABASE]
    if type(connection) is not DatabaseWrapper:
        raise ImproperlyConfigured(
            '%s database ENGINE must be "redjango.backend"')
except KeyError:
    raise ImproperlyConfigured(
        '%s database not configured in settings.DATABASES'
        % settings.REDJANGO_DEFAULT_DATABASE)
