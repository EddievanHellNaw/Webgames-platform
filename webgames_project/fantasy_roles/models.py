# Create your models here.
from django.db import models
from sessions.models import GameSession, Participant
from django.conf import settings
from django.core.exceptions import ValidationError

ROOM_ROLL_AP_COST = 1

def spend_character_ap(character, amount):
    if amount <= 0:
        return True

    if character.current_action_points < amount:
        return False

    character.current_action_points -= amount
    character.save(update_fields=["current_action_points", "updated_at"])

    return True

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

    icon_key = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text="PNG icon filename without extension. Example: assassin, bard, wizard.",
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
    class SkillScope(models.TextChoices):
        ROOM = "ROOM", "Room Skill"
        BOSS = "BOSS", "Boss Skill"

    class EffectCode(models.TextChoices):
        NONE = "NONE", "No Special Effect"

        # Room effects
        ROOM_REDUCE_DIFFICULTY = "ROOM_REDUCE_DIFFICULTY", "Reduce room difficulty"
        ROOM_ROLL_BONUS = "ROOM_ROLL_BONUS", "Add bonus to room roll"
        ROOM_REDUCE_FAILURE_DAMAGE = "ROOM_REDUCE_FAILURE_DAMAGE", "Reduce failure damage"
        ROOM_REROLL_AFTER_FAIL = "ROOM_REROLL_AFTER_FAIL", "Reroll after failed room roll"
        ROOM_RANDOM_ROLL_BONUS = "ROOM_RANDOM_ROLL_BONUS", "Random bonus before roll"
        ROOM_RECOVER_LIFE_ON_SUCCESS = "ROOM_RECOVER_LIFE_ON_SUCCESS", "Recover life on success"
        ROOM_FIELD_AID = "ROOM_FIELD_AID", "Reduce another player’s failure damage"

        # Boss effects — for later
        BOSS_DAMAGE_OVER_TIME = "BOSS_DAMAGE_OVER_TIME", "Boss damage over time"
        BOSS_DAMAGE_BUFF = "BOSS_DAMAGE_BUFF", "Boss damage buff"
        BOSS_SKIP_TURN = "BOSS_SKIP_TURN", "Boss skips turn"
        BOSS_PARTY_DAMAGE_BUFF = "BOSS_PARTY_DAMAGE_BUFF", "Party damage buff"
        BOSS_TAUNT = "BOSS_TAUNT", "Force boss to target user"
        BOSS_DOUBLE_ATTACK = "BOSS_DOUBLE_ATTACK", "Attack twice"
        BOSS_PARTY_SHIELD = "BOSS_PARTY_SHIELD", "Party shield"
        BOSS_FIXED_DAMAGE = "BOSS_FIXED_DAMAGE", "Fixed boss damage"
        BOSS_UNTARGETABLE = "BOSS_UNTARGETABLE", "User cannot be attacked"
        BOSS_RESTORE_AP = "BOSS_RESTORE_AP", "Restore AP"
        BOSS_HEAL = "BOSS_HEAL", "Restore life"
        BOSS_D6_DAMAGE = "BOSS_D6_DAMAGE", "Deal d6 damage"
        BOSS_D6_PLUS_DAMAGE = "BOSS_D6_PLUS_DAMAGE", "Deal d6 plus damage"
        BOSS_LIFESTEAL = "BOSS_LIFESTEAL", "Lifesteal effect"

    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="skills",
    )

    name = models.CharField(max_length=100)
    ap_cost = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)

    skill_scope = models.CharField(
        max_length=20,
        choices=SkillScope.choices,
        default=SkillScope.ROOM,
    )

    effect_code = models.CharField(
        max_length=60,
        choices=EffectCode.choices,
        default=EffectCode.NONE,
    )

    effect_value = models.SmallIntegerField(
        default=0,
        help_text="Main numeric value for the effect, such as +2, -1, or 5 healing.",
    )

    secondary_value = models.SmallIntegerField(
        default=0,
        help_text="Optional second value, such as d6 + 2 or damage reduction.",
    )

    duration_turns = models.PositiveSmallIntegerField(
        default=0,
        help_text="Used mostly for boss effects.",
    )

    roll_bonus = models.PositiveSmallIntegerField(
        default=0,
        help_text="Direct bonus added to a die roll, if applicable.",
    )

    can_use_in_combat = models.BooleanField(default=True)

    can_use_in_trap = models.BooleanField(
        default=False,
        help_text="Usually false. Trap rooms normally require written actions.",
    )

    can_use_in_treasure = models.BooleanField(default=False)

    can_use_in_special = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.character_class.name} · {self.name}"

