from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Аккаунты"

    def ready(self):
        from django.contrib import admin
        from django.contrib.auth.signals import user_logged_in, user_login_failed
        from . import lockout
        from .models import LoginEvent

        def log_login(sender, request, user, **kwargs):
            if request is None:
                return
            LoginEvent.objects.create(
                user=user, ip=request.META.get("REMOTE_ADDR") or None,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:200])

        def on_login_failed(sender, credentials, request=None, **kwargs):
            lockout.record_failure(credentials.get("username"), request)

        def on_login_ok(sender, request, user, **kwargs):
            lockout.clear_failures(user.get_username())

        user_logged_in.connect(log_login, dispatch_uid="log_login_event")
        user_logged_in.connect(on_login_ok, dispatch_uid="clear_login_failures")
        user_login_failed.connect(on_login_failed, dispatch_uid="record_login_failure")

        # вход в админку (/admin/) тоже защищён от подбора пароля
        admin.site.login_form = lockout.LockoutAdminAuthenticationForm