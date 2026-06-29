import random

from django.db import transaction

from django.db import transaction

from .models import (
    DungeonRoom,
    DungeonRoomConnection,
    DungeonRunConnection,
    DungeonRunRoom,
    PartyDungeonRun,
)


GRID_POSITIONS = [
    (1, 1), (1, 2), (1, 3),
    (2, 1), (2, 2), (2, 3),
    (3, 1), (3, 2), (3, 3),
]


def clamp(value, minimum=1, maximum=5):
    return max(minimum, min(maximum, value))


def random_difficulty(base_difficulty):
    return clamp(base_difficulty + random.choice([-1, 0, 0, 1]))


def build_room_type_list(dungeon):
    room_types = []

    room_types += [DungeonRunRoom.RoomType.COMBAT] * dungeon.combat_room_count
    room_types += [DungeonRunRoom.RoomType.TRAP] * dungeon.trap_room_count
    room_types += [DungeonRunRoom.RoomType.TREASURE] * dungeon.treasure_room_count
    room_types += [DungeonRunRoom.RoomType.SPECIAL] * dungeon.special_room_count

    if len(room_types) < dungeon.room_count:
        missing = dungeon.room_count - len(room_types)
        room_types += [DungeonRunRoom.RoomType.TRAP] * missing

    if len(room_types) > dungeon.room_count:
        raise ValueError(
            f"{dungeon.name} has more configured rooms than room_count allows."
        )

    random.shuffle(room_types)

    # Avoid making the starting room the special mimic room.
    if room_types[0] == DungeonRunRoom.RoomType.SPECIAL:
        for index, room_type in enumerate(room_types):
            if room_type != DungeonRunRoom.RoomType.SPECIAL:
                room_types[0], room_types[index] = room_types[index], room_types[0]
                break

    return room_types


def get_adjacent_positions(position):
    row, col = position

    possible = [
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ]

    return [
        item for item in possible
        if 1 <= item[0] <= 3 and 1 <= item[1] <= 3
    ]


def generate_connected_grid_edges():
    """
    Creates a connected random graph over a 3x3 grid.

    The result is:
    - Always fully connected.
    - Still random.
    - Uses only adjacent grid positions.
    """
    positions = GRID_POSITIONS[:]
    start = positions[0]

    visited = {start}
    frontier = [start]
    edges = set()

    while len(visited) < len(positions):
        current = random.choice(frontier)
        neighbors = [
            neighbor for neighbor in get_adjacent_positions(current)
            if neighbor not in visited
        ]

        if not neighbors:
            frontier.remove(current)
            continue

        neighbor = random.choice(neighbors)
        visited.add(neighbor)
        frontier.append(neighbor)

        edge = tuple(sorted([current, neighbor]))
        edges.add(edge)

    all_possible_edges = set()

    for position in positions:
        for neighbor in get_adjacent_positions(position):
            edge = tuple(sorted([position, neighbor]))
            all_possible_edges.add(edge)

    extra_edges = list(all_possible_edges - edges)
    random.shuffle(extra_edges)

    # Add a few extra paths so the dungeon is not just a line/tree.
    extra_edge_count = random.randint(2, 4)

    for edge in extra_edges[:extra_edge_count]:
        edges.add(edge)

    return edges


def generated_room_name(room_type, room_number):
    if room_type == DungeonRunRoom.RoomType.TRAP:
        return f"Trap Room {room_number}"

    if room_type == DungeonRunRoom.RoomType.COMBAT:
        return f"Combat Room {room_number}"

    if room_type == DungeonRunRoom.RoomType.TREASURE:
        return f"Treasure Room {room_number}"

    if room_type == DungeonRunRoom.RoomType.SPECIAL:
        return f"Suspicious Room {room_number}"

    return f"Room {room_number}"


def generated_flavor_text(room_type, dungeon):
    if room_type == DungeonRunRoom.RoomType.TRAP:
        return (
            f"A dangerous obstacle blocks the way through {dungeon.name}. "
            "Describe what your character does to overcome it."
        )

    if room_type == DungeonRunRoom.RoomType.COMBAT:
        return (
            f"An enemy appears inside {dungeon.name}. "
            "Use attacks or skills to defeat it."
        )

    if room_type == DungeonRunRoom.RoomType.TREASURE:
        return (
            "The party finds a treasure room. "
            "Something useful may be hidden here."
        )

    if room_type == DungeonRunRoom.RoomType.SPECIAL:
        return (
            "This room feels strange. The treasure may not be what it seems."
        )

    return "The party enters a mysterious room."


