from datetime import timedelta

from django.core.mail import send_mass_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.library.models import Loan


class Command(BaseCommand):
    help = "Отправляет напоминания о книгах, срок возврата которых завтра или уже прошёл"

    def handle(self, *args, **options):
        today = timezone.localdate()
        loans = Loan.objects.filter(returned_at__isnull=True, due_date__lte=today + timedelta(days=1)) \
            .select_related("user", "copy__book")
        by_user = {}
        for loan in loans:
            by_user.setdefault(loan.user, []).append(loan)
        mails = []
        for user, items in by_user.items():
            profile = getattr(user, "profile", None)
            if not user.email or (profile and not profile.notify_books):
                continue
            lines = "\n".join("- %s (вернуть до %s%s)" % (
                l.copy.book.title, l.due_date.strftime("%d.%m.%Y"), ", просрочена" if l.due_date < today else "")
                for l in items)
            mails.append(("Напоминание о возврате книг",
                          "Здравствуйте!\n\nПожалуйста, верните книги в школьную библиотеку:\n%s\n\nСпасибо!" % lines,
                          None, [user.email]))
        send_mass_mail(mails, fail_silently=True)
        self.stdout.write(self.style.SUCCESS("Отправлено напоминаний: %d" % len(mails)))
