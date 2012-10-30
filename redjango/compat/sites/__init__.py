# coding: utf-8

# $Id: $
from django.db.models.loading import register_models

__author__ = 'tumbler'
import models

def patch():
    import django.contrib.sites
    django.contrib.sites.models.Site = models.Site
    django.contrib.sites.models.SiteManager = models.SiteManager
    register_models('django.contrib.sites', models.Site)