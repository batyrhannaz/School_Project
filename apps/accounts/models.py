from django.conf import settings
from django.db import models


class Profile(models.Model):
    TEACHER, PARENT, STUDENT, LIBRARIAN = "teacher", "parent", "student", "librarian"
    ROLES = [(TEACHER, "Учитель"), (PARENT, "Родитель"), (STUDENT, "Ученик(ца)"), (LIBRARIAN, "Библиотекарь")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("Роль", max_length=10, choices=ROLES, default=STUDENT)
    school_class = models.ForeignKey("school.SchoolClass", verbose_name="Класс (для ученика)", null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="students")
    children = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name="Дети (для родителя)",
                                      blank=True, related_name="parents")
    photo = models.ImageField("Фото профиля", upload_to="avatars/", blank=True)
    default_child = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Ребёнок по умолчанию", null=True,
                                      blank=True, on_delete=models.SET_NULL, related_name="+")
    default_class = models.ForeignKey("school.SchoolClass", verbose_name="Класс по умолчанию (учитель)", null=True,
                                      blank=True, on_delete=models.SET_NULL, related_name="+")
    notify_grades = models.BooleanField("Уведомлять о новых оценках", default=True)
    notify_books = models.BooleanField("Напоминать о возврате книг", default=True)
    notify_digest = models.BooleanField("Сводка за неделю", default=False)
    totp_secret = models.CharField(max_length=32, blank=True)
    totp_enabled = models.BooleanField("Двухфакторный вход", default=False)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"


class LoginEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_events")
    created = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Вход в систему"
        verbose_name_plural = "История входов"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    text = models.CharField("Текст", max_length=200)
    url = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created", "-id"]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return self.text

class LoginFailure(models.Model):
    """Неудачная попытка входа. Нужна для временной блокировки после нескольких ошибок подряд."""
    username = models.CharField("Логин", max_length=150, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Неудачная попытка входа"
        verbose_name_plural = "Неудачные попытки входа"

    def __str__(self):
        return "%s · %s" % (self.username, self.created.strftime("%d.%m.%Y %H:%M"))