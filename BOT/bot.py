from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, LOG_GROUP_ID, SUPPORT_GROUP_ID, DB_EXPORT_PASSKEY, logger
from crm_manager import crm
from ai_service import ai_service
from qr_generator import generate_user_qr
from database import fetch_all_users_csv
import datetime
import io
import re

# --- פונקציות עזר ותזמון ---

async def notify_log_group(context, message):
    if LOG_GROUP_ID:
        try:
            await context.bot.send_message(chat_id=LOG_GROUP_ID, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to log to group {LOG_GROUP_ID}: {e}")

async def send_initial_followup(context: ContextTypes.DEFAULT_TYPE):
    """נשלח לאחר 24 שעות"""
    user_id = context.job.data
    try:
        await context.bot.send_message(
            chat_id=user_id, 
            text="👋 היי שוב! רציתי לוודא שקיבלת את כל המידע שאתה צריך. יש שאלה ספציפית שתרצה לשאול?"
        )
        await crm.update_lead_score(user_id, 1) 
    except Exception as e:
        logger.warning(f"Failed to send followup to {user_id}: {e}")

def schedule_followup(context: ContextTypes.DEFAULT_TYPE, user_id):
    """מגדיר שליחת הודעה לאחר 24 שעות"""
    delay = datetime.timedelta(hours=24)
    context.job_queue.run_once(
        send_initial_followup, 
        delay, 
        data=user_id, 
        name=f"followup_{user_id}"
    )

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # 1. ניתוח פרמטר ה-START
    referrer_id = None
    campaign_source = None
    
    if args and args[0]:
        param = args[0]
        # ניתוח קוד קמפיין מורכב (Campaign_ReferrerID) או פשוט
        match = re.match(r'([A-Za-z0-9]+)_(\d+)', param)
        if match:
            campaign_source = match.group(1)
            referrer_id = int(match.group(2))
        elif param.isdigit():
            referrer_id = int(param)
        else:
            campaign_source = param
            
    # 2. רישום ל-DB
    await crm.add_user(user.id, user.username, user.first_name, referred_by=referrer_id, campaign_source=campaign_source)
    
    # 3. תזמון Follow-up
    schedule_followup(context, user.id)
    
    # 4. עדכון קבוצת לוגים
    score = await crm.get_user_lead_score(user.id)
    log_msg = f"🔔 **ליד חדש!** (ציון: {score})\nID: {user.id}\nמקור: {campaign_source or 'ישיר'}"
    if referrer_id:
        log_msg += f" (הופנה ע\"י {referrer_id})"
    await notify_log_group(context, log_msg)

    # 5. תפריט ראשי
    keyboard = [
        [InlineKeyboardButton("🤖 צור QR שיתוף אישי", callback_data="get_qr")],
        [InlineKeyboardButton("💬 פנה לתמיכה", callback_data="support_req")],
        [InlineKeyboardButton("📊 הסטטוס שלי", callback_data="my_status")]
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔒 פאנל ניהול", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"שלום {user.first_name}! אני הבוט המתקדם לחברת הפרסום שלך. איך אפשר לעזור?",
        reply_markup=reply_markup
    )

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.effective_user.id
    
    await crm.update_lead_score(user_id, 1)

    # 1. ניתוח כוונות באמצעות AI
    intent_prompt = f"סווג את כוונת המשתמש הבאה לקטגוריה אחת בלבד. התשובה שלך תהיה רק שם הקטגוריה: 'התעניינות במחיר', 'בקשת תמיכה', 'שאלה כללית', 'בקשת חזרה טלפונית', 'אחר'. טקסט: {user_text}"
    intent_type = "שאלה כללית"
    
    if ai_service.use_openai: 
        try:
            intent_response = await ai_service.get_response(intent_prompt)
            # מנקה את התגובה כדי לקבל רק את שם הקטגוריה
            intent_type = intent_response.strip().replace("'", "").split('\n')[0] 
        except Exception as e:
            logger.warning(f"AI intent analysis failed: {e}")
            
    # 2. שמירה ב-CRM עם סיווג
    await crm.log_interaction(user_id, user_text, source="user_msg", intent_type=intent_type)
    
    # 3. קבלת תשובה רגילה מ-AI
    await update.message.reply_chat_action("typing")
    ai_response = await ai_service.get_response(user_text)
    
    await update.message.reply_text(ai_response)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    
    if data == "get_qr":
        # ניקוד בונוס על יצירת QR
        await crm.update_lead_score(user.id, 2)
        bot_username = context.bot.username
        
        # לצורך הדוגמה, נשתמש ב-ID כקמפיין ברירת מחדל ב-QR האישי
        qr_bio = generate_user_qr(bot_username, user.id, campaign_source="SHARE") 
        await query.message.reply_photo(photo=qr_bio, caption="זה קוד ה-QR האישי שלך!\nכל מי שיסרוק אותו יירשם תחתיך (מקור: SHARE).")
    
    elif data == "support_req":
        if SUPPORT_GROUP_ID:
            # מעדכן את הניקוד על פנייה יזומה לתמיכה
            await crm.update_lead_score(user.id, 3) 
            text = f"🆘 **בקשת תמיכה חדשה (ציון גבוה)**\nמאת: {user.first_name} ({user.id})\nיוזר: @{user.username}\n\nנא לפנות אליו בפרטי."
            await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=text, parse_mode='Markdown')
            await query.edit_message_text("הבקשה נשלחה לצוות התמיכה. ניצור איתך קשר בהקדם!")
        else:
            await query.edit_message_text("מערכת התמיכה אינה מוגדרת כרגע.")

    elif data == "my_status":
        score = await crm.get_user_lead_score(user.id)
        # מעקב אחר הפניות
        referrals = await crm.get_referral_count(user.id)
        await query.edit_message_text(f"📊 **הסטטוס שלך**\n⭐ ניקוד הליד שלך: {score}/10\n👥 אנשים שהצטרפו דרכך: {referrals}")

    elif data == "admin_panel":
        if user.id not in ADMIN_IDS:
            await query.edit_message_text("אין לך גישה.")
            return
        
        stats = await crm.get_stats()
        text = (
            f"🔒 **פאנל ניהול**\n"
            f"👥 משתמשים רשומים: {stats['total_users']}\n"
            f"⭐ ניקוד ממוצע: {stats['avg_score']}\n"
            f"\nכדי לייצא נתונים, השתמש בפקודה:\n`/export [סיסמה סודית]`"
        )
        await query.edit_message_text(text, parse_mode='Markdown')

async def export_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("אין לך הרשאת אדמין.")
        return
    
    if not DB_EXPORT_PASSKEY or not context.args or context.args[0] != DB_EXPORT_PASSKEY:
        await update.message.reply_text("הסיסמה לייצוא אינה תקינה או חסרה בהגדרות השרת.")
        return
        
    await update.message.reply_text("מייצא נתונים... אנא המתן.")
    
    csv_file = await fetch_all_users_csv()
    
    if csv_file:
        # שליחת הקובץ ב-BytesI/O
        csv_file_bytes = io.BytesIO(csv_file.getvalue().encode('utf-8'))
        csv_file_bytes.name = f'eliezer_leads_{datetime.date.today()}.csv'
        await context.bot.send_document(
            chat_id=user.id, 
            document=csv_file_bytes, 
            caption="הנתונים של כל המשתמשים מחוברת ה-CRM."
        )
    else:
        await update.message.reply_text("לא נמצאו נתונים לייצוא או אירעה שגיאה.")


def create_bot_application():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("export", export_data_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_message))
    
    return application
