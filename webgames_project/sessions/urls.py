from django.urls import path
from . import views

app_name = "sessions"

urlpatterns = [
    path("create/<int:game_id>/", views.create_session, name="create_session"),
    path("lobby/<str:join_code>/", views.teacher_lobby, name="teacher_lobby"),
    path("start/<str:join_code>/", views.start_session, name="start_session"),

    path("join/<str:join_code>/", views.join_session, name="join_session"),
    path("wait/<str:join_code>/", views.student_waiting_room, name="student_waiting_room"),
    path("status/<str:join_code>/", views.session_status, name="session_status"),

    path("started/<str:join_code>/", views.placeholder_game_started, name="placeholder_game_started"),
    path(
        "lobby/<str:join_code>/participants/",
        views.teacher_lobby_participants,
        name="teacher_lobby_participants",
    ),
]