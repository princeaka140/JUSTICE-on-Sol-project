
import requests
import os
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from .database import get_db, Admin, User
from .config import settings
from typing import List, Optional


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message via the bot token to a chat (user/group/channel).
    Uses placeholder BOT_TOKEN from config; replace with real token in .env or environment.
    """
    token = settings.BOT_TOKEN
    if not token or token.startswith('REPLACE'):
        # no-op for placeholder; return True so callers can proceed in dev
        print(f"[telegram stub] -> {chat_id}: {text}")
        return True
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=8)
        return r.ok
    except Exception as e:
        print("send_telegram_message error:", e)
        return False


def is_user_member_of(chat_id: str, user_id: int) -> bool:
    """Check if user_id is member of chat_id (group/channel)."""
    token = settings.BOT_TOKEN
    if not token or token.startswith('REPLACE'):
        return True
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        r = requests.get(url, params={"chat_id": chat_id, "user_id": user_id}, timeout=8)
        j = r.json()
        if not j.get('ok'):
            return False
        status = j['result'].get('status')
        # statuses: creator, administrator, member, restricted, left, kicked
        return status in ('creator', 'administrator', 'member', 'restricted')
    except Exception as e:
        print('is_user_member_of error', e)
        return False


def post_submission_for_review(channel_id: str, submission_id: int, user_tg: str, text: str):
    """Post a message to channel with inline approve/reject buttons and the submission details."""
    token = settings.BOT_TOKEN
    if not token or token.startswith('REPLACE'):
        print(f"[submission stub] -> channel:{channel_id} sub:{submission_id} user:{user_tg} msg:{text}")
        return True
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Approve", "callback_data": f"approve:{submission_id}"}, {"text": "❌ Reject", "callback_data": f"reject:{submission_id}"}],
            [{"text": "Approve All", "callback_data": "approve_all"}, {"text": "Reject All", "callback_data": "reject_all"}]
        ]
    }
    payload = {
        "chat_id": channel_id,
        "text": f"New submission #{submission_id} by {user_tg}:\n{text}",
        "reply_markup": keyboard,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=8)
        return r.ok
    except Exception as e:
        print('post_submission_for_review error', e)
        return False


def _owner_ids() -> List[int]:
    return settings.owner_ids


def is_owner_request(request: Request) -> bool:
    """Return True if request contains owner identity via x-owner-id or admin key."""
    api_key = request.headers.get('x-admin-key') or request.headers.get('X-Admin-Key')
    if api_key and api_key == settings.BOT_API_KEY:
        return True
    owner = request.headers.get('x-owner-id')
    if not owner:
        return False
    try:
        return int(owner) in _owner_ids()
    except Exception:
        return False


def is_admin_request(request: Request, db: Session) -> Optional[Admin]:
    """Return Admin instance if request is from an active admin (x-admin-id header with telegram id or admin key)."""
    # API key gives privileged access
    api_key = request.headers.get('x-admin-key') or request.headers.get('X-Admin-Key')
    if api_key and api_key == settings.BOT_API_KEY:
        return True

    admin_id = request.headers.get('x-admin-id') or request.headers.get('X-Admin-Id')
    if not admin_id:
        return None
    a = db.query(Admin).filter(Admin.telegram_id == str(admin_id)).first()
    if not a or not a.is_active:
        return None
    return a


def require_owner(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Owner only')
    return True


def require_verified(request: Request, db: Session = Depends(get_db)):
    # expect x-user-id header with integer User.id
    uid = request.headers.get('x-user-id') or request.headers.get('X-User-Id')
    if not uid:
        raise HTTPException(status_code=401, detail='Missing user id header')
    try:
        uid = int(uid)
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid user id header')
    user = db.query(User).filter(User.id == uid).first()
    if not user or not user.verified or user.banned:
        raise HTTPException(status_code=403, detail='Access denied: not verified or banned')
    request.state.user = user
    return user

