# Create your views here.
import base64
from io import BytesIO

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from games.models import GameTemplate
from roleplay.models import RolePlayRun, RolePlaySituation
from roleplay.services import RoleAssignmentError, assign_roles_to_run

from .models import GameSession, Participant



@login_required
def create_session(request, game_id):
    game_template = get_object_or_404(
        GameTemplate,
        id=game_id,
        is_active=True,
    )

    # -----------------------------------------------
    # ROLE PLAY
    # Teacher must choose a situation before the
    # GameSession is created.
    # -----------------------------------------------
    if game_template.code == GameTemplate.GameCode.ROLE_PLAY:

        situations = (
            RolePlaySituation.objects
            .filter(is_active=True)
            .prefetch_related("roles")
            .order_by("title")
        )

        if request.method == "POST":
            situation_id = request.POST.get("situation_id")

            situation = get_object_or_404(
                RolePlaySituation,
                id=situation_id,
                is_active=True,
            )

            with transaction.atomic():
                session = GameSession.objects.create(
                    teacher=request.user,
                    game_template=game_template,
                    title=f"{situation.title} - Role Play",
                    current_step="waiting",
                )

                RolePlayRun.objects.create(
                    game_session=session,
                    situation=situation,
                )

            return redirect(
                "sessions:teacher_lobby",
                join_code=session.join_code,
            )

        return render(
            request,
            "roleplay/select_situation.html",
            {
                "game_template": game_template,
                "situations": situations,
            },
        )

    # -----------------------------------------------
    # OTHER GAMES
    # Keep the existing behavior.
    # -----------------------------------------------

    session = GameSession.objects.create(
        teacher=request.user,
        game_template=game_template,
        title=f"{game_template.title} Session",
    )

    return redirect(
        "sessions:teacher_lobby",
        join_code=session.join_code,
    )

