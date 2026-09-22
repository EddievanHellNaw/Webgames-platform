from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from sessions.models import GameSession, Participant


def student_hunt(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
    )

    participant_id = request.session.get(
        "participant_id"
    )

    participant = None

    if participant_id:
        participant = (
            Participant.objects
            .filter(
                id=participant_id,
                session=session,
            )
            .first()
        )

    return render(
        request,
        "treasure_hunt/student_hunt.html",
        {
            "session": session,
            "participant": participant,
        },
    )


@login_required
def teacher_hunt(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
    )

    return render(
        request,
        "treasure_hunt/teacher_hunt.html",
        {
            "session": session,
        },
    )