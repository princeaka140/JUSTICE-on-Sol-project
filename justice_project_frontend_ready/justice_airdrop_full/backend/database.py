from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import datetime
from .config import settings

DATABASE_URL = settings.DATABASE_URL

# sqlite needs check_same_thread disabled for simple local usage
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    wallet = Column(String, nullable=True)
    referrals = Column(Integer, default=0)
    banned = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    device_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    referral_code = Column(String, nullable=True)
    referral_link = Column(String, nullable=True)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    instruction = Column(Text, nullable=True)
    link = Column(String, nullable=True)
    reward = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    proof = Column(Text, nullable=True)
    status = Column(String, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User')
    task = relationship('Task')

class Withdrawal(Base):
    __tablename__ = 'withdrawals'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float)
    wallet = Column(String)
    status = Column(String, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User')


class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, nullable=False)  # user | group
    target_id = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    is_owner = Column(Boolean, default=False)
    group_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    allowed_commands = Column(Text, nullable=True)  # comma separated or json list
    added_at = Column(DateTime, default=datetime.datetime.utcnow)


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String)  # withdrawal | presale | credit | debit
    amount = Column(Float)
    wallet = Column(String, nullable=True)
    status = Column(String, default='pending')
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User')

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency - yields a DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
