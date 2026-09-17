import math
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from games.models import GameTemplate
from sessions.models import GameSession, Participant

from .models import (
    AdventureCharacter,
    AdventureRun,
    AdventureStory,
    AdventureTeam,
    AdventureTeamMembership,
    StoryStation,
    TeamDecision,
    AdventureWrittenResponse
)

from .services import (
    AdventureDecisionError,
    get_available_choices,
    get_dominant_genre,
    resolve_automatic_stations,
    restart_team_adventure,
    rewind_team_to_station,
    submit_team_decision,
    undo_last_team_decision,
)

@login_required
def story_setup(request):
    game_template = get_object_or_404(
        GameTemplate,
        code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
        is_active=True,
    )

    stories = (
        AdventureStory.objects
        .filter(is_active=True)
        .prefetch_related(
            "characters",
            "stations",
        )
        .order_by(
            "english_level",
            "title",
        )
    )

    if request.method == "POST":
        story_id = request.POST.get("story_id")

        story = get_object_or_404(
            AdventureStory,
            id=story_id,
            is_active=True,
        )

        with transaction.atomic():
            session = GameSession.objects.create(
                teacher=request.user,
                game_template=game_template,
                title=f"{story.title} Session",
            )

            AdventureRun.objects.create(
                session=session,
                story=story,
            )

        return redirect(
            "sessions:teacher_lobby",
            join_code=session.join_code,
        )

    return render(
        request,
        "choose_adventure/story_setup.html",
        {
            "stories": stories,
        },
    )
