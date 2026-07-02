import re
from django import forms
from .models import PlayerCharacter


# ============================================================
# Language production helpers
# ============================================================
def count_backstory_ideas(text):
    cleaned = (text or "").strip()

    if not cleaned:
        return 0

    chunks = re.split(r"(?:[.!?]+|\n+|;)", cleaned)

    meaningful_chunks = [
        chunk.strip()
        for chunk in chunks
        if len(chunk.strip().split()) >= 2
    ]

    return len(meaningful_chunks)


class PlayerCharacterForm(forms.ModelForm):
    class Meta:
        model = PlayerCharacter
        fields = [
            "character_class",
            "visual_variant",
            "character_name",
            "english_level",
            "backstory",
        ]

        widgets = {
            "character_class": forms.RadioSelect,
            "visual_variant": forms.RadioSelect,
            "backstory": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Write your character's backstory here...",
                }
            ),
        }

        labels = {
            "character_class": "Choose your class",
            "visual_variant": "Choose your character version",
            "character_name": "Character name",
            "english_level": "English practice level",
            "backstory": "Character backstory",
        }

    def clean_backstory(self):
        backstory = self.cleaned_data.get("backstory", "")

        if count_backstory_ideas(backstory) < 5:
            raise forms.ValidationError(
                "Write at least 5 ideas for your hero backstory."
            )

        return backstory

    def __init__(self, *args, **kwargs):
        character_classes = kwargs.pop("character_classes", None)
        super().__init__(*args, **kwargs)

        if character_classes is not None:
            self.fields["character_class"].queryset = character_classes