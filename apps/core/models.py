"""Core models — User, Menu, MenuRole, and base models."""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


# ---------------------------------------------------------------------------
# Approval Workflow Models (T016)
# ---------------------------------------------------------------------------

WORKFLOW_MODULE_CHOICES = [
    ("financial", "Financial"),
    ("scm", "Supply Chain"),
    ("crm", "CRM"),
    ("mrp", "MRP"),
    ("hrm", "HRM"),
]

WORKFLOW_NODE_TYPE_CHOICES = [
    ("start", "Start"),
    ("end", "End"),
    ("approve", "Approve"),
    ("condition", "Condition"),
    ("notify", "Notify"),
    ("action", "Action"),
]

WORKFLOW_EXECUTION_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
    ("completed", "Completed"),
]

WORKFLOW_STEP_ACTION_CHOICES = [
    ("approve", "Approve"),
    ("reject", "Reject"),
    ("return", "Return"),
    ("delegate", "Delegate"),
]

WORKFLOW_STEP_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
    ("skipped", "Skipped"),
]


class WorkflowDefinition(ConcurrencyModel):
    """Configurable approval workflow definition."""

    name = models.CharField(max_length=200)
    module = models.CharField(max_length=50, choices=WORKFLOW_MODULE_CHOICES)
    document_type = models.CharField(
        max_length=100,
        help_text="e.g. PurchaseOrder, SalesInvoice, LeaveRequest",
    )
    version = models.PositiveIntegerField(default=1)
    flow_data = models.JSONField(
        default=dict, blank=True, help_text="React-flow nodes/edges JSON"
    )
    is_active = models.BooleanField(default=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_definitions",
        help_text="Null = global template",
    )
    is_global_template = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_workflows"
    )

    class Meta:
        db_table = "core_workflow_definition"
        ordering = ["module", "document_type", "name"]
        unique_together = [("name", "company", "version")]
        verbose_name = "Workflow Definition"
        verbose_name_plural = "Workflow Definitions"

    def __str__(self):
        return f"{self.name} v{self.version}"


class WorkflowNode(ConcurrencyModel):
    """Node within a workflow definition."""

    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="nodes"
    )
    node_id = models.CharField(
        max_length=100, help_text="React-flow node ID (e.g. 'node_1')"
    )
    node_type = models.CharField(max_length=20, choices=WORKFLOW_NODE_TYPE_CHOICES)
    label = models.CharField(max_length=200, blank=True, default="")
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "core_workflow_node"
        unique_together = [("workflow", "node_id")]
        ordering = ["workflow", "node_id"]
        verbose_name = "Workflow Node"
        verbose_name_plural = "Workflow Nodes"

    def __str__(self):
        return f"{self.workflow.name} → {self.label or self.node_id}"


class WorkflowEdge(ConcurrencyModel):
    """Edge connecting workflow nodes."""

    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="edges"
    )
    source_node_id = models.CharField(max_length=100)
    target_node_id = models.CharField(max_length=100)
    label = models.CharField(max_length=200, blank=True, default="")
    condition = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "core_workflow_edge"
        ordering = ["workflow", "source_node_id", "target_node_id"]
        verbose_name = "Workflow Edge"
        verbose_name_plural = "Workflow Edges"

    def __str__(self):
        return f"{self.workflow.name}: {self.source_node_id} → {self.target_node_id}"


