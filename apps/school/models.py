from django.conf import settings
from django.db import models
from django.utils import timezone

WEEKDAYS = [(1, "Понедельник"), (2, "Вторник"), (3, "Среда"), (4, "Четверг"), (5, "Пятница"), (6, "Суббота")]


class SchoolClass(models.Model):
    name = models.CharField("Класс", max_length=10, unique=True, help_text="Например: 9А")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Классный руководитель", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["name"]
        verbose_name = "Класс"
        verbose_name_plural = "Классы"

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField("Предмет", max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    def __str__(self):
        return self.name


class Lesson(models.Model):
    school_class = models.ForeignKey(SchoolClass, verbose_name="Класс", on_delete=models.CASCADE, related_name="lessons")
    weekday = models.PositiveSmallIntegerField("День недели", choices=WEEKDAYS)
    number = models.PositiveSmallIntegerField("№ урока")
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Учитель", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="lessons")
    room = models.CharField("Кабинет", max_length=20, blank=True)

    class Meta:
        ordering = ["weekday", "number"]
        unique_together = [("school_class", "weekday", "number")]
        verbose_name = "Урок"
        verbose_name_plural = "Расписание"

    def __str__(self):
        return f"{self.school_class} · {self.get_weekday_display()} · {self.number} · {self.subject}"


class Grade(models.Model):
    VALUES = [(5, "5"), (4, "4"), (3, "3"), (2, "2")]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Ученик", on_delete=models.CASCADE,
                                related_name="grades")
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.CASCADE, related_name="grades")
    value = models.PositiveSmallIntegerField("Оценка", choices=VALUES)
    date = models.DateField("Дата", default=timezone.localdate)
    comment = models.CharField("Комментарий", max_length=200, blank=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Учитель", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"

    def __str__(self):
        return f"{self.student} · {self.subject} · {self.value}"


class Homework(models.Model):
    school_class = models.ForeignKey(SchoolClass, verbose_name="Класс", on_delete=models.CASCADE, related_name="homework")
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Учитель", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    text = models.TextField("Задание")
    attachment = models.FileField("Файл", upload_to="homework/", blank=True)
    due_date = models.DateField("Сдать до")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "-id"]
        verbose_name = "Домашнее задание"
        verbose_name_plural = "Домашние задания"

    def __str__(self):
        return f"{self.school_class} · {self.subject} · до {self.due_date}"


class Attendance(models.Model):
    PRESENT, LATE, ABSENT, EXCUSED = "present", "late", "absent", "excused"
    STATUSES = [(PRESENT, "Присутствует"), (LATE, "Опоздал(а)"), (ABSENT, "Отсутствует"),
                (EXCUSED, "Уважительная причина")]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Ученик", on_delete=models.CASCADE,
                                related_name="attendance")
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.CASCADE)
    date = models.DateField("Дата", default=timezone.localdate)
    status = models.CharField("Статус", max_length=10, choices=STATUSES, default=PRESENT)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Отметил", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-date", "-id"]
        unique_together = [("student", "subject", "date")]
        verbose_name = "Посещаемость"
        verbose_name_plural = "Посещаемость"

    def __str__(self):
        return f"{self.student} · {self.date} · {self.get_status_display()}"

class Announcement(models.Model):
    school_class = models.ForeignKey(SchoolClass, verbose_name="Класс", null=True, blank=True,
                                     on_delete=models.CASCADE, related_name="announcements",
                                     help_text="Пусто: объявление для всей школы")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")
    title = models.CharField("Заголовок", max_length=150)
    text = models.TextField("Текст")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"

    def __str__(self):
        return "%s · %s" % (self.school_class or "Вся школа", self.title)
