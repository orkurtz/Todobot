# Dockerfile סופי וממוטב עבור Todobot ב-Railway

# שלב 1: הבנייה (Builder) - התקנה של תלויות
FROM python:3.10-slim as builder

# מונע יצירת קבצי .pyc מיותרים ומוודא פלט מיידי
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# התקנת כלי פיתוח (build-essential) הנחוצים לקומפילציה
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# העתקת קובץ הדרישות והתקנה
COPY requirements.txt .
# הדגל --no-cache-dir חוסך נפח ע"י מניעת קבצי מטמון pip
RUN pip install --no-cache-dir -r requirements.txt

# **** פקודות ניקוי אגרסיביות להפחתת גודל (מפחיתות את ה-7.9 GB) ****
# ניקוי מטמון pip
RUN rm -rf /root/.cache/pip
# הסרת תיקיות קומפילציה מיותרות
RUN find /usr/local/lib/python*/site-packages/ -name "__pycache__" -exec rm -rf {} +
# אם יש צורך בניקוי נוסף:
# RUN rm -rf /root/.config/huggingface 
# RUN rm -rf /root/.torch

# ---
# שלב 2: הריצה (Runtime) - תמונה קטנה ומוכנה להפצה
FROM python:3.10-slim

WORKDIR /app

# התקנת תלויות מערכת נחוצות לזמן הריצה (כגון ל-PostgreSQL ו-NumPy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# **** התיקון לשגיאת gunicorn could not be found ****
# מוסיף את נתיב ההפעלה של ספריות Python (כמו gunicorn) לנתיבי המערכת
ENV PATH="/usr/local/bin:$PATH"

# העתק את התלויות המותקנות והמנוקות משלב ה-Builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# העתק את כל קבצי הפרויקט שלך (קוד המקור)
COPY . .

# פקודת חשיפת הפורט עבור Railway
EXPOSE $PORT

# פקודת ההפעלה הסופית של האפליקציה
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
