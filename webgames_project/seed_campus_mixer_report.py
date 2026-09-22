from roleplay.models import (
    RolePlaySituation,
    RolePlayRecordTemplate,
    RolePlayRecordField,
)


situation = RolePlaySituation.objects.get(
    slug="the-campus-connection-mixer"
)


template, created = RolePlayRecordTemplate.objects.update_or_create(
    situation=situation,
    title="Campus Connection Mixer Report",
    defaults={
        "instructions": (
            "Report on one successful conversation from the mixer. "
            "Identify the person you talked to, describe the experience "
            "you learned about, and report the conditional question you discussed."
        ),
        "applies_to_all_roles": True,
        "is_required": True,
        "allow_multiple": False,
        "sort_order": 1,
    },
)


# Rebuild fields so rerunning the seed stays predictable.
template.fields.all().delete()


RolePlayRecordField.objects.create(
    template=template,
    label="Person I connected with",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text="Write the name of one classmate you had a complete conversation with.",
    placeholder="I talked to...",
    required=True,
    sort_order=1,
)


RolePlayRecordField.objects.create(
    template=template,
    label="How we started the conversation",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write the small talk topic or expression you used to begin "
        "and continue the conversation."
    ),
    placeholder="We started talking about... I asked...",
    required=True,
    sort_order=2,
)


RolePlayRecordField.objects.create(
    template=template,
    label="Experience I discovered",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Describe your classmate's experience. Use Present Perfect "
        "to introduce the experience and Simple Past for the details."
    ),
    placeholder=(
        "This person has... It happened when... "
        "They went/saw/tried..."
    ),
    required=True,
    sort_order=3,
)


RolePlayRecordField.objects.create(
    template=template,
    label="Our What If question",
    field_type=RolePlayRecordField.FieldType.LONG_TEXT,
    help_text=(
        "Write one First or Second Conditional question from your conversation "
        "and summarize your classmate's answer."
    ),
    placeholder=(
        "I asked: 'What would you do if...?' "
        "They said they would..."
    ),
    required=True,
    sort_order=4,
)


RolePlayRecordField.objects.create(
    template=template,
    label="How we ended the conversation",
    field_type=RolePlayRecordField.FieldType.SHORT_TEXT,
    help_text="Write the expression you used to close the conversation politely.",
    placeholder="It was nice talking to you. See you later!",
    required=True,
    sort_order=5,
)


print("Campus Connection Mixer report created.")
print(f"Situation: {situation.title}")
print(f"Fields: {template.fields.count()}")