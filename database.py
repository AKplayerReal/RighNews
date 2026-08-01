from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Integer, String
from sqlalchemy.exc import OperationalError
import os
from datetime import datetime

# ============================================
# اصلاح رشته اتصال
# ============================================
def get_database_url():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ DATABASE_URL is not set!")
        return None
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        print("✅ Fixed DATABASE_URL: postgres:// → postgresql://")
    return db_url

DATABASE_URL = get_database_url()

# ============================================
# راه‌اندازی موتور دیتابیس
# ============================================
engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print("✅ Database engine created successfully")
    except Exception as e:
        print(f"❌ Failed to create database engine: {e}")

# ============================================
# مدل‌های دیتابیس
# ============================================
class Article(Base):
    __tablename__ = "articles"
    
    id = Column(BigInteger, primary_key=True, index=True)
    source_url = Column(Text, unique=True, nullable=False)
    source_type = Column(String(50), nullable=False)
    title_english = Column(Text, nullable=False)
    title_persian = Column(Text)
    content_english = Column(Text, nullable=False)
    content_persian = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
    fact_check_notes = Column(Text)

class ArticleEmbedding(Base):
    __tablename__ = "article_embeddings"
    
    id = Column(BigInteger, primary_key=True, index=True)
    article_id = Column(BigInteger, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    # embeddings به صورت JSON در TEXT ذخیره می‌شوند (موقتاً)
    embedding_json = Column(Text)  # JSON string از لیست اعداد
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# تابع راه‌اندازی
# ============================================
def init_db():
    if not engine:
        print("⚠️ Database engine not available")
        return False
    
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"⚠️ Database init error: {e}")
        return False

def get_db():
    if not SessionLocal:
        raise Exception("Database not available")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
