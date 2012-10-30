import datetime
from django.db.models.query import EmptyQuerySet
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.models import User as DjangoUser
from redjango import models
from redjango.compat import bind_method


class UserManager(models.Manager):
    create_superuser = bind_method(DjangoUserManager.create_superuser)
    create_user = bind_method(DjangoUserManager.create_user)

class User(models.Model):
    username = models.CharField(_('username'), max_length=30, unique=True, help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
#    email = models.EmailField(_('e-mail address'), blank=True)
    password = models.CharField(_('password'), max_length=128, help_text=_("Use '[algo]$[salt]$[hexdigest]' or use the <a href=\"password/\">change password form</a>."))
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_("Designates whether the user can log into this admin site."))
    is_active = models.BooleanField(_('active'), default=True, help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."))
    is_superuser = models.BooleanField(_('superuser status'), default=False, help_text=_("Designates that this user has all permissions without explicitly assigning them."))
    last_login = models.DateTimeField(_('last login'), default=datetime.datetime.now)
    date_joined = models.DateTimeField(_('date joined'), default=datetime.datetime.now)
#    groups = models.ManyToManyField(Group, verbose_name=_('groups'), blank=True,
#        help_text=_("In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."))
#    user_permissions = models.ManyToManyField(Permission, verbose_name=_('user permissions'), blank=True)
    objects = UserManager()

    set_password = bind_method(DjangoUser.set_password)
    set_unusable_password = bind_method(DjangoUser.set_unusable_password)
    check_password = bind_method(DjangoUser.check_password)
    _message_set = EmptyQuerySet()
