from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
import uuid

class UserRole(str, Enum):
    PARENT = "parent"
    KID = "kid"

class Intent(str, Enum):
    GIVEAWAY = "giveaway"
    SELL = "sell"
    SHARE = "share"

class ReservationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Profile(SQLModel, table=True):
    __tablename__ = "profile"
    id: uuid.UUID = Field(primary_key=True)
    username: Optional[str] = Field(default=None, unique=True)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole = Field(default=UserRole.PARENT)
    parent_id: Optional[uuid.UUID] = Field(default=None, foreign_key="profile.id")
    credits: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    books: List["Book"] = Relationship(back_populates="owner")
    reservations: List["Reservation"] = Relationship(back_populates="borrower")

class Category(SQLModel, table=True):
    __tablename__ = "category"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    books: List["Book"] = Relationship(back_populates="category")

class Book(SQLModel, table=True):
    __tablename__ = "book"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    author: str = Field(index=True)
    description: Optional[str] = None
    isbn: Optional[str] = None
    published_year: Optional[int] = None
    pages: Optional[int] = None
    price: Optional[float] = None
    stock_count: int = Field(default=1)
    intent: Intent = Field(default=Intent.SHARE)
    is_active: bool = Field(default=True)
    
    owner_id: uuid.UUID = Field(foreign_key="profile.id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    owner: Profile = Relationship(back_populates="books")
    category: Optional[Category] = Relationship(back_populates="books")
    reservations: List["Reservation"] = Relationship(back_populates="book")

class Reservation(SQLModel, table=True):
    __tablename__ = "reservation"
    id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="book.id")
    borrower_id: uuid.UUID = Field(foreign_key="profile.id")
    status: ReservationStatus = Field(default=ReservationStatus.PENDING)
    
    start_date: datetime
    end_date: datetime
    credits_used: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    book: Book = Relationship(back_populates="reservations")
    borrower: Profile = Relationship(back_populates="reservations")

class CreditsHistory(SQLModel, table=True):
    __tablename__ = "creditshistory"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="profile.id")
    amount: int
    type: str # daily_bonus, share_bonus, purchase, reservation_spend
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FeedItem(SQLModel, table=True):
    __tablename__ = "feeditem"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="profile.id")
    action_type: str # upload, reservation
    content: str
    feed_metadata: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
    is_public: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