class ClassWeakness(models.Model):
    class WeaknessScope(models.TextChoices):
        ROOM = "ROOM", "Room Weakness"
        BOSS = "BOSS", "Boss Weakness"

    class EffectCode(models.TextChoices):
        NONE = "NONE", "No Special Effect"

        # Room weaknesses
        ROOM_EXTRA_TRAP_FAIL_DAMAGE = "ROOM_EXTRA_TRAP_FAIL_DAMAGE", "Extra damage on failed Trap Room"
        ROOM_EXTRA_COMBAT_FAIL_DAMAGE = "ROOM_EXTRA_COMBAT_FAIL_DAMAGE", "Extra damage on failed Combat Room"
        ROOM_TRAP_ROLL_PENALTY = "ROOM_TRAP_ROLL_PENALTY", "Penalty on Trap Room rolls"
        ROOM_COMBAT_ROLL_PENALTY = "ROOM_COMBAT_ROLL_PENALTY", "Penalty on Combat Room rolls"
        ROOM_EXTRA_DAMAGE_AFTER_SKILL_FAIL = "ROOM_EXTRA_DAMAGE_AFTER_SKILL_FAIL", "Extra damage after failed skill roll"
        ROOM_NEXT_SKILL_COST_AFTER_FAIL = "ROOM_NEXT_SKILL_COST_AFTER_FAIL", "Next room skill costs more after fail"
        ROOM_LOSE_AP_ON_LOW_NATURAL_ROLL = "ROOM_LOSE_AP_ON_LOW_NATURAL_ROLL", "Lose AP on low natural roll"
        ROOM_SKILLS_COST_LIFE = "ROOM_SKILLS_COST_LIFE", "Room skills cost life instead of AP"

        # Boss weaknesses — for later
        BOSS_EXTRA_DAMAGE_TAKEN = "BOSS_EXTRA_DAMAGE_TAKEN", "Extra boss damage taken"
        BOSS_AFTER_SKILL_EXTRA_DAMAGE = "BOSS_AFTER_SKILL_EXTRA_DAMAGE", "Extra damage after using skill"
        BOSS_CANNOT_REPEAT_SKILL = "BOSS_CANNOT_REPEAT_SKILL", "Cannot repeat same skill"
        BOSS_FAILED_ROLL_BACKLASH = "BOSS_FAILED_ROLL_BACKLASH", "Failed roll backlash"
        BOSS_ATTACK_DIFFICULTY_UP = "BOSS_ATTACK_DIFFICULTY_UP", "Boss difficulty up for attacks"
        BOSS_CONSECUTIVE_SKILL_COST_UP = "BOSS_CONSECUTIVE_SKILL_COST_UP", "Consecutive skill cost up"
        BOSS_LOW_ROLL_SELF_DAMAGE = "BOSS_LOW_ROLL_SELF_DAMAGE", "Low roll self damage"
        BOSS_SKILLS_COST_LIFE = "BOSS_SKILLS_COST_LIFE", "Boss skills cost life instead of AP"

    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="weaknesses",
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    weakness_scope = models.CharField(
        max_length=20,
        choices=WeaknessScope.choices,
        default=WeaknessScope.ROOM,
    )

    effect_code = models.CharField(
        max_length=70,
        choices=EffectCode.choices,
        default=EffectCode.NONE,
    )

    effect_value = models.SmallIntegerField(
        default=0,
        help_text="Main numeric value for the weakness, such as +1 damage or -1 roll.",
    )

    secondary_value = models.SmallIntegerField(
        default=0,
        help_text="Optional second value.",
    )

    duration_turns = models.PositiveSmallIntegerField(
        default=0,
        help_text="Used mostly for boss weaknesses.",
    )

    def __str__(self):
        return f"{self.character_class.name} · {self.name}"


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
    
    room_skill_ap_penalty = models.PositiveSmallIntegerField(
        default=0,
        help_text="Temporary AP penalty applied to the next room skill.",
    )
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
    combat_room_count = models.PositiveSmallIntegerField(default=3)
    trap_room_count = models.PositiveSmallIntegerField(default=4)
    special_room_count = models.PositiveSmallIntegerField(
    default=1,
    help_text="Usually 1 special mimic room."
    )

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

    def recalculate_difficulty_rating(self, save=True):
        """
        Updates the dungeon difficulty based on the average difficulty
        of its designed dungeon rooms.

        Boss rooms are ignored because boss difficulty is controlled by BossTemplate.
        """
        from django.db.models import Avg

        average_difficulty = (
            DungeonRoom.objects
            .filter(dungeon=self)
            .exclude(room_type=DungeonRoom.RoomType.BOSS)
            .aggregate(avg_difficulty=Avg("difficulty"))
            .get("avg_difficulty")
        )

        if average_difficulty is None:
            return self.difficulty_rating

        calculated_rating = round(average_difficulty)
        calculated_rating = max(1, min(5, calculated_rating))

        self.difficulty_rating = calculated_rating

        if save:
            self.save(update_fields=["difficulty_rating"])

        return calculated_rating

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

    is_mimic_room = models.BooleanField(
        default=False,
        help_text="Mark this if this room begins as a special room but becomes a mimic encounter.",
    )

    mimic_image = models.ImageField(
        upload_to="dungeon_rooms/mimics/",
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

class DungeonRoomTemplate(models.Model):
    class RoomType(models.TextChoices):
        TRAP = "TRAP", "Trap Room"
        COMBAT = "COMBAT", "Combat Room"
        TREASURE = "TREASURE", "Treasure Room"
        SPECIAL = "SPECIAL", "Special Room"

    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="room_templates",
    )

    name = models.CharField(max_length=150)

    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
    )

    image = models.ImageField(
        upload_to="room_templates/",
        blank=True,
        null=True,
    )

    difficulty = models.PositiveSmallIntegerField(
        default=3,
        help_text="Use a value from 1 to 5.",
    )

    flavor_text = models.TextField(
        blank=True,
        help_text="Description or hint shown to players.",
    )

    failure_text = models.TextField(
        blank=True,
        help_text="What happens when players fail.",
    )

    damage_on_failure = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional explicit damage. Useful for combat rooms.",
    )

    is_mimic_room = models.BooleanField(
        default=False,
        help_text="Mark this if the special room is a mimic encounter.",
    )

    mimic_image = models.ImageField(
        upload_to="fantasy_roles/rooms/mimics/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["dungeon", "room_type", "difficulty", "name"]

    def __str__(self):
        return f"{self.dungeon.name} - {self.name}"
    
class ItemTemplate(models.Model):
    class ItemScope(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        DUNGEON_SPECIFIC = "DUNGEON_SPECIFIC", "Dungeon-specific"
    class EffectCode(models.TextChoices):
        NONE = "NONE", "No special effect"

        HEAL_PARTY = "HEAL_PARTY", "Restore Life to party"
        RESTORE_AP_PARTY = "RESTORE_AP_PARTY", "Restore AP to party"

        PERMANENT_ROLL_BONUS = "PERMANENT_ROLL_BONUS", "Permanent roll bonus"
        CLEAR_TRAP_ROOM = "CLEAR_TRAP_ROOM", "Automatically clear trap room"
        REVIVE_MEMBER = "REVIVE_MEMBER", "Revive a defeated party member"
        RUN_DAMAGE_REDUCTION = "RUN_DAMAGE_REDUCTION", "Reduce damage for the run"
    name = models.CharField(max_length=150)

    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="item_templates",
        null=True,
        blank=True,
        help_text="Leave blank if this item can appear in any dungeon.",
    )

    scope = models.CharField(
        max_length=30,
        choices=ItemScope.choices,
        default=ItemScope.GLOBAL,
    )

    image = models.ImageField(
        upload_to="items/",
        blank=True,
        null=True,
    )

    effect_text = models.TextField()

    effect_code = models.CharField(
        max_length=40,
        choices=EffectCode.choices,
        default=EffectCode.NONE,
    )

    effect_value = models.SmallIntegerField(
        default=0,
        help_text="Main value, such as +2 roll bonus, 10 healing, or 2 damage reduction.",
    )

    can_use_in_rooms = models.BooleanField(default=True)

    can_use_in_boss = models.BooleanField(default=True)

    roll_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional number needed to obtain this item from a chest.",
    )

    

    is_consumable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    
    class Meta:
        ordering = ["name"]

    def __str__(self):
        if self.dungeon:
            return f"{self.name} - {self.dungeon.name}"
        return self.name
    
