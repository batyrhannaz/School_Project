from .models import Loan


def loans_badge(request):
    if request.user.is_authenticated:
        return {"active_loans": Loan.objects.filter(user=request.user, returned_at__isnull=True).count()}
    return {}
