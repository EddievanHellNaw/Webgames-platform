from django.db import models
from sessions.models import GameSession, Participant


class AdventureGenre(models.TextChoices):
    SCI_FI = "SCI_FI", "Sci-Fi"
    CYBERPUNK = "CYBERPUNK", "Cyberpunk"
    BIO_HORROR = "BIO_HORROR", "Bio-Horror"

class AdventureStory(models.Model):
    class EnglishLevel(models.IntegerChoices):
        ENGLISH_1 = 1, "English 1"
        ENGLISH_2 = 2, "English 2"
        ENGLISH_3 = 3, "English 3"
        ENGLISH_4 = 4, "English 4"
        ENGLISH_5 = 5, "English 5"

    title = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=160,
        unique=True,
    )

    cover_image = models.ImageField(
        upload_to="choose_adventure/story_covers/",
        blank=True,
        null=True,
        help_text="Optional cover image shown in story selection and lobby.",
    )

    english_level = models.PositiveSmallIntegerField(
        choices=EnglishLevel.choices,
    )

    grammar_focus = models.CharField(
        max_length=200,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    introduction = models.TextField(
        blank=True,
        help_text="Introductory text shown before the adventure begins.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "english_level",
            "title",
        ]

    def __str__(self):
        return f"English {self.english_level} — {self.title}"

class AdventureRun(models.Model):
    session = models.OneToOneField(
        GameSession,
        on_delete=models.CASCADE,
        related_name="adventure_run",
    )

    story = models.ForeignKey(
        AdventureStory,
        on_delete=models.PROTECT,
        related_name="runs",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.story.title} — {self.session.join_code}"

class AdventureTeam(models.Model):
    adventure_run = models.ForeignKey(
        AdventureRun,
        on_delete=models.CASCADE,
        related_name="teams",
    )

    name = models.CharField(
        max_length=100,
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    selected_character = models.ForeignKey(
        "AdventureCharacter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teams",
    )

    character_selected_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adventure_character_selections",
    )

    character_selected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_station = models.ForeignKey(
        "StoryStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teams_currently_here",
    )

    containment_score = models.IntegerField(
        default=0,
    )

    humanity_score = models.IntegerField(
        default=0,
    )

    knowledge_score = models.IntegerField(
        default=0,
    )

    sci_fi_score = models.IntegerField(
        default=0,
    )

    cyberpunk_score = models.IntegerField(
        default=0,
    )

    bio_horror_score = models.IntegerField(
        default=0,
    )

    story_flags = models.JSONField(
        default=list,
        blank=True,
    )

    is_finished = models.BooleanField(
        default=False,
    )

    ending_station = models.ForeignKey(
        "StoryStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teams_finished_here",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "sort_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["adventure_run", "name"],
                name="unique_team_name_per_adventure_run",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.adventure_run.story.title}"


class AdventureTeamMembership(models.Model):
    team = models.ForeignKey(
        AdventureTeam,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="adventure_team_membership",
    )

    joined_team_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "team__sort_order",
            "participant__joined_at",
        ]

    def __str__(self):
        return f"{self.participant.display_name} → {self.team.name}"

    
class AdventureCharacter(models.Model):
    story = models.ForeignKey(
        AdventureStory,
        on_delete=models.CASCADE,
        related_name="characters",
    )

    name = models.CharField(
        max_length=100,
    )

    role = models.CharField(
        max_length=150,
        blank=True,
        help_text="Example: Engineer, Student, Security Officer.",
    )

    portrait_image = models.ImageField(
        upload_to="choose_adventure/character_portraits/",
        blank=True,
        null=True,
        help_text="Optional portrait shown during character selection and gameplay.",
    )

    description = models.TextField(
        blank=True,
    )

    perspective = models.TextField(
        blank=True,
        help_text=(
            "Information that should influence how this character "
            "approaches decisions."
        ),
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "sort_order",
            "name",
        ]

    def __str__(self):
        return f"{self.name} — {self.story.title}"


