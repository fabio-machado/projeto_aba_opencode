"""
Forms for the core app.

Demonstrates backend validation pattern per Constitution dual-validation requirement.
"""

from django import forms


class ExampleForm(forms.Form):
    """
    Example form demonstrating Django Form validation.

    Used as a reference for future forms in the application.
    """

    title = forms.CharField(
        max_length=200,
        min_length=3,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[48px]",
                "placeholder": "Enter title (min 3 characters)",
            }
        ),
        help_text="Must be at least 3 characters long.",
    )

    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[48px]",
                "placeholder": "Optional description",
                "rows": 3,
            }
        ),
    )

    status = forms.ChoiceField(
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        required=True,
        widget=forms.RadioSelect(
            attrs={
                "class": "space-y-2",
            }
        ),
        help_text="Use toggle/radio buttons instead of select per Constitution.",
    )

    def clean_title(self) -> str:
        """Validate title field."""
        title = self.cleaned_data.get("title", "")
        if title and len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters.")
        return title
