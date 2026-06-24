# Create your models here.
import uuid
from django.conf import settings
from django.db import models
from games.models import GameTemplate


class GameSession(models.Model):
    class Status(models.TextChoices):
        LOBBY = "LOBBY", "Lobby"
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_sessions",
    )
    game_template = models.ForeignKey(
        GameTemplate,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    title = models.CharField(max_length=150)
    join_code = models.SlugField(max_length=12, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LOBBY,
    )

    current_step = models.CharField(
        max_length=50,
        default="waiting",
        help_text="Used to route students to the correct game step.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class Participant(models.Model):
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    display_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    is_ready = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "student_id")

    def __str__(self):
        return self.display_name