from httpx import AsyncClient

from app.auth import current_active_user
from app.main import app
from app.models.racer import Racer
from app.models.user import User


# Mock user for authenticated endpoints
def mock_current_user():
    return User(id="test-user-id", email="test@example.com", hashed_password="fake")


# Override auth dependency for tests
app.dependency_overrides[current_active_user] = mock_current_user


class TestListRacers:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/racers")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_data(self, client: AsyncClient, session):
        # Create test data directly in DB
        racer = Racer(name="Mario", weight=5, acceleration=5, speed=5)
        session.add(racer)
        await session.commit()

        response = await client.get("/racers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Mario"


class TestCreateRacer:
    async def test_create_success(self, client: AsyncClient):
        response = await client.post(
            "/racers",
            json={"name": "Luigi", "weight": 4, "acceleration": 6, "speed": 5},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Luigi"
        assert data["weight"] == 4
        assert "id" in data

    async def test_create_duplicate_name(self, client: AsyncClient, session):
        # Create existing racer
        racer = Racer(name="Peach", weight=3, acceleration=7, speed=4)
        session.add(racer)
        await session.commit()

        # Try to create duplicate
        response = await client.post(
            "/racers",
            json={"name": "Peach", "weight": 3, "acceleration": 7, "speed": 4},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_invalid_stats(self, client: AsyncClient):
        response = await client.post(
            "/racers",
            json={"name": "Invalid", "weight": 15, "acceleration": 5, "speed": 5},
        )
        assert response.status_code == 422  # Validation error


class TestGetRacer:
    async def test_get_existing(self, client: AsyncClient, session):
        racer = Racer(name="Toad", weight=2, acceleration=8, speed=3)
        session.add(racer)
        await session.commit()
        await session.refresh(racer)

        response = await client.get(f"/racers/{racer.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Toad"

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/racers/nonexistent-id")
        assert response.status_code == 404


class TestUpdateRacer:
    async def test_update_partial(self, client: AsyncClient, session):
        racer = Racer(name="Bowser", weight=10, acceleration=2, speed=6)
        session.add(racer)
        await session.commit()
        await session.refresh(racer)

        response = await client.patch(
            f"/racers/{racer.id}",
            json={"speed": 7},  # Only update speed
        )
        assert response.status_code == 200
        data = response.json()
        assert data["speed"] == 7
        assert data["weight"] == 10  # Unchanged

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch(
            "/racers/nonexistent-id",
            json={"speed": 5},
        )
        assert response.status_code == 404


class TestDeleteRacer:
    async def test_delete_success(self, client: AsyncClient, session):
        racer = Racer(name="Yoshi", weight=4, acceleration=6, speed=5)
        session.add(racer)
        await session.commit()
        await session.refresh(racer)

        response = await client.delete(f"/racers/{racer.id}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/racers/{racer.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/racers/nonexistent-id")
        assert response.status_code == 404
