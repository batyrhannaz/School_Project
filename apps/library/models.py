from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField("Название", max_length=200)
    author = models.CharField("Автор", max_length=200)
    description = models.TextField("Описание", blank=True)
    cover = models.ImageField("Обложка", upload_to="covers/", blank=True)
    category = models.ForeignKey(Category, verbose_name="Категория", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="books")

    class Meta:
        ordering = ["title"]
        verbose_name = "Книга"
        verbose_name_plural = "Книги"

    def __str__(self):
        return f"{self.title} — {self.author}"

    @property
    def available_count(self):
        return self.copies.filter(status=BookCopy.AVAILABLE).count()


class BookCopy(models.Model):
    AVAILABLE, ON_LOAN, WRITTEN_OFF = "available", "on_loan", "written_off"
    STATUSES = [(AVAILABLE, "В наличии"), (ON_LOAN, "Выдана"), (WRITTEN_OFF, "Списана")]

    book = models.ForeignKey(Book, verbose_name="Книга", on_delete=models.CASCADE, related_name="copies")
    inventory_number = models.CharField("Инвентарный номер", max_length=50, unique=True)
    status = models.CharField("Статус", max_length=20, choices=STATUSES, default=AVAILABLE)

    class Meta:
        verbose_name = "Экземпляр"
        verbose_name_plural = "Экземпляры"

    def __str__(self):
        return f"{self.book.title} №{self.inventory_number}"


class LibrarySettings(models.Model):
    loan_days = models.PositiveSmallIntegerField("Срок выдачи по умолчанию, дней", default=14)

    class Meta:
        verbose_name = "Настройки библиотеки"
        verbose_name_plural = "Настройки библиотеки"

    def __str__(self):
        return "Настройки библиотеки"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class Loan(models.Model):
    copy = models.ForeignKey(BookCopy, verbose_name="Экземпляр", on_delete=models.PROTECT, related_name="loans")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Читатель",
                             on_delete=models.CASCADE, related_name="loans")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Выдал", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="+")
    issued_at = models.DateField("Дата выдачи", default=timezone.localdate)
    due_date = models.DateField("Вернуть до", blank=True,
                                help_text="Если оставить пустым, срок поставится по настройке библиотеки")
    returned_at = models.DateField("Дата возврата", null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "Выдача"
        verbose_name_plural = "Выдачи"

    def __str__(self):
        return f"{self.copy} → {self.user}"

    @property
    def is_overdue(self):
        return self.returned_at is None and self.due_date < timezone.localdate()

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = self.issued_at + timedelta(days=LibrarySettings.load().loan_days)
        super().save(*args, **kwargs)
        self.copy.status = BookCopy.AVAILABLE if self.returned_at else BookCopy.ON_LOAN
        self.copy.save(update_fields=["status"])
