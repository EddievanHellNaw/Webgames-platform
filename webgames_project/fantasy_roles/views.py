# Create your views here.
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render

from games.models import GameTemplate
from sessions.models import GameSession, Participant

from .forms import PlayerCharacterForm
from .services import generate_dungeon_run
from .models import (
    ROOM_ROLL_AP_COST,
    AdventuringParty,
    BossAbility,
    BossActionLog,
    BossCombatEffect,
    BossEncounter,
    BossTemplate,
    CharacterClass,
    ClassSkill,
    ClassWeakness,
    Dungeon,
    DungeonRunConnection,
    DungeonRunRoom,
    DungeonVocabularySet,
    ItemTemplate,
    PartyDungeonRun,
    PartyInventoryItem,
    PartyMember,
    PlayerCharacter,
    RoomAttempt,
)

# ============================================================
# Student identity / access helpers
# ============================================================
def get_student_participant(request, session):
    participant_id = request.session.get("participant_id")

    if not participant_id:
        return None

    return Participant.objects.filter(
        id=participant_id,
        session=session,
    ).first()

def get_student_character_and_membership(request, session):
    participant = get_student_participant(request, session)

    if participant is None:
        return None, None, None

    character = PlayerCharacter.objects.filter(
        session=session,
        participant=participant,
    ).first()

    if character is None:
        return participant, None, None

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related("party", "party__current_dm")
        .first()
    )

    return participant, character, membership

# ============================================================
# Shared party / character helpers
# ============================================================
def get_living_party_members(party):
    return list(
        PartyMember.objects
        .filter(
            party=party,
            character__current_life__gt=0,
        )
        .select_related(
            "character",
            "character__character_class",
        )
        .order_by("order", "joined_at")
    )

def apply_damage(character, damage):
    if damage <= 0:
        return

    character.current_life = max(0, character.current_life - damage)
    character.save(update_fields=["current_life", "updated_at"])

def party_is_defeated(party):
    return not PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
    ).exists()

def spend_character_ap(character, amount):
    if amount <= 0:
        return True

    if character.current_action_points < amount:
        return False

    character.current_action_points -= amount
    character.save(update_fields=["current_action_points", "updated_at"])

    return True

def spend_character_life(character, amount):
    if amount <= 0:
        return True

    # Prevent a character from killing themselves with a room skill.
    if character.current_life <= amount:
        return False

    character.current_life -= amount
    character.save(update_fields=["current_life", "updated_at"])

    return True

def lose_character_ap(character, amount):
    if amount <= 0:
        return

    character.current_action_points = max(
        0,
        character.current_action_points - amount,
    )
    character.save(update_fields=["current_action_points", "updated_at"])

def recover_character_life(character, amount):
    if amount <= 0:
        return

    character.current_life = min(
        character.character_class.max_life,
        character.current_life + amount,
    )
    character.save(update_fields=["current_life", "updated_at"])

def reset_party_ap(party):
    memberships = (
        PartyMember.objects
        .filter(party=party)
        .select_related("character", "character__character_class")
    )

    for membership in memberships:
        character = membership.character
        character.current_action_points = character.character_class.action_points
        character.save(update_fields=["current_action_points", "updated_at"])

# ============================================================
# Dungeon failure / status helpers
# ============================================================

def party_has_living_members(party):
    return PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
    ).exists()

def party_has_ap_remaining(party):
    return PartyMember.objects.filter(
        party=party,
        character__current_life__gt=0,
        character__current_action_points__gt=0,
    ).exists()

def fail_dungeon_run(run, failure_reason):
    run.status = PartyDungeonRun.Status.FAILED
    run.failure_reason = failure_reason
    run.current_turn_character = None
    run.save(
        update_fields=[
            "status",
            "failure_reason",
            "current_turn_character",
            "updated_at",
        ]
    )

def check_dungeon_failure_state(run):
    if run.status != PartyDungeonRun.Status.ACTIVE:
        return False

    if not party_has_living_members(run.party):
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.PARTY_DEFEATED,
        )
        return True

    if not party_has_ap_remaining(run.party):
        fail_dungeon_run(
            run,
            PartyDungeonRun.FailureReason.OUT_OF_AP,
        )
        return True

    return False

def update_run_status_after_room_result(run):
    if check_dungeon_failure_state(run):
        return
    if party_is_defeated(run.party):
        run.status = PartyDungeonRun.Status.FAILED
        run.save(update_fields=["status", "updated_at"])
        return

    uncleared_rooms_exist = run.generated_rooms.filter(
        is_cleared=False,
    ).exists()

    if not uncleared_rooms_exist:
        run.status = PartyDungeonRun.Status.BOSS_READY
        run.save(update_fields=["status", "updated_at"])

# ============================================================
# Room skill / weakness helpers
# ============================================================

def skill_can_be_used_in_room(skill, room):
    if skill.skill_scope != ClassSkill.SkillScope.ROOM:
        return False

    if room.room_type == DungeonRunRoom.RoomType.COMBAT:
        return skill.can_use_in_combat

    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        return skill.can_use_in_trap

    if room.room_type == DungeonRunRoom.RoomType.TREASURE:
        return skill.can_use_in_treasure

    if room.room_type == DungeonRunRoom.RoomType.SPECIAL:
        return False

    return False

def get_room_weaknesses(character):
    return list(
        character.character_class.weaknesses.filter(
            weakness_scope=ClassWeakness.WeaknessScope.ROOM,
        )
    )

def get_weakness_value(weaknesses, effect_code, default=0):
    for weakness in weaknesses:
        if weakness.effect_code == effect_code:
            return weakness.effect_value
    return default

def has_weakness(weaknesses, effect_code):
    return any(
        weakness.effect_code == effect_code
        for weakness in weaknesses
    )

def set_next_room_skill_penalty(character, amount):
    if amount <= 0:
        return

    character.room_skill_ap_penalty = max(
        character.room_skill_ap_penalty,
        amount,
    )
    character.save(update_fields=["room_skill_ap_penalty", "updated_at"])

def clear_next_room_skill_penalty(character):
    if character.room_skill_ap_penalty == 0:
        return

    character.room_skill_ap_penalty = 0
    character.save(update_fields=["room_skill_ap_penalty", "updated_at"])

def transform_special_room_into_mimic(room):
    if room.room_type != DungeonRunRoom.RoomType.SPECIAL:
        return

    original_name = room.name or "Suspicious Chest"

    if not original_name.lower().startswith("mimic"):
        room.name = f"Mimic Ambush — {original_name}"

    room.room_type = DungeonRunRoom.RoomType.COMBAT

    if not room.flavor_text:
        room.flavor_text = (
            "The chest twists open with teeth and claws. "
            "It was a Mimic waiting for the perfect moment to attack!"
        )

    room.save(
        update_fields=[
            "name",
            "room_type",
            "flavor_text",
        ]
    )

def award_random_item_to_party(party, dungeon, room):
    eligible_items = (
        ItemTemplate.objects
        .filter(is_active=True)
        .filter(
            models.Q(scope=ItemTemplate.ItemScope.GLOBAL)
            | models.Q(dungeon=dungeon)
        )
    )

    items = list(eligible_items)

    if not items:
        return None

    item = random.choice(items)

    inventory_item, created = PartyInventoryItem.objects.get_or_create(
        party=party,
        item=item,
        defaults={
            "quantity": 0,
            "obtained_in_room": room,
        },
    )

    inventory_item.quantity += 1

    if inventory_item.obtained_in_room is None:
        inventory_item.obtained_in_room = room

    inventory_item.save()

    return item

# ============================================================
# Trap / turn room group-check helpers
# ============================================================

