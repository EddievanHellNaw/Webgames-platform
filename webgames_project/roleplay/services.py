import secrets

from django.db import transaction

from .models import (
    RoleAssignment,
    RolePlayRun,
)


class RoleAssignmentError(Exception):
    pass

MARKET_MATCH_SLUG = "market-match-inspector"


def _build_market_match_pairs(roles):
    """
    Build pairs using the seeded sort order:

    1 + 2 = first pair
    3 + 4 = second pair
    5 + 6 = third pair
    etc.
    """

    grouped_roles = {}

    for role in roles:
        pair_number = (role.sort_order + 1) // 2

        grouped_roles.setdefault(
            pair_number,
            [],
        ).append(role)

    pairs = []

    for pair_number in sorted(grouped_roles):
        members = grouped_roles[pair_number]

        product_roles = [
            role
            for role in members
            if role.name.startswith("Product:")
        ]

        match_roles = [
            role
            for role in members
            if role.name.startswith("Match:")
        ]

        if (
            len(members) != 2
            or len(product_roles) != 1
            or len(match_roles) != 1
        ):
            raise RoleAssignmentError(
                (
                    f"Market Match pair {pair_number} is incomplete. "
                    "Every pair must contain one Product role and "
                    "one Match role."
                )
            )

        pairs.append(
            (
                product_roles[0],
                match_roles[0],
            )
        )

    return pairs


def _select_market_match_roles(
    roles,
    participants,
    previous_roles,
    rng,
):
    """
    Select complete Market Match pairs.

    For an odd number of students, duplicate one role from a
    selected pair. This creates one trio while preserving all
    natural matches.
    """

    participant_count = len(participants)

    if participant_count < 2:
        raise RoleAssignmentError(
            "At least two students are required for Market Match."
        )

    pairs = _build_market_match_pairs(roles)

    required_pair_count = participant_count // 2

    if required_pair_count > len(pairs):
        raise RoleAssignmentError(
            (
                f"{participant_count} students need "
                f"{required_pair_count} pairs, but only "
                f"{len(pairs)} complete pairs are available."
            )
        )

    def create_candidate():
        selected_pairs = rng.sample(
            pairs,
            required_pair_count,
        )

        candidate_roles = []

        for product_role, match_role in selected_pairs:
            candidate_roles.extend(
                [
                    product_role,
                    match_role,
                ]
            )

        # When attendance is odd, one selected pair becomes a trio.
        if participant_count % 2 == 1:
            trio_pair = rng.choice(selected_pairs)
            repeated_role = rng.choice(trio_pair)

            candidate_roles.append(
                repeated_role
            )

        rng.shuffle(candidate_roles)

        return candidate_roles

    # Try to avoid giving students their previous role.
    for _ in range(200):
        candidate_roles = create_candidate()

        valid = all(
            previous_roles.get(participant.id)
            != role.id
            for participant, role in zip(
                participants,
                candidate_roles,
            )
        )

        if valid:
            return candidate_roles

    # Repetition is allowed only when it is unavoidable.
    return create_candidate()

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

    # =======================================================
    # SPECIAL ASSIGNMENT: MARKET MATCH
    # =======================================================

    if run.situation.slug == MARKET_MATCH_SLUG:

        selected_roles = _select_market_match_roles(
            roles=roles,
            participants=participants,
            previous_roles=previous_roles,
            rng=rng,
        )

    # =======================================================
    # STANDARD ASSIGNMENT: ALL OTHER ROLE PLAYS
    # =======================================================

    else:

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

        # If avoiding repetition is impossible,
        # create a valid randomized round.
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