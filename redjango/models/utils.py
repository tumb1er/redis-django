import base64

def _encode_key(s):
    try:
        return base64.b64encode(str(s)).replace("\n", "")
    except UnicodeError, e:
        return base64.b64encode(s.encode('utf-8')).replace("\n", "")


class classproperty(object):
    """this is a simple property-like class but for class attributes.
    """
    def __init__(self, get):
        self.get = get
    def __get__(self, inst, cls):
        if hasattr(self.get, '__func__'):
            return self.get.__func__(cls)
        return self.get(cls)