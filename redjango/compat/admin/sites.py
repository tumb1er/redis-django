from django.conf import settings
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AlreadyRegistered, AdminSite as DjangoAdminSite
from django.core.exceptions import ImproperlyConfigured
from redjango.models.base import ModelBase
from django.db.models.base import ModelBase as DjangoModelBase

class AdminSite(DjangoAdminSite):
    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if not admin_class:
            admin_class = ModelAdmin

        # Don't import the humongous validation code unless required
        if admin_class and settings.DEBUG:
            from django.contrib.admin.validation import validate
        else:
            validate = lambda model, adminclass: None

        if (isinstance(model_or_iterable, ModelBase) or
            isinstance(model_or_iterable, DjangoModelBase)):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                                           'cannot be registered with admin.' % model.__name__)

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            if options:
                # For reasons I don't quite understand, without a __module__
                # the created class appears to "live" in the wrong place,
                # which causes issues later on.
                options['__module__'] = __name__
                admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

            # Validate (which might be a no-op)
            validate(admin_class, model)

            # Instantiate the admin class to save in the registry
            self._registry[model] = admin_class(model, self)