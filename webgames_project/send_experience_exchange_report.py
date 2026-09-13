from roleplay.models import (
    RolePlaySituation,
    RolePlayRecordTemplate,
    RolePlayRecordField,
)

situation = RolePlaySituation.objects.get(
    slug="the-experience-exchange"
)

template, created = RolePlayRecordTemplate.objects.update_or_create(
    situation=situation,
    title="Experience Exchange Objective Report",
    defaults={
        "instructions": (
            "Report on your mission. First describe your own experience. "
            "Then identify a classmate you talked to and explain what you "
            "learned from them and how their experience connects to your objective."
        ),
        "applies_to_all_roles": True,
        "is_required": True,
        "allow_multiple": False,
        "sort_order": 1,
    },
)

# Rebuild the fields so running this script again stays predictable.
template.fields.all().delete()

RolePlayRecordField.objects.create(
    template=template,
    label="My experience",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text="Describe the experience connected to your role.",
    placeholder="I have...",
    required=True,
    sort_order=1,
)

RolePlayRecordField.objects.create(
    template=template,
    label="Person I interviewed",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text="Write the name of one classmate you talked to.",
    placeholder="I talked to...",
    required=True,
    sort_order=2,
)

RolePlayRecordField.objects.create(
    template=template,
    label="What I discovered",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text="Explain how this person's experience connects to your mission.",
    placeholder="This person has...",
    required=True,
    sort_order=3,
)

print("Experience Exchange objective report created.")
print(f"Situation: {situation.title}")
print(f"Fields: {template.fields.count()}")