def get_templates_for_type(dungeon, room_type):
    return list(
        DungeonRoomTemplate.objects.filter(
            dungeon=dungeon,
            room_type=room_type,
            is_active=True,
        )
    )


def choose_template_for_room(dungeon, room_type, used_template_ids):
    templates = get_templates_for_type(dungeon, room_type)

    if not templates:
        raise ValueError(
            f"No active {room_type} templates found for {dungeon.name}. "
            "Add room templates in the Django admin."
        )

    available_templates = [
        template for template in templates
        if template.id not in used_template_ids
    ]

    if not available_templates:
        raise ValueError(
            f"Not enough active {room_type} templates for {dungeon.name}. "
            "Add more templates or lower this dungeon's room count configuration."
        )

    template = random.choice(available_templates)
    used_template_ids.add(template.id)
    return template

@transaction.atomic
def generate_dungeon_run(run):
    """
    Generates a dungeon run from the designed DungeonRoom map.

    The map structure stays readable:
    - Room numbers, grid positions, and connections come from the designed slots.

    The room contents are shuffled:
    - Name, type, difficulty, text, images, and mimic data come from randomized DungeonRoom records.

    This means the same dungeon layout can produce different runs.
    """
    run = (
        PartyDungeonRun.objects
        .select_for_update()
        .select_related("dungeon")
        .get(id=run.id)
    )

    dungeon = run.dungeon

    DungeonRunConnection.objects.filter(run=run).delete()
    DungeonRunRoom.objects.filter(run=run).delete()

    slot_rooms = list(
        DungeonRoom.objects
        .filter(dungeon=dungeon)
        .exclude(room_type=DungeonRoom.RoomType.BOSS)
        .order_by("number")
    )

    if not slot_rooms:
        raise ValueError(
            f"{dungeon.name} has no designed DungeonRoom records."
        )

    content_rooms = slot_rooms[:]
    random.shuffle(content_rooms)

    # Avoid an identical order when possible.
    if (
        len(content_rooms) > 1
        and [room.id for room in content_rooms] == [room.id for room in slot_rooms]
    ):
        content_rooms = content_rooms[1:] + content_rooms[:1]

    generated_by_slot_id = {}
    generated_rooms = []

    for slot_room, content_room in zip(slot_rooms, content_rooms):
        generated_room = DungeonRunRoom.objects.create(
            run=run,
            source_room=content_room,
            source_template=None,

            # Map slot identity
            room_number=slot_room.number,
            grid_row=slot_room.grid_row,
            grid_col=slot_room.grid_col,

            # Randomized room content
            name=content_room.name or f"Room {slot_room.number}",
            room_type=content_room.room_type,
            difficulty=content_room.difficulty or dungeon.difficulty_rating or 3,
            flavor_text=content_room.flavor_text,
            failure_text=content_room.failure_text,
            damage_on_failure=content_room.damage_on_failure,
            is_cleared=False,
        )

        generated_by_slot_id[slot_room.id] = generated_room
        generated_rooms.append(generated_room)

    source_connections = (
        DungeonRoomConnection.objects
        .filter(dungeon=dungeon)
        .select_related("from_room", "to_room")
        .order_by("from_room__number", "to_room__number")
    )

    created_connection_count = 0

    for source_connection in source_connections:
        from_generated_room = generated_by_slot_id.get(
            source_connection.from_room_id
        )
        to_generated_room = generated_by_slot_id.get(
            source_connection.to_room_id
        )

        if not from_generated_room or not to_generated_room:
            continue

        DungeonRunConnection.objects.get_or_create(
            run=run,
            from_room=from_generated_room,
            to_room=to_generated_room,
        )

        created_connection_count += 1

    # Fallback if no designed connections exist.
    if created_connection_count == 0 and len(generated_rooms) > 1:
        for index in range(len(generated_rooms) - 1):
            DungeonRunConnection.objects.get_or_create(
                run=run,
                from_room=generated_rooms[index],
                to_room=generated_rooms[index + 1],
            )

    first_room = generated_by_slot_id[slot_rooms[0].id]

    run.current_room = first_room
    run.current_turn_character = None
    run.turn_number = 1
    run.status = PartyDungeonRun.Status.ACTIVE
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

    dungeon.recalculate_difficulty_rating(save=True)

    return run