from django.contrib import admin
from .models import Book, BookCopy, Category, LibrarySettings, Loan


class CopyInline(admin.TabularInline):
    model = BookCopy
    extra = 1


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category")
    search_fields = ("title", "author")
    list_filter = ("category",)
    inlines = [CopyInline]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("copy", "user", "issued_at", "due_date", "returned_at")
    list_filter = ("returned_at",)
    search_fields = ("user__username", "copy__book__title")

    def save_model(self, request, obj, form, change):
        if not obj.issued_by:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Category)


@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not LibrarySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
