# Create your models here.
from django.db import models
from sessions.models import GameSession, Participant


class CharacterClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    # Optional fallback image, in case you already uploaded one
    image = models.ImageField(
        upload_to="character_classes/default/",
        blank=True,
        null=True,
    )

    female_image = models.ImageField(
        upload_to="character_classes/female/",
        blank=True,
        null=True,
    )

    male_image = models.ImageField(
        upload_to="character_classes/male/",
        blank=True,
        null=True,
    )

    max_life = models.PositiveIntegerField(default=10)
    action_points = models.PositiveIntegerField(default=3)
    attack = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    

class ClassSkill(models.Model):
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    name = models.CharField(max_length=100)
    ap_cost = models.PositiveIntegerField(default=1)
    description = models.TextField()

    class Meta:
        ordering = ["ap_cost", "name"]

    def __str__(self):
        return f"{self.character_class.name} - {self.name}"


class ClassWeakness(models.Model):
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="weaknesses",
    )
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.character_class.name} - {self.name}"


class PlayerCharacter(models.Model):
    class EnglishLevel(models.TextChoices):
        LEVEL_1 = "LEVEL_1", "Level 1 - Can / Can't"
        LEVEL_2 = "LEVEL_2", "Level 2 - Simple Past"
        LEVEL_3 = "LEVEL_3", "Level 3 - Modal Verbs"
        LEVEL_4 = "LEVEL_4", "Level 4 - Infinitives and Gerunds"
        LEVEL_5 = "LEVEL_5", "Level 5 - Present Perfect / Communication Strategies"

    class VisualVariant(models.TextChoices):
        FEMALE = "FEMALE", "Female"
        MALE = "MALE", "Male"

    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="fantasy_characters",
    )
    participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="fantasy_character",
    )
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.PROTECT,
        related_name="player_characters",
    )

    visual_variant = models.CharField(
        max_length=10,
        choices=VisualVariant.choices,
        default=VisualVariant.FEMALE,
    )

    character_name = models.CharField(max_length=100)

    english_level = models.CharField(
        max_length=20,
        choices=EnglishLevel.choices,
        default=EnglishLevel.LEVEL_2,
    )

    backstory = models.TextField()

    current_life = models.PositiveIntegerField(default=10)
    current_action_points = models.PositiveIntegerField(default=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    teacher_notes = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.current_life = self.character_class.max_life
            self.current_action_points = self.character_class.action_points

        super().save(*args, **kwargs)

    @property
    def selected_image(self):
        if self.visual_variant == self.VisualVariant.FEMALE:
            return self.character_class.female_image or self.character_class.image

        if self.visual_variant == self.VisualVariant.MALE:
            return self.character_class.male_image or self.character_class.image

        return self.character_class.image

    def __str__(self):
        return f"{self.character_name} ({self.character_class.name})"