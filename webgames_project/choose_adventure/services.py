from django.db import transaction

from .models import (
    AdventureGenre,
    AdventureTeam,
    AutomaticRoute,
    StoryChoice,
    StoryStation,
    TeamDecision,
)


# ============================================================
# Exceptions
# ============================================================


class AdventureDecisionError(Exception):
    pass


# ============================================================
# Genre helpers
# ============================================================


def get_dominant_genre(team):
    scores = {
        AdventureGenre.SCI_FI: team.sci_fi_score,
        AdventureGenre.CYBERPUNK: team.cyberpunk_score,
        AdventureGenre.BIO_HORROR: team.bio_horror_score,
    }

    highest_score = max(scores.values())

    winners = [
        genre
        for genre, score in scores.items()
        if score == highest_score
    ]

    if len(winners) == 1:
        return winners[0]

    return ""


# ============================================================
# Choice availability
# ============================================================


def choice_is_available(choice, team):
    flags = set(team.story_flags or [])

    required_flags = set(
        choice.required_flags or []
    )

    forbidden_flags = set(
        choice.forbidden_flags or []
    )

    if not required_flags.issubset(flags):
        return False

    if forbidden_flags.intersection(flags):
        return False

    if (
        choice.min_containment is not None
        and team.containment_score
        < choice.min_containment
    ):
        return False

    if (
        choice.min_humanity is not None
        and team.humanity_score
        < choice.min_humanity
    ):
        return False

    if (
        choice.min_knowledge is not None
        and team.knowledge_score
        < choice.min_knowledge
    ):
        return False

    if choice.required_dominant_genre:
        if (
            get_dominant_genre(team)
            != choice.required_dominant_genre
        ):
            return False

    return True


def get_available_choices(team):
    if not team.current_station:
        return []

    choices = (
        team.current_station.choices
        .filter(is_active=True)
        .order_by(
            "sort_order",
            "id",
        )
    )

    return [
        choice
        for choice in choices
        if choice_is_available(
            choice,
            team,
        )
    ]


# ============================================================
# Automatic route matching
# ============================================================


def automatic_route_matches(route, team):
    flags = set(team.story_flags or [])

    required_flags = set(
        route.required_flags or []
    )

    forbidden_flags = set(
        route.forbidden_flags or []
    )

    if not required_flags.issubset(flags):
        return False

    if forbidden_flags.intersection(flags):
        return False

    if route.dominant_genre:
        if (
            get_dominant_genre(team)
            != route.dominant_genre
        ):
            return False

    if (
        route.min_containment is not None
        and team.containment_score
        < route.min_containment
    ):
        return False

    if (
        route.max_containment is not None
        and team.containment_score
        > route.max_containment
    ):
        return False

    if (
        route.min_humanity is not None
        and team.humanity_score
        < route.min_humanity
    ):
        return False

    if (
        route.max_humanity is not None
        and team.humanity_score
        > route.max_humanity
    ):
        return False

    if (
        route.min_knowledge is not None
        and team.knowledge_score
        < route.min_knowledge
    ):
        return False

    if (
        route.max_knowledge is not None
        and team.knowledge_score
        > route.max_knowledge
    ):
        return False

    return True


def resolve_automatic_stations(team):
    """
    Advance through AUTO stations until the team reaches:

    - a normal choice station,
    - an ending,
    - or an AUTO station with no matching route.
    """

    safety_counter = 0

    while (
        team.current_station
        and team.current_station.advance_mode
        == StoryStation.AdvanceMode.AUTO
    ):
        safety_counter += 1

        if safety_counter > 20:
            raise AdventureDecisionError(
                "Automatic story routing entered a loop."
            )

        routes = (
            AutomaticRoute.objects
            .filter(
                station=team.current_station,
            )
            .select_related(
                "target_station",
            )
            .order_by(
                "-priority",
                "id",
            )
        )

        matching_route = None

        for route in routes:
            if automatic_route_matches(
                route,
                team,
            ):
                matching_route = route
                break

        if matching_route is None:
            break

        team.current_station = (
            matching_route.target_station
        )

        if (
            team.current_station.station_type
            == StoryStation.StationType.ENDING
        ):
            team.is_finished = True
            team.ending_station = (
                team.current_station
            )

        team.save(
            update_fields=[
                "current_station",
                "is_finished",
                "ending_station",
            ]
        )

        if team.is_finished:
            break


# ============================================================
# Player decision submission
# ============================================================


