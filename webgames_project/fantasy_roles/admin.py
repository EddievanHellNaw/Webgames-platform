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
    PartyDungeonRun,
)

class ClassSkillInline(admin.TabularInline):
    model = ClassSkill
    extra = 1


class ClassWeaknessInline(admin.TabularInline):
    model = ClassWeakness
    extra = 1

class PartyMemberInline(admin.TabularInline):
    model = PartyMember
    extra = 1

class DungeonVocabularySetInline(admin.StackedInline):
    model = DungeonVocabularySet
    extra = 1

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


@admin.register(Dungeon)
class DungeonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kingdom",
        "difficulty_rating",
        "room_count",
        "treasure_room_count",
        "final_boss_name",
        "play_style",
        "is_active",
        "order",
    )
    list_filter = ("is_active", "kingdom", "play_style", "difficulty_rating")
    search_fields = ("name", "kingdom", "description", "final_boss_name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [DungeonRoomInline, DungeonVocabularySetInline]


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