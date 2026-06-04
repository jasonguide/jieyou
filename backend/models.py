import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import declarative_base


def _utcnow():
    return datetime.now(timezone.utc)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "jieyoupu.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Letter(Base):
    __tablename__ = "letters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, default="healing")
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    signature = Column(String, default="—— 你的解忧人")
    created_at = Column(DateTime, default=_utcnow)

    codes = relationship("Code", back_populates="letter")


class Code(Base):
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    letter_id = Column(Integer, ForeignKey("letters.id"))
    status = Column(String, default="active")
    used_at = Column(DateTime, nullable=True)
    batch_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    letter = relationship("Letter", back_populates="codes")


class UserProfile(Base):
    """用户档案：一个兑换码绑定一个年龄和自动生成的昵称"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)  # 兑换码
    nickname = Column(String, nullable=False)  # 兑换码后3位+"用户"
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class Question(Base):
    """问题池：种子问题 + 用户提问"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asker_code = Column(String, nullable=False)  # 提问者兑换码（种子问题用"seed"）
    asker_nickname = Column(String, nullable=False)
    asker_age = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)  # 问题内容
    source = Column(String, default="user")  # seed=种子问题, user=用户提问
    status = Column(String, default="pending")  # pending/approved/rejected/answered/expired
    created_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=True)  # 过期时间（7天）

    answers = relationship("Answer", back_populates="question", order_by="Answer.id")


class Answer(Base):
    """回答：用户对问题的回答"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    answerer_code = Column(String, nullable=False)  # 回答者兑换码
    answerer_nickname = Column(String, nullable=False)
    answerer_age = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)  # 回答内容
    status = Column(String, default="pending")  # pending/approved/rejected
    created_at = Column(DateTime, default=_utcnow)

    question = relationship("Question", back_populates="answers")
