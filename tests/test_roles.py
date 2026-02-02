from uuid import uuid4

from httpx import AsyncClient

from app.auth import current_active_user
from app.main import app
from app.models.user import User


class TestRoleAccess:
    """Test that role-based access control works correctly."""

    async def test_admin_can_access_admin_route(
        self, admin_client: AsyncClient, admin_user: User, session
    ):
        """Admin users can access admin-gated endpoints."""
        # Create a target user in the DB to update
        target = User(id=uuid4(), email="target@example.com", hashed_password="fake")
        session.add(target)
        await session.commit()

        response = await admin_client.patch(
            f"/admin/users/{target.id}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 200

    async def test_regular_user_gets_403(self, auth_client: AsyncClient, test_user: User):
        """Regular users are forbidden from admin endpoints."""
        response = await auth_client.patch(
            f"/admin/users/{uuid4()}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    async def test_superuser_bypasses_role_check(
        self, client: AsyncClient, superuser: User, session
    ):
        """Superusers can access admin endpoints regardless of their role."""
        app.dependency_overrides[current_active_user] = lambda: superuser
        try:
            target = User(id=uuid4(), email="target2@example.com", hashed_password="fake")
            session.add(target)
            await session.commit()

            response = await client.patch(
                f"/admin/users/{target.id}/role",
                json={"role": "admin"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(current_active_user, None)


class TestRoleUpdate:
    """Test the PATCH /admin/users/{user_id}/role endpoint."""

    async def test_update_role_success(self, admin_client: AsyncClient, admin_user: User, session):
        """Successfully update a user's role."""
        target = User(id=uuid4(), email="target3@example.com", hashed_password="fake")
        session.add(target)
        await session.commit()

        response = await admin_client.patch(
            f"/admin/users/{target.id}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["email"] == "target3@example.com"

    async def test_invalid_role_returns_422(
        self, admin_client: AsyncClient, admin_user: User, session
    ):
        """Invalid role value returns 422."""
        target = User(id=uuid4(), email="target4@example.com", hashed_password="fake")
        session.add(target)
        await session.commit()

        response = await admin_client.patch(
            f"/admin/users/{target.id}/role",
            json={"role": "supervillain"},
        )
        assert response.status_code == 422

    async def test_user_not_found_returns_404(self, admin_client: AsyncClient, admin_user: User):
        """Updating a non-existent user returns 404."""
        response = await admin_client.patch(
            f"/admin/users/{uuid4()}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"


class TestAuthMeIncludesRole:
    """Test that /auth/me returns the role field."""

    async def test_me_returns_role_for_regular_user(self, client: AsyncClient):
        user = User(
            id=uuid4(),
            email="me@example.com",
            hashed_password="fake",
            role="user",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
        app.dependency_overrides[current_active_user] = lambda: user
        try:
            response = await client.get("/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "user"
        finally:
            app.dependency_overrides.pop(current_active_user, None)

    async def test_me_returns_role_for_admin(self, client: AsyncClient):
        user = User(
            id=uuid4(),
            email="meadmin@example.com",
            hashed_password="fake",
            role="admin",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
        app.dependency_overrides[current_active_user] = lambda: user
        try:
            response = await client.get("/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "admin"
        finally:
            app.dependency_overrides.pop(current_active_user, None)
