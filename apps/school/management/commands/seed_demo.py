from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import Profile
from apps.library.models import Book, BookCopy, Category, Loan
from apps.news.models import News
from apps.school.models import Attendance, Grade, Homework, Lesson, SchoolClass, Subject
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


def make_user(username, first, last, role):
    user, created = User.objects.get_or_create(username=username, defaults={"first_name": first, "last_name": last})
    if created:
        user.set_password("demo12345")
        user.save()
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": role})
    return user, profile


class Command(BaseCommand):
    help = "Создаёт демо-данные: teacher1, parent1, student1 (пароль demo12345)"

    def handle(self, *args, **opts):
        teacher, _ = make_user("teacher1", "Айгуль", "Сыдыкова", "teacher")
        parent, pp = make_user("parent1", "Марат", "Ибраимов", "parent")
        student, sp = make_user("student1", "Айбек", "Ибраимов", "student")

        cls, _ = SchoolClass.objects.get_or_create(name="9А", defaults={"teacher": teacher})
        sp.school_class = cls
        sp.save()
        pp.children.add(student)

        names = ["Математика", "Кыргыз тили", "Русский язык", "Физика", "История"]
        subjects = [Subject.objects.get_or_create(name=n)[0] for n in names]
        for day in range(1, 6):
            for num in range(1, 5):
                Lesson.objects.get_or_create(
                    school_class=cls, weekday=day, number=num,
                    defaults={"subject": subjects[(day + num) % 5], "teacher": teacher, "room": str(100 + num)})

        if not Grade.objects.exists():
            for i, subj in enumerate(subjects):
                for v in (5, 4, 5 if i % 2 else 3):
                    Grade.objects.create(student=student, subject=subj, value=v, teacher=teacher)

        cat, _ = Category.objects.get_or_create(name="Классика")
        book, _ = Book.objects.get_or_create(title="Манас", defaults={"author": "Народный эпос", "category": cat,
                                                                      "description": "Кыргызский героический эпос."})
        copy, _ = BookCopy.objects.get_or_create(book=book, inventory_number="M-001")
        BookCopy.objects.get_or_create(book=book, inventory_number="M-002")
        if not Loan.objects.exists():
            Loan.objects.create(copy=copy, user=student, due_date=timezone.localdate() + timedelta(days=14))
        if not News.objects.exists():
            News.objects.create(title="Начало нового учебного года", text="Добро пожаловать в новый учебный год!")

        make_user("librarian1", "Гульнара", "Осмонова", "librarian")
        if not Homework.objects.exists():
            Homework.objects.create(school_class=cls, subject=subjects[0], teacher=teacher,
                                    text="Параграф 12, упражнения 1–5.", due_date=timezone.localdate() + timedelta(days=2))
        if not Attendance.objects.exists():
            Attendance.objects.create(student=student, subject=subjects[1], status="late", teacher=teacher)
        self.stdout.write(self.style.SUCCESS(
            "Готово. Логины: teacher1 / parent1 / student1 / librarian1, пароль: demo12345"))
