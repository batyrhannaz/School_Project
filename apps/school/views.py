from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.accounts.models import Profile
from apps.accounts.notify import guardians_and_student, notify
from apps.accounts.roles import class_of, role_of
from apps.library.models import Loan
from .forms import AnnouncementForm, GradeForm, HomeworkForm
from .models import WEEKDAYS, Announcement, Attendance, Grade, Homework, Lesson, SchoolClass, Subject
from .notify import notify_grade

User = get_user_model()
WEEKDAY_NAMES = dict(WEEKDAYS)


def pick_child(request):
    children = list(request.user.profile.children.all())
    cid = request.GET.get("child", "")
    child = next((c for c in children if str(c.pk) == cid), None)
    if child is None:
        default = request.user.profile.default_child
        child = default if default in children else (children[0] if children else None)
    return children, child


def teacher_classes(user, role):
    if role == "staff":
        return SchoolClass.objects.all()
    qs = SchoolClass.objects.filter(Q(teacher=user) | Q(lessons__teacher=user)).distinct()
    return qs if qs.exists() else SchoolClass.objects.all()


def only_teachers(user):
    if role_of(user) not in ("teacher", "staff"):
        raise PermissionDenied

def announcements_for(user, role):
    """Объявления, которые видит пользователь: для всей школы + для его классов (+ свои, если учитель)."""
    qs = Announcement.objects.select_related("school_class", "author")
    if role == "staff":
        return qs
    class_ids = []
    if role == "student":
        cls = class_of(user)
        class_ids = [cls.pk] if cls else []
    elif role == "parent":
        class_ids = [c.pk for c in (class_of(child) for child in user.profile.children.all()) if c]
    elif role == "teacher":
        class_ids = list(teacher_classes(user, role).values_list("pk", flat=True))
    cond = Q(school_class__isnull=True) | Q(school_class_id__in=class_ids)
    if role == "teacher":
        cond |= Q(author=user)
    return qs.filter(cond)

@login_required
def cabinet(request):
    user, role = request.user, role_of(request.user)
    today = timezone.localdate()
    ctx = {"today": today, "announcements": announcements_for(user, role)[:3]}
    if role == "student":
        cls = class_of(user)
        ctx["school_class"] = cls
        ctx["today_lessons"] = (Lesson.objects.filter(school_class=cls, weekday=today.isoweekday())
                                .select_related("subject") if cls else [])
        ctx["latest_grades"] = Grade.objects.filter(student=user).select_related("subject")[:5]
        ctx["on_hand"] = Loan.objects.filter(user=user, returned_at__isnull=True).select_related("copy__book")
        ctx["homework_next"] = (Homework.objects.filter(school_class=cls, due_date__gte=today)
                                .select_related("subject").order_by("due_date")[:4] if cls else [])
    elif role == "teacher":
        ctx["today_lessons"] = (Lesson.objects.filter(teacher=user, weekday=today.isoweekday())
                                .select_related("subject", "school_class"))
        ctx["my_classes"] = SchoolClass.objects.filter(Q(teacher=user) | Q(lessons__teacher=user)).distinct()
        ctx["given"] = Grade.objects.filter(teacher=user).select_related("subject", "student")[:5]
    elif role == "parent":
        cards = []
        for c in user.profile.children.all():
            qs = Grade.objects.filter(student=c)
            cls = class_of(c)
            cards.append({
                "child": c, "school_class": cls,
                "avg": qs.aggregate(a=Avg("value"))["a"],
                "latest": qs.select_related("subject")[:3],
                "books": Loan.objects.filter(user=c, returned_at__isnull=True).count(),
                "homework": Homework.objects.filter(school_class=cls, due_date__gte=today).count() if cls else 0,
            })
        ctx["cards"] = cards
    elif role == "librarian":
        active = Loan.objects.filter(returned_at__isnull=True)
        overdue = active.filter(due_date__lt=today)
        ctx["active_count"] = active.count()
        ctx["overdue_count"] = overdue.count()
        ctx["overdue"] = overdue.select_related("user", "copy__book").order_by("due_date")[:5]
    return render(request, "school/cabinet.html", ctx)



