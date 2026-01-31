from uuid import uuid4

from httpx import AsyncClient

from app.auth import current_active_user
from app.main import app
from app.models.note import Note
from app.models.user import User


class TestListNotes:
    async def test_list_empty(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.get("/notes")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_data(self, client: AsyncClient, test_user: User, session):
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Test note", body="Some content", user_id=test_user.id)
        session.add(note)
        await session.commit()

        response = await client.get("/notes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test note"

    async def test_user_isolation(
        self, client: AsyncClient, test_user: User, other_user: User, session
    ):
        """Users can only see their own notes."""
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Other's note", body="Private", user_id=other_user.id)
        session.add(note)
        await session.commit()

        response = await client.get("/notes")
        assert response.status_code == 200
        assert response.json() == []


class TestCreateNote:
    async def test_create_success(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.post(
            "/notes",
            json={"title": "My note", "body": "Hello world"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My note"
        assert data["body"] == "Hello world"
        assert "id" in data
        assert "created_at" in data

    async def test_create_without_body(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.post("/notes", json={"title": "Title only"})
        assert response.status_code == 201
        assert response.json()["body"] is None

    async def test_create_invalid_title(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.post("/notes", json={"title": ""})
        assert response.status_code == 422


class TestGetNote:
    async def test_get_existing(self, client: AsyncClient, test_user: User, session):
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Get me", user_id=test_user.id)
        session.add(note)
        await session.commit()
        await session.refresh(note)

        response = await client.get(f"/notes/{note.id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get me"

    async def test_get_not_found(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.get(f"/notes/{uuid4()}")
        assert response.status_code == 404

    async def test_get_other_users_note(
        self, client: AsyncClient, test_user: User, other_user: User, session
    ):
        """Cannot access another user's note."""
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Private", user_id=other_user.id)
        session.add(note)
        await session.commit()
        await session.refresh(note)

        response = await client.get(f"/notes/{note.id}")
        assert response.status_code == 404


class TestUpdateNote:
    async def test_update_partial(self, client: AsyncClient, test_user: User, session):
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Original", body="Original body", user_id=test_user.id)
        session.add(note)
        await session.commit()
        await session.refresh(note)

        response = await client.patch(f"/notes/{note.id}", json={"title": "Updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["body"] == "Original body"

    async def test_update_not_found(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.patch(f"/notes/{uuid4()}", json={"title": "Nope"})
        assert response.status_code == 404


class TestDeleteNote:
    async def test_delete_success(self, client: AsyncClient, test_user: User, session):
        app.dependency_overrides[current_active_user] = lambda: test_user
        note = Note(title="Delete me", user_id=test_user.id)
        session.add(note)
        await session.commit()
        await session.refresh(note)

        response = await client.delete(f"/notes/{note.id}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/notes/{note.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[current_active_user] = lambda: test_user
        response = await client.delete(f"/notes/{uuid4()}")
        assert response.status_code == 404
