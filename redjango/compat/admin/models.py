from django.contrib.contenttypes.models import ContentType

__author__ = 'tumbler'


from django.contrib.admin.models import LogEntryManager as DjangoLogEntryManager
from django.utils.translation import ugettext_lazy as _

from redjango.compat.auth.models import User
from redjango.compat import bind_method
from redjango import models

class LogEntryManager(models.Manager):
    log_action = bind_method(DjangoLogEntryManager.log_action)

class LogEntry(models.Model):
    action_time = models.DateTimeField(_('action time'), auto_now=True)
    user = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), max_length=200)
    action_flag = models.PositiveSmallIntegerField(_('action flag'))
    change_message = models.TextField(_('change message'), blank=True)
    objects = LogEntryManager()
    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('log entries')
        db_table = 'django_admin_log'
        ordering = ('-action_time',)
