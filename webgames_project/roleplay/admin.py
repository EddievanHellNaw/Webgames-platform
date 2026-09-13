from django.contrib import admin

from .models import (
    RoleAssignment,
    RoleCard,
    RolePlayRecordField,
    RolePlayRecordResponse,
    RolePlayRecordSubmission,
    RolePlayRecordTemplate,
    RolePlayRun,
    RolePlaySituation,
)


class RoleCardInline(admin.TabularInline):
    model = RoleCard
    extra = 0

    fields = (
        "name",
        "character_name",
        "copies_available",
        "sort_order",
        "is_active",
    )


@admin.register(RolePlaySituation)
class RolePlaySituationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "language_target",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = (
        "title",
        "summary",
        "language_target",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

    inlines = [RoleCardInline]


@admin.register(RoleCard)
class RoleCardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "character_name",
        "situation",
        "copies_available",
        "is_active",
    )

    list_filter = (
        "situation",
        "is_active",
    )

    search_fields = (
        "name",
        "character_name",
        "objective",
    )


class RecordFieldInline(admin.TabularInline):
    model = RolePlayRecordField
    extra = 0


@admin.register(RolePlayRecordTemplate)
class RolePlayRecordTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "situation",
        "applies_to_all_roles",
        "is_required",
        "allow_multiple",
    )

    list_filter = (
        "situation",
        "is_required",
        "allow_multiple",
    )

    filter_horizontal = ("roles",)

    inlines = [RecordFieldInline]


@admin.register(RolePlayRun)
class RolePlayRunAdmin(admin.ModelAdmin):
    list_display = (
        "game_session",
        "situation",
        "status",
        "started_at",
    )

    list_filter = (
        "status",
        "situation",
    )


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "role",
        "run",
        "assigned_at",
        "viewed_at",
    )

    list_filter = (
        "run",
        "role",
    )


@admin.register(RolePlayRecordSubmission)
class RolePlayRecordSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "template",
        "sequence",
        "is_submitted",
        "updated_at",
    )


@admin.register(RolePlayRecordResponse)
class RolePlayRecordResponseAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "field",
        "value",
    )

# Register your models here.
