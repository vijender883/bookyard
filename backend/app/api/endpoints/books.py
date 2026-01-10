from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlmodel import Session, select, or_
from app.models.book import Book, Profile
from app.core.auth import get_current_user
from app.db.session import get_session
import uuid

router = APIRouter()

@router.get("/", response_model=List[Book])
async def list_books(
    session: Session = Depends(get_session),
    search: Optional[str] = Query(None, description="Search by title or author"),
    category_id: Optional[int] = Query(None, description="Filter by category")
):
    """
    Retrieve all books with optional search and category filters.
    """
    statement = select(Book)
    if category_id:
        statement = statement.where(Book.category_id == category_id)
    if search:
        # Simple search logic for now, using GIN index in Postgres
        statement = statement.where(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%")
            )
        )
    
    books = session.exec(statement).all()
    return books

@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: int, session: Session = Depends(get_session)):
    """
    Retrieve a specific book by ID.
    """
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book

@router.post("/", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_in: Book, # Using full model for demo simplicity
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Create a new book. Sets the authenticated user as the owner.
    """
    user_id = uuid.UUID(user["sub"])
    # Ensure profile exists
    profile = session.get(Profile, user_id)
    if not profile:
        profile = Profile(id=user_id)
        session.add(profile)
    
    book_in.owner_id = user_id
    session.add(book_in)
    session.commit()
    session.refresh(book_in)
    return book_in

@router.put("/{book_id}", response_model=Book)
async def update_book(
    book_id: int, 
    book_in: Book, 
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Update a book. Only the owner can update.
    """
    db_book = session.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    user_id = uuid.UUID(user["sub"])
    if db_book.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this book")
    
    book_data = book_in.model_dump(exclude_unset=True)
    for key, value in book_data.items():
        if key not in ["id", "owner_id", "created_at"]:
            setattr(db_book, key, value)
    
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int, 
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    """
    Delete a book. Only the owner can delete.
    """
    db_book = session.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    user_id = uuid.UUID(user["sub"])
    if db_book.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")
        
    session.delete(db_book)
    session.commit()
    return None