class PartyInventoryItem(models.Model):
    party = models.ForeignKey(
        AdventuringParty,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )

    item = models.ForeignKey(
        ItemTemplate,
        on_delete=models.PROTECT,
        related_name="party_inventory_entries",
    )

    quantity = models.PositiveIntegerField(default=1)

    obtained_in_room = models.ForeignKey(
        "DungeonRunRoom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_obtained_here",
    )

    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["item__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["party", "item"],
                name="unique_item_per_party_inventory",
            )
        ]

    def __str__(self):
        return f"{self.party.name} - {self.item.name} x{self.quantity}"
    

class PartyDungeonRun(models.Model):
    class Status(models.TextChoices):
        SELECTED = "SELECTED", "Selected"
        ACTIVE = "ACTIVE", "Active"
        BOSS_READY = "BOSS_READY", "Boss Ready"
        BOSS_ACTIVE = "BOSS_ACTIVE", "Boss Active"
        CLEARED = "CLEARED", "Cleared"
        FAILED = "FAILED", "Failed"

    class FailureReason(models.TextChoices):
        NONE = "NONE", "No failure"
        PARTY_DEFEATED = "PARTY_DEFEATED", "The party was defeated"
        OUT_OF_AP = "OUT_OF_AP", "The party ran out of AP"

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
        "DungeonRunRoom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_party_runs",
    )

    current_turn_character = models.ForeignKey(
        "PlayerCharacter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_turn_runs",
    )

    turn_number = models.PositiveIntegerField(default=1)

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

    failure_reason = models.CharField(
        max_length=30,
        choices=FailureReason.choices,
        default=FailureReason.NONE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.party and self.party.session.game_template.code != "FANTASY_ROLES":
            raise ValidationError(
                "Dungeon runs can only be created for Fantasy Roles sessions."
            )

        if self.current_room and self.current_room.run_id != self.id:
            raise ValidationError(
                "Current room must belong to this dungeon run."
            )

    def __str__(self):
        return f"{self.party.name} in {self.dungeon.name}"
    
class ItemRunEffect(models.Model):
    run = models.ForeignKey(
        PartyDungeonRun,
        on_delete=models.CASCADE,
        related_name="item_effects",
    )

    item = models.ForeignKey(
        ItemTemplate,
        on_delete=models.CASCADE,
        related_name="run_effects",
    )

    effect_code = models.CharField(
        max_length=40,
        choices=ItemTemplate.EffectCode.choices,
    )

    value = models.SmallIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.run} · {self.item.name} · {self.effect_code}" 

