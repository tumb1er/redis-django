# coding: utf-8
from django.core.exceptions import ValidationError
from django.test import TestCase
import redjango
import redjango.backend.base

class AttributesTest(TestCase):
    """Проверка получения соединения для redis"""

    def setUp(self):
        from django.contrib.sites.models import Site
        from redjango.models.fields import Attribute

        self.default_redis = redjango.settings.REDJANGO_DEFAULT_DATABASE
        self.DatabaseWrapper = redjango.backend.base.DatabaseWrapper
        self.a1 = Attribute(name='n',
            indexed=False,
            required=True,
            validator=lambda v: True,
            unique=True,
            default=1)
        self.s = Site()
        self.conn = redjango.connection

    def test_attribute_init(self):
        """Проверяет инициализацию всех параметров"""
        self.assertDictContainsSubset({'name': 'n', 'indexed': False,
                                       'required': True, 'unique': True,
                                       'default': 1}, self.a1.__dict__)
        self.assertTrue(self.a1.validator(None))

    def test_attribute_descriptor_protocol(self):
        """Проверяет работу дескриптора атриботов модели"""
        from redjango.models.fields import Attribute
        from redjango.models import Model

        self.conn.cursor().flushdb()

        class MyModel(Model):
            attr = Attribute()

        mm = MyModel()
        mm.attr = 'value'
        with self.assertRaises(AttributeError) as cm:
            a = MyModel.attr
        the_exception = cm.exception
        self.assertEqual(the_exception.args[0],
            "type object 'MyModel' has no attribute 'attr'")
        self.assertEqual(mm.attr, 'value')

    def test_attribute_default_value_getter(self):
        """Проверяет, что у модели есть значение атрибута по умолчанию"""
        from redjango.models.fields import Attribute
        from redjango.models import Model

        self.conn.cursor().flushdb()

        class MyModel(Model):
            attr = Attribute(default=2)

        mm = MyModel()
        self.assertEqual(mm.attr, 2)
        self.assertEqual(mm.__dict__['_attr'], 2)

    def test_unique_attribute(self):
        from redjango.models.fields import IntegerField
        from redjango.models import Model

        self.conn.cursor().flushdb()

        class MyModel(Model):
            attr = IntegerField(unique=True)

        m1 = MyModel(attr=1)
        m1.save()
        with self.assertRaises(ValidationError) as cm:
            m2 = MyModel(attr=1)
            m2.save()
        the_exception = cm.exception

    def test_getting_value_from_db(self):
        from redjango.models.fields import IntegerField
        from redjango.models import Model

        self.conn.cursor().flushdb()

        class MyModel(Model):
            attr = IntegerField()

        mm = MyModel()
        mm.attr = 1
        mm.save()
        id = mm.id
        del mm
        m2 = MyModel.objects.get(id=id)
        self.assertEqual(m2.attr, 1)

    def test_typecast(self):
        from redjango.models import fields, Model
        import datetime
        class FKModel(Model):
            pass

        class MyModel(Model):
            attr = fields.Attribute()
            int_f = fields.IntegerField()
            bool_f = fields.BooleanField()
            char_f = fields.CharField()
            cnt = fields.Counter()
            date_f = fields.DateField()
            dt_f = fields.DateTimeField()
            float_f = fields.FloatField()
        mm = MyModel(
            attr='attribute',
            int_f=1,
            bool_f=True,
            char_f='char',
            date_f=datetime.date.today(),
            dt_f=datetime.datetime.now().replace(microsecond=125000),
            float_f=3.1415)
        for fn in ('attr', 'int_f', 'bool_f', 'char_f', 'date_f', 'dt_f',
                      'float_f'):
            init_val = getattr(mm, fn)
            # FIXME: аналогичный тест сделать для django model
            field = MyModel._meta.local_fields.get(fn)
            db_val = field.typecast_for_storage(init_val)
            ret_val = field.typecast_for_read(db_val)
            self.assertEqual(init_val, ret_val)
