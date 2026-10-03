"""Защита входа от подбора пароля.

После MAX_ATTEMPTS неудачных попыток подряд для одного логина вход закрывается на LOCK_MINUTES минут
(даже если потом ввести правильный пароль). Успешный вход сбрасывает счётчик.
Блокировка считается по логину, а не по IP: за прокси Render адрес клиента легко подделать.
"""
import ipaddress
import math
from datetime import timedelta

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import LoginFailure

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def normalize(username):
    return (username or "").strip().lower()[:150]


def minutes_left(username):
    """0, если вход разрешён; иначе сколько минут ещё действует блокировка."""
    name = normalize(username)
    if not name:
        return 0
    since = timezone.now() - timedelta(minutes=LOCK_MINUTES)
    recent = list(LoginFailure.objects.filter(username=name, created__gte=since)
                  .order_by("-created").values_list("created", flat=True)[:MAX_ATTEMPTS])
    if len(recent) < MAX_ATTEMPTS:
        return 0
    left = (recent[0] + timedelta(minutes=LOCK_MINUTES)) - timezone.now()
    return max(1, math.ceil(left.total_seconds() / 60))


def client_ip(request):
    if request is None:
        return None
    raw = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def record_failure(username, request=None):
    name = normalize(username)
    if not name or minutes_left(name):
        return  # уже заблокирован: срок не продлеваем
    LoginFailure.objects.create(username=name, ip=client_ip(request))
    LoginFailure.objects.filter(created__lt=timezone.now() - timedelta(days=1)).delete()


def clear_failures(username):
    name = normalize(username)
    if name:
        LoginFailure.objects.filter(username=name).delete()


class LockoutMixin:
    def clean(self):
        left = minutes_left(self.cleaned_data.get("username"))
        if left:
            raise ValidationError(
                "Слишком много неудачных попыток входа. Попробуйте снова через %d мин." % left, code="locked")
        return super().clean()


class LockoutAuthenticationForm(LockoutMixin, AuthenticationForm):
    pass


class LockoutAdminAuthenticationForm(LockoutMixin, AdminAuthenticationForm):
    pass