def get_trap_progress(room):
    if room.room_type != DungeonRunRoom.RoomType.TRAP:
        return None

    living_members = get_living_party_members(room.run.party)
    living_character_ids = [
        member.character_id
        for member in living_members
    ]

    attempts = (
        RoomAttempt.objects
        .filter(
            room=room,
            challenge_round=room.challenge_round,
            character_id__in=living_character_ids,
        )
        .select_related("character")
    )

    attempted_character_ids = set(
        attempts.values_list("character_id", flat=True)
    )

    successful_character_ids = set(
        attempts.filter(success=True).values_list("character_id", flat=True)
    )

    living_count = len(living_character_ids)
    required_successes = max(1, (living_count + 1) // 2)

    return {
        "round": room.challenge_round,
        "living_count": living_count,
        "attempted_count": len(attempted_character_ids),
        "success_count": len(successful_character_ids),
        "required_successes": required_successes,
        "all_attempted": living_count > 0 and len(attempted_character_ids) >= living_count,
        "attempted_character_ids": attempted_character_ids,
        "successful_character_ids": successful_character_ids,
    }

def character_attempted_current_trap_round(room, character):
    if room.room_type != DungeonRunRoom.RoomType.TRAP:
        return False

    return RoomAttempt.objects.filter(
        room=room,
        character=character,
        challenge_round=room.challenge_round,
    ).exists()

def get_turn_eligible_members(run):
    living_members = get_living_party_members(run.party)

    if (
        run.current_room
        and run.current_room.room_type == DungeonRunRoom.RoomType.TRAP
        and not run.current_room.is_cleared
    ):
        eligible_members = [
            member
            for member in living_members
            if not character_attempted_current_trap_round(
                run.current_room,
                member.character,
            )
        ]

        if eligible_members:
            return eligible_members

    return living_members

def ensure_run_has_turn(run):
    if check_dungeon_failure_state(run):
        return None

    eligible_members = get_turn_eligible_members(run)

    if not eligible_members:
        return None

    eligible_character_ids = [
        member.character_id
        for member in eligible_members
    ]

    if run.current_turn_character_id in eligible_character_ids:
        return run.current_turn_character

    run.current_turn_character = eligible_members[0].character
    run.save(
        update_fields=[
            "current_turn_character",
            "updated_at",
        ]
    )

    return run.current_turn_character

def advance_room_turn(run):
    if check_dungeon_failure_state(run):
        return None

    eligible_members = get_turn_eligible_members(run)

    if not eligible_members:
        run.current_turn_character = None
        run.save(
            update_fields=[
                "current_turn_character",
                "updated_at",
            ]
        )
        return None

    eligible_characters = [
        member.character
        for member in eligible_members
    ]

    eligible_character_ids = [
        character.id
        for character in eligible_characters
    ]

    current_id = run.current_turn_character_id

    if current_id not in eligible_character_ids:
        next_character = eligible_characters[0]
    else:
        current_index = eligible_character_ids.index(current_id)
        next_index = (current_index + 1) % len(eligible_characters)
        next_character = eligible_characters[next_index]

    run.current_turn_character = next_character
    run.turn_number += 1
    run.save(
        update_fields=[
            "current_turn_character",
            "turn_number",
            "updated_at",
        ]
    )

    return next_character

# ============================================================
# Boss setup helpers
# ============================================================
def get_boss_template_for_run(run):
    if not run or not run.dungeon_id:
        return None

    try:
        return run.dungeon.boss_template
    except BossTemplate.DoesNotExist:
        return None

def get_boss_encounter_for_run(run):
    if not run:
        return None

    try:
        return run.boss_encounter
    except BossEncounter.DoesNotExist:
        return None

def get_boss_hp_percent(encounter):
    if not encounter:
        return 0

    max_life = encounter.max_life_for_current_phase or 1
    percent = round((encounter.current_life / max_life) * 100)

    return max(0, min(100, percent))

def refresh_party_for_boss(party):
    party_members = (
        PartyMember.objects
        .filter(party=party)
        .select_related("character", "character__character_class")
    )

    for member in party_members:
        character = member.character
        character.current_life = character.character_class.max_life
        character.current_action_points = character.character_class.action_points
        character.room_skill_ap_penalty = 0
        character.save(
            update_fields=[
                "current_life",
                "current_action_points",
                "room_skill_ap_penalty",
                "updated_at",
            ]
        )

def create_boss_encounter_for_run(run):
    boss_template = get_boss_template_for_run(run)

    if not boss_template:
        return None

    encounter, created = BossEncounter.objects.get_or_create(
        run=run,
        defaults={
            "boss": boss_template,
            "status": BossEncounter.Status.ACTIVE,
            "phase": BossEncounter.Phase.NORMAL,
            "current_life": boss_template.phase_one_life,
            "current_actor": BossEncounter.CurrentActor.BOSS,
            "current_turn_character": None,
            "next_boss_ability_slot": "FIRST",
            "round_number": 1,
            "player_phase_number": 0,
            "has_transformed": False,
        },
    )

    return encounter

# ============================================================
# Boss targeting / effect helpers
# ============================================================
def get_living_boss_characters(party):
    return [
        member.character
        for member in get_living_party_members(party)
    ]

def get_random_living_character(party):
    characters = get_living_boss_characters(party)

    if not characters:
        return None

    return random.choice(characters)

def get_lowest_life_character(party):
    characters = get_living_boss_characters(party)

    if not characters:
        return None

    lowest_life = min(character.current_life for character in characters)
    tied = [
        character
        for character in characters
        if character.current_life == lowest_life
    ]

    return random.choice(tied)

def get_highest_life_character(party):
    characters = get_living_boss_characters(party)

    if not characters:
        return None

    highest_life = max(character.current_life for character in characters)
    tied = [
        character
        for character in characters
        if character.current_life == highest_life
    ]

    return random.choice(tied)

def get_highest_attack_character(party):
    characters = get_living_boss_characters(party)

    if not characters:
        return None

    highest_attack = max(
        character.character_class.attack
        for character in characters
    )

    tied = [
        character
        for character in characters
        if character.character_class.attack == highest_attack
    ]

    return random.choice(tied)

def get_current_boss_ability(encounter):
    if not encounter:
        return None

    phase = (
        BossAbility.Phase.RAGE
        if encounter.phase == BossEncounter.Phase.RAGE
        else BossAbility.Phase.NORMAL
    )

    ability = (
        encounter.boss.abilities
        .filter(
            is_active=True,
            phase=phase,
            slot=encounter.next_boss_ability_slot,
        )
        .order_by("order")
        .first()
    )

    if ability:
        return ability

    ability = (
        encounter.boss.abilities
        .filter(
            is_active=True,
            phase=BossAbility.Phase.BOTH,
            slot=encounter.next_boss_ability_slot,
        )
        .order_by("order")
        .first()
    )

    return ability

def add_boss_effect(
    encounter,
    effect_code,
    target_type,
    source_ability=None,
    target_character=None,
    value=0,
    secondary_value=0,
    remaining_turns=1,
    note="",
):
    return BossCombatEffect.objects.create(
        encounter=encounter,
        source_ability=source_ability,
        target_type=target_type,
        target_character=target_character,
        effect_code=effect_code,
        value=value,
        secondary_value=secondary_value,
        remaining_turns=max(1, remaining_turns),
        note=note,
    )

def consume_boss_effect(effect):
    if effect.remaining_turns <= 1:
        effect.remaining_turns = 0
        effect.is_active = False
    else:
        effect.remaining_turns -= 1

    effect.save(
        update_fields=[
            "remaining_turns",
            "is_active",
        ]
    )

def get_active_boss_effects(encounter, **filters):
    return BossCombatEffect.objects.filter(
        encounter=encounter,
        is_active=True,
        **filters,
    )

def get_boss_damage_bonus(encounter):
    effects = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PARTY,
        effect_code=BossCombatEffect.EffectCode.PARTY_EXTRA_BOSS_DAMAGE_TAKEN,
    )

    return sum(effect.value for effect in effects)

def consume_boss_damage_bonus_effects(encounter, effect_ids):
    effects = BossCombatEffect.objects.filter(
        encounter=encounter,
        id__in=effect_ids,
        is_active=True,
    )

    for effect in effects:
        consume_boss_effect(effect)

def apply_boss_damage_to_character(encounter, character, base_damage):
    if not character or base_damage <= 0:
        return 0

    damage = base_damage + get_boss_damage_bonus(encounter)

    apply_damage(character, damage)

    return damage
# ============================================================
# Boss turn-cycle / combat / victory helpers
# ============================================================

DIRECT_BOSS_SKILL_EFFECTS = {
    ClassSkill.EffectCode.BOSS_FIXED_DAMAGE,
    ClassSkill.EffectCode.BOSS_D6_DAMAGE,
    ClassSkill.EffectCode.BOSS_D6_PLUS_DAMAGE,
    ClassSkill.EffectCode.BOSS_HEAL,
    ClassSkill.EffectCode.BOSS_RESTORE_AP,
    ClassSkill.EffectCode.BOSS_DOUBLE_ATTACK,
}

def skill_can_be_used_in_boss_step_one(skill):
    return (
        skill.skill_scope == ClassSkill.SkillScope.BOSS
        and skill.effect_code in DIRECT_BOSS_SKILL_EFFECTS
    )

def get_available_direct_boss_skills(character):
    if not character:
        return []

    return [
        skill
        for skill in character.character_class.skills
        .filter(skill_scope=ClassSkill.SkillScope.BOSS)
        .order_by("ap_cost", "name")
        if skill_can_be_used_in_boss_step_one(skill)
    ]

def boss_skills_cost_life(character):
    return character.character_class.weaknesses.filter(
        weakness_scope=ClassWeakness.WeaknessScope.BOSS,
        effect_code=ClassWeakness.EffectCode.BOSS_SKILLS_COST_LIFE,
    ).exists()

def apply_damage_to_boss(encounter, damage):
    if damage <= 0:
        return 0

    before_life = encounter.current_life

    encounter.current_life = max(
        0,
        encounter.current_life - damage,
    )
    encounter.save(update_fields=["current_life", "updated_at"])

    return before_life - encounter.current_life

def recover_character_ap(character, amount):
    if amount <= 0:
        return 0

    before_ap = character.current_action_points

    character.current_action_points = min(
        character.character_class.action_points,
        character.current_action_points + amount,
    )
    character.save(update_fields=["current_action_points", "updated_at"])

    return character.current_action_points - before_ap

def boss_party_is_defeated(encounter):
    return not PartyMember.objects.filter(
        party=encounter.run.party,
        character__current_life__gt=0,
    ).exists()

def mark_boss_encounter_lost(encounter):
    encounter.status = BossEncounter.Status.LOST
    encounter.current_actor = BossEncounter.CurrentActor.BOSS
    encounter.current_turn_character = None
    encounter.save(
        update_fields=[
            "status",
            "current_actor",
            "current_turn_character",
            "updated_at",
        ]
    )

    encounter.run.status = PartyDungeonRun.Status.FAILED
    encounter.run.failure_reason = PartyDungeonRun.FailureReason.PARTY_DEFEATED
    encounter.run.current_turn_character = None
    encounter.run.save(
        update_fields=[
            "status",
            "failure_reason",
            "current_turn_character",
            "updated_at",
        ]
    )

    BossActionLog.objects.create(
        encounter=encounter,
        actor_type=BossActionLog.ActorType.SYSTEM,
        action_type=BossActionLog.ActionType.DEFEAT,
        phase=encounter.phase,
        round_number=encounter.round_number,
        player_phase_number=encounter.player_phase_number,
        result_text=encounter.boss.defeat_text or "The party was defeated by the boss.",
    )

def check_boss_party_defeat_state(encounter):
    if encounter.status != BossEncounter.Status.ACTIVE:
        return True

    if boss_party_is_defeated(encounter):
        mark_boss_encounter_lost(encounter)
        return True

    return False

def check_boss_transformation_or_victory(encounter, triggering_character=None):
    encounter.refresh_from_db()

    if encounter.current_life > 0:
        return False

    if (
        encounter.phase == BossEncounter.Phase.NORMAL
        and not encounter.has_transformed
    ):
        encounter.phase = BossEncounter.Phase.RAGE
        encounter.current_life = encounter.boss.phase_two_life
        encounter.has_transformed = True
        encounter.transformed_by_character = triggering_character

        encounter.save(
            update_fields=[
                "phase",
                "current_life",
                "has_transformed",
                "transformed_by_character",
                "updated_at",
            ]
        )

        BossCombatEffect.objects.filter(
            encounter=encounter,
            target_type=BossCombatEffect.TargetType.BOSS,
            is_active=True,
        ).update(is_active=False)

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.SYSTEM,
            action_type=BossActionLog.ActionType.TRANSFORMATION,
            character=triggering_character,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            success=True,
            result_text=(
                encounter.boss.transformation_text
                or f"{encounter.boss.normal_name} transforms into {encounter.current_boss_name}!"
            ),
        )

        return False

    encounter.status = BossEncounter.Status.WON
    encounter.current_turn_character = None
    encounter.save(
        update_fields=[
            "status",
            "current_turn_character",
            "updated_at",
        ]
    )

    encounter.run.status = PartyDungeonRun.Status.CLEARED
    encounter.run.current_turn_character = None
    encounter.run.save(
        update_fields=[
            "status",
            "current_turn_character",
            "updated_at",
        ]
    )

    BossActionLog.objects.create(
        encounter=encounter,
        actor_type=BossActionLog.ActorType.SYSTEM,
        action_type=BossActionLog.ActionType.VICTORY,
        character=triggering_character,
        phase=encounter.phase,
        round_number=encounter.round_number,
        player_phase_number=encounter.player_phase_number,
        success=True,
        result_text=encounter.boss.victory_text or "The boss was defeated. The realm is saved!",
    )

    return True

def character_has_boss_skip_effect(encounter, character):
    return get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PLAYER,
        target_character=character,
        effect_code=BossCombatEffect.EffectCode.PLAYER_SKIP_TURN,
    ).first()

