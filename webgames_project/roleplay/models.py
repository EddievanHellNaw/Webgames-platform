from django.db import models
from sessions.models import GameSession, Participant


class RolePlaySituation(models.Model):
    """
    A complete role-play scenario.

    Examples:
    - Restaurant Complaint
    - Murder Mystery
    - Job Interview
    - Airport Problem
    """

    title = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=160,
        unique=True,
    )

    summary = models.TextField(
        blank=True,
        help_text="Short description shown to the teacher.",
    )

    student_briefing = models.TextField(
        blank=True,
        help_text=(
            "Information every student should know before "
            "the role play begins."
        ),
    )

    teacher_notes = models.TextField(
        blank=True,
        help_text="Instructions visible only to the teacher.",
    )

    language_target = models.TextField(
        blank=True,
        help_text=(
            "Grammar, vocabulary, communicative function, "
            "or learning objective practiced in this situation."
        ),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def total_role_slots(self):
        return sum(
            role.copies_available
            for role in self.roles.filter(is_active=True)
        )


class RoleCard(models.Model):
    """
    One possible role inside a situation.
    """

    situation = models.ForeignKey(
        RolePlaySituation,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    name = models.CharField(
        max_length=120,
        help_text="Role name, e.g. Detective, Customer, Manager.",
    )

    character_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional character identity.",
    )

    public_description = models.TextField(
        blank=True,
        help_text=(
            "Information that is safe for the student "
            "to reveal during the activity."
        ),
    )

    private_briefing = models.TextField(
        blank=True,
        help_text="Information known only by this role.",
    )

    objective = models.TextField(
        blank=True,
        help_text="What this role is trying to accomplish.",
    )

    secret_information = models.TextField(
        blank=True,
        help_text=(
            "Optional secrets, evidence, motivations, "
            "or hidden constraints."
        ),
    )

    useful_language = models.TextField(
        blank=True,
        help_text=(
            "Optional vocabulary, sentence starters, "
            "or language support."
        ),
    )

    copies_available = models.PositiveIntegerField(
        default=1,
        help_text=(
            "How many students may receive this role "
            "during the same session."
        ),
    )

    sort_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        if self.character_name:
            return f"{self.name} — {self.character_name}"

        return self.name


class RolePlayRecordTemplate(models.Model):
    """
    A report, register, worksheet, log, etc. that students
    may complete during the role play.
    """

    situation = models.ForeignKey(
        RolePlaySituation,
        on_delete=models.CASCADE,
        related_name="record_templates",
    )

    title = models.CharField(max_length=150)

    instructions = models.TextField(blank=True)

    applies_to_all_roles = models.BooleanField(
        default=False,
        help_text=(
            "If checked, every role receives this document."
        ),
    )

    roles = models.ManyToManyField(
        RoleCard,
        blank=True,
        related_name="record_templates",
        help_text=(
            "Leave empty when the document applies to all roles."
        ),
    )

    is_required = models.BooleanField(default=False)

    allow_multiple = models.BooleanField(
        default=False,
        help_text=(
            "Allows the student to create several entries, "
            "such as an interview log or transaction register."
        ),
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return f"{self.situation}: {self.title}"


class RolePlayRecordField(models.Model):

    class FieldType(models.TextChoices):
        SHORT_TEXT = "SHORT_TEXT", "Short text"
        LONG_TEXT = "LONG_TEXT", "Long text"
        NUMBER = "NUMBER", "Number"
        CHOICE = "CHOICE", "Choice"
        CHECKBOX = "CHECKBOX", "Checkbox"

    template = models.ForeignKey(
        RolePlayRecordTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    label = models.CharField(max_length=150)

    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.SHORT_TEXT,
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
    )

    placeholder = models.CharField(
        max_length=255,
        blank=True,
    )

    required = models.BooleanField(default=False)

    options = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Used for Choice fields. Example: '
            '["Yes", "No", "Unknown"]'
        ),
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label


class RolePlayRun(models.Model):
    """
    Role-play-specific information attached to the generic
    GameSession that already handles the QR/lobby.
    """

    class Status(models.TextChoices):
        SETUP = "SETUP", "Setup"
        ASSIGNED = "ASSIGNED", "Roles Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        FINISHED = "FINISHED", "Finished"

    game_session = models.OneToOneField(
        GameSession,
        on_delete=models.CASCADE,
        related_name="roleplay_run",
    )

    situation = models.ForeignKey(
        RolePlaySituation,
        on_delete=models.PROTECT,
        related_name="runs",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SETUP,
    )

    current_round = models.PositiveIntegerField(
        default=1,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.situation} / {self.game_session}"


class RoleAssignment(models.Model):
    """
    Connects one participant to their privately assigned role.
    """

    run = models.ForeignKey(
        RolePlayRun,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="roleplay_assignments",
    )

    role = models.ForeignKey(
        RoleCard,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    round_number = models.PositiveIntegerField(
        default=1,
    )

    # We will populate this when the role is assigned.
    # This prevents later edits to the template from changing
    # a role that is already being played.
    role_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    viewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "run",
                    "participant",
                    "round_number",
                ],
                name="unique_roleplay_assignment_per_participant_round",
            ),
        ]

    def __str__(self):
        return f"{self.participant} → {self.role}"


class RolePlayRecordSubmission(models.Model):
    """
    One completed or partially completed report/register.
    """

    assignment = models.ForeignKey(
        RoleAssignment,
        on_delete=models.CASCADE,
        related_name="record_submissions",
    )

    template = models.ForeignKey(
        RolePlayRecordTemplate,
        on_delete=models.PROTECT,
        related_name="submissions",
    )

    sequence = models.PositiveIntegerField(default=1)

    is_submitted = models.BooleanField(default=False)
    teacher_feedback = models.TextField(
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "assignment",
                    "template",
                    "sequence",
                ],
                name="unique_roleplay_record_instance",
            ),
        ]

    def __str__(self):
        return f"{self.assignment} / {self.template}"


class RolePlayRecordResponse(models.Model):
    submission = models.ForeignKey(
        RolePlayRecordSubmission,
        on_delete=models.CASCADE,
        related_name="responses",
    )

    field = models.ForeignKey(
        RolePlayRecordField,
        on_delete=models.PROTECT,
        related_name="responses",
    )

    value = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "field"],
                name="unique_roleplay_field_response",
            ),
        ]

    def __str__(self):
        return f"{self.field}: {self.value[:40]}"