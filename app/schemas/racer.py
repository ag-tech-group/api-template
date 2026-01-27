from pydantic import BaseModel, Field


class RacerBase(BaseModel):
    """Base schema with shared racer fields."""

    name: str = Field(..., min_length=1, max_length=100, examples=["Mario"])
    weight: int = Field(..., ge=1, le=10, description="Weight class (1=light, 10=heavy)")
    acceleration: int = Field(..., ge=1, le=10, description="Acceleration stat")
    speed: int = Field(..., ge=1, le=10, description="Top speed stat")


class RacerCreate(RacerBase):
    """Schema for creating a new racer."""

    pass


class RacerUpdate(BaseModel):
    """Schema for updating a racer. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=100)
    weight: int | None = Field(None, ge=1, le=10)
    acceleration: int | None = Field(None, ge=1, le=10)
    speed: int | None = Field(None, ge=1, le=10)


class RacerRead(RacerBase):
    """Schema for reading a racer (includes id)."""

    id: str

    model_config = {"from_attributes": True}
