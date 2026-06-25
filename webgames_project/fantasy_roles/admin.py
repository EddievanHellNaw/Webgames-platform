# Register your models here.
from django.contrib import admin
from .models import (
    CharacterClass,
    ClassSkill,
    ClassWeakness,
    PlayerCharacter,
    AdventuringParty,
    PartyMember,
    Dungeon,
    DungeonRoom,
    DungeonRoomConnection,
    DungeonVocabularySet,
    DungeonRoomTemplate,
    ItemTemplate,
    PartyInventoryItem,
    PartyDungeonRun,
    DungeonRunRoom,
    DungeonRunConnection,
    RoomAttempt,
)

class ClassSkillInline(admin.TabularInline):
    model = ClassSkill
    extra = 1
    fields = (
        "name",
        "skill_scope",
        "effect_code",
        "ap_cost",
        "effect_value",
        "secondary_value",
        "duration_turns",
        "roll_bonus",
        "can_use_in_combat",
        "can_use_in_trap",
        "can_use_in_treasure",
        "can_use_in_special",
        "description",
    )


class ClassWeaknessInline(admin.TabularInline):
    model = ClassWeakness
    extra = 1
    fields = (
        "name",
        "weakness_scope",
        "effect_code",
        "effect_value",
        "secondary_value",
        "duration_turns",
        "description",
    )

class PartyMemberInline(admin.TabularInline):
    model = PartyMember
    extra = 1

class DungeonVocabularySetInline(admin.StackedInline):
    model = DungeonVocabularySet
    extra = 1

class DungeonRunRoomInline(admin.TabularInline):
    model = DungeonRunRoom
    extra = 0
    readonly_fields = (
        "room_number",
        "name",
        "room_type",
        "difficulty",
        "is_cleared",
        "grid_row",
        "grid_col",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

class DungeonRoomTemplateInline(admin.TabularInline):
    model = DungeonRoomTemplate
    extra = 1
    fields = (
        "name",
        "room_type",
        "difficulty",
        "damage_on_failure",
        "is_mimic_room",
        "is_active",
    )

class DungeonRoomInline(admin.TabularInline):
    model = DungeonRoom
    extra = 0
    fields = (
        "number",
        "name",
        "room_type",
        "difficulty",
        "grid_row",
        "grid_col",
    )


class ItemTemplateInline(admin.TabularInline):
    model = ItemTemplate
    extra = 1
    fields = (
        "name",
        "scope",
        "roll_number",
        "is_consumable",
        "is_active",
    )


@admin.register(DungeonRunRoom)
class DungeonRunRoomAdmin(admin.ModelAdmin):
    list_display = (
        "run",
        "room_number",
        "name",
        "source_template",
        "room_type",
        "difficulty",
        "is_cleared",
        "grid_row",
        "grid_col",
    )
    list_filter = ("room_type", "difficulty", "is_cleared")
    search_fields = ("name", "run__party__name", "run__dungeon__name")


@admin.register(DungeonRunConnection)
class DungeonRunConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "run",
        "from_room",
        "to_room",
    )
    list_filter = ("run__dungeon",)

@admin.register(AdventuringParty)
class AdventuringPartyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "session",
        "member_count",
        "current_dm",
        "is_locked",
        "created_at",
    )
    list_filter = ("session", "is_locked")
    search_fields = ("name", "session__title")
    inlines = [PartyMemberInline]

@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "max_life",
        "action_points",
        "attack",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    fields = (
        "name",
        "slug",
        "description",
        "image",
        "female_image",
        "male_image",
        "max_life",
        "action_points",
        "attack",
        "is_active",
    )
    inlines = [ClassSkillInline, ClassWeaknessInline]


@admin.register(PlayerCharacter)
class PlayerCharacterAdmin(admin.ModelAdmin):
    list_display = (
        "character_name",
        "participant",
        "character_class",
        "visual_variant",
        "session",
        "english_level",
        "is_approved",
    )
    list_filter = (
        "character_class",
        "visual_variant",
        "english_level",
        "is_approved",
    )
    search_fields = (
        "character_name",
        "participant__display_name",
        "backstory",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(DungeonRoomTemplate)
class DungeonRoomTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "dungeon",
        "room_type",
        "difficulty",
        "damage_on_failure",
        "is_mimic_room",
        "is_active",
    )
    list_filter = ("dungeon", "room_type", "difficulty", "is_mimic_room", "is_active")
    search_fields = ("name", "flavor_text", "failure_text")


@admin.register(ItemTemplate)
class ItemTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "dungeon",
        "scope",
        "roll_number",
        "is_consumable",
        "is_active",
    )
    list_filter = ("scope", "dungeon", "is_consumable", "is_active")
    search_fields = ("name", "effect_text")


@admin.register(PartyInventoryItem)
class PartyInventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "party",
        "item",
        "quantity",
        "obtained_in_room",
        "obtained_at",
    )
    list_filter = ("party", "item")
    search_fields = ("party__name", "item__name")


@admin.register(Dungeon)
class DungeonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kingdom",
        "difficulty_rating",
        "room_count",
        "combat_room_count",
        "trap_room_count",
        "treasure_room_count",
        "special_room_count",
        "final_boss_name",
        "play_style",
        "is_active",
        "order",
    )
    list_filter = ("is_active", "kingdom", "play_style", "difficulty_rating")
    search_fields = ("name", "kingdom", "description", "final_boss_name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        DungeonRoomInline,
        DungeonVocabularySetInline,
        DungeonRoomTemplateInline,
        ItemTemplateInline,
    ]

@admin.register(DungeonRoom)
class DungeonRoomAdmin(admin.ModelAdmin):
    list_display = (
        "dungeon",
        "number",
        "name",
        "room_type",
        "difficulty",
        "damage_on_failure",
    )
    list_filter = ("dungeon", "room_type")
    search_fields = ("name", "flavor_text", "failure_text")


@admin.register(DungeonRoomConnection)
class DungeonRoomConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "dungeon",
        "from_room",
        "to_room",
    )
    list_filter = ("dungeon",)


@admin.register(PartyDungeonRun)
class PartyDungeonRunAdmin(admin.ModelAdmin):
    list_display = (
        "party",
        "dungeon",
        "current_room",
        "status",
        "selected_by_character",
        "created_at",
    )
    list_filter = ("dungeon", "status")
    search_fields = ("party__name", "dungeon__name")
    inlines = [DungeonRunRoomInline]

@admin.register(RoomAttempt)
class RoomAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "room",
        "character",
        "action_type",
        "skill_used",
        "die_roll",
        "roll_bonus",
        "final_roll_total",
        "difficulty_at_roll",
        "success",
        "damage_taken",
        "item_awarded",
        "created_at",
    )
    list_filter = (
        "action_type",
        "success",
        "room__room_type",
        "room__run__dungeon",
    )
    search_fields = (
        "character__character_name",
        "action_text",
        "result_text",
        "room__name",
        "skill_used__name",
    )