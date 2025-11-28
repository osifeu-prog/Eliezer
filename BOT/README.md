# 🤖 Telegram CRM Bot

בוט טלגרם חכם לניהול לידים, הכולל שרת API מהיר (FastAPI) לקליטת לידים מהאתר.

## 🚀 תכונות חדשות
- **FastAPI Backend**: ביצועים מהירים ותיעוד אוטומטי ב `/docs`.
- **Async Support**: המערכת לא "נתקעת" בזמן כתיבה לדאטהבייס.
- **CSV Export**: ייצוא כל הלידים לאקסל בלחיצת כפתור.
- **Admin Security**: רק מנהלים מורשים יכולים לגשת לבוט.

## 🛠️ התקנה והרצה

1. **התקנת תלויות**
   ```bash
   pip install -r requirements.txt
# Eliezer Bot

בוט טלגרם המנוהל על ידי FastAPI ורץ על פלטפורמת Railway.

## מבנה הפרויקט
* `main.py`: השרת (FastAPI) שמקבל את ה-Webhooks.
* `bot.py`: לוגיקת הבוט (פקודות והודעות).
* `config.py`: הגדרות ומשתני סביבה.

## התקנה
1. וודא שכל משתני הסביבה מוגדרים ב-Railway:
   - `TELEGRAM_BOT_TOKEN`
   - `WEBHOOK_URL` (ללא /telegram בסוף, הקוד מוסיף זאת)
   - `ADMIN_IDS`

2. דחוף את הקוד לגיטהאב והתחבר ל-Railway.
