from roleplay.models import RolePlaySituation, RoleCard


situation, situation_created = RolePlaySituation.objects.update_or_create(
    slug="the-star-dish-supply-mission",
    defaults={
        "title": "The Star Dish Supply Mission",
        "summary": (
            "Restaurant teams visit the University Ingredient Market to find "
            "products for their star dishes. Every student represents a "
            "restaurant and also manages a supplier stall with private "
            "inventory, quantities, prices, and availability."
        ),
        "student_briefing": (
            "Your restaurant team is preparing its star dish. Bring your "
            "ingredient list to the University Ingredient Market. Talk to "
            "different suppliers and find the products your team needs. "
            "Ask about quantities, containers, and prices. You also manage "
            "a supplier stall, so answer questions using the private "
            "information on your role card. Do not show your card to anyone."
        ),
        "teacher_notes": (
            "Use this activity after teams choose their restaurant and star "
            "dish, but before they complete the final shopping list. Give "
            "students 3–5 minutes to review their team list and role card. "
            "Model one customer-supplier conversation before starting. "
            "Allow 10–15 minutes for the market interaction. Every student "
            "should speak to at least two classmates, ask two quantity "
            "questions, make one polite request, and answer questions about "
            "their own inventory. If an ingredient is unavailable, students "
            "should ask for or offer a substitute. Provide shopping lists "
            "and role information as accessible plain text when required."
        ),
        "language_target": (
            "Countable and uncountable nouns; there is and there are; "
            "some, any, much, many, a few, and a little; How much? and "
            "How many?; containers and measurements; prices; polite "
            "requests with I’d like"
        ),
        "is_active": True,
    },
)


shared_objective = (
    "Find at least two ingredients for your team’s star dish. Speak to at "
    "least two classmates. Ask about quantities and prices, make a polite "
    "request, and record what is available or unavailable. When another "
    "student visits your stall, use your private inventory to answer them. "
    "If nobody has an ingredient, choose a possible substitute."
)

shared_language = (
    "Can I help you? | Do you have any...? | Is there any...? | "
    "How much ... is there? | How many ... are there? | "
    "There is some... | There is a little... | "
    "There are a few... | There isn’t any... | "
    "There aren’t any... | I’d like... | "
    "How much is it? | How much are they? | "
    "Would you like ... instead?"
)


roles = [
    (
        "The Fresh Produce Supplier",
        "You supply fresh fruit and vegetables to local restaurants.",
        (
            "Your stall has 12 tomatoes at $5 MXN each, 8 onions at "
            "$6 each, 6 bell peppers at $12 each, and 4 cucumbers at "
            "$10 each."
        ),
        (
            "There isn’t any lettuce today. You can offer cabbage for "
            "$18 MXN instead."
        ),
    ),
    (
        "The Dairy Supplier",
        "You supply milk, cheese, butter, and other dairy products.",
        (
            "Your stall has 4 cartons of milk at $28 MXN each, "
            "500 grams of cheese at $70, 500 grams of butter at $65, "
            "and 8 cups of yogurt at $15 each."
        ),
        (
            "There is only a little cheese left. One customer can buy "
            "a maximum of 250 grams."
        ),
    ),
    (
        "The Bakery Supplier",
        "You supply bread and baking products to restaurants.",
        (
            "Your stall has 10 loaves of bread at $35 MXN each, "
            "24 tortillas at $2 each, 4 bags of flour at $25 each, "
            "and 6 boxes of cookies at $30 each."
        ),
        (
            "There aren’t any hamburger buns. You can offer sliced "
            "bread instead."
        ),
    ),
    (
        "The Meat Supplier",
        "You supply meat and protein products.",
        (
            "Your stall has 1 kilogram of chicken at $110 MXN, "
            "2 kilograms of beef at $180 per kilogram, 12 sausages "
            "at $10 each, and 6 cans of tuna at $25 each."
        ),
        (
            "There is only a little chicken left. You cannot sell more "
            "than one kilogram."
        ),
    ),
    (
        "The Pantry Supplier",
        "You supply basic cooking ingredients and dry food.",
        (
            "Your stall has 5 bottles of oil at $45 MXN each, "
            "4 bags of rice at $30 each, 3 boxes of pasta at $25 each, "
            "and 6 jars of mayonnaise at $35 each."
        ),
        (
            "There isn’t any pasta sauce. You can offer two cans of "
            "tomatoes for $22 MXN each."
        ),
    ),
    (
        "The Fruit Market Supplier",
        "You supply fresh fruit for drinks, desserts, and salads.",
        (
            "Your stall has 10 apples at $8 MXN each, 12 bananas at "
            "$6 each, 500 grams of strawberries at $45, and 6 oranges "
            "at $7 each."
        ),
        (
            "There are only a few strawberries left. You cannot sell "
            "more than 250 grams to one customer."
        ),
    ),
    (
        "The Canned Goods Supplier",
        "You supply canned and preserved ingredients.",
        (
            "Your stall has 8 cans of beans at $22 MXN each, "
            "6 cans of corn at $20 each, 4 jars of salsa at $32 each, "
            "and 5 cans of tomatoes at $22 each."
        ),
        (
            "There isn’t any tuna today. You can offer beans or corn "
            "as an alternative."
        ),
    ),
    (
        "The Beverage Supplier",
        "You supply drinks and beverage ingredients.",
        (
            "Your stall has 10 bottles of water at $15 MXN each, "
            "8 cans of soda at $20 each, 4 cartons of apple juice at "
            "$38 each, and 2 bags of coffee at $120 each."
        ),
        (
            "There isn’t any orange juice. You can offer apple juice "
            "instead."
        ),
    ),
    (
        "The Breakfast Supplier",
        "You supply products commonly used for breakfast dishes.",
        (
            "Your stall has 6 eggs at $4 MXN each, 4 boxes of cereal "
            "at $65 each, 3 jars of jam at $55 each, and 2 bottles of "
            "honey at $80 each."
        ),
        (
            "There are only a few eggs left. You cannot sell more than "
            "four eggs to one customer."
        ),
    ),
    (
        "The Seasoning Supplier",
        "You supply seasonings, sauces, and cooking essentials.",
        (
            "Your stall has 4 bags of salt at $18 MXN each, "
            "3 bags of sugar at $32 each, 6 jars of herbs at $25 each, "
            "and 5 bottles of hot sauce at $28 each."
        ),
        (
            "There isn’t any black pepper. You can offer chili powder "
            "instead."
        ),
    ),
    (
        "The International Food Supplier",
        "You supply ingredients used in international dishes.",
        (
            "Your stall has 6 packages of noodles at $22 MXN each, "
            "20 tortillas at $2 each, 4 cans of coconut milk at "
            "$35 each, and 2 jars of curry sauce at $48 each."
        ),
        (
            "There are only two jars of curry sauce left. There isn’t "
            "enough for every restaurant."
        ),
    ),
    (
        "The Dessert Supplier",
        "You supply ingredients for cakes and desserts.",
        (
            "Your stall has 2 kilograms of flour at $25 MXN per "
            "kilogram, 1 kilogram of sugar at $32, 12 eggs at $4 each, "
            "and 6 cartons of cream at $30 each."
        ),
        (
            "There isn’t any chocolate. You can offer cocoa powder for "
            "$40 MXN per bag."
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