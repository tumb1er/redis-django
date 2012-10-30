__author__ = 'tumbler'


def bind_method(bound_method):
    def inner(*args, **kwargs):
        return bound_method.im_func(*args, **kwargs)
    return inner

def patch():
    """
    Monkeypatches the django.contrib.auth.models module and the admin
    autodiscover function
    """
    import auth
    import admin
    import sessions
    import sites
    auth.patch()
    admin.patch()
    sessions.patch()
    sites.patch()
    print 'patched!'
    # sys.modules['django.contrib.auth'].models = redjango.compat.auth.models