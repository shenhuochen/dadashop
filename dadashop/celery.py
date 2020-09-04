from celery import Celery
import os

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE','dadashop.settings')
app =Celery('dadashop')
app.conf.update(
    BROKEN_URL="redis://:@127.0.0.1:6379/4"
)
app.autodiscover_tasks(settings.INSTALLED_APPS)