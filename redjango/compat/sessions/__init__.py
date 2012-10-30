from django.db.models.loading import register_models

__author__ = 'tumbler'

def patch():
    import django.contrib.sessions.models
    import models
    django.contrib.sessions.models.Session = models.Session
    django.contrib.sessions.models.SessionManager = models.SessionManager
    register_models('django.contrib.sessions', models.Session)

