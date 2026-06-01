"""Core models — Menu, MenuRole, and base models."""

import uuid

from django.db import models


class ConcurrencyModel(models.Model):
    """Base model with concurrency control fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


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
