"""
پنل مدیریت حرفه‌ای رای‌نیوز
بر پایه SQLAdmin - با آپلود تصویر و احراز هویت
"""
import os
import shutil
import secrets
from datetime import datetime
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.datastructures import UploadFile
from sqlalchemy import select
from database import engine, Article, ArticleEmbedding, SessionLocal
from image_picker import pick_image


# ============================================
# احراز هویت (با رمز ADMIN_SECRET)
# ============================================
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_pass = os.getenv("ADMIN_SECRET", "righnews-admin-2026")

        if username == admin_user and password == admin_pass:
            request.session.update({"authenticated": True, "user": username})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)


# ============================================
# آپلود تصویر
# ============================================
async def upload_image(file: UploadFile) -> str:
    """ذخیره تصویر آپلود شده و برگرداندن URL نسبی"""
    if not file or not file.filename:
        return ""
    
    # تولید نام یکتا
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        return ""
    
    filename = f"{secrets.token_hex(8)}{ext}"
    upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return f"/static/uploads/{filename}"


# ============================================
# ModelView برای مقالات
# ============================================
class ArticleAdmin(ModelView, model=Article):
    # تنظیمات عمومی
    name = "مقاله"
    name_plural = "مقالات"
    icon = "fa-solid fa-newspaper"
    column_default_sort = ("created_at", True)
    page_size = 20
    
    # ستون‌های لیست
    column_list = [
        Article.id,
        Article.title_persian,
        Article.source_type,
        Article.verified,
        Article.published_at,
        Article.created_at,
    ]
    
    # نام‌های فارسی ستون‌ها
    column_labels = {
        Article.id: "شناسه",
        Article.source_url: "لینک منبع",
        Article.source_type: "نوع منبع",
        Article.title_english: "عنوان انگلیسی",
        Article.title_persian: "عنوان فارسی",
        Article.content_english: "متن انگلیسی",
        Article.content_persian: "ترجمه فارسی",
        Article.image_url: "آدرس تصویر",
        Article.published_at: "تاریخ انتشار",
        Article.created_at: "تاریخ ثبت",
        Article.verified: "راستی‌آزمایی",
        Article.fact_check_notes: "یادداشت راستی‌آزمایی",
    }
    
    # فیلدهای فرم (به ترتیب نمایش)
    form_columns = [
        Article.title_persian,
        Article.title_english,
        Article.source_url,
        Article.source_type,
        Article.content_persian,
        Article.content_english,
        Article.image_url,
        Article.verified,
        Article.fact_check_notes,
        Article.published_at,
    ]
    
    # نوع فیلدها
    form_args = {
        "title_persian": {"label": "عنوان فارسی"},
        "title_english": {"label": "عنوان انگلیسی"},
        "content_persian": {
            "label": "ترجمه فارسی",
            "render_kw": {"rows": 10, "dir": "rtl"},
        },
        "content_english": {
            "label": "متن انگلیسی",
            "render_kw": {"rows": 10, "dir": "ltr"},
        },
        "image_url": {
            "label": "آدرس تصویر (URL) — می‌توانید لینک دلخواه وارد کنید",
        },
        "source_type": {
            "label": "نوع منبع",
            "render_kw": {"placeholder": "arxiv / rss / web"},
        },
        "fact_check_notes": {
            "label": "یادداشت راستی‌آزمایی",
            "render_kw": {"rows": 3},
        },
    }
    
    # جستجو و فیلتر
    column_searchable_list = [Article.title_persian, Article.title_english, Article.content_persian]
    column_sortable_list = [Article.id, Article.created_at, Article.published_at, Article.verified]
    column_filters = [Article.source_type, Article.verified]
    
    # جزئیات
    column_details_list = [
        Article.id,
        Article.title_persian,
        Article.title_english,
        Article.content_persian,
        Article.content_english,
        Article.image_url,
        Article.source_url,
        Article.source_type,
        Article.verified,
        Article.fact_check_notes,
        Article.published_at,
        Article.created_at,
    ]

    async def on_model_change(self, data, model, is_created, request):
        """قبل از ذخیره: اگر تصویر نداشت، خودکار انتخاب شود"""
        if not data.get("image_url") and data.get("title_english") and data.get("content_english"):
            data["image_url"] = pick_image(
                data["title_english"],
                data["content_english"],
                article_id=getattr(model, "id", None),
            )


# ============================================
# ModelView برای Embeddings (فقط مشاهده)
# ============================================
class ArticleEmbeddingAdmin(ModelView, model=ArticleEmbedding):
    name = "بخش‌بندی"
    name_plural = "بخش‌بندی‌های RAG"
    icon = "fa-solid fa-brain"
    column_list = [ArticleEmbedding.id, ArticleEmbedding.article_id, ArticleEmbedding.chunk_index]
    column_labels = {
        ArticleEmbedding.id: "شناسه",
        ArticleEmbedding.article_id: "شناسه مقاله",
        ArticleEmbedding.chunk_index: "شماره بخش",
        ArticleEmbedding.chunk_text: "متن بخش",
        ArticleEmbedding.created_at: "تاریخ ایجاد",
    }
    can_create = False
    can_edit = False
    can_delete = True


# ============================================
# اتصال به FastAPI
# ============================================
def setup_admin(app):
    """نصب پنل ادمین روی اپلیکیشن"""
    from starlette.middleware.sessions import SessionMiddleware

    # اضافه کردن SessionMiddleware برای احراز هویت
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET", "righnews-session-secret-change-in-prod"),
    )

    # ایجاد Admin
    authentication_backend = AdminAuth(secret_key="righnews-admin-secret")
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="پنل مدیریت رای‌نیوز",
        logo_url="/static/logo.svg",
        base_url="/admin",
    )

    # ثبت ModelView ها
    admin.add_view(ArticleAdmin)
    admin.add_view(ArticleEmbeddingAdmin)

    return admin
