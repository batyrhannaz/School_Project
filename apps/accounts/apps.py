from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Аккаунты"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from .models import LoginEvent

        def log_login(sender, request, user, **kwargs):
            if request is None:
                return
            LoginEvent.objects.create(
                user=user, ip=request.META.get("REMOTE_ADDR") or None,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:200])

        user_logged_in.connect(log_login, dispatch_uid="log_login_event")