def party_has_boss_skip_effect(encounter):
    return get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PARTY,
        effect_code=BossCombatEffect.EffectCode.PARTY_SKIP_TURN,
    ).first()

def consume_party_cannot_attack_effects(encounter):
    effects = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PARTY,
        effect_code=BossCombatEffect.EffectCode.PARTY_CANNOT_ATTACK,
    )

    for effect in effects:
        consume_boss_effect(effect)

def consume_character_turn_effects(encounter, character):
    effects = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PLAYER,
        target_character=character,
        effect_code__in=[
            BossCombatEffect.EffectCode.PLAYER_CANNOT_ATTACK,
            BossCombatEffect.EffectCode.PLAYER_DAMAGE_DEALT_OVERRIDE,
            BossCombatEffect.EffectCode.PLAYER_EXTRA_DAMAGE_ON_FAILED_THROW,
        ],
    )

    for effect in effects:
        consume_boss_effect(effect)

def finish_boss_player_phase(encounter):
    consume_party_cannot_attack_effects(encounter)

    encounter.current_actor = BossEncounter.CurrentActor.BOSS
    encounter.current_turn_character = None
    encounter.save(
        update_fields=[
            "current_actor",
            "current_turn_character",
            "updated_at",
        ]
    )

    resolve_boss_turn(encounter)

def set_next_boss_player_turn_or_boss(encounter):
    encounter.refresh_from_db()

    if check_boss_party_defeat_state(encounter):
        return

    party_skip_effect = party_has_boss_skip_effect(encounter)

    if party_skip_effect:
        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.SYSTEM,
            action_type=BossActionLog.ActionType.PASS,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            success=True,
            result_text="The whole party loses this player phase.",
        )

        consume_boss_effect(party_skip_effect)
        finish_boss_player_phase(encounter)
        return

    living_members = get_living_party_members(encounter.run.party)

    acted_character_ids = set(
        BossActionLog.objects
        .filter(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.PLAYER,
            player_phase_number=encounter.player_phase_number,
        )
        .exclude(character=None)
        .values_list("character_id", flat=True)
    )

    for member in living_members:
        character = member.character

        if character.id in acted_character_ids:
            continue

        skip_effect = character_has_boss_skip_effect(encounter, character)

        if skip_effect:
            BossActionLog.objects.create(
                encounter=encounter,
                actor_type=BossActionLog.ActorType.PLAYER,
                action_type=BossActionLog.ActionType.PASS,
                character=character,
                phase=encounter.phase,
                round_number=encounter.round_number,
                player_phase_number=encounter.player_phase_number,
                success=True,
                result_text=f"{character.character_name} is unable to act this turn.",
            )

            consume_boss_effect(skip_effect)
            continue

        encounter.current_actor = BossEncounter.CurrentActor.PLAYER
        encounter.current_turn_character = character
        encounter.save(
            update_fields=[
                "current_actor",
                "current_turn_character",
                "updated_at",
            ]
        )
        return

    finish_boss_player_phase(encounter)

def can_character_basic_attack_boss(encounter, character):
    boss_untargetable = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.BOSS,
        effect_code=BossCombatEffect.EffectCode.BOSS_UNTARGETABLE,
    ).exists()

    if boss_untargetable:
        return False, "The boss cannot be attacked right now."

    party_cannot_attack = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PARTY,
        effect_code=BossCombatEffect.EffectCode.PARTY_CANNOT_ATTACK,
    ).exists()

    if party_cannot_attack:
        return False, "The party cannot attack this turn."

    player_cannot_attack = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PLAYER,
        target_character=character,
        effect_code=BossCombatEffect.EffectCode.PLAYER_CANNOT_ATTACK,
    ).exists()

    if player_cannot_attack:
        return False, "You cannot attack this turn."

    return True, ""

def get_character_basic_boss_damage(encounter, character):
    damage = character.character_class.attack

    override_effect = (
        get_active_boss_effects(
            encounter,
            target_type=BossCombatEffect.TargetType.PLAYER,
            target_character=character,
            effect_code=BossCombatEffect.EffectCode.PLAYER_DAMAGE_DEALT_OVERRIDE,
        )
        .order_by("value")
        .first()
    )

    if override_effect:
        damage = override_effect.value

    return max(0, damage)

def get_failed_boss_throw_damage(encounter, character):
    effects = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.PLAYER,
        target_character=character,
        effect_code=BossCombatEffect.EffectCode.PLAYER_EXTRA_DAMAGE_ON_FAILED_THROW,
    )

    return sum(effect.value for effect in effects)

def resolve_boss_pending_effects(encounter):
    result_parts = []
    total_damage = 0

    pending_effects = get_active_boss_effects(
        encounter,
        target_type=BossCombatEffect.TargetType.BOSS,
        effect_code=BossCombatEffect.EffectCode.BOSS_PENDING_DAMAGE_HIGHEST_LIFE,
    )

    for effect in pending_effects:
        target = get_highest_life_character(encounter.run.party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                effect.value,
            )
            total_damage += damage

            result_parts.append(
                f"{encounter.current_boss_name}'s delayed attack hits "
                f"{target.character_name} for {damage} damage."
            )

        consume_boss_effect(effect)

    return {
        "result_text": " ".join(result_parts),
        "damage_to_players": total_damage,
    }

def apply_boss_ability_effect(encounter, ability):
    party = encounter.run.party
    code = ability.effect_code

    result_parts = []
    die_roll = None
    total_damage = 0
    healing_done = 0

    if code == BossAbility.EffectCode.DAMAGE_LOWEST_LIFE:
        target = get_lowest_life_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage
            result_parts.append(
                f"{ability.name} hits {target.character_name} for {damage} damage."
            )

    elif code == BossAbility.EffectCode.PARALYZE_HIGHEST_ATTACK:
        target = get_highest_attack_character(party)

        if target:
            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_SKIP_TURN,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )
            result_parts.append(
                f"{target.character_name} is paralyzed for {ability.duration_turns} turn(s)."
            )

    elif code == BossAbility.EffectCode.WEAKEN_HIGHEST_ATTACK:
        target = get_highest_attack_character(party)

        if target:
            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_DAMAGE_DEALT_OVERRIDE,
                value=ability.effect_value,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )

            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_EXTRA_DAMAGE_ON_FAILED_THROW,
                value=ability.secondary_value,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )

            result_parts.append(
                f"{target.character_name} is weakened. Their damage is limited to "
                f"{ability.effect_value} for {ability.duration_turns} turn(s)."
            )

    elif code == BossAbility.EffectCode.DAMAGE_RANDOM_AND_SKIP:
        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_SKIP_TURN,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )

            result_parts.append(
                f"{ability.name} hits {target.character_name} for {damage} damage. "
                f"{target.character_name} loses their next action."
            )

    elif code == BossAbility.EffectCode.DAMAGE_PARTY_D6_PLUS:
        die_roll = random.randint(1, 6)
        base_damage = die_roll + ability.secondary_value

        for character in get_living_boss_characters(party):
            damage = apply_boss_damage_to_character(
                encounter,
                character,
                base_damage,
            )
            total_damage += damage

        result_parts.append(
            f"{ability.name} erupts across the battlefield. "
            f"Roll: {die_roll}. The party takes {base_damage} base damage each."
        )

    elif code == BossAbility.EffectCode.DAMAGE_RANDOM_AND_PARALYZE:
        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_SKIP_TURN,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )

            result_parts.append(
                f"{target.character_name} is caught by {ability.name}, "
                f"takes {damage} damage, and loses their next action."
            )

    elif code == BossAbility.EffectCode.PARTY_SKIP_AND_RANDOM_DAMAGE:
        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.PARTY,
            effect_code=BossCombatEffect.EffectCode.PARTY_SKIP_TURN,
            remaining_turns=ability.duration_turns,
            note=ability.description,
        )

        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            result_parts.append(
                f"The party is stunned by {ability.name}. "
                f"{target.character_name} also takes {damage} damage."
            )

    elif code == BossAbility.EffectCode.SELF_HEAL:
        before_life = encounter.current_life
        max_life = encounter.max_life_for_current_phase

        encounter.current_life = min(
            max_life,
            encounter.current_life + ability.effect_value,
        )
        encounter.save(update_fields=["current_life", "updated_at"])

        healing_done = encounter.current_life - before_life

        result_parts.append(
            f"{encounter.current_boss_name} recovers {healing_done} life."
        )

    elif code == BossAbility.EffectCode.DAMAGE_RANDOM_CANNOT_ATTACK:
        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            add_boss_effect(
                encounter=encounter,
                source_ability=ability,
                target_type=BossCombatEffect.TargetType.PLAYER,
                target_character=target,
                effect_code=BossCombatEffect.EffectCode.PLAYER_CANNOT_ATTACK,
                remaining_turns=ability.duration_turns,
                note=ability.description,
            )

            result_parts.append(
                f"{ability.name} hits {target.character_name} for {damage} damage. "
                f"{target.character_name} cannot attack next turn."
            )

    elif code == BossAbility.EffectCode.PARTY_PARALYZE_AND_DAMAGE_TAKEN_UP:
        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.PARTY,
            effect_code=BossCombatEffect.EffectCode.PARTY_SKIP_TURN,
            remaining_turns=ability.duration_turns,
            note=ability.description,
        )

        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.PARTY,
            effect_code=BossCombatEffect.EffectCode.PARTY_EXTRA_BOSS_DAMAGE_TAKEN,
            value=ability.effect_value,
            remaining_turns=1,
            note=ability.description,
        )

        result_parts.append(
            f"{ability.name} paralyzes the party. "
            f"The next boss damage is increased by {ability.effect_value}."
        )

    elif code == BossAbility.EffectCode.DAMAGE_RANDOM_AND_PARTY_CANNOT_ATTACK:
        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.PARTY,
            effect_code=BossCombatEffect.EffectCode.PARTY_CANNOT_ATTACK,
            remaining_turns=ability.duration_turns,
            note=ability.description,
        )

        if target:
            result_parts.append(
                f"{ability.name} hits {target.character_name} for {damage} damage. "
                f"The party cannot attack next turn."
            )
        else:
            result_parts.append(
                f"{ability.name} prevents the party from attacking next turn."
            )

    elif code == BossAbility.EffectCode.DAMAGE_ALL_PLAYERS:
        for character in get_living_boss_characters(party):
            damage = apply_boss_damage_to_character(
                encounter,
                character,
                ability.effect_value,
            )
            total_damage += damage

        result_parts.append(
            f"{ability.name} hits the whole party for {ability.effect_value} base damage."
        )

    elif code == BossAbility.EffectCode.DAMAGE_RANDOM_PLAYER:
        target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            result_parts.append(
                f"{ability.name} hits {target.character_name} for {damage} damage."
            )

    elif code == BossAbility.EffectCode.DAMAGE_TRANSFORMER:
        target = encounter.transformed_by_character

        if not target or target.current_life <= 0:
            target = get_random_living_character(party)

        if target:
            damage = apply_boss_damage_to_character(
                encounter,
                target,
                ability.effect_value,
            )
            total_damage += damage

            result_parts.append(
                f"{ability.name} burns {target.character_name} for {damage} damage."
            )

    elif code == BossAbility.EffectCode.BOSS_UNTARGETABLE_THEN_DAMAGE_HIGHEST_LIFE:
        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.BOSS,
            effect_code=BossCombatEffect.EffectCode.BOSS_UNTARGETABLE,
            remaining_turns=1,
            note=ability.description,
        )

        add_boss_effect(
            encounter=encounter,
            source_ability=ability,
            target_type=BossCombatEffect.TargetType.BOSS,
            effect_code=BossCombatEffect.EffectCode.BOSS_PENDING_DAMAGE_HIGHEST_LIFE,
            value=ability.effect_value,
            remaining_turns=1,
            note=ability.description,
        )

        result_parts.append(
            f"{encounter.current_boss_name} flies out of reach. "
            f"It cannot be attacked until its next turn."
        )

    else:
        result_parts.append(
            f"{encounter.current_boss_name} uses {ability.name}, but nothing happens yet."
        )

    return {
        "result_text": " ".join(result_parts),
        "die_roll": die_roll,
        "damage_to_players": total_damage,
        "healing_done": healing_done,
    }

