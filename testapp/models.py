__author__ = 'tumbler'

from redjango import models

class TestModel(models.Model):
    num = models.IntegerField()