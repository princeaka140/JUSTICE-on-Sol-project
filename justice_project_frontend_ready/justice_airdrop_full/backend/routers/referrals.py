from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import SessionLocal, User
import uuid

router = APIRouter(prefix="/referrals", tags=["referrals"])

# --- DB Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Get stats for a user ---
@router.get("/")
def referral_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user.username,
        "referrals": user.referrals,
        "balance": user.balance,
        "referral_link": user.referral_link or f"https://yoursite.com/register?ref={user.referral_code}"
    }

# --- Leaderboard ---
@router.get("/leaderboard")
def leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.referrals.desc()).limit(limit).all()
    return [
        {"username": r.username or "Anonymous", "referrals": r.referrals, "balance": r.balance}
        for r in rows
    ]

# --- Rank ---
@router.get("/rank")
def user_rank(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    higher = db.query(User).filter(User.referrals > user.referrals).count()
    rank = higher + 1
    total = db.query(User).count()

    return {
        "username": user.username,
        "referrals": user.referrals,
        "rank": rank,
        "total_users": total
    }

# --- Generate referral link ---
@router.post("/generate")
def generate_link(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    unique_code = str(uuid.uuid4())[:8]
    link = f"https://yoursite.com/register?ref={unique_code}"

    user.referral_code = unique_code
    user.referral_link = link

    db.commit()
    db.refresh(user)

    return {"link": link, "code": unique_code}

# --- Register referral ---
@router.post("/register")
def register_referral(
    referrer_code: str = Body(...),
    referred_telegram_id: str = Body(...),
    db: Session = Depends(get_db)
):
    referrer = db.query(User).filter(User.referral_code == referrer_code).first()
    if not referrer:
        raise HTTPException(status_code=404, detail="Referrer not found")

    if str(referrer.telegram_id) == str(referred_telegram_id):
        raise HTTPException(status_code=400, detail="Cannot refer yourself")

    referred = db.query(User).filter(User.telegram_id == referred_telegram_id).first()
    if not referred:
        referred = User(telegram_id=referred_telegram_id, referrals=0, balance=0)
        db.add(referred)
        db.commit()
        db.refresh(referred)

    referrer.referrals += 1
    referrer.balance += 10  # optional reward

    db.commit()
    db.refresh(referrer)

    return {"ok": True, "referrer_id": referrer.id, "referrals": referrer.referrals, "balance": referrer.balance}