def resolve_boss_turn(encounter):
    """
    Automatically resolves the boss's turn.

    Flow:
    1. Resolve delayed boss effects.
    2. Use the current boss ability slot.
    3. Log the result.
    4. Advance to the player phase.
    """
    encounter.refresh_from_db()

    if encounter.status != BossEncounter.Status.ACTIVE:
        return

    if encounter.current_actor != BossEncounter.CurrentActor.BOSS:
        return

    pending_result = resolve_boss_pending_effects(encounter)

    ability = get_current_boss_ability(encounter)

    boss_damage_bonus_effect_ids = list(
        get_active_boss_effects(
            encounter,
            target_type=BossCombatEffect.TargetType.PARTY,
            effect_code=BossCombatEffect.EffectCode.PARTY_EXTRA_BOSS_DAMAGE_TAKEN,
        ).values_list("id", flat=True)
    )

    previous_slot = encounter.next_boss_ability_slot

    if ability:
        ability_result = apply_boss_ability_effect(encounter, ability)

        combined_result_text = " ".join(
            text
            for text in [
                pending_result.get("result_text", ""),
                ability_result.get("result_text", ""),
            ]
            if text
        )

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.BOSS,
            action_type=BossActionLog.ActionType.BOSS_ABILITY,
            boss_ability=ability,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            die_roll=ability_result.get("die_roll"),
            success=True,
            damage_to_players=(
                pending_result.get("damage_to_players", 0)
                + ability_result.get("damage_to_players", 0)
            ),
            healing_done=ability_result.get("healing_done", 0),
            result_text=combined_result_text,
        )

    else:
        combined_result_text = pending_result.get("result_text", "")

        if not combined_result_text:
            combined_result_text = (
                f"{encounter.current_boss_name} has no ability in this slot."
            )

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.BOSS,
            action_type=BossActionLog.ActionType.BOSS_ABILITY,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            success=True,
            damage_to_players=pending_result.get("damage_to_players", 0),
            result_text=combined_result_text,
        )

    consume_boss_damage_bonus_effects(
        encounter,
        boss_damage_bonus_effect_ids,
    )

    if check_boss_party_defeat_state(encounter):
        return

    if previous_slot == BossAbility.Slot.FIRST:
        encounter.next_boss_ability_slot = BossAbility.Slot.SECOND
    else:
        encounter.next_boss_ability_slot = BossAbility.Slot.FIRST
        encounter.round_number += 1

    encounter.player_phase_number += 1
    encounter.current_actor = BossEncounter.CurrentActor.PLAYER
    encounter.current_turn_character = None
    encounter.save(
        update_fields=[
            "next_boss_ability_slot",
            "round_number",
            "player_phase_number",
            "current_actor",
            "current_turn_character",
            "updated_at",
        ]
    )

    set_next_boss_player_turn_or_boss(encounter)

def resolve_direct_boss_skill(encounter, character, skill):
    code = skill.effect_code

    result_parts = [
        f"{character.character_name} used {skill.name}."
    ]

    die_roll = None
    final_roll_total = None
    difficulty = encounter.current_difficulty
    success = True
    damage_to_boss = 0
    healing_done = 0

    if code == ClassSkill.EffectCode.BOSS_FIXED_DAMAGE:
        damage = skill.effect_value
        damage_to_boss = apply_damage_to_boss(encounter, damage)

        result_parts.append(
            f"It deals {damage_to_boss} damage to {encounter.current_boss_name}."
        )

    elif code == ClassSkill.EffectCode.BOSS_D6_DAMAGE:
        die_roll = random.randint(1, 6)
        damage_to_boss = apply_damage_to_boss(encounter, die_roll)

        result_parts.append(
            f"The d6 rolled {die_roll}. It deals {damage_to_boss} damage."
        )

    elif code == ClassSkill.EffectCode.BOSS_D6_PLUS_DAMAGE:
        die_roll = random.randint(1, 6)
        bonus = skill.secondary_value or skill.effect_value
        damage = die_roll + bonus

        damage_to_boss = apply_damage_to_boss(encounter, damage)

        result_parts.append(
            f"The d6 rolled {die_roll} + {bonus}. "
            f"It deals {damage_to_boss} damage."
        )

    elif code == ClassSkill.EffectCode.BOSS_HEAL:
        before_life = character.current_life
        recover_character_life(character, skill.effect_value)
        character.refresh_from_db()

        healing_done = character.current_life - before_life

        result_parts.append(
            f"{character.character_name} recovers {healing_done} Life."
        )

    elif code == ClassSkill.EffectCode.BOSS_RESTORE_AP:
        restored_ap = recover_character_ap(character, skill.effect_value)

        result_parts.append(
            f"{character.character_name} recovers {restored_ap} AP."
        )

    elif code == ClassSkill.EffectCode.BOSS_DOUBLE_ATTACK:
        total_damage = 0
        roll_texts = []

        for attack_number in [1, 2]:
            roll = random.randint(1, 6)
            hit = roll >= difficulty

            roll_texts.append(str(roll))

            if hit:
                damage = character.character_class.attack
                total_damage += apply_damage_to_boss(encounter, damage)

        die_roll = None
        damage_to_boss = total_damage

        result_parts.append(
            f"Cleave rolls: {', '.join(roll_texts)}. "
            f"It deals {damage_to_boss} total damage."
        )

    else:
        success = False
        result_parts.append(
            "This boss skill is not implemented yet."
        )

    return {
        "result_text": " ".join(result_parts),
        "die_roll": die_roll,
        "final_roll_total": final_roll_total,
        "difficulty": difficulty,
        "success": success,
        "damage_to_boss": damage_to_boss,
        "healing_done": healing_done,
    }

# ============================================================
# Context builders
# ============================================================

def build_party_room_attempt_log(party, limit=8):
    return list(
        RoomAttempt.objects
        .filter(room__run__party=party)
        .select_related(
            "room",
            "character",
            "character__character_class",
            "skill_used",
            "item_awarded",
        )
        .order_by("-created_at")[:limit]
    )

def build_teacher_room_attempt_log(session, limit=24):
    return list(
        RoomAttempt.objects
        .filter(room__run__party__session=session)
        .select_related(
            "room",
            "room__run",
            "room__run__party",
            "character",
            "character__character_class",
            "skill_used",
            "item_awarded",
        )
        .order_by("-created_at")[:limit]
    )

def build_teacher_dungeon_cards(session):
    party_cards = []

    parties = (
        AdventuringParty.objects
        .filter(session=session)
        .select_related("current_dm")
        .order_by("created_at")
    )

    for party in parties:
        members = (
            PartyMember.objects
            .filter(party=party)
            .select_related(
                "character",
                "character__character_class",
            )
            .order_by("order", "joined_at")
        )

        run = (
            PartyDungeonRun.objects
            .filter(party=party)
            .select_related(
                "party",
                "dungeon",
                "current_room",
                "current_turn_character",
                "boss_encounter",
                "boss_encounter__boss",
                "boss_encounter__current_turn_character",
            )
            .first()
        )

        generated_rooms = []
        cleared_rooms_count = 0
        total_rooms_count = 0

        boss_template = None
        boss_encounter = None
        boss_hp_percent = 0

        if run:
            generated_rooms = list(
                run.generated_rooms
                .select_related("source_template")
                .order_by("room_number")
            )

            total_rooms_count = len(generated_rooms)
            cleared_rooms_count = sum(
                1 for room in generated_rooms if room.is_cleared
            )

            boss_template = get_boss_template_for_run(run)
            boss_encounter = get_boss_encounter_for_run(run)

            if boss_encounter:
                boss_hp_percent = get_boss_hp_percent(boss_encounter)

        party_cards.append(
            {
                "party": party,
                "members": members,
                "run": run,
                "generated_rooms": generated_rooms,
                "cleared_rooms_count": cleared_rooms_count,
                "total_rooms_count": total_rooms_count,
                "attempt_log": build_party_room_attempt_log(party),
                "boss_template": boss_template,
                "boss_encounter": boss_encounter,
                "boss_hp_percent": boss_hp_percent,
            }
        )

    return party_cards

