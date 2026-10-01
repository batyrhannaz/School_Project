from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from apps.library.models import Book
from apps.news.models import News


def home(request):
    return render(request, "core/home.html", {
        "latest_news": News.objects.all()[:3],
        "books_count": Book.objects.count(),
        "news_count": News.objects.count(),
    })


@require_POST
def set_lang(request):
    lang = request.POST.get("lang", "ru")
    lang = lang if lang in ("ru", "ky") else "ru"
    nxt = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    response = redirect(nxt)
    response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
    return response
