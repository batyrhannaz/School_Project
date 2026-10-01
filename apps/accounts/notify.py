from .models import Notification


def notify(users, text, url=""):
    """Уведомления внутри сайта (колокольчик в меню)."""
    seen, objs = set(), []
    for u in users:
        if u is not None and u.pk not in seen:
            seen.add(u.pk)
            objs.append(Notification(user=u, text=text[:200], url=url))
    Notification.objects.bulk_create(objs)


def guardians_and_student(student):
    return [student] + [p.user for p in student.parents.select_related("user")]
