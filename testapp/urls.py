from django.conf.urls.defaults import patterns, url
from testapp import views
urlpatterns = patterns('',
    url(r'^$', views.HomeView.as_view(),
        name='test'),
)