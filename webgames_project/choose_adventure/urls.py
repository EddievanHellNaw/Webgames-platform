from django.urls import path

from . import views


app_name = "choose_adventure"


urlpatterns = [
    path(
        "setup/",
        views.story_setup,
        name="story_setup",
    ),

    path(
        "session/<str:join_code>/teams/",
        views.teacher_team_setup,
        name="teacher_team_setup",
    ),

    path(
        "session/<str:join_code>/begin-character-selection/",
        views.teacher_begin_character_selection,
        name="teacher_begin_character_selection",
    ),

    path(
        "session/<str:join_code>/team/<int:team_id>/reset-character/",
        views.teacher_reset_character,
        name="teacher_reset_character",
    ),

    path(
        "session/<str:join_code>/characters/",
        views.student_character_selection,
        name="student_character_selection",
    ),

    path(
        "session/<str:join_code>/characters/panel/",
        views.student_character_selection_panel,
        name="student_character_selection_panel",
    ),

    path(
        "session/<str:join_code>/begin-adventure/",
        views.teacher_begin_adventure,
        name="teacher_begin_adventure",
    ),

    path(
        "session/<str:join_code>/story/",
        views.student_story_station,
        name="student_story_station",
    ),

    path(
        "session/<str:join_code>/story/panel/",
        views.student_story_station_panel,
        name="student_story_station_panel",
    ),

    path(
        "session/<str:join_code>/story/choose/",
        views.student_submit_choice,
        name="student_submit_choice",
    ),

    path(
        "session/<str:join_code>/monitor/",
        views.teacher_adventure_monitor,
        name="teacher_adventure_monitor",
    ),

    path(
        "session/<str:join_code>/monitor/panel/",
        views.teacher_adventure_monitor_panel,
        name="teacher_adventure_monitor_panel",
    ),
    path(
        "session/<str:join_code>/monitor/team/<int:team_id>/",
        views.teacher_team_detail,
        name="teacher_team_detail",
    ),

    path(
        "session/<str:join_code>/monitor/team/<int:team_id>/undo/",
        views.teacher_undo_team_decision,
        name="teacher_undo_team_decision",
    ),

    path(
        "session/<str:join_code>/monitor/team/<int:team_id>/rewind/",
        views.teacher_rewind_team,
        name="teacher_rewind_team",
    ),

    path(
        "session/<str:join_code>/monitor/team/<int:team_id>/restart/",
        views.teacher_restart_team,
        name="teacher_restart_team",
    ),
    path(
        "session/<str:join_code>/response/<int:station_id>/",
        views.student_save_written_response,
        name="student_save_written_response",
    ),
]