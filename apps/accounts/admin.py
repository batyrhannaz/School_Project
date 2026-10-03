from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import LoginEvent, LoginFailure, Profile
User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    exclude = ("totp_secret",)
    filter_horizontal = ("children",)


admin.site.unregister(User)


@admin.register(User)
class SchoolUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "first_name", "last_name", "is_staff")


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("user", "created", "ip")
    readonly_fields = ("user", "created", "ip", "user_agent")

@admin.register(LoginFailure)
class LoginFailureAdmin(admin.ModelAdmin):
    """Пока у логина 5 свежих записей, вход закрыт. Чтобы разблокировать сразу, удалите записи этого логина."""
    list_display = ("username", "created", "ip")
    search_fields = ("username",)
    readonly_fields = ("username", "created", "ip")

    def has_add_permission(self, request):
        return False