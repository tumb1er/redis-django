from query import QuerySet

############
# Managers #
############

class ManagerDescriptor(object):
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, owner):
        if instance is not None:
            raise AttributeError
        return self.manager


class Manager(object):
    def __init__(self, model=None):
        self.model = model
        self._inherited = False
        self.creation_counter = 0
        self._db = None

    def contribute_to_class(self, model, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.model = model
        setattr(model, name, ManagerDescriptor(self))
        if not getattr(model, '_default_manager', None) or self.creation_counter < model._default_manager.creation_counter:
            model._default_manager = self
        if model._meta.abstract or (self._inherited and not self.model._meta.proxy):
            model._meta.abstract_managers.append((self.creation_counter, name,
                                                  self))
        else:
            model._meta.concrete_managers.append((self.creation_counter, name,
                                                  self))

    def get_query_set(self):
        return QuerySet(self.model)

    def all(self):
        return self.get_query_set()

    def create(self, **kwargs):
        return self.get_query_set().create(**kwargs)

    def get_or_create(self, **kwargs):
        return self.get_query_set().get_or_create(**kwargs)

    def filter(self, **kwargs):
        return self.get_query_set().filter(**kwargs)

    def exclude(self, **kwargs):
        return self.get_query_set().exclude(**kwargs)

    def get_by_id(self, id):
        return self.get_query_set().get_by_id(id)

    def order(self, field):
        return self.get_query_set().order(field)

    def zfilter(self, **kwargs):
        return self.get_query_set().zfilter(**kwargs)

    def get(self, **kwargs):
        if len(kwargs) == 1 and ('id' in kwargs or 'pk' in kwargs):
            pk = kwargs.get('id', kwargs.get('pk'))
            if pk:
                return self.get_by_id(pk)
        filters = {}
        zfilters = {}
        for k,v in kwargs.items():
            if '__' in k:
                zfilters[k] = v
            else:
                filters[k] = v
        res = self.filter(**filters)
        if zfilters:
            res = res.zfilter(**zfilters)
        if not len(res):
            raise self.model.DoesNotExist
        if len(res) > 1:
            raise self.model.MultipleObjectsReturned
        print res[0].__dict__
        return res[0]


