from django.core.management.base import BaseCommand, CommandError

from fantasy_roles.models import (
    Dungeon,
    BossTemplate,
    BossAbility,
)


class Command(BaseCommand):
    help = "Seed boss templates and abilities for Fantasy Roles dungeons."

    def handle(self, *args, **options):
        bosses = [
            {
                "dungeon_names": [
                    "Mind's Prison",
                    "Minds Prison",
                    "Mind’s Prison",
                ],
                "boss": {
                    "normal_name": "Sven the Mindbreaker",
                    "rage_name": "Sven’s True Nature",
                    "phase_one_life": 35,
                    "phase_two_life": 18,
                    "phase_one_difficulty": 4,
                    "phase_two_difficulty": 4,
                    "transformation_name": "Mind’s True Nature",
                    "intro_text": (
                        "The air twists around the party as Sven the Mindbreaker "
                        "steps forward. Every doubt, fear, and hidden memory begins "
                        "to echo inside their minds."
                    ),
                    "transformation_text": (
                        "Sven’s illusion breaks. The Mindbreaker reveals his true "
                        "nature, and the dungeon itself seems to think, breathe, and hate."
                    ),
                    "victory_text": (
                        "With Sven defeated, Mystopia is freed from the prison of fear. "
                        "Dreams return to the realm, and the voices in the dark finally fall silent."
                    ),
                    "defeat_text": (
                        "Sven’s mind games consume the party. Mystopia remains trapped "
                        "inside an endless nightmare."
                    ),
                },
                "abilities": [
                    {
                        "name": "Mind Fracture",
                        "description": (
                            "Deals 3 damage to a random player. "
                            "That player can’t attack next turn."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_CANNOT_ATTACK,
                        "effect_value": 3,
                        "duration_turns": 1,
                        "order": 1,
                    },
                    {
                        "name": "Deepest Abyss",
                        "description": (
                            "Paralyzes the whole party. "
                            "The party receives +1 damage from Sven next turn."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.PARTY_PARALYZE_AND_DAMAGE_TAKEN_UP,
                        "effect_value": 1,
                        "duration_turns": 1,
                        "order": 2,
                    },
                    {
                        "name": "Mind Fracture",
                        "description": (
                            "Deals 3 damage to a random player. "
                            "The party can’t attack next turn."
                        ),
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_AND_PARTY_CANNOT_ATTACK,
                        "effect_value": 3,
                        "duration_turns": 1,
                        "order": 1,
                    },
                ],
            },
            {
                "dungeon_names": [
                    "Volcanic Manor",
                ],
                "boss": {
                    "normal_name": "Karragh, Old Iron King",
                    "rage_name": "Karragh, Obsidian Blade",
                    "phase_one_life": 35,
                    "phase_two_life": 18,
                    "phase_one_difficulty": 3,
                    "phase_two_difficulty": 3,
                    "transformation_name": "Cool Down",
                    "intro_text": (
                        "The heat becomes unbearable as Karragh, Old Iron King, rises "
                        "from molten stone. His armor glows like a forge, and every step "
                        "shakes the manor."
                    ),
                    "transformation_text": (
                        "The flames around Karragh cool into black glass. His molten fury "
                        "hardens into an obsidian blade."
                    ),
                    "victory_text": (
                        "The volcanic rage fades. Pyroterra’s people can finally rebuild "
                        "beneath a calmer sky."
                    ),
                    "defeat_text": (
                        "Karragh’s fire consumes the party. The manor burns brighter, and "
                        "Pyroterra falls deeper into ruin."
                    ),
                },
                "abilities": [
                    {
                        "name": "Lava Punch",
                        "description": (
                            "Deals 3 damage to a random player. "
                            "That player can’t do an action for 1 turn."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_AND_SKIP,
                        "effect_value": 3,
                        "duration_turns": 1,
                        "order": 1,
                    },
                    {
                        "name": "Eruption",
                        "description": "Deals d6 + 1 damage to the whole party.",
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.DAMAGE_PARTY_D6_PLUS,
                        "secondary_value": 1,
                        "order": 2,
                    },
                    {
                        "name": "Obsidian Blade",
                        "description": (
                            "Deals 5 damage to a random player. "
                            "That player can’t do an action for 1 turn."
                        ),
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_AND_SKIP,
                        "effect_value": 5,
                        "duration_turns": 1,
                        "order": 1,
                    },
                ],
            },
            {
                "dungeon_names": [
                    "Eternal Maze",
                ],
                "boss": {
                    "normal_name": "Gorrk",
                    "rage_name": "Gorrk, Nature’s Frailty",
                    "phase_one_life": 45,
                    "phase_two_life": 23,
                    "phase_one_difficulty": 3,
                    "phase_two_difficulty": 3,
                    "transformation_name": "Nature’s Frail",
                    "intro_text": (
                        "Roots split the stone floor as Gorrk emerges from the maze. "
                        "The forest itself seems to guard him."
                    ),
                    "transformation_text": (
                        "The ancient growth around Gorrk begins to wither. His body cracks, "
                        "but the dying forest fights with desperate strength."
                    ),
                    "victory_text": (
                        "The maze releases its prisoners. SylvanWood breathes again, and "
                        "the forest paths return to those who were lost."
                    ),
                    "defeat_text": (
                        "The maze closes around the heroes. Gorrk’s vines erase the path behind them."
                    ),
                },
                "abilities": [
                    {
                        "name": "Ensnaring Vine",
                        "description": (
                            "A random player can’t do an action for 1 turn. "
                            "That player receives 3 damage."
                        ),
                        "phase": BossAbility.Phase.BOTH,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_AND_PARALYZE,
                        "effect_value": 3,
                        "duration_turns": 1,
                        "order": 1,
                    },
                    {
                        "name": "Primal Shriek",
                        "description": (
                            "The party can’t do an action for 1 turn. "
                            "Deals 3 damage to a random player."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.PARTY_SKIP_AND_RANDOM_DAMAGE,
                        "effect_value": 3,
                        "duration_turns": 1,
                        "order": 2,
                    },
                    {
                        "name": "Frailty",
                        "description": "Gorrk, Nature’s Frailty gets 4 life back.",
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.SELF_HEAL,
                        "effect_value": 4,
                        "order": 2,
                    },
                ],
            },
            {
                "dungeon_names": [
                    "Corrupted Palace",
                ],
                "boss": {
                    "normal_name": "Goethia the Usurper",
                    "rage_name": "Goethia the Vengeful",
                    "phase_one_life": 30,
                    "phase_two_life": 15,
                    "phase_one_difficulty": 3,
                    "phase_two_difficulty": 4,
                    "transformation_name": "Goethia’s Mask",
                    "intro_text": (
                        "Goethia the Usurper waits upon a broken throne. Light bends "
                        "around her mask as spectral voices sing from the palace walls."
                    ),
                    "transformation_text": (
                        "Goethia’s mask cracks. The false queen vanishes, and Goethia "
                        "the Vengeful rises in her place."
                    ),
                    "victory_text": (
                        "The corrupted throne is broken. Dunesia is free from Goethia’s rule, "
                        "and the palace begins to remember its true name."
                    ),
                    "defeat_text": (
                        "Goethia’s song claims the party. The palace remains hers, and the realm kneels."
                    ),
                },
                "abilities": [
                    {
                        "name": "Light Beam",
                        "description": "Deals 3 damage to the player with the lowest life.",
                        "phase": BossAbility.Phase.BOTH,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_LOWEST_LIFE,
                        "effect_value": 3,
                        "order": 1,
                    },
                    {
                        "name": "Spectral Song",
                        "description": (
                            "The player with the highest attack is paralyzed for 2 turns."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.PARALYZE_HIGHEST_ATTACK,
                        "duration_turns": 2,
                        "order": 2,
                    },
                    {
                        "name": "Vengeful Queen",
                        "description": (
                            "The player with the highest attack can only deal 1 damage "
                            "for 3 turns. They receive 2 damage on failed throws."
                        ),
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.WEAKEN_HIGHEST_ATTACK,
                        "effect_value": 1,
                        "secondary_value": 2,
                        "duration_turns": 3,
                        "order": 2,
                    },
                ],
            },
            {
                "dungeon_names": [
                    "The Castle of the Madman",
                    "Castle of the Madman",
                ],
                "boss": {
                    "normal_name": "Morgoth the Calamity",
                    "rage_name": "Morgoth the Chained",
                    "phase_one_life": 40,
                    "phase_two_life": 20,
                    "phase_one_difficulty": 4,
                    "phase_two_difficulty": 4,
                    "transformation_name": "Chain the Beast",
                    "intro_text": (
                        "The castle trembles as Morgoth the Calamity tears through the darkness. "
                        "The beast is not guarding the castle. The castle was built to contain him."
                    ),
                    "transformation_text": (
                        "Ancient chains awaken and wrap around Morgoth. The Calamity is bound, "
                        "but even chained, the beast still burns."
                    ),
                    "victory_text": (
                        "Morgoth falls, and the castle’s curse breaks. Marshlund is no longer "
                        "haunted by the roar beneath its stones."
                    ),
                    "defeat_text": (
                        "The chains break. Morgoth’s calamity spreads beyond the castle walls."
                    ),
                },
                "abilities": [
                    {
                        "name": "Black Fire",
                        "description": "Deals 2 damage to the party.",
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_ALL_PLAYERS,
                        "effect_value": 2,
                        "order": 1,
                    },
                    {
                        "name": "Tail’s Whip",
                        "description": "Deals 5 damage to a random player.",
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_PLAYER,
                        "effect_value": 5,
                        "order": 2,
                    },
                    {
                        "name": "Black Fire",
                        "description": "Deals 2 damage to the player who chained the beast.",
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_TRANSFORMER,
                        "effect_value": 2,
                        "order": 1,
                    },
                ],
            },
            {
                "dungeon_names": [
                    "Dr. Kranken's Twisted Lab",
                    "Dr. Kranken’s Twisted Lab",
                    "Kranken's Twisted Lab",
                    "Kranken’s Twisted Lab",
                ],
                "boss": {
                    "normal_name": "Chimaera the Abomination",
                    "rage_name": "Kranken’s Monster",
                    "phase_one_life": 30,
                    "phase_two_life": 15,
                    "phase_one_difficulty": 3,
                    "phase_two_difficulty": 4,
                    "transformation_name": "Monster’s Evolution",
                    "intro_text": (
                        "Glass tanks shatter across the laboratory as Chimaera the Abomination "
                        "lurches into the light. Dr. Kranken’s experiment is alive."
                    ),
                    "transformation_text": (
                        "The monster convulses as lightning tears through its body. "
                        "Chimaera evolves into Kranken’s Monster."
                    ),
                    "victory_text": (
                        "The experiment is destroyed. Aquaheim is safe from Dr. Kranken’s creation, "
                        "and the twisted lab falls silent."
                    ),
                    "defeat_text": (
                        "The monster survives. Dr. Kranken’s work continues, and Aquaheim becomes "
                        "his testing ground."
                    ),
                },
                "abilities": [
                    {
                        "name": "Bestial Attack",
                        "description": "Deals 3 damage to a random player.",
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_RANDOM_PLAYER,
                        "effect_value": 3,
                        "order": 1,
                    },
                    {
                        "name": "Fly",
                        "description": (
                            "Can’t be attacked until next turn. Then it deals 4 damage "
                            "to the player with the most health."
                        ),
                        "phase": BossAbility.Phase.NORMAL,
                        "slot": BossAbility.Slot.SECOND,
                        "effect_code": BossAbility.EffectCode.BOSS_UNTARGETABLE_THEN_DAMAGE_HIGHEST_LIFE,
                        "effect_value": 4,
                        "duration_turns": 2,
                        "order": 2,
                    },
                    {
                        "name": "Electric Beast",
                        "description": "Deals 3 damage to all players.",
                        "phase": BossAbility.Phase.RAGE,
                        "slot": BossAbility.Slot.FIRST,
                        "effect_code": BossAbility.EffectCode.DAMAGE_ALL_PLAYERS,
                        "effect_value": 3,
                        "order": 1,
                    },
                ],
            },
        ]

        created_count = 0
        updated_count = 0
        ability_count = 0

        for boss_data in bosses:
            dungeon = self.get_dungeon(boss_data["dungeon_names"])

            boss_defaults = boss_data["boss"]

            boss_template, created = BossTemplate.objects.update_or_create(
                dungeon=dungeon,
                defaults=boss_defaults,
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created boss: {boss_template.normal_name}"
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated boss: {boss_template.normal_name}"
                    )
                )

            BossAbility.objects.filter(boss=boss_template).delete()

            for ability_data in boss_data["abilities"]:
                BossAbility.objects.create(
                    boss=boss_template,
                    **ability_data,
                )
                ability_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Boss seeding complete. Created: {created_count}, "
                f"Updated: {updated_count}, Abilities: {ability_count}"
            )
        )

    def get_dungeon(self, possible_names):
        for name in possible_names:
            dungeon = Dungeon.objects.filter(name__iexact=name).first()

            if dungeon:
                return dungeon

        raise CommandError(
            "Could not find dungeon with any of these names: "
            + ", ".join(possible_names)
        )