from .models import Notification
from .roles import role_of


def role(request):
    user = request.user
    ctx = {"role": role_of(user)}
    if user.is_authenticated:
        ctx["unread"] = Notification.objects.filter(user=user, is_read=False).count()
    return ctx
