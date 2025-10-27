# שלב 1: שלב הבנייה - להורדת והתקנת כל התלויות הנדרשות
FROM python:3.10-slim as builder

# הגדרת משתני סביבה כדי להבטיח ש-Python לא יצור קבצי קומפילציה מיותרים
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# התקנת תלויות מערכת נחוצות לקומפילציה אם יש צורך (כמו gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# העתק רק את קובץ הדרישות והתקן אותו.
# שימוש ב--no-cache-dir מבטיח ניקוי קבצים זמניים מיד, וחוסך נפח.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---
# שלב 2: שלב הריצה - תמונה קטנה ונקייה לזמן ריצה בלבד
FROM python:3.10-slim

# ייתכן שצריך להתקין תלויות מערכת קטנות לזמן ריצה בלבד (כמו libgomp ל-numpy/scipy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# העתק את התלויות המותקנות משלב הבנייה (הדרך שחוסכת מקום)
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# העתק את כל שאר קבצי הפרויקט שלך
COPY . .

# Railway צריך את הפורט פתוח
EXPOSE $PORT

# הפקודה שתריץ את האפליקציה (כמו ב-Procfile שלך)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
