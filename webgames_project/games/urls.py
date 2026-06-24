from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    path("dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
]