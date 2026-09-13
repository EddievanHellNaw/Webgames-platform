from django.contrib import admin

from .models import GameTemplate


@admin.register(GameTemplate)
class GameTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "is_active",
    )

    list_filter = (
        "is_active",
        "code",
    )

    search_fields = (
        "title",
        "description",
    )