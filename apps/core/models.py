"""Core models — User, Menu, MenuRole, and base models."""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class ConcurrencyError(Exception):
    """Raised when optimistic locking detects a conflict."""

    pass


class ConcurrencyModel(models.Model):
    """Base model with concurrency control fields.

    Every model MUST inherit from this. Provides:
    - id: UUID primary key
    - created_at: auto-set on creation
    - updated_at: auto-updated on save
    - version: optimistic locking field (auto-increments on save)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = self.__class__.objects.get(pk=self.pk)
                if original.version != self.version:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )
                self.version += 1
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class UserManager(BaseUserManager):
    """Custom user manager with email as the login field."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(ConcurrencyModel, AbstractBaseUser, PermissionsMixin):
    """Custom user model with email-based login."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Multi-company support
    current_company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_users",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "core_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Company(ConcurrencyModel):
    """Company for multi-tenant architecture."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    registration_number = models.CharField(max_length=50, blank=True, default="")
    tax_number = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_company"
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class UserCompany(ConcurrencyModel):
    """Junction table linking users to companies."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_companies"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="company_users"
    )

    class Meta:
        db_table = "core_user_company"
        unique_together = ("user", "company")
        verbose_name = "User Company"
        verbose_name_plural = "User Companies"

    def __str__(self):
        return f"{self.user.email} → {self.company.name}"


class Menu(ConcurrencyModel):
    """Database-driven navigation menu item."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Lucide icon name (e.g. 'LayoutDashboard', 'DollarSign')",
    )
    url = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Route path (e.g. '/app/financial/gl')",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)
    permission_codename = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Required permission codename (e.g. 'view_journalentry')",
    )
    is_active = models.BooleanField(default=True)
    level = models.PositiveIntegerField(
        default=0,
        help_text="Nesting level: 0=root, 1=sub, 2=sub-sub",
    )
    module = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Module grouping tag (e.g. 'financial', 'scm')",
    )

    class Meta:
        db_table = "core_menu"
        ordering = ["sort_order", "name"]
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return self.name

    def get_ancestors(self):
        """Return list of ancestor menus from root to parent."""
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_descendants(self, include_self=False):
        """Return all descendant menus (depth-first)."""
        descendants = []
        if include_self:
            descendants.append(self)
        for child in self.children.filter(is_active=True).order_by("sort_order"):
            descendants.extend(child.get_descendants(include_self=True))
        return descendants


class MenuRole(ConcurrencyModel):
    """Junction table linking menus to roles."""

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="menu_roles")
    role = models.ForeignKey(
        "auth.Group",
        on_delete=models.CASCADE,
        related_name="menu_roles",
    )

    class Meta:
        db_table = "core_menu_role"
        unique_together = ("menu", "role")
        verbose_name = "Menu Role"
        verbose_name_plural = "Menu Roles"

    def __str__(self):
        return f"{self.menu.name} → {self.role.name}"
