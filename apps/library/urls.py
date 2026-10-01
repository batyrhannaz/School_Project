from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("book/<int:pk>/", views.book_detail, name="book_detail"),
    path("my-loans/", views.my_loans, name="my_loans"),
    path("desk/", views.desk, name="desk"),
    path("return/<int:pk>/", views.return_loan, name="return_loan"),
    path("debtors/", views.debtors, name="debtors"),
    path("add-book/", views.add_book, name="add_book"),
]
