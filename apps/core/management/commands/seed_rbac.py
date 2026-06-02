"""Seed command to create default roles and permissions."""

from django.core.management.base import BaseCommand

from apps.core.models import (
    ACTION_CHOICES,
    MODULE_CHOICES,
    Permission,
    Role,
    RolePermission,
)


class Command(BaseCommand):
    help = "Create default roles and permissions for development"

    def handle(self, *args, **options):
        self._create_permissions()
        self._create_roles()
        self._assign_permissions()
        self.stdout.write(self.style.SUCCESS("Default roles and permissions created"))

    def _create_permissions(self):
        created = 0
        for module, _ in MODULE_CHOICES:
            for action, _ in ACTION_CHOICES:
                codename = f"{module}_{action}"
                _, was_created = Permission.objects.get_or_create(
                    codename=codename,
                    defaults={
                        "module": module,
                        "action": action,
                        "description": f"{action} in {module}",
                    },
                )
                if was_created:
                    created += 1
        self.stdout.write(
            f"  Permissions: {created} created, {Permission.objects.count()} total"
        )

    def _create_roles(self):
        roles_data = [
            ("Admin", "Full system access", True),
            ("Finance Manager", "Manage financial operations", False),
            ("Accountant", "Daily accounting tasks", False),
            ("SCM Manager", "Manage supply chain", False),
            ("Sales", "CRM and sales operations", False),
            ("HR Manager", "Manage HR operations", False),
            ("Employee", "Basic self-service access", False),
        ]

        created = 0
        for name, desc, is_system in roles_data:
            _, was_created = Role.objects.get_or_create(
                name=name,
                defaults={"description": desc, "is_system": is_system},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Roles: {created} created, {Role.objects.count()} total")

    def _assign_permissions(self):
        """Assign all permissions to Admin role, assign subset to other roles."""
        admin = Role.objects.get(name="Admin")
        for perm in Permission.objects.all():
            RolePermission.objects.get_or_create(role=admin, permission=perm)

        finance_manager = Role.objects.filter(name="Finance Manager").first()
        if finance_manager:
            for perm in Permission.objects.filter(module="financial"):
                RolePermission.objects.get_or_create(
                    role=finance_manager, permission=perm
                )
            for action in ["view", "export"]:
                for perm in Permission.objects.filter(
                    action=action, module__in=["scm", "crm", "hrm"]
                ):
                    RolePermission.objects.get_or_create(
                        role=finance_manager, permission=perm
                    )

        accountant = Role.objects.filter(name="Accountant").first()
        if accountant:
            for perm in Permission.objects.filter(
                module="financial", action__in=["view", "create", "update"]
            ):
                RolePermission.objects.get_or_create(role=accountant, permission=perm)

        scm_manager = Role.objects.filter(name="SCM Manager").first()
        if scm_manager:
            for perm in Permission.objects.filter(module="scm"):
                RolePermission.objects.get_or_create(role=scm_manager, permission=perm)
            for action in ["view", "export"]:
                for perm in Permission.objects.filter(
                    action=action, module__in=["financial", "crm"]
                ):
                    RolePermission.objects.get_or_create(
                        role=scm_manager, permission=perm
                    )

        sales = Role.objects.filter(name="Sales").first()
        if sales:
            for perm in Permission.objects.filter(module="crm"):
                RolePermission.objects.get_or_create(role=sales, permission=perm)
            for perm in Permission.objects.filter(
                module="financial", action__in=["view"]
            ):
                RolePermission.objects.get_or_create(role=sales, permission=perm)

        hr_manager = Role.objects.filter(name="HR Manager").first()
        if hr_manager:
            for perm in Permission.objects.filter(module="hrm"):
                RolePermission.objects.get_or_create(role=hr_manager, permission=perm)
            for perm in Permission.objects.filter(module="admin", action__in=["view"]):
                RolePermission.objects.get_or_create(role=hr_manager, permission=perm)

        employee = Role.objects.filter(name="Employee").first()
        if employee:
            for perm in Permission.objects.filter(module="hrm", action__in=["view"]):
                RolePermission.objects.get_or_create(role=employee, permission=perm)

        self.stdout.write("  Role-permission assignments created")
