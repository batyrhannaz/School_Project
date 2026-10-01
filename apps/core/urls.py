from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("lang/", views.set_lang, name="set_lang"),
]
