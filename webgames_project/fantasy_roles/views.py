# Create your views here.
from django.shortcuts import get_object_or_404, redirect, render

from games.models import GameTemplate
from sessions.models import GameSession, Participant
from .services import generate_dungeon_run
from django.contrib import messages
from django.db import models
import random
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .forms import PlayerCharacterForm
from .models import (
    ROOM_ROLL_AP_COST,
    CharacterClass,
    PlayerCharacter,
    AdventuringParty,
    PartyMember,
    Dungeon,
    DungeonRunConnection,
    DungeonVocabularySet,
    PartyDungeonRun,
    DungeonRunRoom,
    ItemTemplate,
    PartyInventoryItem,
    RoomAttempt,
    ClassSkill,
    ClassWeakness,
)


def get_student_participant(request, session):
    participant_id = request.session.get("participant_id")

    if not participant_id:
        return None

    return Participant.objects.filter(
        id=participant_id,
        session=session,
    ).first()


def character_create(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    existing_character = PlayerCharacter.objects.filter(
        session=session,
        participant=participant,
    ).first()

    if existing_character:
        return redirect(
            "fantasy_roles:character_detail",
            join_code=session.join_code,
        )

    character_classes = CharacterClass.objects.filter(is_active=True)

    if request.method == "POST":
        form = PlayerCharacterForm(
            request.POST,
            character_classes=character_classes,
        )

        if form.is_valid():
            player_character = form.save(commit=False)
            player_character.session = session
            player_character.participant = participant
            player_character.save()

            return redirect(
                "fantasy_roles:character_detail",
                join_code=session.join_code,
            )
    else:
        form = PlayerCharacterForm(character_classes=character_classes)

    return render(
        request,
        "fantasy_roles/character_create.html",
        {
            "session": session,
            "participant": participant,
            "form": form,
            "character_classes": character_classes,
        },
    )


def party_has_living_members(party):
    return PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
    ).exists()


def party_has_ap_remaining(party):
    return PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
        character__current_action_points__gt=0,
    ).exists()


def fail_dungeon_run(run, failure_reason):
    run.status = PartyDungeonRun.Status.FAILED
    run.failure_reason = failure_reason
    run.current_turn_character = None
    run.save(
        update_fields=[
            "status",
            "failure_reason",
            "current_turn_character",
            "updated_at",
        ]
    )


def check_dungeon_failure_state(run):
    if run.status != PartyDungeonRun.Status.ACTIVE:
        return False

    if not party_has_living_members(run.party):
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.PARTY_DEFEATED,
        )
        return True

    if not party_has_ap_remaining(run.party):
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.OUT_OF_AP,
        )
        return True

    return False

def transform_special_room_into_mimic(room):
    if room.room_type != DungeonRunRoom.RoomType.SPECIAL:
        return

    original_name = room.name or "Suspicious Chest"

    if not original_name.lower().startswith("mimic"):
        room.name = f"Mimic Ambush — {original_name}"

    room.room_type = DungeonRunRoom.RoomType.COMBAT

    if not room.flavor_text:
        room.flavor_text = (
            "The chest twists open with teeth and claws. "
            "It was a Mimic waiting for the perfect moment to attack!"
        )

    room.save(
        update_fields=[
            "name",
            "room_type",
            "flavor_text",
        ]
    )

def get_living_party_members(party):
    return list(
        PartyMember.objects
        .filter(
            party=party,
            character__current_life__gt=0,
        )
        .select_related(
            "character",
            "character__character_class",
        )
        .order_by("order", "joined_at")
    )


def ensure_run_has_turn(run):
    living_members = get_living_party_members(run.party)

    if not living_members:
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.PARTY_DEFEATED,
        )
        return None
    
    if not party_has_ap_remaining(run.party):
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.OUT_OF_AP,
        )
        return None

    living_character_ids = [
        member.character_id
        for member in living_members
    ]

    if run.current_turn_character_id in living_character_ids:
        return run.current_turn_character

    run.current_turn_character = living_members[0].character
    run.save(
        update_fields=[
            "current_turn_character",
            "updated_at",
        ]
    )

    return run.current_turn_character