class WorkflowExecution(ConcurrencyModel):
    """Runtime execution instance of a workflow."""

    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="executions"
    )
    document_type = models.CharField(max_length=100)
    document_id = models.UUIDField()
    current_node_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=WORKFLOW_EXECUTION_STATUS_CHOICES,
        default="pending",
    )
    requester = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflow_requests",
        help_text="User who submitted for approval",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflow_created_documents",
        help_text="User who created the document",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="workflow_executions"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "core_workflow_execution"
        ordering = ["-started_at"]
        verbose_name = "Workflow Execution"
        verbose_name_plural = "Workflow Executions"
        indexes = [
            models.Index(fields=["document_type", "document_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.workflow.name} ({self.document_type}:{self.document_id}) — {self.status}"


class WorkflowExecutionStep(ConcurrencyModel):
    """Individual step within a workflow execution."""

    execution = models.ForeignKey(
        WorkflowExecution, on_delete=models.CASCADE, related_name="steps"
    )
    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.SET_NULL,
        null=True,
        related_name="execution_steps",
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_steps",
    )
    action = models.CharField(
        max_length=20, choices=WORKFLOW_STEP_ACTION_CHOICES, blank=True, default=""
    )
    comment = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=WORKFLOW_STEP_STATUS_CHOICES,
        default="pending",
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    delegated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_approval_steps",
    )

    class Meta:
        db_table = "core_workflow_execution_step"
        ordering = ["timestamp"]
        verbose_name = "Workflow Execution Step"
        verbose_name_plural = "Workflow Execution Steps"

    def __str__(self):
        return f"{self.execution} — {self.action or 'pending'} by {self.approver}"


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
    is_custom = models.BooleanField(
        default=False,
        help_text="True if this is a user-defined custom field stored in custom_fields JSONB",
    )
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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")

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


class Attachment(ConcurrencyModel):
    """Generic file attachment linked to any record via ContentType."""

    ALLOWED_EXTENSIONS = {
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "doc",
        "docx",
        "xls",
        "xlsx",
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="attachments"
    )
    object_id = models.UUIDField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    file = models.FileField(upload_to="attachments/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_attachment"
        ordering = ["-created_at"]
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.file_name


class NumberingSeriesPolicy(ConcurrencyModel):
    """Global numbering series template — shared across companies."""

    document_type = models.CharField(
        max_length=100, unique=True, help_text="e.g., invoice, purchase_order"
    )
    prefix = models.CharField(max_length=20, blank=True, default="")
    date_format = models.CharField(
        max_length=20, blank=True, default="", help_text="e.g., YYYYMM, YYMM"
    )
    padding = models.PositiveIntegerField(
        default=6, help_text="Zero-padding for running number"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_numbering_policy"
        ordering = ["document_type"]
        verbose_name = "Numbering Series Policy"
        verbose_name_plural = "Numbering Series Policies"

    def __str__(self):
        return f"{self.prefix}{self.document_type}"


class CompanyNumberingSeries(ConcurrencyModel):
    """Per-company numbering series counter — assigned from a policy."""

    RESET_PERIOD_CHOICES = [
        ("yearly", "Yearly"),
        ("monthly", "Monthly"),
        ("never", "Never"),
    ]

    policy = models.ForeignKey(
        NumberingSeriesPolicy,
        on_delete=models.CASCADE,
        related_name="company_assignments",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="numbering_assignments",
    )
    next_number = models.PositiveIntegerField(default=1)
    reset_period = models.CharField(
        max_length=20, choices=RESET_PERIOD_CHOICES, default="yearly"
    )
    last_reset_at = models.DateTimeField(
        null=True, blank=True, help_text="When the counter was last reset"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_company_numbering_series"
        ordering = ["policy__document_type"]
        verbose_name = "Company Numbering Series"
        verbose_name_plural = "Company Numbering Series"
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "company"],
                name="uq_company_numbering_policy_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["policy"]),
        ]

    def __str__(self):
        return f"{self.policy} @ {self.company.name if self.company else '?'}"


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
        obj = cls.objects.order_by("-updated_at").first()
        if not obj:
            obj = cls.objects.create()
        return obj


class AuditLog(models.Model):
    """Immutable audit trail for all model changes."""

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
    ]

    CATEGORY_CHOICES = [
        ("crud", "CRUD"),
        ("login", "Login"),
        ("export", "Export"),
        ("config", "Configuration"),
        ("file", "File"),
        ("approval", "Approval"),
        ("bulk", "Bulk Operation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Dotted model class name (e.g. 'core.Company')",
    )
    record_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="String representation of the record's PK",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, db_index=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="crud",
        db_index=True,
        help_text="Audit category for grouping and filtering",
    )
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (export format, file name, etc.)",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    bulk_operation = models.ForeignKey(
        "AuditLogBulk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Links individual audit entries to a parent bulk operation",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "core_audit_log"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"[{self.category}] {self.action} {self.model_name} #{self.record_id}"


class AuditLogBulk(models.Model):
    """Tracks bulk operations (bulk update, bulk delete, bulk import)."""

    OPERATION_TYPES = [
        ("bulk_update", "Bulk Update"),
        ("bulk_delete", "Bulk Delete"),
        ("bulk_import", "Bulk Import"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    description = models.CharField(max_length=500, blank=True, default="")
    record_count = models.PositiveIntegerField(default=0)
    affected_models = models.JSONField(
        default=list,
        blank=True,
        help_text="List of model names affected",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_operations",
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_operations",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "core_audit_log_bulk"
        ordering = ["-created_at"]
        verbose_name = "Audit Log Bulk Operation"
        verbose_name_plural = "Audit Log Bulk Operations"

    def __str__(self):
        return f"{self.operation_type} — {self.record_count} records"


class AuditRetention(models.Model):
    """Configurable audit log retention policy per company."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="audit_retention",
    )
    retention_years = models.PositiveIntegerField(default=7)
    auto_archive = models.BooleanField(default=True)
    last_archive_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_audit_retention"
        verbose_name = "Audit Retention Policy"
        verbose_name_plural = "Audit Retention Policies"

    def __str__(self):
        return f"{self.company} — {self.retention_years} years"


class AuditExport(models.Model):
    """Tracks audit log export operations."""

    EXPORT_TYPES = [
        ("csv", "CSV"),
        ("excel", "Excel"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    export_type = models.CharField(max_length=10, choices=EXPORT_TYPES)
    filters = models.JSONField(default=dict, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_exports",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_exports",
    )
    file_path = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_audit_export"
        ordering = ["-created_at"]
        verbose_name = "Audit Export"
        verbose_name_plural = "Audit Exports"

    def __str__(self):
        return f"{self.export_type} export — {self.record_count} records"


class NotificationType(ConcurrencyModel):
    """Configuration template for notification types."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    email_template = models.TextField(blank=True, default="")
    in_app_template = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_notification_type"
        ordering = ["name"]
        verbose_name = "Notification Type"
        verbose_name_plural = "Notification Types"

    def __str__(self):
        return self.name


class Notification(ConcurrencyModel):
    """In-app and standard notification record."""

    notification_type = models.ForeignKey(
        NotificationType, on_delete=models.CASCADE, related_name="notifications"
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "core_notification"
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.title} for {self.recipient.email}"


class PushSubscription(ConcurrencyModel):
    """PWA push notification subscriptions for Web Push protocol."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.TextField()
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_push_subscription"
        ordering = ["-created_at"]
        verbose_name = "Push Subscription"
        verbose_name_plural = "Push Subscriptions"

    def __str__(self):
        return f"Push for {self.user.email}"


class ApprovalToken(ConcurrencyModel):
    """Secure tokens for quick email approvals without login."""

    execution = models.ForeignKey(
        WorkflowExecution, on_delete=models.CASCADE, related_name="approval_tokens"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="approval_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    action = models.CharField(
        max_length=20,
        choices=[("approve", "Approve"), ("reject", "Reject")],
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="approval_tokens"
    )

    class Meta:
        db_table = "core_approval_token"
        ordering = ["-created_at"]
        verbose_name = "Approval Token"
        verbose_name_plural = "Approval Tokens"

    def __str__(self):
        return f"{self.action} token for {self.user.email}"


class Channel(ConcurrencyModel):
    """Internal chat channel or direct message thread."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    type = models.CharField(
        max_length=20,
        choices=[
            ("public", "Public"),
            ("private", "Private"),
            ("direct", "Direct Message"),
            ("group_dm", "Group DM"),
            ("system", "System"),
            ("broadcast", "Broadcast"),
        ],
        default="public",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_channels",
    )
    is_archived = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="channels"
    )

    class Meta:
        db_table = "core_channel"
        ordering = ["name"]
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        return f"{self.type} - {self.name} ({self.company.code})"


class ChannelMember(ConcurrencyModel):
    """Membership of a user in a channel."""

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="channel_memberships"
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ("owner", "Owner"),
            ("admin", "Admin"),
            ("member", "Member"),
        ],
        default="member",
    )
    last_read_at = models.DateTimeField(auto_now_add=True)
    notification_mute = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_channel_member"
        unique_together = [("channel", "user")]
        ordering = ["joined_at"]
        verbose_name = "Channel Member"
        verbose_name_plural = "Channel Members"

    def __str__(self):
        return f"{self.user.email} in {self.channel.name}"


