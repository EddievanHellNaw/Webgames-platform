from django.urls import path
from . import views

app_name = "fantasy_roles"

urlpatterns = [
    path(
        "<str:join_code>/character/create/",
        views.character_create,
        name="character_create",
    ),
    path(
        "<str:join_code>/character/",
        views.character_detail,
        name="character_detail",
    ),
    path(
        "<str:join_code>/teacher/characters/",
        views.teacher_character_list,
        name="teacher_character_list",
    ),
]