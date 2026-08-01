from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Integer, String
from pgvector.sqlalchemy import Vector
import os
from datetime import datetime

# خواندن رشته اتصال از متغیرهای محیطی گردو
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# ایجاد موتور دیتابیس
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# مدل جدول مقالات
class Article(Base):
    __tablename__ = "articles"
    
    id = Column(BigInteger, primary_key=True, index=True)
    source_url = Column(Text, unique=True, nullable=False)
    source_type = Column(String(50), nullable=False)  # 'arxiv', 'rss', 'web'
    title_english = Column(Text, nullable=False)
    title_persian = Column(Text)
    content_english = Column(Text, nullable=False)
    content_persian = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
    fact_check_notes = Column(Text)

# مدل جدول بردارهای Embedding (برای RAG)
class ArticleEmbedding(Base):
    __tablename__ = "article_embeddings"
    
    id = Column(BigInteger, primary_key=True, index=True)
    article_id = Column(BigInteger, nullable=False)  # Foreign key to articles
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # برای مدل‌های embedding کوچک
    created_at = Column(DateTime, default=datetime.utcnow)

# تابع راه‌اندازی دیتابیس
def init_db():
    """ساخت جداول و فعال‌سازی pgvector"""
    with engine.connect() as conn:
        # فعال‌سازی اکستنشن pgvector
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    # ساخت جداول
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

# تابع برای دریافت session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# تست اتصال
if __name__ == "__main__":
    init_db()
    print("✅ Database connection test successful!")