class Message(ConcurrencyModel):
    """Message sent within a channel or DM thread."""

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_sent"
    )
    content = models.TextField()
    content_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text"),
            ("file", "File Attachment"),
            ("link", "Link Preview"),
            ("system", "System"),
        ],
        default="text",
    )
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    link_type = models.CharField(max_length=50, blank=True, default="")
    link_id = models.UUIDField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "core_message"
        ordering = ["created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"Msg {self.id} by {self.sender.email} in {self.channel.name}"


class MessageAttachment(ConcurrencyModel):
    """File attachment uploaded within a message."""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="chat_attachments/")
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)

    class Meta:
        db_table = "core_message_attachment"
        verbose_name = "Message Attachment"
        verbose_name_plural = "Message Attachments"

    def __str__(self):
        return self.file_name


class MessageReaction(ConcurrencyModel):
    """Emoji reaction to a message."""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="message_reactions"
    )
    emoji = models.CharField(max_length=50)

    class Meta:
        db_table = "core_message_reaction"
        unique_together = [("message", "user", "emoji")]
        verbose_name = "Message Reaction"
        verbose_name_plural = "Message Reactions"

    def __str__(self):
        return f"{self.user.email} reacts {self.emoji} to message {self.message.id}"


class MessageRead(ConcurrencyModel):
    """Individual read tracking per message and user."""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="read_records"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_read"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_message_read"
        unique_together = [("message", "user")]
        verbose_name = "Message Read"
        verbose_name_plural = "Message Reads"

    def __str__(self):
        return f"Message {self.message.id} read by {self.user.email}"


