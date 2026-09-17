from roleplay.models import RolePlaySituation, RoleCard


situation, situation_created = RolePlaySituation.objects.update_or_create(
    slug="market-match-inspector",
    defaults={
        "title": "Find Your Market Match",
        "summary": (
            "Students receive either a grocery product or its natural "
            "container or measurement. They must find their matching "
            "classmate and correct ten Market Inspector sentences together."
        ),
        "student_briefing": (
            "You have one half of a grocery expression. You are either a "
            "Read your secret word. Find the classmate with your matching "
            "product, container, or measurement. Do not show your card or ask "
            "for the answer. Ask three clue questions. Then guess: 'Are you...?' "
            "When you find your partner, correct the ten sentences together."
        ),
        "teacher_notes": (
            "Use this activity before the Star Dish Supply Mission. "
            "Students first read their private information and find their "
            "exact product-container partner. Allow approximately five "
            "minutes for matching and ten to fifteen minutes for correcting "
            "the sentences. All students receive the same ten incorrect "
            "sentences. With an odd number of students, create one trio. "
            "For Lucero, provide a product role through plain text and ask "
            "her partner to read the ten sentences aloud."
        ),
        "language_target": (
            "Countable and uncountable nouns; containers and measurements; "
            "there is and there are; much and many; a few and a little; "
            "How much and How many; singular and plural container forms"
        ),
        "is_active": True,
    },
)


market_inspector_sentences = (
    "CORRECT THESE 10 MARKET INSPECTOR SENTENCES:\n\n"
    "1. There aren't many milk in the carton.\n"
    "2. I need two bottle of oil.\n"
    "3. There isn't many rice in the bag.\n"
    "4. We bought three can of tuna.\n"
    "5. There are a few jam in the jar.\n"
    "6. How many cereal is there in the box?\n"
    "7. We need two dozens of eggs.\n"
    "8. There is a few kilograms of tomatoes.\n"
    "9. I'd like two breads, please.\n"
    "10. How much liters of juice do we need?"
)


product_role_language = (
    "Are you a container? | "
    "Are you used for liquids? | "
    "Are you made of glass, metal, paper, or plastic? | "
    "Can people carry food in you? | "
    "Do you measure weight? | "
    "Do you measure liquids? | "
    "Do you represent twelve items? | "
    "Can I buy my product in you? | "
    "I think your word is... | "
    "Are you a...? | "
    "I think we are a match because..."
)


match_role_language = (
    "Is your noun countable? | "
    "Is it uncountable? | "
    "Is it a liquid? | "
    "Do people drink it? | "
    "Do people cook with it? | "
    "Is it sweet or salty? | "
    "Is it used for breakfast? | "
    "Does it come from a plant or an animal? | "
    "I think your product is... | "
    "Are you...? | "
    "I think we are a match because..."
)


pairs = [
    {
        "product": "Milk",
        "product_type": "uncountable",
        "match": "Carton",
        "match_type": "countable container",
        "expression": "a carton of milk",
    },
    {
        "product": "Oil",
        "product_type": "uncountable",
        "match": "Bottle",
        "match_type": "countable container",
        "expression": "a bottle of oil",
    },
    {
        "product": "Rice",
        "product_type": "uncountable",
        "match": "Bag",
        "match_type": "countable container",
        "expression": "a bag of rice",
    },
    {
        "product": "Tuna",
        "product_type": "uncountable",
        "match": "Can",
        "match_type": "countable container",
        "expression": "a can of tuna",
    },
    {
        "product": "Jam",
        "product_type": "uncountable",
        "match": "Jar",
        "match_type": "countable container",
        "expression": "a jar of jam",
    },
    {
        "product": "Cereal",
        "product_type": "uncountable",
        "match": "Box",
        "match_type": "countable container",
        "expression": "a box of cereal",
    },
    {
        "product": "Eggs",
        "product_type": "countable",
        "match": "Dozen",
        "match_type": "countable quantity",
        "expression": "a dozen eggs",
    },
    {
        "product": "Tomatoes",
        "product_type": "countable",
        "match": "Kilogram",
        "match_type": "countable measurement",
        "expression": "a kilogram of tomatoes",
    },
    {
        "product": "Bread",
        "product_type": "uncountable",
        "match": "Loaf",
        "match_type": "countable unit",
        "expression": "a loaf of bread",
    },
    {
        "product": "Juice",
        "product_type": "uncountable",
        "match": "Liter",
        "match_type": "countable measurement",
        "expression": "a liter of juice",
    },
]


