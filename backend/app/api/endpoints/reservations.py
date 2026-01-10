from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.models.book import Book, Reservation, Profile, ReservationStatus
from app.core.auth import get_current_user
from app.db.session import get_session
import uuid

router = APIRouter()

@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    reservation_in: Reservation, # Simplified for demo, should use a Create schema
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Reserve a book using credits.
    """
    user_id = uuid.UUID(user["sub"])
    profile = session.get(Profile, user_id)
    book = session.get(Book, reservation_in.book_id)
    
    if not book or not book.is_active:
        raise HTTPException(status_code=404, detail="Book not available")
    
    if profile.credits < reservation_in.credits_used:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    profile.credits -= reservation_in.credits_used
    reservation_in.borrower_id = user_id
    reservation_in.status = ReservationStatus.PENDING
    
    session.add(profile)
    session.add(reservation_in)
    session.commit()
    session.refresh(reservation_in)
    return reservation_in

@router.get("/my", response_model=List[Reservation])
async def list_my_reservations(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    List current user's reservations.
    """
    user_id = uuid.UUID(user["sub"])
    statement = select(Reservation).where(Reservation.borrower_id == user_id)
    results = session.exec(statement)
    return results.all()