@transaction.atomic
def submit_team_decision(
    *,
    team_id,
    choice_id,
    participant,
):
    team = (
        AdventureTeam.objects
        .select_for_update()
        .select_related(
            "current_station",
            "adventure_run",
            "adventure_run__session",
        )
        .get(id=team_id)
    )

    if team.is_finished:
        raise AdventureDecisionError(
            "This team has already completed the adventure."
        )

    if team.current_station is None:
        raise AdventureDecisionError(
            "This team does not have a current story station."
        )

    choice = (
        StoryChoice.objects
        .select_related(
            "station",
            "next_station",
        )
        .filter(
            id=choice_id,
            is_active=True,
        )
        .first()
    )

    if choice is None:
        raise AdventureDecisionError(
            "That choice is not available."
        )

    # Another teammate may already have submitted.
    if (
        choice.station_id
        != team.current_station_id
    ):
        raise AdventureDecisionError(
            "Your team has already moved to the next station."
        )

    if TeamDecision.objects.filter(
        team=team,
        station=team.current_station,
    ).exists():
        raise AdventureDecisionError(
            "Your team has already made this decision."
        )

    if not choice_is_available(
        choice,
        team,
    ):
        raise AdventureDecisionError(
            "That option is not available to your team."
        )

    previous_station = (
        team.current_station
    )

    TeamDecision.objects.create(
        team=team,
        station=previous_station,
        selected_choice=choice,
        selected_by=participant,
    )

    # --------------------------------------------------------
    # Scores
    # --------------------------------------------------------

    team.containment_score += (
        choice.containment_delta
    )

    team.humanity_score += (
        choice.humanity_delta
    )

    team.knowledge_score += (
        choice.knowledge_delta
    )

    team.sci_fi_score += (
        choice.sci_fi_delta
    )

    team.cyberpunk_score += (
        choice.cyberpunk_delta
    )

    team.bio_horror_score += (
        choice.bio_horror_delta
    )

    # --------------------------------------------------------
    # Flags
    # --------------------------------------------------------

    current_flags = list(
        team.story_flags or []
    )

    for flag in choice.set_flags or []:
        if flag not in current_flags:
            current_flags.append(flag)

    team.story_flags = (
        current_flags
    )

    # --------------------------------------------------------
    # Move to next station
    # --------------------------------------------------------

    team.current_station = (
        choice.next_station
    )

    if team.current_station is None:
        raise AdventureDecisionError(
            "This choice does not have a next station."
        )

    if (
        team.current_station.station_type
        == StoryStation.StationType.ENDING
    ):
        team.is_finished = True
        team.ending_station = (
            team.current_station
        )

    team.save(
        update_fields=[
            "containment_score",
            "humanity_score",
            "knowledge_score",
            "sci_fi_score",
            "cyberpunk_score",
            "bio_horror_score",
            "story_flags",
            "current_station",
            "is_finished",
            "ending_station",
        ]
    )

    if not team.is_finished:
        resolve_automatic_stations(
            team
        )

    return team


# ============================================================
# Team state reconstruction
# ============================================================


def _reset_team_state(
    team,
    start_station,
):
    """
    Reset runtime story state while preserving:

    - team membership
    - selected character
    - TeamDecision history
    """

    team.current_station = (
        start_station
    )

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


def _replay_choice(
    team,
    decision,
):
    """
    Reapply one existing TeamDecision.

    Does not create a new decision.
    """

    choice = (
        decision.selected_choice
    )

    if choice is None:
        raise AdventureDecisionError(
            "A saved decision refers to a choice "
            "that no longer exists."
        )

    if team.current_station is None:
        raise AdventureDecisionError(
            "The team has no current station "
            "while rebuilding its history."
        )

    if (
        decision.station_id
        != team.current_station_id
    ):
        raise AdventureDecisionError(
            "The team's decision history does not "
            "match its reconstructed story path."
        )

    if (
        choice.station_id
        != team.current_station_id
    ):
        raise AdventureDecisionError(
            "A saved choice does not belong to "
            "the expected story station."
        )

    if not choice_is_available(
        choice,
        team,
    ):
        raise AdventureDecisionError(
            (
                f'The saved choice "{choice.text}" '
                "is no longer valid for the "
                "reconstructed team state."
            )
        )

    # --------------------------------------------------------
    # Scores
    # --------------------------------------------------------

    team.containment_score += (
        choice.containment_delta
    )

    team.humanity_score += (
        choice.humanity_delta
    )

    team.knowledge_score += (
        choice.knowledge_delta
    )

    team.sci_fi_score += (
        choice.sci_fi_delta
    )

    team.cyberpunk_score += (
        choice.cyberpunk_delta
    )

    team.bio_horror_score += (
        choice.bio_horror_delta
    )

    # --------------------------------------------------------
    # Flags
    # --------------------------------------------------------

    flags = list(
        team.story_flags or []
    )

    for flag in choice.set_flags or []:
        if flag not in flags:
            flags.append(flag)

    team.story_flags = flags

    # --------------------------------------------------------
    # Advance
    # --------------------------------------------------------

    team.current_station = (
        choice.next_station
    )

    if team.current_station is None:
        raise AdventureDecisionError(
            "A saved choice does not have a next station."
        )

    team.is_finished = False
    team.ending_station = None

    if (
        team.current_station.station_type
        == StoryStation.StationType.ENDING
    ):
        team.is_finished = True

        team.ending_station = (
            team.current_station
        )

    team.save(
        update_fields=[
            "containment_score",
            "humanity_score",
            "knowledge_score",
            "sci_fi_score",
            "cyberpunk_score",
            "bio_horror_score",
            "story_flags",
            "current_station",
            "is_finished",
            "ending_station",
        ]
    )

    if not team.is_finished:
        resolve_automatic_stations(
            team
        )


