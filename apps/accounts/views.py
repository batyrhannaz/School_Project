import csv

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.library.models import Loan
from apps.school.models import Grade, SchoolClass
from . import totp
from .models import LoginEvent, Notification
from .roles import role_of

User = get_user_model()
ROLE_LABELS = {"teacher": "Учитель", "parent": "Родитель", "student": "Ученик(ца)", "librarian": "Библиотекарь"}
MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _redirect_after_login(request, nxt):
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("cabinet")


# ---------- вход ----------
def choose_role(request):
    if request.user.is_authenticated:
        return redirect("cabinet")
    return render(request, "accounts/choose_role.html", {"next": request.GET.get("next", "")})


def role_login(request, role):
    if role not in ROLE_LABELS:
        raise Http404
    if request.user.is_authenticated:
        return redirect("cabinet")
    form = AuthenticationForm(request, data=request.POST or None)
    nxt = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        profile = getattr(user, "profile", None)
        user_role = getattr(profile, "role", None)
        if user.is_staff or user_role == role:
            if profile and profile.totp_enabled:
                request.session["pending_2fa"] = {"uid": user.pk, "next": nxt, "tries": 0}
                return redirect("login_2fa")
            login(request, user)
            return _redirect_after_login(request, nxt)
        form.add_error(None, "Этот аккаунт не относится к роли «%s». Вернитесь и выберите другую роль." % ROLE_LABELS[role])
    return render(request, "accounts/login.html", {
        "form": form, "role": role, "role_label": ROLE_LABELS[role], "next": nxt,
    })


def login_2fa(request):
    pending = request.session.get("pending_2fa")
    if not pending:
        return redirect("login")
    user = User.objects.filter(pk=pending["uid"], is_active=True).first()
    if user is None or not getattr(user, "profile", None):
        request.session.pop("pending_2fa", None)
        return redirect("login")
    error = None
    if request.method == "POST":
        if totp.verify(user.profile.totp_secret, request.POST.get("code")):
            request.session.pop("pending_2fa", None)
            login(request, user, backend=MODEL_BACKEND)
            return _redirect_after_login(request, pending.get("next"))
        pending["tries"] = pending.get("tries", 0) + 1
        if pending["tries"] >= 5:
            request.session.pop("pending_2fa", None)
            return redirect("login")
        request.session["pending_2fa"] = pending
        error = "Неверный код. Попробуйте ещё раз."
    return render(request, "accounts/login_2fa.html", {"error": error})


# ---------- профиль и почта ----------
class EmailForm(forms.Form):
    email = forms.EmailField(label="Gmail или другая почта")


@login_required
def profile(request):
    user = request.user
    form = EmailForm(request.POST or None, initial={"email": user.email})
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        if email == (user.email or "").lower():
            messages.info(request, "Эта почта уже привязана.")
        else:
            token = signing.dumps({"uid": user.pk, "email": email}, salt="email-confirm")
            link = request.build_absolute_uri(reverse("confirm_email", args=[token]))
            try:
                send_mail(
                    "Подтверждение почты",
                    "Здравствуйте!\n\nЧтобы привязать эту почту к аккаунту, перейдите по ссылке "
                    "(действует 24 часа):\n%s\n\nЕсли это были не вы, просто проигнорируйте письмо." % link,
                    None, [email])
                messages.success(request, "Письмо со ссылкой отправлено на %s. Перейдите по ссылке, чтобы привязать почту." % email)
            except Exception:
                messages.error(request, "Не удалось отправить письмо. Проверьте настройки почты сервера.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def confirm_email(request, token):
    try:
        data = signing.loads(token, salt="email-confirm", max_age=86400)
    except signing.BadSignature:
        messages.error(request, "Ссылка недействительна или устарела. Отправьте письмо ещё раз.")
        return redirect("profile")
    if data.get("uid") != request.user.pk:
        messages.error(request, "Эта ссылка предназначена для другого аккаунта. Войдите под нужным.")
        return redirect("profile")
    request.user.email = data["email"]
    request.user.save(update_fields=["email"])
    messages.success(request, "Почта %s привязана. Теперь по ней можно сбросить пароль." % data["email"])
    return redirect("profile")


# ---------- настройки ----------
class SettingsForm(forms.Form):
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)
    photo = forms.ImageField(label="Фото профиля", required=False)
    remove_photo = forms.BooleanField(label="Удалить фото", required=False)
    notify_grades = forms.BooleanField(label="Присылать на почту новые оценки", required=False)
    notify_books = forms.BooleanField(label="Напоминать о сроке возврата книг", required=False)
    notify_digest = forms.BooleanField(label="Присылать сводку за неделю (оценки и книги)", required=False)
    default_child = forms.ModelChoiceField(queryset=User.objects.none(), required=False,
                                           label="Ребёнок по умолчанию", empty_label="— первый по списку —")
    default_class = forms.ModelChoiceField(queryset=SchoolClass.objects.all(), required=False,
                                           label="Класс по умолчанию (для выставления оценок)", empty_label="— все классы —")

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if profile is not None and profile.role == "parent":
            self.fields["default_child"].queryset = profile.children.all()
        self.fields["default_child"].label_from_instance = lambda u: u.get_full_name() or u.username


def user_sessions(user):
    return [s for s in Session.objects.filter(expire_date__gte=timezone.now())
            if s.get_decoded().get("_auth_user_id") == str(user.pk)]


