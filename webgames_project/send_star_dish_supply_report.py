from roleplay.models import (
    RolePlaySituation,
    RolePlayRecordTemplate,
    RolePlayRecordField,
)


situation = RolePlaySituation.objects.get(
    slug="the-star-dish-supply-mission"
)


template, created = RolePlayRecordTemplate.objects.update_or_create(
    situation=situation,
    title="Star Dish Supply Mission Report",
    defaults={
        "instructions": (
            "Teams:\n"
            "Name your star dish and it's ingredients\n"
            "Decide what everyone will buy.\n\n"
            "Individual:\n"
            "Write about the supplier and what you found.\n"
        ),
        "applies_to_all_roles": True,
        "is_required": True,
        "allow_multiple": False,
        "sort_order": 1,
    },
)


# Rebuild the fields when the seeder runs.
template.fields.all().delete()


RolePlayRecordField.objects.create(
    template=template,
    label="Our star dish",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write the name of your dish. Write what you have and "
        "what you do not have. Use There is or There are."
    ),
    placeholder=(
        "Our star dish is tacos. There are a few tomatoes. "
        "There is some meat. There isn't any cheese."
    ),
    required=True,
    sort_order=1,
)


RolePlayRecordField.objects.create(
    template=template,
    label="What we will buy",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write at least two things your restaurant will buy. "
        "Include a quantity, container, or measurement."
    ),
    placeholder=(
        "We will buy 6 tomatoes and one kilogram of chicken. "
        "We will also buy a bottle of oil."
    ),
    required=True,
    sort_order=2,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Supplier I spoke to",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text=(
        "Write your classmate's name and supplier role."
    ),
    placeholder=(
        "I spoke to Ana. She was the Fresh Produce Supplier."
    ),
    required=True,
    sort_order=3,
)

RolePlayRecordField.objects.create(
    template=template,
    label="What I found",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write two questions and answers. Use How much or How many."
    ),
    placeholder=(
        "How many tomatoes do you have? There are 12 tomatoes.\n"
        "How much cheese do you have? There are 500 grams."
    ),
    required=True,
    sort_order=4,
)





print("Star Dish Supply Mission report created.")
print(f"Situation: {situation.title}")
print(f"Fields: {template.fields.count()}")