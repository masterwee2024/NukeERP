"""Menu API endpoints using Django Ninja."""

from uuid import UUID

from django.db import transaction
from django.utils.dateparse import parse_datetime
from ninja import Field, ModelSchema, Router, Schema
from ninja.errors import HttpError

from apps.core.models import Menu, MenuRole

router = Router()


# --- Schemas ---


class MenuCreateSchema(Schema):
    name: str
    slug: str
    icon: str = ""
    url: str = ""
    parent_id: UUID | None = None
    sort_order: int = 0
    permission_codename: str = ""
    is_active: bool = True
    level: int = 0
    module: str = ""


class MenuUpdateSchema(Schema):
    name: str | None = None
    icon: str | None = None
    url: str | None = None
    parent_id: UUID | None = None
    sort_order: int | None = None
    permission_codename: str | None = None
    is_active: bool | None = None
    module: str | None = None
    updated_at: str | None = None


class MenuOutSchema(ModelSchema):
    children: list["MenuOutSchema"] = Field(default_factory=list)

    class Meta:
        model = Menu
        fields = (
            "id",
            "name",
            "slug",
            "icon",
            "url",
            "parent",
            "sort_order",
            "permission_codename",
            "is_active",
            "level",
            "module",
            "created_at",
            "updated_at",
        )


class MenuTreeSchema(Schema):
    id: UUID
    name: str
    slug: str
    icon: str
    url: str
    level: int
    module: str
    sort_order: int
    children: list["MenuTreeSchema"] = Field(default_factory=list)


# --- Helpers ---


def _build_tree(menus: list[Menu], parent_id: UUID | None = None) -> list[dict]:
    """Build a nested tree structure from flat menu list."""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            node = {
                "id": menu.id,
                "name": menu.name,
                "slug": menu.slug,
                "icon": menu.icon,
                "url": menu.url,
                "level": menu.level,
                "module": menu.module,
                "sort_order": menu.sort_order,
                "children": _build_tree(menus, menu.id),
            }
            tree.append(node)
    return tree


def _get_user_menu_ids(user) -> set:
    """Get set of menu IDs the user has access to via their groups."""
    if user.is_superuser:
        return set(Menu.objects.filter(is_active=True).values_list("id", flat=True))

    group_ids = user.groups.values_list("id", flat=True)
    return set(
        MenuRole.objects.filter(role_id__in=group_ids).values_list("menu_id", flat=True)
    )


# --- Endpoints ---


@router.get("/", response=list[MenuTreeSchema])
def get_menu_tree(request):
    """Return filtered menu tree for the current user."""
    user = request.auth

    if user.is_superuser:
        menus = Menu.objects.filter(is_active=True).order_by("sort_order", "name")
    else:
        menu_ids = _get_user_menu_ids(user)
        menus = Menu.objects.filter(id__in=menu_ids, is_active=True).order_by(
            "sort_order", "name"
        )

    return _build_tree(menus, parent_id=None)


@router.get("/all/", response=list[MenuOutSchema])
def get_all_menus(request):
    """Return all menus (admin view with role assignments)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Admin access required")

    return Menu.objects.filter(is_active=True).order_by("sort_order", "name")


@router.post("/", response=MenuOutSchema)
def create_menu(request, payload: MenuCreateSchema):
    """Create a new menu item (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Admin access required")

    parent = None
    if payload.parent_id:
        try:
            parent = Menu.objects.get(id=payload.parent_id)
        except Menu.DoesNotExist:
            raise HttpError(404, "Parent menu not found") from None

    with transaction.atomic():
        menu = Menu.objects.create(
            name=payload.name,
            slug=payload.slug,
            icon=payload.icon,
            url=payload.url,
            parent=parent,
            sort_order=payload.sort_order,
            permission_codename=payload.permission_codename,
            is_active=payload.is_active,
            level=0 if parent is None else parent.level + 1,
            module=payload.module,
        )

    return menu


@router.put("/{menu_id}/", response=MenuOutSchema)
def update_menu(request, menu_id: UUID, payload: MenuUpdateSchema):
    """Update a menu item (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Admin access required")

    try:
        menu = Menu.objects.get(id=menu_id)
    except Menu.DoesNotExist:
        raise HttpError(404, "Menu not found") from None

    # Optimistic locking: validate updated_at matches
    if payload.updated_at:
        client_dt = parse_datetime(payload.updated_at)
        if client_dt and menu.updated_at != client_dt:
            raise HttpError(
                409,
                "Record was modified by another user. Please reload and try again.",
            )

    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        if update_data["parent_id"]:
            try:
                parent = Menu.objects.get(id=update_data["parent_id"])
                menu.parent = parent
                menu.level = parent.level + 1
            except Menu.DoesNotExist:
                raise HttpError(404, "Parent menu not found") from None
        else:
            menu.parent = None
            menu.level = 0
        del update_data["parent_id"]

    for field, value in update_data.items():
        if field != "updated_at":
            setattr(menu, field, value)

    menu.save()
    return menu


@router.delete("/{menu_id}/")
def delete_menu(request, menu_id: UUID):
    """Soft-delete (deactivate) a menu item (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Admin access required")

    try:
        menu = Menu.objects.get(id=menu_id)
    except Menu.DoesNotExist:
        raise HttpError(404, "Menu not found") from None

    menu.is_active = False
    menu.save()

    return {"detail": f"Menu '{menu.name}' deactivated"}


@router.get("/admin/tree/")
def get_admin_menu_tree(request):
    """Return full menu tree with role assignments (admin view)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Admin access required")

    menus = Menu.objects.filter(is_active=True).order_by("sort_order", "name")
    tree = _build_tree(menus, parent_id=None)

    # Annotate with role assignments
    menu_roles = MenuRole.objects.select_related("role").all()
    roles_by_menu = {}
    for mr in menu_roles:
        roles_by_menu.setdefault(mr.menu_id, []).append(mr.role.name)

    def annotate(nodes):
        for node in nodes:
            node["roles"] = roles_by_menu.get(node["id"], [])
            annotate(node["children"])

    annotate(tree)
    return tree