class BossTemplate(models.Model):
    dungeon = models.OneToOneField(
        Dungeon,
        on_delete=models.CASCADE,
        related_name="boss_template",
    )

    normal_name = models.CharField(max_length=120)
    rage_name = models.CharField(max_length=120, blank=True)

    image = models.ImageField(
        upload_to="bosses/",
        blank=True,
        null=True,
    )

    rage_image = models.ImageField(
        upload_to="bosses/rage/",
        blank=True,
        null=True,
    )

    phase_one_life = models.PositiveIntegerField(default=30)
    phase_two_life = models.PositiveIntegerField(default=15)

    phase_one_difficulty = models.PositiveSmallIntegerField(default=3)
    phase_two_difficulty = models.PositiveSmallIntegerField(default=4)

    transformation_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Example: Goethia's Mask, Cool Down, Chain the Beast.",
    )

    intro_text = models.TextField(blank=True)
    transformation_text = models.TextField(blank=True)
    victory_text = models.TextField(blank=True)
    defeat_text = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.normal_name} · {self.dungeon.name}"

    @property
    def rage_display_name(self):
        return self.rage_name or self.normal_name    
    
class BossAbility(models.Model):
    class Phase(models.TextChoices):
        NORMAL = "NORMAL", "Normal Form"
        RAGE = "RAGE", "Rage Form"
        BOTH = "BOTH", "Both Forms"

    class Slot(models.TextChoices):
        FIRST = "FIRST", "First Ability"
        SECOND = "SECOND", "Second Ability"

    class EffectCode(models.TextChoices):
        NONE = "NONE", "No Special Effect"

        DAMAGE_LOWEST_LIFE = (
            "DAMAGE_LOWEST_LIFE",
            "Damage player with lowest life",
        )

        PARALYZE_HIGHEST_ATTACK = (
            "PARALYZE_HIGHEST_ATTACK",
            "Paralyze player with highest attack",
        )

        WEAKEN_HIGHEST_ATTACK = (
            "WEAKEN_HIGHEST_ATTACK",
            "Highest attack player deals limited damage",
        )

        DAMAGE_RANDOM_AND_SKIP = (
            "DAMAGE_RANDOM_AND_SKIP",
            "Damage random player and skip their action",
        )

        DAMAGE_PARTY_D6_PLUS = (
            "DAMAGE_PARTY_D6_PLUS",
            "Deal d6 plus value damage to party",
        )

        DAMAGE_RANDOM_AND_PARALYZE = (
            "DAMAGE_RANDOM_AND_PARALYZE",
            "Damage random player and paralyze",
        )

        PARTY_SKIP_AND_RANDOM_DAMAGE = (
            "PARTY_SKIP_AND_RANDOM_DAMAGE",
            "Party skips action and random player takes damage",
        )

        SELF_HEAL = (
            "SELF_HEAL",
            "Boss heals itself",
        )

        DAMAGE_RANDOM_CANNOT_ATTACK = (
            "DAMAGE_RANDOM_CANNOT_ATTACK",
            "Damage random player and prevent attacking",
        )

        PARTY_PARALYZE_AND_DAMAGE_TAKEN_UP = (
            "PARTY_PARALYZE_AND_DAMAGE_TAKEN_UP",
            "Paralyze party and increase next boss damage",
        )

        DAMAGE_RANDOM_AND_PARTY_CANNOT_ATTACK = (
            "DAMAGE_RANDOM_AND_PARTY_CANNOT_ATTACK",
            "Damage random player and party cannot attack",
        )

        DAMAGE_ALL_PLAYERS = (
            "DAMAGE_ALL_PLAYERS",
            "Damage all players",
        )

        DAMAGE_RANDOM_PLAYER = (
            "DAMAGE_RANDOM_PLAYER",
            "Damage random player",
        )

        DAMAGE_TRANSFORMER = (
            "DAMAGE_TRANSFORMER",
            "Damage player who triggered transformation",
        )

        BOSS_UNTARGETABLE_THEN_DAMAGE_HIGHEST_LIFE = (
            "BOSS_UNTARGETABLE_THEN_DAMAGE_HIGHEST_LIFE",
            "Boss cannot be attacked, then damages highest life player",
        )

    boss = models.ForeignKey(
        BossTemplate,
        on_delete=models.CASCADE,
        related_name="abilities",
    )

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.NORMAL,
    )

    slot = models.CharField(
        max_length=20,
        choices=Slot.choices,
    )

    effect_code = models.CharField(
        max_length=80,
        choices=EffectCode.choices,
        default=EffectCode.NONE,
    )

    effect_value = models.SmallIntegerField(
        default=0,
        help_text="Main value, such as damage, healing, or damage limit.",
    )

    secondary_value = models.SmallIntegerField(
        default=0,
        help_text="Optional second value, such as d6 bonus or failed roll penalty.",
    )

    duration_turns = models.PositiveSmallIntegerField(
        default=0,
        help_text="How long the effect lasts.",
    )

    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["boss", "phase", "slot", "order"]

    def __str__(self):
        return f"{self.boss.normal_name} · {self.get_phase_display()} · {self.name}"
    
