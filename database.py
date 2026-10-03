import json
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger, Text, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import DATABASE_URL

# 🚀 Setup ultra-high-performance asynchronous connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_recycle=3600,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- 1. CORE USER DEMOGRAPHICS ---
class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    student_class: Mapped[str] = mapped_column(String(20), nullable=True)
    board: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- 2. NEURAL CONVERSATION MEMORY ---
class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- 3. BATTLE ARENA & PERFORMANCE LOGS ---
class QuizStat(Base):
    __tablename__ = "quiz_stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    subject: Mapped[str] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=3)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# 🧠 COGNITIVE ENGINE UTILITIES (CRUD OPS)
# ==========================================

async def init_db():
    """Initializes the Neural Database Schema securely."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user(user_id: int) -> User:
    """Fetches user profile data."""
    async with AsyncSessionLocal() as session:
        return await session.get(User, user_id)

async def create_or_update_user(user_id: int, username: str, student_class: str = None, board: str = None):
    """Advanced UPSERT logic for user profiling without dropping data."""
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
    """Logs chat history for AI Context Memory."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            log = Conversation(user_id=user_id, role=role, content=content)
            session.add(log)
            await session.commit()

async def get_recent_context(user_id: int, limit: int = 6):
    """Retrieves recent cognitive context for the AI."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.timestamp.desc()).limit(limit)
        result = await session.execute(stmt)
        history = result.scalars().all()
        return [{"role": h.role, "content": h.content} for h in reversed(history)]

async def save_quiz_stat(user_id: int, subject: str, score: int, total: int = 3):
    """Logs battle arena performance."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stat = QuizStat(user_id=user_id, subject=subject, score=score, total=total)
            session.add(stat)
            await session.commit()

# 🔥 NEW ULTRA-ADVANCED FEATURE: WEAKNESS ANALYTICS 🔥
async def analyze_weaknesses(user_id: int):
    """
    Advanced SQL Aggregation: Calculates accuracy per subject to find cognitive weaknesses.
    Returns a list of tuples: [('Science', 45.5), ('Maths', 80.0)]
    """
    async with AsyncSessionLocal() as session:
        # Executes deep database math to find subjects where the student fails most
        stmt = text('''
            SELECT subject, 
                   (CAST(SUM(score) AS FLOAT) / SUM(total)) * 100 as accuracy
            FROM quiz_stats
            WHERE user_id = :uid
            GROUP BY subject
            HAVING COUNT(id) >= 1
            ORDER BY accuracy ASC
            LIMIT 3
        ''')
        result = await session.execute(stmt, {"uid": user_id})
        return result.fetchall()
    
