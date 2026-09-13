import secrets

from django.db import transaction

from .models import (
    RoleAssignment,
    RolePlayRun,
)


class RoleAssignmentError(Exception):
    pass


def build_role_snapshot(role):
    return {
        "role_id": role.id,
        "name": role.name,
        "character_name": role.character_name,
        "public_description": role.public_description,
        "private_briefing": role.private_briefing,
        "objective": role.objective,
        "secret_information": role.secret_information,
        "useful_language": role.useful_language,

        "situation": {
            "title": role.situation.title,
            "student_briefing": role.situation.student_briefing,
            "language_target": role.situation.language_target,
        },
    }


@transaction.atomic
def assign_roles_to_run(
    run,
    round_number=None,
):
    """
    Assign one role to every current participant for one round.

    Existing assignments for that round are preserved.

    Whenever possible, students will NOT receive the same role
    they had in the immediately previous round.
    """

    run = (
        RolePlayRun.objects
        .select_for_update()
        .select_related(
            "game_session",
            "situation",
        )
        .get(pk=run.pk)
    )

    if round_number is None:
        round_number = run.current_round

    existing_assignments = list(
        run.assignments
        .filter(
            round_number=round_number,
        )
        .select_related(
            "participant",
            "role",
        )
    )

    if existing_assignments:
        return existing_assignments

    participants = list(
        run.game_session
        .participants
        .all()
        .order_by("joined_at")
    )

    if not participants:
        raise RoleAssignmentError(
            "At least one student must join before roles can be assigned."
        )

    roles = list(
        run.situation.roles
        .filter(is_active=True)
        .order_by(
            "sort_order",
            "id",
        )
    )

    role_pool = []

    for role in roles:
        role_pool.extend(
            [role] * role.copies_available
        )

    if not role_pool:
        raise RoleAssignmentError(
            "This situation does not have any active roles."
        )

    if len(participants) > len(role_pool):
        raise RoleAssignmentError(
            (
                f"{len(participants)} students are in the session, "
                f"but only {len(role_pool)} role slots are available."
            )
        )

    # -----------------------------------------------
    # Find everyone's previous role.
    # -----------------------------------------------

    previous_roles = {}

    if round_number > 1:

        previous_roles = dict(
            run.assignments
            .filter(
                round_number=round_number - 1,
            )
            .values_list(
                "participant_id",
                "role_id",
            )
        )

    rng = secrets.SystemRandom()

    selected_roles = None

    # -----------------------------------------------
    # Try several randomized arrangements until we
    # find one in which nobody repeats their last role.
    # -----------------------------------------------

    for _ in range(200):

        candidate_pool = list(role_pool)
        rng.shuffle(candidate_pool)

        candidate_roles = candidate_pool[
            :len(participants)
        ]

        valid = all(
            previous_roles.get(participant.id)
            != role.id
            for participant, role
            in zip(
                participants,
                candidate_roles,
            )
        )

        if valid:
            selected_roles = candidate_roles
            break

    # If a non-repeating arrangement is impossible,
    # still create a valid randomized round.
    if selected_roles is None:

        candidate_pool = list(role_pool)
        rng.shuffle(candidate_pool)

        selected_roles = candidate_pool[
            :len(participants)
        ]

    assignments = []

    for participant, role in zip(
        participants,
        selected_roles,
    ):

        assignment = RoleAssignment.objects.create(
            run=run,
            participant=participant,
            role=role,
            round_number=round_number,
            role_snapshot=build_role_snapshot(role),
        )

        assignments.append(assignment)

    return assignments