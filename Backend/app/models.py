from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint, CheckConstraint
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EventStatus(Enum):
    DRAFT = "draft"
    OPEN = "open"
    ASSIGNED = "assigned"
    FINISHED = "finished"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=45, nullable=False)
    password: str = Field(nullable=False)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default=datetime.utcnow())

    participants: List["Participant"] = Relationship(back_populates="user")


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=45, nullable=False)
    date: datetime = Field(nullable=False)
    status: EventStatus = Field(nullable=False)
    created_at: datetime = Field(default=datetime.utcnow())

    participants: List["Participant"] = Relationship(back_populates="event")
    assignments: List["Assignment"] = Relationship(back_populates="event")


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    event_id: int = Field(foreign_key="event.id")
    message: Optional[str] = None

    user: User = Relationship(back_populates="participants")
    event: Event = Relationship(back_populates="participants")
    assignments: List["Assignment"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": ["Assignment.receiver_id"]},
    )
    assignments: List["Assignment"] = Relationship(
        back_populates="gifter",
        sa_relationship_kwargs={"foreign_keys": ["Assignment.gifter_id"]},
    )

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="unique_participant"),
    )


class Assignment(SQLModel, table=True):
    receiver_id: int = Field(foreign_key="participant.id", primary_key=True)
    gifter_id: int = Field(foreign_key="participant.id", primary_key=True)
    event_id: int = Field(foreign_key="event.id", primary_key=True)

    event: Event = Relationship(back_populates="assignments")

    receiver: Participant = Relationship(
        back_populates="assignments",
        sa_relationship_kwargs={"foreign_keys": [receiver_id]},
    )
    gifter: Participant = Relationship(
        back_populates="assignments",
        sa_relationship_kwargs={"foreign_keys": [gifter_id]},
    )

    __table_args__ = (
        CheckConstraint("receiver_id != gifter_id", name="no_self_assignment"),
    )
