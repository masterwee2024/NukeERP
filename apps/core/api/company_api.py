"""Company API — multi-company CRUD, switch, and user assignment."""

from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import Company, User, UserCompany
from apps.core.services import company_service

router = Router()


class CompanyOut(Schema):
    id: str
    name: str
    code: str
    registration_number: str = ""
    tax_number: str = ""
    is_active: bool = True
    parent_id: str | None = None
    is_group: bool = False
    address: str = ""
    city: str = ""
    state: str = ""
    postcode: str = ""
    country: str = "MY"
    phone: str = ""
    email: str = ""
    base_currency: str = "MYR"
    date_format: str = "Y-m-d"
    timezone: str = "Asia/Kuala_Lumpur"
    logo: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_parent_id(obj):
        return str(obj.parent_id) if obj.parent_id else None

    @staticmethod
    def resolve_logo(obj):
        return obj.logo.url if obj.logo else None


class CompanyCreate(Schema):
    name: str
    code: str
    registration_number: str = ""
    tax_number: str = ""
    parent_id: str | None = None
    is_group: bool = False
    address: str = ""
    city: str = ""
    state: str = ""
    postcode: str = ""
    country: str = "MY"
    phone: str = ""
    email: str = ""
    base_currency: str = "MYR"
    date_format: str = "Y-m-d"
    timezone: str = "Asia/Kuala_Lumpur"


class CompanyUpdate(Schema):
    name: str | None = None
    code: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    parent_id: str | None = None
    is_group: bool | None = None
    is_active: bool | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    base_currency: str | None = None
    date_format: str | None = None
    timezone: str | None = None


class CompanySwitchOut(Schema):
    id: str
    name: str
    code: str


class UserCompanyOut(Schema):
    user_id: str
    company_id: str
    company_name: str
    is_default: bool


class UserCompanyAssign(Schema):
    company_ids: list[str]
    default_id: str | None = None


# --- Company CRUD ---


# --- Company CRUD (static paths before {id}) ---


@router.get("/", response=list[CompanyOut])
def list_companies(request):
    """List companies accessible by the current user."""
    if request.auth.is_superuser:
        return list(Company.objects.filter(is_active=True).order_by("name"))
    return company_service.get_user_companies(request.auth)


