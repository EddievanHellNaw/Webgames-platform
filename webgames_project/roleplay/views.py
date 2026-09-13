from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from games.models import GameTemplate
from sessions.models import (
    GameSession,
    Participant,
)

from .models import (
    RoleAssignment,
    RolePlayRecordResponse,
    RolePlayRecordSubmission,
    RolePlayRun,
)

from .services import (
    RoleAssignmentError,
    assign_roles_to_run,
)


# ============================================================
# Helpers
# ============================================================


def _useful_language_items(text):
    """
    Turn:
        Have you ever...? Where did you go? Who...?

    into a list of question chips.
    """

    if not text:
        return []

    parts = []

    for item in text.split("?"):
        item = item.strip()

        if item:
            parts.append(f"{item}?")

    return parts


def _get_assignment_report_template(assignment):
    """
    Find the report that applies to this student's role.

    A report can either:
    - apply to everyone in the situation
    - apply specifically to this role
    """

    return (
        assignment.run.situation.record_templates
        .filter(
            Q(applies_to_all_roles=True)
            | Q(roles=assignment.role)
        )
        .prefetch_related("fields")
        .distinct()
        .order_by("sort_order", "id")
        .first()
    )


# ============================================================
# Student role screen
# ============================================================


def student_role(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
    )

    # This screen only belongs to Role Play sessions.
    if session.game_template.code != GameTemplate.GameCode.ROLE_PLAY:
        return redirect(
            "sessions:student_waiting_room",
            join_code=session.join_code,
        )

    # Identify this student from the browser session.
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

    # Students should remain in the waiting room
    # until the teacher starts the game.
    if session.status != GameSession.Status.ACTIVE:
        return redirect(
            "sessions:student_waiting_room",
            join_code=session.join_code,
        )

    run = get_object_or_404(
        RolePlayRun,
        game_session=session,
    )

    # IMPORTANT:
    # A student can now have one assignment PER ROUND.
    # We only retrieve their current assignment.
    assignment = get_object_or_404(
        RoleAssignment.objects.select_related(
            "role",
            "run",
            "run__situation",
        ),
        run=run,
        participant=participant,
        round_number=run.current_round,
    )

    # Mark the current role as viewed.
    if assignment.viewed_at is None:
        assignment.viewed_at = timezone.now()
        assignment.save(
            update_fields=["viewed_at"]
        )

    role = assignment.role_snapshot

    useful_language = _useful_language_items(
        role.get("useful_language", "")
    )

    report_template = _get_assignment_report_template(
        assignment
    )

    submission = None
    report_fields = []
    report_error = None

    # ========================================================
    # Report / Notes
    # ========================================================

    if report_template:

        submission = (
            RolePlayRecordSubmission.objects
            .filter(
                assignment=assignment,
                template=report_template,
                sequence=1,
            )
            .prefetch_related("responses")
            .first()
        )

        if request.method == "POST":

            # ------------------------------------------------
            # Protect against submitting an OLD round after
            # the teacher has already started a new one.
            # ------------------------------------------------

            posted_assignment_id = request.POST.get(
                "assignment_id"
            )

            if (
                posted_assignment_id
                and posted_assignment_id != str(assignment.id)
            ):

                messages.warning(
                    request,
                    "A new round has started. Your role has changed.",
                )

                return redirect(
                    "roleplay:student_role",
                    join_code=session.join_code,
                )

            # ------------------------------------------------
            # Create/retrieve this round's report.
            # ------------------------------------------------

            submission, _ = (
                RolePlayRecordSubmission.objects
                .get_or_create(
                    assignment=assignment,
                    template=report_template,
                    sequence=1,
                )
            )

            missing_required = []

            for field in report_template.fields.all():

                value = request.POST.get(
                    f"field_{field.id}",
                    "",
                ).strip()

                if field.required and not value:
                    missing_required.append(
                        field.label
                    )

                RolePlayRecordResponse.objects.update_or_create(
                    submission=submission,
                    field=field,
                    defaults={
                        "value": value,
                    },
                )

            action = request.POST.get(
                "report_action",
                "save",
            )

            # ------------------------------------------------
            # SUBMIT
            # ------------------------------------------------

            if action == "submit":

                if missing_required:

                    report_error = (
                        "Complete all required fields before "
                        "submitting your report."
                    )

                else:

                    submission.is_submitted = True
                    submission.submitted_at = timezone.now()

                    submission.save(
                        update_fields=[
                            "is_submitted",
                            "submitted_at",
                            "updated_at",
                        ]
                    )

                    messages.success(
                        request,
                        "Your report has been submitted.",
                    )

                    return redirect(
                        "roleplay:student_role",
                        join_code=session.join_code,
                    )

            # ------------------------------------------------
            # SAVE DRAFT
            # ------------------------------------------------

            else:

                submission.save(
                    update_fields=[
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    "Your notes have been saved.",
                )

                return redirect(
                    "roleplay:student_role",
                    join_code=session.join_code,
                )

        # ----------------------------------------------------
        # Build current values for the template.
        # ----------------------------------------------------

        response_values = {}

        if submission:

            response_values = {
                response.field_id: response.value
                for response in submission.responses.all()
            }

        for field in report_template.fields.all():

            report_fields.append(
                {
                    "field": field,
                    "value": response_values.get(
                        field.id,
                        "",
                    ),
                }
            )

    return render(
        request,
        "roleplay/student_role.html",
        {
            "session": session,
            "participant": participant,
            "assignment": assignment,
            "role": role,

            "current_round": run.current_round,

            "useful_language": useful_language,

            "report_template": report_template,
            "report_fields": report_fields,
            "submission": submission,
            "report_error": report_error,
        },
    )


# ============================================================
# Student round polling
# ============================================================


def student_role_status(request, join_code):
    """
    Called periodically by the student's phone.

    If the teacher starts another round, the assignment ID
    and/or round number changes. The JS can then reload the
    role page automatically.
    """

    session = get_object_or_404(
        GameSession,
        join_code=join_code,
    )

    participant_id = request.session.get(
        "participant_id"
    )

    if not participant_id:

        return JsonResponse(
            {
                "valid": False,
            }
        )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=session,
    )

    run = get_object_or_404(
        RolePlayRun,
        game_session=session,
    )

    assignment = (
        run.assignments
        .filter(
            participant=participant,
            round_number=run.current_round,
        )
        .first()
    )

    return JsonResponse(
        {
            "valid": True,
            "round": run.current_round,
            "assignment_id": (
                assignment.id
                if assignment
                else None
            ),
        }
    )


