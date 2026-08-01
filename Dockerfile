# استفاده از پایتون نسخه ۳.۱۰ که برای هوش مصنوعی بسیار پایدار است
FROM python:3.10-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب پیش‌نیازهای سیستمی (برای جلوگیری از خطای psycopg2 و کتابخانه‌های دیتابیس)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل requirements و نصب کتابخانه‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن بقیه کدهای پروژه
COPY . .

# باز کردن پورت ۸۰۰۰ (پورت پیش‌فرض FastAPI)
EXPOSE 8000

# دستور اجرای سرور
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