def advance_room_turn(run):
    living_members = get_living_party_members(run.party)

    if not living_members:
        run.status = PartyDungeonRun.Status.FAILED
        run.current_turn_character = None
        run.save(
            update_fields=[
                "status",
                "current_turn_character",
                "updated_at",
            ]
        )
        return None

    living_characters = [
        member.character
        for member in living_members
    ]

    current_id = run.current_turn_character_id

    if current_id not in [character.id for character in living_characters]:
        next_character = living_characters[0]
    else:
        current_index = [
            character.id
            for character in living_characters
        ].index(current_id)

        next_index = (current_index + 1) % len(living_characters)
        next_character = living_characters[next_index]

    run.current_turn_character = next_character
    run.turn_number += 1
    run.save(
        update_fields=[
            "current_turn_character",
            "turn_number",
            "updated_at",
        ]
    )

    return next_character

def character_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    player_character = get_object_or_404(
        PlayerCharacter.objects.select_related(
            "character_class",
            "participant",
            "session",
        ),
        session=session,
        participant=participant,
    )

    skills = ClassSkill.objects.filter(
        character_class=player_character.character_class,
    ).order_by("ap_cost", "name")

    weaknesses = ClassWeakness.objects.filter(
        character_class=player_character.character_class,
    ).order_by("name")

    return render(
        request,
        "fantasy_roles/character_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": player_character,
            "skills": skills,
            "weaknesses": weaknesses,
        },
    )

ROOM_ROLL_AP_COST = 1


def get_room_weaknesses(character):
    return list(
        character.character_class.weaknesses.filter(
            weakness_scope=ClassWeakness.WeaknessScope.ROOM,
        )
    )


def get_weakness_value(weaknesses, effect_code, default=0):
    for weakness in weaknesses:
        if weakness.effect_code == effect_code:
            return weakness.effect_value
    return default


def has_weakness(weaknesses, effect_code):
    return any(
        weakness.effect_code == effect_code
        for weakness in weaknesses
    )


def spend_character_ap(character, amount):
    if amount <= 0:
        return True

    if character.current_action_points < amount:
        return False

    character.current_action_points -= amount
    character.save(update_fields=["current_action_points", "updated_at"])

    return True


def spend_character_life(character, amount):
    if amount <= 0:
        return True

    # Prevent a character from killing themselves with a room skill.
    if character.current_life <= amount:
        return False

    character.current_life -= amount
    character.save(update_fields=["current_life", "updated_at"])

    return True


def lose_character_ap(character, amount):
    if amount <= 0:
        return

    character.current_action_points = max(
        0,
        character.current_action_points - amount,
    )
    character.save(update_fields=["current_action_points", "updated_at"])


def recover_character_life(character, amount):
    if amount <= 0:
        return

    character.current_life = min(
        character.character_class.max_life,
        character.current_life + amount,
    )
    character.save(update_fields=["current_life", "updated_at"])


def set_next_room_skill_penalty(character, amount):
    if amount <= 0:
        return

    character.room_skill_ap_penalty = max(
        character.room_skill_ap_penalty,
        amount,
    )
    character.save(update_fields=["room_skill_ap_penalty", "updated_at"])


def clear_next_room_skill_penalty(character):
    if character.room_skill_ap_penalty == 0:
        return

    character.room_skill_ap_penalty = 0
    character.save(update_fields=["room_skill_ap_penalty", "updated_at"])