# ============================================================
# Teacher monitor
# ============================================================


@login_required
def teacher_monitor(request, join_code):

    run = get_object_or_404(
        RolePlayRun.objects.select_related(
            "game_session",
            "situation",
        ),
        game_session__join_code=join_code,
        game_session__teacher=request.user,
    )

    # IMPORTANT:
    # Only show assignments from the CURRENT round.
    assignments = list(
        run.assignments
        .filter(
            round_number=run.current_round,
        )
        .select_related(
            "participant",
            "role",
        )
        .prefetch_related(
            "record_submissions",
        )
        .order_by(
            "participant__display_name",
        )
    )

    viewed_count = sum(
        1
        for assignment in assignments
        if assignment.viewed_at
    )

    submitted_count = sum(
        1
        for assignment in assignments
        if any(
            submission.is_submitted
            for submission
            in assignment.record_submissions.all()
        )
    )

    return render(
        request,
        "roleplay/teacher_monitor.html",
        {
            "run": run,
            "session": run.game_session,
            "situation": run.situation,
            "assignments": assignments,

            "current_round": run.current_round,

            "total_students": len(assignments),
            "viewed_count": viewed_count,
            "submitted_count": submitted_count,
        },
    )


# ============================================================
# Teacher monitor AJAX status
# ============================================================


@login_required
def teacher_monitor_status(request, join_code):

    run = get_object_or_404(
        RolePlayRun,
        game_session__join_code=join_code,
        game_session__teacher=request.user,
    )

    assignments = (
        run.assignments
        .filter(
            round_number=run.current_round,
        )
        .select_related(
            "participant",
            "role",
        )
        .prefetch_related(
            "record_submissions",
        )
        .all()
    )

    students = []

    for assignment in assignments:

        submitted = any(
            submission.is_submitted
            for submission
            in assignment.record_submissions.all()
        )

        students.append(
            {
                "assignment_id": assignment.id,
                "participant_id": assignment.participant_id,
                "participant": assignment.participant.display_name,
                "role": assignment.role.name,
                "viewed": bool(assignment.viewed_at),
                "submitted": submitted,
            }
        )

    return JsonResponse(
        {
            "round": run.current_round,
            "students": students,
        }
    )


