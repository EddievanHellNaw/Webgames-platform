from django.core.management.base import BaseCommand

from fantasy_roles.models import Dungeon


class Command(BaseCommand):
    help = "Recalculate dungeon difficulty ratings from average room difficulty."

    def handle(self, *args, **options):
        dungeons = Dungeon.objects.filter(is_active=True).order_by("order", "name")

        if not dungeons.exists():
            self.stdout.write(self.style.WARNING("No active dungeons found."))
            return

        for dungeon in dungeons:
            old_rating = dungeon.difficulty_rating
            new_rating = dungeon.recalculate_difficulty_rating(save=True)

            self.stdout.write(
                self.style.SUCCESS(
                    f"{dungeon.name}: {old_rating} → {new_rating}"
                )
            )
            