from django.contrib import admin

from .models import (
    AdventureCharacter,
    AdventureRun,
    AdventureStory,
    AdventureTeam,
    AdventureTeamMembership,
    AutomaticRoute,
    StoryChoice,
    StoryStation,
    TeamDecision,
)


@admin.register(AdventureStory)
class AdventureStoryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "english_level",
        "grammar_focus",
        "is_active",
    )

    list_filter = (
        "english_level",
        "is_active",
    )

    search_fields = (
        "title",
        "description",
        "grammar_focus",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

@admin.register(AdventureRun)
class AdventureRunAdmin(admin.ModelAdmin):
    list_display = (
        "story",
        "session",
        "teacher_name",
        "created_at",
    )

    list_filter = (
        "story",
        "created_at",
    )

    search_fields = (
        "story__title",
        "session__join_code",
        "session__teacher__username",
    )

    @admin.display(description="Teacher")
    def teacher_name(self, obj):
        return obj.session.teacher

@admin.register(AutomaticRoute)
class AutomaticRouteAdmin(admin.ModelAdmin):
    list_display = (
        "station",
        "target_station",
        "dominant_genre",
        "priority",
    )

    list_filter = (
        "station__story",
        "dominant_genre",
    )


@admin.register(AdventureCharacter)
class AdventureCharacterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "story",
        "role",
        "sort_order",
        "is_active",
    )

    list_filter = (
        "story",
        "is_active",
    )

    search_fields = (
        "name",
        "role",
        "description",
    )

@admin.register(AdventureTeam)
class AdventureTeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "adventure_run",
        "selected_character",
        "current_station",
        "sort_order",
    )

    list_filter = (
        "adventure_run__story",
    )


@admin.register(AdventureTeamMembership)
class AdventureTeamMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "team",
        "joined_team_at",
    )

    list_filter = (
        "team__adventure_run__story",
    )

@admin.register(StoryStation)
class StoryStationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "story",
        "station_type",
        "is_start",
        "sort_order",
    )

    list_filter = (
        "story",
        "station_type",
        "is_start",
    )

    search_fields = (
        "title",
        "story_text",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }


@admin.register(StoryChoice)
class StoryChoiceAdmin(admin.ModelAdmin):
    list_display = (
        "station",
        "text",
        "next_station",
        "sort_order",
        "is_active",
    )

    list_filter = (
        "station__story",
        "is_active",
    )

    search_fields = (
        "text",
        "station__title",
        "next_station__title",
    )

@admin.register(TeamDecision)
class TeamDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "station",
        "selected_choice",
        "selected_by",
        "created_at",
    )

    list_filter = (
        "team__adventure_run__story",
        "created_at",
    )