def _rebuild_locked_team(team):
    """
    Reconstruct a team entirely from its existing
    TeamDecision history.

    The AdventureTeam row must already be locked.
    """

    story = (
        team.adventure_run.story
    )

    start_station = (
        StoryStation.objects
        .filter(
            story=story,
            is_start=True,
        )
        .order_by(
            "sort_order",
            "id",
        )
        .first()
    )

    if start_station is None:
        raise AdventureDecisionError(
            "This story does not have a start station."
        )

    decisions = list(
        TeamDecision.objects
        .filter(team=team)
        .select_related(
            "station",
            "selected_choice",
            "selected_choice__station",
            "selected_choice__next_station",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    _reset_team_state(
        team,
        start_station,
    )

    # Future stories could potentially begin
    # with an automatic station.
    resolve_automatic_stations(
        team
    )

    for decision in decisions:

        if team.is_finished:
            raise AdventureDecisionError(
                "The saved history contains decisions "
                "after the team reached an ending."
            )

        _replay_choice(
            team,
            decision,
        )

    team.refresh_from_db()

    return team


# ============================================================
# Public reconstruction helper
# ============================================================


@transaction.atomic
def rebuild_team_state(team_id):
    team = (
        AdventureTeam.objects
        .select_for_update()
        .select_related(
            "adventure_run",
            "adventure_run__story",
        )
        .get(id=team_id)
    )

    return _rebuild_locked_team(
        team
    )


# ============================================================
# Teacher intervention
# ============================================================


@transaction.atomic
def undo_last_team_decision(
    team_id,
):
    team = (
        AdventureTeam.objects
        .select_for_update()
        .select_related(
            "adventure_run",
            "adventure_run__story",
        )
        .get(id=team_id)
    )

    last_decision = (
        TeamDecision.objects
        .filter(team=team)
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )

    if last_decision is None:
        raise AdventureDecisionError(
            "This team has no decisions to undo."
        )

    undone_station = (
        last_decision.station
    )

    undone_choice = (
        last_decision.selected_choice
    )

    last_decision.delete()

    _rebuild_locked_team(
        team
    )

    return (
        team,
        undone_station,
        undone_choice,
    )


@transaction.atomic
def restart_team_adventure(
    team_id,
):
    team = (
        AdventureTeam.objects
        .select_for_update()
        .select_related(
            "adventure_run",
            "adventure_run__story",
        )
        .get(id=team_id)
    )

    TeamDecision.objects.filter(
        team=team,
    ).delete()

    _rebuild_locked_team(
        team
    )

    return team


@transaction.atomic
def rewind_team_to_station(
    *,
    team_id,
    station_id,
):
    team = (
        AdventureTeam.objects
        .select_for_update()
        .select_related(
            "adventure_run",
            "adventure_run__story",
            "current_station",
        )
        .get(id=team_id)
    )

    target_station = (
        StoryStation.objects
        .filter(
            id=station_id,
            story=team.adventure_run.story,
        )
        .first()
    )

    if target_station is None:
        raise AdventureDecisionError(
            "That station does not belong "
            "to this adventure."
        )

    if (
        team.current_station_id
        == target_station.id
    ):
        return team

    decisions = list(
        TeamDecision.objects
        .filter(team=team)
        .select_related(
            "station",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    target_index = None

    for index, decision in enumerate(
        decisions
    ):
        if (
            decision.station_id
            == target_station.id
        ):
            target_index = index
            break

    if target_index is None:
        raise AdventureDecisionError(
            "The team can only rewind to a station "
            "it previously visited."
        )

    # Delete the decision made AT the destination
    # and everything that occurred afterward.
    #
    # Rebuilding then naturally leaves the team
    # waiting at the chosen station.

    decisions_to_delete = (
        decisions[target_index:]
    )

    TeamDecision.objects.filter(
        id__in=[
            decision.id
            for decision
            in decisions_to_delete
        ]
    ).delete()

    _rebuild_locked_team(
        team
    )

    return team