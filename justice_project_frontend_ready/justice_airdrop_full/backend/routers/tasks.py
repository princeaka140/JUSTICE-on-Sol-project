from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from ..database import SessionLocal, Task, Submission, User, Notification
from typing import List, Optional
from ..helpers import require_verified
from ..helpers import send_telegram_message
from ..helpers import is_user_member_of, post_submission_for_review
from ..config import settings
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(ROOT) / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CreateTask(BaseModel):
    title: str
    instruction: Optional[str] = None
    link: Optional[str] = None
    reward: float = 0.0

@router.post('/add')
def add_task(payload: CreateTask, db=Depends(get_db)):
    t = Task(title=payload.title, instruction=payload.instruction, link=payload.link, reward=payload.reward)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"ok": True, "task_id": t.id}

@router.get('/list')
def list_tasks(db=Depends(get_db), verified_user=Depends(require_verified)):
    """Return active tasks. Access requires verified user (Telegram WebApp auth or x-user-id header)."""
    tasks = db.query(Task).filter(Task.active == True).all()
    return tasks

@router.post('/submit')
async def submit_task(telegram_id: str = '', task_id: int = 0, proof_text: Optional[str] = None, file: UploadFile | None = File(None), db=Depends(get_db), verified_user=Depends(require_verified)):
    # note: expecting multipart form with fields telegram_id, task_id, proof_text, and optional file
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    # ensure user is member of group and channel
    try:
        ok_group = is_user_member_of(settings.ADMIN_GROUP_ID, int(telegram_id))
        ok_channel = is_user_member_of(settings.ADMIN_CHANNEL_ID, int(telegram_id))
    except Exception:
        ok_group = ok_channel = False
    if not (ok_group and ok_channel):
        try:
            send_telegram_message(telegram_id, "You must join the official group and channel before using the bot. Please join and try again.")
        except Exception:
            pass
        raise HTTPException(status_code=403, detail='User must join group and channel')

    file_url = None
    if file:
        fname = f"{uuid.uuid4().hex}_{file.filename}"
        dest = UPLOAD_DIR / fname
        with open(dest, 'wb') as f:
            f.write(await file.read())
        file_url = f"/static/uploads/{fname}"

    submission = Submission(user_id=user.id, task_id=int(task_id), proof=(proof_text or '') + (f"\nFile: {file_url}" if file_url else ''))
    db.add(submission)
    db.commit()
    db.refresh(submission)
    # create notification for admins and post to channel
    try:
        post_submission_for_review(settings.ADMIN_CHANNEL_ID, submission.id, user.telegram_id, submission.proof)
    except Exception:
        pass
    return {"ok": True, "submission_id": submission.id}


@router.get('/my_submissions')
def my_submissions(db=Depends(get_db), verified_user=Depends(require_verified)):
    user = verified_user
    subs = db.query(Submission).filter(Submission.user_id == user.id).order_by(Submission.created_at.desc()).all()
    return [{"id": s.id, "task_id": s.task_id, "status": s.status, "proof": s.proof, "created_at": s.created_at.isoformat()} for s in subs]