class BossEncounter(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        WON = "WON", "Won"
        LOST = "LOST", "Lost"

    class Phase(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        RAGE = "RAGE", "Rage"

    class CurrentActor(models.TextChoices):
        BOSS = "BOSS", "Boss"
        PLAYER = "PLAYER", "Player"

    run = models.OneToOneField(
        PartyDungeonRun,
        on_delete=models.CASCADE,
        related_name="boss_encounter",
    )

    boss = models.ForeignKey(
        BossTemplate,
        on_delete=models.PROTECT,
        related_name="encounters",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.NORMAL,
    )

    current_life = models.PositiveIntegerField()

    current_actor = models.CharField(
        max_length=20,
        choices=CurrentActor.choices,
        default=CurrentActor.BOSS,
    )

    current_turn_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_boss_turns",
    )

    next_boss_ability_slot = models.CharField(
        max_length=20,
        choices=BossAbility.Slot.choices,
        default=BossAbility.Slot.FIRST,
    )

    round_number = models.PositiveIntegerField(default=1)

    player_phase_number = models.PositiveIntegerField(
        default=0,
        help_text="Increments after each boss action. Used to track which players acted.",
    )

    has_transformed = models.BooleanField(default=False)

    transformed_by_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_boss_transformations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.run.party.name} vs {self.boss.normal_name}"

    @property
    def current_boss_name(self):
        if self.phase == self.Phase.RAGE:
            return self.boss.rage_display_name
        return self.boss.normal_name

    @property
    def current_difficulty(self):
        if self.phase == self.Phase.RAGE:
            return self.boss.phase_two_difficulty
        return self.boss.phase_one_difficulty

    @property
    def max_life_for_current_phase(self):
        if self.phase == self.Phase.RAGE:
            return self.boss.phase_two_life
        return self.boss.phase_one_life
    
