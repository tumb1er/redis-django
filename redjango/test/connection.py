# coding: utf-8


from django.test import TestCase
import django.db

import redjango
import redjango.backend.base
import redjango.containers


#noinspection PyUnresolvedReferences
class ConnectionTest(TestCase):
    """Проверка получения соединения для redis"""

    def setUp(self):
        from django.contrib.sites.models import Site
        from redjango.models import Model
        self.default_redis = redjango.settings.REDJANGO_DEFAULT_DATABASE
        self.DatabaseWrapper = redjango.backend.base.DatabaseWrapper
        self.m1 = Model()
        self.m2 = Model()
        self.s = Site()
        self.conn = redjango.connection 

    def test_redjango_connection_cursor(self):
        """Проверяет, что connection.cursor() возвращает клиент редиса"""
        c = self.conn.cursor()
        c.execute("GET", "1")
        c.executemany((("SET","1", "2"), ("GET", "1")))
        self.assertIsInstance(c.cursor, redjango.backend.base.CursorWrapper)

    def test_db_failure_recovery(self):
        """Проверяет состояние соединения после обработки DatabaseError"""
        from django.db.utils import DatabaseError
        c = self.conn.cursor()
        with self.assertRaises(DatabaseError) as cm:
            c.execute("GET1")
        with self.assertRaises(DatabaseError) as cm:
            c.executemany((("GET1",), ("GET2",)))
        c.ping()

    def test_ping(self):
        """Проверяет вызов метода ping редиса"""
        self.assertTrue(self.conn.cursor().ping())
        
    def test_info(self):
        """Проверяет вызов info"""
        info = self.conn.cursor().info()
        self.assertIsInstance(info, dict)
        self.assertIn('connected_clients', info)
        self.assertEqual(info['connected_clients'], 1)
        c2 = self.conn.cursor()
        self.assertEqual(info['connected_clients'], 1)
        
    def test_reconnect(self):
        """Проверяем автореконнект клиента"""
        self.conn.close()
        self.assertTrue(self.conn.cursor().ping())

    def test_redjango_default_database(self):
        """Проверяет, как возвращается соединение с редисом по умолчанию"""
        self.assertIsInstance(redjango.connection,
            self.DatabaseWrapper)

    def test_django_connection_by_name(self):
        """Проверяет, как возвращается connection средствами django"""
        self.assertIsInstance(django.db.connections[self.default_redis],
            self.DatabaseWrapper)

    #noinspection PyUnresolvedReferences
    def test_redjango_container_db_property(self):
        """Проверяет, как работает свойство db у класса Container"""
        #noinspection PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
        c = redjango.containers.Container('key')
        self.assertIsInstance(c.db, self.DatabaseWrapper)

    def test_redjango_router_db_for_read(self):
        """Проверяет роутер на работу с моделями redjango и django"""
        from django.contrib.sites.models import Site
        from redjango.models import Model

        db = django.db.router.db_for_read(Model)
        self.assertEqual(db, self.default_redis)

        db = django.db.router.db_for_read(Site)
        self.assertNotEqual(db, self.default_redis)

    def test_redjango_router_db_for_write(self):
        """Проверяет роутер на работу с моделями redjango и django"""
        from django.contrib.sites.models import Site
        from redjango.models import Model

        db = django.db.router.db_for_write(Model)
        self.assertEqual(db, self.default_redis)

        db = django.db.router.db_for_write(Site)
        self.assertNotEqual(db, self.default_redis)

    def test_redjango_router_allow_relation(self):
        """Проверяет роутер на работу с моделями redjango и django"""

        res = django.db.router.allow_relation(self.s, self.m1)
        self.assertFalse(res)

        res = django.db.router.allow_relation(self.m2, self.m1)
        self.assertTrue(res)



