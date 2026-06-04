"""Tests for Chart of Accounts (T021)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.mixins.models import ConcurrencyError
from apps.core.models import Company, User
from apps.financial.models import Account, AccountCompany
from apps.financial.services.account_service import (
    create_account,
    delete_account,
    get_account_flat,
    get_account_tree,
    import_accounts_from_csv,
    set_company_assignments,
    update_account,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@test.com",
        password="admin123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def other_company(db):
    return Company.objects.create(name="Other Company", code="OC")


@pytest.fixture
def root_account(db):
    return Account.objects.create(
        code="1000", name="Assets", account_type="asset", level=0, is_group=True
    )


@pytest.fixture
def child_account(db, root_account):
    return Account.objects.create(
        code="1100",
        name="Current Assets",
        account_type="asset",
        subtype="current_asset",
        parent=root_account,
        level=1,
        is_group=True,
    )


@pytest.fixture
def leaf_account(db, child_account):
    return Account.objects.create(
        code="1110",
        name="Cash",
        account_type="asset",
        subtype="current_asset",
        parent=child_account,
        level=2,
    )


# ── Model Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestAccountModel:
    def test_create_account(self):
        account = Account.objects.create(
            code="9999", name="Test Account", account_type="asset"
        )
        assert account.code == "9999"
        assert str(account) == "9999 — Test Account"
        assert account.is_active is True
        assert account.level == 0

    def test_account_hierarchy(self, root_account, child_account, leaf_account):
        assert leaf_account.parent == child_account
        assert child_account.parent == root_account
        assert leaf_account.level == 2

    def test_account_str(self, root_account):
        assert str(root_account) == "1000 — Assets"


@pytest.mark.django_db
class TestAccountCompanyModel:
    def test_create_assignment(self, admin_user, company, root_account):
        ac = AccountCompany.objects.create(account=root_account, company=company)
        assert ac.is_active is True
        assert str(ac) == f"1000 - {company.name}"

    def test_unique_together(self, company, root_account):
        AccountCompany.objects.create(account=root_account, company=company)
        with pytest.raises(IntegrityError):
            AccountCompany.objects.create(account=root_account, company=company)

    def test_create_account(self, root_account):
        account = create_account(
            code="1111",
            name="Test",
            account_type="asset",
            parent_id=root_account.id,
        )
        assert account.code == "1111"
        assert account.parent_id == root_account.id
        assert account.level == 1

    def test_update_account(self, root_account):
        updated = update_account(root_account.id, name="Updated Assets")
        assert updated.name == "Updated Assets"

    def test_delete_leaf_account(self, leaf_account):
        result = delete_account(leaf_account.id)
        assert result is True
        assert not Account.objects.filter(id=leaf_account.id).exists()

    def test_delete_group_account_blocked(self, root_account, child_account):
        with pytest.raises(ConcurrencyError):
            delete_account(root_account.id)

    def test_get_account_tree(self, root_account, child_account, leaf_account):
        tree = get_account_tree()
        assert len(tree) > 0
        # Find the root account in the tree
        root_node = next((n for n in tree if n["code"] == "1000"), None)
        assert root_node is not None
        assert len(root_node["children"]) > 0


@pytest.mark.django_db
class TestCompanyAssignments:
    def test_set_company_assignments(
        self, company, root_account, child_account, leaf_account
    ):
        count = set_company_assignments(
            company.id,
            [root_account.id, child_account.id],
        )
        assert count == 2
        assert AccountCompany.objects.filter(company=company).count() == 2

    def test_set_company_assignments_replaces(
        self, company, root_account, child_account
    ):
        set_company_assignments(company.id, [root_account.id, child_account.id])
        set_company_assignments(company.id, [root_account.id])
        assert AccountCompany.objects.filter(company=company).count() == 1

    def test_get_account_flat_assigned(self, company, root_account, child_account):
        set_company_assignments(company.id, [root_account.id])
        results = get_account_flat(company_id=company.id)
        root_result = next((r for r in results if r["code"] == "1000"), None)
        assert root_result is not None
        assert root_result["is_assigned"] is True
        child_result = next((r for r in results if r["code"] == "1100"), None)
        assert child_result is not None
        assert child_result["is_assigned"] is False

    def test_tree_filtered_by_company(
        self, company, root_account, child_account, leaf_account
    ):
        set_company_assignments(company.id, [root_account.id, child_account.id])
        tree = get_account_tree(company_id=company.id)
        codes = {n["code"] for n in tree}
        assert "1000" in codes
        assert "1100" not in codes  # child is in tree under root, not top-level
        # root has children
        root_node = next(n for n in tree if n["code"] == "1000")
        assert len(root_node["children"]) == 1


@pytest.mark.django_db
class TestImportAccounts:
    def test_import_csv(self):
        content = "code,name,account_type,subtype,parent_code,mfrs_code\n"
        content += "1000,Assets,asset,,,\n"
        content += "1100,Current Assets,asset,current_asset,1000,\n"
        content += "1110,Cash,asset,current_asset,1100,\n"

        result = import_accounts_from_csv(content)
        assert result["created"] == 3
        assert Account.objects.count() == 3

    def test_import_csv_missing_fields(self):
        content = "code,name,account_type\n"
        content += "1000,,asset\n"
        result = import_accounts_from_csv(content)
        assert result["created"] == 0
        assert len(result["errors"]) > 0

    def test_import_csv_empty(self):
        content = "code,name,account_type\n"
        result = import_accounts_from_csv(content)
        assert result["created"] == 0
        assert result["total"] == 0


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAccountAPI:
    def _auth_header(self, user):
        token = AccessToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_list_accounts(self, client, admin_user, root_account):
        response = client.get(
            "/api/v1/financial/accounts/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

    def test_create_account(self, client, admin_user, root_account):
        response = client.post(
            "/api/v1/financial/accounts/",
            {
                "code": "9999",
                "name": "Test Account",
                "account_type": "asset",
                "parent_id": str(root_account.id),
            },
            content_type="application/json",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "9999"

    def test_delete_account(self, client, admin_user, leaf_account):
        response = client.delete(
            f"/api/v1/financial/accounts/{leaf_account.id}/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        assert not Account.objects.filter(id=leaf_account.id).exists()

    def test_delete_group_account_blocked(
        self, client, admin_user, root_account, child_account
    ):
        response = client.delete(
            f"/api/v1/financial/accounts/{root_account.id}/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 409

    def test_download_template(self, client, admin_user):
        response = client.get(
            "/api/v1/financial/accounts/template/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        assert "code" in response.content.decode()

    def test_list_assignments(self, client, admin_user, company, root_account):
        set_company_assignments(company.id, [root_account.id])
        response = client.get(
            f"/api/v1/financial/accounts/assignments/{company.id}/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        assert any(r["is_assigned"] for r in data["results"])

    def test_set_assignments(
        self, client, admin_user, company, root_account, child_account
    ):
        response = client.post(
            f"/api/v1/financial/accounts/assignments/{company.id}/",
            {"account_ids": [str(root_account.id), str(child_account.id)]},
            content_type="application/json",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_count"] == 2

    def test_import_csv_api(self, client, admin_user):
        csv_content = b"code,name,account_type\n9999,Test,asset\n"
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = client.post(
            "/api/v1/financial/accounts/import/",
            {"file": file},
            **self._auth_header(admin_user),
        )
        assert response.status_code == 200
