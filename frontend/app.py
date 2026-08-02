import streamlit as st
import requests
import json

# ============================================
# تنظیمات
# ============================================
# آدرس API شما روی گردو
API_BASE_URL = "https://righnews.gerdoo.app"

# رمز ادمین برای endpointهای محافظت‌شده
ADMIN_SECRET = "righnews-admin-2026"

# ============================================
# تنظیمات صفحه (RTL و فارسی)
# ============================================
st.set_page_config(
    page_title="RighNews - آژانس خبری هوش مصنوعی",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# استایل سفارشی برای RTL و فونت فارسی
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Vazirmatn', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    
    .main-title {
        text-align: center;
        color: #1E88E5;
        font-size: 3em;
        margin-bottom: 0;
    }
    
    .subtitle {
        text-align: center;
        color: #666;
        margin-top: 0;
    }
    
    .verified-badge {
        background-color: #4CAF50;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        display: inline-block;
    }
    
    .unverified-badge {
        background-color: #F44336;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        display: inline-block;
    }
    
    .article-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-right: 4px solid #1E88E5;
        margin-bottom: 15px;
    }
    
    .persian-title {
        color: #1E88E5;
        font-size: 1.3em;
        font-weight: 700;
        margin-bottom: 10px;
    }
    
    .english-title {
        color: #666;
        font-size: 0.95em;
        font-style: italic;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# توابع API
# ============================================
def get_articles():
    """دریافت لیست مقالات"""
    try:
        response = requests.get(f"{API_BASE_URL}/articles", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"خطا در اتصال به سرور: {e}")
        return None

def get_article(article_id: int):
    """دریافت جزئیات یک مقاله"""
    try:
        response = requests.get(f"{API_BASE_URL}/articles/{article_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"خطا در دریافت مقاله: {e}")
        return None

def process_article(arxiv_id: str):
    """پردازش یک مقاله جدید"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/process-article",
            json={"arxiv_id": arxiv_id},
            timeout=60  # پردازش ممکن است طولانی باشد
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"خطا در پردازش: {e}")
        return None

# ============================================
# هدر اصلی
# ============================================
st.markdown('<h1 class="main-title">📰 RighNews</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">آژانس خبری هوش مصنوعی | ترجمه و راستی‌آزمایی خودکار مقالات علمی</p>', unsafe_allow_html=True)
st.markdown("---")

# ============================================
# سایدبار
# ============================================
with st.sidebar:
    st.header("🔧 کنترل پنل")
    
    st.markdown("### 🆕 پردازش مقاله جدید")
    arxiv_input = st.text_input(
        "شناسه یا URL مقاله arXiv",
        placeholder="مثال: 1706.03762",
        help="مثال‌ها: 1706.03762 یا https://arxiv.org/abs/1706.03762"
    )
    
    if st.button("🚀 پردازش و ذخیره", type="primary", use_container_width=True):
        if arxiv_input:
            with st.spinner("در حال دانلود، ترجمه و راستی‌آزمایی..."):
                result = process_article(arxiv_input)
                if result:
                    if result.get("status") == "success":
                        st.success(f"✅ مقاله با موفقیت ذخیره شد (ID: {result.get('article_id')})")
                        st.balloons()
                        # رفرش لیست
                        st.session_state['refresh'] = True
                    else:
                        st.error(f"❌ خطا: {result.get('error', 'خطای ناشناخته')}")
        else:
            st.warning("لطفاً یک شناسه arXiv وارد کنید")
    
    st.markdown("---")
    st.markdown("### 📊 وضعیت سیستم")
    
    # تست سلامت
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5).json()
        st.success("🟢 سرور آنلاین")
        st.info(f"🤖 مدل: {health.get('model', 'N/A')}")
        
        db_test = requests.get(f"{API_BASE_URL}/db-test", timeout=5).json()
        st.info(f"📚 تعداد مقالات: {db_test.get('article_count', 0)}")
    except:
        st.error("🔴 سرور آفلاین")
    
    st.markdown("---")
    st.markdown("### 🔗 لینک‌های مفید")
    st.markdown(f"- [📖 API Docs]({API_BASE_URL}/docs)")
    st.markdown("- [📂 GitHub](https://github.com/AKplayerReal/RighNews)")

# ============================================
# محتوای اصلی
# ============================================
tab1, tab2 = st.tabs(["📚 لیست مقالات", "ℹ️ درباره RighNews"])

with tab1:
    st.subheader("📚 مقالات ترجمه و راستی‌آزمایی شده")
    
    articles_data = get_articles()
    
    if articles_data and articles_data.get("articles"):
        articles = articles_data["articles"]
        st.info(f"📊 تعداد کل مقالات: {len(articles)}")
        
        # جستجو
        search_query = st.text_input("🔍 جستجو در مقالات", placeholder="کلیدواژه فارسی یا انگلیسی...")
        
        for article in articles:
            # فیلتر جستجو
            if search_query:
                searchable = f"{article['title_english']} {article['title_persian']} {article['content_persian']}".lower()
                if search_query.lower() not in searchable:
                    continue
            
            # کارت مقاله
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f'<div class="persian-title">{article["title_persian"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="english-title">{article["title_english"]}</div>', unsafe_allow_html=True)
                
                with col2:
                    if article["verified"]:
                        st.markdown('<span class="verified-badge">✓ راستی‌آزمایی شد</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="unverified-badge">⚠ نیاز به بررسی</span>', unsafe_allow_html=True)
                
                # نمایش خلاصه
                with st.expander(f"📖 مشاهده جزئیات کامل (ID: {article['id']})"):
                    inner_col1, inner_col2 = st.columns(2)
                    
                    with inner_col1:
                        st.markdown("#### 🇬🇧 چکیده انگلیسی")
                        st.info(article.get("content_english", "نامشخص"))
                    
                    with inner_col2:
                        st.markdown("#### 🇮🇷 ترجمه فارسی")
                        st.success(article.get("content_persian", "نامشخص"))
                    
                    st.markdown("---")
                    st.markdown("#### ✅ گزارش راستی‌آزمایی")
                    st.write(f"**وضعیت:** {article.get('fact_check_notes', 'نامشخص')}")
                    st.write(f"**تاریخ انتشار:** {article.get('published_at', 'نامشخص')}")
                    st.write(f"**منبع:** {article.get('source_type', 'نامشخص')}")
                    
                    if article.get("source_url"):
                        st.markdown(f"[🔗 مشاهده مقاله اصلی]({article['source_url']})")
                
                st.markdown("---")
    else:
        st.warning("هنوز مقاله‌ای پردازش نشده است. از سایدبار یک شناسه arXiv وارد کنید!")

with tab2:
    st.subheader("ℹ️ درباره پروژه RighNews")
    
    st.markdown("""
    ### 🎯 هدف پروژه
    
    RighNews یک **آژانس خبری هوش مصنوعی** است که به صورت خودکار:
    
    1. 📥 **جمع‌آوری**: مقالات علمی را از arXiv دانلود می‌کند
    2. 🌐 **ترجمه**: عنوان و چکیده را با استفاده از DeepSeek V4 Flash به فارسی ترجمه می‌کند
    3. ✅ **راستی‌آزمایی**: اعداد و مشخصات فنی را استخراج و حفظ می‌کند
    4. 💾 **ذخیره‌سازی**: همه داده‌ها را در PostgreSQL نگه می‌دارد
    
    ### 🛠️ تکنولوژی‌های استفاده شده
    
    | لایه | تکنولوژی |
    |------|---------|
    | Backend | FastAPI + Python |
    | AI Translation | DeepSeek V4 Flash via GapGPT |
    | Database | PostgreSQL (Gerdoo PaaS) |
    | Frontend | Streamlit |
    | Deployment | Gerdoo Cloud Platform |
    | Source Control | GitHub |
    
    ### 👨‍💻 توسعه‌دهنده
    
    این پروژه توسط یک دانشجوی پژوهشگر در حوزه هوش مصنوعی ساخته شده است.
    
    ### 📊 آمار فعلی
    """)
    
    # نمایش آمار زنده
    try:
        db_test = requests.get(f"{API_BASE_URL}/db-test", timeout=5).json()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 تعداد مقالات", db_test.get("article_count", 0))
        with col2:
            st.metric("✓ راستی‌آزمایی شده", db_test.get("article_count", 0))
        with col3:
            st.metric("📊 وضعیت", "فعال")
    except:
        st.warning("خطا در دریافت آمار")
