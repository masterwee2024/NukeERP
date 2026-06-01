"""Core admin configuration."""

from django.contrib import admin

from apps.core.models import Menu, MenuRole


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "module", "level", "sort_order", "is_active")
    list_filter = ("is_active", "module", "level")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuRole)
class MenuRoleAdmin(admin.ModelAdmin):
    list_display = ("menu", "role")
    list_filter = ("role",)
