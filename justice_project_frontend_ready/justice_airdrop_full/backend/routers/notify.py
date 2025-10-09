from fastapi import APIRouter, BackgroundTasks, Request, Depends, HTTPException
from pydantic import BaseModel
from ..helpers import require_owner, send_telegram_message
from ..database import SessionLocal, User, Notification
from typing import List, Optional
import datetime

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class NotifyUser(BaseModel):
    telegram_id: str
    message: str


@router.post('/user')
def notify_user(payload: NotifyUser, background_tasks: BackgroundTasks, db=Depends(get_db)):
    # store notification in DB and optionally send to telegram
    n = Notification(target_type='user', target_id=str(payload.telegram_id), message=payload.message)
    db.add(n); db.commit(); db.refresh(n)

    def send():
        try:
            send_telegram_message(payload.telegram_id, payload.message)
        except Exception:
            pass

    background_tasks.add_task(send)
    return {"ok": True, "notification_id": n.id}


class NotifyGroup(BaseModel):
    group_id: str
    message: str
    ttl: int = 120


@router.post('/group')
def notify_group(payload: NotifyGroup, background_tasks: BackgroundTasks, db=Depends(get_db)):
    n = Notification(target_type='group', target_id=str(payload.group_id), message=payload.message)
    db.add(n); db.commit(); db.refresh(n)

    def send():
        try:
            send_telegram_message(payload.group_id, payload.message)
        except Exception:
            pass

    background_tasks.add_task(send)
    return {"ok": True, "notification_id": n.id}


@router.get('/user/{telegram_id}')
def get_notifications(telegram_id: str, limit: int = 50, db=Depends(get_db)):
    notes = db.query(Notification).filter(Notification.target_type == 'user', Notification.target_id == str(telegram_id)).order_by(Notification.created_at.desc()).limit(limit).all()
    return {"notifications": [{"id": n.id, "message": n.message, "created_at": n.created_at.isoformat(), "read": n.read} for n in notes]}


@router.get('/count/{telegram_id}')
def get_notification_count(telegram_id: str, db=Depends(get_db)):
    c = db.query(Notification).filter(Notification.target_type == 'user', Notification.target_id == str(telegram_id), Notification.read == False).count()
    return {"count": c}


@router.post('/read/{telegram_id}')
def mark_read(telegram_id: str, db=Depends(get_db)):
    updated = db.query(Notification).filter(Notification.target_type == 'user', Notification.target_id == str(telegram_id), Notification.read == False).update({"read": True})
    db.commit()
    return {"ok": True, "marked": updated}


@router.post('/read_one/{notification_id}')
def mark_read_one(notification_id: int, db=Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == int(notification_id)).first()
    if not n:
        raise HTTPException(status_code=404, detail='notification not found')
    n.read = True
    db.add(n); db.commit()
    return {"ok": True, "id": n.id}

