from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.notify import notify
from apps.accounts.roles import role_of
from .forms import BookForm, IssueForm
from .models import Book, BookCopy, Category, Loan


def only_librarian(user):
    if role_of(user) not in ("librarian", "staff"):
        raise PermissionDenied


def catalog(request):
    books = Book.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    if q:
        books = books.filter(Q(title__icontains=q) | Q(author__icontains=q))
    if cat.isdigit():
        books = books.filter(category_id=int(cat))
    return render(request, "library/catalog.html", {
        "books": books, "categories": Category.objects.all(), "q": q, "cat": cat,
    })


def book_detail(request, pk):
    return render(request, "library/book_detail.html", {"book": get_object_or_404(Book, pk=pk)})


@login_required
def my_loans(request):
    readers = [request.user]
    profile = getattr(request.user, "profile", None)
    is_parent = bool(profile and profile.role == "parent")
    if is_parent:
        readers += list(profile.children.all())
    loans = Loan.objects.filter(user__in=readers).select_related("copy__book", "user")
    return render(request, "library/my_loans.html", {"loans": loans, "show_reader": is_parent})


@login_required
def desk(request):
    only_librarian(request.user)
    form = IssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        copy = cd["copy"]
        if copy.status != BookCopy.AVAILABLE:
            messages.error(request, "Этот экземпляр уже выдан.")
        else:
            loan = Loan(copy=copy, user=cd["reader"], issued_by=request.user)
            if cd["days"]:
                loan.due_date = timezone.localdate() + timedelta(days=cd["days"])
            loan.save()
            notify([loan.user], "Вам выдана книга «%s», вернуть до %s" % (copy.book.title, loan.due_date.strftime("%d.%m.%Y")),
                   "/library/my-loans/")
            messages.success(request, "Выдано: %s → %s" % (copy.book.title, loan.user.get_full_name() or loan.user.username))
        return redirect("desk")
    active = Loan.objects.filter(returned_at__isnull=True).select_related("user", "copy__book").order_by("due_date")
    return render(request, "library/desk.html", {"form": form, "active": active, "today": timezone.localdate()})


@login_required
@require_POST
def return_loan(request, pk):
    only_librarian(request.user)
    loan = get_object_or_404(Loan, pk=pk, returned_at__isnull=True)
    loan.returned_at = timezone.localdate()
    loan.save()
    messages.success(request, "Принято: %s" % loan.copy.book.title)
    return redirect(request.POST.get("next") or "desk")


@login_required
def debtors(request):
    only_librarian(request.user)
    today = timezone.localdate()
    loans = list(Loan.objects.filter(returned_at__isnull=True, due_date__lt=today)
                 .select_related("user", "copy__book").order_by("due_date"))
    for l in loans:
        l.days_over = (today - l.due_date).days
    return render(request, "library/debtors.html", {"loans": loans})


@login_required
def add_book(request):
    only_librarian(request.user)
    form = BookForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        book = form.save(commit=False)
        new_cat = form.cleaned_data["new_category"].strip()
        if new_cat:
            book.category = Category.objects.get_or_create(name=new_cat)[0]
        book.save()
        for i in range(1, form.cleaned_data["copies"] + 1):
            BookCopy.objects.create(book=book, inventory_number="K%d-%d" % (book.pk, i))
        messages.success(request, "Книга добавлена: %s (экземпляров: %d)" % (book.title, form.cleaned_data["copies"]))
        return redirect("add_book")
    return render(request, "library/book_form.html", {"form": form})
