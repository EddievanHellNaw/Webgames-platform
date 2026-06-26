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
    "<str:join_code>/dungeon/select/",
    views.student_dungeon_select,
    name="student_dungeon_select",
    ),
    path(
        "<str:join_code>/dungeon/live/",
        views.student_dungeon_live_panel,
        name="student_dungeon_live_panel",
    ),
    path(
        "<str:join_code>/dungeon/",
        views.student_dungeon_detail,
        name="student_dungeon_detail",
    ),

    path(
    "<str:join_code>/room/action/",
    views.submit_room_action,
    name="submit_room_action",
    ),
    path(
        "<str:join_code>/room/move/<int:room_id>/",
        views.move_to_room,
        name="move_to_room",
    ),

    path(
    "<str:join_code>/dungeon/inventory/",
    views.student_inventory_panel,
    name="student_inventory_panel",
    ),

    path(
    "<str:join_code>/teacher/dungeons/live/",
    views.teacher_dungeon_monitor_panel,
    name="teacher_dungeon_monitor_panel",
    ),

    path(
    "<str:join_code>/room/pass/",
    views.pass_room_turn,
    name="pass_room_turn",
    ),

    path(
    "<str:join_code>/teacher/dungeons/<int:run_id>/retry/",
    views.retry_dungeon_run,
    name="retry_dungeon_run",
    ),

    path(
    "<str:join_code>/boss/start/",
    views.start_boss_fight,
    name="start_boss_fight",
    ),

    path(
    "<str:join_code>/teacher/dungeons/<int:run_id>/boss/start/",
    views.teacher_start_boss_fight,
    name="teacher_start_boss_fight",
    ),

    path(
        "<str:join_code>/boss/activate/",
        views.activate_boss_ability,
        name="activate_boss_ability",
    ),
    path(
        "<str:join_code>/boss/basic-attack/",
        views.boss_basic_attack,
        name="boss_basic_attack",
    ),
    path(
        "<str:join_code>/boss/pass/",
        views.boss_pass_turn,
        name="boss_pass_turn",
    ),

    path(
    "<str:join_code>/boss/use-skill/",
    views.boss_use_skill,
    name="boss_use_skill",
    ),
]