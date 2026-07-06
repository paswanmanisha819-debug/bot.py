import json
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import DATABASE_URL

# Setup high-performance connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_recycle=3600,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    student_class: Mapped[str] = mapped_column(String(20), nullable=True)  # e.g., "10th", "12th"
    board: Mapped[str] = mapped_column(String(50), nullable=True)          # e.g., "CBSE", "State Board"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" or "model"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class QuizStat(Base):
    __tablename__ = "quiz_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    subject: Mapped[str] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=3)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Async Database Helper Utilities
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user(user_id: int) -> User:
    async with AsyncSessionLocal() as session:
        return await session.get(User, user_id)

async def create_or_update_user(user_id: int, username: str, student_class: str = None, board: str = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if not user:
                user = User(user_id=user_id, username=username, student_class=student_class, board=board)
                session.add(user)
            else:
                if student_class: user.student_class = student_class
                if board: user.board = board
            await session.commit()

async def log_conversation(user_id: int, role: str, content: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            log = Conversation(user_id=user_id, role=role, content=content)
            session.add(log)
            await session.commit()

async def get_recent_context(user_id: int, limit: int = 6):
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.timestamp.desc()).limit(limit)
        result = await session.execute(stmt)
        history = result.scalars().all()
        # Return in chronological order
        return [{"role": h.role, "parts": [h.content]} for h in reversed(history)]

async def save_quiz_stat(user_id: int, subject: str, score: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stat = QuizStat(user_id=user_id, subject=subject, score=score)
            session.add(stat)
            await session.commit()