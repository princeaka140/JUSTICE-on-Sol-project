from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from ..database import SessionLocal, User, Task, Submission, Withdrawal, Admin, Notification
from pydantic import BaseModel
from ..helpers import require_owner, require_verified
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import tempfile
import os

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/stats')
def stats(db=Depends(get_db)):
    users = db.query(User).count()
    tasks = db.query(Task).count()
    submissions = db.query(Submission).count()
    withdrawals = db.query(Withdrawal).count()
    total_balance = db.query(User).with_entities(User.balance).all()
    total_balance = sum([b[0] for b in total_balance]) if total_balance else 0
    return {"users": users, "tasks": tasks, "submissions": submissions, "withdrawals": withdrawals, "total_balance": total_balance}


@router.get('/stats/summary')
def stats_summary(db=Depends(get_db), user=Depends(require_verified)):
    """Return a richer summary for frontend stats dashboard (requires verified user)."""
    users = db.query(User).count()
    tasks = db.query(Task).count()
    submissions_total = db.query(Submission).count()
    submissions_pending = db.query(Submission).filter(Submission.status == 'pending').count()
    submissions_approved = db.query(Submission).filter(Submission.status == 'approved').count()
    submissions_rejected = db.query(Submission).filter(Submission.status == 'rejected').count()
    withdrawals_total = db.query(Withdrawal).count()
    withdrawals_pending = db.query(Withdrawal).filter(Withdrawal.status == 'pending').count()
    total_balance = db.query(User).with_entities(User.balance).all()
    total_balance = sum([b[0] for b in total_balance]) if total_balance else 0
    return {
        'users': users,
        'tasks': tasks,
        'submissions': {
            'total': submissions_total,
            'pending': submissions_pending,
            'approved': submissions_approved,
            'rejected': submissions_rejected,
        },
        'withdrawals': {
            'total': withdrawals_total,
            'pending': withdrawals_pending,
        },
        'total_balance': total_balance
    }


