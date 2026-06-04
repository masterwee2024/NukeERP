"""Core admin configuration — custom AdminSite with company filtering and branding."""

import csv
from io import StringIO

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path

from apps.core.models import (
    AuditLog,
    Company,
    Menu,
    MenuRole,
    Permission,
    Role,
    RolePermission,
    User,
    UserCompany,
    UserRole,
)

# ── Custom Admin Site ────────────────────────────────────────────


class PyERPAdminSite(AdminSite):
    """Custom admin site with pyERP branding and company filtering."""

    site_header = "pyERP Administration"
    site_title = "pyERP Admin"
    index_title = "Dashboard"

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        for app in app_list:
            if app.get("app_label") == "core":
                app["name"] = "pyERP Core"
        return app_list

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["company_count"] = Company.objects.count()
        extra_context["user_count"] = User.objects.count()
        extra_context["audit_log_count"] = AuditLog.objects.count()
        extra_context["role_count"] = Role.objects.count()
        return super().index(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        context = {
            "title": "Dashboard",
            "company_count": Company.objects.count(),
            "user_count": User.objects.count(),
            "audit_log_count": AuditLog.objects.count(),
            "role_count": Role.objects.count(),
            "site_header": self.site_header,
            "site_title": self.site_title,
            "has_permission": self.has_permission(request),
        }
        return render(request, "admin/dashboard.html", context)


admin_site = PyERPAdminSite(name="pyerp_admin")


# ── Company-Filtering Mixin ──────────────────────────────────────


class CompanyFilterMixin:
    """Mixin that filters querysets by the user's company.

    Superusers see all data. Non-superusers see only records
    belonging to companies they have access to.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or not request.user.is_authenticated:
            return qs
        company_ids = list(
            UserCompany.objects.filter(user=request.user).values_list(
                "company_id", flat=True
            )
        )
        if hasattr(self.model, "company_id"):
            return qs.filter(company_id__in=company_ids)
        if hasattr(self.model, "company"):
            return qs.filter(company__in=company_ids)
        if self.model is Company:
            return qs.filter(id__in=company_ids)
        return qs

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        if not request.user.is_authenticated:
            return False
        return UserCompany.objects.filter(user=request.user).exists()

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.user.is_authenticated:
            return False
        return UserCompany.objects.filter(user=request.user).exists()


# ── Custom Actions ───────────────────────────────────────────────


def export_as_csv(modeladmin, request, queryset):
    """Export selected records as CSV."""
    meta = modeladmin.model._meta
    field_names = [f.name for f in meta.fields]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow(
            [
                str(getattr(obj, name)) if getattr(obj, name) is not None else ""
                for name in field_names
            ]
        )

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{meta.db_table}.csv"'
    return response


export_as_csv.short_description = "Export selected as CSV"


def bulk_activate(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"Activated {updated} record(s).")


bulk_activate.short_description = "Activate selected"


def bulk_deactivate(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"Deactivated {updated} record(s).")


bulk_deactivate.short_description = "Deactivate selected"


# ── Model Admins ─────────────────────────────────────────────────


@admin.register(Company, site=admin_site)
class CompanyAdmin(CompanyFilterMixin, admin.ModelAdmin):
    list_display = ("name", "code", "parent", "is_group", "is_active")
    list_filter = ("is_active", "is_group")
    search_fields = ("name", "code")
    actions = [export_as_csv, bulk_activate, bulk_deactivate]
    fieldsets = (
        (None, {"fields": ("name", "code", "parent", "is_group", "is_active")}),
        (
            "Contact",
            {
                "fields": (
                    "phone",
                    "email",
                    "address",
                    "city",
                    "state",
                    "postcode",
                    "country",
                )
            },
        ),
        ("Registration", {"fields": ("registration_no", "sst_no")}),
        ("Defaults", {"fields": ("base_currency",)}),
    )


@admin.register(User, site=admin_site)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    actions = [export_as_csv, bulk_activate, bulk_deactivate]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Company", {"fields": ("current_company",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ["permission"]


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    autocomplete_fields = ["role"]


class UserCompanyInline(admin.TabularInline):
    model = UserCompany
    extra = 1
    autocomplete_fields = ["company"]


@admin.register(Role, site=admin_site)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_system")
    list_filter = ("is_active", "is_system")
    search_fields = ("name",)
    actions = [export_as_csv, bulk_activate, bulk_deactivate]
    fieldsets = ((None, {"fields": ("name", "description", "is_active", "is_system")}),)
    inlines = [RolePermissionInline]


@admin.register(Permission, site=admin_site)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "module", "action", "description")
    list_filter = ("module", "action")
    search_fields = ("codename", "description")
    actions = [export_as_csv]


@admin.register(Menu, site=admin_site)
class MenuAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "module",
        "parent",
        "level",
        "sort_order",
        "is_active",
    )
    list_filter = ("is_active", "module", "level")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    actions = [export_as_csv, bulk_activate, bulk_deactivate]
    list_editable = ("sort_order", "is_active")


class MenuRoleInline(admin.TabularInline):
    model = MenuRole
    extra = 1
    autocomplete_fields = ["role"]


@admin.register(MenuRole, site=admin_site)
class MenuRoleAdmin(admin.ModelAdmin):
    list_display = ("menu", "role")
    list_filter = ("role",)


@admin.register(UserCompany, site=admin_site)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "is_default")
    list_filter = ("company", "is_default")
    autocomplete_fields = ["user", "company"]
    actions = [export_as_csv]


@admin.register(UserRole, site=admin_site)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    autocomplete_fields = ["user", "role"]
    actions = [export_as_csv]


@admin.register(RolePermission, site=admin_site)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")
    list_filter = ("role",)
    autocomplete_fields = ["role", "permission"]
    actions = [export_as_csv]


@admin.register(AuditLog, site=admin_site)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "category",
        "action",
        "model_name",
        "record_id",
        "user",
        "company",
    )
    list_filter = ("category", "action", "model_name")
    search_fields = ("model_name", "record_id", "user__email")
    date_hierarchy = "timestamp"
    readonly_fields = (
        "model_name",
        "record_id",
        "action",
        "category",
        "changes",
        "metadata",
        "user",
        "ip_address",
        "company",
        "timestamp",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