@router.post("/", response=CompanyOut)
def create_company(request, data: CompanyCreate):
    """Create a new company (superadmin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can create companies")
    parent = None
    if data.parent_id:
        try:
            parent = Company.objects.get(id=data.parent_id)
        except Company.DoesNotExist:
            raise HttpError(400, "Parent company not found") from None
    company = Company.objects.create(
        name=data.name,
        code=data.code,
        registration_number=data.registration_number,
        tax_number=data.tax_number,
        parent=parent,
        is_group=data.is_group,
        address=data.address,
        city=data.city,
        state=data.state,
        postcode=data.postcode,
        country=data.country,
        phone=data.phone,
        email=data.email,
        base_currency=data.base_currency,
        date_format=data.date_format,
        timezone=data.timezone,
    )
    return company


@router.get("/current/", response=CompanySwitchOut)
def get_current_company(request):
    """Get the current active company for the user."""
    company = company_service.get_user_default_company(request.auth)
    if company is None:
        companies = company_service.get_user_companies(request.auth)
        if companies:
            company = companies[0]
        else:
            raise HttpError(404, "No company assigned")
    return {
        "id": str(company.id),
        "name": company.name,
        "code": company.code,
    }


@router.get("/tree/", response=list[dict])
def get_company_tree(request):
    """Get full company hierarchy tree."""
    return company_service.get_company_tree()


@router.post("/switch/", response=CompanySwitchOut)
def switch_company(request, payload: CompanySwitchOut):
    """Switch the current active company."""
    try:
        company = Company.objects.get(id=payload.id, is_active=True)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    ucs = UserCompany.objects.filter(user=request.auth, company=company)
    if not ucs.exists() and not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    request.auth.current_company = company
    request.auth.save(update_fields=["current_company"])
    return {
        "id": str(company.id),
        "name": company.name,
        "code": company.code,
    }


@router.put("/default/", response=CompanySwitchOut)
def set_default_company(request, payload: CompanySwitchOut):
    """Set the default company for the user."""
    try:
        company = Company.objects.get(id=payload.id, is_active=True)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    ucs = UserCompany.objects.filter(user=request.auth, company=company)
    if not ucs.exists() and not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    company_service.set_user_default_company(request.auth, company)
    return {
        "id": str(company.id),
        "name": company.name,
        "code": company.code,
    }


@router.get("/admin/user-companies/{user_id}/", response=list[UserCompanyOut])
def list_user_companies(request, user_id: UUID):
    """List company assignments for a user (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    return [
        {
            "user_id": str(uc.user_id),
            "company_id": str(uc.company_id),
            "company_name": uc.company.name,
            "is_default": uc.is_default,
        }
        for uc in UserCompany.objects.filter(user=user).select_related("company")
    ]


@router.post("/admin/user-companies/{user_id}/", response=list[UserCompanyOut])
def assign_user_companies(request, user_id: UUID, data: UserCompanyAssign):
    """Assign companies to a user (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    company_service.assign_user_to_companies(user, data.company_ids, data.default_id)
    return list_user_companies(request, user_id)


@router.delete("/admin/user-companies/{user_id}/{company_id}/")
def unassign_user_company(request, user_id: UUID, company_id: UUID):
    """Remove a company assignment from a user (admin only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=user_id)
        company = Company.objects.get(id=company_id)
    except (User.DoesNotExist, Company.DoesNotExist):
        raise HttpError(404, "User or company not found") from None
    company_service.unassign_user_from_company(user, company)
    return 204


# --- Parameterized routes (must come after static paths) ---


@router.get("/{id}/", response=CompanyOut)
def get_company(request, id: UUID):
    """Get company details."""
    try:
        company = Company.objects.get(id=id, is_active=True)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    if not request.auth.is_superuser:
        user_companies = company_service.get_user_companies(request.auth)
        if company not in user_companies:
            raise HttpError(403, "Access denied")
    return company


@router.put("/{id}/", response=CompanyOut)
def update_company(request, id: UUID, data: CompanyUpdate):
    """Update company details."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can update companies")
    try:
        company = Company.objects.get(id=id)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    update_data = data.model_dump(exclude_unset=True)
    parent_id = update_data.pop("parent_id", None)
    if parent_id is not None:
        try:
            update_data["parent"] = Company.objects.get(id=parent_id)
        except Company.DoesNotExist:
            raise HttpError(400, "Parent company not found") from None
    for field, value in update_data.items():
        setattr(company, field, value)
    company.save()
    return company


@router.delete("/{id}/")
def deactivate_company(request, id: UUID):
    """Soft-delete a company by setting is_active=False."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can deactivate companies")
    try:
        company = Company.objects.get(id=id)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    company.is_active = False
    company.save()
    return 204


@router.get("/{id}/children/", response=list[CompanyOut])
def get_company_children(request, id: UUID):
    """Get child companies."""
    try:
        company = Company.objects.get(id=id, is_active=True)
    except Company.DoesNotExist:
        raise HttpError(404, "Company not found") from None
    return company_service.get_company_children(company)


@router.post("/{id}/children/", response=CompanyOut)
def add_child_company(request, id: UUID, data: CompanyCreate):
    """Add a child company under the given parent."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can create companies")
    try:
        parent = Company.objects.get(id=id)
    except Company.DoesNotExist:
        raise HttpError(404, "Parent company not found") from None
    company = Company.objects.create(
        name=data.name,
        code=data.code,
        registration_number=data.registration_number,
        tax_number=data.tax_number,
        parent=parent,
        is_group=data.is_group,
        address=data.address or "",
        city=data.city or "",
        state=data.state or "",
        postcode=data.postcode or "",
        country=data.country or "MY",
        phone=data.phone or "",
        email=data.email or "",
        base_currency=data.base_currency or "MYR",
        date_format=data.date_format or "Y-m-d",
        timezone=data.timezone or "Asia/Kuala_Lumpur",
    )
    return company