@login_required
def schedule(request):
    user, role = request.user, role_of(request.user)
    children, child, cls = [], None, None
    if role == "student":
        cls = class_of(user)
        lessons = Lesson.objects.filter(school_class=cls) if cls else Lesson.objects.none()
    elif role == "parent":
        children, child = pick_child(request)
        cls = class_of(child) if child else None
        lessons = Lesson.objects.filter(school_class=cls) if cls else Lesson.objects.none()
    elif role == "teacher":
        lessons = Lesson.objects.filter(teacher=user)
    else:
        lessons = Lesson.objects.all()
    lessons = lessons.select_related("subject", "school_class", "teacher")
    by_day = {n: [] for n, _ in WEEKDAYS}
    for lesson in lessons:
        by_day[lesson.weekday].append(lesson)
    return render(request, "school/schedule.html", {
        "days": [(name, by_day[n]) for n, name in WEEKDAYS],
        "today_name": WEEKDAY_NAMES.get(timezone.localdate().isoweekday()),
        "children": children, "child": child, "school_class": cls,
    })


@login_required
def grades(request):
    user, role = request.user, role_of(request.user)
    children, student = [], None
    if role == "student":
        student = user
    elif role == "parent":
        children, student = pick_child(request)
    else:
        return redirect("add_grade")
    by_subject = {}
    if student:
        for g in Grade.objects.filter(student=student).select_related("subject").order_by("date", "id"):
            by_subject.setdefault(g.subject, []).append(g)
    rows = [(s, gl, round(sum(x.value for x in gl) / len(gl), 2)) for s, gl in by_subject.items()]
    return render(request, "school/grades.html", {"rows": rows, "children": children, "child": student if role == "parent" else None})


@login_required
def classes(request):
    user, role = request.user, role_of(request.user)
    if role not in ("teacher", "staff"):
        raise PermissionDenied
    qs = SchoolClass.objects.all() if role == "staff" else SchoolClass.objects.filter(
        Q(teacher=user) | Q(lessons__teacher=user)).distinct()
    items = [(c, c.students.select_related("user").order_by("user__last_name", "user__username")) for c in qs]
    return render(request, "school/classes.html", {"items": items})


@login_required
def add_grade(request):
    only_teachers(request.user)
    initial = {}
    if request.GET.get("student", "").isdigit():
        initial["student"] = int(request.GET["student"])
    profile = getattr(request.user, "profile", None)
    default_class = None if initial else (profile.default_class if profile else None)
    form = GradeForm(request.POST or None, initial=initial, school_class=default_class)
    if request.method == "POST" and form.is_valid():
        grade = form.save(commit=False)
        grade.teacher = request.user
        grade.save()
        notify_grade(grade)
        notify(guardians_and_student(grade.student), "Новая оценка: %s — %s" % (grade.subject, grade.value),
               "%s?child=%d" % (reverse("grades"), grade.student.pk))
        messages.success(request, "Оценка выставлена: %s — %s" % (grade.student, grade.value))
        return redirect("add_grade")
    recent = Grade.objects.filter(teacher=request.user).select_related("student", "subject")[:8]
    return render(request, "school/grade_form.html", {"form": form, "recent": recent})


# ---------- домашние задания ----------
@login_required
def homework(request):
    user, role = request.user, role_of(request.user)
    today = timezone.localdate()
    children, child = [], None
    if role in ("student", "parent"):
        if role == "parent":
            children, child = pick_child(request)
            cls = class_of(child) if child else None
        else:
            cls = class_of(user)
        qs = Homework.objects.filter(school_class=cls) if cls else Homework.objects.none()
    elif role == "teacher":
        qs = Homework.objects.filter(teacher=user)
    elif role == "staff":
        qs = Homework.objects.all()
    else:
        raise PermissionDenied
    qs = qs.select_related("subject", "school_class", "teacher")
    return render(request, "school/homework.html", {
        "upcoming": qs.filter(due_date__gte=today).order_by("due_date"),
        "past": qs.filter(due_date__lt=today).order_by("-due_date")[:10],
        "children": children, "child": child, "today": today,
        "can_edit": role in ("teacher", "staff"),
    })


@login_required
def add_homework(request):
    only_teachers(request.user)
    role = role_of(request.user)
    today = timezone.localdate()
    form = HomeworkForm(request.POST or None, request.FILES or None, classes=teacher_classes(request.user, role),
                        initial={"due_date": today + timedelta(days=1)})
    if request.method == "POST" and form.is_valid():
        hw = form.save(commit=False)
        hw.teacher = request.user
        hw.save()
        students = list(User.objects.filter(profile__school_class=hw.school_class, profile__role="student"))
        parents = [p.user for p in Profile.objects.filter(children__in=students).select_related("user").distinct()]
        notify(students + parents, "Домашнее задание: %s (до %s)" % (hw.subject, hw.due_date.strftime("%d.%m")),
               reverse("homework"))
        messages.success(request, "Задание добавлено для класса %s." % hw.school_class)
        return redirect("homework")
    return render(request, "school/homework_form.html", {"form": form})