@login_required
def teacher_team_setup(request, join_code):
    session = get_object_or_404(
        GameSession.objects.select_related("game_template"),
        join_code=join_code,
        teacher=request.user,
    )

    if session.game_template.code != GameTemplate.GameCode.CHOOSE_ADVENTURE:
        return redirect(
            "sessions:teacher_lobby",
            join_code=session.join_code,
        )

    adventure_run = get_object_or_404(
        AdventureRun.objects.select_related("story"),
        session=session,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "auto_generate":
            try:
                team_size = int(request.POST.get("team_size", 4))
            except (TypeError, ValueError):
                team_size = 4

            team_size = max(2, min(team_size, 8))

            participants = list(
                session.participants.order_by("joined_at", "id")
            )

            if participants:
                random.shuffle(participants)

                with transaction.atomic():
                    AdventureTeamMembership.objects.filter(
                        team__adventure_run=adventure_run
                    ).delete()

                    AdventureTeam.objects.filter(
                        adventure_run=adventure_run
                    ).delete()

                    team_count = math.ceil(
                        len(participants) / team_size
                    )

                    teams = []

                    for index in range(team_count):
                        team = AdventureTeam.objects.create(
                            adventure_run=adventure_run,
                            name=f"Team {index + 1}",
                            sort_order=index + 1,
                        )
                        teams.append(team)

                    for index, participant in enumerate(participants):
                        AdventureTeamMembership.objects.create(
                            team=teams[index % team_count],
                            participant=participant,
                        )

            return redirect(
                "choose_adventure:teacher_team_setup",
                join_code=session.join_code,
            )

        if action == "clear_teams":
            with transaction.atomic():
                AdventureTeamMembership.objects.filter(
                    team__adventure_run=adventure_run
                ).delete()

                AdventureTeam.objects.filter(
                    adventure_run=adventure_run
                ).delete()

            return redirect(
                "choose_adventure:teacher_team_setup",
                join_code=session.join_code,
            )

    teams = (
            AdventureTeam.objects
            .filter(
                adventure_run=adventure_run,
            )
            .select_related(
                "selected_character",
                "character_selected_by",
                "current_station",
            )
            .prefetch_related(
                "memberships__participant",
            )
            .order_by(
                "sort_order",
                "id",
            )
        )
    participant_count = session.participants.count()

    assigned_count = (
        AdventureTeamMembership.objects
        .filter(
            team__adventure_run=adventure_run,
        )
        .count()
    )

    team_count = teams.count()

    selected_character_count = (
        AdventureTeam.objects
        .filter(
            adventure_run=adventure_run,
            selected_character__isnull=False,
        )
        .count()
    )

    can_begin_character_selection = (
        participant_count > 0
        and team_count > 0
        and assigned_count == participant_count
    )

    can_start_adventure=(
        team_count > 0
        and selected_character_count == team_count
    )

    assigned_participant_ids = AdventureTeamMembership.objects.filter(
        team__adventure_run=adventure_run
    ).values_list("participant_id", flat=True)

    unassigned_participants = (
        session.participants
        .exclude(id__in=assigned_participant_ids)
        .order_by("joined_at", "id")
    )

    return render(
        request,
        "choose_adventure/teacher_team_setup.html",
        {
            "session": session,
            "adventure_run": adventure_run,
            "teams": teams,
            "unassigned_participants": unassigned_participants,
            "participant_count": session.participants.count(),
            "assigned_count": assigned_count,
            "team_count": team_count,
            "selected_character_count": selected_character_count,
            "can_begin_character_selection": can_begin_character_selection,
            "assigned_count": assigned_count,
            "team_count": team_count,
            "selected_character_count": selected_character_count,
            "can_begin_character_selection": can_begin_character_selection,
            "can_start_adventure": can_start_adventure,
        },
    )

@login_required
@require_POST
def teacher_begin_character_selection(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    adventure_run = get_object_or_404(
        AdventureRun,
        session=session,
    )

    participant_count = session.participants.count()

    assigned_count = (
        AdventureTeamMembership.objects
        .filter(
            team__adventure_run=adventure_run,
        )
        .count()
    )

    team_count = (
        AdventureTeam.objects
        .filter(
            adventure_run=adventure_run,
        )
        .count()
    )

    if participant_count == 0:
        messages.error(
            request,
            "At least one student must join before character selection begins.",
        )

        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    if team_count == 0:
        messages.error(
            request,
            "Create the teams before beginning character selection.",
        )

        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    if assigned_count != participant_count:
        messages.error(
            request,
            "Every student must be assigned to a team first.",
        )

        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    session.status = GameSession.Status.ACTIVE
    session.current_step = "character_selection"

    if session.started_at is None:
        session.started_at = timezone.now()

    session.save(
        update_fields=[
            "status",
            "current_step",
            "started_at",
        ]
    )

    return redirect(
        "choose_adventure:teacher_team_setup",
        join_code=session.join_code,
    )

def student_character_selection(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    # ============================================================
    # Phase routing
    # ============================================================

    # The teacher has already started the adventure.
    if session.current_step == "story_station":
        return redirect(
            "choose_adventure:student_story_station",
            join_code=session.join_code,
        )

    # Character selection has not started yet.
    if session.current_step != "character_selection":
        return redirect(
            "sessions:student_waiting_room",
            join_code=session.join_code,
        )

    # ============================================================
    # Student identity
    # ============================================================

    participant_id = request.session.get("participant_id")

    if not participant_id:
        return redirect(
            "sessions:join_session",
            join_code=session.join_code,
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    # ============================================================
    # Team
    # ============================================================

    membership = get_object_or_404(
        AdventureTeamMembership.objects.select_related(
            "team",
            "team__adventure_run",
            "team__adventure_run__story",
            "team__selected_character",
            "team__character_selected_by",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    team = membership.team
    story = team.adventure_run.story

    # ============================================================
    # Available characters
    # ============================================================

    characters = (
        AdventureCharacter.objects
        .filter(
            story=story,
            is_active=True,
        )
        .order_by(
            "sort_order",
            "name",
        )
    )

    # ============================================================
    # Character choice
    # ============================================================

    if request.method == "POST":
        character_id = request.POST.get("character_id")

        character = get_object_or_404(
            AdventureCharacter,
            id=character_id,
            story=story,
            is_active=True,
        )

        with transaction.atomic():
            locked_team = (
                AdventureTeam.objects
                .select_for_update()
                .get(id=team.id)
            )

            # First confirmed choice wins.
            if locked_team.selected_character_id is None:
                locked_team.selected_character = character
                locked_team.character_selected_by = participant
                locked_team.character_selected_at = timezone.now()

                locked_team.save(
                    update_fields=[
                        "selected_character",
                        "character_selected_by",
                        "character_selected_at",
                    ]
                )

        return redirect(
            "choose_adventure:student_character_selection",
            join_code=session.join_code,
        )

    # ============================================================
    # Team members
    # ============================================================

    team_members = (
        AdventureTeamMembership.objects
        .filter(team=team)
        .select_related("participant")
        .order_by("participant__joined_at")
    )

    # ============================================================
    # GET response
    # ============================================================

    return render(
        request,
        "choose_adventure/student_character_selection.html",
        {
            "session": session,
            "participant": participant,
            "team": team,
            "story": story,
            "characters": characters,
            "team_members": team_members,
        },
    )

def student_character_selection_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    # ============================================================
    # Teacher has started the adventure
    # ============================================================

    if session.current_step == "story_station":
        response = HttpResponse(status=204)

        response["HX-Redirect"] = reverse(
            "choose_adventure:student_story_station",
            args=[session.join_code],
        )

        return response

    # ============================================================
    # Student identity
    # ============================================================

    participant_id = request.session.get("participant_id")

    if not participant_id:
        return redirect(
            "sessions:join_session",
            join_code=session.join_code,
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    # ============================================================
    # Team
    # ============================================================

    membership = get_object_or_404(
        AdventureTeamMembership.objects.select_related(
            "team",
            "team__selected_character",
            "team__character_selected_by",
            "team__adventure_run__story",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    team = membership.team
    story = team.adventure_run.story

    characters = (
        AdventureCharacter.objects
        .filter(
            story=story,
            is_active=True,
        )
        .order_by(
            "sort_order",
            "name",
        )
    )

    return render(
        request,
        "choose_adventure/partials/_character_selection_panel.html",
        {
            "session": session,
            "participant": participant,
            "team": team,
            "story": story,
            "characters": characters,
        },
    )

@login_required
@require_POST
def teacher_reset_character(request, join_code, team_id):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    team = get_object_or_404(
        AdventureTeam,
        id=team_id,
        adventure_run__session=session,
    )

    team.selected_character = None
    team.character_selected_by = None
    team.character_selected_at = None

    team.save(
        update_fields=[
            "selected_character",
            "character_selected_by",
            "character_selected_at",
        ]
    )

    return redirect(
        "choose_adventure:teacher_team_setup",
        join_code=session.join_code,
    )

@login_required
@require_POST
def teacher_begin_adventure(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    adventure_run = get_object_or_404(
        AdventureRun.objects.select_related("story"),
        session=session,
    )

    teams = list(
        AdventureTeam.objects
        .filter(adventure_run=adventure_run)
        .select_related("selected_character")
        .order_by("sort_order", "id")
    )

    if not teams:
        messages.error(
            request,
            "Create the teams before starting the adventure.",
        )
        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    if any(team.selected_character is None for team in teams):
        messages.error(
            request,
            "Every team must choose a character before the adventure can begin.",
        )
        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    start_station = (
        StoryStation.objects
        .filter(
            story=adventure_run.story,
            is_start=True,
        )
        .order_by("sort_order", "id")
        .first()
    )

    if not start_station:
        messages.error(
            request,
            "This story does not have a valid start station.",
        )
        return redirect(
            "choose_adventure:teacher_team_setup",
            join_code=session.join_code,
        )

    with transaction.atomic():
        TeamDecision.objects.filter(
            team__adventure_run=adventure_run
        ).delete()

        for team in teams:
            team.current_station = start_station
            team.containment_score = 0
            team.humanity_score = 0
            team.knowledge_score = 0
            team.sci_fi_score = 0
            team.cyberpunk_score = 0
            team.bio_horror_score = 0
            team.story_flags = []
            team.is_finished = False
            team.ending_station = None

            team.save(
                update_fields=[
                    "current_station",
                    "containment_score",
                    "humanity_score",
                    "knowledge_score",
                    "sci_fi_score",
                    "cyberpunk_score",
                    "bio_horror_score",
                    "story_flags",
                    "is_finished",
                    "ending_station",
                ]
            )

        session.status = GameSession.Status.ACTIVE
        session.current_step = "story_station"

        if session.started_at is None:
            session.started_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "current_step",
                "started_at",
            ]
        )

    messages.success(
        request,
        "Adventure started successfully.",
    )

    return redirect(
        "choose_adventure:teacher_adventure_monitor",
        join_code=session.join_code,
    )

def student_story_station(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    participant_id = request.session.get(
        "participant_id"
    )

    if not participant_id:
        return redirect(
            "sessions:join_session",
            join_code=session.join_code,
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    membership = get_object_or_404(
        AdventureTeamMembership.objects
        .select_related(
            "team",
            "team__selected_character",
            "team__current_station",
            "team__ending_station",
            "team__adventure_run",
            "team__adventure_run__story",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    team = membership.team

    if team.selected_character is None:
        return redirect(
            "choose_adventure:student_character_selection",
            join_code=session.join_code,
        )

    return render(
        request,
        "choose_adventure/student_story_station.html",
        {
            "session": session,
            "participant": participant,
            "team": team,
            "story": team.adventure_run.story,
        },
    )
def student_story_station_panel(
    request,
    join_code,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    participant_id = request.session.get(
        "participant_id"
    )

    if not participant_id:
        return redirect(
            "sessions:join_session",
            join_code=session.join_code,
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    membership = get_object_or_404(
        AdventureTeamMembership.objects
        .select_related(
            "team",
            "team__selected_character",
            "team__current_station",
            "team__ending_station",
            "team__adventure_run",
            "team__adventure_run__story",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    team = membership.team
    story = team.adventure_run.story
    current_station = team.current_station
    response_station = None

    if (
        team.is_finished
        and team.ending_station
    ):
        response_station = (
            team.ending_station
        )

    elif current_station:
        response_station = (
            current_station
        )


    written_response = None

    if response_station:
        written_response = (
            AdventureWrittenResponse.objects
            .filter(
                team=team,
                participant=participant,
                station=response_station,
            )
            .first()
        )

    # ------------------------------------------------------------
    # Resolve deterministic system stations.
    #
    # Normally this happens immediately after a team decision.
    # This also safely advances older test sessions that may
    # already be sitting on an AUTO station.
    # ------------------------------------------------------------

    if (
        current_station
        and not team.is_finished
        and current_station.advance_mode
        == StoryStation.AdvanceMode.AUTO
    ):
        resolve_automatic_stations(team)

        team.refresh_from_db(
            fields=[
                "current_station",
                "is_finished",
                "ending_station",
            ]
        )

        current_station = team.current_station

    choices = []

    if (
        current_station
        and not team.is_finished
        and current_station.advance_mode
        == StoryStation.AdvanceMode.CHOICE
    ):
        choices = get_available_choices(team)

    decision_number = (
        team.decisions.count() + 1
    )

    path_decisions = (
        team.decisions
        .select_related(
            "station",
            "selected_choice",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    return render(
        request,
        "choose_adventure/partials/_story_station_panel.html",
        {
            "session": session,
            "participant": participant,
            "team": team,
            "story": story,
            "current_station": current_station,
            "choices": choices,
            "decision_number": decision_number,
            "path_decisions": path_decisions,
            "written_response": written_response,
        },
    )

@require_POST
def student_submit_choice(
    request,
    join_code,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.CHOOSE_ADVENTURE,
    )

    participant_id = request.session.get(
        "participant_id"
    )

    if not participant_id:
        return redirect(
            "sessions:join_session",
            join_code=session.join_code,
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    membership = get_object_or_404(
        AdventureTeamMembership.objects
        .select_related(
            "team",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    choice_id = request.POST.get(
        "choice_id"
    )

    if not choice_id:
        messages.error(
            request,
            "Choose an option before confirming.",
        )

        return redirect(
            "choose_adventure:student_story_station",
            join_code=session.join_code,
        )

    try:
        submit_team_decision(
            team_id=membership.team_id,
            choice_id=choice_id,
            participant=participant,
        )

    except AdventureDecisionError as exc:
        messages.warning(
            request,
            str(exc),
        )

    return redirect(
        "choose_adventure:student_story_station",
        join_code=session.join_code,
    )

@login_required
def teacher_adventure_monitor(
    request,
    join_code,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    adventure_run = get_object_or_404(
        AdventureRun.objects.select_related(
            "story",
        ),
        session=session,
    )

    return render(
        request,
        "choose_adventure/teacher_adventure_monitor.html",
        {
            "session": session,
            "adventure_run": adventure_run,
        },
    )

@login_required
def teacher_adventure_monitor_panel(
    request,
    join_code,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    adventure_run = get_object_or_404(
        AdventureRun.objects.select_related(
            "story",
        ),
        session=session,
    )

    decision_queryset = (
        TeamDecision.objects
        .select_related(
            "station",
            "selected_choice",
            "selected_by",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    teams = (
        AdventureTeam.objects
        .filter(
            adventure_run=adventure_run,
        )
        .select_related(
            "selected_character",
            "current_station",
            "ending_station",
        )
        .prefetch_related(
            "memberships__participant",
            Prefetch(
                "decisions",
                queryset=decision_queryset,
            ),
        )
        .order_by(
            "sort_order",
            "id",
        )
    )

    team_count = teams.count()

    finished_count = (
        AdventureTeam.objects
        .filter(
            adventure_run=adventure_run,
            is_finished=True,
        )
        .count()
    )

    return render(
        request,
        "choose_adventure/partials/_teacher_adventure_monitor_panel.html",
        {
            "session": session,
            "adventure_run": adventure_run,
            "teams": teams,
            "team_count": team_count,
            "finished_count": finished_count,
        },
    )

@login_required
def teacher_team_detail(
    request,
    join_code,
    team_id,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    team = get_object_or_404(
        AdventureTeam.objects
        .select_related(
            "adventure_run",
            "adventure_run__story",
            "selected_character",
            "current_station",
            "ending_station",
        )
        .prefetch_related(
            "memberships__participant",
        ),
        id=team_id,
        adventure_run__session=session,
    )

    decisions = list(
        TeamDecision.objects
        .filter(team=team)
        .select_related(
            "station",
            "selected_choice",
            "selected_by",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    # Every station where the team actually made
    # a decision is a safe rewind target.
    rewind_stations = [
        decision.station
        for decision in decisions
    ]

    dominant_genre = (
        get_dominant_genre(team)
    )

    dominant_genre_label = {
        "SCI_FI": "Sci-Fi",
        "CYBERPUNK": "Cyberpunk",
        "BIO_HORROR": "Bio-Horror",
    }.get(
        dominant_genre,
        "Tied / Undetermined",
    )

    return render(
        request,
        "choose_adventure/teacher_team_detail.html",
        {
            "session": session,
            "team": team,
            "story": team.adventure_run.story,
            "decisions": decisions,
            "rewind_stations": rewind_stations,
            "dominant_genre_label": (
                dominant_genre_label
            ),
        },
    )

@login_required
@require_POST
def teacher_undo_team_decision(
    request,
    join_code,
    team_id,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    team = get_object_or_404(
        AdventureTeam,
        id=team_id,
        adventure_run__session=session,
    )

    try:
        (
            rebuilt_team,
            undone_station,
            undone_choice,
        ) = undo_last_team_decision(
            team.id
        )

        if undone_choice:
            messages.success(
                request,
                (
                    f"{rebuilt_team.name} was returned "
                    f'to "{undone_station.title}". '
                    f'Undid: "{undone_choice.text}".'
                ),
            )
        else:
            messages.success(
                request,
                (
                    f"{rebuilt_team.name}'s last "
                    "decision was undone."
                ),
            )

    except AdventureDecisionError as exc:
        messages.error(
            request,
            str(exc),
        )

    return redirect(
        "choose_adventure:teacher_team_detail",
        join_code=session.join_code,
        team_id=team.id,
    )

@login_required
@require_POST
def teacher_rewind_team(
    request,
    join_code,
    team_id,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    team = get_object_or_404(
        AdventureTeam,
        id=team_id,
        adventure_run__session=session,
    )

    station_id = request.POST.get(
        "station_id"
    )

    if not station_id:
        messages.error(
            request,
            "Choose a station to rewind to.",
        )

        return redirect(
            "choose_adventure:teacher_team_detail",
            join_code=session.join_code,
            team_id=team.id,
        )

    try:
        rebuilt_team = (
            rewind_team_to_station(
                team_id=team.id,
                station_id=station_id,
            )
        )

        messages.success(
            request,
            (
                f"{rebuilt_team.name} was rewound "
                f'to "{rebuilt_team.current_station.title}".'
            ),
        )

    except AdventureDecisionError as exc:
        messages.error(
            request,
            str(exc),
        )

    return redirect(
        "choose_adventure:teacher_team_detail",
        join_code=session.join_code,
        team_id=team.id,
    )

@login_required
@require_POST
def teacher_restart_team(
    request,
    join_code,
    team_id,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    team = get_object_or_404(
        AdventureTeam,
        id=team_id,
        adventure_run__session=session,
    )

    try:
        rebuilt_team = (
            restart_team_adventure(
                team.id
            )
        )

        messages.success(
            request,
            (
                f"{rebuilt_team.name} has been "
                "restarted from the beginning."
            ),
        )

    except AdventureDecisionError as exc:
        messages.error(
            request,
            str(exc),
        )

    return redirect(
        "choose_adventure:teacher_team_detail",
        join_code=session.join_code,
        team_id=team.id,
    )  

@require_POST
def student_save_written_response(
    request,
    join_code,
    station_id,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    participant_id = request.session.get(
        "participant_id"
    )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    membership = get_object_or_404(
        AdventureTeamMembership.objects
        .select_related(
            "team",
            "team__adventure_run",
            "team__adventure_run__story",
        ),
        participant=participant,
        team__adventure_run__session=session,
    )

    team = membership.team

    station = get_object_or_404(
        StoryStation,
        id=station_id,
        story=team.adventure_run.story,
    )

    # --------------------------------------------------------
    # Accept a response if this is:
    #
    # - the team's current station,
    # - its ending,
    # - or a station the team has already visited.
    #
    # The last case is useful if a teammate confirms the
    # story choice a fraction of a second before this student
    # submits their writing.
    # --------------------------------------------------------

    station_is_valid = (
        team.current_station_id
        == station.id
        or team.ending_station_id
        == station.id
        or TeamDecision.objects.filter(
            team=team,
            station=station,
        ).exists()
    )

    if not station_is_valid:
        return HttpResponse(
            "This station is no longer available.",
            status=403,
        )

    response_text = (
        request.POST.get(
            "response_text",
            "",
        ).strip()
    )

    if not response_text:
        return HttpResponse(
            "Write an answer before saving.",
            status=400,
        )

    AdventureWrittenResponse.objects.update_or_create(
        team=team,
        participant=participant,
        station=station,
        defaults={
            "text": response_text,
        },
    )

    if request.headers.get(
        "HX-Request"
    ) == "true":
        return HttpResponse(
            "Saved ✓"
        )

    return redirect(
        "choose_adventure:student_story_station",
        join_code=session.join_code,
    )

@login_required
def teacher_adventure_monitor_panel(
    request,
    join_code,
):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=(
            GameTemplate.GameCode.CHOOSE_ADVENTURE
        ),
    )

    adventure_run = get_object_or_404(
        AdventureRun.objects.select_related(
            "story"
        ),
        session=session,
    )


    decision_queryset = (
        TeamDecision.objects
        .select_related(
            "station",
            "selected_choice",
            "selected_by",
        )
        .order_by(
            "created_at",
            "id",
        )
    )


    response_queryset = (
        AdventureWrittenResponse.objects
        .select_related(
            "participant",
            "station",
        )
        .order_by(
            "station__sort_order",
            "participant__display_name",
            "updated_at",
        )
    )


    teams = list(
        AdventureTeam.objects
        .filter(
            adventure_run=adventure_run
        )
        .select_related(
            "selected_character",
            "current_station",
            "ending_station",
        )
        .prefetch_related(
            "memberships__participant",

            Prefetch(
                "decisions",
                queryset=decision_queryset,
            ),

            Prefetch(
                "written_responses",
                queryset=response_queryset,
                to_attr="loaded_written_responses",
            ),
        )
        .order_by(
            "sort_order",
            "id",
        )
    )


    # --------------------------------------------------------
    # Separate normal story answers from final answers.
    # --------------------------------------------------------

    for team in teams:

        team.story_written_responses = []
        team.final_written_responses = []

        for response in (
            team.loaded_written_responses
        ):

            if (
                team.ending_station_id
                and response.station_id
                == team.ending_station_id
            ):
                team.final_written_responses.append(
                    response
                )

            else:
                team.story_written_responses.append(
                    response
                )


    team_count = len(teams)

    finished_count = sum(
        1
        for team in teams
        if team.is_finished
    )


    return render(
        request,
        (
            "choose_adventure/partials/"
            "_teacher_adventure_monitor_panel.html"
        ),
        {
            "session": session,
            "adventure_run": adventure_run,
            "teams": teams,
            "team_count": team_count,
            "finished_count": finished_count,
        },
    )