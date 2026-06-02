"""Core models — User, Menu, MenuRole, and base models."""

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.core.mixins.models import ConcurrencyModel


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

    # Group hierarchy
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_group = models.BooleanField(default=False)

    # Address
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    postcode = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="MY")

    # Contact
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    # Branding
    logo = models.ImageField(upload_to="company_logos/", blank=True)

    # Localization
    base_currency = models.CharField(max_length=3, blank=True, default="MYR")
    date_format = models.CharField(max_length=20, blank=True, default="Y-m-d")
    timezone = models.CharField(max_length=50, blank=True, default="Asia/Kuala_Lumpur")

    # Fiscal year
    fiscal_year_start = models.DateField(null=True, blank=True)
    fiscal_year_end = models.DateField(null=True, blank=True)

    # Inter-company & forex GL accounts — add FK to financial.Account
    # once the Account model exists (T021 / T029c)

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
    is_default = models.BooleanField(default=False)

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


class PageConfig(ConcurrencyModel):
    """Database-driven page configuration."""

    PAGE_TYPES = [
        ("form", "Form"),
        ("list", "List"),
        ("detail", "Detail"),
        ("dashboard", "Dashboard"),
    ]

    LAYOUTS = [
        ("single", "Single Column"),
        ("two_column", "Two Column"),
        ("tabs", "Tabs"),
        ("wizard", "Wizard"),
    ]

    page_key = models.SlugField(max_length=100, unique=True)
    page_title = models.CharField(max_length=200)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPES)
    module = models.CharField(
        max_length=50,
        help_text="Module grouping (financial, scm, crm, mrp, hrm, admin)",
    )
    entity_model = models.CharField(
        max_length=100, blank=True, default="", help_text="Django model name"
    )
    api_endpoint = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)

    # Layout settings
    layout = models.CharField(max_length=20, choices=LAYOUTS, default="single")
    desktop_layout = models.CharField(max_length=20, choices=LAYOUTS, default="single")
    mobile_layout = models.CharField(max_length=20, choices=LAYOUTS, default="single")
    list_mobile_view = models.CharField(
        max_length=10,
        choices=[("table", "Table"), ("card", "Card")],
        default="card",
    )
    mobile_group_by = models.CharField(
        max_length=100, blank=True, default="", help_text="Field name for card grouping"
    )

    # Actions (JSON)
    actions = models.JSONField(default=list, blank=True)
    breadcrumbs = models.JSONField(default=list, blank=True)

    # Pagination
    page_size = models.PositiveIntegerField(default=25)
    sort_default = models.CharField(max_length=100, blank=True, default="")
    sort_direction = models.CharField(
        max_length=4,
        choices=[("asc", "Ascending"), ("desc", "Descending")],
        default="asc",
    )

    class Meta:
        db_table = "core_page_config"
        ordering = ["module", "page_key"]
        verbose_name = "Page Config"
        verbose_name_plural = "Page Configs"

    def __str__(self):
        return f"{self.page_key} ({self.page_type})"