def build_student_dungeon_context(request, session):
    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    run = None
    connected_rooms = []
    connected_room_ids = []
    generated_rooms = []
    recent_attempts = []
    latest_attempt = None
    party_inventory = []
    party_members = []
    is_current_dm = False
    available_skills = []
    current_turn_character = None
    is_current_turn = False
    trap_progress = None
    has_attempted_current_trap_round = False   
    boss_template = None
    boss_encounter = None
    boss_logs = []
    boss_hp_percent = 0 
    current_boss_ability = None
    is_boss_player_turn = False
    boss_can_basic_attack = False
    boss_attack_block_reason = ""
    available_boss_skills = []
    latest_boss_log = None

    if membership:
        is_current_dm = membership.party.current_dm_id == character.id

        run = (
            PartyDungeonRun.objects
            .filter(party=membership.party)
            .select_related(
                "dungeon",
                "current_room",
                "current_room__source_template",
                "party",
                "party__current_dm",
                "current_turn_character",
            )
            .first()
        )

        party_members = (
            PartyMember.objects
            .filter(party=membership.party)
            .select_related(
                "character",
                "character__character_class",
                "party",
            )
            .order_by("order", "joined_at")
        )  
        party_inventory = (
            PartyInventoryItem.objects
            .filter(party=membership.party)
            .select_related("item")
        )

        if run:
            generated_rooms = (
                run.generated_rooms
                .select_related("source_template")
                .all()
            )
            current_turn_character = run.current_turn_character
            is_current_turn = (
                current_turn_character is not None
                and character is not None
                and current_turn_character.id == character.id
            )

        if run and run.current_room:
            connections = (
                DungeonRunConnection.objects
                .filter(
                    models.Q(from_room=run.current_room)
                    | models.Q(to_room=run.current_room)
                )
                .select_related(
                    "from_room",
                    "to_room",
                    "from_room__source_template",
                    "to_room__source_template",
                )
            )

            connected_rooms = [
                connection.other_room(run.current_room)
                for connection in connections
            ]

            connected_room_ids = [room.id for room in connected_rooms]

            recent_attempts = []
            latest_attempt = None

            if run:
                recent_attempts = list(
                    RoomAttempt.objects
                    .filter(room__run=run)
                    .select_related(
                        "character",
                        "character__character_class",
                        "skill_used",
                        "item_awarded",
                        "room",
                    )
                    .order_by("-created_at")[:8]
                )

                if recent_attempts:
                    latest_attempt = recent_attempts[0]

            if run and run.current_room:
                room_skills = (
                    character.character_class.skills
                    .filter(skill_scope=ClassSkill.SkillScope.ROOM)
                    .order_by("ap_cost", "name")
                )

                available_skills = [
                    skill
                    for skill in room_skills
                    if skill_can_be_used_in_room(skill, run.current_room)
                ]
        if run and run.status == PartyDungeonRun.Status.ACTIVE:
            ensure_run_has_turn(run)
            run.refresh_from_db()

        if (run
            and run.current_room
            and run.current_room.room_type == DungeonRunRoom.RoomType.TRAP
            ):
            trap_progress = get_trap_progress(run.current_room)

            if character:
                has_attempted_current_trap_round = character_attempted_current_trap_round(
                    run.current_room,
                    character,
                )
        boss_template = get_boss_template_for_run(run)
        boss_encounter = get_boss_encounter_for_run(run)

        if boss_encounter:
            boss_hp_percent = get_boss_hp_percent(boss_encounter)
            boss_logs = list(
                boss_encounter.action_logs
                .select_related(
                    "character",
                    "boss_ability",
                    "player_skill",
                )
                .order_by("-created_at")[:12]
            )

            latest_boss_log = (
                boss_encounter.action_logs
                .filter(actor_type=BossActionLog.ActorType.BOSS)
                .select_related("boss_ability")
                .order_by("-created_at")
                .first()
            )
            current_boss_ability = get_current_boss_ability(boss_encounter)

            if (
                character
                and boss_encounter.current_actor == BossEncounter.CurrentActor.PLAYER
                and boss_encounter.current_turn_character_id == character.id
            ):
                is_boss_player_turn = True

                boss_can_basic_attack, boss_attack_block_reason = can_character_basic_attack_boss(
                    boss_encounter,
                    character,
                )
            if character:
                available_boss_skills = get_available_direct_boss_skills(character)

    return {
        "session": session,
        "participant": participant,
        "character": character,
        "membership": membership,
        "run": run,
        "connected_rooms": connected_rooms,
        "connected_room_ids": connected_room_ids,
        "generated_rooms": generated_rooms,
        "recent_attempts": recent_attempts,
        "latest_attempt": latest_attempt,
        "party_inventory": party_inventory,
        "party_members": party_members,
        "is_current_dm": is_current_dm,
        "available_skills": available_skills,
        "current_turn_character": current_turn_character,
        "is_current_turn": is_current_turn,
        "trap_progress": trap_progress,
        "has_attempted_current_trap_round": has_attempted_current_trap_round,
        "boss_template": boss_template,
        "boss_encounter": boss_encounter,
        "boss_logs": boss_logs,
        "boss_hp_percent": boss_hp_percent,
        "current_boss_ability": current_boss_ability,
        "is_boss_player_turn": is_boss_player_turn,
        "boss_can_basic_attack": boss_can_basic_attack,
        "boss_attack_block_reason": boss_attack_block_reason,
        "available_boss_skills": available_boss_skills,
        "latest_boss_log": latest_boss_log,
    }

# ============================================================
# Character views
# ============================================================

def character_create(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    existing_character = PlayerCharacter.objects.filter(
        session=session,
        participant=participant,
    ).first()

    if existing_character:
        return redirect(
            "fantasy_roles:character_detail",
            join_code=session.join_code,
        )

    character_classes = CharacterClass.objects.filter(is_active=True)

    if request.method == "POST":
        form = PlayerCharacterForm(
            request.POST,
            character_classes=character_classes,
        )

        if form.is_valid():
            player_character = form.save(commit=False)
            player_character.session = session
            player_character.participant = participant
            player_character.save()

            return redirect(
                "fantasy_roles:character_detail",
                join_code=session.join_code,
            )
    else:
        form = PlayerCharacterForm(character_classes=character_classes)

    return render(
        request,
        "fantasy_roles/character_create.html",
        {
            "session": session,
            "participant": participant,
            "form": form,
            "character_classes": character_classes,
        },
    )

def character_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    player_character = get_object_or_404(
        PlayerCharacter.objects.select_related(
            "character_class",
            "participant",
            "session",
        ),
        session=session,
        participant=participant,
    )

    skills = ClassSkill.objects.filter(
        character_class=player_character.character_class,
    ).order_by("ap_cost", "name")

    weaknesses = ClassWeakness.objects.filter(
        character_class=player_character.character_class,
    ).order_by("name")

    return render(
        request,
        "fantasy_roles/character_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": player_character,
            "skills": skills,
            "weaknesses": weaknesses,
        },
    )

# ============================================================
# Teacher views
# ============================================================
@login_required
def teacher_character_list(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        character_id = request.POST.get("character_id")

        character = get_object_or_404(
            PlayerCharacter,
            id=character_id,
            session=session,
        )

        if action == "approve_character":
            character.is_approved = True
            character.save(update_fields=["is_approved", "updated_at"])

            messages.success(
                request,
                f"{character.character_name} has been approved.",
            )

        elif action == "unapprove_character":
            character.is_approved = False
            character.save(update_fields=["is_approved", "updated_at"])

            messages.info(
                request,
                f"{character.character_name} has been marked for review.",
            )

        return redirect(
            "fantasy_roles:teacher_character_list",
            join_code=session.join_code,
        )

    characters = (
        PlayerCharacter.objects
        .filter(session=session)
        .select_related(
            "participant",
            "character_class",
        )
        .order_by("participant__joined_at", "character_name")
    )

    return render(
        request,
        "fantasy_roles/teacher_character_list.html",
        {
            "session": session,
            "characters": characters,
        },
    )

@login_required
def teacher_party_setup(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_party":
            party_name = request.POST.get("party_name", "").strip()

            if not party_name:
                party_count = AdventuringParty.objects.filter(session=session).count() + 1
                party_name = f"Party {party_count}"

            AdventuringParty.objects.get_or_create(
                session=session,
                name=party_name,
            )

        elif action == "add_member":
            party_id = request.POST.get("party_id")
            character_id = request.POST.get("character_id")

            party = get_object_or_404(
                AdventuringParty,
                id=party_id,
                session=session,
            )

            character = get_object_or_404(
                PlayerCharacter,
                id=character_id,
                session=session,
            )

            if PartyMember.objects.filter(character=character).exists():
                messages.warning(
                    request,
                    f"{character.character_name} is already assigned to a party.",
                )
            elif party.members.count() >= 4:
                messages.warning(
                    request,
                    f"{party.name} already has 4 members.",
                )
            else:
                PartyMember.objects.create(
                    party=party,
                    character=character,
                    order=party.members.count() + 1,
                )

        elif action == "remove_member":
            member_id = request.POST.get("member_id")

            member = get_object_or_404(
                PartyMember,
                id=member_id,
                party__session=session,
            )

            party = member.party

            if party.current_dm_id == member.character_id:
                party.current_dm = None
                party.save()

            member.delete()

        elif action == "set_dm":
            member_id = request.POST.get("member_id")

            member = get_object_or_404(
                PartyMember,
                id=member_id,
                party__session=session,
            )

            party = member.party
            party.current_dm = member.character
            party.save()

        elif action == "delete_party":
            party_id = request.POST.get("party_id")

            party = get_object_or_404(
                AdventuringParty,
                id=party_id,
                session=session,
            )

            party.delete()

        return redirect(
            "fantasy_roles:teacher_party_setup",
            join_code=session.join_code,
        )

    characters = (
        PlayerCharacter.objects
        .filter(session=session)
        .select_related(
            "participant",
            "character_class",
        )
        .order_by("participant__joined_at", "character_name")
    )

    unassigned_characters = characters.filter(
        party_membership__isnull=True,
    )

    parties = (
        AdventuringParty.objects
        .filter(session=session)
        .prefetch_related(
            "members__character__participant",
            "members__character__character_class",
        )
        .order_by("created_at", "name")
    )

    return render(
        request,
        "fantasy_roles/teacher_party_setup.html",
        {
            "session": session,
            "characters": characters,
            "unassigned_characters": unassigned_characters,
            "parties": parties,
        },
    )

@login_required
def teacher_dungeon_setup(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    party_cards = build_teacher_dungeon_cards(session)
    room_attempt_log = build_teacher_room_attempt_log(session)

    return render(
        request,
        "fantasy_roles/teacher_dungeon_setup.html",
        {
            "session": session,
            "party_cards": party_cards,
            "room_attempt_log": room_attempt_log,
        },
    )

@login_required
def teacher_dungeon_monitor_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    party_cards = build_teacher_dungeon_cards(session)
    room_attempt_log = build_teacher_room_attempt_log(session)

    return render(
        request,
        "fantasy_roles/partials/_teacher_dungeon_monitor_panel.html",
        {
            "session": session,
            "party_cards": party_cards,
            "room_attempt_log": room_attempt_log,
        },
    )
# ============================================================
# Student party / dungeon views
# ============================================================
def student_party_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    character = get_object_or_404(
        PlayerCharacter.objects.select_related(
            "character_class",
            "participant",
        ),
        session=session,
        participant=participant,
    )

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related(
            "party",
            "party__current_dm",
        )
        .first()
    )

    party_members = []
    is_current_dm = False
    existing_run = None

    if membership:
        party_members = (
            PartyMember.objects
            .filter(party=membership.party)
            .select_related(
                "character",
                "character__participant",
                "character__character_class",
            )
            .order_by("order", "joined_at")
        )

        is_current_dm = membership.party.current_dm_id == character.id

        existing_run = (
            PartyDungeonRun.objects
            .filter(party=membership.party)
            .select_related(
                "dungeon",
                "current_room",
            )
            .first()
        )

    return render(
        request,
        "fantasy_roles/student_party_detail.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
            "party_members": party_members,
            "is_current_dm": is_current_dm,
            "existing_run": existing_run,
        },
    )

def student_dungeon_detail(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/student_dungeon_detail.html",
        context,
    )

def student_dungeon_live_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/partials/_student_dungeon_live_shell.html",
        context,
    )

