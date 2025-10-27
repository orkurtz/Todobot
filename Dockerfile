# Dockerfile ממוטב עבור Todobot ב-Railway

# שלב 1: הבנייה (Builder) - התקנה של תלויות
# משתמשים בתמונת slim כבסיס קטן יותר להתקנה
FROM python:3.10-slim as builder

# מונע יצירת קבצי .pyc מיותרים ומוודא פלט מיידי
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# התקנת כלי פיתוח (build-essential) הנחוצים לקומפילציה של תלויות כבדות
# קריטי לספריות C/C++ ב-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# העתקת קובץ הדרישות והתקנה
COPY requirements.txt .
# הדגל --no-cache-dir חוסך נפח ע"י מניעת קבצי מטמון pip
RUN pip install --no-cache-dir -r requirements.txt

# **** סעיף 2.1: פקודות ניקוי אגרסיביות ****
# מטרת הניקוי היא להפחית את נפח ה-site-packages לפני העברה לשלב הריצה
# 1. ניקוי מטמון pip שעדיין נותר
RUN rm -rf /root/.cache/pip

# 2. הסרת תיקיות קומפילציה מיותרות (כמו __pycache__) מתוך התלויות
RUN find /usr/local/lib/python*/site-packages/ -name "__pycache__" -exec rm -rf {} +

# 3. ניקוי תיקיות דגמים/מטמון של ספריות AI/ML כבדות (הערה: שנה לפי הצורך)
# אם הדגם הורד לתיקיית הבית, נקה אותה:
# RUN rm -rf /root/.cache/huggingface  # נפוץ לספריות Transformers
# RUN rm -rf /root/.torch               # נפוץ לספריות PyTorch

# ---
# שלב 2: הריצה (Runtime) - תמונה קטנה ומוכנה להפצה
FROM python:3.10-slim

WORKDIR /app

# התקנת תלויות מערכת נחוצות לזמן הריצה בלבד (ללא כלי קומפילציה)
# libpq-dev: קריטי לחיבורי PostgreSQL (בשימוש נפוץ ב-Railway)
# libgomp1: נחוץ לריצת ספריות ממוטבות כמו NumPy/SciPy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# העתק את התלויות המותקנות והמנוקות משלב ה-Builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# העתק את כל קבצי הפרויקט שלך (קוד המקור, כולל app.py, gunicorn.conf.py וכו')
COPY . .

# פקודת חשיפת הפורט עבור Railway
EXPOSE $PORT

# פקודת ההפעלה הסופית של האפליקציה (בהתאם ל-Procfile שלך)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
