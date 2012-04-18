# coding: utf-8
from django.db.backends.dummy.base import *
from django.db.backends.signals import connection_created
from redis.exceptions import *
import sys
from django.db import utils
from redis.client import list_or_args

try:
    from redis import Redis
except ImportError, e:
    Redis = None
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading redis module: %s" % e)

def complain(*args, **kwargs):
    import traceback
    traceback.print_stack()
    raise ImproperlyConfigured("You haven't set the database ENGINE setting yet.")

class CursorWrapper(object):
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, command, params=()):
        try:
            args = list_or_args(command, params)
            return self.cursor.execute_command(*args)
        except RedisError as e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def executemany(self, commands):
        pipeline = None
        try:
            pipeline = self.cursor.pipeline()
            for c in commands:
                pipeline.execute_command(*c)
            return pipeline.execute()
        except RedisError as e:
            # pipeline похоже оставляет непрочитанные ответы от сервера,
            # которые мы сейчас и распарсим
            pool = self.cursor.connection_pool
            connection = pool.get_connection('PING')
            ret = True
            while ret:
                try:
                    ret = self.parse_response(connection, 'PING')
                except RedisError as re:
                    pass
            pool.release(connection)
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]
        finally:
            if pipeline:
                pipeline.reset()


    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

class RedisDatabaseCreation(BaseDatabaseCreation):
    def create_test_db(self, verbosity=1, autoclobber=False):
        pass
    
    def destroy_test_db(self, old_database_name, verbosity=1):
        self.connection.flushdb()



class DatabaseWrapper(BaseDatabaseWrapper):
    operators = {}
    # Override the base class implementations with null
    # implementations. Anything that tries to actually
    # do something raises complain; anything that tries
    # to rollback or undo something raises ignore.
    _commit = complain
    _rollback = ignore
    enter_transaction_management = complain
    leave_transaction_management = ignore
    set_dirty = complain
    set_clean = complain
    commit_unless_managed = complain
    rollback_unless_managed = ignore
    savepoint = ignore
    savepoint_commit = complain
    savepoint_rollback = ignore
    close = ignore

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = BaseDatabaseFeatures(self)
        self.ops = DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = RedisDatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)


    def _valid_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping()
                return True
            except DatabaseError:
                self.connection.close()
                self.connection = None
        return False

    def _cursor(self):
        if not self._valid_connection():
            kwargs = {}
            settings_dict = self.settings_dict
            if settings_dict['NAME']:
                kwargs['db'] = settings_dict['NAME']
            if settings_dict['PASSWORD']:
                kwargs['password'] = settings_dict['PASSWORD']
            if settings_dict['HOST']:
                kwargs['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                kwargs['port'] = int(settings_dict['PORT'])
            # We need the number of potentially affected rows after an
            # "UPDATE", not the number of changed rows.
            kwargs.update(settings_dict['OPTIONS'])
            self.connection = Redis(**kwargs)
            connection_created.send(sender=self.__class__, connection=self)
        cursor = CursorWrapper(self.connection)
        return cursor

    def __getattribute__(self, item):
        try:
            return super(DatabaseWrapper, self).__getattribute__(item)
        except AttributeError:
            return getattr(self.cursor(), item)

    def __delitem__(self, key):
        self.cursor().execute_command('DEL', key)