class BossCombatEffect(models.Model):
    class TargetType(models.TextChoices):
        PLAYER = "PLAYER", "Player"
        PARTY = "PARTY", "Party"
        BOSS = "BOSS", "Boss"

    class EffectCode(models.TextChoices):
        PLAYER_SKIP_TURN = "PLAYER_SKIP_TURN", "Player skips turn"
        PLAYER_CANNOT_ATTACK = "PLAYER_CANNOT_ATTACK", "Player cannot attack"
        PLAYER_DAMAGE_DEALT_OVERRIDE = "PLAYER_DAMAGE_DEALT_OVERRIDE", "Player damage is overridden"
        PLAYER_EXTRA_DAMAGE_ON_FAILED_THROW = "PLAYER_EXTRA_DAMAGE_ON_FAILED_THROW", "Extra damage on failed throw"

        PARTY_SKIP_TURN = "PARTY_SKIP_TURN", "Party skips turn"
        PARTY_CANNOT_ATTACK = "PARTY_CANNOT_ATTACK", "Party cannot attack"
        PARTY_EXTRA_BOSS_DAMAGE_TAKEN = "PARTY_EXTRA_BOSS_DAMAGE_TAKEN", "Party receives extra boss damage"
        PARTY_DAMAGE_REDUCTION = "PARTY_DAMAGE_REDUCTION", "Party damage reduction"

        BOSS_UNTARGETABLE = "BOSS_UNTARGETABLE", "Boss cannot be attacked"
        BOSS_PENDING_DAMAGE_HIGHEST_LIFE = "BOSS_PENDING_DAMAGE_HIGHEST_LIFE", "Boss will damage highest life player"

    encounter = models.ForeignKey(
        BossEncounter,
        on_delete=models.CASCADE,
        related_name="combat_effects",
    )

    source_ability = models.ForeignKey(
        BossAbility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_effects",
    )

    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
    )

    target_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="boss_combat_effects",
    )

    effect_code = models.CharField(
        max_length=80,
        choices=EffectCode.choices,
    )

    value = models.SmallIntegerField(default=0)
    secondary_value = models.SmallIntegerField(default=0)

    remaining_turns = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.target_character.character_name if self.target_character else self.get_target_type_display()
        return f"{target} · {self.get_effect_code_display()}"

