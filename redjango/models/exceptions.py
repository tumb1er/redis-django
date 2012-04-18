##########
# ERRORS #
##########

class ValidationError(Exception):
    pass

class MissingID(Exception):
    pass

class AttributeNotIndexed(Exception):
    pass

class FieldValidationError(Exception):

    def __init__(self, errors, *args, **kwargs):
        super(FieldValidationError, self).__init__(*args, **kwargs)
        self._errors = errors

    @property
    def errors(self):
        return self._errors

class BadKeyError(Exception):
    pass
