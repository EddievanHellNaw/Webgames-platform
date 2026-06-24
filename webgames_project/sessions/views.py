# Create your views here.
import base64
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse

from games.models import GameTemplate
from .models import GameSession, Participant


@login_required
def create_session(request, game_id):
    game_template = get_object_or_404(GameTemplate, id=game_id, is_active=True)

    session = GameSession.objects.create(
        teacher=request.user,
        game_template=game_template,
        title=f"{game_template.title} Session",
    )

    return redirect("sessions:teacher_lobby", join_code=session.join_code)


@login_required
def teacher_lobby(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    join_url = request.build_absolute_uri(
        reverse("sessions:join_session", args=[session.join_code])
    )

    qr_image = generate_qr_code(join_url)

    return render(
        request,
        "sessions/teacher_lobby.html",
        {
            "session": session,
            "join_url": join_url,
            "qr_image": qr_image,
        },
    )


@login_required
def start_session(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    if request.method == "POST":
        session.status = GameSession.Status.ACTIVE

        if session.game_template.code == GameTemplate.GameCode.FANTASY_ROLES:
            session.current_step = "character_creation"
        else:
            session.current_step = "intro"

        session.started_at = timezone.now()
        session.save()

    return redirect("sessions:teacher_lobby", join_code=session.join_code)


def join_session(request, join_code):
    session = get_object_or_404(GameSession, join_code=join_code)

    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()
        student_id = request.POST.get("student_id", "").strip()

        if display_name:
            participant = Participant.objects.create(
                session=session,
                display_name=display_name,
                student_id=student_id,
            )

            request.session["participant_id"] = participant.id

            return redirect("sessions:student_waiting_room", join_code=session.join_code)

    return render(
        request,
        "sessions/join_session.html",
        {
            "session": session,
        },
    )


def student_waiting_room(request, join_code):
    session = get_object_or_404(GameSession, join_code=join_code)
    participant_id = request.session.get("participant_id")

    if not participant_id:
        return redirect("sessions:join_session", join_code=session.join_code)

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    if session.status == GameSession.Status.ACTIVE:
        return redirect_to_game_step(session)

    return render(
        request,
        "sessions/student_waiting_room.html",
        {
            "session": session,
            "participant": participant,
        },
    )


def session_status(request, join_code):
    session = get_object_or_404(GameSession, join_code=join_code)

    return JsonResponse(
        {
            "status": session.status,
            "current_step": session.current_step,
            "redirect_url": get_game_step_url(session),
        }
    )


def redirect_to_game_step(session):
    return redirect(get_game_step_url(session))


def get_game_step_url(session):
    if session.game_template.code == GameTemplate.GameCode.FANTASY_ROLES:
        if session.current_step == "character_creation":
            return reverse(
                "sessions:placeholder_game_started",
                args=[session.join_code],
            )

    return reverse(
        "sessions:placeholder_game_started",
        args=[session.join_code],
    )


def placeholder_game_started(request, join_code):
    session = get_object_or_404(GameSession, join_code=join_code)

    return render(
        request,
        "sessions/game_started_placeholder.html",
        {
            "session": session,
        },
    )


def generate_qr_code(data):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    image_png = buffer.getvalue()
    encoded = base64.b64encode(image_png).decode("utf-8")
    return f"data:image/png;base64,{encoded}"