@login_required
def session_qr_code(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    join_url = request.build_absolute_uri(
        reverse(
            "sessions:join_session",
            args=[session.join_code],
        )
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(join_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

@login_required
def teacher_lobby(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    # ============================================================
    # Active-game redirects
    # ============================================================

    if (
        session.game_template.code
        == GameTemplate.GameCode.ROLE_PLAY
        and session.status
        == GameSession.Status.ACTIVE
    ):
        return redirect(
            "roleplay:teacher_monitor",
            join_code=session.join_code,
        )

    if (
            session.game_template.code
            == GameTemplate.GameCode.CHOOSE_ADVENTURE
            and session.status
            == GameSession.Status.ACTIVE
        ):
            if session.current_step == "character_selection":
                return redirect(
                    "choose_adventure:teacher_team_setup",
                    join_code=session.join_code,
                )

            if session.current_step == "story_station":
                return redirect(
                    "choose_adventure:teacher_adventure_monitor",
                    join_code=session.join_code,
                )


    # ============================================================
    # Shared join information
    # ============================================================

    join_url = request.build_absolute_uri(
        reverse(
            "sessions:join_session",
            args=[session.join_code],
        )
    )

    qr_image = generate_qr_code(join_url)


    # ============================================================
    # Game-specific lobby data
    # ============================================================

    roleplay_run = None
    adventure_run = None


    # ------------------------------------------------------------
    # Role Play
    # ------------------------------------------------------------

    if (
        session.game_template.code
        == GameTemplate.GameCode.ROLE_PLAY
    ):
        roleplay_run = (
            RolePlayRun.objects
            .select_related("situation")
            .filter(game_session=session)
            .first()
        )


    # ------------------------------------------------------------
    # Choose Your Own Adventure
    # ------------------------------------------------------------

    elif (
        session.game_template.code
        == GameTemplate.GameCode.CHOOSE_ADVENTURE
    ):
        adventure_run = getattr(
            session,
            "adventure_run",
            None,
        )

    # ============================================================
    # Render shared lobby
    # ============================================================

    return render(
        request,
        "sessions/teacher_lobby.html",
        {
            "session": session,
            "join_url": join_url,
            "qr_image": qr_image,

            # Game-specific context
            "roleplay_run": roleplay_run,
            "adventure_run": adventure_run,
        },
    )

@login_required
def start_session(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    if request.method != "POST":
        return redirect(
            "sessions:teacher_lobby",
            join_code=session.join_code,
        )

    # Don't start an already finished session.
    if session.status == GameSession.Status.ENDED:
        messages.error(
            request,
            "This session has already ended.",
        )

        return redirect(
            "sessions:teacher_lobby",
            join_code=session.join_code,
        )

    # ------------------------------------------------
    # FANTASY ROLES
    # ------------------------------------------------

    if session.game_template.code == GameTemplate.GameCode.FANTASY_ROLES:

        session.status = GameSession.Status.ACTIVE
        session.current_step = "character_creation"

        if not session.started_at:
            session.started_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "current_step",
                "started_at",
            ]
        )

    # ------------------------------------------------
    # ROLE PLAY
    # ------------------------------------------------

    elif session.game_template.code == GameTemplate.GameCode.ROLE_PLAY:

        try:
            run = session.roleplay_run

        except RolePlayRun.DoesNotExist:
            messages.error(
                request,
                "This Role Play session does not have a situation assigned.",
            )

            return redirect(
                "sessions:teacher_lobby",
                join_code=session.join_code,
            )

        try:
            with transaction.atomic():

                assign_roles_to_run(run)

                run.status = RolePlayRun.Status.IN_PROGRESS

                if not run.started_at:
                    run.started_at = timezone.now()

                run.save(
                    update_fields=[
                        "status",
                        "started_at",
                    ]
                )

                session.status = GameSession.Status.ACTIVE
                session.current_step = "role_card"

                if not session.started_at:
                    session.started_at = timezone.now()

                session.save(
                    update_fields=[
                        "status",
                        "current_step",
                        "started_at",
                    ]
                )

        except RoleAssignmentError as exc:
            messages.error(
                request,
                str(exc),
            )

            return redirect(
                "sessions:teacher_lobby",
                join_code=session.join_code,
            )

    # ------------------------------------------------
    # CHOOSE YOUR OWN ADVENTURE
    # ------------------------------------------------

    elif (
        session.game_template.code
        == GameTemplate.GameCode.CHOOSE_ADVENTURE
    ):
        # CYOA does not use the generic Start Session flow.
        # Teams must be configured before character selection begins.
        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )


    # ------------------------------------------------
    # OTHER GAMES
    # ------------------------------------------------

    else:

        session.status = GameSession.Status.ACTIVE
        session.current_step = "intro"

        if not session.started_at:
            session.started_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "current_step",
                "started_at",
            ]
        )

    return redirect(
        "sessions:teacher_lobby",
        join_code=session.join_code,
    )

