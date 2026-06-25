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

            recent_attempts = (
                RoomAttempt.objects
                .filter(room=run.current_room)
                .select_related(
                    "character",
                    "skill_used",
                    "item_awarded",
                )
                [:5]
            )

            available_skills = [
                skill for skill in character.character_class.skills.all()
                if skill_can_be_used_in_room(skill, run.current_room)
            ]

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
        "party_inventory": party_inventory,
        "party_members": party_members,
        "is_current_dm": is_current_dm,
        "available_skills": available_skills,
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
        "fantasy_roles/partials/student_dungeon_live_panel.html",
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


def update_run_status_after_room_result(run):
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

    action_text = request.POST.get("action_text", "").strip()
    action_type = request.POST.get("action_type", "").strip()

    skill = None
    roll_bonus = 0
    final_roll_total = None

    if action_type == RoomAttempt.ActionType.SKILL:
        skill_id = request.POST.get("skill_id")

        skill = get_object_or_404(
            ClassSkill,
            id=skill_id,
            character_class=character.character_class,
        )

        if not skill_can_be_used_in_room(skill, room):
            messages.warning(request, "This skill cannot be used in this room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        if character.current_action_points < skill.ap_cost:
            messages.warning(request, "You do not have enough AP to use this skill.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        character.current_action_points -= skill.ap_cost
        character.save(update_fields=["current_action_points", "updated_at"])

        roll_bonus = skill.roll_bonus

    die_roll = None
    success = False
    damage_taken = 0
    item_awarded = None
    result_text = ""

    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        action_type = RoomAttempt.ActionType.TRAP_ACTION

        if not action_text:
            messages.warning(request, "Write an action before rolling for a trap room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        die_roll = random.randint(1, 6)
        success = die_roll > room.difficulty

        if success:
            room.is_cleared = True
            room.save(update_fields=["is_cleared"])
            reset_party_ap(membership.party)
            result_text = f"Success! You rolled {die_roll} and cleared the trap."
        else:
            damage_taken = room.difficulty
            apply_damage(character, damage_taken)
            result_text = (
                f"Failure. You rolled {die_roll}. "
                f"{character.character_name} took {damage_taken} damage."
            )

    elif room.room_type == DungeonRunRoom.RoomType.COMBAT:
        if action_type == RoomAttempt.ActionType.SKILL:
            action_type = RoomAttempt.ActionType.SKILL
        else:
            action_type = RoomAttempt.ActionType.BASIC_ATTACK

        die_roll = random.randint(1, 6)
        final_roll_total = die_roll + roll_bonus
        success = final_roll_total > room.difficulty

        if success:
            room.is_cleared = True
            room.save(update_fields=["is_cleared"])
            reset_party_ap(membership.party)

            if skill:
                result_text = (
                    f"Success! {character.character_name} used {skill.name}, "
                    f"rolled {die_roll} + {roll_bonus} = {final_roll_total}, "
                    "and defeated the enemy."
                )
            else:
                result_text = (
                    f"Success! You rolled {die_roll} and defeated the enemy."
                )
        else:
            damage_taken = room.damage_on_failure or room.difficulty
            apply_damage(character, damage_taken)

            if skill:
                result_text = (
                    f"Failure. {character.character_name} used {skill.name}, "
                    f"rolled {die_roll} + {roll_bonus} = {final_roll_total}. "
                    f"{character.character_name} took {damage_taken} damage."
                )
            else:
                result_text = (
                    f"Failure. You rolled {die_roll}. "
                    f"{character.character_name} took {damage_taken} damage."
                )

    elif room.room_type == DungeonRunRoom.RoomType.SPECIAL:
        action_type = RoomAttempt.ActionType.SPECIAL_ACTION

        die_roll = random.randint(1, 6)
        success = die_roll > room.difficulty

        if success:
            room.is_cleared = True
            room.save(update_fields=["is_cleared"])
            reset_party_ap(membership.party)
            result_text = f"Success! You rolled {die_roll} and survived the special room."
        else:
            damage_taken = room.damage_on_failure or room.difficulty
            apply_damage(character, damage_taken)
            result_text = (
                f"Failure. You rolled {die_roll}. "
                f"{character.character_name} took {damage_taken} damage."
            )

    elif room.room_type == DungeonRunRoom.RoomType.TREASURE:
        if action_type == RoomAttempt.ActionType.LEAVE_TREASURE:
            success = True
            room.is_cleared = True
            room.save(update_fields=["is_cleared"])
            reset_party_ap(membership.party)
            result_text = "The party left the treasure room safely."

        else:
            action_type = RoomAttempt.ActionType.OPEN_CHEST
            die_roll = random.randint(1, 6)
            success = die_roll > room.difficulty

            if success:
                item_awarded = award_random_item_to_party(
                    membership.party,
                    run.dungeon,
                    room,
                )
                room.is_cleared = True
                room.save(update_fields=["is_cleared"])
                reset_party_ap(membership.party)

                if item_awarded:
                    result_text = (
                        f"Success! You rolled {die_roll} and found "
                        f"{item_awarded.name}."
                    )
                else:
                    result_text = (
                        f"Success! You rolled {die_roll}, but no items are available yet."
                    )
            else:
                damage_taken = room.damage_on_failure or room.difficulty
                apply_damage(character, damage_taken)
                result_text = (
                    f"Failure. You rolled {die_roll}. "
                    f"{character.character_name} took {damage_taken} damage."
                )

    else:
        messages.warning(request, "This room type is not ready yet.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    RoomAttempt.objects.create(
        room=room,
        character=character,
        action_type=action_type,
        skill_used=skill,
        action_text=action_text,
        die_roll=die_roll,
        roll_bonus=roll_bonus,
        final_roll_total=final_roll_total,
        difficulty_at_roll=room.difficulty,
        success=success,
        damage_taken=damage_taken,
        item_awarded=item_awarded,
        result_text=result_text,
    )

    update_run_status_after_room_result(run)

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
    if room.room_type == DungeonRunRoom.RoomType.COMBAT:
        return skill.can_use_in_combat

    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        return skill.can_use_in_trap

    if room.room_type == DungeonRunRoom.RoomType.SPECIAL:
        return skill.can_use_in_special

    return False