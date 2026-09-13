from django.urls import path

from . import views


app_name = "roleplay"


urlpatterns = [

    # ========================================================
    # Student
    # ========================================================

    path(
        "play/<str:join_code>/",
        views.student_role,
        name="student_role",
    ),

    path(
        "play/<str:join_code>/status/",
        views.student_role_status,
        name="student_role_status",
    ),


    # ========================================================
    # Teacher monitor
    # ========================================================

    path(
        "monitor/<str:join_code>/",
        views.teacher_monitor,
        name="teacher_monitor",
    ),

    path(
        "monitor/<str:join_code>/status/",
        views.teacher_monitor_status,
        name="teacher_monitor_status",
    ),


    # ========================================================
    # Rounds
    # ========================================================

    path(
        "monitor/<str:join_code>/new-round/",
        views.reassign_roles,
        name="reassign_roles",
    ),


    # ========================================================
    # Reports
    # ========================================================

    path(
        "monitor/<str:join_code>/student/<int:participant_id>/",
        views.teacher_student_reports,
        name="teacher_student_reports",
    ),

]