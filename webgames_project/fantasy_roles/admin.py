# Register your models here.
from django.contrib import admin
from .models import CharacterClass, ClassSkill, ClassWeakness, PlayerCharacter


class ClassSkillInline(admin.TabularInline):
    model = ClassSkill
    extra = 1


class ClassWeaknessInline(admin.TabularInline):
    model = ClassWeakness
    extra = 1


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