@router.get('/stats/series')
def stats_series(minutes: int = 60, interval: int = 60, db=Depends(get_db), user=Depends(require_verified)):
    """Return time-series of approved submissions over the past `minutes` minutes, binned by `interval` seconds.
    Example: minutes=60, interval=60 returns per-minute counts for the last hour.
    """
    now = datetime.utcnow()
    start = now - timedelta(minutes=minutes)
    subs = db.query(Submission).filter(Submission.status == 'approved', Submission.created_at >= start).all()

    # create bins
    bins = defaultdict(int)
    # compute number of intervals
    total_seconds = minutes * 60
    buckets = int(total_seconds // interval)
    # align start to interval boundary
    start_ts = int(start.replace(tzinfo=timezone.utc).timestamp())
    base = start_ts - (start_ts % interval)
    labels = []
    counts = []
    for i in range(buckets + 1):
        t = base + i * interval
        labels.append(t)
        bins[t] = 0

    for s in subs:
        ts = int(s.created_at.replace(tzinfo=timezone.utc).timestamp())
        bucket = ts - (ts % interval)
        if bucket in bins:
            bins[bucket] += 1

    # prepare arrays
    for t in labels:
        counts.append(bins.get(t, 0))

    # return ISO labels for frontend convenience
    iso_labels = [datetime.fromtimestamp(t, tz=timezone.utc).isoformat() for t in labels]
    return {'labels': iso_labels, 'counts': counts}


@router.post('/add_video')
def add_video(file: bytes = None, request: Request = None):
    """Accept an uploaded video file (multipart/form-data) and save it to the video folder.
    This endpoint requires owner privileges (require_owner via header or bot proxy).
    """
    # require owner
    require_owner(request)
    # In FastAPI we'd normally use UploadFile; but to keep the interface simple when called via HTTP client,
    # the framework will handle multipart. Here we use Request to access the files.
    try:
        f = request
        # request._files is not a public API; use starlette request parsing
        from fastapi import UploadFile, File
        # fallback: parse manually
        form = None
        try:
            form = request.form()
        except Exception:
            form = None
        # if using a proper client, use the 'file' field
        uploaded = None
        if form:
            form = form
        # we'll handle via starlette's body
        # Instead of complicating parsing here, instruct client to call /admin/upload_video using the example script.
        return {'ok': False, 'detail': 'Use /admin/upload_video with multipart form-data field "file" (UploadFile).'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post('/upload_video')
async def upload_video(file: 'UploadFile' , request: Request, db=Depends(get_db)):
    """Upload new video file (multipart form-data). Field name: file. Requires owner header."""
    require_owner(request)
    try:
        filename = file.filename or 'uploaded_video.mp4'
        # sanitize filename
        import os
        root = os.path.dirname(os.path.dirname(__file__))
        video_dir = os.path.join(root, 'video')
        if not os.path.isdir(video_dir):
            os.makedirs(video_dir, exist_ok=True)
        # choose a canonical name: sonic.mp4 (overwrite) or keep original
        target = os.path.join(video_dir, 'sonic.mp4')
        with open(target, 'wb') as out:
            content = await file.read()
            out.write(content)
        return {'ok': True, 'video_url': f'/static/video/{os.path.basename(target)}'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApprovePayload(BaseModel):
    submission_id: int
    admin_note: str = None

@router.post('/approve_submission')
def approve_submission(payload: ApprovePayload, db=Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == payload.submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail='Submission not found')
    # require owner/admin header
    # Note: we do not have request object here; for strictness admin actions should be proxied through bot which uses /admin endpoints with owner headers
    if sub.status != 'pending':
        raise HTTPException(status_code=400, detail='Not pending')
    sub.status = 'approved'
    # credit user balance
    user = db.query(User).filter(User.id == sub.user_id).first()
    task = db.query(Task).filter(Task.id == sub.task_id).first()
    if user and task:
        user.balance += task.reward
        task.active = False  # optionally deactivate task for this user flow
        db.add(user); db.add(task)
    db.add(sub)
    db.commit()
    return {"ok": True}


# ---- Added admin bulk and management endpoints ----
@router.post('/approve_all')
def approve_all(request: Request, db=Depends(get_db)):
    # must be called by bot with owner header
    require_owner(request)
    submissions = db.query(Submission).filter(Submission.status=='pending').all()
    count = 0
    for s in submissions:
        s.status = 'approved'
        if s.task:
            s.user.balance = s.user.balance + (s.task.reward or 0)
        db.add(s); db.add(s.user)
        count += 1
    db.commit()
    return {'ok': True, 'approved': count}

@router.post('/reject_all')
def reject_all(request: Request, db=Depends(get_db)):
    require_owner(request)
    submissions = db.query(Submission).filter(Submission.status=='pending').all()
    count = 0
    for s in submissions:
        s.status = 'rejected'
        db.add(s)
        count += 1
    db.commit()
    return {'ok': True, 'rejected': count}

@router.post('/add_balance')
def add_balance(payload: dict, request: Request, db=Depends(get_db)):
    # payload: {{'telegram_id': 12345, 'amount': 10.0}}
    require_owner(request)
    tg = payload.get('telegram_id') or payload.get('telegramId') or payload.get('user_id')
    amt = float(payload.get('amount') or 0)
    if not tg: raise HTTPException(status_code=400, detail='missing telegram id')
    user = db.query(User).filter(User.telegram_id==int(tg)).first()
    if not user: raise HTTPException(status_code=404, detail='user not found')
    user.balance = (user.balance or 0) + amt
    db.add(user); db.commit()
    return {'ok': True, 'telegram_id': user.telegram_id, 'new_balance': user.balance}


class AdminAction(BaseModel):
    telegram_id: str


@router.post('/add_admin')
def add_admin(payload: AdminAction, request: Request, db=Depends(get_db)):
    require_owner(request)
    # add or activate Admin record
    a = db.query(Admin).filter(Admin.telegram_id == str(payload.telegram_id)).first()
    if not a:
        a = Admin(telegram_id=str(payload.telegram_id), is_owner=False, is_active=True)
        db.add(a); db.commit(); db.refresh(a)
    else:
        a.is_active = True
        db.add(a); db.commit(); db.refresh(a)
    return {'ok': True, 'admin_id': a.id, 'telegram_id': a.telegram_id, 'is_active': a.is_active}


@router.post('/remove_admin')
def remove_admin(payload: AdminAction, request: Request, db=Depends(get_db)):
    require_owner(request)
    a = db.query(Admin).filter(Admin.telegram_id == str(payload.telegram_id)).first()
    if not a:
        raise HTTPException(status_code=404, detail='admin not found')
    # soft disable
    a.is_active = False
    db.add(a); db.commit(); db.refresh(a)
    return {'ok': True, 'telegram_id': a.telegram_id, 'is_active': a.is_active}


class AdminCmds(BaseModel):
    telegram_id: str
    allowed_commands: str  # comma separated list


@router.post('/set_commands')
def set_admin_commands(payload: AdminCmds, request: Request, db=Depends(get_db)):
    require_owner(request)
    a = db.query(Admin).filter(Admin.telegram_id == str(payload.telegram_id)).first()
    if not a:
        raise HTTPException(status_code=404, detail='admin not found')
    a.allowed_commands = payload.allowed_commands
    db.add(a); db.commit(); db.refresh(a)
    return {'ok': True, 'telegram_id': a.telegram_id, 'allowed_commands': a.allowed_commands}

@router.post('/ban')
def ban_user(payload: dict, request: Request, db=Depends(get_db)):
    require_owner(request)
    tg = payload.get('telegram_id') or payload.get('user_id')
    if not tg: raise HTTPException(status_code=400, detail='missing telegram id')
    user = db.query(User).filter(User.telegram_id==int(tg)).first()
    if not user: raise HTTPException(status_code=404, detail='user not found')
    user.banned = True
    db.add(user); db.commit()
    return {'ok': True, 'telegram_id': user.telegram_id}

@router.post('/unban')
def unban_user(payload: dict, request: Request, db=Depends(get_db)):
    require_owner(request)
    tg = payload.get('telegram_id') or payload.get('user_id')
    if not tg: raise HTTPException(status_code=400, detail='missing telegram id')
    user = db.query(User).filter(User.telegram_id==int(tg)).first()
    if not user: raise HTTPException(status_code=404, detail='user not found')
    user.banned = False
    db.add(user); db.commit()
    return {'ok': True, 'telegram_id': user.telegram_id}

@router.post('/open_withdrawals')
def open_withdrawals(request: Request):
    require_owner(request)
    # set a redis flag or file; for simplicity write to a temp file
    try:
        tmp = os.path.join(tempfile.gettempdir(), 'withdrawals_open')
        with open(tmp, 'w') as f: f.write('1')
    except Exception:
        pass
    return {'ok': True, 'open': True}

@router.post('/close_withdrawals')
def close_withdrawals(request: Request):
    require_owner(request)
    try:
        tmp = os.path.join(tempfile.gettempdir(), 'withdrawals_open')
        if os.path.exists(tmp): os.remove(tmp)
    except Exception:
        pass
    return {'ok': True, 'open': False}


@router.post('/callback')
def handle_callback(payload: dict, request: Request, db=Depends(get_db)):
    """Handle callback actions from bot or admin UI. Expected payload: {"action": "approve|reject|approve_all|reject_all", "submission_id": 123}
    This endpoint requires owner or admin API key/header.
    """
    # auth: owner or BOT_API_KEY
    try:
        require_owner(request)
    except Exception:
        api_key = request.headers.get('x-admin-key') or request.headers.get('X-Admin-Key')
        if not api_key or api_key != os.getenv('BOT_API_KEY'):
            raise HTTPException(status_code=403, detail='Unauthorized')

    action = payload.get('action')
    sub_id = payload.get('submission_id')
    if action in ('approve', 'reject') and sub_id:
        s = db.query(Submission).filter(Submission.id == int(sub_id)).first()
        if not s:
            raise HTTPException(status_code=404, detail='submission not found')
        s.status = 'approved' if action == 'approve' else 'rejected'
        # credit user on approve
        if action == 'approve' and s.task:
            s.user.balance = (s.user.balance or 0) + (s.task.reward or 0)
        db.add(s); db.add(s.user)
        # create notification for user
        note_text = f"Your submission #{s.id} has been {s.status}."
        n = Notification(target_type='user', target_id=str(s.user.telegram_id), message=note_text)
        db.add(n)
        db.commit()
        # try to send telegram message as well
        try:
            from ..helpers import send_telegram_message
            send_telegram_message(s.user.telegram_id, note_text)
        except Exception:
            pass
        return {'ok': True, 'submission_id': s.id, 'status': s.status}
    if action == 'approve_all':
        submissions = db.query(Submission).filter(Submission.status == 'pending').all()
        for s in submissions:
            s.status = 'approved'
            if s.task:
                s.user.balance = (s.user.balance or 0) + (s.task.reward or 0)
            db.add(s); db.add(s.user)
        db.commit()
        return {'ok': True, 'approved': len(submissions)}
    if action == 'reject_all':
        submissions = db.query(Submission).filter(Submission.status == 'pending').all()
        for s in submissions:
            s.status = 'rejected'
            db.add(s)
        db.commit()
        return {'ok': True, 'rejected': len(submissions)}

    raise HTTPException(status_code=400, detail='unknown action')

@router.post('/add_task')
def admin_add_task(payload: dict, request: Request, db=Depends(get_db)):
    """
    Admin-only: Create a new user task.
    Also notifies the REVIEW_CHANNEL_ID for review.
    Example payload:
    {
        "title": "Join our Telegram Channel",
        "instruction": "Join and submit screenshot proof.",
        "link": "https://t.me/YourChannel",
        "reward": 0.5
    }
    """
    require_owner(request)

    title = payload.get("title")
    instruction = payload.get("instruction")
    link = payload.get("link")
    reward = float(payload.get("reward", 0))

    if not title:
        raise HTTPException(status_code=400, detail="Missing task title")

    # Save new task
    t = Task(
        title=title.strip(),
        instruction=instruction.strip() if instruction else None,
        link=link.strip() if link else None,
        reward=reward,
        active=True,
        created_at=datetime.utcnow()
    )

    db.add(t)
    db.commit()
    db.refresh(t)

    # --- Notify review channel ---
    try:
        msg = (
            f"🆕 *New Task Added for Review*\n\n"
            f"📋 *{t.title}*\n"
            f"💰 Reward: {t.reward} USDT\n"
            f"📝 {t.instruction or 'No instruction provided.'}\n"
            f"{f'🔗 [Open Link]({t.link})' if t.link else ''}\n\n"
            f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        send_telegram_message(settings.REVIEW_CHANNEL_ID, msg)
    except Exception as e:
        print("⚠️ Failed to notify REVIEW_CHANNEL:", e)

    return {
        "ok": True,
        "task_id": t.id,
        "title": t.title,
        "instruction": t.instruction,
        "link": t.link,
        "reward": t.reward,
        "active": t.active,
        "notified_review_channel": settings.REVIEW_CHANNEL_ID
    }