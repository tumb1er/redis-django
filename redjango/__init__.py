# coding: utf-8

# $Id: $
from django.db import connections
from django.conf import settings
connection = connections[settings.REDJANGO_DEFAULT_DATABASE]