class ApprovalPolicy(ConcurrencyModel):
    """Policy that auto-routes transactions to a workflow based on conditions."""

    name = models.CharField(max_length=200)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name="policies"
    )
    module = models.CharField(max_length=50, choices=WORKFLOW_MODULE_CHOICES)
    document_type = models.CharField(max_length=100)
    conditions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of condition objects: [{field, operator, value, value_to?}]",
    )
    priority = models.PositiveIntegerField(
        default=100, help_text="Lower number = higher priority"
    )
    is_active = models.BooleanField(default=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approval_policies",
        help_text="Null = global policy",
    )

    class Meta:
        db_table = "core_approval_policy"
        ordering = ["module", "document_type", "priority", "name"]
        verbose_name = "Approval Policy"
        verbose_name_plural = "Approval Policies"

    def __str__(self):
        scope = "Global" if self.company is None else self.company.code
        return f"{self.name} [{scope}] ({self.module}.{self.document_type})"


# ── Import / Data Migration Models ─────────────────────────────────


class ImportTemplate(ConcurrencyModel):
    """Defines an import template for a specific entity type (e.g. Items, Customers)."""

    name = models.CharField(max_length=200)
    entity_type = models.SlugField(unique=True, help_text="Unique key e.g. 'items'")
    description = models.TextField(blank=True)
    column_definitions = models.JSONField(
        default=list,
        help_text="List of column dicts: [{name, label, type, required, max_length, fk_model, format_example}]",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_import_template"
        ordering = ["name"]
        verbose_name = "Import Template"
        verbose_name_plural = "Import Templates"

    def __str__(self):
        return self.name


class ImportJob(ConcurrencyModel):
    """Tracks a single CSV import execution."""

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("validating", "Validating"),
        ("importing", "Importing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("rolled_back", "Rolled Back"),
    ]

    template = models.ForeignKey(
        ImportTemplate, on_delete=models.CASCADE, related_name="jobs"
    )
    file_name = models.CharField(max_length=500)
    uploaded_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, related_name="import_jobs"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    total_rows = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="import_jobs",
    )
    error_log = models.TextField(
        blank=True, help_text="General job-level error messages"
    )

    class Meta:
        db_table = "core_import_job"
        ordering = ["-created_at"]
        verbose_name = "Import Job"
        verbose_name_plural = "Import Jobs"

    def __str__(self):
        return f"{self.template.name} — {self.file_name} ({self.status})"


