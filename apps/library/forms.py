from django import forms
from django.contrib.auth import get_user_model

from .models import Book, BookCopy

User = get_user_model()


class IssueForm(forms.Form):
    reader = forms.ModelChoiceField(queryset=User.objects.none(), label="Читатель")
    copy = forms.ModelChoiceField(queryset=BookCopy.objects.none(), label="Экземпляр книги")
    days = forms.IntegerField(label="Срок, дней (пусто = по умолчанию)", required=False, min_value=1, max_value=180)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reader"].queryset = (User.objects.filter(is_active=True, profile__isnull=False)
                                          .select_related("profile__school_class").order_by("last_name", "username"))
        self.fields["reader"].label_from_instance = lambda u: "%s (%s%s)" % (
            u.get_full_name() or u.username, u.profile.get_role_display(),
            (", " + str(u.profile.school_class)) if u.profile.school_class else "")
        self.fields["copy"].queryset = (BookCopy.objects.filter(status=BookCopy.AVAILABLE)
                                        .select_related("book").order_by("book__title"))


class BookForm(forms.ModelForm):
    new_category = forms.CharField(label="Или новая категория", required=False, max_length=100)
    copies = forms.IntegerField(label="Сколько экземпляров", min_value=1, max_value=50, initial=1)

    class Meta:
        model = Book
        fields = ["title", "author", "category", "description", "cover"]