# ============================================================
# Start a new round / reassign roles
# ============================================================


@login_required
@require_POST
def reassign_roles(request, join_code):

    run = get_object_or_404(
        RolePlayRun.objects.select_related(
            "game_session",
        ),
        game_session__join_code=join_code,
        game_session__teacher=request.user,
    )

    if (
        run.game_session.status
        != GameSession.Status.ACTIVE
    ):

        messages.error(
            request,
            "Only an active Role Play session can begin a new round.",
        )

        return redirect(
            "roleplay:teacher_monitor",
            join_code=join_code,
        )

    try:

        with transaction.atomic():

            locked_run = (
                RolePlayRun.objects
                .select_for_update()
                .get(pk=run.pk)
            )

            next_round = (
                locked_run.current_round + 1
            )

            # Create fresh assignments FIRST.
            assign_roles_to_run(
                locked_run,
                round_number=next_round,
            )

            # Only switch the active round after
            # assignments were successfully created.
            locked_run.current_round = next_round

            locked_run.save(
                update_fields=[
                    "current_round",
                ]
            )

    except RoleAssignmentError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "roleplay:teacher_monitor",
            join_code=join_code,
        )

    messages.success(
        request,
        (
            f"Round {next_round} has started. "
            "New roles have been assigned."
        ),
    )

    return redirect(
        "roleplay:teacher_monitor",
        join_code=join_code,
    )


# ============================================================
# Teacher - individual student report history
# ============================================================


@login_required
def teacher_student_reports(
    request,
    join_code,
    participant_id,
):

    run = get_object_or_404(
        RolePlayRun.objects.select_related(
            "game_session",
            "situation",
        ),
        game_session__join_code=join_code,
        game_session__teacher=request.user,
    )

    participant = get_object_or_404(
        Participant,
        id=participant_id,
        session=run.game_session,
    )

    # ========================================================
    # SAVE TEACHER FEEDBACK
    # ========================================================

    if request.method == "POST":

        submission_id = request.POST.get(
            "submission_id"
        )

        submission = get_object_or_404(
            RolePlayRecordSubmission.objects.select_related(
                "assignment",
            ),
            id=submission_id,
            assignment__run=run,
            assignment__participant=participant,
        )

        feedback = request.POST.get(
            "teacher_feedback",
            "",
        ).strip()

        action = request.POST.get(
            "review_action",
            "save",
        )

        submission.teacher_feedback = feedback

        if action == "review":
            submission.reviewed_at = timezone.now()

        elif action == "unreview":
            submission.reviewed_at = None

        submission.save(
            update_fields=[
                "teacher_feedback",
                "reviewed_at",
                "updated_at",
            ]
        )

        if action == "review":
            messages.success(
                request,
                "Feedback saved and report marked as reviewed.",
            )

        elif action == "unreview":
            messages.success(
                request,
                "Report marked as needing review.",
            )

        else:
            messages.success(
                request,
                "Feedback saved.",
            )

        return redirect(
            "roleplay:teacher_student_reports",
            join_code=join_code,
            participant_id=participant.id,
        )

    # ========================================================
    # REPORT HISTORY
    # ========================================================

    assignments = (
        run.assignments
        .filter(
            participant=participant,
        )
        .select_related(
            "role",
        )
        .prefetch_related(
            "record_submissions__template",

            Prefetch(
                "record_submissions__responses",
                queryset=(
                    RolePlayRecordResponse.objects
                    .select_related("field")
                    .order_by(
                        "field__sort_order",
                        "field_id",
                    )
                ),
            ),
        )
        .order_by(
            "-round_number",
        )
    )

    return render(
        request,
        "roleplay/teacher_student_reports.html",
        {
            "run": run,
            "session": run.game_session,
            "situation": run.situation,
            "participant": participant,
            "assignments": assignments,
        },
    )