@login_required
def settings_page(request):
    user = request.user
    profile = getattr(user, "profile", None)
    initial = {"first_name": user.first_name, "last_name": user.last_name}
    if profile:
        initial.update(notify_grades=profile.notify_grades, notify_books=profile.notify_books,
                       notify_digest=profile.notify_digest, default_child=profile.default_child_id,
                       default_class=profile.default_class_id)
    form = SettingsForm(request.POST or None, request.FILES or None, initial=initial, profile=profile)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        user.first_name, user.last_name = cd["first_name"], cd["last_name"]
        user.save(update_fields=["first_name", "last_name"])
        if profile:
            profile.notify_grades = cd["notify_grades"]
            profile.notify_books = cd["notify_books"]
            profile.notify_digest = cd["notify_digest"]
            if profile.role == "parent":
                profile.default_child = cd["default_child"]
            if profile.role == "teacher":
                profile.default_class = cd["default_class"]
            if cd["remove_photo"]:
                profile.photo = ""
            elif cd["photo"]:
                profile.photo = cd["photo"]
            profile.save()
        messages.success(request, "Настройки сохранены.")
        return redirect("settings")
    return render(request, "accounts/settings.html", {
        "form": form, "profile": profile,
        "events": LoginEvent.objects.filter(user=user)[:5],
        "sessions_count": len(user_sessions(user)),
    })


class PasswordChange(SuccessMessageMixin, auth_views.PasswordChangeView):
    success_message = "Пароль изменён."


# ---------- безопасность ----------
@login_required
def two_factor(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        messages.error(request, "Двухфакторный вход доступен аккаунтам с ролью (учитель, родитель, ученик).")
        return redirect("settings")
    code = request.POST.get("code")
    if profile.totp_enabled:
        if request.method == "POST":
            if totp.verify(profile.totp_secret, code):
                profile.totp_enabled, profile.totp_secret = False, ""
                profile.save(update_fields=["totp_enabled", "totp_secret"])
                messages.success(request, "Двухфакторный вход отключён.")
                return redirect("settings")
            messages.error(request, "Неверный код.")
        return render(request, "accounts/two_factor.html", {"enabled": True})
    secret = request.session.get("totp_setup") or totp.new_secret()
    request.session["totp_setup"] = secret
    if request.method == "POST":
        if totp.verify(secret, code):
            profile.totp_secret, profile.totp_enabled = secret, True
            profile.save(update_fields=["totp_secret", "totp_enabled"])
            request.session.pop("totp_setup", None)
            messages.success(request, "Двухфакторный вход включён. При следующем входе понадобится код из приложения.")
            return redirect("settings")
        messages.error(request, "Неверный код. Проверьте, что время на телефоне точное, и попробуйте ещё раз.")
    return render(request, "accounts/two_factor.html", {
        "enabled": False, "secret": " ".join(secret[i:i + 4] for i in range(0, len(secret), 4)),
        "uri": totp.uri(secret, request.user.username),
    })


@login_required
@require_POST
def logout_everywhere(request):
    count = 0
    for s in user_sessions(request.user):
        if s.session_key != request.session.session_key:
            s.delete()
            count += 1
    messages.success(request, "Выход выполнен на других устройствах: %d." % count)
    return redirect("settings")


# ---------- данные ----------
@login_required
def export_data(request):
    user, role = request.user, role_of(request.user)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="my_data.csv"'
    response.write("\ufeff")  # чтобы Excel правильно показал кириллицу
    w = csv.writer(response, delimiter=";")
    students = []
    if role == "student":
        students = [user]
    elif role == "parent":
        students = list(user.profile.children.all())
    w.writerow(["Оценки"])
    w.writerow(["Ученик", "Предмет", "Оценка", "Дата", "Комментарий"])
    grades = Grade.objects.filter(teacher=user) if role == "teacher" else Grade.objects.filter(student__in=students)
    for g in grades.select_related("student", "subject"):
        w.writerow([g.student.get_full_name() or g.student.username, g.subject, g.value, g.date.strftime("%d.%m.%Y"), g.comment])
    w.writerow([])
    w.writerow(["Выдачи книг"])
    w.writerow(["Читатель", "Книга", "Выдана", "Вернуть до", "Возвращена"])
    for l in Loan.objects.filter(user__in=[user] + students).select_related("user", "copy__book").distinct():
        w.writerow([l.user.get_full_name() or l.user.username, l.copy.book.title, l.issued_at.strftime("%d.%m.%Y"),
                    l.due_date.strftime("%d.%m.%Y"), l.returned_at.strftime("%d.%m.%Y") if l.returned_at else ""])
    return response


@login_required
def delete_account(request):
    user = request.user
    if user.is_staff:
        messages.error(request, "Аккаунт сотрудника отключает администратор.")
        return redirect("settings")
    has_loans = Loan.objects.filter(user=user, returned_at__isnull=True).exists()
    if request.method == "POST":
        if has_loans:
            messages.error(request, "Сначала верните книги в библиотеку.")
        elif not user.check_password(request.POST.get("password", "")):
            messages.error(request, "Неверный пароль.")
        else:
            user.is_active = False
            user.save(update_fields=["is_active"])
            logout(request)
            messages.success(request, "Аккаунт отключён. Чтобы вернуть его, обратитесь к администратору школы.")
            return redirect("home")
        return redirect("delete_account")
    return render(request, "accounts/delete_account.html", {"has_loans": has_loans})


@login_required
def notifications(request):
    qs = Notification.objects.filter(user=request.user)
    items = list(qs[:50])
    qs.filter(is_read=False).update(is_read=True)
    return render(request, "accounts/notifications.html", {"items": items})
