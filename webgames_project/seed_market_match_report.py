from roleplay.models import (
    RolePlaySituation,
    RolePlayRecordTemplate,
    RolePlayRecordField,
)


situation = RolePlaySituation.objects.get(
    slug="market-match-inspector"
)

template, created = RolePlayRecordTemplate.objects.update_or_create(
    situation=situation,
    title="Market Match Inspector Report",
    defaults={
        "instructions": (
            "Record your partner, your natural grocery match, and the "
            "ten Market Inspector sentences you corrected together."
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
    label="My partner",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text="Write the name of the classmate you worked with.",
    placeholder="I worked with...",
    required=True,
    sort_order=1,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Our natural pair",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text=(
        "Write the complete product and container expression."
    ),
    placeholder="Milk + carton = a carton of milk.",
    required=True,
    sort_order=2,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Our ten corrected sentences",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write the ten Market Inspector sentences correctly."
    ),
    placeholder=(
        "1. There isn't much milk in the carton.\n"
        "2. I need two bottles of oil.\n"
        "Continue until sentence 10."
    ),
    required=True,
    sort_order=3,
)


print("Market Match Inspector report updated.")
print(f"Situation: {situation.title}")
print(f"Fields: {template.fields.count()}")