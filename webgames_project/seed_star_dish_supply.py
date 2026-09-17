from roleplay.models import RolePlaySituation, RoleCard


situation, situation_created = RolePlaySituation.objects.update_or_create(
    slug="the-star-dish-supply-mission",
    defaults={
        "title": "The Star Dish Supply Mission",
        "summary": (
            "Restaurant teams shop for ingredients for their star dish. "
            "Each student is a customer and a supplier."
        ),
        "student_briefing": (
            "Your team has a restaurant and a star dish. You need "
            "ingredients for your dish. Talk to different suppliers. "
            "Ask about products, quantities, and prices. Buy at least "
            "two ingredients. You also have a market stall. Use your "
            "role card to answer questions. Do not show your card."
        ),
        "teacher_notes": (
            "Use this activity after teams choose their restaurant and "
            "star dish. Give students time to read their ingredient list "
            "and role card. Model one short customer-supplier conversation. "
            "Students should talk to at least two classmates. They should "
            "ask about quantities and prices and use I'd like. Help students "
            "record their purchases. Provide the role information as plain "
            "text when needed."
        ),
        "language_target": (
            "Countable and uncountable nouns; there is and there are; "
            "some, any, much, many, a few, and a little; How much? and "
            "How many?; containers and measurements; prices; polite "
            "requests with I'd like"
        ),
        "is_active": True,
    },
)


shared_objective = (
    "• Find 2 ingredients for your star dish.\n"
    "• You have $100 MXN.\n"
    "• Buy the 2 ingredients.\n"
    "• Use the Useful Language section.\n"
    "• Do not show your role card."
)


shared_language = (
    "Can I help you? | "
    "Do you have any...? | "
    "Yes, I do. | "
    "No, I don't. | "
    "How many ... do you have? | "
    "How much ... do you have? | "
    "There is some... | "
    "There is a little... | "
    "There are a few... | "
    "There isn't any... | "
    "There aren't any... | "
    "How much is it? | "
    "How much are they? | "
    "I'd like... | "
    "Here you are. | "
    "Would you like ... instead?"
)


