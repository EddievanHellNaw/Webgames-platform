# Create your views here.
from django.shortcuts import get_object_or_404, redirect, render

from games.models import GameTemplate
from sessions.models import GameSession, Participant
from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .forms import PlayerCharacterForm
from .models import (
    CharacterClass,
    PlayerCharacter,
    AdventuringParty,
    PartyMember,
    Dungeon,
    DungeonRoomConnection,
    DungeonVocabularySet,
    PartyDungeonRun,
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
        PlayerCharacter,
        session=session,
        participant=participant,
    )

    return render(
        request,
        "fantasy_roles/character_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": player_character,
        },
    )


def teacher_character_list(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    characters = PlayerCharacter.objects.filter(
        session=session,
    ).select_related(
        "participant",
        "character_class",
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

    characters = PlayerCharacter.objects.filter(
        session=session,
    ).select_related(
        "participant",
        "character_class",
    )

    unassigned_characters = characters.filter(
        party_membership__isnull=True,
    )

    parties = AdventuringParty.objects.filter(
        session=session,
    ).prefetch_related(
        "members__character__participant",
        "members__character__character_class",
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
        PlayerCharacter,
        session=session,
        participant=participant,
    )

    membership = PartyMember.objects.filter(
        character=character,
    ).select_related(
        "party",
    ).first()

    return render(
        request,
        "fantasy_roles/student_party_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
        },
    )

@login_required
def teacher_dungeon_setup(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    parties = (
        AdventuringParty.objects
        .filter(session=session)
        .select_related(
            "current_dm",
            "dungeon_run__dungeon",
            "dungeon_run__current_room",
            "dungeon_run__selected_by_character",
        )
        .prefetch_related(
            "members__character__participant",
            "members__character__character_class",
        )
    )

    return render(
        request,
        "fantasy_roles/teacher_dungeon_setup.html",
        {
            "session": session,
            "parties": parties,
        },
    )

def student_dungeon_detail(request, join_code):
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
        .select_related("party")
        .first()
    )

    run = None
    connected_rooms = []

    if membership:
        run = (
            PartyDungeonRun.objects
            .filter(party=membership.party)
            .select_related("dungeon", "current_room")
            .first()
        )

        if run and run.current_room:
            connections = (
                DungeonRoomConnection.objects
                .filter(
                    models.Q(from_room=run.current_room)
                    | models.Q(to_room=run.current_room)
                )
                .select_related("from_room", "to_room")
            )

            connected_rooms = [
                connection.other_room(run.current_room)
                for connection in connections
            ]

    return render(
        request,
        "fantasy_roles/student_dungeon_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
            "run": run,
            "connected_rooms": connected_rooms,
        },
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

        PartyDungeonRun.objects.create(
            party=membership.party,
            dungeon=dungeon,
            selected_by_character=character,
            status=PartyDungeonRun.Status.SELECTED,
        )

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