@login_required
def teacher_character_list(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        character_id = request.POST.get("character_id")

        character = get_object_or_404(
            PlayerCharacter,
            id=character_id,
            session=session,
        )

        if action == "approve_character":
            character.is_approved = True
            character.save(update_fields=["is_approved", "updated_at"])

            messages.success(
                request,
                f"{character.character_name} has been approved.",
            )

        elif action == "unapprove_character":
            character.is_approved = False
            character.save(update_fields=["is_approved", "updated_at"])

            messages.info(
                request,
                f"{character.character_name} has been marked for review.",
            )

        return redirect(
            "fantasy_roles:teacher_character_list",
            join_code=session.join_code,
        )

    characters = (
        PlayerCharacter.objects
        .filter(session=session)
        .select_related(
            "participant",
            "character_class",
        )
        .order_by("participant__joined_at", "character_name")
    )

    return render(
        request,
        "fantasy_roles/teacher_character_list.html",
        {
            "session": session,
            "characters": characters,
        },
    )

@login_required
def teacher_party_setup(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_party":
            party_name = request.POST.get("party_name", "").strip()

            if not party_name:
                party_count = AdventuringParty.objects.filter(session=session).count() + 1
                party_name = f"Party {party_count}"

            AdventuringParty.objects.get_or_create(
                session=session,
                name=party_name,
            )

        elif action == "add_member":
            party_id = request.POST.get("party_id")
            character_id = request.POST.get("character_id")

            party = get_object_or_404(
                AdventuringParty,
                id=party_id,
                session=session,
            )

            character = get_object_or_404(
                PlayerCharacter,
                id=character_id,
                session=session,
            )

            if PartyMember.objects.filter(character=character).exists():
                messages.warning(
                    request,
                    f"{character.character_name} is already assigned to a party.",
                )
            elif party.members.count() >= 4:
                messages.warning(
                    request,
                    f"{party.name} already has 4 members.",
                )
            else:
                PartyMember.objects.create(
                    party=party,
                    character=character,
                    order=party.members.count() + 1,
                )

        elif action == "remove_member":
            member_id = request.POST.get("member_id")

            member = get_object_or_404(
                PartyMember,
                id=member_id,
                party__session=session,
            )

            party = member.party

            if party.current_dm_id == member.character_id:
                party.current_dm = None
                party.save()

            member.delete()

        elif action == "set_dm":
            member_id = request.POST.get("member_id")

            member = get_object_or_404(
                PartyMember,
                id=member_id,
                party__session=session,
            )

            party = member.party
            party.current_dm = member.character
            party.save()

        elif action == "delete_party":
            party_id = request.POST.get("party_id")

            party = get_object_or_404(
                AdventuringParty,
                id=party_id,
                session=session,
            )

            party.delete()

        return redirect(
            "fantasy_roles:teacher_party_setup",
            join_code=session.join_code,
        )

    characters = (
        PlayerCharacter.objects
        .filter(session=session)
        .select_related(
            "participant",
            "character_class",
        )
        .order_by("participant__joined_at", "character_name")
    )

    unassigned_characters = characters.filter(
        party_membership__isnull=True,
    )

    parties = (
        AdventuringParty.objects
        .filter(session=session)
        .prefetch_related(
            "members__character__participant",
            "members__character__character_class",
        )
        .order_by("created_at", "name")
    )

    return render(
        request,
        "fantasy_roles/teacher_party_setup.html",
        {
            "session": session,
            "characters": characters,
            "unassigned_characters": unassigned_characters,
            "parties": parties,
        },
    )


def student_party_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    character = get_object_or_404(
        PlayerCharacter.objects.select_related(
            "character_class",
            "participant",
        ),
        session=session,
        participant=participant,
    )

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related(
            "party",
            "party__current_dm",
        )
        .first()
    )

    party_members = []
    is_current_dm = False
    existing_run = None

    if membership:
        party_members = (
            PartyMember.objects
            .filter(party=membership.party)
            .select_related(
                "character",
                "character__participant",
                "character__character_class",
            )
            .order_by("order", "joined_at")
        )

        is_current_dm = membership.party.current_dm_id == character.id

        existing_run = (
            PartyDungeonRun.objects
            .filter(party=membership.party)
            .select_related(
                "dungeon",
                "current_room",
            )
            .first()
        )

    return render(
        request,
        "fantasy_roles/student_party_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
            "party_members": party_members,
            "is_current_dm": is_current_dm,
            "existing_run": existing_run,
        },
    )

def build_teacher_dungeon_cards(session):
    parties = (
        AdventuringParty.objects
        .filter(session=session)
        .select_related("current_dm")
        .prefetch_related(
            "members__character__participant",
            "members__character__character_class",
        )
        .order_by("created_at", "name")
    )

    runs = (
        PartyDungeonRun.objects
        .filter(party__session=session)
        .select_related(
            "party",
            "dungeon",
            "current_room",
            "current_room__source_template",
            "selected_by_character",
        )
        .prefetch_related(
            "generated_rooms__source_template",
        )
    )

    runs_by_party_id = {
        run.party_id: run
        for run in runs
    }

    party_cards = []

    for party in parties:
        run = runs_by_party_id.get(party.id)
        generated_rooms = []
        cleared_count = 0
        total_rooms = 0
        progress = 0

        if run:
            generated_rooms = list(run.generated_rooms.all())
            total_rooms = len(generated_rooms)
            cleared_count = sum(1 for room in generated_rooms if room.is_cleared)

            if total_rooms:
                progress = round((cleared_count / total_rooms) * 100)

        party_cards.append(
            {
                "party": party,
                "members": list(party.members.all()),
                "run": run,
                "generated_rooms": generated_rooms,
                "cleared_count": cleared_count,
                "total_rooms": total_rooms,
                "progress": progress,
            }
        )

    return party_cards

