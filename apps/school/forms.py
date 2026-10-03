from django import forms
from django.contrib.auth import get_user_model
from .models import Announcement, Grade, Homework

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


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["school_class", "title", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, classes=None, allow_school=False, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["school_class"]
        if classes is not None:
            field.queryset = classes
        if allow_school:
            field.required = False
            field.empty_label = "Вся школа"
        else:
            field.required = True
            field.empty_label = None