class PageConfigField(ConcurrencyModel):
    """Field-level configuration for a page."""

    FIELD_TYPES = [
        ("text", "Text"),
        ("textarea", "Textarea"),
        ("number", "Number"),
        ("decimal", "Decimal"),
        ("email", "Email"),
        ("password", "Password"),
        ("date", "Date"),
        ("datetime", "DateTime"),
        ("time", "Time"),
        ("select", "Select"),
        ("multi_select", "Multi Select"),
        ("checkbox", "Checkbox"),
        ("radio", "Radio"),
        ("file", "File"),
        ("image", "Image"),
        ("hidden", "Hidden"),
        ("heading", "Heading"),
        ("divider", "Divider"),
        ("json", "JSON"),
        ("parent_child", "Parent-Child Table"),
    ]

    page_config = models.ForeignKey(
        PageConfig, on_delete=models.CASCADE, related_name="fields"
    )
    field_name = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    placeholder = models.CharField(max_length=200, blank=True, default="")
    help_text = models.CharField(max_length=500, blank=True, default="")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    data_type = models.CharField(
        max_length=20, blank=True, default="", help_text="String, Integer, etc."
    )
    required = models.BooleanField(default=False)
    readonly = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    default_value = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)

    # Grouping
    group_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="header, details, totals, notes",
    )

    # Layout
    col_span = models.PositiveIntegerField(default=1, help_text="1-12 column span")
    width = models.CharField(
        max_length=10,
        choices=[
            ("full", "Full"),
            ("half", "Half"),
            ("third", "Third"),
            ("quarter", "Quarter"),
        ],
        default="full",
    )

    # Responsive settings
    show_on_desktop = models.BooleanField(default=True)
    show_on_mobile = models.BooleanField(default=True)
    desktop_col_span = models.PositiveIntegerField(default=1)
    mobile_col_span = models.PositiveIntegerField(default=12)
    mobile_render_as = models.CharField(
        max_length=10,
        choices=[
            ("text", "Text"),
            ("badge", "Badge"),
            ("card", "Card"),
            ("compact", "Compact"),
        ],
        default="text",
    )

    # Validation
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    max_value = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    pattern = models.CharField(max_length=200, blank=True, default="")
    custom_validator = models.CharField(max_length=200, blank=True, default="")

    # Options
    options_source = models.CharField(
        max_length=10,
        choices=[
            ("static", "Static"),
            ("api", "API"),
            ("enum", "Enum"),
            ("model", "Model"),
        ],
        blank=True,
        default="",
    )
    options = models.JSONField(default=list, blank=True)
    options_api = models.CharField(max_length=200, blank=True, default="")
    options_label_field = models.CharField(max_length=100, blank=True, default="")
    options_value_field = models.CharField(max_length=100, blank=True, default="")
    option_group_by = models.CharField(max_length=100, blank=True, default="")

    # Related entity
    related_entity = models.CharField(max_length=100, blank=True, default="")
    related_display = models.CharField(max_length=100, blank=True, default="")
    related_search = models.JSONField(default=dict, blank=True)
    related_fields = models.JSONField(default=list, blank=True)

    # Conditional display
    show_when = models.JSONField(default=dict, blank=True)
    depends_on = models.JSONField(default=dict, blank=True)

    # Column settings (for list pages)
    is_column = models.BooleanField(default=False)
    column_order = models.PositiveIntegerField(default=0)
    column_width = models.CharField(max_length=10, blank=True, default="")
    column_align = models.CharField(
        max_length=10,
        choices=[("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="left",
    )
    sortable = models.BooleanField(default=False)
    filterable = models.BooleanField(default=False)
    searchable = models.BooleanField(default=False)
    aggregate = models.CharField(max_length=20, blank=True, default="")

    # Rendering
    render_as = models.CharField(max_length=20, blank=True, default="")

    # Parent-child (inline tables)
    parent_field = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_fields",
    )
    line_entity = models.CharField(max_length=100, blank=True, default="")
    line_fields = models.JSONField(default=list, blank=True)

    # Permissions
    permission_read = models.CharField(max_length=100, blank=True, default="")
    permission_write = models.CharField(max_length=100, blank=True, default="")

    # Display
    icon = models.CharField(max_length=50, blank=True, default="")
    prefix = models.CharField(max_length=20, blank=True, default="")
    suffix = models.CharField(max_length=20, blank=True, default="")
    format = models.CharField(max_length=50, blank=True, default="")
    badge_color = models.JSONField(default=dict, blank=True)
    css_class = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "core_page_config_field"
        ordering = ["sort_order", "field_name"]
        verbose_name = "Page Config Field"
        verbose_name_plural = "Page Config Fields"

    def __str__(self):
        return f"{self.page_config.page_key}.{self.field_name}"


# ---------------------------------------------------------------------------
# RBAC Models — Role-Based Access Control (T014)
# ---------------------------------------------------------------------------

MODULE_CHOICES = [
    ("financial", "Financial"),
    ("scm", "Supply Chain"),
    ("crm", "CRM"),
    ("mrp", "MRP"),
    ("hrm", "HRM"),
    ("admin", "Administration"),
]

ACTION_CHOICES = [
    ("view", "View"),
    ("create", "Create"),
    ("update", "Update"),
    ("delete", "Delete"),
    ("approve", "Approve"),
    ("post", "Post"),
    ("export", "Export"),
]


class Permission(ConcurrencyModel):
    """Granular permission for module + action."""

    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    codename = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "core_permission"
        unique_together = ("module", "action")
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["module", "action"]

    def __str__(self):
        return self.codename

    def save(self, *args, **kwargs):
        if not self.codename:
            self.codename = f"{self.module}_{self.action}"
        super().save(*args, **kwargs)


class Role(ConcurrencyModel):
    """Role that groups permissions together."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False, help_text="System roles cannot be deleted"
    )

    class Meta:
        db_table = "core_role"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name


class RolePermission(ConcurrencyModel):
    """Junction table linking roles to permissions."""

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )

    class Meta:
        db_table = "core_role_permission"
        unique_together = ("role", "permission")
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

    def __str__(self):
        return f"{self.role.name} → {self.permission.codename}"


class UserRole(ConcurrencyModel):
    """Junction table linking users to roles."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="user_roles"
    )

    class Meta:
        db_table = "core_user_role"
        unique_together = ("user", "role")
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"

    def __str__(self):
        return f"{self.user.email} → {self.role.name}"


class LoginHistory(ConcurrencyModel):
    """Record of user login events."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="login_history"
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    device_type = models.CharField(max_length=50, blank=True, default="")
    is_successful = models.BooleanField(default=True)
    login_time = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "core_login_history"
        ordering = ["-login_time"]
        verbose_name = "Login History"
        verbose_name_plural = "Login Histories"

    def __str__(self):
        return f"{self.user.email} @ {self.login_time}"


class EmailSetting(ConcurrencyModel):
    """SMTP email configuration singleton."""

    smtp_host = models.CharField(max_length=255, blank=True, default="")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True, default="")
    smtp_password = models.CharField(max_length=500, blank=True, default="")
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(blank=True, default="")
    from_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "core_email_setting"
        verbose_name = "Email Setting"
        verbose_name_plural = "Email Settings"

    def __str__(self):
        return f"SMTP: {self.smtp_host}:{self.smtp_port}"

    def save(self, *args, **kwargs):
        # Encrypt password before storing
        if self.smtp_password and not self.smtp_password.startswith("enc:"):
            from django.core.signing import TimestampSigner
            signer = TimestampSigner()
            self.smtp_password = "enc:" + signer.sign(self.smtp_password)
        super().save(*args, **kwargs)

    def get_decrypted_password(self) -> str:
        """Decrypt the stored password."""
        if not self.smtp_password:
            return ""
        if self.smtp_password.startswith("enc:"):
            from django.core.signing import SignatureExpired, TimestampSigner
            try:
                signer = TimestampSigner()
                return signer.unsign(self.smtp_password[4:], max_age=None)
            except (SignatureExpired, Exception):
                return ""
        return self.smtp_password

    @classmethod
    def load(cls) -> "EmailSetting":
        """Get or create the singleton email config."""
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj
