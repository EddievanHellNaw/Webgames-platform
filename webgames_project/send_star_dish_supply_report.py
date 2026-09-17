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
            "Report the result of your ingredient mission. Describe your "
            "star dish and kitchen inventory, identify the classmate you "
            "spoke to, record the quantities you discovered, and explain "
            "what your restaurant needs to buy."
        ),
        "applies_to_all_roles": True,
        "is_required": True,
        "allow_multiple": False,
        "sort_order": 1,
    },
)

template.fields.all().delete()

RolePlayRecordField.objects.create(
    template=template,
    label="Our star dish and kitchen inventory",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Name the dish. Use there is, there are, some, any, "
        "a few, or a little to describe the available ingredients."
    ),
    placeholder=(
        "Our star dish is... There is some... "
        "There are a few... There isn't any..."
    ),
    required=True,
    sort_order=1,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Person I spoke to",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text="Write the name and role of one classmate.",
    placeholder="I spoke to... They were a market vendor.",
    required=True,
    sort_order=2,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Quantities I discovered",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Record at least two questions and answers using "
        "How much or How many."
    ),
    placeholder=(
        "How many tomatoes are there? There are... "
        "How much cheese is there? There is..."
    ),
    required=True,
    sort_order=3,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Our final shopping decision",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "List what the restaurant will buy. Include quantities, "
        "containers, or measurements."
    ),
    placeholder=(
        "We need a kilo of... We need two cans of... "
        "We would like to buy..."
    ),
    required=True,
    sort_order=4,
)

print("Star Dish Supply Mission report created.")
print(f"Situation: {situation.title}")
print(f"Fields: {template.fields.count()}")