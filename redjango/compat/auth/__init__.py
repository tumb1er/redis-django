def patch():
    import django.contrib.auth.models
    import models
    django.contrib.auth.models.User = models.User
