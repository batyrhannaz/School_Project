from django.contrib import admin
from .models import Attendance, Grade, Homework, Lesson, SchoolClass, Subject

admin.site.register(SchoolClass)
admin.site.register(Subject)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("school_class", "weekday", "number", "subject", "teacher", "room")
    list_filter = ("school_class", "weekday")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "value", "date", "teacher")
    list_filter = ("subject", "date")
    search_fields = ("student__username", "student__last_name")


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ("school_class", "subject", "due_date", "teacher")
    list_filter = ("school_class", "subject")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "date", "status")
    list_filter = ("status", "date")
    search_fields = ("student__username", "student__last_name")
