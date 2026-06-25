import random

from django.db import transaction

from .models import (
    DungeonRunConnection,
    DungeonRunRoom,
    DungeonRoomTemplate,
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
    Generates the randomized dungeon for one party run.
    Safe to call once after PartyDungeonRun is created.
    """
    if run.generated_rooms.exists():
        return run

    dungeon = run.dungeon
    room_types = build_room_type_list(dungeon)

    positions = GRID_POSITIONS[:]

    position_to_room = {}
    used_template_ids = set()

    for index, position in enumerate(positions, start=1):
        room_type = room_types[index - 1]
        template = choose_template_for_room(
            dungeon,
            room_type,
            used_template_ids,
        )


        room = DungeonRunRoom.objects.create(
            run=run,
            source_template=template,
            room_number=index,
            name=template.name,
            room_type=room_type,
            difficulty=template.difficulty,
            flavor_text=template.flavor_text,
            failure_text=template.failure_text,
            damage_on_failure=template.damage_on_failure,
            grid_row=position[0],
            grid_col=position[1],
        )
        # IMPORTANT:
        # The key must be the grid position tuple, for example (1, 1).
        position_to_room[position] = room

    edges = generate_connected_grid_edges()

    for position_a, position_b in edges:
        DungeonRunConnection.objects.create(
            run=run,
            from_room=position_to_room[position_a],
            to_room=position_to_room[position_b],
        )

    starting_room = position_to_room[(1, 1)]
    run.current_room = starting_room
    run.status = PartyDungeonRun.Status.ACTIVE
    run.save(update_fields=["current_room", "status", "updated_at"])

    return run