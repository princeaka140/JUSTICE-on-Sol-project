from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SessionLocal, User
from typing import Optional

router = APIRouter()

class StartRequest(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    device_hash: Optional[str] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post('/start')
def start(req: StartRequest, db=Depends(get_db)):
    # create user if not exists
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        user = User(telegram_id=req.telegram_id, username=req.username, device_hash=req.device_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
    # respond with required join links and status
    return {"verified": user.verified, "required": {"group": True, "channel": True}}

@router.post('/verify')
def verify(telegram_id: str, device_hash: Optional[str] = None, db=Depends(get_db)):
    # This endpoint should be called after Telegram membership check + captcha on frontend
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    if device_hash and user.device_hash and user.device_hash != device_hash:
        # device already registered -> deny
        raise HTTPException(status_code=403, detail='Device already used')
    user.verified = True
    if device_hash:
        user.device_hash = device_hash
    db.add(user)
    db.commit()
    return {"ok": True, "verified": True}
