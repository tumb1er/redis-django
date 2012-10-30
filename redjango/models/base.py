from itertools import izip
import sys
import time
from datetime import datetime, date
from django.core import exceptions
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import router, connections, IntegrityError
from django.db.models.base import ModelState
from redjango.containers import Set, List
from fields import *
from key import Key
from manager import ManagerDescriptor, Manager
from utils import _encode_key, classproperty
from exceptions import FieldValidationError, MissingID, BadKeyError
from redjango.models.options import Options


__all__ = ['Model', 'from_key']

ZINDEXABLE = (IntegerField, DateTimeField, DateField, FloatField)

##############################
# Model Class Initialization #
##############################

def _initialize_attributes(model_class, name, bases, attrs):
    """Initialize the attributes of the model."""
    model_class._attributes = {}
    for k, v in attrs.iteritems():
        if isinstance(v, Field):
            model_class._attributes[k] = v
            v.name = v.name or k

def _initialize_referenced(model_class, attribute):
    """Adds a property to the target of a reference field that
    returns the list of associated objects.
    """
    # this should be a descriptor
    def _related_objects(self):
        return (model_class.objects
                .filter(**{attribute.attname: self.id}))

    klass = attribute._target_type
    if isinstance(klass, basestring):
        return klass, model_class, attribute
    else:
        related_name = (attribute.related_name or
                model_class.__name__.lower() + '_set')
        setattr(klass, related_name,
                property(_related_objects))

def _initialize_lists(model_class, name, bases, attrs):
    """Stores the list fields descriptors of a model."""
    model_class._lists = {}
    for k, v in attrs.iteritems():
        if isinstance(v, ListField):
            model_class._lists[k] = v
            v.name = v.name or k

def _initialize_references(model_class, name, bases, attrs):
    """Stores the list of reference field descriptors of a model."""
    model_class._references = {}
    h = {}
    deferred = []
    for k, v in attrs.iteritems():
        if isinstance(v, ForeignKey):
            model_class._references[k] = v
            v.name = v.name or k
            att = Field(name=v.attname)
            h[v.attname] = att
            setattr(model_class, v.attname, att)
            refd = _initialize_referenced(model_class, v)
            if refd:
                deferred.append(refd)
    attrs.update(h)
    return deferred

def _initialize_indices(model_class, name, bases, attrs):
    """Stores the list of indexed attributes."""
    model_class._indices = []
    for k, v in attrs.iteritems():
        if isinstance(v, (Field, ListField, ForeignKey)) and v.db_index:
            model_class._indices.append(k)
    if model_class._meta['indices']:
        model_class._indices.extend(model_class._meta['indices'])

def _initialize_counters(model_class, name, bases, attrs):
    """Stores the list of counter fields."""
    model_class._counters = []
    for k, v in attrs.iteritems():
        if isinstance(v, Counter):
            model_class._counters.append(k)

def _initialize_key(model_class, name):
    """Initializes the key of the model."""
    model_class._key = Key(model_class._meta['key'] or name)


def _initialize_manager(model_class):
    """Initializes the objects manager attribute of the model."""
    model_class.objects = ManagerDescriptor(Manager(model_class))

def subclass_exception(name, parents, module):
    return type(name, parents, {'__module__': module})


_deferred_refs = []

