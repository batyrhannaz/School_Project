from django import forms
from django.contrib.auth import get_user_model
from .models import Grade, Homework

User = get_user_model()


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ["student", "subject", "value", "comment"]

    def __init__(self, *args, school_class=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(profile__role="student").select_related("profile__school_class")
        if school_class is not None:
            qs = qs.filter(profile__school_class=school_class)
        self.fields["student"].queryset = qs.order_by("profile__school_class__name", "last_name", "username")
        self.fields["student"].label_from_instance = lambda u: "%s (%s)" % (
            u.get_full_name() or u.username, u.profile.school_class or "без класса")


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ["school_class", "subject", "due_date", "text", "attachment"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, classes=None, **kwargs):
        super().__init__(*args, **kwargs)
        if classes is not None:
            self.fields["school_class"].queryset = classes