def student_inventory_panel(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    context = build_student_dungeon_context(request, session)

    if context["participant"] is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if context["character"] is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    return render(
        request,
        "fantasy_roles/partials/_inventory_contents.html",
        context,
    )

def student_dungeon_select(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant = get_student_participant(request, session)

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    character = get_object_or_404(
        PlayerCharacter,
        session=session,
        participant=participant,
    )

    membership = (
        PartyMember.objects
        .filter(character=character)
        .select_related("party", "party__current_dm")
        .first()
    )

    if membership is None:
        return redirect(
            "fantasy_roles:student_party_detail",
            join_code=session.join_code,
        )

    existing_run = (
        PartyDungeonRun.objects
        .filter(party=membership.party)
        .select_related("dungeon", "current_room", "selected_by_character")
        .first()
    )

    is_current_dm = membership.party.current_dm_id == character.id

    if request.method == "POST":
        if existing_run:
            messages.warning(
                request,
                "Your party has already chosen a dungeon.",
            )
            return redirect(
                "fantasy_roles:student_dungeon_detail",
                join_code=session.join_code,
            )

        if not is_current_dm:
            messages.warning(
                request,
                "Only the current DM can choose the dungeon for the party.",
            )
            return redirect(
                "fantasy_roles:student_dungeon_select",
                join_code=session.join_code,
            )

        dungeon_id = request.POST.get("dungeon_id")

        dungeon = get_object_or_404(
            Dungeon,
            id=dungeon_id,
            is_active=True,
        )

        run = PartyDungeonRun.objects.create(
            party=membership.party,
            dungeon=dungeon,
            selected_by_character=character,
            status=PartyDungeonRun.Status.SELECTED,
        )

        generate_dungeon_run(run)
        ensure_run_has_turn(run)

        messages.success(
            request,
            f"Your party chose {dungeon.name}.",
        )

        return redirect(
            "fantasy_roles:student_dungeon_detail",
            join_code=session.join_code,
        )

    dungeons = (
        Dungeon.objects
        .filter(is_active=True)
        .prefetch_related("vocabulary_sets")
    )

    vocabulary_by_dungeon = {}

    for dungeon in dungeons:
        vocabulary_by_dungeon[dungeon.id] = (
            dungeon.vocabulary_sets
            .filter(english_level=character.english_level)
            .first()
        )

    dungeons = Dungeon.objects.filter(is_active=True).order_by("order", "name")

    dungeon_cards = []

    for dungeon in dungeons:
        vocabulary_set = DungeonVocabularySet.objects.filter(
            dungeon=dungeon,
            english_level=character.english_level,
        ).first()

        dungeon_cards.append(
            {
                "dungeon": dungeon,
                "vocabulary_set": vocabulary_set,
            }
        )

    return render(
        request,
        "fantasy_roles/student_dungeon_select.html",
        {
            "session": session,
            "participant": participant,
            "character": character,
            "membership": membership,
            "existing_run": existing_run,
            "is_current_dm": is_current_dm,
            "dungeon_cards": dungeon_cards,
        },
    )

# ============================================================
# Room action views
# ============================================================
def submit_room_action(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    room = run.current_room

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "This dungeon is not currently active.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if room.is_cleared:
        messages.warning(request, "This room has already been cleared.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if character.current_life <= 0:
        messages.warning(request, "Your character cannot act because they have 0 life.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
    ensure_run_has_turn(run)

    if run.current_turn_character_id != character.id:
        if run.current_turn_character:
            messages.warning(
                request,
                f"It is {run.current_turn_character.character_name}'s turn.",
            )
        else:
            messages.warning(
                request,
                "There is no active turn right now.",
            )

        return redirect(
            "fantasy_roles:student_dungeon_detail",
            join_code=session.join_code,
        )
    if (
        room.room_type == DungeonRunRoom.RoomType.TRAP
        and character_attempted_current_trap_round(room, character)
    ):
        messages.warning(
            request,
            "You already attempted this trap round. Wait for the rest of your party.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
   
    action_text = request.POST.get("action_text", "").strip()
    submitted_action_type = request.POST.get("action_type", "").strip()

    skill = None
    room_weaknesses = get_room_weaknesses(character)

    ap_cost = ROOM_ROLL_AP_COST
    life_cost = 0

    roll_modifier = 0
    effective_difficulty = room.difficulty
    failure_damage_reduction = 0
    recover_life_on_success = 0
    reroll_after_fail = False
    random_bonus_roll = None
    random_bonus_applied = False

    action_type = submitted_action_type

    if submitted_action_type == RoomAttempt.ActionType.SKILL:
        skill_id = request.POST.get("skill_id")

        skill = get_object_or_404(
            ClassSkill,
            id=skill_id,
            character_class=character.character_class,
        )

        if not skill_can_be_used_in_room(skill, room):
            messages.warning(request, "This skill cannot be used in this room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        ap_cost = skill.ap_cost + character.room_skill_ap_penalty
        action_type = RoomAttempt.ActionType.SKILL

        if has_weakness(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_SKILLS_COST_LIFE,
        ):
            life_cost = ap_cost
            ap_cost = 0

        effect_code = skill.effect_code

        if effect_code == ClassSkill.EffectCode.ROOM_REDUCE_DIFFICULTY:
            effective_difficulty = max(
                0,
                room.difficulty - skill.effect_value,
            )

        elif effect_code == ClassSkill.EffectCode.ROOM_ROLL_BONUS:
            roll_modifier += skill.effect_value or skill.roll_bonus

        elif effect_code == ClassSkill.EffectCode.ROOM_REDUCE_FAILURE_DAMAGE:
            failure_damage_reduction += skill.effect_value

        elif effect_code == ClassSkill.EffectCode.ROOM_REROLL_AFTER_FAIL:
            reroll_after_fail = True

        elif effect_code == ClassSkill.EffectCode.ROOM_RANDOM_ROLL_BONUS:
            random_bonus_roll = random.randint(1, 6)

            if random_bonus_roll >= 4:
                roll_modifier += skill.effect_value
                random_bonus_applied = True

        elif effect_code == ClassSkill.EffectCode.ROOM_RECOVER_LIFE_ON_SUCCESS:
            effective_difficulty = max(
                0,
                room.difficulty - skill.effect_value,
            )
            recover_life_on_success = skill.secondary_value

        elif effect_code == ClassSkill.EffectCode.ROOM_FIELD_AID:
            failure_damage_reduction += skill.effect_value

    elif submitted_action_type == RoomAttempt.ActionType.LEAVE_TREASURE:
        ap_cost = 0
        action_type = RoomAttempt.ActionType.LEAVE_TREASURE

    # Room weakness roll penalties.
    if room.room_type == DungeonRunRoom.RoomType.TRAP:
        roll_modifier -= get_weakness_value(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_TRAP_ROLL_PENALTY,
        )

    if room.room_type == DungeonRunRoom.RoomType.COMBAT:
        roll_modifier -= get_weakness_value(
            room_weaknesses,
            ClassWeakness.EffectCode.ROOM_COMBAT_ROLL_PENALTY,
        )

    if not spend_character_ap(character, ap_cost):
        messages.warning(
            request,
            f"You need {ap_cost} AP to do that action.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if not spend_character_life(character, life_cost):
        messages.warning(
            request,
            f"You need more than {life_cost} Life to use that skill.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if skill:
        clear_next_room_skill_penalty(character)

    die_roll = None
    first_die_roll = None
    final_roll_total = None
    success = False
    damage_taken = 0
    item_awarded = None
    result_text_parts = []

    if skill:
        result_text_parts.append(
            f"{character.character_name} used {skill.name}."
        )

    if effective_difficulty != room.difficulty:
        result_text_parts.append(
            f"Room difficulty changed from {room.difficulty} to {effective_difficulty}."
        )

    if roll_modifier > 0:
        result_text_parts.append(
            f"Roll bonus: +{roll_modifier}."
        )

    if roll_modifier < 0:
        result_text_parts.append(
            f"Roll penalty: {roll_modifier}."
        )

    if failure_damage_reduction:
        result_text_parts.append(
            f"Failure damage will be reduced by {failure_damage_reduction}."
        )
    if random_bonus_roll is not None:
        if random_bonus_applied:
            result_text_parts.append(
                f"Quick Invention rolled {random_bonus_roll}, so +{skill.effect_value} was added."
            )
        else:
            result_text_parts.append(
                f"Quick Invention rolled {random_bonus_roll}, so no bonus was added."
            )

    # Treasure room: leaving safely does not require a roll.
    if (
        room.room_type in [
            DungeonRunRoom.RoomType.TREASURE,
            DungeonRunRoom.RoomType.SPECIAL,
        ]
        and action_type == RoomAttempt.ActionType.LEAVE_TREASURE
    ):
        success = True
        room.is_cleared = True
        room.save(update_fields=["is_cleared"])

        if room.room_type == DungeonRunRoom.RoomType.SPECIAL:
            result_text_parts.append(
                "The party decided not to touch the suspicious chest and moved on safely."
            )
        else:
            result_text_parts.append(
                "The party left the treasure room safely."
            )

    else:
        if (
            room.room_type == DungeonRunRoom.RoomType.TRAP
            and not action_text
            and action_type != RoomAttempt.ActionType.SKILL
            ):
        
            messages.warning(request, "Write an action before rolling for this room.")
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
        
        first_die_roll = random.randint(1, 6)
        die_roll = first_die_roll
        final_roll_total = die_roll + roll_modifier
        success = final_roll_total > effective_difficulty

        if not success and reroll_after_fail:
            second_die_roll = random.randint(1, 6)
            die_roll = second_die_roll
            final_roll_total = die_roll + roll_modifier
            success = final_roll_total > effective_difficulty

            result_text_parts.append(
                f"Shadow Step activated: first roll {first_die_roll}, reroll {second_die_roll}."
            )

        # Room-specific default action labels.
        if room.room_type == DungeonRunRoom.RoomType.TRAP and not skill:
            action_type = RoomAttempt.ActionType.TRAP_ACTION

        elif room.room_type == DungeonRunRoom.RoomType.COMBAT and not skill:
            action_type = RoomAttempt.ActionType.BASIC_ATTACK

        elif room.room_type == DungeonRunRoom.RoomType.SPECIAL and not skill:
            action_type = RoomAttempt.ActionType.SPECIAL_ACTION

        elif room.room_type == DungeonRunRoom.RoomType.TREASURE and not skill:
            action_type = RoomAttempt.ActionType.OPEN_CHEST

        if success:
            if room.room_type in [
                DungeonRunRoom.RoomType.TREASURE,
                DungeonRunRoom.RoomType.SPECIAL,
            ]:
                item_awarded = award_random_item_to_party(
                    membership.party,
                    run.dungeon,
                    room,
                )

            if room.room_type == DungeonRunRoom.RoomType.TRAP:
                result_text_parts.append(
                    f"{character.character_name} succeeded on the trap attempt."
                )

            if recover_life_on_success:
                recover_character_life(character, recover_life_on_success)
                result_text_parts.append(
                    f"{character.character_name} recovered {recover_life_on_success} Life."
                )

            room.is_cleared = True
            room.save(update_fields=["is_cleared"])

            if item_awarded:
                result_text_parts.append(
                    f"Success! You rolled {die_roll}"
                    f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                    f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                    f" = {final_roll_total} and found {item_awarded.name}."
                )
            else:
                result_text_parts.append(
                    f"Success! You rolled {die_roll}"
                    f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                    f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                    f" = {final_roll_total} and cleared the room."
                )

        else:
            if room.room_type == DungeonRunRoom.RoomType.TRAP:
                base_damage = room.difficulty
            else:
                base_damage = room.damage_on_failure or room.difficulty

            extra_damage = 0

            if room.room_type == DungeonRunRoom.RoomType.TRAP:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_TRAP_FAIL_DAMAGE,
                )

            if room.room_type == DungeonRunRoom.RoomType.COMBAT:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_COMBAT_FAIL_DAMAGE,
                )

            if skill:
                extra_damage += get_weakness_value(
                    room_weaknesses,
                    ClassWeakness.EffectCode.ROOM_EXTRA_DAMAGE_AFTER_SKILL_FAIL,
                )

            damage_taken = max(
                0,
                base_damage + extra_damage - failure_damage_reduction,
            )

            apply_damage(character, damage_taken)

            if (
                room.room_type == DungeonRunRoom.RoomType.SPECIAL
                and action_type == RoomAttempt.ActionType.OPEN_CHEST
            ):
                transform_special_room_into_mimic(room)

                result_text_parts.append(
                    "The chest was a Mimic! It transforms into a Combat Room."
                )

            next_skill_penalty = get_weakness_value(
                room_weaknesses,
                ClassWeakness.EffectCode.ROOM_NEXT_SKILL_COST_AFTER_FAIL,
            )

            if next_skill_penalty:
                set_next_room_skill_penalty(character, next_skill_penalty)
                result_text_parts.append(
                    f"Broken Focus: your next room skill costs +{next_skill_penalty} AP."
                )

            result_text_parts.append(
                f"Failure. You rolled {die_roll}"
                f"{' + ' + str(roll_modifier) if roll_modifier > 0 else ''}"
                f"{' - ' + str(abs(roll_modifier)) if roll_modifier < 0 else ''}"
                f" = {final_roll_total}. "
                f"{character.character_name} took {damage_taken} damage."
            )

        # Artificer weakness: natural room roll 1 or 2 loses AP.
        low_roll_threshold = 0

        for weakness in room_weaknesses:
            if weakness.effect_code == ClassWeakness.EffectCode.ROOM_LOSE_AP_ON_LOW_NATURAL_ROLL:
                low_roll_threshold = weakness.secondary_value
                ap_loss = weakness.effect_value

                if die_roll is not None and die_roll <= low_roll_threshold:
                    lose_character_ap(character, ap_loss)
                    result_text_parts.append(
                        f"Unstable Tools: natural roll {die_roll}, so {character.character_name} lost {ap_loss} AP."
                    )

    result_text = " ".join(result_text_parts)

    attempt = RoomAttempt.objects.create(
        room=room,
        character=character,
        action_type=action_type,
        skill_used=skill,
        action_text=action_text,
        die_roll=die_roll,
        roll_bonus=roll_modifier,
        final_roll_total=final_roll_total,
        difficulty_at_roll=effective_difficulty,
        success=success,
        damage_taken=damage_taken,
        item_awarded=item_awarded,
        result_text=result_text,
        challenge_round=room.challenge_round,
    )

    if room.room_type == DungeonRunRoom.RoomType.TRAP and not room.is_cleared:
        trap_progress = get_trap_progress(room)

        if trap_progress["all_attempted"]:
            if trap_progress["success_count"] >= trap_progress["required_successes"]:
                room.is_cleared = True
                room.save(update_fields=["is_cleared"])

                result_text = (
                    f"{result_text} "
                    f"Trap cleared! {trap_progress['success_count']} of "
                    f"{trap_progress['living_count']} heroes succeeded."
                )

                attempt.result_text = result_text
                attempt.save(update_fields=["result_text"])

            else:
                old_round = room.challenge_round
                room.challenge_round += 1
                room.save(update_fields=["challenge_round"])

                result_text = (
                    f"{result_text} "
                    f"The party did not get enough successes. "
                    f"Round {old_round} failed: {trap_progress['success_count']} of "
                    f"{trap_progress['living_count']} heroes succeeded. "
                    f"The trap resets for another round."
                )

                attempt.result_text = result_text
                attempt.save(update_fields=["result_text"])
        else:
            remaining = trap_progress["living_count"] - trap_progress["attempted_count"]

            result_text = (
                f"{result_text} "
                f"Waiting for {remaining} more party member"
                f"{'s' if remaining != 1 else ''} to attempt the trap."
            )

            attempt.result_text = result_text
            attempt.save(update_fields=["result_text"])

    update_run_status_after_room_result(run)
    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.ACTIVE:
        next_character = advance_room_turn(run)

        if next_character:
            result_text = (
                f"{result_text} "
                f"Next turn: {next_character.character_name}."
            )

            attempt.result_text = result_text
            attempt.save(update_fields=["result_text"])

    messages.info(request, result_text)

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def move_to_room(request, join_code, room_id):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "The party cannot move right now.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if membership.party.current_dm_id != character.id:
        messages.warning(request, "Only the current DM can move the party.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if not run.current_room.is_cleared:
        messages.warning(request, "Clear the current room before moving.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    target_room = get_object_or_404(
        DungeonRunRoom,
        id=room_id,
        run=run,
    )

    connection_exists = DungeonRunConnection.objects.filter(
        run=run,
    ).filter(
        models.Q(from_room=run.current_room, to_room=target_room)
        | models.Q(from_room=target_room, to_room=run.current_room)
    ).exists()

    if not connection_exists:
        messages.warning(request, "That room is not connected to your current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run.current_room = target_room
    run.save(update_fields=["current_room", "updated_at"])

    messages.success(
        request,
        f"The party moved to Room {target_room.room_number}: {target_room.name}.",
    )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def pass_room_turn(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.ACTIVE:
        messages.warning(request, "The party cannot pass turns right now.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room is None:
        messages.warning(request, "There is no current room.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.current_room.is_cleared:
        messages.warning(request, "The room is already cleared.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    ensure_run_has_turn(run)
    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.FAILED:
        messages.warning(
            request,
            "The dungeon has failed.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
    
    if run.current_turn_character_id != character.id:
        if run.current_turn_character:
            messages.warning(
                request,
                f"It is {run.current_turn_character.character_name}'s turn.",
            )
        else:
            messages.warning(request, "There is no active turn right now.")

        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    next_character = advance_room_turn(run)

    run.refresh_from_db()

    if run.status == PartyDungeonRun.Status.FAILED:
        messages.warning(
            request,
            "The dungeon has failed.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if next_character:
        messages.info(
            request,
            f"{character.character_name} passed. Next turn: {next_character.character_name}.",
        )
    else:
        messages.warning(
            request,
            "No living characters remain.",
        )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

@login_required
def retry_dungeon_run(request, join_code, run_id):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    run = get_object_or_404(
        PartyDungeonRun.objects.select_related("party", "dungeon"),
        id=run_id,
        party__session=session,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.FAILED:
        messages.warning(
            request,
            "Only failed dungeon runs can be retried.",
        )
        return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

    with transaction.atomic():
        party = run.party

        run.current_room = None
        run.current_turn_character = None
        run.turn_number = 1
        run.status = PartyDungeonRun.Status.SELECTED
        run.failure_reason = PartyDungeonRun.FailureReason.NONE
        run.save(
            update_fields=[
                "current_room",
                "current_turn_character",
                "turn_number",
                "status",
                "failure_reason",
                "updated_at",
            ]
        )

        PartyInventoryItem.objects.filter(party=party).delete()

        RoomAttempt.objects.filter(room__run=run).delete()
        DungeonRunConnection.objects.filter(run=run).delete()
        DungeonRunRoom.objects.filter(run=run).delete()

        party_members = (
            PartyMember.objects
            .filter(party=party)
            .select_related("character", "character__character_class")
        )

        for member in party_members:
            character = member.character
            character.current_life = character.character_class.max_life
            character.current_action_points = character.character_class.action_points
            character.room_skill_ap_penalty = 0
            character.save(
                update_fields=[
                    "current_life",
                    "current_action_points",
                    "room_skill_ap_penalty",
                    "updated_at",
                ]
            )

        generate_dungeon_run(run)
        ensure_run_has_turn(run)

    messages.success(
        request,
        f"{party.name} can retry {run.dungeon.name}.",
    )

    return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

# ============================================================
# Boss action views
# ============================================================
def start_boss_fight(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if not membership:
        messages.error(request, "You need to be in a party to start the boss fight.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    party = membership.party

    if party.current_dm_id != character.id:
        messages.error(request, "Only the current DM can start the boss fight.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun.objects.select_related("party", "dungeon"),
        party=party,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.BOSS_READY:
        messages.warning(request, "The boss fight is not ready yet.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    boss_template = get_boss_template_for_run(run)

    if not boss_template:
        messages.error(
            request,
            "This dungeon does not have a boss assigned yet.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    with transaction.atomic():
        refresh_party_for_boss(party)

        encounter = create_boss_encounter_for_run(run)

        run.status = PartyDungeonRun.Status.BOSS_ACTIVE
        run.current_room = None
        run.current_turn_character = None
        run.turn_number = 1
        run.save(
            update_fields=[
                "status",
                "current_room",
                "current_turn_character",
                "turn_number",
                "updated_at",
            ]
        )
        
        resolve_boss_turn(encounter)

    messages.success(
        request,
        f"The final battle against {encounter.current_boss_name} has begun!",
    )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

@login_required
def teacher_start_boss_fight(request, join_code, run_id):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        teacher=request.user,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    run = get_object_or_404(
        PartyDungeonRun.objects.select_related("party", "dungeon"),
        id=run_id,
        party__session=session,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

    if run.status != PartyDungeonRun.Status.BOSS_READY:
        messages.warning(request, "This party is not ready for the boss fight yet.")
        return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

    boss_template = get_boss_template_for_run(run)

    if not boss_template:
        messages.error(
            request,
            "This dungeon does not have a boss assigned yet.",
        )
        return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

    with transaction.atomic():
        refresh_party_for_boss(run.party)

        encounter = create_boss_encounter_for_run(run)

        run.status = PartyDungeonRun.Status.BOSS_ACTIVE
        run.current_room = None
        run.current_turn_character = None
        run.turn_number = 1
        run.save(
            update_fields=[
                "status",
                "current_room",
                "current_turn_character",
                "turn_number",
                "updated_at",
            ]
        )
        resolve_boss_turn(encounter)

    messages.success(
        request,
        f"{run.party.name} has started the boss fight against {encounter.current_boss_name}.",
    )

    return redirect("fantasy_roles:teacher_dungeon_setup", join_code=session.join_code)

def activate_boss_ability(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if not membership:
        messages.error(request, "You need to be in a party.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if membership.party.current_dm_id != character.id:
        messages.error(request, "Only the current DM can activate boss abilities.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
        status=PartyDungeonRun.Status.BOSS_ACTIVE,
    )

    encounter = get_object_or_404(
        BossEncounter,
        run=run,
        status=BossEncounter.Status.ACTIVE,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if encounter.current_actor != BossEncounter.CurrentActor.BOSS:
        messages.warning(request, "It is not the boss's turn.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    with transaction.atomic():
        encounter = BossEncounter.objects.select_for_update().get(id=encounter.id)

        pending_result = resolve_boss_pending_effects(encounter)

        ability = get_current_boss_ability(encounter)

        boss_damage_bonus_effect_ids = list(
            get_active_boss_effects(
                encounter,
                target_type=BossCombatEffect.TargetType.PARTY,
                effect_code=BossCombatEffect.EffectCode.PARTY_EXTRA_BOSS_DAMAGE_TAKEN,
            ).values_list("id", flat=True)
        )

        previous_slot = encounter.next_boss_ability_slot

        if ability:
            ability_result = apply_boss_ability_effect(encounter, ability)

            combined_result_text = " ".join(
                text
                for text in [
                    pending_result.get("result_text", ""),
                    ability_result.get("result_text", ""),
                ]
                if text
            )

            BossActionLog.objects.create(
                encounter=encounter,
                actor_type=BossActionLog.ActorType.BOSS,
                action_type=BossActionLog.ActionType.BOSS_ABILITY,
                boss_ability=ability,
                phase=encounter.phase,
                round_number=encounter.round_number,
                player_phase_number=encounter.player_phase_number,
                die_roll=ability_result.get("die_roll"),
                success=True,
                damage_to_players=(
                    pending_result.get("damage_to_players", 0)
                    + ability_result.get("damage_to_players", 0)
                ),
                healing_done=ability_result.get("healing_done", 0),
                result_text=combined_result_text,
            )
        else:
            combined_result_text = pending_result.get("result_text", "")

            if not combined_result_text:
                combined_result_text = (
                    f"{encounter.current_boss_name} has no ability in this slot."
                )

            BossActionLog.objects.create(
                encounter=encounter,
                actor_type=BossActionLog.ActorType.BOSS,
                action_type=BossActionLog.ActionType.BOSS_ABILITY,
                phase=encounter.phase,
                round_number=encounter.round_number,
                player_phase_number=encounter.player_phase_number,
                success=True,
                damage_to_players=pending_result.get("damage_to_players", 0),
                result_text=combined_result_text,
            )

        consume_boss_damage_bonus_effects(
            encounter,
            boss_damage_bonus_effect_ids,
        )

        if check_boss_party_defeat_state(encounter):
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        if previous_slot == BossAbility.Slot.FIRST:
            encounter.next_boss_ability_slot = BossAbility.Slot.SECOND
        else:
            encounter.next_boss_ability_slot = BossAbility.Slot.FIRST
            encounter.round_number += 1

        encounter.player_phase_number += 1
        encounter.current_actor = BossEncounter.CurrentActor.PLAYER
        encounter.current_turn_character = None
        encounter.save(
            update_fields=[
                "next_boss_ability_slot",
                "round_number",
                "player_phase_number",
                "current_actor",
                "current_turn_character",
                "updated_at",
            ]
        )

        set_next_boss_player_turn_or_boss(encounter)

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def boss_basic_attack(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if not membership:
        messages.error(request, "You need to be in a party.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
        status=PartyDungeonRun.Status.BOSS_ACTIVE,
    )

    encounter = get_object_or_404(
        BossEncounter,
        run=run,
        status=BossEncounter.Status.ACTIVE,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if (
        encounter.current_actor != BossEncounter.CurrentActor.PLAYER
        or encounter.current_turn_character_id != character.id
    ):
        messages.warning(request, "It is not your boss turn.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    can_attack, reason = can_character_basic_attack_boss(encounter, character)

    if not can_attack:
        messages.warning(request, reason)
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    with transaction.atomic():
        encounter = BossEncounter.objects.select_for_update().get(id=encounter.id)

        die_roll = random.randint(1, 6)
        final_roll_total = die_roll
        difficulty = encounter.current_difficulty
        success = final_roll_total >= difficulty

        damage_to_boss = 0
        damage_to_player = 0

        if success:
            damage_to_boss = get_character_basic_boss_damage(
                encounter,
                character,
            )

            encounter.current_life = max(
                0,
                encounter.current_life - damage_to_boss,
            )
            encounter.save(update_fields=["current_life", "updated_at"])

            result_text = (
                f"{character.character_name} rolled {die_roll} and hit "
                f"{encounter.current_boss_name} for {damage_to_boss} damage."
            )
        else:
            extra_damage = get_failed_boss_throw_damage(encounter, character)

            if extra_damage > 0:
                damage_to_player = apply_boss_damage_to_character(
                    encounter,
                    character,
                    extra_damage,
                )

                result_text = (
                    f"{character.character_name} rolled {die_roll} and missed. "
                    f"They take {damage_to_player} backlash damage."
                )
            else:
                result_text = (
                    f"{character.character_name} rolled {die_roll} and missed."
                )

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.PLAYER,
            action_type=BossActionLog.ActionType.BASIC_ATTACK,
            character=character,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            die_roll=die_roll,
            final_roll_total=final_roll_total,
            difficulty_at_roll=difficulty,
            success=success,
            damage_to_boss=damage_to_boss,
            damage_to_players=damage_to_player,
            result_text=result_text,
        )

        if check_boss_transformation_or_victory(
            encounter,
            triggering_character=character,
        ):
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        consume_character_turn_effects(encounter, character)

        if check_boss_party_defeat_state(encounter):
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        set_next_boss_player_turn_or_boss(encounter)

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def boss_pass_turn(request, join_code):

    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if not membership:
        messages.error(request, "You need to be in a party.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
        status=PartyDungeonRun.Status.BOSS_ACTIVE,
    )

    encounter = get_object_or_404(
        BossEncounter,
        run=run,
        status=BossEncounter.Status.ACTIVE,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if (
        encounter.current_actor != BossEncounter.CurrentActor.PLAYER
        or encounter.current_turn_character_id != character.id
    ):
        messages.warning(request, "It is not your boss turn.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    with transaction.atomic():
        encounter = BossEncounter.objects.select_for_update().get(id=encounter.id)

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.PLAYER,
            action_type=BossActionLog.ActionType.PASS,
            character=character,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            success=True,
            result_text=f"{character.character_name} passes their turn.",
        )

        consume_character_turn_effects(encounter, character)

        set_next_boss_player_turn_or_boss(encounter)

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

def boss_use_skill(request, join_code):
    session = get_object_or_404(
        GameSession,
        join_code=join_code,
        game_template__code=GameTemplate.GameCode.FANTASY_ROLES,
    )

    participant, character, membership = get_student_character_and_membership(
        request,
        session,
    )

    if participant is None:
        return redirect("sessions:join_session", join_code=session.join_code)

    if character is None:
        return redirect("fantasy_roles:character_create", join_code=session.join_code)

    if membership is None:
        return redirect("fantasy_roles:student_party_detail", join_code=session.join_code)

    run = get_object_or_404(
        PartyDungeonRun,
        party=membership.party,
        status=PartyDungeonRun.Status.BOSS_ACTIVE,
    )

    encounter = get_object_or_404(
        BossEncounter,
        run=run,
        status=BossEncounter.Status.ACTIVE,
    )

    if request.method != "POST":
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if (
        encounter.current_actor != BossEncounter.CurrentActor.PLAYER
        or encounter.current_turn_character_id != character.id
    ):
        messages.warning(request, "It is not your boss turn.")
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    skill_id = request.POST.get("skill_id")

    skill = get_object_or_404(
        ClassSkill,
        id=skill_id,
        character_class=character.character_class,
        skill_scope=ClassSkill.SkillScope.BOSS,
    )

    if not skill_can_be_used_in_boss_step_one(skill):
        messages.warning(
            request,
            "This boss skill will be available in the next skill pass.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    ap_cost = skill.ap_cost
    life_cost = 0

    if boss_skills_cost_life(character):
        life_cost = ap_cost
        ap_cost = 0

    if not spend_character_ap(character, ap_cost):
        messages.warning(
            request,
            f"You need {ap_cost} AP to use {skill.name}.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    if not spend_character_life(character, life_cost):
        messages.warning(
            request,
            f"You need more than {life_cost} Life to use {skill.name}.",
        )
        return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

    with transaction.atomic():
        encounter = BossEncounter.objects.select_for_update().get(id=encounter.id)

        skill_result = resolve_direct_boss_skill(
            encounter,
            character,
            skill,
        )

        BossActionLog.objects.create(
            encounter=encounter,
            actor_type=BossActionLog.ActorType.PLAYER,
            action_type=BossActionLog.ActionType.BOSS_SKILL,
            character=character,
            player_skill=skill,
            phase=encounter.phase,
            round_number=encounter.round_number,
            player_phase_number=encounter.player_phase_number,
            die_roll=skill_result.get("die_roll"),
            final_roll_total=skill_result.get("final_roll_total"),
            difficulty_at_roll=skill_result.get("difficulty"),
            success=skill_result.get("success", True),
            damage_to_boss=skill_result.get("damage_to_boss", 0),
            healing_done=skill_result.get("healing_done", 0),
            result_text=skill_result.get("result_text", ""),
        )

        if check_boss_transformation_or_victory(
            encounter,
            triggering_character=character,
        ):
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        consume_character_turn_effects(encounter, character)

        if check_boss_party_defeat_state(encounter):
            return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)

        set_next_boss_player_turn_or_boss(encounter)

    messages.success(
        request,
        skill_result.get("result_text", f"{character.character_name} used {skill.name}."),
    )

    return redirect("fantasy_roles:student_dungeon_detail", join_code=session.join_code)
