# Create your models here.
from django.db import models
from sessions.models import GameSession, Participant
from django.conf import settings
from django.core.exceptions import ValidationError

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
    
class AdventuringParty(models.Model):
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="fantasy_parties",
    )
    name = models.CharField(max_length=100)

    current_dm = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dm_for_parties",
    )

    is_locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "name"],
                name="unique_party_name_per_session",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.session.title}"

    @property
    def member_count(self):
        return self.members.count()


class PartyMember(models.Model):
    party = models.ForeignKey(
        AdventuringParty,
        on_delete=models.CASCADE,
        related_name="members",
    )
    character = models.OneToOneField(
        PlayerCharacter,
        on_delete=models.CASCADE,
        related_name="party_membership",
    )
    order = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "joined_at"]

    def save(self, *args, **kwargs):
        if self.character.session_id != self.party.session_id:
            raise ValueError("Character and party must belong to the same session.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.character.character_name} in {self.party.name}"
    

class Dungeon(models.Model):
    class PlayStyle(models.TextChoices):
        COMBAT_HEAVY = "COMBAT_HEAVY", "Combat-heavy"
        PUZZLE_HEAVY = "PUZZLE_HEAVY", "Puzzle-heavy"
        BALANCED = "BALANCED", "Balanced"
        TREASURE_HEAVY = "TREASURE_HEAVY", "Treasure-heavy"

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)

    kingdom = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: Mystopia, Marshlund, Pyroterra.",
    )

    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="dungeons/",
        blank=True,
        null=True,
        help_text="Dungeon cover image shown to students.",
    )

    difficulty_rating = models.PositiveSmallIntegerField(
        default=3,
        help_text="Use a value from 1 to 5.",
    )

    room_count = models.PositiveSmallIntegerField(default=9)

    treasure_room_count = models.PositiveSmallIntegerField(default=1)

    final_boss_name = models.CharField(
        max_length=150,
        blank=True,
    )

    play_style = models.CharField(
        max_length=30,
        choices=PlayStyle.choices,
        default=PlayStyle.BALANCED,
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        if self.kingdom:
            return f"{self.name} - {self.kingdom}"
        return self.name

class DungeonVocabularySet(models.Model):
    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="vocabulary_sets",
    )

    english_level = models.CharField(
        max_length=20,
        choices=PlayerCharacter.EnglishLevel.choices,
    )

    useful_vocabulary = models.TextField(
        blank=True,
        help_text="One word or phrase per line is recommended.",
    )

    sentence_frames = models.TextField(
        blank=True,
        help_text="Example sentence starters or useful structures.",
    )

    teacher_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["dungeon", "english_level"]
        constraints = [
            models.UniqueConstraint(
                fields=["dungeon", "english_level"],
                name="unique_vocabulary_set_per_dungeon_level",
            )
        ]

    def __str__(self):
        return f"{self.dungeon.name} - {self.get_english_level_display()}"

class DungeonRoom(models.Model):
    class RoomType(models.TextChoices):
        TRAP = "TRAP", "Trap Room"
        COMBAT = "COMBAT", "Combat Room"
        TREASURE = "TREASURE", "Treasure Room"
        BOSS = "BOSS", "Boss Room"
        SPECIAL = "SPECIAL", "Special Room"

    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="rooms",
    )

    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=150, blank=True)

    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.TRAP,
    )

    difficulty = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Difficulty value used for trap/combat checks.",
    )

    flavor_text = models.TextField(blank=True)
    failure_text = models.TextField(blank=True)

    damage_on_failure = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional explicit damage for combat rooms.",
    )

    image = models.ImageField(
        upload_to="dungeon_rooms/",
        blank=True,
        null=True,
    )

    grid_row = models.PositiveSmallIntegerField(default=1)
    grid_col = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["dungeon", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["dungeon", "number"],
                name="unique_room_number_per_dungeon",
            )
        ]

    def __str__(self):
        room_label = self.name or f"Room {self.number}"
        return f"{self.dungeon.name} - {room_label}"


class DungeonRoomConnection(models.Model):
    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="room_connections",
    )

    from_room = models.ForeignKey(
        DungeonRoom,
        on_delete=models.CASCADE,
        related_name="connections_from",
    )

    to_room = models.ForeignKey(
        DungeonRoom,
        on_delete=models.CASCADE,
        related_name="connections_to",
    )

    class Meta:
        ordering = ["dungeon", "from_room__number", "to_room__number"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_room", "to_room"],
                name="unique_dungeon_room_connection",
            )
        ]

    def clean(self):
        if self.from_room_id and self.to_room_id:
            if self.from_room_id == self.to_room_id:
                raise ValidationError("A room cannot connect to itself.")

            if self.from_room.dungeon_id != self.to_room.dungeon_id:
                raise ValidationError("Connected rooms must belong to the same dungeon.")

            if self.dungeon_id != self.from_room.dungeon_id:
                raise ValidationError("Connection dungeon must match the selected rooms.")

    def save(self, *args, **kwargs):
        if self.from_room_id and self.to_room_id:
            if self.from_room_id > self.to_room_id:
                self.from_room_id, self.to_room_id = self.to_room_id, self.from_room_id

        self.full_clean()
        super().save(*args, **kwargs)

    def other_room(self, current_room):
        if current_room.id == self.from_room_id:
            return self.to_room
        return self.from_room

    def __str__(self):
        return f"{self.dungeon.name}: Room {self.from_room.number} ↔ Room {self.to_room.number}"


class PartyDungeonRun(models.Model):
    class Status(models.TextChoices):
        SELECTED = "SELECTED", "Selected"
        ACTIVE = "ACTIVE", "Active"
        CLEARED = "CLEARED", "Cleared"
        FAILED = "FAILED", "Failed"

    party = models.OneToOneField(
        AdventuringParty,
        on_delete=models.CASCADE,
        related_name="dungeon_run",
    )

    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.PROTECT,
        related_name="party_runs",
    )

    current_room = models.ForeignKey(
        DungeonRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_party_runs",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SELECTED,
    )

    selected_by_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_dungeon_runs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.current_room and self.current_room.dungeon_id != self.dungeon_id:
            raise ValidationError("Current room must belong to the selected dungeon.")

        if self.party and self.party.session.game_template.code != "FANTASY_ROLES":
            raise ValidationError("Dungeon runs can only be created for Fantasy Roles sessions.")

    def save(self, *args, **kwargs):
        if not self.current_room_id:
            self.current_room = (
                DungeonRoom.objects
                .filter(dungeon=self.dungeon, number=1)
                .first()
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.party.name} in {self.dungeon.name}"