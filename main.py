from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
import os
import uvicorn

# Import از فایل database.py که قبلاً ساختیم
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
# مدل‌های Pydantic (ساختار ورودی/خروجی)
# ============================================
class ArticleRequest(BaseModel):
    english_text: str

class TranslationResponse(BaseModel):
    persian_translation: str
    model_used: str = "gemma-3-27b-it"

# ============================================
# رویداد Startup: راه‌اندازی دیتابیس هنگام شروع سرور
# ============================================
@app.on_event("startup")
async def startup_event():
    """ساخت جداول و فعال‌سازی pgvector هنگام بالا آمدن سرور"""
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
    """صفحه اصلی - تست زنده بودن سرور"""
    return {
        "message": "RighNews Core is alive! 🚀",
        "service": "Modular AI News Agency",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "translate": "/translate-test",
            "database_test": "/db-test"
        }
    }

@app.get("/health")
def health_check():
    """برای مانیتورینگ و health check"""
    return {
        "status": "healthy",
        "service": "righnews",
        "database": "connected" if os.getenv("DATABASE_URL") else "not configured"
    }

@app.post("/translate-test", response_model=TranslationResponse)
async def translate_test(req: ArticleRequest):
    """ترجمه متن انگلیسی فناوری به فارسی با استفاده از GapGPT"""
    api_key = os.getenv("GAPGPT_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="GAPGPT_API_KEY is missing in environment variables!"
        )
    
    # اتصال به API اختصاصی GapGPT
    client = OpenAI(
        base_url="https://api.gapgpt.app/v1",
        api_key=api_key
    )
    
    try:
        chat_completion = client.chat.completions.create(
            model="gemma-3-27b-it",
            messages=[
                {
                    "role": "system", 
                    "content": "تو یک روزنامه‌نگار حرفه‌ای فناوری هستی. متن انگلیسی زیر را به فارسی روان و دقیق ترجمه کن. از اصطلاحات استاندارد فناوری فارسی استفاده کن. هیچ توضیح اضافی یا احوال‌پرسی اضافه نکن."
                },
                {"role": "user", "content": req.english_text}
            ],
            temperature=0.2
        )
        return TranslationResponse(
            persian_translation=chat_completion.choices[0].message.content
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"GapGPT API Error: {str(e)}"
        )

@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    """تست اتصال به دیتابیس PostgreSQL"""
    try:
        # شمارش مقالات موجود
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

# ============================================
# اجرای سرور (فقط برای تست لوکال یا Docker)
# ============================================
if __name__ == "__main__":
    # خواندن پورت از متغیر محیطی گردو (اگر نبود، پیش‌فرض 8000)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