# Validate that all products and matching words are unique.
products = [pair["product"] for pair in pairs]
matches = [pair["match"] for pair in pairs]

if len(pairs) != 10:
    raise ValueError("The activity must contain exactly 10 pairs.")

if len(products) != len(set(products)):
    raise ValueError("Every product must be unique.")

if len(matches) != len(set(matches)):
    raise ValueError("Every container or measurement must be unique.")


created_count = 0
updated_count = 0
current_role_names = []


for pair_number, pair in enumerate(pairs, start=1):
    product_role_name = f"Product: {pair['product']}"
    match_role_name = f"Match: {pair['match']}"

    current_role_names.extend([
        product_role_name,
        match_role_name,
    ])

    # Product role
    _, created = RoleCard.objects.update_or_create(
        situation=situation,
        name=product_role_name,
        defaults={
            "character_name": "",
            "public_description": (
                "You have a grocery product. Find its natural container, "
                "quantity, unit, or measurement."
            ),
            "private_briefing": (
                "YOUR PRIVATE MATCH INFORMATION\n\n"
                f"Your product: {pair['product'].upper()}\n"
                f"Product noun type: {pair['product_type'].upper()}\n"
                f"Find this match: {pair['match'].upper()}\n"
                f"Complete expression: {pair['expression']}"
            ),
            "objective": (
                f"Find the classmate who has {pair['match'].upper()}. "
                f"Confirm that your complete expression is "
                f"'{pair['expression']}'. Then correct the ten Market "
                "Inspector sentences together."
            ),
            "secret_information": market_inspector_sentences,
            "useful_language": product_role_language,
            "copies_available": 1,
            "sort_order": pair_number * 2 - 1,
            "is_active": True,
        },
    )

    if created:
        created_count += 1
    else:
        updated_count += 1

    # Container, unit, quantity, or measurement role
    _, created = RoleCard.objects.update_or_create(
        situation=situation,
        name=match_role_name,
        defaults={
            "character_name": "",
            "public_description": (
                "You have a container, quantity, unit, or measurement. "
                "Find the grocery product that naturally matches it."
            ),
            "private_briefing": (
                "YOUR PRIVATE MATCH INFORMATION\n\n"
                f"Your word: {pair['match'].upper()}\n"
                f"Word type: {pair['match_type'].upper()}\n"
                f"Find this product: {pair['product'].upper()}\n"
                f"Product noun type: {pair['product_type'].upper()}\n"
                f"Complete expression: {pair['expression']}"
            ),
            "objective": (
                f"Find the classmate who has {pair['product'].upper()}. "
                f"Confirm that your complete expression is "
                f"'{pair['expression']}'. Then correct the ten Market "
                "Inspector sentences together."
            ),
            "secret_information": market_inspector_sentences,
            "useful_language": match_role_language,
            "copies_available": 1,
            "sort_order": pair_number * 2,
            "is_active": True,
        },
    )

    if created:
        created_count += 1
    else:
        updated_count += 1


# Remove outdated or unpaired roles from this situation.
RoleCard.objects.filter(
    situation=situation
).exclude(
    name__in=current_role_names
).delete()


print("Market Match and Inspector seed complete.")
print(
    f"Situation: {situation.title} "
    f"({'created' if situation_created else 'updated'})"
)
print(f"Roles created: {created_count}")
print(f"Roles updated: {updated_count}")
print(f"Verified natural pairs: {len(pairs)}")
print(f"Total paired roles: {len(current_role_names)}")
print(f"Total active role slots: {situation.total_role_slots}")