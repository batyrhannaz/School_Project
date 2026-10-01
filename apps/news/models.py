from django.db import models


class News(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    text = models.TextField("Текст")
    image = models.ImageField("Фото", upload_to="news/", blank=True)
    created = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title
