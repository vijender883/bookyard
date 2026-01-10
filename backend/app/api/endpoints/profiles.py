from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.models.book import Profile
from app.core.auth import get_current_user
from app.db.session import get_session
import uuid

router = APIRouter()

@router.get("/me", response_model=Profile)
async def get_my_profile(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    user_id = uuid.UUID(user["sub"])
    profile = session.get(Profile, user_id)
    if not profile:
        # Auto-create profile if it doesn't exist
        profile = Profile(id=user_id, username=user.get("username"))
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile

@router.get("/{profile_id}", response_model=Profile)
async def get_profile(
    profile_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """
    Get a specific profile by ID.
    """
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

@router.post("/credits/daily-bonus")
async def claim_daily_bonus(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Claim daily credit bonus (1 credit per day).
    Logic for verifying 'per day' should be added here.
    """
    user_id = uuid.UUID(user["sub"])
    profile = session.get(Profile, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile.credits += 1
    session.add(profile)
    session.commit()
    return {"message": "Daily bonus claimed", "credits": profile.credits}
