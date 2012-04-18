import os
import sys

from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'redis-cli'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        args = [self.executable_name]
        db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
        passwd = settings_dict['OPTIONS'].get('passwd', settings_dict['PASSWORD'])
        host = settings_dict['OPTIONS'].get('host', settings_dict['HOST'])
        port = settings_dict['OPTIONS'].get('port', settings_dict['PORT'])
        if passwd:
            args += ["-a", passwd]
        if host:
            if '/' in host:
                args += ["-s", host]
            else:
                args += ["-h", host]
        if port:
            args += ["-p", port]
        if db:
            args += ["-n", db]

        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)

