from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteRead])
async def list_notes(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
    skip: int = 0,
    limit: int = 100,
):
    """List the current user's notes."""
    result = await session.execute(
        select(Note)
        .where(Note.user_id == user.id)
        .order_by(Note.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Get a single note by ID (must belong to current user)."""
    note = await session.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_in: NoteCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Create a new note for the current user."""
    note = Note(**note_in.model_dump(), user_id=user.id)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: UUID,
    note_in: NoteUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Update a note (must belong to current user)."""
    note = await session.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = note_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    await session.commit()
    await session.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Delete a note (must belong to current user)."""
    note = await session.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    await session.delete(note)
    await session.commit()