roles = [
    (
        "The Fresh Produce Supplier",
        "You sell fresh vegetables.",
        (
            "Your stall has:\n"
            "• 12 tomatoes: $5 MXN each\n"
            "• 8 onions: $6 MXN each\n"
            "• 6 bell peppers: $12 MXN each\n"
            "• 4 cucumbers: $10 MXN each"
        ),
        (
            "There isn't any lettuce today.\n"
            "You have cabbage: $18 MXN each."
        ),
    ),
    (
        "The Dairy Supplier",
        "You sell milk, cheese, butter, and yogurt.",
        (
            "Your stall has:\n"
            "• 4 cartons of milk: $28 MXN each\n"
            "• 500 grams of cheese: $70 MXN\n"
            "• 500 grams of butter: $65 MXN\n"
            "• 8 cups of yogurt: $15 MXN each"
        ),
        (
            "There is only a little cheese left.\n"
            "One customer can buy 250 grams."
        ),
    ),
    (
        "The Bakery Supplier",
        "You sell bread and baking products.",
        (
            "Your stall has:\n"
            "• 10 loaves of bread: $35 MXN each\n"
            "• 24 tortillas: $2 MXN each\n"
            "• 4 bags of flour: $25 MXN each\n"
            "• 6 boxes of cookies: $30 MXN each"
        ),
        (
            "There aren't any hamburger buns.\n"
            "You can offer sliced bread instead."
        ),
    ),
    (
        "The Meat Supplier",
        "You sell meat and other protein products.",
        (
            "Your stall has:\n"
            "• 1 kilogram of chicken: $110 MXN\n"
            "• 2 kilograms of beef: $180 MXN per kilogram\n"
            "• 12 sausages: $10 MXN each\n"
            "• 6 cans of tuna: $25 MXN each"
        ),
        (
            "There is only a little chicken left.\n"
            "One customer can buy 1 kilogram."
        ),
    ),
    (
        "The Pantry Supplier",
        "You sell basic cooking ingredients.",
        (
            "Your stall has:\n"
            "• 5 bottles of oil: $45 MXN each\n"
            "• 4 bags of rice: $30 MXN each\n"
            "• 3 boxes of pasta: $25 MXN each\n"
            "• 6 jars of mayonnaise: $35 MXN each"
        ),
        (
            "There isn't any pasta sauce.\n"
            "You have 2 cans of tomatoes: $22 MXN each."
        ),
    ),
    (
        "The Fruit Market Supplier",
        "You sell fresh fruit.",
        (
            "Your stall has:\n"
            "• 10 apples: $8 MXN each\n"
            "• 12 bananas: $6 MXN each\n"
            "• 500 grams of strawberries: $45 MXN\n"
            "• 6 oranges: $7 MXN each"
        ),
        (
            "There are only a few strawberries left.\n"
            "One customer can buy 250 grams."
        ),
    ),
    (
        "The Canned Goods Supplier",
        "You sell food in cans and jars.",
        (
            "Your stall has:\n"
            "• 8 cans of beans: $22 MXN each\n"
            "• 6 cans of corn: $20 MXN each\n"
            "• 4 jars of salsa: $32 MXN each\n"
            "• 5 cans of tomatoes: $22 MXN each"
        ),
        (
            "There isn't any tuna today.\n"
            "You can offer beans or corn instead."
        ),
    ),
    (
        "The Beverage Supplier",
        "You sell drinks.",
        (
            "Your stall has:\n"
            "• 10 bottles of water: $15 MXN each\n"
            "• 8 cans of soda: $20 MXN each\n"
            "• 4 cartons of apple juice: $38 MXN each\n"
            "• 2 bags of coffee: $120 MXN each"
        ),
        (
            "There isn't any orange juice.\n"
            "You can offer apple juice instead."
        ),
    ),
    (
        "The Breakfast Supplier",
        "You sell breakfast food.",
        (
            "Your stall has:\n"
            "• 6 eggs: $4 MXN each\n"
            "• 4 boxes of cereal: $65 MXN each\n"
            "• 3 jars of jam: $55 MXN each\n"
            "• 2 bottles of honey: $80 MXN each"
        ),
        (
            "There are only a few eggs left.\n"
            "One customer can buy 4 eggs."
        ),
    ),
    (
        "The Seasoning Supplier",
        "You sell salt, sugar, herbs, and sauces.",
        (
            "Your stall has:\n"
            "• 4 bags of salt: $18 MXN each\n"
            "• 3 bags of sugar: $32 MXN each\n"
            "• 6 jars of herbs: $25 MXN each\n"
            "• 5 bottles of hot sauce: $28 MXN each"
        ),
        (
            "There isn't any black pepper.\n"
            "You can offer chili powder instead."
        ),
    ),
    (
        "The International Food Supplier",
        "You sell food from different countries.",
        (
            "Your stall has:\n"
            "• 6 packages of noodles: $22 MXN each\n"
            "• 20 tortillas: $2 MXN each\n"
            "• 4 cans of coconut milk: $35 MXN each\n"
            "• 2 jars of curry sauce: $48 MXN each"
        ),
        (
            "There are only 2 jars of curry sauce.\n"
            "There isn't enough for every restaurant."
        ),
    ),
    (
        "The Dessert Supplier",
        "You sell ingredients for cakes and desserts.",
        (
            "Your stall has:\n"
            "• 2 kilograms of flour: $25 MXN per kilogram\n"
            "• 1 kilogram of sugar: $32 MXN\n"
            "• 12 eggs: $4 MXN each\n"
            "• 6 cartons of cream: $30 MXN each"
        ),
        (
            "There isn't any chocolate.\n"
            "You have cocoa powder: $40 MXN per bag."
        ),
    ),
]


# Remove outdated roles from this situation if the seed changes later.
active_role_names = [role[0] for role in roles]

RoleCard.objects.filter(
    situation=situation
).exclude(
    name__in=active_role_names
).delete()


created_count = 0
updated_count = 0

for sort_order, (
    name,
    public_description,
    private_briefing,
    secret_information,
) in enumerate(roles, start=1):

    _, created = RoleCard.objects.update_or_create(
        situation=situation,
        name=name,
        defaults={
            "character_name": "",
            "public_description": public_description,
            "private_briefing": private_briefing,
            "objective": shared_objective,
            "secret_information": secret_information,
            "useful_language": shared_language,
            # Twelve roles with two copies provide 24 student slots.
            "copies_available": 2,
            "sort_order": sort_order,
            "is_active": True,
        },
    )

    if created:
        created_count += 1
    else:
        updated_count += 1


print("Star Dish Supply Mission seed complete.")
print(
    f"Situation: {situation.title} "
    f"({'created' if situation_created else 'updated'})"
)
print(f"Roles created: {created_count}")
print(f"Roles updated: {updated_count}")
print(f"Total active role slots: {situation.total_role_slots}")