@login_required
def teacher_dungeon_setup(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    party_cards = build_teacher_dungeon_cards(session)

    return render(
        request,
        "fantasy_roles/teacher_dungeon_setup.html",
        {
            "session": session,
            "party_cards": party_cards,
        },
    )

@login_required
def teacher_dungeon_monitor_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    party_cards = build_teacher_dungeon_cards(session)

    return render(
        request,
        "fantasy_roles/partials/_teacher_dungeon_monitor_panel.html",
        {
            "session": session,
            "party_cards": party_cards,
        },
    )

def build_student_dungeon_context(request, session):
    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    run = None
    connected_rooms = []
    connected_room_ids = []
    generated_rooms = []
    recent_attempts = []
    party_inventory = []
    party_members = []
    is_current_dm = False
    available_skills = []
    current_turn_character = None
    is_current_turn = False

    if membership:
        is_current_dm = membership.party.current_dm_id == character.id

        run = (
            PartyDungeonRun.objects
            .filter(party=membership.party)
            .select_related(
                "dungeon",
                "current_room",
                "current_room__source_template",
                "party",
                "party__current_dm",
                "current_turn_character",
            )
            .first()
        )

        party_members = (
            PartyMember.objects
            .filter(party=membership.party)
            .select_related(
                "character",
                "character__character_class",
                "party",
            )
            .order_by("order", "joined_at")
        )  
        party_inventory = (
            PartyInventoryItem.objects
            .filter(party=membership.party)
            .select_related("item")
        )

        if run:
            generated_rooms = (
                run.generated_rooms
                .select_related("source_template")
                .all()
            )
            current_turn_character = run.current_turn_character
            is_current_turn = (
                current_turn_character is not None
                and character is not None
                and current_turn_character.id == character.id
            )

        if run and run.current_room:
            connections = (
                DungeonRunConnection.objects
                .filter(
                    models.Q(from_room=run.current_room)
                    | models.Q(to_room=run.current_room)
                )
                .select_related(
                    "from_room",
                    "to_room",
                    "from_room__source_template",
                    "to_room__source_template",
                )
            )

            connected_rooms = [
                connection.other_room(run.current_room)
                for connection in connections
            ]

            connected_room_ids = [room.id for room in connected_rooms]

            recent_attempts = []
            latest_attempt = None

            if run:
                recent_attempts = list(
                    RoomAttempt.objects
                    .filter(room__run=run)
                    .select_related(
                        "character",
                        "character__character_class",
                        "skill_used",
                        "item_awarded",
                        "room",
                    )
                    .order_by("-created_at")[:8]
                )

                if recent_attempts:
                    latest_attempt = recent_attempts[0]

            if run and run.current_room:
                room_skills = (
                    character.character_class.skills
                    .filter(skill_scope=ClassSkill.SkillScope.ROOM)
                    .order_by("ap_cost", "name")
                )

                available_skills = [
                    skill
                    for skill in room_skills
                    if skill_can_be_used_in_room(skill, run.current_room)
                ]
        if run.status == PartyDungeonRun.Status.ACTIVE:
            ensure_run_has_turn(run)
            run.refresh_from_db()

    return {
        "session": session,
        "participant": participant,
        "character": character,
        "membership": membership,
        "run": run,
        "connected_rooms": connected_rooms,
        "connected_room_ids": connected_room_ids,
        "generated_rooms": generated_rooms,
        "recent_attempts": recent_attempts,
        "latest_attempt": latest_attempt,
        "party_inventory": party_inventory,
        "party_members": party_members,
        "is_current_dm": is_current_dm,
        "available_skills": available_skills,
        "current_turn_character": current_turn_character,
        "is_current_turn": is_current_turn,
    }

def student_dungeon_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/student_dungeon_detail.html",
        context,
    )

def student_dungeon_live_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/partials/_student_dungeon_live_shell.html",
        context,
    )


def student_inventory_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/partials/_inventory_contents.html",
        context,
    )