class ModelBase(type):
    """Metaclass of the Model."""

    def __new__(cls, name, bases, attrs):
        super_new = super(ModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)
        abstract = getattr(attr_meta, 'abstract', False)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        if getattr(meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            kwargs = {"app_label": model_module.__name__.split('.')[-2]}
        else:
            kwargs = {}

        new_class.add_to_class('_meta', Options(meta, **kwargs))

        global _deferred_refs
        deferred = _initialize_references(new_class, name, bases, attrs)
        _deferred_refs.extend(deferred)
        _initialize_attributes(new_class, name, bases, attrs)
        _initialize_counters(new_class, name, bases, attrs)
        _initialize_lists(new_class, name, bases, attrs)
        _initialize_indices(new_class, name, bases, attrs)
        _initialize_key(new_class, name)
        _initialize_manager(new_class)
        # if targeted by a reference field using a string,
        # override for next try
        for target, model_class, att in _deferred_refs:
            if name == target:
                att._target_type = new_class
                _initialize_referenced(model_class, att)

        if not abstract:
            new_class.add_to_class('DoesNotExist', subclass_exception('DoesNotExist',
                tuple(x.DoesNotExist
                    for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                or (ObjectDoesNotExist,), module))
            new_class.add_to_class('MultipleObjectsReturned', subclass_exception('MultipleObjectsReturned',
                tuple(x.MultipleObjectsReturned
                    for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                or (MultipleObjectsReturned,), module))
            if base_meta and not base_meta.abstract:
                # Non-abstract child classes inherit some attributes from their
                # non-abstract parent (unless an ABC comes before it in the
                # method resolution order).
                if not hasattr(meta, 'ordering'):
                    new_class._meta.ordering = base_meta.ordering
                if not hasattr(meta, 'get_latest_by'):
                    new_class._meta.get_latest_by = base_meta.get_latest_by

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        return new_class


    def AAAA(cls, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, ModelBase)]
        module = attrs.pop('__module__')
        super(ModelBase, cls).__init__(name, bases, attrs)
        cls.add_to_class('_meta', Options(attrs.pop('Meta', None)))
        cls._meta.local_fields = []
        for fname, field in attrs.iteritems():
            cls.add_to_class(fname, field)
        global _deferred_refs
        deferred = _initialize_references(cls, name, bases, attrs)
        _deferred_refs.extend(deferred)
        _initialize_attributes(cls, name, bases, attrs)
        _initialize_counters(cls, name, bases, attrs)
        _initialize_lists(cls, name, bases, attrs)
        _initialize_indices(cls, name, bases, attrs)
        _initialize_key(cls, name)
        _initialize_manager(cls)
        # if targeted by a reference field using a string,
        # override for next try
        for target, model_class, att in _deferred_refs:
            if name == target:
                att._target_type = cls
                _initialize_referenced(model_class, att)

        cls.add_to_class('DoesNotExist', subclass_exception('DoesNotExist',
            tuple(x.DoesNotExist
                for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
            or (ObjectDoesNotExist,), module))
        print cls.DoesNotExist
        cls.add_to_class('MultipleObjectsReturned', subclass_exception('MultipleObjectsReturned',
            tuple(x.MultipleObjectsReturned
                for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
            or (MultipleObjectsReturned,), module))

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


class Model(object):
    __metaclass__ = ModelBase
    _attributes = None
    _lists = None
    _indices = None
    _references = None
    _counters = None
    _key = None
    objects = None
    _deferred = False

    class DoesNotExist(exceptions.ObjectDoesNotExist):
        pass

    def __init__(self, *args, **kwargs):
        self.update_attributes(*args, **kwargs)

        self._state = ModelState()

    def is_valid(self):
        """Returns True if all the fields are valid.

        It first validates the fields (required, unique, etc.)
        and then calls the validate method.
        """
        self._errors = []
        for field in self.fields:
            try:
                field.validate(self)
            except FieldValidationError, e:
                self._errors.extend(e.errors)
        self.validate()
        return not bool(self._errors)

    def validate(self):
        """Overriden in the model class.

        Do custom validation here. Add tuples to self._errors.

        Example:

            class Person(Model):
                name = Field(required=True)

                def validate(self):
                    if name == 'Nemo':
                        self._errors.append(('name', 'cannot be Nemo'))

        """
        pass

    def update_attributes(self, *args, **kwargs):
        """Updates the attributes of the model."""
        attrs = self.attributes.values() + self.lists.values() \
                + self.references.values()
        fields_iter = iter(self._meta.fields)
        # Handling *args
        for val, field in izip(args, fields_iter):
            field.__set__(self, val)
            kwargs.pop(field.name, None)
        # Handling defaults
        for field in fields_iter:
            if kwargs:
                try:
                    val = kwargs.pop(field.attname)
                except KeyError:
                    # This is done with an exception rather than the
                    # default argument on pop because we don't want
                    # get_default() to be evaluated, and then not used.
                    # Refs #12057.
                    val = field.get_default()
            else:
                val = field.get_default()
            field.__set__(self, val)

        print self.__dict__

    def save(self, force_insert=False, force_update=False, using=None):
        """Saves the instance to the datastore."""
        if not self.is_valid():
            raise IntegrityError(self._errors)
        _new = self.is_new()
        if _new:
            self._initialize_id()
        with Mutex(self):
            self._write(_new)
        return True

    def key(self, att=None):
        """Returns the Redis key where the values are stored."""
        if att is not None:
            return self._key[self.id][att]
        else:
            return self._key[self.id]

    def delete(self):
        """Deletes the object from the datastore."""
        connection = router.db_for_write(self.__class__, instance=self)
        db = connections[connection]
        pipeline = db.pipeline()
        self._delete_from_indices(pipeline)
        self._delete_membership(pipeline)
        pipeline.delete(self.key())
        pipeline.execute()

    def is_new(self):
        """Returns True if the instance is new.

        Newness is based on the presence of the _id attribute.
        """
        return not hasattr(self, '_id')

    def incr(self, att, val=1):
        """Increments a counter."""
        if att not in self.counters:
            raise ValueError("%s is not a counter.")
        connection = router.db_for_write(self.__class__, instance=self)
        db = connections[connection]
        db.hincrby(self.key(), att, val)

    def decr(self, att, val=1):
        """Decrements a counter."""
        self.incr(att, -1 * val)


    @property
    def attributes_dict(self):
        """Returns the mapping of the model attributes and their
        values.
        """
        h = {}
        for k in self.attributes.keys():
            h[k] = getattr(self, k)
        for k in self.lists.keys():
            h[k] = getattr(self, k)
        for k in self.references.keys():
            h[k] = getattr(self, k)
        return h


    @property
    def id(self):
        """Returns the id of the instance.

        Raises MissingID if the instance is new.
        """
        if not hasattr(self, '_id'):
            raise MissingID
        return self._id

    @id.setter
    def id(self, val):
        """Returns the id of the instance as a string."""
        self._id = str(val)

    @property
    def db(self):
        """Return the database that will be used if
        this query is executed now"""
        # FIXME
        raise NotImplementedError()

    @property
    def errors(self):
        """Returns the list of errors after validation."""
        if not hasattr(self, '_errors'):
            self.is_valid()
        return self._errors

    @property
    def fields(self):
        """Returns the list of field names of the model."""
        return (self.attributes.values() + self.lists.values()
                + self.references.values())

    #################
    # Class Methods #
    #################

    @classproperty
    def attributes(cls):
        """Return the attributes of the model.

        Returns a dict with models attribute name as keys
        and attribute descriptors as values.
        """
        return dict(cls._attributes)

    @classproperty
    def lists(cls):
        """Returns the lists of the model.

        Returns a dict with models attribute name as keys
        and ListField descriptors as values.
        """
        return dict(cls._lists)

    @classproperty
    def indices(cls):
        """Return a list of the indices of the model."""
        return cls._indices

    @classproperty
    def references(cls):
        """Returns the mapping of reference fields of the model."""
        return cls._references

    @classproperty
    def counters(cls):
        """Returns the mapping of the counters."""
        return cls._counters

    @classmethod
    def exists(cls, id):
        """Checks if the model with id exists."""
        using = router.db_for_read(cls)
        connection = connections[using]
        return bool(connection.exists(cls._key[str(id)]) or
                    connection.sismember(cls._key['all'], str(id)))

    ###################
    # Private methods #
    ###################

    def _initialize_id(self):
        """Initializes the id of the instance."""
        if not self._meta.pk:
            using = router.db_for_write(self.__class__, instance=self)
            connection = connections[using]
            self.id = str(connection.incr(self._key['id']))
        else:
            self.id = getattr(self, self._meta.pk.name)

    def _write(self, _new=False):
        """Writes the values of the attributes to the datastore.

        This method also creates the indices and saves the lists
        associated to the object.
        """
        using = router.db_for_write(self.__class__, instance=self)
        connection = connections[using]
        pipeline = connection.pipeline()
        self._create_membership(pipeline)
        self._update_indices(pipeline)
        h = {}
        # attributes
        for k, v in self.attributes.iteritems():
            if isinstance(v, DateTimeField):
                if v.auto_now:
                    setattr(self, k, datetime.now())
                if v.auto_now_add and _new:
                    setattr(self, k, datetime.now())
            elif isinstance(v, DateField):
                if v.auto_now:
                    setattr(self, k, date.today())
                if v.auto_now_add and _new:
                    setattr(self, k, date.today())
            for_storage = getattr(self, k)
            if for_storage is not None:
                h[k] = v.typecast_for_storage(for_storage)
        # indices
        for index in self.indices:
            if index not in self.lists and index not in self.attributes:
                v = getattr(self, index)
                if callable(v):
                    v = v()
                if v:
                    try:
                        h[index] = unicode(v)
                    except UnicodeError:
                        h[index] = unicode(v.decode('utf-8'))
        pipeline.delete(self.key())
        if h:
            pipeline.hmset(self.key(), h)

        # lists
        for k, v in self.lists.iteritems():
            l = List(self.key()[k], pipeline=pipeline)
            l.clear()
            values = getattr(self, k)
            if values:
                if v._redjango_model:
                    l.extend([item.id for item in values])
                else:
                    l.extend(values)
        pipeline.execute()

    ##############
    # Membership #
    ##############

    def _create_membership(self, pipeline=None):
        """Adds the id of the object to the set of all objects of the same
        class.
        """
        Set(self._key['all'], pipeline=pipeline).add(self.id)

    def _delete_membership(self, pipeline=None):
        """Removes the id of the object to the set of all objects of the
        same class.
        """
        Set(self._key['all'], pipeline=pipeline).remove(self.id)


    ############
    # INDICES! #
    ############

    def _update_indices(self, pipeline=None):
        """Updates the indices of the object."""
        self._delete_from_indices(pipeline)
        self._add_to_indices(pipeline)

    def _add_to_indices(self, pipeline):
        """Adds the base64 encoded values of the indices."""
        for att in self.indices:
            self._add_to_index(att, pipeline=pipeline)

    def _add_to_index(self, att, val=None, pipeline=None):
        """
        Adds the id to the index.

        This also adds to the _indices set of the object.
        """
        index = self._index_key_for(att)
        if index is None:
            return
        t, index = index
        if t == 'attribute':
            pipeline.sadd(index, self.id)
            pipeline.sadd(self.key()['_indices'], index)
        elif t == 'list':
            for i in index:
                pipeline.sadd(i, self.id)
                pipeline.sadd(self.key()['_indices'], i)
        elif t == 'sortedset':
            zindex, index = index
            pipeline.sadd(index, self.id)
            pipeline.sadd(self.key()['_indices'], index)
            descriptor = self.attributes[att]
            score = descriptor.typecast_for_storage(getattr(self, att))
            pipeline.zadd(zindex, self.id, score)
            pipeline.sadd(self.key()['_zindices'], zindex)


    def _delete_from_indices(self, pipeline):
        """Deletes the object's id from the sets(indices) it has been added
        to and removes its list of indices (used for housekeeping).
        """
        s = Set(self.key()['_indices'])
        z = Set(self.key()['_zindices'])
        for index in s.members:
            pipeline.srem(index, self.id)
        for index in z.members:
            pipeline.zrem(index, self.id)
        pipeline.delete(s.key)
        pipeline.delete(z.key)

    def _index_key_for(self, att, value=None):
        """Returns a key based on the attribute and its value.

        The key is used for indexing.
        """
        if value is None:
            value = getattr(self, att)
            if callable(value):
                value = value()
        if value is None:
            return None
        if att not in self.lists:
            return self._get_index_key_for_non_list_attr(att, value)
        else:
            return self._tuple_for_index_key_attr_list(att, value)

    def _get_index_key_for_non_list_attr(self, att, value):
        descriptor = self.attributes.get(att)
        if descriptor and isinstance(descriptor, ZINDEXABLE):
            #noinspection PyUnresolvedReferences
            sval = descriptor.typecast_for_storage(value)
            return self._tuple_for_index_key_attr_zset(att, value, sval)
        elif descriptor:
            val = descriptor.typecast_for_storage(value)
            return self._tuple_for_index_key_attr_val(att, val)
        else:
            # this is non-attribute index defined in Meta
            return self._tuple_for_index_key_attr_val(att, value)

    def _tuple_for_index_key_attr_val(self, att, val):
        return 'attribute', self._index_key_for_attr_val(att, val)

    def _tuple_for_index_key_attr_list(self, att, val):
        return 'list', [self._index_key_for_attr_val(att, e) for e in val]

    def _tuple_for_index_key_attr_zset(self, att, val, sval):
        return ('sortedset',
                (self._key[att], self._index_key_for_attr_val(att, sval)))

    def _index_key_for_attr_val(self, att, val):
        return self._key[att][_encode_key(val)]

    ##################
    # Python methods #
    ##################

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.key() == other.key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        if not self.is_new():
            return "<%s %s>" % (self.key(), self.attributes_dict)
        return "<%s %s>" % (self.__class__.__name__, self.attributes_dict)



def get_model_from_key(key):
    """Gets the model from a given key."""
    _known_models = {}
    model_name = key.split(':', 2)[0]
    # populate
    for klass in Model.__subclasses__():
        _known_models[klass.__name__] = klass
    return _known_models.get(model_name, None)


def from_key(key):
    """Returns the model instance based on the key.

    Raises BadKeyError if the key is not recognized by
    redjango or no defined model can be found.
    Returns None if the key could not be found.
    """
    model = get_model_from_key(key)
    if model is None:
        raise BadKeyError
    try:
        _, id = key.split(':', 2)
        id = int(id)
    except ValueError, TypeError:
        raise BadKeyError
    return model.objects.get_by_id(id)


class Mutex(object):
    """Implements locking so that other instances may not modify it.

    Code ported from Ohm.
    """
    def __init__(self, instance):
        self.instance = instance

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.unlock()

    def lock(self):
        o = self.instance
        using = router.db_for_write(o.__class__, instance=o)
        connection = connections[using]
        while not connection.setnx(o.key('_lock'), self.lock_timeout):
            lock = connection.get(o.key('_lock'))
            if not lock:
                continue
            if not self.lock_has_expired(lock):
                time.sleep(0.5)
                continue
            lock = connection.getset(o.key('_lock'), self.lock_timeout)
            if not lock:
                break
            if self.lock_has_expired(lock):
                break

    def lock_has_expired(self, lock):
        return float(lock) < time.time()

    def unlock(self):
        using = router.db_for_write(self.instance.__class__,
            instance=self.instance)
        connection = connections[using]
        connection.delete(self.instance.key('_lock'))

    @property
    def lock_timeout(self):
        return "%f" % (time.time() + 1.0)

