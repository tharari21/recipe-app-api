"""
Django admin customization
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# If we change language in configuration so anywhere you add this import it will translate accordingly
# _ is standard django convention but we can call it anything
from django.utils.translation import gettext_lazy as _

from core import models

# To edit the view of admin page for users we must extend from BaseUserAdmin
class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""
    ordering = ["id"]
    list_display = ["email", "name"]
    fieldsets = (
        (None, {'fields': ('email','password')}),
        (
            _("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser")}
        ),
        (_("Important dates"), {"fields": ("last_login",)}),
    )
    readonly_fields = ["last_login"]
    add_fieldsets = (

        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "password1",
                "password2",
                "name",
                "is_active",
                "is_staff",
                "is_superuser"
            )
        }),

    )



admin.site.register(models.User, UserAdmin)
# Default options no need to change the look of admin page
admin.site.register(models.Recipe)
admin.site.register(models.Tag)
