from django.urls import path

from . import views


app_name = "treasure_hunt"


urlpatterns = [
    path(
        "<str:join_code>/",
        views.student_hunt,
        name="student_hunt",
    ),

    path(
        "<str:join_code>/teacher/",
        views.teacher_hunt,
        name="teacher_hunt",
    ),
]