class BossActionLog(models.Model):
    class ActorType(models.TextChoices):
        BOSS = "BOSS", "Boss"
        PLAYER = "PLAYER", "Player"
        SYSTEM = "SYSTEM", "System"

    class ActionType(models.TextChoices):
        BOSS_ABILITY = "BOSS_ABILITY", "Boss Ability"
        BASIC_ATTACK = "BASIC_ATTACK", "Basic Attack"
        BOSS_SKILL = "BOSS_SKILL", "Boss Skill"
        ITEM_USE = "ITEM_USE", "Use Item"
        PASS = "PASS", "Pass"
        TRANSFORMATION = "TRANSFORMATION", "Transformation"
        VICTORY = "VICTORY", "Victory"
        DEFEAT = "DEFEAT", "Defeat"

    encounter = models.ForeignKey(
        BossEncounter,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )

    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
    )

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
    )

    character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boss_action_logs",
    )

    boss_ability = models.ForeignKey(
        BossAbility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_logs",
    )

    player_skill = models.ForeignKey(
        ClassSkill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boss_action_logs",
    )

    player_item = models.ForeignKey(
        ItemTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boss_action_logs",
    )

    phase = models.CharField(
        max_length=20,
        choices=BossEncounter.Phase.choices,
        default=BossEncounter.Phase.NORMAL,
    )

    roll_sequence = models.JSONField(
        default=list,
        blank=True,
    )

    roll_breakdown = models.JSONField(
        default=list,
        blank=True,
    )

    difficulty_breakdown = models.JSONField(
        default=list,
        blank=True,
    )

    damage_breakdown = models.JSONField(
        default=list,
        blank=True,
    )
    round_number = models.PositiveIntegerField(default=1)
    player_phase_number = models.PositiveIntegerField(default=0)

    die_roll = models.PositiveSmallIntegerField(null=True, blank=True)
    final_roll_total = models.SmallIntegerField(null=True, blank=True)
    difficulty_at_roll = models.PositiveSmallIntegerField(null=True, blank=True)

    success = models.BooleanField(default=False)

    damage_to_boss = models.PositiveIntegerField(default=0)
    damage_to_players = models.PositiveIntegerField(default=0)
    healing_done = models.PositiveIntegerField(default=0)

    result_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.encounter} · {self.get_action_type_display()}"

class DungeonRunRoom(models.Model):
    class RoomType(models.TextChoices):
        TRAP = "TRAP", "Trap Room"
        COMBAT = "COMBAT", "Combat Room"
        TREASURE = "TREASURE", "Treasure Room"
        SPECIAL = "SPECIAL", "Special Room"
        BOSS = "BOSS", "Boss Room"

    run = models.ForeignKey(
        PartyDungeonRun,
        on_delete=models.CASCADE,
        related_name="generated_rooms",
    )

    source_room = models.ForeignKey(
        DungeonRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_run_rooms",
    )

    source_template = models.ForeignKey(
        DungeonRoomTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_run_rooms",
    )

    challenge_round = models.PositiveSmallIntegerField(default=1)
    
    room_number = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=150, blank=True)

    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
    )

    difficulty = models.PositiveSmallIntegerField(default=3)

    flavor_text = models.TextField(blank=True)
    failure_text = models.TextField(blank=True)

    damage_on_failure = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    @property
    def display_image(self):
        """
        Image used by templates.

        New source of truth:
        - DungeonRoom image for normal rooms.
        - DungeonRoom mimic_image after a mimic transforms.

        Legacy fallback:
        - DungeonRoomTemplate image / mimic_image.
        """
        if self.source_room:
            if (
                self.source_room.is_mimic_room
                and self.room_type == self.RoomType.COMBAT
                and self.source_room.mimic_image
            ):
                return self.source_room.mimic_image

            if self.source_room.image:
                return self.source_room.image

        if self.source_template:
            if (
                self.source_template.is_mimic_room
                and self.room_type == self.RoomType.COMBAT
                and self.source_template.mimic_image
            ):
                return self.source_template.mimic_image

            if self.source_template.image:
                return self.source_template.image

        return None
    is_cleared = models.BooleanField(default=False)

    grid_row = models.PositiveSmallIntegerField(default=1)
    grid_col = models.PositiveSmallIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["run", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "room_number"],
                name="unique_generated_room_number_per_run",
            )
        ]

    def __str__(self):
        return f"{self.run.party.name} - Room {self.room_number}"


