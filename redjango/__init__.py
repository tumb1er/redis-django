# coding: utf-8

# $Id: $
from redjango import settings
from redjango.backend.base import DatabaseWrapper
from django.db import connections
from django.core.exceptions import ImproperlyConfigured


try:
    connection = connections[settings.REDJANGO_DEFAULT_DATABASE]
    if type(connection) is not DatabaseWrapper:
        raise ImproperlyConfigured(
            '%s database ENGINE must be "redjango.backend"')
except KeyError:
    raise ImproperlyConfigured(
        '%s database not configured in settings.DATABASES'
            % settings.REDJANGO_DEFAULT_DATABASE)
