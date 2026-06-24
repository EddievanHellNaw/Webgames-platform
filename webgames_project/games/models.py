from django.db import models

# Create your models here.
class GameTemplate(models.Model):
    class GameCode(models.TextChoices):
        FANTASY_ROLES = "FANTASY_ROLES", "Fantasy Roles"
        CHOOSE_ADVENTURE = "CHOOSE_ADVENTURE", "Choose Your Own Adventure"
        TREASURE_HUNT = "TREASURE_HUNT", "Treasure Hunt"
        ROLE_PLAY = "ROLE_PLAY", "Role Play"

    code = models.CharField(
        max_length=50,
        choices=GameCode.choices,
        unique=True,
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title