class StoryStation(models.Model):
    class StationType(models.TextChoices):
        STORY = "STORY", "Story Station"
        SYSTEM = "SYSTEM", "System Station"
        ENDING = "ENDING", "Ending"

    class AdvanceMode(models.TextChoices):
        CHOICE = "CHOICE", "Player Choice"
        AUTO = "AUTO", "Automatic"
        TERMINAL = "TERMINAL", "Terminal"

    story = models.ForeignKey(
        AdventureStory,
        on_delete=models.CASCADE,
        related_name="stations",
    )

    title = models.CharField(max_length=150)

    slug = models.SlugField(max_length=160)

    station_type = models.CharField(
        max_length=20,
        choices=StationType.choices,
        default=StationType.STORY,
    )

    scene_image = models.ImageField(
        upload_to="choose_adventure/station_scenes/",
        blank=True,
        null=True,
        help_text="Optional scene image shown when this station is active.",
    )

    advance_mode = models.CharField(
        max_length=20,
        choices=AdvanceMode.choices,
        default=AdvanceMode.CHOICE,
    )

    story_text = models.TextField()

    is_start = models.BooleanField(default=False)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["story", "slug"],
                name="unique_station_slug_per_story",
            ),
        ]

    def __str__(self):
        return f"{self.story.title} — {self.title}"

    @property
    def is_ending(self):
        return self.station_type == self.StationType.ENDING


class StoryChoice(models.Model):
    station = models.ForeignKey(
        StoryStation,
        on_delete=models.CASCADE,
        related_name="choices",
    )

    text = models.CharField(max_length=300)

    next_station = models.ForeignKey(
        StoryStation,
        on_delete=models.PROTECT,
        related_name="incoming_choices",
    )

    # Outcome scores
    containment_delta = models.SmallIntegerField(default=0)
    humanity_delta = models.SmallIntegerField(default=0)
    knowledge_delta = models.SmallIntegerField(default=0)

    # Genre weights
    sci_fi_delta = models.SmallIntegerField(default=0)
    cyberpunk_delta = models.SmallIntegerField(default=0)
    bio_horror_delta = models.SmallIntegerField(default=0)

    # Persistent story state
    set_flags = models.JSONField(
        default=list,
        blank=True,
    )

    required_flags = models.JSONField(
        default=list,
        blank=True,
    )

    forbidden_flags = models.JSONField(
        default=list,
        blank=True,
    )

    required_dominant_genre = models.CharField(
        max_length=20,
        choices=AdventureGenre.choices,
        blank=True,
    )

    min_containment = models.IntegerField(
        null=True,
        blank=True,
    )

    min_humanity = models.IntegerField(
        null=True,
        blank=True,
    )

    min_knowledge = models.IntegerField(
        null=True,
        blank=True,
    )

    sort_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.station.title} → {self.text}"

class AutomaticRoute(models.Model):
    station = models.ForeignKey(
        StoryStation,
        on_delete=models.CASCADE,
        related_name="automatic_routes",
    )

    target_station = models.ForeignKey(
        StoryStation,
        on_delete=models.PROTECT,
        related_name="incoming_automatic_routes",
    )

    label = models.CharField(
        max_length=150,
        blank=True,
    )

    priority = models.PositiveIntegerField(
        default=0,
    )

    dominant_genre = models.CharField(
        max_length=20,
        choices=AdventureGenre.choices,
        blank=True,
    )

    min_containment = models.IntegerField(
        null=True,
        blank=True,
    )

    max_containment = models.IntegerField(
        null=True,
        blank=True,
    )

    min_humanity = models.IntegerField(
        null=True,
        blank=True,
    )

    max_humanity = models.IntegerField(
        null=True,
        blank=True,
    )

    min_knowledge = models.IntegerField(
        null=True,
        blank=True,
    )

    max_knowledge = models.IntegerField(
        null=True,
        blank=True,
    )

    required_flags = models.JSONField(
        default=list,
        blank=True,
    )

    forbidden_flags = models.JSONField(
        default=list,
        blank=True,
    )

    class Meta:
        ordering = ["-priority", "id"]

    def __str__(self):
        return (
            f"{self.station.title} → "
            f"{self.target_station.title}"
        )

class TeamDecision(models.Model):
    team = models.ForeignKey(
        AdventureTeam,
        on_delete=models.CASCADE,
        related_name="decisions",
    )

    station = models.ForeignKey(
        StoryStation,
        on_delete=models.CASCADE,
        related_name="team_decisions",
    )

    selected_choice = models.ForeignKey(
        "StoryChoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_decisions",
    )

    selected_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adventure_team_decisions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["team", "station"],
                name="one_decision_per_team_station",
            ),
        ]

    def __str__(self):
        return f"{self.team.name} @ {self.station.title}"

class AdventureWrittenResponse(models.Model):
    team = models.ForeignKey(
        AdventureTeam,
        on_delete=models.CASCADE,
        related_name="written_responses",
    )

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="adventure_written_responses",
    )

    station = models.ForeignKey(
        StoryStation,
        on_delete=models.CASCADE,
        related_name="written_responses",
    )

    text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "team",
                    "participant",
                    "station",
                ],
                name=(
                    "one_written_response_"
                    "per_student_station"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.participant.display_name} "
            f"— {self.station.title}"
        )