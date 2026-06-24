from django import forms
from .models import PlayerCharacter


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

    def __init__(self, *args, **kwargs):
        character_classes = kwargs.pop("character_classes", None)
        super().__init__(*args, **kwargs)

        if character_classes is not None:
            self.fields["character_class"].queryset = character_classes