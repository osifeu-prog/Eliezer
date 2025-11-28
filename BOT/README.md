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
# Eliezer Advanced CRM AI Bot

בוט טלגרם מתקדם המשלב CRM, PostgreSQL, AI (OpenAI/HuggingFace) ומערכת תזמון (JobQueue), המיועד לחברות פרסום. הבוט פרוס ב-Railway באמצעות Webhooks ו-FastAPI.

## 🔑 הגדרות סביבה נדרשות ב-Railway

* `TELEGRAM_BOT_TOKEN`: הטוקן שקיבלת מ-BotFather.
* `WEBHOOK_URL`: ה-Domain של השרת שלך ב-Railway (ללא / בסוף).
* **`DATABASE_URL`**: נוצר אוטומטית על ידי Railway לאחר הוספת תוסף PostgreSQL.
* `ADMIN_IDS`: רשימת מזהי משתמשים מופרדת בפסיקים (למשל: `12345,67890`).
* `LOG_GROUP_ID`: מזהה קבוצת הלוגים (צריך להתחיל במינוס, לדוגמה: `-100123...`).
* `SUPPORT_GROUP_ID`: מזהה קבוצת התמיכה.
* **`DB_EXPORT_PASSKEY`**: סיסמה סודית לייצוא נתונים דרך `/export [passkey]`.
* `OPENAI_API_KEY` או `HF_API_TOKEN` (אחד מהם נדרש עבור AI).

## 🚀 פריסה והרצה

1.  **הוספת PostgreSQL:** בתוך פרויקט Railway, הוסף שירות מסד נתונים מסוג PostgreSQL.
2.  **הגדרת המשתנים:** הכנס את כל משתני הסביבה (כולל המפתחות והקבוצות) כפי שמפורט למעלה.
3.  **העלאת קוד:** דחף את כל 12 הקבצים הללו לריפוזיטורי ה-GitHub המחובר ל-Railway.
4.  **הפעלה:** Railway יבנה ויפעיל את הפרויקט באופן אוטומטי, יצור את הטבלאות, ויגדיר את ה-Webhook.
