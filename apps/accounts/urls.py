from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

urlpatterns = [
    path("", views.choose_role, name="login"),
    path("verify/", views.login_2fa, name="login_2fa"),
    path("login/<str:role>/", views.role_login, name="role_login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # профиль и привязка почты
    path("notifications/", views.notifications, name="notifications"),
    path("profile/", views.profile, name="profile"),
    path("profile/confirm/<str:token>/", views.confirm_email, name="confirm_email"),

    # настройки, безопасность, данные
    path("settings/", views.settings_page, name="settings"),
    path("settings/2fa/", views.two_factor, name="two_factor"),
    path("settings/logout-everywhere/", views.logout_everywhere, name="logout_everywhere"),
    path("settings/export/", views.export_data, name="export_data"),
    path("settings/deactivate/", views.delete_account, name="delete_account"),
    path("password-change/", views.PasswordChange.as_view(
        template_name="accounts/password_change.html", success_url=reverse_lazy("settings")), name="password_change"),

    # сброс пароля по почте
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/pw_reset_form.html",
        email_template_name="accounts/pw_reset_email.txt",
        subject_template_name="accounts/pw_reset_subject.txt",
        success_url=reverse_lazy("password_reset_done")), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/pw_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/pw_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/pw_reset_complete.html"), name="password_reset_complete"),
]
