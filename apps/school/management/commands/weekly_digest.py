from datetime import timedelta

from django.core.mail import send_mass_mail
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from apps.accounts.models import Profile
from apps.library.models import Loan
from apps.school.models import Grade


class Command(BaseCommand):
    help = "Отправляет родителям и ученикам сводку за неделю (оценки и книги), если включено в настройках"

    def handle(self, *args, **options):
        since = timezone.localdate() - timedelta(days=7)
        mails = []
        for p in Profile.objects.filter(notify_digest=True).select_related("user"):
            user = p.user
            if not user.email or not user.is_active:
                continue
            if p.role == "parent":
                students = list(p.children.all())
            elif p.role == "student":
                students = [user]
            else:
                continue
            blocks = []
            for s in students:
                grades = Grade.objects.filter(student=s, date__gte=since).select_related("subject")
                g_lines = "\n".join("  %s: %s (%s)" % (g.subject, g.value, g.date.strftime("%d.%m")) for g in grades) \
                    or "  оценок за неделю нет"
                avg = Grade.objects.filter(student=s).aggregate(a=Avg("value"))["a"]
                loans = Loan.objects.filter(user=s, returned_at__isnull=True).select_related("copy__book")
                b_lines = "\n".join("  %s (до %s)" % (l.copy.book.title, l.due_date.strftime("%d.%m")) for l in loans) or "  нет"
                blocks.append("%s\nОценки за неделю:\n%s\nСредний балл: %s\nКниги на руках:\n%s" % (
                    s.get_full_name() or s.username, g_lines, round(avg, 2) if avg else "—", b_lines))
            if blocks:
                mails.append(("Сводка за неделю", "Здравствуйте!\n\n" + "\n\n".join(blocks), None, [user.email]))
        send_mass_mail(mails, fail_silently=True)
        self.stdout.write(self.style.SUCCESS("Отправлено сводок: %d" % len(mails)))
