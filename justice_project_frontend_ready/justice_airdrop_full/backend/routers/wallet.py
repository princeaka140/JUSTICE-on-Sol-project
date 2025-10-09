from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db, User, Withdrawal, Transaction
from sqlalchemy.orm import Session
import os, tempfile

router = APIRouter(prefix='/wallet')


class SetWallet(BaseModel):
    wallet: str


class Withdraw(BaseModel):
    amount: float


class PresaleRequest(BaseModel):
    amount: float
    wallet: Optional[str] = None


def _get_user_by_header(telegram_id: Optional[str], x_user_id: Optional[str], db: Session):
    if x_user_id:
        user = db.query(User).filter(User.id == int(x_user_id)).first()
        return user
    if telegram_id:
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    return None


@router.get('/info')
def wallet_info(telegram_id: Optional[str] = None, x_user_id: Optional[str] = Header(None, alias='x-user-id'), db: Session = Depends(get_db)):
    user = _get_user_by_header(telegram_id, x_user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    pending = db.query(Withdrawal).filter(Withdrawal.user_id == user.id, Withdrawal.status == 'pending').count()
    total_earned = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.type == 'credit').with_entities(Transaction.amount).all()
    total_earned = sum([t[0] for t in total_earned]) if total_earned else 0
    return {
        'balance': user.balance,
        'wallet': user.wallet,
        'pending': pending,
        'total_earned': total_earned
    }


@router.get('/transactions')
def transactions(limit: int = 50, telegram_id: Optional[str] = None, x_user_id: Optional[str] = Header(None, alias='x-user-id'), db: Session = Depends(get_db)):
    user = _get_user_by_header(telegram_id, x_user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).limit(limit).all()
    result = []
    for t in txs:
        result.append({
            'id': t.id,
            'type': t.type,
            'amount': t.amount,
            'wallet': t.wallet,
            'status': t.status,
            'metadata': t.metadata,
            'created_at': t.created_at.isoformat()
        })
    return {'transactions': result}


@router.post('/set')
def set_wallet(payload: SetWallet, telegram_id: Optional[str] = None, x_user_id: Optional[str] = Header(None, alias='x-user-id'), db: Session = Depends(get_db)):
    user = _get_user_by_header(telegram_id, x_user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.wallet = payload.wallet
    db.add(user)
    db.commit()
    return {"ok": True, "wallet": user.wallet}


@router.post('/request')
def request_withdraw(payload: Withdraw, telegram_id: Optional[str] = None, x_user_id: Optional[str] = Header(None, alias='x-user-id'), db: Session = Depends(get_db)):
    user = _get_user_by_header(telegram_id, x_user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    # check if withdrawals are open
    tmp = os.path.join(tempfile.gettempdir(), 'withdrawals_open')
    if not os.path.exists(tmp):
        raise HTTPException(status_code=403, detail='Withdrawals are currently closed')

    if payload.amount <= 0 or payload.amount > user.balance:
        raise HTTPException(status_code=400, detail='Invalid amount')
    w = Withdrawal(user_id=user.id, amount=payload.amount, wallet=user.wallet)
    db.add(w)
    user.balance -= payload.amount
    db.add(user)
    # record transaction
    tx = Transaction(user_id=user.id, type='withdrawal', amount=payload.amount, wallet=user.wallet, status='pending')
    db.add(tx)
    db.commit()
    db.refresh(w)
    db.refresh(tx)
    return {"ok": True, "withdrawal_id": w.id, 'transaction_id': tx.id}


@router.post('/presale')
def presale_request(payload: PresaleRequest, telegram_id: Optional[str] = None, x_user_id: Optional[str] = Header(None, alias='x-user-id'), db: Session = Depends(get_db)):
    user = _get_user_by_header(telegram_id, x_user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    # PRESALE is not available for the moment
    raise HTTPException(status_code=503, detail='Presale is not available at the moment')
