# Create your views here.
from django.shortcuts import get_object_or_404, redirect, render

from games.models import GameTemplate
from sessions.models import GameSession, Participant
from .forms import PlayerCharacterForm
from .models import CharacterClass, PlayerCharacter


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