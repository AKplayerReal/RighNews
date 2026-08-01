from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
import os
import uvicorn

from database import init_db, get_db, Article

# ============================================
# راه‌اندازی اولیه FastAPI
# ============================================
app = FastAPI(
    title="RighNews Core API",
    description="Modular AI News Agency for Persian Tech News",
    version="1.0.0"
)

# ============================================
# مدل‌های Pydantic
# ============================================
class ArticleRequest(BaseModel):
    english_text: str

class TranslationResponse(BaseModel):
    persian_translation: str
    model_used: str = "deepseek-v4-flash"
    reasoning_used: bool = False

# ============================================
# رویداد Startup
# ============================================
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")

# ============================================
# Endpointها
# ============================================

@app.get("/")
def read_root():
    return {
        "message": "RighNews Core is alive! 🚀",
        "service": "Modular AI News Agency",
        "version": "1.0.0",
        "model": "DeepSeek V4 Flash via GapGPT",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "translate": "/translate-test",
            "database_test": "/db-test"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "righnews",
        "model": "deepseek-v4-flash",
        "provider": "GapGPT",
        "database": "connected" if os.getenv("DATABASE_URL") else "not configured"
    }

@app.post("/translate-test", response_model=TranslationResponse)
async def translate_test(req: ArticleRequest):
    """ترجمه متن انگلیسی فناوری به فارسی با DeepSeek V4 Flash"""
    api_key = os.getenv("GAPGPT_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="GAPGPT_API_KEY is missing in environment variables!"
        )
    
    # اتصال به GapGPT
    client = OpenAI(
        base_url="https://api.gapgpt.app/v1",
        api_key=api_key
    )
    
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {
                    "role": "system", 
                    "content": """تو یک روزنامه‌نگار حرفه‌ای و متخصص فناوری هستی. 
وظیفه تو ترجمه دقیق و روان متون فناوری از انگلیسی به فارسی است.

قوانین مهم:
- فقط ترجمه کن، هیچ توضیح یا تفسیری اضافه نکن
- از اصطلاحات استاندارد فناوری فارسی استفاده کن (مثلاً: هوش مصنوعی، یادگیری ماشین، رایانش ابری)
- اعداد و نام‌های خاص (مثل Apple, M3, RTX 4090) را به انگلیسی نگه دار
- لحن خبری و حرفه‌ای را حفظ کن
- مستقیماً ترجمه را خروجی بده، بدون هیچ پیش‌گفتار یا پس‌گفتار"""
                },
                {"role": "user", "content": req.english_text}
            ],
            temperature=0.3,  # کمی بالاتر برای روانی بیشتر
            # پارامترهای اختیاری برای کنترل reasoning
            extra_body={
                "enable_thinking": False  # غیرفعال کردن reasoning برای سرعت بیشتر
            } if False else None  # این خط را می‌توانید حذف کنید اگر API پشتیبانی نمی‌کند
        )
        
        # استخراج متن ترجمه
        translated_text = chat_completion.choices[0].message.content
        
        # بررسی وجود reasoning (فقط برای اطلاع)
        reasoning_used = hasattr(chat_completion.choices[0].message, 'reasoning_content') and \
                         chat_completion.choices[0].message.reasoning_content is not None
        
        return TranslationResponse(
            persian_translation=translated_text,
            reasoning_used=reasoning_used
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"GapGPT API Error: {str(e)}"
        )

@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    try:
        article_count = db.query(Article).count()
        return {
            "status": "connected",
            "article_count": article_count,
            "message": "Database is working! 🎉",
            "tables": ["articles", "article_embeddings"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Database connection failed"
        }
@app.post("/init-db")
def init_database_manually(secret: str = ""):
    """ساخت دستی جداول - نیاز به رمز دارد"""
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "righnews-admin-2026")
    
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
@app.post("/force-init-db")
def force_init_database(secret: str = ""):
    """
    ساخت اجباری جداول با اجرای مستقیم SQL
    این endpoint خطاها را به طور کامل نمایش می‌دهد
    """
    import traceback
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "righnews-admin-2026")
    
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    from database import engine, DATABASE_URL
    from sqlalchemy import text
    
    results = {
        "database_url_present": bool(DATABASE_URL),
        "engine_present": bool(engine),
        "steps": []
    }
    
    if not engine:
        results["error"] = "Database engine not available"
        return results
    
    try:
        # مرحله ۱: فعال‌سازی pgvector
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            results["steps"].append({"step": "pgvector", "status": "success"})
    except Exception as e:
        results["steps"].append({
            "step": "pgvector", 
            "status": "error", 
            "error": str(e)
        })
    
    try:
        # مرحله ۲: ساخت جدول articles
        create_articles = """
        CREATE TABLE IF NOT EXISTS articles (
            id BIGSERIAL PRIMARY KEY,
            source_url TEXT UNIQUE NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            title_english TEXT NOT NULL,
            title_persian TEXT,
            content_english TEXT NOT NULL,
            content_persian TEXT,
            published_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            verified BOOLEAN DEFAULT FALSE,
            fact_check_notes TEXT
        );
        """
        with engine.connect() as conn:
            conn.execute(text(create_articles))
            conn.commit()
            results["steps"].append({"step": "articles_table", "status": "success"})
    except Exception as e:
        results["steps"].append({
            "step": "articles_table",
            "status": "error",
            "error": str(e)
        })
    
    try:
        # مرحله ۳: ساخت جدول article_embeddings
        create_embeddings = """
        CREATE TABLE IF NOT EXISTS article_embeddings (
            id BIGSERIAL PRIMARY KEY,
            article_id BIGINT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        with engine.connect() as conn:
            conn.execute(text(create_embeddings))
            conn.commit()
            results["steps"].append({"step": "embeddings_table", "status": "success"})
    except Exception as e:
        results["steps"].append({
            "step": "embeddings_table",
            "status": "error",
            "error": str(e)
        })
    
    # بررسی نهایی
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('articles', 'article_embeddings')
            """))
            tables = [row[0] for row in result]
            results["created_tables"] = tables
    except Exception as e:
        results["check_error"] = str(e)
    
    return results
    
    # بقیه کد مثل قبل
# ============================================
# اجرای سرور
# ============================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
