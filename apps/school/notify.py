from django.core.mail import send_mass_mail


def notify_grade(grade):
    """Письмо ученику и его родителям о новой оценке (если почта привязана и уведомления включены)."""
    student = grade.student
    name = student.get_full_name() or student.username
    to = []
    sp = getattr(student, "profile", None)
    if student.email and (sp is None or sp.notify_grades):
        to.append(student.email)
    for parent_profile in student.parents.select_related("user"):
        if parent_profile.notify_grades and parent_profile.user.email:
            to.append(parent_profile.user.email)
    to = list(dict.fromkeys(to))
    if not to:
        return
    text = "Новая оценка\n\nУченик: %s\nПредмет: %s\nОценка: %s\nДата: %s\n%s" % (
        name, grade.subject, grade.value, grade.date.strftime("%d.%m.%Y"),
        ("Комментарий: %s\n" % grade.comment) if grade.comment else "")
    subject = "Новая оценка: %s, %s" % (name, grade.value)
    send_mass_mail([(subject, text, None, [addr]) for addr in to], fail_silently=True)
