# coding: utf-8

# $Id: $

class RedjangoRouter(object):
    """Роутер для поддержки Redjango"""
    # pylint: disable=C0111,W0613,R0201,C0103
    def db_for_read(self, model, **hints):
        from redjango import settings
        from redjango.models.base import ModelBase
        if isinstance(model, ModelBase):
            return  settings.REDJANGO_DEFAULT_DATABASE

    def db_for_write(self, model, **hints):
        from redjango import settings
        from redjango.models.base import ModelBase
        if isinstance(model, ModelBase):
            return  settings.REDJANGO_DEFAULT_DATABASE

    def allow_syncdb(self, db, model):
        from redjango.models.base import ModelBase
        return not isinstance(model, ModelBase)

    def allow_relation(self, obj1, obj2, **hints):
        from redjango.models.base import Model
        if isinstance(obj1, Model) and isinstance(obj2, Model):
            return True
        if isinstance(obj1, Model) or isinstance(obj2, Model):
            return False
        