@login_required
def teacher_lobby_participants(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    participants = (
        Participant.objects
        .filter(session=session)
        .order_by("joined_at")
    )

    return render(
        request,
        "sessions/partials/_lobby_participants.html",
        {
            "session": session,
            "participants": participants,
        },
    )

def join_session(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
    )

    join_error = None

    # ============================================================
    # 1. ENDED SESSION
    # ============================================================
    # Once a session has explicitly ended, nobody should be able
    # to join or rejoin it.
    # ============================================================

    if session.status == GameSession.Status.ENDED:
        return render(
            request,
            "sessions/join_session.html",
            {
                "session": session,
                "join_error": "This session has ended.",
                "join_closed": True,
                "rejoin_only": False,
            },
        )

    # ============================================================
    # 2. CHECK BROWSER SESSION
    # ============================================================
    # If this browser already belongs to a participant in this
    # GameSession, send them straight back into the session.
    #
    # This handles the normal case where a student:
    # - closes the tab
    # - closes the browser
    # - loses connection
    # - scans the QR code again
    # ============================================================

    participant_id = request.session.get("participant_id")

    if participant_id:
        existing_browser_participant = (
            Participant.objects
            .filter(
                id=participant_id,
                session=session,
            )
            .first()
        )

        if existing_browser_participant:
            return redirect(
                "sessions:student_waiting_room",
                join_code=session.join_code,
            )

    # ============================================================
    # 3. PROCESS STUDENT ENTRY / RE-ENTRY
    # ============================================================

    if request.method == "POST":

        display_name = request.POST.get(
            "display_name",
            "",
        ).strip()

        student_id = request.POST.get(
            "student_id",
            "",
        ).strip()

        # --------------------------------------------------------
        # Try to recover an existing participant by Student ID.
        # --------------------------------------------------------
        #
        # This is the fallback when the browser no longer has the
        # participant_id cookie/session information.
        # --------------------------------------------------------

        existing_participant = None

        if student_id:
            existing_participant = (
                Participant.objects
                .filter(
                    session=session,
                    student_id=student_id,
                )
                .first()
            )

        if existing_participant:

            request.session["participant_id"] = existing_participant.id
            request.session.modified = True

            return redirect(
                "sessions:student_waiting_room",
                join_code=session.join_code,
            )

        # ========================================================
        # ACTIVE SESSION
        # ========================================================
        # The roster is locked after Start.
        #
        # Existing students may rejoin.
        # Brand-new participants may NOT be created.
        # ========================================================

        if session.status == GameSession.Status.ACTIVE:

            if not student_id:
                join_error = (
                    "This activity has already started. "
                    "Enter the same Student ID you used when you joined "
                    "to return to your activity."
                )
            else:
                join_error = (
                    "We could not find a participant with that Student ID "
                    "in this session. Check the ID and try again."
                )

        # ========================================================
        # LOBBY SESSION
        # ========================================================

        elif session.status == GameSession.Status.LOBBY:

            if not display_name:
                join_error = "Please enter your name."

            # ----------------------------------------------------
            # ROLE PLAY CAPACITY
            # ----------------------------------------------------

            elif (
                session.game_template.code
                == GameTemplate.GameCode.ROLE_PLAY
            ):

                try:
                    run = session.roleplay_run

                    role_capacity = run.situation.total_role_slots
                    participant_count = session.participants.count()

                    if participant_count >= role_capacity:
                        join_error = (
                            "All available roles for this situation "
                            "have already been claimed."
                        )

                except RolePlayRun.DoesNotExist:
                    join_error = (
                        "This Role Play session is not configured correctly."
                    )

            # ----------------------------------------------------
            # CREATE NEW PARTICIPANT
            # ----------------------------------------------------

            if not join_error:

                participant = Participant.objects.create(
                    session=session,
                    display_name=display_name,
                    student_id=student_id,
                )

                request.session["participant_id"] = participant.id
                request.session.modified = True

                return redirect(
                    "sessions:student_waiting_room",
                    join_code=session.join_code,
                )

    # ============================================================
    # 4. DISPLAY JOIN / REJOIN SCREEN
    # ============================================================

    rejoin_only = (
        session.status == GameSession.Status.ACTIVE
    )

    return render(
        request,
        "sessions/join_session.html",
        {
            "session": session,
            "join_error": join_error,
            "join_closed": False,
            "rejoin_only": rejoin_only,
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
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
    )

    redirect_url = None

    if session.status == GameSession.Status.ACTIVE:
        redirect_url = get_game_step_url(session)

    return JsonResponse(
        {
            "status": session.status,
            "current_step": session.current_step,
            "redirect_url": redirect_url,
        }
    )


def redirect_to_game_step(session):
    return redirect(get_game_step_url(session))


def get_game_step_url(session):

    # -----------------------------------------------
    # FANTASY ROLES
    # -----------------------------------------------

    if session.game_template.code == GameTemplate.GameCode.FANTASY_ROLES:

        if session.current_step == "character_creation":
            return reverse(
                "fantasy_roles:character_create",
                args=[session.join_code],
            )

    # -----------------------------------------------
    # ROLE PLAY
    # -----------------------------------------------

    if session.game_template.code == GameTemplate.GameCode.ROLE_PLAY:

        if session.current_step == "role_card":
            return reverse(
                "roleplay:student_role",
                args=[session.join_code],
            )
    # -----------------------------------------------
    # CYOA
    # -----------------------------------------------

    if (
        session.game_template.code
        == GameTemplate.GameCode.CHOOSE_ADVENTURE
    ):
        if session.current_step == "character_selection":
            return reverse(
                "choose_adventure:student_character_selection",
                args=[session.join_code],
            )

        if session.current_step == "story_station":
            return reverse(
                "choose_adventure:student_story_station",
                args=[session.join_code],
            )

    # -----------------------------------------------
    # FALLBACK
    # -----------------------------------------------

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