def student_dungeon_select(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    character = get_object_or_404(
        PlayerCharacter,
        session=session,
        participant=participant,
    )

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related("party", "party__current_dm")
        .first()
    )

    if membership is None:
        return redirect(
            "fantasy_roles:student_party_detail",
            join_code=session.join_code,
        )

    existing_run = (
        PartyDungeonRun.objects
        .filter(party=membership.party)
        .select_related("dungeon", "current_room", "selected_by_character")
        .first()
    )

    is_current_dm = membership.party.current_dm_id == character.id

    if request.method == "POST":
        if existing_run:
            messages.warning(
                request,
                "Your party has already chosen a dungeon.",
            )
            return redirect(
                "fantasy_roles:student_dungeon_detail",
                join_code=session.join_code,
            )

        if not is_current_dm:
            messages.warning(
                request,
                "Only the current DM can choose the dungeon for the party.",
            )
            return redirect(
                "fantasy_roles:student_dungeon_select",
                join_code=session.join_code,
            )

        dungeon_id = request.POST.get("dungeon_id")

        dungeon = get_object_or_404(
            Dungeon,
            id=dungeon_id,
            is_active=True,
        )

        run = PartyDungeonRun.objects.create(
            party=membership.party,
            dungeon=dungeon,
            selected_by_character=character,
            status=PartyDungeonRun.Status.SELECTED,
        )

        generate_dungeon_run(run)
        ensure_run_has_turn(run)

        messages.success(
            request,
            f"Your party chose {dungeon.name}.",
        )

        return redirect(
            "fantasy_roles:student_dungeon_detail",
            join_code=session.join_code,
        )

    dungeons = (
        Dungeon.objects
        .filter(is_active=True)
        .prefetch_related("vocabulary_sets")
    )

    vocabulary_by_dungeon = {}

    for dungeon in dungeons:
        vocabulary_by_dungeon[dungeon.id] = (
            dungeon.vocabulary_sets
            .filter(english_level=character.english_level)
            .first()
        )

    dungeons = Dungeon.objects.filter(is_active=True).order_by("order", "name")

    dungeon_cards = []

    for dungeon in dungeons:
        vocabulary_set = DungeonVocabularySet.objects.filter(
            dungeon=dungeon,
            english_level=character.english_level,
        ).first()

        dungeon_cards.append(
            {
                "dungeon": dungeon,
                "vocabulary_set": vocabulary_set,
            }
        )

    return render(
        request,
        "fantasy_roles/student_dungeon_select.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
            "existing_run": existing_run,
            "is_current_dm": is_current_dm,
            "dungeon_cards": dungeon_cards,
        },
    )

def get_student_character_and_membership(request, session):
    participant = get_student_participant(request, session)

    if participant is None:
        return None, None, None

    character = PlayerCharacter.objects.filter(
        session=session,
        participant=participant,
    ).first()

    if character is None:
        return participant, None, None

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related("party", "party__current_dm")
        .first()
    )

    return participant, character, membership


def apply_damage(character, damage):
    if damage <= 0:
        return

    character.current_life = max(0, character.current_life - damage)
    character.save(update_fields=["current_life", "updated_at"])


def party_is_defeated(party):
    return not PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
    ).exists()


def award_random_item_to_party(party, dungeon, room):
    eligible_items = (
        ItemTemplate.objects
        .filter(is_active=True)
        .filter(
            models.Q(scope=ItemTemplate.ItemScope.GLOBAL)
            | models.Q(dungeon=dungeon)
        )
    )

    items = list(eligible_items)

    if not items:
        return None

    item = random.choice(items)

    inventory_item, created = PartyInventoryItem.objects.get_or_create(
        party=party,
        item=item,
        defaults={
            "quantity": 0,
            "obtained_in_room": room,
        },
    )

    inventory_item.quantity += 1

    if inventory_item.obtained_in_room is None:
        inventory_item.obtained_in_room = room

    inventory_item.save()

    return item

def spend_character_ap(character, amount):
    if amount <= 0:
        return True

    if character.current_action_points < amount:
        return False

    character.current_action_points -= amount
    character.save(update_fields=["current_action_points", "updated_at"])

    return True

def update_run_status_after_room_result(run):
    if check_dungeon_failure_state(run):
        return
    if party_is_defeated(run.party):
        run.status = PartyDungeonRun.Status.FAILED
        run.save(update_fields=["status", "updated_at"])
        return

    uncleared_rooms_exist = run.generated_rooms.filter(
        is_cleared=False,
    ).exists()

    if not uncleared_rooms_exist:
        run.status = PartyDungeonRun.Status.BOSS_READY
        run.save(update_fields=["status", "updated_at"])