class DungeonRunConnection(models.Model):
    run = models.ForeignKey(
        PartyDungeonRun,
        on_delete=models.CASCADE,
        related_name="generated_connections",
    )

    from_room = models.ForeignKey(
        DungeonRunRoom,
        on_delete=models.CASCADE,
        related_name="generated_connections_from",
    )

    to_room = models.ForeignKey(
        DungeonRunRoom,
        on_delete=models.CASCADE,
        related_name="generated_connections_to",
    )

    class Meta:
        ordering = ["run", "from_room__room_number", "to_room__room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_room", "to_room"],
                name="unique_generated_room_connection",
            )
        ]

    def clean(self):
        if self.from_room_id and self.to_room_id:
            if self.from_room_id == self.to_room_id:
                raise ValidationError("A room cannot connect to itself.")

            if self.from_room.run_id != self.to_room.run_id:
                raise ValidationError("Connected rooms must belong to the same run.")

            if self.run_id != self.from_room.run_id:
                raise ValidationError("Connection run must match the selected rooms.")

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
        return (
            f"{self.run.party.name}: Room {self.from_room.room_number} "
            f"↔ Room {self.to_room.room_number}"
        )
    
class RoomAttempt(models.Model):
    class ActionType(models.TextChoices):
        TRAP_ACTION = "TRAP_ACTION", "Trap Action"
        BASIC_ATTACK = "BASIC_ATTACK", "Basic Attack"
        SKILL = "SKILL", "Skill"
        OPEN_CHEST = "OPEN_CHEST", "Open Chest"
        LEAVE_TREASURE = "LEAVE_TREASURE", "Leave Treasure"
        SPECIAL_ACTION = "SPECIAL_ACTION", "Special Action"
        USE_ITEM = "USE_ITEM", "Use Item"

    room = models.ForeignKey(
        DungeonRunRoom,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.CASCADE,
        related_name="room_attempts",
    )

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
    )

    skill_used = models.ForeignKey(
        ClassSkill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_attempts",
    )

    challenge_round = models.PositiveSmallIntegerField(default=1)
    
    action_text = models.TextField(blank=True)

    die_roll = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    difficulty_at_roll = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    success = models.BooleanField(default=False)

    damage_taken = models.PositiveIntegerField(default=0)

    item_awarded = models.ForeignKey(
        ItemTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_attempts_awarded",
    )

    item_used = models.ForeignKey(
        ItemTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_attempts_used",
    )
    
    roll_bonus = models.SmallIntegerField(default=0) 
    
    roll_breakdown = models.JSONField(
        default=list,
        blank=True,
        help_text="Named roll modifiers for UI animation. Example: [{'label': 'Lucky Charm', 'value': 2}]",
    )

    difficulty_breakdown = models.JSONField(
        default=list,
        blank=True,
        help_text="Named difficulty changes for UI animation. Example: [{'label': 'Arcane Insight', 'value': -2, 'from': 5, 'to': 3}]",
    )

    damage_breakdown = models.JSONField(
        default=list,
        blank=True,
        help_text="Named damage reductions or increases for UI animation. Example: [{'label': 'Protection Ring', 'value': -2}]",
    )

    final_roll_total = models.PositiveSmallIntegerField(null=True, blank=True)
    
    result_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.character.character_name} - {self.room.name}"
    
class RoomSupportEffect(models.Model):
    room = models.ForeignKey(
        DungeonRunRoom,
        on_delete=models.CASCADE,
        related_name="support_effects",
    )
    source_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.CASCADE,
        related_name="room_support_effects_created",
    )
    target_character = models.ForeignKey(
        PlayerCharacter,
        on_delete=models.CASCADE,
        related_name="room_support_effects_received",
        blank=True,
        null=True,
    )
    skill = models.ForeignKey(
        ClassSkill,
        on_delete=models.CASCADE,
        related_name="room_support_effects",
    )
    effect_code = models.CharField(
        max_length=60,
        choices=ClassSkill.EffectCode.choices,
    )
    effect_value = models.SmallIntegerField(default=0)
    secondary_value = models.SmallIntegerField(default=0)
    uses_remaining = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.skill.name} on {self.room.name}"