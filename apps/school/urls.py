from django.urls import path
from . import views

urlpatterns = [
    path("", views.cabinet, name="cabinet"),
    path("schedule/", views.schedule, name="schedule"),
    path("grades/", views.grades, name="grades"),
    path("classes/", views.classes, name="classes"),
    path("add-grade/", views.add_grade, name="add_grade"),
    path("homework/", views.homework, name="homework"),
    path("homework/add/", views.add_homework, name="add_homework"),
    path("homework/<int:pk>/delete/", views.delete_homework, name="delete_homework"),
    path("attendance/", views.attendance, name="attendance"),
    path("attendance/mark/", views.mark_attendance, name="mark_attendance"),
    path("announcements/", views.announcements, name="announcements"),
    path("announcements/add/", views.add_announcement, name="add_announcement"),
    path("announcements/<int:pk>/delete/", views.delete_announcement, name="delete_announcement"),
]
