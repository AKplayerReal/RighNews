from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
import os
import uvicorn
from database import init_db, get_db, Article
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import jdatetime

# ============================================
# راه‌اندازی اولیه FastAPI
# ============================================
app = FastAPI(
    title="RighNews Core API",
    description="Modular AI News Agency for Persian Tech News",
    version="1.0.0"
)
# ============================================
# قالب‌های HTML (سایت رای‌نیوز)
# ============================================
templates = Jinja2Templates(directory="templates")

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def fa_date(value):
    """تبدیل تاریخ میلادی به شمسی فارسی"""
    try:
        d = value.date() if hasattr(value, "date") else value
        return jdatetime.date.fromgregorian(date=d).strftime("%d %B %Y").translate(FA_DIGITS)
    except Exception:
        return "—"

def fa_num(value):
    """تبدیل اعداد به فارسی"""
    return str(value).translate(FA_DIGITS)

templates.env.filters["fadate"] = fa_date
templates.env.filters["fanum"] = fa_num
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def custom_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "404.html", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)# ============================================
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
@app.get("/api")
def api_root():
    """اطلاعات سیستم (JSON) — برای تست و برنامه‌های دیگر"""
    return {
        "service": "RayNews Core API",
        "status": "alive",
        "version": "1.0.0",
        "endpoints": {
            "website": "/",
            "articles_list": "/articles",
            "article_detail": "/articles/{id}",
            "process_article": "/process-article",
            "health": "/health",
            "db_test": "/db-test",
            "docs": "/docs",
        },
    }
@app.post("/articles/{article_id}/reprocess")
def reprocess_article(article_id: int, secret: str = "", db: Session = Depends(get_db)):
    """حذف و پردازش مجدد یک مقاله (برای اصلاح ترجمه‌های خراب)"""
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "righnews-admin-2026")
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # استخراج شناسه arXiv از لینک منبع
    match = re.search(r'(\d{4}\.\d{4,5})', article.source_url or "")
    if not match:
        raise HTTPException(status_code=400, detail="Cannot extract arXiv ID from source_url")
    arxiv_id = match.group(1)

    # حذف نسخه قدیمی
    db.delete(article)
    db.commit()

    # پردازش مجدد با پرامپت اصلاح‌شده
    processor = ArticleProcessor()
    return processor.process(arxiv_id)
# ============================================
# 🌐 صفحات HTML سایت رای‌نیوز
# ============================================

# ============================================
# 🌐 صفحات HTML سایت رای‌نیوز
# ============================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", db: Session = Depends(get_db)):
    """صفحه اصلی سایت — سردر روزنامه"""
    articles = []
    if db is not None:
        articles = db.query(Article).order_by(Article.created_at.desc()).all()

    q = q.strip()
    if q:
        needle = q.lower()
        matches = [
            a for a in articles
            if needle in " ".join([
                a.title_persian or "", a.title_english or "",
                a.content_persian or "", a.content_english or ""
            ]).lower()
        ]
    else:
        matches = articles

    # تاریخ شمسی (ضدخطا)
    try:
        today = jdatetime.date.today().strftime("%A، %d %B %Y").translate(FA_DIGITS)
    except Exception:
        today = jdatetime.date.today().strftime("%d %B %Y").translate(FA_DIGITS)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "articles": articles,
            "lead": articles[0] if articles and not q else None,
            "latest": articles[1:6] if not q else [],
            "grid": (articles[1:] if len(articles) > 1 else articles) if not q else matches,
            "q": q,
            "verified_count": sum(1 for a in articles if a.verified),
            "today": today,
        },
    )


@app.get("/article/{article_id}", response_class=HTMLResponse)
def article_page(request: Request, article_id: int, db: Session = Depends(get_db)):
    """صفحه داخلی مقاله — نمایش دوزبانه"""
    article = None
    others = []
    if db is not None:
        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            others = (
                db.query(Article)
                .filter(Article.id != article_id)
                .order_by(Article.created_at.desc())
                .limit(3)
                .all()
            )

    if not article:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    return templates.TemplateResponse(
        request,
        "article.html",
        {"article": article, "others": others},
    )
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
from processor import ArticleProcessor
from pydantic import BaseModel

class ProcessRequest(BaseModel):
    arxiv_id: str

@app.post("/process-article")
async def process_article(req: ProcessRequest):
    """
    پردازش کامل یک مقاله از arXiv:
    ۱. دانلود مقاله
    ۲. ترجمه عنوان و چکیده
    ۳. راستی‌آزمایی اعداد
    ۴. ذخیره در دیتابیس
    """
    try:
        processor = ArticleProcessor()
        result = processor.process(req.arxiv_id)
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
@app.get("/articles")
def list_articles(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    لیست مقالات ذخیره شده (از جدید به قدیمی)
    """
    try:
        articles = (
            db.query(Article)
            .order_by(Article.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return {
            "count": len(articles),
            "articles": [
                {
                    "id": a.id,
                    "source_type": a.source_type,
                    "title_english": a.title_english,
                    "title_persian": a.title_persian,
                    "content_english": a.content_english[:200] + "..." if a.content_english else None,
                    "content_persian": a.content_persian[:200] + "..." if a.content_persian else None,
                    "verified": a.verified,
                    "fact_check_notes": a.fact_check_notes,
                    "published_at": str(a.published_at) if a.published_at else None,
                    "created_at": str(a.created_at) if a.created_at else None,
                }
                for a in articles
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/articles/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    """دریافت یک مقاله خاص با جزئیات کامل"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {
        "id": article.id,
        "source_url": article.source_url,
        "source_type": article.source_type,
        "title_english": article.title_english,
        "title_persian": article.title_persian,
        "content_english": article.content_english,
        "content_persian": article.content_persian,
        "verified": article.verified,
        "fact_check_notes": article.fact_check_notes,
        "published_at": str(article.published_at) if article.published_at else None,
        "created_at": str(article.created_at) if article.created_at else None,
    }
# ============================================
# اجرای سرور
# ============================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
