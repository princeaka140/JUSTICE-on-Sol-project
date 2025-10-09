# backend/routers/account.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal, User

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/account")
def get_account(user_id: int = Query(..., description="User ID to fetch"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user.username,
        "balance": user.balance,
        "wallet_connected": bool(user.wallet),
        "wallet_address": user.wallet,
        "photo_url": f"/static/photos/{user.id}.jpg",  # optional placeholder
        "verified": user.verified,
        "created_at": user.created_at
    }
