from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.racer import Racer
from app.models.user import User
from app.schemas.racer import RacerCreate, RacerRead, RacerUpdate

router = APIRouter(prefix="/racers", tags=["racers"])


@router.get("", response_model=list[RacerRead])
async def list_racers(
    session: AsyncSession = Depends(get_async_session),
    skip: int = 0,
    limit: int = 100,
):
    """List all racers with optional pagination."""
    result = await session.execute(select(Racer).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{racer_id}", response_model=RacerRead)
async def get_racer(
    racer_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a single racer by ID."""
    racer = await session.get(Racer, racer_id)
    if not racer:
        raise HTTPException(status_code=404, detail="Racer not found")
    return racer


@router.post("", response_model=RacerRead, status_code=status.HTTP_201_CREATED)
async def create_racer(
    racer_in: RacerCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),  # Remove this line to disable auth
):
    """Create a new racer. Requires authentication."""
    # Check for duplicate name
    existing = await session.execute(select(Racer).where(Racer.name == racer_in.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Racer with this name already exists")

    racer = Racer(**racer_in.model_dump())
    session.add(racer)
    await session.commit()
    await session.refresh(racer)
    return racer


@router.patch("/{racer_id}", response_model=RacerRead)
async def update_racer(
    racer_id: str,
    racer_in: RacerUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),  # Remove this line to disable auth
):
    """Update a racer. Requires authentication."""
    racer = await session.get(Racer, racer_id)
    if not racer:
        raise HTTPException(status_code=404, detail="Racer not found")

    update_data = racer_in.model_dump(exclude_unset=True)

    # Check for duplicate name if name is being updated
    if "name" in update_data:
        existing = await session.execute(
            select(Racer).where(Racer.name == update_data["name"], Racer.id != racer_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Racer with this name already exists")

    for field, value in update_data.items():
        setattr(racer, field, value)

    await session.commit()
    await session.refresh(racer)
    return racer


@router.delete("/{racer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_racer(
    racer_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),  # Remove this line to disable auth
):
    """Delete a racer. Requires authentication."""
    racer = await session.get(Racer, racer_id)
    if not racer:
        raise HTTPException(status_code=404, detail="Racer not found")

    await session.delete(racer)
    await session.commit()
