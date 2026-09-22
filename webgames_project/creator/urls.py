from django.urls import path

from . import views


app_name = "creator"


urlpatterns = [
    path("", views.creator_dashboard, name="dashboard"),
]