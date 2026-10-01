from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import LoginEvent, Profile

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