def submit_room_action(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    room = run.current_room

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "This dungeon is not currently active.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if room.is_cleared:
        messages.warning(request, "This room has already been cleared.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if character.current_life <= 0:
        messages.warning(request, "Your character cannot act because they have 0 life.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
    ensure_run_has_turn(run)

    if run.current_turn_character_id != character.id:
        if run.current_turn_character:
            messages.warning(
                request,
                f"It is {run.current_turn_character.character_name}'s turn.",
            )
        else:
            messages.warning(
                request,
                "There is no active turn right now.",
            )

        return redirect(
            "fantasy_roles:student_dungeon_detail",
            join_code=session.join_code,
        )

    action_text = request.POST.get("action_text", "").strip()
    submitted_action_type = request.POST.get("action_type", "").strip()

    skill = None
    room_weaknesses = get_room_weaknesses(character)

    ap_cost = ROOM_ROLL_AP_COST
    life_cost = 0

    roll_modifier = 0
    effective_difficulty = room.difficulty
    failure_damage_reduction = 0
    recover_life_on_success = 0
    reroll_after_fail = False
    random_bonus_roll = None
    random_bonus_applied = False

    action_type = submitted_action_type

    if submitted_action_type == RoomAttempt.ActionType.SKILL:
        skill_id = request.POST.get("skill_id")

        skill = get_object_or_404(
            ClassSkill,
            id=skill_id,
            character_class=character.character_class,
        )

        if not skill_can_be_used_in_room(skill, room):
            messages.warning(request, "This skill cannot be used in this room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        ap_cost = skill.ap_cost + character.room_skill_ap_penalty
        action_type = RoomAttempt.ActionType.SKILL

        if has_weakness(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_SKILLS_COST_LIFE,
        ):
            life_cost = ap_cost
            ap_cost = 0

        effect_code = skill.effect_code

        if effect_code == ClassSkill.EffectCode.ROOM_REDUCE_DIFFICULTY:
            effective_difficulty = max(
                0,
                room.difficulty - skill.effect_value,
            )

        elif effect_code == ClassSkill.EffectCode.ROOM_ROLL_BONUS:
            roll_modifier += skill.effect_value or skill.roll_bonus

        elif effect_code == ClassSkill.EffectCode.ROOM_REDUCE_FAILURE_DAMAGE:
            failure_damage_reduction += skill.effect_value

        elif effect_code == ClassSkill.EffectCode.ROOM_REROLL_AFTER_FAIL:
            reroll_after_fail = True

        elif effect_code == ClassSkill.EffectCode.ROOM_RANDOM_ROLL_BONUS:
            random_bonus_roll = random.randint(1, 6)

            if random_bonus_roll >= 4:
                roll_modifier += skill.effect_value
                random_bonus_applied = True

        elif effect_code == ClassSkill.EffectCode.ROOM_RECOVER_LIFE_ON_SUCCESS:
            effective_difficulty = max(
                0,
                room.difficulty - skill.effect_value,
            )
            recover_life_on_success = skill.secondary_value

        elif effect_code == ClassSkill.EffectCode.ROOM_FIELD_AID:
            failure_damage_reduction += skill.effect_value

    elif submitted_action_type == RoomAttempt.ActionType.LEAVE_TREASURE:
        ap_cost = 0
        action_type = RoomAttempt.ActionType.LEAVE_TREASURE

    # Room weakness roll penalties.
    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        roll_modifier -= get_weakness_value(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_TRAP_ROLL_PENALTY,
        )

    if room.room_type == DungeonRunRoom.RoomType.COMBAT:
        roll_modifier -= get_weakness_value(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_COMBAT_ROLL_PENALTY,
        )

    if not spend_character_ap(character, ap_cost):
        messages.warning(
            request,
            f"You need {ap_cost} AP to do that action.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if not spend_character_life(character, life_cost):
        messages.warning(
            request,
            f"You need more than {life_cost} Life to use that skill.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if skill:
        clear_next_room_skill_penalty(character)

    die_roll = None
    first_die_roll = None
    final_roll_total = None
    success = False
    damage_taken = 0
    item_awarded = None
    result_text_parts = []

    if skill:
        result_text_parts.append(
            f"{character.character_name} used {skill.name}."
        )

    if effective_difficulty != room.difficulty:
        result_text_parts.append(
            f"Room difficulty changed from {room.difficulty} to {effective_difficulty}."
        )

    if roll_modifier > 0:
        result_text_parts.append(
            f"Roll bonus: +{roll_modifier}."
        )

    if roll_modifier < 0:
        result_text_parts.append(
            f"Roll penalty: {roll_modifier}."
        )

    if failure_damage_reduction:
        result_text_parts.append(
            f"Failure damage will be reduced by {failure_damage_reduction}."
        )
    if random_bonus_roll is not None:
        if random_bonus_applied:
            result_text_parts.append(
                f"Quick Invention rolled {random_bonus_roll}, so +{skill.effect_value} was added."
            )
        else:
            result_text_parts.append(
                f"Quick Invention rolled {random_bonus_roll}, so no bonus was added."
            )

    # Treasure room: leaving safely does not require a roll.
    if (
        room.room_type in [
            DungeonRunRoom.RoomType.TREASURE,
            DungeonRunRoom.RoomType.SPECIAL,
        ]
        and action_type == RoomAttempt.ActionType.LEAVE_TREASURE
    ):
        success = True
        room.is_cleared = True
        room.save(update_fields=["is_cleared"])

        if room.room_type == DungeonRunRoom.RoomType.SPECIAL:
            result_text_parts.append(
                "The party decided not to touch the suspicious chest and moved on safely."
            )
        else:
            result_text_parts.append(
                "The party left the treasure room safely."
            )

    else:
        if (
            room.room_type == DungeonRunRoom.RoomType.TRAP
            and not action_text
            and action_type != RoomAttempt.ActionType.SKILL
            ):
        
            messages.warning(request, "Write an action before rolling for this room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
        
        first_die_roll = random.randint(1, 6)
        die_roll = first_die_roll
        final_roll_total = die_roll + roll_modifier
        success = final_roll_total > effective_difficulty

        if not success and reroll_after_fail:
            second_die_roll = random.randint(1, 6)
            die_roll = second_die_roll
            final_roll_total = die_roll + roll_modifier
            success = final_roll_total > effective_difficulty

            result_text_parts.append(
                f"Shadow Step activated: first roll {first_die_roll}, reroll {second_die_roll}."
            )

        # Room-specific default action labels.
        if room.room_type == DungeonRunRoom.RoomType.TRAP and not skill:
            action_type = RoomAttempt.ActionType.TRAP_ACTION

        elif room.room_type == DungeonRunRoom.RoomType.COMBAT and not skill:
            action_type = RoomAttempt.ActionType.BASIC_ATTACK

        elif room.room_type == DungeonRunRoom.RoomType.SPECIAL and not skill:
            action_type = RoomAttempt.ActionType.SPECIAL_ACTION

        elif room.room_type == DungeonRunRoom.RoomType.TREASURE and not skill:
            action_type = RoomAttempt.ActionType.OPEN_CHEST

        if success:
            if room.room_type in [
                DungeonRunRoom.RoomType.TREASURE,
                DungeonRunRoom.RoomType.SPECIAL,
            ]:
                item_awarded = award_random_item_to_party(
                    membership.party,
                    run.dungeon,
                    room,
                )

            if recover_life_on_success:
                recover_character_life(character, recover_life_on_success)
                result_text_parts.append(
                    f"{character.character_name} recovered {recover_life_on_success} Life."
                )

            room.is_cleared = True
            room.save(update_fields=["is_cleared"])

            if item_awarded:
                result_text_parts.append(
                    f"Success! You rolled {die_roll}"
                    f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                    f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                    f" = {final_roll_total} and found {item_awarded.name}."
                )
            else:
                result_text_parts.append(
                    f"Success! You rolled {die_roll}"
                    f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                    f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                    f" = {final_roll_total} and cleared the room."
                )

        else:
            if room.room_type == DungeonRunRoom.RoomType.TRAP:
                base_damage = room.difficulty
            else:
                base_damage = room.damage_on_failure or room.difficulty

            extra_damage = 0

            if room.room_type == DungeonRunRoom.RoomType.TRAP:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_TRAP_FAIL_DAMAGE,
                )

            if room.room_type == DungeonRunRoom.RoomType.COMBAT:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_COMBAT_FAIL_DAMAGE,
                )

            if skill:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_DAMAGE_AFTER_SKILL_FAIL,
                )

            damage_taken = max(
                0,
                base_damage + extra_damage - failure_damage_reduction,
            )

            apply_damage(character, damage_taken)

            if (
                room.room_type == DungeonRunRoom.RoomType.SPECIAL
                and action_type == RoomAttempt.ActionType.OPEN_CHEST
            ):
                transform_special_room_into_mimic(room)

                result_text_parts.append(
                    "The chest was a Mimic! It transforms into a Combat Room."
                )

            next_skill_penalty = get_weakness_value(
                room_weaknesses,
                ClassWeakness.EffectCode.ROOM_NEXT_SKILL_COST_AFTER_FAIL,
            )

            if next_skill_penalty:
                set_next_room_skill_penalty(character, next_skill_penalty)
                result_text_parts.append(
                    f"Broken Focus: your next room skill costs +{next_skill_penalty} AP."
                )

            result_text_parts.append(
                f"Failure. You rolled {die_roll}"
                f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                f" = {final_roll_total}. "
                f"{character.character_name} took {damage_taken} damage."
            )

        # Artificer weakness: natural room roll 1 or 2 loses AP.
        low_roll_threshold = 0

        for weakness in room_weaknesses:
            if weakness.effect_code == ClassWeakness.EffectCode.ROOM_LOSE_AP_ON_LOW_NATURAL_ROLL:
                low_roll_threshold = weakness.secondary_value
                ap_loss = weakness.effect_value

                if die_roll is not None and die_roll <= low_roll_threshold:
                    lose_character_ap(character, ap_loss)
                    result_text_parts.append(
                        f"Unstable Tools: natural roll {die_roll}, so {character.character_name} lost {ap_loss} AP."
                    )

    result_text = " ".join(result_text_parts)

    attempt = RoomAttempt.objects.create(
        room=room,
        character=character,
        action_type=action_type,
        skill_used=skill,
        action_text=action_text,
        die_roll=die_roll,
        roll_bonus=roll_modifier,
        final_roll_total=final_roll_total,
        difficulty_at_roll=effective_difficulty,
        success=success,
        damage_taken=damage_taken,
        item_awarded=item_awarded,
        result_text=result_text,
    )

    update_run_status_after_room_result(run)
    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.ACTIVE:
        next_character = advance_room_turn(run)

        if next_character:
            result_text = (
                f"{result_text} "
                f"Next turn: {next_character.character_name}."
            )

            attempt.result_text = result_text
            attempt.save(update_fields=["result_text"])

    messages.info(request, result_text)

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def move_to_room(request, join_code, room_id):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "The party cannot move right now.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if membership.party.current_dm_id != character.id:
        messages.warning(request, "Only the current DM can move the party.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if not run.current_room.is_cleared:
        messages.warning(request, "Clear the current room before moving.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    target_room = get_object_or_404(
        DungeonRunRoom,
        id=room_id,
        run=run,
    )

    connection_exists = DungeonRunConnection.objects.filter(
        run=run,
    ).filter(
        models.Q(from_room=run.current_room, to_room=target_room)
        | models.Q(from_room=target_room, to_room=run.current_room)
    ).exists()

    if not connection_exists:
        messages.warning(request, "That room is not connected to your current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run.current_room = target_room
    run.save(update_fields=["current_room", "updated_at"])

    messages.success(
        request,
        f"The party moved to Room {target_room.room_number}: {target_room.name}.",
    )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def reset_party_ap(party):
    memberships = (
        PartyMember.objects
        .filter(party=party)
        .select_related("character", "character__character_class")
    )

    for membership in memberships:
        character = membership.character
        character.current_action_points = character.character_class.action_points
        character.save(update_fields=["current_action_points", "updated_at"])


def skill_can_be_used_in_room(skill, room):
    if skill.skill_scope != ClassSkill.SkillScope.ROOM:
        return False

    if room.room_type == DungeonRunRoom.RoomType.COMBAT:
        return skill.can_use_in_combat

    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        return skill.can_use_in_trap

    if room.room_type == DungeonRunRoom.RoomType.TREASURE:
        return skill.can_use_in_treasure

    if room.room_type == DungeonRunRoom.RoomType.SPECIAL:
        return False

    return False

def pass_room_turn(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "The party cannot pass turns right now.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room.is_cleared:
        messages.warning(request, "The room is already cleared.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    ensure_run_has_turn(run)
    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.FAILED:
        messages.warning(
            request,
            "The dungeon has failed.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
    
    if run.current_turn_character_id != character.id:
        if run.current_turn_character:
            messages.warning(
                request,
                f"It is {run.current_turn_character.character_name}'s turn.",
            )
        else:
            messages.warning(request, "There is no active turn right now.")

        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    next_character = advance_room_turn(run)

    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.FAILED:
        messages.warning(
            request,
            "The dungeon has failed.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if next_character:
        messages.info(
            request,
            f"{character.character_name} passed. Next turn: {next_character.character_name}.",
        )
    else:
        messages.warning(
            request,
            "No living characters remain.",
        )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)