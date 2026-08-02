"""
پنل مدیریت حرفه‌ای سفارشی برای رای‌نیوز
طراحی مدرن، فارسی، RTL با Tailwind CSS
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import Article, get_db
from image_picker import pick_image

# Router برای پنل ادمین
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Templates
admin_templates = Jinja2Templates(directory="templates/admin")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session storage (در production از Redis یا دیتابیس استفاده کنید)
sessions = {}

# ============================================
# احراز هویت
# ============================================
def get_current_user(request: Request) -> Optional[str]:
    """دریافت کاربر فعلی از session"""
    session_id = request.cookies.get("admin_session")
    if not session_id:
        return None
    
    session = sessions.get(session_id)
    if not session:
        return None
    
    if datetime.now() > session["expires"]:
        del sessions[session_id]
        return None
    
    return session["username"]

def require_auth(request: Request):
    """چک کردن احراز هویت"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/admin/login"})
    return user

# ============================================
# صفحه لاگین
# ============================================
@admin_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """صفحه ورود"""
    return admin_templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None}
    )

@admin_router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """پردازش فرم لاگین"""
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_SECRET", "righnews-admin-2026")
    
    if username != admin_user or password != admin_pass:
        return admin_templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "نام کاربری یا رمز عبور اشتباه است"}
        )
    
    # ایجاد session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "username": username,
        "expires": datetime.now() + timedelta(days=7)
    }
    
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="admin_session",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )
    return response

@admin_router.get("/logout")
async def logout(request: Request):
    """خروج از پنل"""
    session_id = request.cookies.get("admin_session")
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response

# ============================================
# داشبورد
# ============================================
@admin_router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """داشبورد اصلی"""
    user = require_auth(request)
    
    # آمار
    total_articles = db.query(Article).count()
    verified_articles = db.query(Article).filter(Article.verified == True).count()
    recent_articles = db.query(Article).order_by(Article.created_at.desc()).limit(5).all()
    
    return admin_templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_articles": total_articles,
            "verified_articles": verified_articles,
            "recent_articles": recent_articles
        }
    )

# ============================================
# لیست مقالات
# ============================================
@admin_router.get("/articles", response_class=HTMLResponse)
async def list_articles(
    request: Request,
    q: str = "",
    verified: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """لیست مقالات با جستجو و فیلتر"""
    user = require_auth(request)
    
    query = db.query(Article)
    
    # جستجو
    if q:
        query = query.filter(
            (Article.title_persian.ilike(f"%{q}%")) |
            (Article.title_english.ilike(f"%{q}%")) |
            (Article.content_persian.ilike(f"%{q}%"))
        )
    
    # فیلتر راستی‌آزمایی
    if verified == "true":
        query = query.filter(Article.verified == True)
    elif verified == "false":
        query = query.filter(Article.verified == False)
    
    articles = query.order_by(Article.created_at.desc()).all()
    
    return admin_templates.TemplateResponse(
        "articles_list.html",
        {
            "request": request,
            "user": user,
            "articles": articles,
            "q": q,
            "verified": verified
        }
    )

# ============================================
# افزودن مقاله جدید
# ============================================
@admin_router.get("/articles/new", response_class=HTMLResponse)
async def new_article_page(request: Request):
    """فرم افزودن مقاله"""
    user = require_auth(request)
    return admin_templates.TemplateResponse(
        "article_form.html",
        {"request": request, "user": user, "article": None}
    )

@admin_router.post("/articles/new")
async def create_article(
    request: Request,
    title_persian: str = Form(...),
    title_english: str = Form(...),
    content_persian: str = Form(...),
    content_english: str = Form(...),
    source_url: str = Form(""),
    source_type: str = Form("arxiv"),
    image_url: str = Form(""),
    verified: bool = Form(False),
    fact_check_notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """ایجاد مقاله جدید"""
    user = require_auth(request)
    
    # اگر تصویر نداشت، خودکار انتخاب شود
    if not image_url:
        image_url = pick_image(title_english, content_english)
    
    article = Article(
        title_persian=title_persian,
        title_english=title_english,
        content_persian=content_persian,
        content_english=content_english,
        source_url=source_url,
        source_type=source_type,
        image_url=image_url,
        verified=verified,
        fact_check_notes=fact_check_notes,
        published_at=datetime.now()
    )
    
    db.add(article)
    db.commit()
    
    return RedirectResponse(url=f"/admin/articles/{article.id}", status_code=303)

# ============================================
# ویرایش مقاله
# ============================================
@admin_router.get("/articles/{article_id}", response_class=HTMLResponse)
async def edit_article_page(request: Request, article_id: int, db: Session = Depends(get_db)):
    """فرم ویرایش مقاله"""
    user = require_auth(request)
    article = db.query(Article).filter(Article.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return admin_templates.TemplateResponse(
        "article_form.html",
        {"request": request, "user": user, "article": article}
    )

@admin_router.post("/articles/{article_id}")
async def update_article(
    request: Request,
    article_id: int,
    title_persian: str = Form(...),
    title_english: str = Form(...),
    content_persian: str = Form(...),
    content_english: str = Form(...),
    source_url: str = Form(""),
    source_type: str = Form("arxiv"),
    image_url: str = Form(""),
    verified: bool = Form(False),
    fact_check_notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """به‌روزرسانی مقاله"""
    user = require_auth(request)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.title_persian = title_persian
    article.title_english = title_english
    article.content_persian = content_persian
    article.content_english = content_english
    article.source_url = source_url
    article.source_type = source_type
    article.image_url = image_url
    article.verified = verified
    article.fact_check_notes = fact_check_notes
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/articles/{article_id}", status_code=303)

# ============================================
# حذف مقاله
# ============================================
@admin_router.post("/articles/{article_id}/delete")
async def delete_article(request: Request, article_id: int, db: Session = Depends(get_db)):
    """حذف مقاله"""
    user = require_auth(request)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    db.delete(article)
    db.commit()
    
    return RedirectResponse(url="/admin/articles", status_code=303)

# ============================================
# آپلود تصویر
# ============================================
@admin_router.post("/articles/{article_id}/image")
async def upload_image(
    request: Request,
    article_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """آپلود تصویر برای مقاله"""
    user = require_auth(request)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # بررسی نوع فایل
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        return JSONResponse({"error": "فقط فایل‌های تصویری مجاز هستند"}, status_code=400)
    
    # ذخیره فایل
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{secrets.token_hex(8)}{ext}"
    upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    image_url = f"/static/uploads/{filename}"
    article.image_url = image_url
    db.commit()
    
    return JSONResponse({"url": image_url})

# ============================================
# API برای انتخاب تصویر خودکار
# ============================================
@admin_router.post("/articles/{article_id}/auto-image")
async def auto_pick_image(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db)
):
    """انتخاب خودکار تصویر بر اساس محتوا"""
    user = require_auth(request)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    image_url = pick_image(article.title_english, article.content_english, article_id)
    article.image_url = image_url
    db.commit()
    
    return JSONResponse({"url": image_url})
