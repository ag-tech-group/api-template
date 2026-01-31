from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Base schema with shared note fields."""

    title: str = Field(..., min_length=1, max_length=200, examples=["Meeting notes"])
    body: str | None = Field(None, examples=["Discussed project timeline and milestones."])


class NoteCreate(NoteBase):
    """Schema for creating a new note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note. All fields optional."""

    title: str | None = Field(None, min_length=1, max_length=200)
    body: str | None = None


class NoteRead(NoteBase):
    """Schema for reading a note (includes id and timestamps)."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
