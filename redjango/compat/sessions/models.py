from redjango import models
from django.utils.translation import ugettext_lazy as _


class SessionManager(models.Manager):
    def encode(self, session_dict):
        """
        Returns the given session dictionary pickled and encoded as a string.
        """
        return SessionStore().encode(session_dict)

    def save(self, session_key, session_dict, expire_date):
        s = self.model(session_key, self.encode(session_dict), expire_date)
        if session_dict:
            s.save()
        else:
            s.delete() # Clear sessions with no data.
        return s


class Session(models.Model):
    session_key = models.CharField(_('session key'), max_length=40,
        primary_key=True)
    session_data = models.TextField(_('session data'))
    expire_date = models.DateTimeField(_('expire date'), db_index=True)
    objects = SessionManager()


from redjango.compat.sessions.backends.db import SessionStore