class ImportRow(ConcurrencyModel):
    """A single row of an import job with validation and import status."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("valid", "Valid"),
        ("error", "Error"),
        ("imported", "Imported"),
        ("skipped", "Skipped"),
    ]

    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="rows")
    row_number = models.IntegerField()
    raw_data = models.JSONField(default=dict, help_text="Original CSV row data")
    mapped_data = models.JSONField(default=dict, help_text="Post-mapping data")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    imported_record_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "core_import_row"
        ordering = ["job", "row_number"]
        unique_together = [["job", "row_number"]]
        verbose_name = "Import Row"
        verbose_name_plural = "Import Rows"

    def __str__(self):
        return f"Row {self.row_number} — {self.status}"


class ImportHistory(ConcurrencyModel):
    """Audit log entry for import or rollback actions."""

    ACTION_CHOICES = [
        ("import", "Import"),
        ("rollback", "Rollback"),
    ]

    job = models.ForeignKey(
        ImportJob, on_delete=models.CASCADE, related_name="history_entries"
    )
    entity_type = models.SlugField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    record_count = models.IntegerField(default=0)
    performed_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, related_name="import_history"
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "core_import_history"
        ordering = ["-created_at"]
        verbose_name = "Import History"
        verbose_name_plural = "Import Histories"

    def __str__(self):
        return f"{self.action} — {self.entity_type} ({self.record_count} records)"


# ── Opening Balance Migration Models ──────────────────────────────


class OpeningBalanceMigration(ConcurrencyModel):
    """Tracks a single opening balance migration for a company."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("rolled_back", "Rolled Back"),
    ]

    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, related_name="opening_migrations"
    )
    go_live_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, related_name="opening_migrations"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "core_opening_balance_migration"
        ordering = ["-created_at"]
        verbose_name = "Opening Balance Migration"
        verbose_name_plural = "Opening Balance Migrations"

    def __str__(self):
        return f"Migration {self.id} — {self.company.code} ({self.go_live_date})"


class OpeningBalanceGL(ConcurrencyModel):
    """GL trial balance line for opening balance migration."""

    migration = models.ForeignKey(
        OpeningBalanceMigration, on_delete=models.CASCADE, related_name="gl_lines"
    )
    account_code = models.CharField(max_length=50)
    account_name = models.CharField(max_length=200, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    row_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_opening_balance_gl"
        ordering = ["row_number"]


class OpeningBalanceAP(ConcurrencyModel):
    """AP opening invoice line."""

    migration = models.ForeignKey(
        OpeningBalanceMigration, on_delete=models.CASCADE, related_name="ap_lines"
    )
    supplier_code = models.CharField(max_length=50)
    invoice_no = models.CharField(max_length=100)
    invoice_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="MYR")
    row_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_opening_balance_ap"
        ordering = ["row_number"]


class OpeningBalanceAR(ConcurrencyModel):
    """AR opening invoice line."""

    migration = models.ForeignKey(
        OpeningBalanceMigration, on_delete=models.CASCADE, related_name="ar_lines"
    )
    customer_code = models.CharField(max_length=50)
    invoice_no = models.CharField(max_length=100)
    invoice_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="MYR")
    row_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_opening_balance_ar"
        ordering = ["row_number"]


