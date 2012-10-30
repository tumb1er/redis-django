from bisect import bisect
import re
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.db.models.options import Options as DjangoOptions, get_verbose_name, DEFAULT_NAMES
from django.utils.translation import string_concat
from redjango.compat import bind_method

class Options(object):
    """Handles options defined in Meta class of the model.

    Example:

        class Person(models.Model):
            name = models.Field()

            class Meta:
                indices = ('full_name',)
                db = redis.Redis(host='localhost', port=29909)

    """
    def __init__(self, meta, app_label=None):
        self.meta = meta
        self.app_label = app_label
        self._meta = None
        self.abstract = False
        self._inherited = False
        self.concrete_managers = []
        self.abstract_managers = []
        self.auto_created = False
        self.local_many_to_many = []
        self.local_fields = []
        self.ordering = None
        self.unique_together = []
        self.order_with_respect_to = None
        self.pk = None


    def get_field(self, field_name, many_to_many=False):
        if self._meta is None:
            return None
        try:
            return self._meta.__dict__[field_name]
        except KeyError:
            return None
    __getitem__ = get_field

    def _fields(self):
        return self.local_fields

    fields = property(_fields)

    def _many_to_many(self):
        # FIXME: implement when M2M support is ready
        return list()
    many_to_many = property(_many_to_many)

    def add_field(self, field):
        self.local_fields.insert(bisect(self.local_fields, field), field)
        self.setup_pk(field)

    def contribute_to_class(self, cls, name):
        from django.db import connection
        from django.db.backends.util import truncate_name

        cls._meta = self
        self.installed = re.sub('\.models$', '', cls.__module__) in settings.INSTALLED_APPS
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

#            # unique_together can be either a tuple of tuples, or a single
#            # tuple of two strings. Normalize it to a tuple of tuples, so that
#            # calling code can uniformly expect that.
#            ut = meta_attrs.pop('unique_together', self.unique_together)
#            if ut and not isinstance(ut[0], (tuple, list)):
#                ut = (ut,)
#            self.unique_together = ut

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            if self.verbose_name_plural is None:
                self.verbose_name_plural = string_concat(self.verbose_name, 's')

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta

    def setup_pk(self, field):
        if not self.pk and field.primary_key:
            self.pk = field
            field.serialize = False