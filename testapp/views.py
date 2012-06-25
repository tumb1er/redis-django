__author__ = 'tumbler'

from django.views.generic.list import ListView
from models import TestModel

class HomeView(ListView):
    template_name = 'test.html'

    def get_queryset(self):
        return TestModel.objects.all()