class OpeningBalanceInventory(ConcurrencyModel):
    """Inventory opening stock line."""

    migration = models.ForeignKey(
        OpeningBalanceMigration,
        on_delete=models.CASCADE,
        related_name="inventory_lines",
    )
    item_code = models.CharField(max_length=50)
    warehouse_code = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=2)
    row_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_opening_balance_inventory"
        ordering = ["row_number"]


class OpeningBalanceAsset(ConcurrencyModel):
    """Fixed asset opening balance line."""

    migration = models.ForeignKey(
        OpeningBalanceMigration, on_delete=models.CASCADE, related_name="asset_lines"
    )
    asset_code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField()
    cost = models.DecimalField(max_digits=18, decimal_places=2)
    accumulated_depreciation = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    useful_life = models.IntegerField(null=True, blank=True, help_text="Years")
    row_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_opening_balance_asset"
        ordering = ["row_number"]


class IndustryTemplate(ConcurrencyModel):
    """JSON-based industry template — pre-configures the platform for a specific industry."""

    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    template_version = models.CharField(max_length=20, default="1.0.0")
    module_dependencies = models.JSONField(default=list, blank=True)
    menu_config = models.JSONField(default=list, blank=True)
    page_config = models.JSONField(default=list, blank=True)
    workflow_config = models.JSONField(default=list, blank=True)
    gl_account_config = models.JSONField(default=list, blank=True)
    report_config = models.JSONField(default=list, blank=True)
    seed_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_industry_template"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} v{self.template_version}"


class IndustryTemplateInstallation(ConcurrencyModel):
    """Records a template installation for a specific company."""

    template = models.ForeignKey(
        IndustryTemplate, on_delete=models.CASCADE, related_name="installations"
    )
    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, related_name="template_installations"
    )
    installed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="template_installations",
    )
    installed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("uninstalled", "Uninstalled")],
        default="active",
    )
    configuration_overrides = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "core_industry_template_installation"
        unique_together = [("template", "company", "status")]
        ordering = ["-installed_at"]

    def __str__(self):
        return f"{self.template.code} @ {self.company_id} ({self.status})"


class TransactionMigration(ConcurrencyModel):
    """Tracks a transaction migration (pending/historical) for a company."""

    MIGRATION_OPTIONS = [
        ("fresh", "Fresh Start"),
        ("full", "Full Migration"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("rolled_back", "Rolled Back"),
    ]

    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, related_name="transaction_migrations"
    )
    opening_migration = models.ForeignKey(
        "OpeningBalanceMigration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_migrations",
    )
    go_live_date = models.DateField()
    migration_option = models.CharField(
        max_length=10, choices=MIGRATION_OPTIONS, default="fresh"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="transaction_migrations",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "core_transaction_migration"
        ordering = ["-created_at"]

    def __str__(self):
        return f"TxMigration {self.id} — {self.company.code} ({self.migration_option})"


class TransactionMigrationLine(ConcurrencyModel):
    """A single line of a transaction migration — typed by line_type."""

    LINE_TYPES = [
        ("pending_po", "Pending Purchase Order"),
        ("pending_so", "Pending Sales Order"),
        ("pending_grn", "Pending Goods Receipt Note"),
        ("historical_journal", "Historical Journal Entry"),
        ("historical_ap_invoice", "Historical AP Invoice"),
        ("historical_ar_invoice", "Historical AR Invoice"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("valid", "Valid"),
        ("error", "Error"),
        ("imported", "Imported"),
        ("rolled_back", "Rolled Back"),
    ]

    migration = models.ForeignKey(
        TransactionMigration,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_type = models.CharField(max_length=30, choices=LINE_TYPES)
    row_number = models.IntegerField(default=0)
    raw_data = models.JSONField(default=dict, help_text="Original CSV row data")
    data = models.JSONField(default=dict, help_text="Parsed and validated data")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "core_transaction_migration_line"
        ordering = ["migration", "line_type", "row_number"]
        verbose_name = "Transaction Migration Line"

    def __str__(self):
        return f"{self.line_type} Row {self.row_number} — {self.status}"
