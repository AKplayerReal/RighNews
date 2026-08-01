FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پورت پیش‌فرض اگر متغیر محیطی نبود
ENV PORT=8000
EXPOSE $PORT

# اجرای مستقیم با python تا بتواند متغیر PORT را بخواند
CMD python main.py