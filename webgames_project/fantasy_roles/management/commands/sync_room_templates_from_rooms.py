from django.core.management.base import BaseCommand
from django.db import transaction

from fantasy_roles.models import (
    Dungeon,
    DungeonRoom,
    DungeonRoomTemplate,
)


def clamp_difficulty(value):
    if value is None:
        return 3

    return max(1, min(5, value))


class Command(BaseCommand):
    help = "Create or update DungeonRoomTemplate records from existing DungeonRoom records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dungeon-slug",
            type=str,
            default="",
            help="Optional dungeon slug. If omitted, all dungeons are synced.",
        )

        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing room templates for the selected dungeon(s) before recreating them.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be synced without changing the database.",
        )

    def handle(self, *args, **options):
        dungeon_slug = options["dungeon_slug"]
        replace = options["replace"]
        dry_run = options["dry_run"]

        dungeons = Dungeon.objects.all().order_by("order", "name")

        if dungeon_slug:
            dungeons = dungeons.filter(slug=dungeon_slug)

        if not dungeons.exists():
            self.stdout.write(
                self.style.WARNING("No matching dungeons found.")
            )
            return

        total_created = 0
        total_updated = 0
        total_skipped = 0

        with transaction.atomic():
            for dungeon in dungeons:
                self.stdout.write("")
                self.stdout.write(
                    self.style.MIGRATE_HEADING(f"Syncing {dungeon.name}")
                )

                source_rooms = (
                    DungeonRoom.objects
                    .filter(dungeon=dungeon)
                    .order_by("number")
                )

                if not source_rooms.exists():
                    self.stdout.write(
                        self.style.WARNING("  No DungeonRoom records found.")
                    )
                    continue

                if replace:
                    existing_count = DungeonRoomTemplate.objects.filter(
                        dungeon=dungeon,
                    ).count()

                    self.stdout.write(
                        f"  Existing templates to delete: {existing_count}"
                    )

                    if not dry_run:
                        DungeonRoomTemplate.objects.filter(
                            dungeon=dungeon,
                        ).delete()

                for room in source_rooms:
                    if room.room_type == DungeonRoom.RoomType.BOSS:
                        total_skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Skipped Room {room.number}: BOSS rooms are not templates."
                            )
                        )
                        continue

                    template_name = room.name or f"Room {room.number}"

                    defaults = {
                        "room_type": room.room_type,
                        "image": room.image,
                        "difficulty": clamp_difficulty(room.difficulty),
                        "flavor_text": room.flavor_text,
                        "failure_text": room.failure_text,
                        "damage_on_failure": room.damage_on_failure,
                        "is_mimic_room": room.room_type == DungeonRoom.RoomType.SPECIAL,
                        "is_active": True,
                    }

                    if dry_run:
                        self.stdout.write(
                            f"  Would sync Room {room.number}: {template_name}"
                        )
                        continue

                    if replace:
                        DungeonRoomTemplate.objects.create(
                            dungeon=dungeon,
                            name=template_name,
                            **defaults,
                        )
                        total_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Created template from Room {room.number}: {template_name}"
                            )
                        )
                    else:
                        template, created = DungeonRoomTemplate.objects.update_or_create(
                            dungeon=dungeon,
                            name=template_name,
                            defaults=defaults,
                        )

                        if created:
                            total_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  Created template from Room {room.number}: {template_name}"
                                )
                            )
                        else:
                            total_updated += 1
                            self.stdout.write(
                                f"  Updated template from Room {room.number}: {template_name}"
                            )

                if not dry_run:
                    dungeon.recalculate_difficulty_rating(save=True)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Recalculated difficulty: {dungeon.difficulty_rating}/5"
                        )
                    )

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {total_created}. Updated: {total_updated}. Skipped: {total_skipped}."
            )
        )