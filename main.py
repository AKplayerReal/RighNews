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

# ============================================
# اجرای سرور
# ============================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
