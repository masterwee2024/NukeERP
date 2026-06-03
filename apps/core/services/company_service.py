"""Company service — business logic for multi-company architecture."""

from typing import Any

from apps.core.models import Company, User, UserCompany


def get_user_companies(user: User) -> list[Company]:
    """Return all companies the user has access to."""
    if user.is_superuser:
        return list(Company.objects.filter(is_active=True).order_by("name"))
    return list(
        Company.objects.filter(company_users__user=user, is_active=True).order_by(
            "name"
        )
    )


def get_user_default_company(user: User) -> Company | None:
    """Return user's default company.

    Priority:
    1. UserCompany.is_default
    2. User.current_company
    3. First assigned company
    4. First active company (for superusers)
    """
    try:
        u = (
            UserCompany.objects.filter(user=user, is_default=True)
            .select_related("company")
            .first()
        )
        if u:
            return u.company
    except UserCompany.DoesNotExist:
        pass
    if user.current_company and user.current_company.is_active:
        return user.current_company
    first = UserCompany.objects.filter(user=user).select_related("company").first()
    if first:
        return first.company
    if user.is_superuser:
        return Company.objects.filter(is_active=True).order_by("name").first()
    return None


def set_user_default_company(user: User, company: Company) -> None:
    """Set a user's default company."""
    UserCompany.objects.filter(user=user).update(is_default=False)
    UserCompany.objects.filter(user=user, company=company).update(is_default=True)
    user.current_company = company
    user.save(update_fields=["current_company"])


def get_company_children(company: Company) -> list[Company]:
    """Return all direct child companies."""
    return list(company.children.filter(is_active=True).order_by("name"))


def get_company_descendants(company: Company) -> list[Company]:
    """Return all descendant companies (recursive)."""
    result = []
    for child in get_company_children(company):
        result.append(child)
        result.extend(get_company_descendants(child))
    return result


def get_company_ancestors(company: Company) -> list[Company]:
    """Return list of ancestor companies from root to parent."""
    ancestors = []
    current = company.parent
    while current is not None:
        ancestors.insert(0, current)
        current = current.parent
    return ancestors


def get_company_group(company: Company) -> Company:
    """Return root group company (top-level ancestor)."""
    ancestors = get_company_ancestors(company)
    return ancestors[0] if ancestors else company


def assign_user_to_companies(
    user: User, company_ids: list[Any], default_id: str | None = None
) -> None:
    """Assign user to multiple companies."""
    companies = Company.objects.filter(id__in=company_ids)
    for company in companies:
        UserCompany.objects.get_or_create(user=user, company=company)
    if default_id:
        try:
            default_company = Company.objects.get(id=default_id)
            set_user_default_company(user, default_company)
        except Company.DoesNotExist:
            pass


def unassign_user_from_company(user: User, company: Company) -> None:
    """Remove user's access to a company."""
    UserCompany.objects.filter(user=user, company=company).delete()
    if user.current_company == company:
        remaining = UserCompany.objects.filter(user=user).first()
        user.current_company = remaining.company if remaining else None
        user.save(update_fields=["current_company"])


def get_company_tree() -> list[dict[str, Any]]:
    """Return a nested tree of all active companies."""
    roots = Company.objects.filter(parent__isnull=True, is_active=True).order_by("name")

    def _build(node: Company) -> dict[str, Any]:
        children = get_company_children(node)
        return {
            "id": str(node.id),
            "name": node.name,
            "code": node.code,
            "is_group": node.is_group,
            "children": [_build(c) for c in children],
        }

    return [_build(root) for root in roots]
