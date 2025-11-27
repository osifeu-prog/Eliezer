# 🤖 Telegram CRM Bot

בוט טלגרם חכם לניהול CRM עבור משרד פרסום, עם אינטגרציה מלאה לאתר דרך Webhook.

## 📁 מבנה הפרויקט
BOT/
├── bot.py # קובץ הבוט הראשי
├── config.py # הגדרות
├── requirements.txt # תלויות
├── database.py # ניהול מסד נתונים
├── webhook_handler.py # טיפול בבקשות מהאתר
├── crm_manager.py # לוגיקת CRM
└── README.md # הוראות

text

## 🚀 התקנה והרצה

### 1. התקנת תלויות
```bash
pip install -r requirements.txt
2. הגדרת משתני סביבה
צור קובץ .env עם ההגדרות הבאות:

env
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://yourdomain.com
DATABASE_URL=sqlite:///crm_bot.db
USE_WEBHOOK=false
3. קבלת Telegram Bot Token
פתחו את @BotFather בטלגרם

שלחו /newbot

בחרו שם לבוט

קבלו את ה-token ושמרו אותו ב-.env

4. הרצת הבוט
bash
# לפיתוח (using polling)
python bot.py

# ל-production (using webhook)
python bot.py
🌐 אינטגרציה עם האתר
הגדרת Webhook באתר
הוסף את הקוד הבא לאתר שלך כדי לשלוח לידים אוטומטית:

javascript
// דוגמה לשליחת ליד מה-API
async function sendLeadToCRM(leadData) {
    try {
        const response = await fetch('/webhook/lead', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(leadData)
        });
        
        return await response.json();
    } catch (error) {
        console.error('Error sending lead:', error);
    }
}

// שימוש
const leadData = {
    name: "שם הלקוח",
    phone: "050-1234567", 
    email: "client@example.com",
    source: "website",
    notes: "התעניין בשירותי שיווק"
};

sendLeadToCRM(leadData);
API Endpoints
POST /webhook/lead

מקבל לידים חדשים מהאתר

Body: { "name": "שם", "phone": "טלפון", "email": "אימייל", "notes": "הערות" }

GET /webhook/status

בדיקת סטטוס השרת

GET /health

בדיקת בריאות המערכת

💾 מסד נתונים
המערכת תומכת ב:

SQLite (ברירת מחדל, לפיתוח)

PostgreSQL (מומלץ ל-production)

MySQL

🎯 תכונות הבוט
ניהול לידים אוטומטי

סטטיסטיקות בזמן אמת

התראות על לידים חדשים

אינטגרציית Webhook

ממשק ניהול בטלגרם

ייצוא דוחות (בפיתוח)

התראות Scheduled (בפיתוח)

📊 פקודות הבוט
/start - התחלת שימוש

/leads - הצג לידים אחרונים

/stats - הצג סטטיסטיקות

/help - עזרה והסברים

🔧 התאמה אישית
ניתן להתאים את הבוט לצרכים שלכם על ידי:

עריכת config.py - הגדרות מערכת

הוספת שדות נוספים ב-database.py

שינוי הטקסטים וההודעות ב-bot.py

הוספת אינטגרציות עם מערכות נוספות

📞 תמיכה
לשאלות ותמיכה, פנו לצוות הפיתוח.

text

## 🚀 הוראות התקנה:

1. צור תיקיה חדשה בשם `BOT` והכנס לתוכה
2. שמור כל קובץ בשם המתאים
3. התקן את התלויות: `pip install -r requirements.txt`
4. צור קובץ `.env` עם הטוקן של הבוט שלך
5. הרץ את הבוט: `python bot.py`

הבוט יוכל כעת:
- לקבל לידים מהאתר דרך Webhook
- לנהל את כל הלידים במסד נתונים
- לספק סטטיסטיקות ודוחות
- לאפשר ניהול מלא דרך הטלגרם

אתה מוזמן להתאים את הקוד לצרכים הספציפיים של משרד הפרסום שלך!
