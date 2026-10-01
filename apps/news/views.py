from django.shortcuts import get_object_or_404, render
from .models import News


def news_list(request):
    return render(request, "news/list.html", {"items": News.objects.all()})


def news_detail(request, pk):
    return render(request, "news/detail.html", {"item": get_object_or_404(News, pk=pk)})
