from uuid import uuid4

from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Racer(Base):
    """Mario Kart racer with stats.

    Stats are integers from 1-10, matching the in-game display.
    """

    __tablename__ = "racers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    weight: Mapped[int]
    acceleration: Mapped[int]
    speed: Mapped[int]

    __table_args__ = (
        CheckConstraint("weight >= 1 AND weight <= 10", name="weight_range"),
        CheckConstraint("acceleration >= 1 AND acceleration <= 10", name="acceleration_range"),
        CheckConstraint("speed >= 1 AND speed <= 10", name="speed_range"),
    )

    def __repr__(self) -> str:
        return f"<Racer {self.name}>"