@login_required
@require_POST
def delete_homework(request, pk):
    hw = get_object_or_404(Homework, pk=pk)
    if role_of(request.user) != "staff" and hw.teacher_id != request.user.pk:
        raise PermissionDenied
    hw.delete()
    messages.success(request, "Задание удалено.")
    return redirect("homework")


# ---------- посещаемость ----------
@login_required
def attendance(request):
    user, role = request.user, role_of(request.user)
    children, student = [], None
    if role == "student":
        student = user
    elif role == "parent":
        children, student = pick_child(request)
    else:
        return redirect("mark_attendance")
    records = list(Attendance.objects.filter(student=student).select_related("subject")) if student else []
    counts = {k: 0 for k, _ in Attendance.STATUSES}
    for r in records:
        counts[r.status] += 1
    return render(request, "school/attendance.html", {
        "summary": [(label, counts[k], k) for k, label in Attendance.STATUSES],
        "problems": [r for r in records if r.status != Attendance.PRESENT][:30],
        "total": len(records),
        "children": children, "child": student if role == "parent" else None,
    })


@login_required
def mark_attendance(request):
    only_teachers(request.user)
    role = role_of(request.user)
    today = timezone.localdate()
    classes_qs = teacher_classes(request.user, role)
    data = request.POST if request.method == "POST" else request.GET
    cls = classes_qs.filter(pk=data["class"]).first() if data.get("class", "").isdigit() else None
    subject = Subject.objects.filter(pk=data["subject"]).first() if data.get("subject", "").isdigit() else None
    date = parse_date(data.get("date", "")) or today
    students, existing = [], {}
    if cls and subject:
        students = list(User.objects.filter(profile__school_class=cls, profile__role="student")
                        .order_by("last_name", "username"))
        existing = {a.student_id: a.status for a in
                    Attendance.objects.filter(subject=subject, date=date, student__in=students)}
        for s in students:
            s.current = existing.get(s.pk, Attendance.PRESENT)
    if request.method == "POST" and students:
        valid = dict(Attendance.STATUSES)
        for s in students:
            status = request.POST.get("status_%d" % s.pk)
            if status not in valid:
                continue
            Attendance.objects.update_or_create(student=s, subject=subject, date=date,
                                                defaults={"status": status, "teacher": request.user})
            if status in (Attendance.ABSENT, Attendance.LATE) and existing.get(s.pk) != status:
                notify(guardians_and_student(s), "%s: %s, %s (%s)" % (
                    valid[status], s.get_full_name() or s.username, subject, date.strftime("%d.%m")),
                    "%s?child=%d" % (reverse("attendance"), s.pk))
        messages.success(request, "Посещаемость сохранена.")
        return redirect("%s?class=%d&subject=%d&date=%s" % (reverse("mark_attendance"), cls.pk, subject.pk, date.isoformat()))
    return render(request, "school/attendance_mark.html", {
        "classes": classes_qs, "subjects": Subject.objects.all(), "cls": cls, "subject": subject,
        "date": date, "students": students, "statuses": Attendance.STATUSES,
    })

# ---------- объявления ----------
@login_required
def announcements(request):
    user, role = request.user, role_of(request.user)
    return render(request, "school/announcements.html", {
        "items": announcements_for(user, role)[:50],
        "can_edit": role in ("teacher", "staff"),
        "is_staff_role": role == "staff",
    })


@login_required
def add_announcement(request):
    only_teachers(request.user)
    role = role_of(request.user)
    form = AnnouncementForm(request.POST or None, classes=teacher_classes(request.user, role),
                            allow_school=(role == "staff"))
    if request.method == "POST" and form.is_valid():
        ann = form.save(commit=False)
        ann.author = request.user
        ann.save()
        if ann.school_class:
            students = list(User.objects.filter(profile__school_class=ann.school_class, profile__role="student"))
            parents = [p.user for p in Profile.objects.filter(children__in=students).select_related("user").distinct()]
            recipients = students + parents
        else:
            recipients = list(User.objects.filter(is_active=True, profile__role__in=["student", "parent", "teacher"])
                              .exclude(pk=request.user.pk))
        notify(recipients, "Объявление: %s" % ann.title, reverse("announcements"))
        messages.success(request, "Объявление опубликовано: %s." % (ann.school_class or "для всей школы"))
        return redirect("announcements")
    return render(request, "school/announcement_form.html", {"form": form})


@login_required
@require_POST
def delete_announcement(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if role_of(request.user) != "staff" and ann.author_id != request.user.pk:
        raise PermissionDenied
    ann.delete()
    messages.success(request, "Объявление удалено.")
    return redirect("announcements")