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
    path(
    "<str:join_code>/teacher/parties/",
    views.teacher_party_setup,
    name="teacher_party_setup",
    ),
    path(
    "<str:join_code>/party/",
    views.student_party_detail,
    name="student_party_detail",
    ),

    path(
    "<str:join_code>/teacher/dungeons/",
    views.teacher_dungeon_setup,
    name="teacher_dungeon_setup",
    ),

    path(
        "<str:join_code>/dungeon/",
        views.student_dungeon_detail,
        name="student_dungeon_detail",
    ),
    
    path(
    "<str:join_code>/dungeon/select/",
    views.student_dungeon_select,
    name="student_dungeon_select",
    ),
]